#!/usr/bin/env Rscript

library(jsonlite)
library(vacalibration)

# Function to run calibration
run_calibration <- function(input_file, output_file) {
  tryCatch({
    # Read input JSON
    input_data <- fromJSON(input_file)

    # Define broad causes for each age group
    neonate_causes <- c("congenital_malformation", "pneumonia", "sepsis_meningitis_inf",
                        "ipre", "other", "prematurity")
    child_causes <- c("malaria", "pneumonia", "diarrhea", "severe_malnutrition",
                     "hiv", "injury", "other", "other_infections", "nn_causes")

    # Get the causes for this age group
    if (input_data$age_group == "neonate") {
      cause_names <- neonate_causes
    } else if (input_data$age_group == "child") {
      cause_names <- child_causes
    } else {
      stop(paste("Unknown age group:", input_data$age_group))
    }

    # Prepare VA data - convert from JSON structure to R format
    va_data <- list()
    for (algo_name in names(input_data$va_data)) {
      algo_data <- input_data$va_data[[algo_name]]

      # Handle different input formats
      if (is.matrix(algo_data) || is.data.frame(algo_data)) {
        # Already in matrix/dataframe format
        if (is.data.frame(algo_data)) {
          algo_data <- as.matrix(algo_data)
        }
        # Set column names if not present
        if (is.null(colnames(algo_data))) {
          colnames(algo_data) <- cause_names
        }
        va_data[[algo_name]] <- algo_data

      } else if (is.list(algo_data) && length(algo_data) > 0) {
        # Check if it's a list of objects with 'cause' field
        if (!is.null(algo_data[[1]]$cause)) {
          # Convert list of {cause: "name", id: x} to binary matrix
          n_deaths <- length(algo_data)
          death_matrix <- matrix(0, nrow = n_deaths, ncol = length(cause_names))
          colnames(death_matrix) <- cause_names
          rownames(death_matrix) <- sapply(algo_data, function(x) as.character(x$id))

          for (i in 1:n_deaths) {
            cause <- algo_data[[i]]$cause
            # Map cause to column index
            col_idx <- which(cause_names == cause)
            if (length(col_idx) > 0) {
              death_matrix[i, col_idx] <- 1
            } else {
              # Try to handle alternative cause names
              if (cause %in% c("sepsis", "meningitis", "infections")) {
                col_idx <- which(cause_names == "sepsis_meningitis_inf")
              } else if (cause == "intrapartum") {
                col_idx <- which(cause_names == "ipre")
              }

              if (length(col_idx) > 0) {
                death_matrix[i, col_idx] <- 1
              } else {
                # Default to "other" if cause not recognized
                col_idx <- which(cause_names == "other")
                death_matrix[i, col_idx] <- 1
              }
            }
          }
          va_data[[algo_name]] <- death_matrix

        } else if (is.numeric(unlist(algo_data))) {
          # It's a numeric vector or list - treat as death counts
          death_counts <- as.numeric(unlist(algo_data))
          if (length(death_counts) == length(cause_names)) {
            names(death_counts) <- cause_names
            va_data[[algo_name]] <- death_counts
          } else {
            stop(paste("Death count vector length", length(death_counts),
                      "doesn't match expected causes", length(cause_names)))
          }
        } else {
          # Try to convert to matrix directly
          va_data[[algo_name]] <- as.matrix(algo_data)
          if (ncol(va_data[[algo_name]]) == length(cause_names)) {
            colnames(va_data[[algo_name]]) <- cause_names
          }
        }
      } else if (length(algo_data) == 0) {
        # Empty data - use example data as fallback
        if (input_data$age_group == "neonate" && algo_name == "insilicova") {
          # Load example data
          data(comsamoz_public_broad, envir = environment())
          va_data[[algo_name]] <- comsamoz_public_broad$data[1:min(100, nrow(comsamoz_public_broad$data)),]
          warning("Using example data for empty input")
        } else {
          stop("Empty data provided and no example data available")
        }
      } else {
        va_data[[algo_name]] <- algo_data
      }
    }

    # Set default parameters if not provided
    # Map API Mmat_type values to R package values
    api_mmat_type <- input_data$mmat_type
    if (is.null(api_mmat_type)) {
      mmat_type <- "prior"
    } else if (api_mmat_type == "Mmatfixed") {
      mmat_type <- "fixed"
    } else if (api_mmat_type == "Mmatprior") {
      mmat_type <- "prior"
    } else {
      mmat_type <- api_mmat_type  # Pass through if already correct
    }

    ensemble <- ifelse(is.null(input_data$ensemble), TRUE, input_data$ensemble)
    verbose <- ifelse(is.null(input_data$verbose), FALSE, input_data$verbose)

    # Run calibration
    result <- vacalibration(
      va_data = va_data,
      age_group = input_data$age_group,
      country = input_data$country,
      Mmat_type = mmat_type,
      ensemble = ensemble,
      verbose = verbose,
      plot_it = FALSE
    )

    # Format output
    output <- list(
      success = TRUE,
      uncalibrated = if (is.null(names(result$p_uncalib))) {
        # If no names, create them based on the cause_names
        setNames(as.list(result$p_uncalib), cause_names)
      } else {
        as.list(result$p_uncalib)
      }
    )

    # Add calibrated results if available
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
      # Handle fixed Mmat case
      output$calibrated <- list()
      for (algo in names(result$p_calib)) {
        output$calibrated[[algo]] <- list(
          mean = as.list(result$p_calib[[algo]]),
          lower_ci = as.list(result$p_calib[[algo]]),  # Same as mean for fixed
          upper_ci = as.list(result$p_calib[[algo]])   # Same as mean for fixed
        )
      }
    }

    # Write output
    write(toJSON(output, auto_unbox = TRUE, na = "null"), output_file)

    return(0)

  }, error = function(e) {
    # Handle errors
    output <- list(
      success = FALSE,
      error = as.character(e$message)
    )
    write(toJSON(output, auto_unbox = TRUE), output_file)
    return(1)
  })
}

# Get command line arguments
args <- commandArgs(trailingOnly = TRUE)

if (length(args) != 2) {
  cat("Usage: Rscript run_calibration.R <input_file> <output_file>\n")
  quit(status = 1)
}

# Run the calibration
status <- run_calibration(args[1], args[2])
quit(status = status)