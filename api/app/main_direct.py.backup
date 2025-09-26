#!/usr/bin/env python3
"""
VA-Calibration API - Direct execution version
Runs calibration immediately without job storage
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from datetime import datetime, timezone
import subprocess
import json
import tempfile
import os

# Import async calibration components
from .async_calibration import (
    AsyncCalibrationRequest,
    JobResponse,
    JobStatusResponse,
    JobListResponse,
    JobOutputResponse,
    start_async_calibration,
    get_job_status,
    list_calibration_jobs,
    get_job_output,
    cancel_job,
    delete_calibration_job
)

# Import Celery job endpoints
from .job_endpoints import (
    create_calibration_job as celery_create_job,
    list_celery_jobs_simple,
    CalibrationJobRequest
)

# Import WebSocket components
from .websocket_handler import (
    websocket_router,
    get_connection_stats
)
from .calibration_service import (
    get_calibration_service
)
from .security import setup_security
from .validation import (
    validate_va_data, ValidationError as CustomValidationError,
    EnhancedValidationMiddleware
)

# Import the router with batch endpoints
from .router import router as api_router

app = FastAPI(
    title="VA-Calibration API (Direct)",
    version="0.1.0",
    description="Direct calibration API with real-time WebSocket support"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup security (API key authentication and rate limiting)
setup_security(app, enable_api_key=True, enable_rate_limit=True)

# Include routers
app.include_router(websocket_router, prefix="/ws", tags=["websockets"])
app.include_router(api_router)  # This includes batch endpoints and job management


class AgeGroup(str, Enum):
    NEONATE = "neonate"
    CHILD = "child"


class DatasetInfo(BaseModel):
    """Information about an available dataset"""
    name: str = Field(description="Dataset name")
    file_path: str = Field(description="Path to the dataset file")
    exists: bool = Field(description="Whether the file exists")
    age_group: str = Field(description="Target age group")
    description: str = Field(description="Dataset description")
    sample_size: Optional[int] = Field(default=None, description="Number of samples")
    causes: Optional[List[str]] = Field(default=None, description="Available causes")


class SupportedConfiguration(BaseModel):
    """Supported configuration for VA calibration"""
    algorithms: List[str] = Field(description="Supported VA algorithms")
    age_groups: List[str] = Field(description="Supported age groups")
    countries: List[str] = Field(description="Supported countries")
    mmat_types: List[str] = Field(description="Supported misclassification matrix types")
    input_formats: List[str] = Field(description="Supported input data formats")


class CauseMapping(BaseModel):
    """Cause mapping information"""
    specific_cause: str = Field(description="Specific cause name")
    broad_cause: str = Field(description="Mapped broad cause category")
    age_group: str = Field(description="Age group this mapping applies to")


class CauseMappingResponse(BaseModel):
    """Response containing cause mappings for an age group"""
    age_group: str = Field(description="Age group")
    broad_causes: List[str] = Field(description="List of broad cause categories")
    mappings: List[CauseMapping] = Field(description="Detailed cause mappings")
    total_mappings: int = Field(description="Total number of specific-to-broad cause mappings")


class DatasetPreviewResponse(BaseModel):
    """Response for dataset preview with statistics"""
    dataset_id: str = Field(description="Dataset identifier")
    sample_data: List[Dict[str, Any]] = Field(description="Sample of first few records")
    total_records: int = Field(description="Total number of records in dataset")
    columns: List[str] = Field(description="Column names in the dataset")
    statistics: Dict[str, Any] = Field(description="Basic dataset statistics")
    metadata: Dict[str, Any] = Field(description="Dataset metadata")


class ConvertCausesRequest(BaseModel):
    """Request to convert specific causes to broad causes"""
    data: List[Dict[str, str]] = Field(
        description="List of records with 'cause' and 'id' fields"
    )
    age_group: AgeGroup = Field(description="Age group for cause mapping")

    @validator('data')
    def validate_data(cls, v):
        if not v:
            raise ValueError("Data cannot be empty")
        for record in v:
            if 'cause' not in record or 'id' not in record:
                raise ValueError("Each record must have 'cause' and 'id' fields")
        return v


class ConvertCausesResponse(BaseModel):
    """Response from cause conversion"""
    converted_data: List[Dict[str, str]] = Field(
        description="Data with broad causes added"
    )
    broad_cause_matrix: Dict[str, List[int]] = Field(
        description="Binary matrix format for VA calibration"
    )
    conversion_summary: Dict[str, int] = Field(
        description="Summary of conversions by broad cause"
    )
    unmapped_causes: List[str] = Field(
        description="Specific causes that couldn't be mapped"
    )


class ValidateDataRequest(BaseModel):
    """Request to validate input data format"""
    data: Dict[str, Union[List[Dict], List[List[int]], List[int]]] = Field(
        description="VA data to validate"
    )
    age_group: AgeGroup = Field(description="Age group for validation")
    expected_format: str = Field(
        default="auto",
        description="Expected format: 'specific_causes', 'broad_causes', 'death_counts', or 'auto'"
    )


class ValidationResult(BaseModel):
    """Single validation result"""
    algorithm: str = Field(description="Algorithm name")
    is_valid: bool = Field(description="Whether the data is valid")
    detected_format: str = Field(description="Detected data format")
    issues: List[str] = Field(description="List of validation issues")
    recommendations: List[str] = Field(description="Recommendations for fixing issues")
    sample_size: Optional[int] = Field(description="Number of records if applicable")
    cause_distribution: Optional[Dict[str, int]] = Field(description="Cause distribution if applicable")


class ValidateDataResponse(BaseModel):
    """Response from data validation"""
    overall_valid: bool = Field(description="Whether all data is valid")
    validation_results: List[ValidationResult] = Field(description="Per-algorithm validation results")
    global_issues: List[str] = Field(description="Issues affecting all algorithms")
    recommendations: List[str] = Field(description="Global recommendations")


class CalibrationRequest(BaseModel):
    """Direct calibration request - supports both design spec and simplified parameters"""

    # Design spec parameters (backwards compatible)
    data_source: Optional[str] = Field(
        default=None,
        description="Data source: 'sample' or 'custom' (from API design)"
    )
    sample_dataset: Optional[str] = Field(
        default=None,
        description="Sample dataset ID if data_source='sample'"
    )
    data_format: Optional[str] = Field(
        default=None,
        description="Data format: 'specific_causes', 'broad_causes', or 'death_counts'"
    )

    # Current implementation parameters
    va_data: Optional[Dict[str, Union[List[Dict], List[List[int]], str]]] = Field(
        default=None,
        description="VA data or 'use_example' to use default data. If not provided, uses example data."
    )
    age_group: AgeGroup = Field(
        default=AgeGroup.NEONATE,
        description="Age group: 'neonate' or 'child'"
    )
    country: str = Field(
        default="Mozambique",
        description="Country for calibration"
    )
    mmat_type: str = Field(
        default="prior",
        description="How to utilize misclassification: 'prior' or 'fixed'"
    )
    ensemble: bool = Field(
        default=True,
        description="Whether to perform ensemble calibration"
    )
    async_: bool = Field(
        default=False,
        description="Whether to run calibration asynchronously",
        alias="async"
    )

    @validator('va_data', pre=True)
    def handle_design_spec_params(cls, v, values):
        """Convert design spec parameters to implementation parameters"""
        data_source = values.get('data_source')
        sample_dataset = values.get('sample_dataset')

        # If using design spec parameters
        if data_source == 'sample' and sample_dataset:
            # Map sample dataset IDs to example data
            dataset_mapping = {
                'comsamoz_broad': 'use_example',
                'comsamoz_specific': 'use_example',
                # Add more mappings as needed
            }
            if sample_dataset in dataset_mapping:
                return {"insilicova": dataset_mapping[sample_dataset]}

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "age_group": "neonate",
                    "country": "Mozambique"
                },
                {
                    "va_data": {
                        "insilicova": "use_example"
                    },
                    "age_group": "neonate"
                },
                {
                    "va_data": {
                        "insilicova": [
                            {"cause": "Birth asphyxia", "id": "death_001"},
                            {"cause": "Neonatal sepsis", "id": "death_002"}
                        ]
                    },
                    "age_group": "neonate"
                },
                {
                    "data_source": "sample",
                    "sample_dataset": "comsamoz_broad",
                    "age_group": "neonate",
                    "country": "Mozambique"
                }
            ]
        }
    }


def check_r_setup():
    """Check if R and required packages are available"""
    try:
        # Check R
        result = subprocess.run(["which", "Rscript"], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Rscript not found"

        # Check packages
        check_cmd = [
            "Rscript", "-e",
            "if(!require(vacalibration, quietly=TRUE)) stop('vacalibration not found'); if(!require(jsonlite, quietly=TRUE)) stop('jsonlite not found')"
        ]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Missing R packages: {result.stderr}"

        return True, "R ready"
    except Exception as e:
        return False, str(e)


@app.get("/")
async def root():
    """Health check"""
    r_ready, r_msg = check_r_setup()

    return {
        "status": "healthy" if r_ready else "warning",
        "service": "VA-Calibration API (Direct)",
        "r_status": r_msg,
        "data_files": {
            "comsamoz_broad": os.path.exists("../data/comsamoz_public_broad.rda"),
            "comsamoz_openVA": os.path.exists("../data/comsamoz_public_openVAout.rda")
        }
    }


@app.post("/calibrate")
async def calibrate(request: CalibrationRequest):
    """Run calibration directly or asynchronously based on async parameter"""

    # Apply enhanced validation
    try:
        request_data = request.model_dump()
        # Determine data format if not specified
        data_format = 'specific_causes'  # default
        if request_data.get('va_data'):
            sample_data = next(iter(request_data['va_data'].values()))
            if sample_data == 'use_example':
                pass  # Keep as is
            elif isinstance(sample_data, list) and sample_data:
                if isinstance(sample_data[0], dict):
                    data_format = 'specific_causes'
                elif isinstance(sample_data[0], list):
                    data_format = 'broad_causes'
            elif isinstance(sample_data, dict):
                data_format = 'death_counts'

            validated_data = validate_va_data(
                request_data['va_data'],
                request_data.get('age_group', 'adult'),
                data_format
            )
            request_data['va_data'] = validated_data
    except CustomValidationError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INVALID_DATA_FORMAT",
                "message": e.message,
                "field": e.field,
                "value": str(e.value) if e.value else None
            }
        )

    # Check if async mode is requested
    if request.async_:
        # Use calibration service for async execution
        calibration_service = get_calibration_service()
        job_id = calibration_service.create_job(request_data)

        # Start calibration in background
        import asyncio
        asyncio.create_task(calibration_service.run_calibration(job_id))

        return {
            "status": "accepted",
            "job_id": job_id,
            "message": "Calibration job started. Connect to WebSocket or poll status endpoint for updates.",
            "urls": {
                "status": f"/calibrate/{job_id}/status",
                "websocket": f"ws://localhost:8000/calibrate/{job_id}/logs"
            },
            "estimated_duration_seconds": 15
        }

    # Otherwise run synchronously using service layer
    calibration_service = get_calibration_service()
    job_id = calibration_service.create_job(request_data)

    try:
        # Run calibration synchronously
        result = await calibration_service.run_calibration(job_id)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Calibration failed: {str(e)}"
        )


# Async calibration endpoints (Celery-based with background workers)
@app.post("/jobs/calibrate")
async def create_calibration_job_endpoint(request: CalibrationJobRequest, background_tasks: BackgroundTasks):
    """Create a new Celery-based calibration job with background workers"""
    return await celery_create_job(request, background_tasks)


@app.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_calibration_job_status(job_id: str):
    """Get status and results of a calibration job"""
    return await get_job_status(job_id)


@app.get("/jobs")
async def list_jobs(
    limit: int = Query(50, description="Maximum number of jobs to return"),
    status: Optional[str] = Query(None, description="Filter by job status")
):
    """List calibration jobs with optional filtering"""
    return await list_celery_jobs_simple(limit=limit, status=status)


@app.get("/jobs/{job_id}/output", response_model=JobOutputResponse)
async def get_calibration_job_output(
    job_id: str,
    start_line: int = Query(0, description="Starting line number for output")
):
    """Get R script output for streaming (useful for progress monitoring)"""
    return await get_job_output(job_id, start_line=start_line)


@app.post("/jobs/{job_id}/cancel", response_model=JobStatusResponse)
async def cancel_calibration_job(job_id: str):
    """Cancel a running calibration job"""
    return await cancel_job(job_id)


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a calibration job"""
    return await delete_calibration_job(job_id)


# WebSocket-enhanced calibration endpoints
@app.post("/calibrate/realtime")
async def create_realtime_calibration(request: CalibrationRequest):
    """Create a new calibration job with real-time WebSocket updates"""
    # Real-time calibrations are always async
    if not request.async_:
        request.async_ = True

    # Convert to async request
    async_request = AsyncCalibrationRequest(
        va_data=request.va_data,
        age_group=request.age_group.value,
        country=request.country,
        mmat_type=request.mmat_type,
        ensemble=request.ensemble
    )

    # Create job using the enhanced calibration service
    calibration_service = get_calibration_service()
    job_id = calibration_service.create_job(async_request.model_dump())

    # Start calibration in background
    import asyncio
    asyncio.create_task(calibration_service.run_calibration(job_id))

    return JobResponse(
        job_id=job_id,
        status="pending",
        message=f"Real-time calibration job created. Connect to WebSocket: /ws/calibrate/{job_id}/logs",
        created_at=datetime.now().isoformat()
    )


@app.get("/calibrate/{job_id}/status")
async def get_realtime_job_status(job_id: str):
    """Get detailed status of a real-time calibration job"""
    calibration_service = get_calibration_service()
    status = calibration_service.get_job_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return status


@app.get("/websocket/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    stats = await get_connection_stats()
    return {
        "websocket_connections": stats,
        "server_time": datetime.now(timezone.utc).isoformat()
    }


@app.get("/example-data")
async def get_example_info():
    """Get information about available example data"""

    return {
        "neonate": {
            "dataset": "comsamoz_public_broad",
            "file": "../data/comsamoz_public_broad.rda",
            "exists": os.path.exists("../data/comsamoz_public_broad.rda"),
            "description": "1190 neonatal deaths from Mozambique COMSA study",
            "causes": [
                "congenital_malformation",
                "pneumonia",
                "sepsis_meningitis_inf",
                "ipre",
                "other",
                "prematurity"
            ]
        },
        "specific_causes": {
            "dataset": "comsamoz_public_openVAout",
            "file": "../data/comsamoz_public_openVAout.rda",
            "exists": os.path.exists("../data/comsamoz_public_openVAout.rda"),
            "description": "Same data with specific cause assignments"
        }
    }


@app.get("/datasets", response_model=List[DatasetInfo])
async def get_datasets():
    """List available sample datasets for VA calibration"""

    datasets = []

    # Neonate broad causes dataset
    broad_file = "../data/comsamoz_public_broad.rda"
    datasets.append(DatasetInfo(
        name="comsamoz_public_broad",
        file_path=broad_file,
        exists=os.path.exists(broad_file),
        age_group="neonate",
        description="1190 neonatal deaths from Mozambique COMSA study with broad cause assignments",
        sample_size=1190,
        causes=[
            "congenital_malformation",
            "pneumonia",
            "sepsis_meningitis_inf",
            "ipre",
            "other",
            "prematurity"
        ]
    ))

    # Specific causes dataset
    specific_file = "../data/comsamoz_public_openVAout.rda"
    datasets.append(DatasetInfo(
        name="comsamoz_public_openVAout",
        file_path=specific_file,
        exists=os.path.exists(specific_file),
        age_group="neonate",
        description="Same COMSA data with specific (high-resolution) cause assignments",
        sample_size=1190,
        causes=None  # Many specific causes mapped to broad
    ))

    # CHAMPS misclassification matrices
    mmat_file = "../data/Mmat_champs.rda"
    datasets.append(DatasetInfo(
        name="Mmat_champs",
        file_path=mmat_file,
        exists=os.path.exists(mmat_file),
        age_group="both",
        description="CHAMPS-based misclassification matrices for calibration",
        sample_size=None,
        causes=None
    ))

    return datasets


@app.get("/supported-configurations", response_model=SupportedConfiguration)
async def get_supported_configurations():
    """Get supported configurations for VA calibration"""

    return SupportedConfiguration(
        algorithms=[
            "eava",
            "insilicova",
            "interva"
        ],
        age_groups=[
            "neonate",  # 0-27 days
            "child"     # 1-59 months
        ],
        countries=[
            "Bangladesh",
            "Ethiopia",
            "Kenya",
            "Mali",
            "Mozambique",
            "Sierra Leone",
            "South Africa",
            "other"  # For countries not in CHAMPS
        ],
        mmat_types=[
            "prior",  # Propagates uncertainty (default)
            "fixed"   # Uses fixed misclassification matrix
        ],
        input_formats=[
            "specific_causes",  # Output from codEAVA()/crossVA() functions
            "broad_causes",     # Output from cause_map() function
            "death_counts"      # Integer counts by broad cause
        ]
    )


@app.get("/cause-mappings/{age_group}", response_model=CauseMappingResponse)
async def get_cause_mappings(age_group: AgeGroup):
    """Get cause mappings for a specific age group"""

    # Check R is available
    r_ready, r_msg = check_r_setup()
    if not r_ready:
        raise HTTPException(status_code=500, detail=f"R not ready: {r_msg}")

    # Create temp directory
    with tempfile.TemporaryDirectory(prefix="causemap_") as tmpdir:
        output_file = os.path.join(tmpdir, "cause_mappings.json")

        # Create R script to extract cause mappings
        r_script_file = os.path.join(tmpdir, "get_mappings.R")
        with open(r_script_file, 'w') as f:
            f.write(get_cause_mapping_script())

        # Run R script
        cmd = ["Rscript", r_script_file, age_group.value, output_file]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        # Check for output
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                mapping_data = json.load(f)

            if mapping_data.get("success"):
                mappings = []
                for mapping in mapping_data.get("mappings", []):
                    mappings.append(CauseMapping(
                        specific_cause=mapping["specific_cause"],
                        broad_cause=mapping["broad_cause"],
                        age_group=age_group.value
                    ))

                return CauseMappingResponse(
                    age_group=age_group.value,
                    broad_causes=mapping_data.get("broad_causes", []),
                    mappings=mappings,
                    total_mappings=len(mappings)
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=mapping_data.get("error", "Failed to get cause mappings")
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"R script failed: {result.stderr or result.stdout}"
            )


@app.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(dataset_id: str, limit: int = 10):
    """Preview sample data with statistics for a specific dataset"""

    # Check R is available
    r_ready, r_msg = check_r_setup()
    if not r_ready:
        raise HTTPException(status_code=500, detail=f"R not ready: {r_msg}")

    # Validate dataset_id
    valid_datasets = {
        "comsamoz_public_broad": "../data/comsamoz_public_broad.rda",
        "comsamoz_public_openVAout": "../data/comsamoz_public_openVAout.rda",
        "Mmat_champs": "../data/Mmat_champs.rda"
    }

    if dataset_id not in valid_datasets:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' not found. Available: {list(valid_datasets.keys())}"
        )

    file_path = valid_datasets[dataset_id]
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Dataset file not found: {file_path}"
        )

    # Create temp directory for R processing
    with tempfile.TemporaryDirectory(prefix="preview_") as tmpdir:
        output_file = os.path.join(tmpdir, "preview.json")

        # Create R script to preview dataset
        r_script_file = os.path.join(tmpdir, "preview.R")
        with open(r_script_file, 'w') as f:
            f.write(get_dataset_preview_script())

        # Run R script
        cmd = ["Rscript", r_script_file, dataset_id, str(limit), output_file]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        # Check for output
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                preview_data = json.load(f)

            if preview_data.get("success"):
                return DatasetPreviewResponse(
                    dataset_id=dataset_id,
                    sample_data=preview_data.get("sample_data", []),
                    total_records=preview_data.get("total_records", 0),
                    columns=preview_data.get("columns", []),
                    statistics=preview_data.get("statistics", {}),
                    metadata=preview_data.get("metadata", {})
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=preview_data.get("error", "Failed to preview dataset")
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"R script failed: {result.stderr or result.stdout}"
            )


@app.post("/convert/causes", response_model=ConvertCausesResponse)
async def convert_causes(request: ConvertCausesRequest):
    """Convert specific causes to broad causes using cause_map()"""

    # Check R is available
    r_ready, r_msg = check_r_setup()
    if not r_ready:
        raise HTTPException(status_code=500, detail=f"R not ready: {r_msg}")

    # Create temp directory
    with tempfile.TemporaryDirectory(prefix="convert_") as tmpdir:
        input_file = os.path.join(tmpdir, "input.json")
        output_file = os.path.join(tmpdir, "output.json")

        # Prepare input data
        input_data = {
            "data": request.data,
            "age_group": request.age_group.value
        }

        # Write input
        with open(input_file, 'w') as f:
            json.dump(input_data, f)

        # Create R script
        r_script_file = os.path.join(tmpdir, "convert.R")
        with open(r_script_file, 'w') as f:
            f.write(get_convert_causes_script())

        # Run R script
        cmd = ["Rscript", r_script_file, input_file, output_file]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        # Check for output
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                output_data = json.load(f)

            if output_data.get("success"):
                return ConvertCausesResponse(
                    converted_data=output_data.get("converted_data", []),
                    broad_cause_matrix=output_data.get("broad_cause_matrix", {}),
                    conversion_summary=output_data.get("conversion_summary", {}),
                    unmapped_causes=output_data.get("unmapped_causes", [])
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=output_data.get("error", "Cause conversion failed")
                )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"R script failed: {result.stderr or result.stdout}"
            )


@app.post("/validate", response_model=ValidateDataResponse)
async def validate_data(request: ValidateDataRequest):
    """Validate input data format before calibration"""

    validation_results = []
    global_issues = []
    global_recommendations = []
    overall_valid = True

    # Get expected causes for age group
    if request.age_group == AgeGroup.NEONATE:
        expected_causes = [
            "congenital_malformation", "pneumonia", "sepsis_meningitis_inf",
            "ipre", "other", "prematurity"
        ]
    else:  # child
        expected_causes = [
            "malaria", "pneumonia", "diarrhea", "severe_malnutrition",
            "hiv", "injury", "other", "other_infections", "nn_causes"
        ]

    # Validate each algorithm's data
    for algo_name, algo_data in request.data.items():
        result = _validate_algorithm_data(
            algo_name, algo_data, expected_causes, request.expected_format
        )
        validation_results.append(result)

        if not result.is_valid:
            overall_valid = False

    # Add global validations
    if not request.data:
        global_issues.append("No algorithm data provided")
        overall_valid = False

    if len(request.data) > 5:
        global_recommendations.append(
            "Consider using fewer algorithms for faster processing"
        )

    return ValidateDataResponse(
        overall_valid=overall_valid,
        validation_results=validation_results,
        global_issues=global_issues,
        recommendations=global_recommendations
    )


def _validate_algorithm_data(
    algo_name: str,
    data: Union[List[Dict], List[List[int]], List[int]],
    expected_causes: List[str],
    expected_format: str
) -> ValidationResult:
    """Validate data for a single algorithm"""

    issues = []
    recommendations = []
    detected_format = "unknown"
    sample_size = None
    cause_distribution = None

    try:
        # Detect format and validate
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                # Check for specific causes format (support both 'id' and 'ID')
                if 'cause' in data[0] and ('id' in data[0] or 'ID' in data[0]):
                    detected_format = "specific_causes"
                    sample_size = len(data)

                    # Check for required fields
                    for i, record in enumerate(data):
                        if 'cause' not in record:
                            issues.append(f"Record {i} missing 'cause' field")
                        if 'id' not in record and 'ID' not in record:
                            issues.append(f"Record {i} missing 'id' or 'ID' field")

                    # Get cause distribution
                    causes = [record.get('cause', 'unknown') for record in data]
                    cause_distribution = {cause: causes.count(cause) for cause in set(causes)}

                else:
                    detected_format = "unknown_dict"
                    issues.append("Dictionary format detected but missing required 'cause' and 'id'/'ID' fields")

            elif isinstance(data[0], list):
                # Binary matrix format
                detected_format = "broad_causes_matrix"
                sample_size = len(data)

                # Validate matrix dimensions
                if len(data[0]) != len(expected_causes):
                    issues.append(
                        f"Matrix width {len(data[0])} doesn't match expected causes {len(expected_causes)}"
                    )

                # Check for binary values
                for i, row in enumerate(data):
                    if not all(val in [0, 1] for val in row):
                        issues.append(f"Row {i} contains non-binary values")

                # Calculate cause distribution
                if not issues:
                    cause_sums = [sum(row[j] for row in data) for j in range(len(expected_causes))]
                    cause_distribution = {expected_causes[j]: cause_sums[j] for j in range(len(expected_causes))}

            elif isinstance(data[0], (int, float)):
                # Death counts format
                detected_format = "death_counts"

                if len(data) != len(expected_causes):
                    issues.append(
                        f"Count vector length {len(data)} doesn't match expected causes {len(expected_causes)}"
                    )

                # Check for non-negative values
                if any(val < 0 for val in data):
                    issues.append("Death counts cannot be negative")

                # Calculate total and distribution
                if not issues:
                    sample_size = sum(data)
                    cause_distribution = {expected_causes[i]: data[i] for i in range(len(expected_causes))}

        elif isinstance(data, str):
            if data == "use_example":
                detected_format = "example_data"
            else:
                detected_format = "unknown_string"
                issues.append(f"Unknown string value: {data}")

        else:
            issues.append(f"Unsupported data type: {type(data)}")

        # Format-specific validations
        if expected_format != "auto" and detected_format != expected_format:
            issues.append(f"Expected format '{expected_format}' but detected '{detected_format}'")

        # Add recommendations
        if detected_format == "specific_causes":
            recommendations.append("Consider using /convert/causes endpoint to convert to broad causes")

        if sample_size and sample_size < 100:
            recommendations.append("Sample size is small; results may be less reliable")

        if sample_size and sample_size > 10000:
            recommendations.append("Large sample size may increase processing time")

        # Check for balanced data
        if cause_distribution:
            max_count = max(cause_distribution.values())
            min_count = min(cause_distribution.values())
            if max_count > 10 * min_count:
                recommendations.append("Data appears imbalanced; consider stratified sampling")

    except Exception as e:
        issues.append(f"Validation error: {str(e)}")

    return ValidationResult(
        algorithm=algo_name,
        is_valid=len(issues) == 0,
        detected_format=detected_format,
        issues=issues,
        recommendations=recommendations,
        sample_size=sample_size,
        cause_distribution=cause_distribution
    )


def get_dataset_preview_script():
    """Generate R script to preview dataset"""
    return '''
library(jsonlite)
library(vacalibration)

args <- commandArgs(trailingOnly = TRUE)
dataset_id <- args[1]
limit <- as.numeric(args[2])
output_file <- args[3]

tryCatch({
    if(dataset_id == "comsamoz_public_broad") {
        data(comsamoz_public_broad, envir = environment())
        dataset <- comsamoz_public_broad

        # Extract sample data
        data_matrix <- dataset$data
        sample_indices <- 1:min(limit, nrow(data_matrix))
        sample_data <- list()

        for(i in sample_indices) {
            row_data <- list()
            row_data[["id"]] <- rownames(data_matrix)[i]
            for(col in colnames(data_matrix)) {
                row_data[[col]] <- data_matrix[i, col]
            }
            sample_data[[length(sample_data) + 1]] <- row_data
        }

        # Calculate statistics
        col_sums <- colSums(data_matrix)
        statistics <- list(
            total_deaths = nrow(data_matrix),
            cause_distribution = as.list(col_sums),
            most_common_cause = names(col_sums)[which.max(col_sums)],
            least_common_cause = names(col_sums)[which.min(col_sums)]
        )

        metadata <- list(
            description = "Mozambique COMSA study with broad cause assignments",
            age_group = "neonate",
            format = "binary_matrix",
            source = "COMSA study"
        )

    } else if(dataset_id == "comsamoz_public_openVAout") {
        data(comsamoz_public_openVAout, envir = environment())
        dataset <- comsamoz_public_openVAout

        # Extract sample data (assuming it has similar structure)
        if(is.list(dataset) && !is.null(dataset$data)) {
            data_content <- dataset$data
        } else {
            data_content <- dataset
        }

        # Handle different data structures
        if(is.matrix(data_content) || is.data.frame(data_content)) {
            sample_indices <- 1:min(limit, nrow(data_content))
            sample_data <- list()

            for(i in sample_indices) {
                row_data <- list()
                row_data[["id"]] <- rownames(data_content)[i]
                if(is.matrix(data_content)) {
                    for(col in colnames(data_content)) {
                        row_data[[col]] <- data_content[i, col]
                    }
                } else {
                    for(col in names(data_content)) {
                        row_data[[col]] <- data_content[i, col]
                    }
                }
                sample_data[[length(sample_data) + 1]] <- row_data
            }

            statistics <- list(
                total_records = nrow(data_content),
                columns = if(is.matrix(data_content)) colnames(data_content) else names(data_content)
            )
        } else {
            # Handle other structures
            sample_data <- list(list(note = "Complex data structure - preview not available"))
            statistics <- list(type = class(data_content))
        }

        metadata <- list(
            description = "COMSA data with specific cause assignments",
            age_group = "neonate",
            format = "openVA_output",
            source = "COMSA study"
        )

    } else if(dataset_id == "Mmat_champs") {
        data(Mmat_champs, envir = environment())
        dataset <- Mmat_champs

        # Handle misclassification matrix structure
        sample_data <- list(list(
            note = "Misclassification matrices",
            structure = "Contains calibration matrices for different age groups and countries"
        ))

        statistics <- list(
            type = "misclassification_matrices",
            countries = if("country" %in% names(dataset)) unique(dataset$country) else "multiple"
        )

        metadata <- list(
            description = "CHAMPS-based misclassification matrices",
            age_group = "both",
            format = "calibration_matrices",
            source = "CHAMPS study"
        )
    } else {
        stop(paste("Unknown dataset:", dataset_id))
    }

    # Prepare output
    output <- list(
        success = TRUE,
        sample_data = sample_data,
        total_records = if(exists("data_matrix")) nrow(data_matrix) else if(exists("data_content") && (is.matrix(data_content) || is.data.frame(data_content))) nrow(data_content) else 0,
        columns = if(exists("data_matrix")) colnames(data_matrix) else if(exists("data_content") && is.matrix(data_content)) colnames(data_content) else c(),
        statistics = statistics,
        metadata = metadata
    )

    # Write output
    write(toJSON(output, auto_unbox = TRUE), output_file)

}, error = function(e) {
    output <- list(success = FALSE, error = as.character(e$message))
    write(toJSON(output, auto_unbox = TRUE), output_file)
})
'''


def get_convert_causes_script():
    """Generate R script to convert specific causes to broad causes"""
    return '''
library(jsonlite)
library(vacalibration)

args <- commandArgs(trailingOnly = TRUE)
input_file <- args[1]
output_file <- args[2]

tryCatch({
    # Read input
    input_data <- fromJSON(input_file)

    cat("Input data structure:\\n")
    cat("Class of input_data$data:", class(input_data$data), "\\n")
    cat("Length of input_data$data:", length(input_data$data), "\\n")

    # Create data frame for cause_map
    # jsonlite automatically converts array of objects to data frame
    if (is.data.frame(input_data$data)) {
        df_causes <- input_data$data
        # Ensure column names are correct for cause_map
        if ("id" %in% names(df_causes) && !"ID" %in% names(df_causes)) {
            names(df_causes)[names(df_causes) == "id"] <- "ID"
        }
    } else if (is.list(input_data$data)) {
        # Fallback for list format
        ids <- c()
        causes <- c()
        for(i in seq_along(input_data$data)) {
            item <- input_data$data[[i]]
            ids <- c(ids, as.character(item[["id"]]))
            causes <- c(causes, as.character(item[["cause"]]))
        }
        df_causes <- data.frame(
            ID = ids,
            cause = causes,
            stringsAsFactors = FALSE
        )
    } else {
        stop("Unexpected data format")
    }

    # Use cause_map to convert
    broad_cause_matrix <- cause_map(df = df_causes, age_group = input_data$age_group)

    # Convert matrix to list format for JSON
    broad_cause_matrix_list <- list()
    for(col in colnames(broad_cause_matrix)) {
        broad_cause_matrix_list[[col]] <- as.numeric(broad_cause_matrix[, col])
    }

    # Create converted data with broad causes added
    converted_data <- list()
    for(i in 1:nrow(broad_cause_matrix)) {
        # Find which broad cause is assigned (assumes one-hot encoding)
        broad_cause_idx <- which(broad_cause_matrix[i, ] == 1)
        broad_cause <- if(length(broad_cause_idx) > 0) colnames(broad_cause_matrix)[broad_cause_idx[1]] else "other"

        converted_data[[i]] <- list(
            id = df_causes$ID[i],
            specific_cause = df_causes$cause[i],
            broad_cause = broad_cause
        )
    }

    # Calculate conversion summary
    conversion_summary <- as.list(colSums(broad_cause_matrix))

    # Find unmapped causes (this would require more sophisticated logic)
    # For now, assume all causes were mapped
    unmapped_causes <- character(0)

    # Prepare output
    output <- list(
        success = TRUE,
        converted_data = converted_data,
        broad_cause_matrix = broad_cause_matrix_list,
        conversion_summary = conversion_summary,
        unmapped_causes = unmapped_causes
    )

    # Write output
    write(toJSON(output, auto_unbox = TRUE), output_file)

}, error = function(e) {
    output <- list(success = FALSE, error = as.character(e$message))
    write(toJSON(output, auto_unbox = TRUE), output_file)
})
'''


def get_cause_mapping_script():
    """Generate R script to extract cause mappings"""
    return '''
library(jsonlite)
library(vacalibration)

args <- commandArgs(trailingOnly = TRUE)
age_group <- args[1]
output_file <- args[2]

tryCatch({
    age_group <- tolower(age_group)

    if(age_group == "neonate") {
        # NEONATAL CAUSES MAPPING
        congenital_malformation <- c("congenital malformation", "malformation")
        pneumonia <- c("neonatal pneumonia", "acute resp infect incl pneumonia", "pneumonia")
        sepsis_meningitis_inf <- c("neonatal sepsis", "pregnancy-related sepsis", "sepsis (non-obstetric)",
                                   "meningitis and encephalitis", "dengue fever", "diarrhoeal diseases",
                                   "diarrhea", "haemorrhagic fever (non-dengue)", "hiv/aids related death",
                                   "malaria", "measles", "other and unspecified infect dis", "pertussis",
                                   "pulmonary tuberculosis", "tetanus", "sepsis", "meningitis", "nnt")
        ipre <- c("birth asphyxia", "intrapartum")
        other <- c("abortion-related death", "accid poisoning & noxious subs", "anaemia of pregnancy",
                   "assault", "asthma", "accid drowning and submersion", "accid expos to smoke fire & flame",
                   "accid fall", "acute abdomen", "acute cardiac disease", "breast neoplasms",
                   "chronic obstructive pulmonary dis", "contact with venomous plant/animal",
                   "diabetes mellitus", "digestive neoplasms", "ectopic pregnancy", "epilepsy",
                   "exposure to force of nature", "fresh stillbirth", "intentional self-harm",
                   "liver cirrhosis", "macerated stillbirth", "obstetric haemorrhage", "obstructed labour",
                   "oral neoplasms", "other and unspecified cardiac dis", "other and unspecified external cod",
                   "other and unspecified maternal cod", "other and unspecified neonatal cod",
                   "other and unspecified neoplasms", "other transport accident", "other and unspecified ncd",
                   "pregnancy-induced hypertension", "renal failure", "reproductive neoplasms mf",
                   "respiratory neoplasms", "road traffic accident", "ruptured uterus", "severe anaemia",
                   "severe malnutrition", "sickle cell with crisis", "stroke", "other")
        prematurity <- c("prematurity", "preterm")

        mappings_list <- list(
            list(causes = congenital_malformation, broad_cause = "congenital_malformation"),
            list(causes = pneumonia, broad_cause = "pneumonia"),
            list(causes = sepsis_meningitis_inf, broad_cause = "sepsis_meningitis_inf"),
            list(causes = ipre, broad_cause = "ipre"),
            list(causes = other, broad_cause = "other"),
            list(causes = prematurity, broad_cause = "prematurity")
        )

        broad_causes <- c("congenital_malformation", "pneumonia", "sepsis_meningitis_inf",
                         "ipre", "other", "prematurity")

    } else if(age_group == "child") {
        # CHILD CAUSES MAPPING
        malaria <- c("malaria")
        pneumonia <- c("acute resp infect incl pneumonia", "neonatal pneumonia", "pneumonia")
        diarrhea <- c("diarrhoeal diseases", "diarrhea/dysentery")
        severe_malnutrition <- c("severe malnutrition", "malnutrition")
        hiv <- c("hiv/aids related death", "aids")
        injury <- c("accid drowning and submersion", "accid expos to smoke fire & flame", "accid fall",
                   "accid poisoning & noxious subs", "assault", "exposure to force of nature",
                   "intentional self-harm", "other and unspecified external cod", "other transport accident",
                   "road traffic accident", "injury")
        other <- c("abortion-related death", "acute abdomen", "acute cardiac disease", "anaemia of pregnancy",
                  "asthma", "breast neoplasms", "chronic obstructive pulmonary dis",
                  "contact with venomous plant/animal", "diabetes mellitus", "digestive neoplasms",
                  "ectopic pregnancy", "epilepsy", "fresh stillbirth", "liver cirrhosis",
                  "macerated stillbirth", "obstetric haemorrhage", "obstructed labour", "oral neoplasms",
                  "other and unspecified cardiac dis", "other and unspecified maternal cod",
                  "other and unspecified ncd", "other and unspecified neonatal cod",
                  "other and unspecified neoplasms", "pregnancy-induced hypertension", "renal failure",
                  "reproductive neoplasms mf", "respiratory neoplasms", "ruptured uterus",
                  "severe anaemia", "sickle cell with crisis", "stroke")
        other_infections <- c("dengue fever", "haemorrhagic fever (non-dengue)", "measles",
                             "meningitis and encephalitis", "neonatal sepsis", "other and unspecified infect dis",
                             "pertussis", "pregnancy-related sepsis", "pulmonary tuberculosis",
                             "sepsis (non-obstetric)", "tetanus", "measles", "meningitis/encephalitis",
                             "other infections")
        nn_causes <- c("congenital malformation", "birth asphyxia", "prematurity", "malformation",
                      "intrapartum", "preterm")

        mappings_list <- list(
            list(causes = malaria, broad_cause = "malaria"),
            list(causes = pneumonia, broad_cause = "pneumonia"),
            list(causes = diarrhea, broad_cause = "diarrhea"),
            list(causes = severe_malnutrition, broad_cause = "severe_malnutrition"),
            list(causes = hiv, broad_cause = "hiv"),
            list(causes = injury, broad_cause = "injury"),
            list(causes = other, broad_cause = "other"),
            list(causes = other_infections, broad_cause = "other_infections"),
            list(causes = nn_causes, broad_cause = "nn_causes")
        )

        broad_causes <- c("malaria", "pneumonia", "diarrhea", "severe_malnutrition", "hiv",
                         "injury", "other", "other_infections", "nn_causes")

    } else {
        stop("Invalid age group. Must be \'neonate\' or \'child\'")
    }

    # Create detailed mappings
    detailed_mappings <- list()
    for(mapping in mappings_list) {
        for(cause in mapping$causes) {
            detailed_mappings[[length(detailed_mappings) + 1]] <- list(
                specific_cause = cause,
                broad_cause = mapping$broad_cause
            )
        }
    }

    # Prepare output
    output <- list(
        success = TRUE,
        age_group = age_group,
        broad_causes = broad_causes,
        mappings = detailed_mappings
    )

    # Write output
    write(toJSON(output, auto_unbox = TRUE), output_file)

}, error = function(e) {
    output <- list(success = FALSE, error = as.character(e$message))
    write(toJSON(output, auto_unbox = TRUE), output_file)
})
'''


def get_r_script():
    """Generate R script for calibration"""
    return '''
library(jsonlite)
library(vacalibration)

args <- commandArgs(trailingOnly = TRUE)
input_file <- args[1]
output_file <- args[2]

tryCatch({
    # Read input
    input_data <- fromJSON(input_file)

    # Process VA data
    va_data <- list()
    for (algo in names(input_data$va_data)) {
        data_value <- input_data$va_data[[algo]]

        if (is.character(data_value) && data_value == "use_example") {
            # Load example data
            if (input_data$age_group == "neonate") {
                data(comsamoz_public_broad, envir = environment())
                va_data[[algo]] <- comsamoz_public_broad$data
            } else {
                # Create synthetic child data
                n <- 100
                child_causes <- c("malaria", "pneumonia", "diarrhea", "severe_malnutrition",
                                "hiv", "injury", "other", "other_infections", "nn_causes")
                mat <- matrix(0, nrow=n, ncol=length(child_causes))
                colnames(mat) <- child_causes
                for (i in 1:n) {
                    mat[i, sample(1:length(child_causes), 1)] <- 1
                }
                va_data[[algo]] <- mat
            }
        } else if (is.list(data_value) && length(data_value) > 0 && !is.null(data_value[[1]]$cause)) {
            # Convert specific causes to broad causes
            df <- data.frame(
                ID = sapply(data_value, function(x) as.character(ifelse(!is.null(x$ID), x$ID, x$id))),
                cause = sapply(data_value, function(x) as.character(x$cause)),
                stringsAsFactors = FALSE
            )
            va_data[[algo]] <- cause_map(df = df, age_group = input_data$age_group)
        } else {
            va_data[[algo]] <- data_value
        }
    }

    # Run calibration
    result <- vacalibration(
        va_data = va_data,
        age_group = input_data$age_group,
        country = input_data$country,
        Mmat_type = input_data$mmat_type,
        ensemble = input_data$ensemble,
        verbose = FALSE,
        plot_it = FALSE
    )

    # Prepare output
    output <- list(success = TRUE)

    # Add uncalibrated CSMF
    if (!is.null(result$p_uncalib)) {
        output$uncalibrated <- as.list(result$p_uncalib)
    }

    # Add calibrated results
    if (!is.null(result$pcalib_postsumm)) {
        output$calibrated <- list()
        for (algo in dimnames(result$pcalib_postsumm)[[1]]) {
            output$calibrated[[algo]] <- list(
                mean = as.list(result$pcalib_postsumm[algo, "postmean", ]),
                lower_ci = as.list(result$pcalib_postsumm[algo, "lowcredI", ]),
                upper_ci = as.list(result$pcalib_postsumm[algo, "upcredI", ])
            )
        }
    } else if (!is.null(result$p_calib)) {
        # Handle fixed case
        output$calibrated <- list()
        for (algo in names(result$p_calib)) {
            output$calibrated[[algo]] <- list(
                mean = as.list(result$p_calib[[algo]]),
                lower_ci = as.list(result$p_calib[[algo]]),
                upper_ci = as.list(result$p_calib[[algo]])
            )
        }
    }

    # Write output
    write(toJSON(output, auto_unbox = TRUE, na = "null"), output_file)

}, error = function(e) {
    output <- list(success = FALSE, error = as.character(e$message))
    write(toJSON(output, auto_unbox = TRUE), output_file)
})
'''


if __name__ == "__main__":
    import uvicorn

    # Check setup
    r_ready, r_msg = check_r_setup()
    print(f"R Status: {r_msg}")

    # Check data files
    data_files = [
        "../data/comsamoz_public_broad.rda",
        "../data/comsamoz_public_openVAout.rda"
    ]
    for f in data_files:
        if os.path.exists(f):
            print(f"✓ Found: {f}")
        else:
            print(f"✗ Missing: {f}")

    uvicorn.run(app, host="0.0.0.0", port=8000)