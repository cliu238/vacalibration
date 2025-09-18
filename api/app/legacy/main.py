from fastapi import FastAPI, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union, Literal
from enum import Enum
import uuid
import asyncio
import subprocess
import json
import os
from datetime import datetime
import tempfile
import shutil

app = FastAPI(
    title="VA-Calibration API",
    version="0.1.0",
    description="Web API for calibrating computer-coded verbal autopsy algorithms"
)

# Store job results in memory (use Redis in production)
job_store: Dict[str, Dict] = {}


class VAAlgorithm(str, Enum):
    EAVA = "eava"
    INSILICOVA = "insilicova"
    INTERVA = "interva"


class AgeGroup(str, Enum):
    NEONATE = "neonate"
    CHILD = "child"


class Country(str, Enum):
    BANGLADESH = "Bangladesh"
    ETHIOPIA = "Ethiopia"
    KENYA = "Kenya"
    MALI = "Mali"
    MOZAMBIQUE = "Mozambique"
    SIERRA_LEONE = "Sierra Leone"
    SOUTH_AFRICA = "South Africa"
    OTHER = "other"


class CalibrationRequest(BaseModel):
    """Request model for calibration job"""

    va_data: Dict[str, Union[List[Dict], List[int]]] = Field(
        ...,
        description="Algorithm-specific VA data. Keys are algorithm names, values are death data"
    )
    age_group: AgeGroup = Field(
        ...,
        description="Age group: 'neonate' (0-27 days) or 'child' (1-59 months)"
    )
    country: Country = Field(
        ...,
        description="Country for country-specific calibration"
    )
    mmat_type: Literal["Mmatprior", "Mmatfixed"] = Field(
        default="Mmatprior",
        description="How to utilize misclassification estimates"
    )
    ensemble: bool = Field(
        default=True,
        description="Whether to perform ensemble calibration for multiple algorithms"
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "va_data": {
                        "insilicova": [
                            {"cause": "sepsis_meningitis_inf", "id": "death_001"},
                            {"cause": "pneumonia", "id": "death_002"}
                        ]
                    },
                    "age_group": "neonate",
                    "country": "Mozambique"
                }
            ]
        }
    }


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CalibrationResponse(BaseModel):
    """Response model for calibration job submission"""

    job_id: str
    status: JobStatus
    message: str
    created_at: datetime


class CalibrationResult(BaseModel):
    """Result model for completed calibration"""

    job_id: str
    status: JobStatus
    uncalibrated_csmf: Optional[Dict[str, float]] = None
    calibrated_csmf: Optional[Dict[str, Dict]] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    runtime_seconds: Optional[float] = None


async def run_r_calibration(job_id: str, request: CalibrationRequest):
    """Run R calibration in background"""
    import logging

    logger = logging.getLogger("uvicorn")
    logger.info(f"Starting calibration job {job_id}")

    start_time = datetime.now()
    job_store[job_id]["status"] = JobStatus.RUNNING

    try:
        # Create temporary directory for this job
        job_dir = f"/tmp/vacalib_job_{job_id}"
        os.makedirs(job_dir, exist_ok=True)
        logger.info(f"Created job directory: {job_dir}")

        # Write input data to temp file
        input_file = os.path.join(job_dir, "input.json")
        output_file = os.path.join(job_dir, "output.json")

        with open(input_file, 'w') as f:
            json.dump(request.model_dump(), f)
        logger.info(f"Wrote input file: {input_file}")

        # Copy R script to job directory
        r_script_src = os.path.join(os.path.dirname(__file__), "..", "r_scripts", "run_calibration.R")
        r_script_dst = os.path.join(job_dir, "run_calibration.R")

        if os.path.exists(r_script_src):
            shutil.copy(r_script_src, r_script_dst)
            logger.info(f"Copied R script from {r_script_src}")
        else:
            # Create inline if r_scripts doesn't exist
            with open(r_script_dst, 'w') as f:
                f.write(get_r_script_content())
            logger.info("Created inline R script")

        # Check if running inside Docker (check for docker.sock mount)
        in_docker_compose = os.path.exists('/var/run/docker.sock')
        logger.info(f"Running in Docker Compose: {in_docker_compose}")

        if in_docker_compose:
            # Running in docker-compose, use docker exec to run in R container
            cmd = [
                "docker", "exec",
                "-i",  # Interactive mode for stdin/stdout
                "vacalib-r",  # R container name from docker-compose
                "Rscript",
                f"/tmp/vacalib_job_{job_id}/run_calibration.R",
                f"/tmp/vacalib_job_{job_id}/input.json",
                f"/tmp/vacalib_job_{job_id}/output.json"
            ]

            # First, copy files to R container
            copy_cmd = [
                "docker", "cp",
                job_dir,
                f"vacalib-r:/tmp/"
            ]

            copy_process = await asyncio.create_subprocess_exec(
                *copy_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await copy_process.communicate()

        else:
            # Running locally or in standalone container
            # Try to use local R installation or docker run
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{job_dir}:/data",
                "vacalibration-r-engine",  # Use the built image
                "Rscript",
                "/data/run_calibration.R",
                "/data/input.json",
                "/data/output.json"
            ]

        # Execute calibration
        logger.info(f"Executing command: {' '.join(cmd)}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()
        logger.info(f"Command completed with return code: {process.returncode}")
        if stderr:
            logger.warning(f"Stderr output: {stderr.decode()}")

        # Read output file
        if in_docker_compose:
            # Copy result back from container
            copy_back_cmd = [
                "docker", "cp",
                f"vacalib-r:{output_file}",
                output_file
            ]
            copy_back_process = await asyncio.create_subprocess_exec(
                *copy_back_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await copy_back_process.communicate()

        # Check if output file exists and read it
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                result_data = json.load(f)
        else:
            # Fallback to stdout if output file doesn't exist
            if stdout:
                result_data = json.loads(stdout.decode())
            else:
                raise Exception(f"No output generated. Stderr: {stderr.decode()}")

        if not result_data.get("success", False):
            raise Exception(result_data.get("error", "Unknown error"))

        # Update job store
        end_time = datetime.now()
        job_store[job_id].update({
            "status": JobStatus.COMPLETED,
            "uncalibrated_csmf": result_data.get("uncalibrated"),
            "calibrated_csmf": result_data.get("calibrated"),
            "completed_at": end_time,
            "runtime_seconds": (end_time - start_time).total_seconds()
        })

        # Clean up
        shutil.rmtree(job_dir, ignore_errors=True)

    except Exception as e:
        import traceback
        # Get detailed error information
        error_details = f"Error: {str(e)}\nType: {type(e).__name__}\nTraceback: {traceback.format_exc()}"

        # Handle errors
        job_store[job_id].update({
            "status": JobStatus.FAILED,
            "error_message": error_details,
            "completed_at": datetime.now()
        })

        # Clean up on error
        if 'job_dir' in locals():
            shutil.rmtree(job_dir, ignore_errors=True)


def get_r_script_content():
    """Return R script content as fallback"""
    return '''#!/usr/bin/env Rscript
library(jsonlite)
library(vacalibration)

run_calibration <- function(input_file, output_file) {
  tryCatch({
    input_data <- fromJSON(input_file)

    va_data <- list()
    for (algo_name in names(input_data$va_data)) {
      va_data[[algo_name]] <- input_data$va_data[[algo_name]]
    }

    result <- vacalibration(
      va_data = va_data,
      age_group = input_data$age_group,
      country = input_data$country,
      Mmat_type = ifelse(is.null(input_data$mmat_type), "Mmatprior", input_data$mmat_type),
      ensemble = ifelse(is.null(input_data$ensemble), TRUE, input_data$ensemble),
      verbose = FALSE,
      plot_it = FALSE,
      nIter = 1000
    )

    output <- list(success = TRUE, uncalibrated = as.list(result$p_uncalib))

    if (!is.null(result$pcalib_postsumm)) {
      output$calibrated <- list()
      for (algo in dimnames(result$pcalib_postsumm)[[1]]) {
        output$calibrated[[algo]] <- list(
          mean = as.list(result$pcalib_postsumm[algo, "postmean", ]),
          lower_ci = as.list(result$pcalib_postsumm[algo, "lowcredI", ]),
          upper_ci = as.list(result$pcalib_postsumm[algo, "upcredI", ])
        )
      }
    }

    write(toJSON(output, auto_unbox = TRUE), output_file)
    return(0)
  }, error = function(e) {
    output <- list(success = FALSE, error = as.character(e$message))
    write(toJSON(output, auto_unbox = TRUE), output_file)
    return(1)
  })
}

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2) {
  cat("Usage: Rscript run_calibration.R <input_file> <output_file>\\n")
  quit(status = 1)
}
status <- run_calibration(args[1], args[2])
quit(status = status)
'''


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "VA-Calibration API",
        "version": "0.1.0"
    }


@app.post("/calibrate", response_model=CalibrationResponse)
async def submit_calibration(
    request: CalibrationRequest,
    background_tasks: BackgroundTasks
):
    """Submit a new calibration job"""

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Initialize job record
    job_store[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "created_at": datetime.now(),
        "request": request.model_dump()
    }

    # Start background task
    background_tasks.add_task(run_r_calibration, job_id, request)

    return CalibrationResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Calibration job submitted successfully",
        created_at=job_store[job_id]["created_at"]
    )


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a calibration job"""

    if job_id not in job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job = job_store[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "created_at": job["created_at"],
        "completed_at": job.get("completed_at"),
        "runtime_seconds": job.get("runtime_seconds")
    }


@app.get("/result/{job_id}", response_model=CalibrationResult)
async def get_calibration_result(job_id: str):
    """Get the results of a completed calibration job"""

    if job_id not in job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job = job_store[job_id]

    return CalibrationResult(
        job_id=job_id,
        status=job["status"],
        uncalibrated_csmf=job.get("uncalibrated_csmf"),
        calibrated_csmf=job.get("calibrated_csmf"),
        error_message=job.get("error_message"),
        completed_at=job.get("completed_at"),
        runtime_seconds=job.get("runtime_seconds")
    )


@app.get("/jobs")
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = 100
):
    """List all jobs, optionally filtered by status"""

    jobs = list(job_store.values())

    if status:
        jobs = [j for j in jobs if j["status"] == status]

    # Sort by creation time, newest first
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    # Apply limit
    jobs = jobs[:limit]

    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "created_at": j["created_at"],
                "completed_at": j.get("completed_at")
            }
            for j in jobs
        ]
    }


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job record"""

    if job_id not in job_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    del job_store[job_id]

    return {"message": f"Job {job_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)