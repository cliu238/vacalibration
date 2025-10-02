#!/usr/bin/env python3
"""
Shared R Script Generation Module
Provides unified R script generation for calibration tasks.
This is the ORIGINAL WORKING version from the Celery migration.
"""

def generate_calibration_r_script() -> str:
    """
    Generate R script for VA calibration (original working version).

    Returns:
        str: Complete R script for calibration execution
    """
    return '''
library(jsonlite)
library(vacalibration)

args <- commandArgs(trailingOnly = TRUE)
input_file <- args[1]
output_file <- args[2]

# Print to stderr so it's captured immediately
cat("=== VA Calibration Starting ===\n", file=stderr())
flush(stderr())

tryCatch({
    # Read input
    cat("Reading input file...\n", file=stderr())
    flush(stderr())
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
    cat("Running vacalibration with verbose=TRUE...\n", file=stderr())
    flush(stderr())
    result <- vacalibration(
        va_data = va_data,
        age_group = input_data$age_group,
        country = input_data$country,
        Mmat_type = input_data$mmat_type,
        ensemble = input_data$ensemble,
        verbose = TRUE,
        plot_it = FALSE
    )
    cat("Calibration completed successfully!\n", file=stderr())
    flush(stderr())

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


def get_calibration_r_script() -> str:
    """
    Backward compatibility wrapper.

    Returns:
        str: Complete R script for calibration execution
    """
    return generate_calibration_r_script()