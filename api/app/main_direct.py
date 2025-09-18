#!/usr/bin/env python3
"""
VA-Calibration API - Direct execution version
Runs calibration immediately without job storage
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union
from enum import Enum
import subprocess
import json
import tempfile
import os

app = FastAPI(
    title="VA-Calibration API (Direct)",
    version="0.1.0",
    description="Direct calibration API - runs immediately without job storage"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgeGroup(str, Enum):
    NEONATE = "neonate"
    CHILD = "child"


class CalibrationRequest(BaseModel):
    """Direct calibration request"""
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
    """Run calibration directly and return results"""

    # Check R is available
    r_ready, r_msg = check_r_setup()
    if not r_ready:
        raise HTTPException(status_code=500, detail=f"R not ready: {r_msg}")

    # Create temp directory
    with tempfile.TemporaryDirectory(prefix="vacalib_") as tmpdir:
        input_file = os.path.join(tmpdir, "input.json")
        output_file = os.path.join(tmpdir, "output.json")

        # Prepare request data
        request_data = request.model_dump()

        # If no va_data provided, use example
        if not request_data.get("va_data"):
            request_data["va_data"] = {"insilicova": "use_example"}

        # Write input
        with open(input_file, 'w') as f:
            json.dump(request_data, f)

        # Create inline R script
        r_script_file = os.path.join(tmpdir, "run.R")
        with open(r_script_file, 'w') as f:
            f.write(get_r_script())

        # Run R script
        cmd = ["Rscript", r_script_file, input_file, output_file]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        # Check for output
        if os.path.exists(output_file):
            with open(output_file, 'r') as f:
                output_data = json.load(f)

            if output_data.get("success"):
                return {
                    "status": "success",
                    "uncalibrated": output_data.get("uncalibrated", {}),
                    "calibrated": output_data.get("calibrated", {}),
                    "age_group": request.age_group,
                    "country": request.country
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=output_data.get("error", "Calibration failed")
                )
        else:
            # Try to parse stdout as JSON if no output file
            if result.stdout:
                try:
                    output_data = json.loads(result.stdout)
                    if output_data.get("success"):
                        return output_data
                except:
                    pass

            raise HTTPException(
                status_code=500,
                detail=f"R script failed: {result.stderr or result.stdout}"
            )


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