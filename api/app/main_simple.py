from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from enum import Enum
import uuid
from datetime import datetime

app = FastAPI(
    title="VA-Calibration API",
    version="0.1.0",
    description="Web API for calibrating computer-coded verbal autopsy algorithms"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store jobs in memory for demo
job_store: Dict[str, Dict] = {}


class VAAlgorithm(str, Enum):
    EAVA = "eava"
    INSILICOVA = "insilicova"
    INTERVA = "interva"


class AgeGroup(str, Enum):
    NEONATE = "neonate"
    CHILD = "child"


class CalibrationRequest(BaseModel):
    va_data: Dict[str, List[Dict]] = Field(
        ...,
        description="Algorithm-specific VA data"
    )
    age_group: AgeGroup
    country: str = "Mozambique"

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "va_data": {
                    "insilicova": [
                        {"cause": "sepsis_meningitis_inf", "id": "death_001"},
                        {"cause": "pneumonia", "id": "death_002"}
                    ]
                },
                "age_group": "neonate",
                "country": "Mozambique"
            }]
        }
    }


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "VA-Calibration API",
        "version": "0.1.0"
    }


@app.post("/calibrate")
async def submit_calibration(request: CalibrationRequest):
    """Submit calibration job"""

    job_id = str(uuid.uuid4())

    # Store job
    job_store[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "request": request.model_dump()
    }

    # Mock response for now
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Calibration job submitted",
        "created_at": job_store[job_id]["created_at"]
    }


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""

    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_store[job_id]

    # Mock completed status with example results
    return {
        "job_id": job_id,
        "status": "completed",
        "created_at": job["created_at"],
        "results": {
            "uncalibrated_csmf": {
                "sepsis_meningitis_inf": 0.305,
                "prematurity": 0.243,
                "pneumonia": 0.124,
                "other": 0.328
            },
            "calibrated_csmf": {
                "sepsis_meningitis_inf": {
                    "mean": 0.559,
                    "ci_lower": 0.398,
                    "ci_upper": 0.770
                },
                "prematurity": {
                    "mean": 0.080,
                    "ci_lower": 0.004,
                    "ci_upper": 0.182
                },
                "pneumonia": {
                    "mean": 0.105,
                    "ci_lower": 0.005,
                    "ci_upper": 0.279
                },
                "other": {
                    "mean": 0.256,
                    "ci_lower": 0.150,
                    "ci_upper": 0.380
                }
            }
        }
    }


@app.get("/jobs")
async def list_jobs():
    """List all jobs"""

    return {
        "total": len(job_store),
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j.get("status", "pending"),
                "created_at": j["created_at"]
            }
            for j in job_store.values()
        ]
    }