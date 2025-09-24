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

      # Check if data is empty or user wants to use example data
      use_example <- FALSE
      if (is.null(algo_data) ||
          (is.list(algo_data) && length(algo_data) == 0) ||
          (is.character(algo_data) && algo_data == "use_example")) {
        use_example <- TRUE
      }

      if (use_example) {
        # Use appropriate example data based on age group and algorithm
        if (input_data$age_group == "neonate") {
          # Load neonate example data
          if (algo_name == "insilicova") {
            # Use comsamoz_public_broad for broad cause example
            data(comsamoz_public_broad, envir = environment())
            va_data[[algo_name]] <- comsamoz_public_broad$data
            message(paste("Using example data (comsamoz_public_broad) for", algo_name))
          } else {
            # For other algorithms, use a subset of the same data
            data(comsamoz_public_broad, envir = environment())
            va_data[[algo_name]] <- comsamoz_public_broad$data
            message(paste("Using example neonate data for", algo_name))
          }
        } else if (input_data$age_group == "child") {
          # For child age group, create synthetic example data
          # Since we don't have child example data in the package
          n_deaths <- 100
          death_matrix <- matrix(0, nrow = n_deaths, ncol = length(child_causes))
          colnames(death_matrix) <- child_causes

          # Create random distribution of causes
          set.seed(123)  # For reproducibility
          for (i in 1:n_deaths) {
            cause_idx <- sample(1:length(child_causes), 1,
                              prob = c(0.15, 0.20, 0.15, 0.05, 0.05, 0.05, 0.10, 0.15, 0.10))
            death_matrix[i, cause_idx] <- 1
          }
          rownames(death_matrix) <- paste0("child_", 1:n_deaths)
          va_data[[algo_name]] <- death_matrix
          message(paste("Using synthetic example child data for", algo_name))
        }
      } else if (is.matrix(algo_data) || is.data.frame(algo_data)) {
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
        # Check if it's a list of objects with 'cause' field (individual-level specific causes)
        if (!is.null(algo_data[[1]]$cause)) {
          # Convert list of {cause: "name", id: x} to data frame for cause_map function
          # This handles individual-level specific (high-resolution) causes
          n_deaths <- length(algo_data)

          # Create data frame in the format expected by cause_map()
          df_causes <- data.frame(
            ID = sapply(algo_data, function(x) as.character(x$id)),
            cause = sapply(algo_data, function(x) as.character(x$cause)),
            stringsAsFactors = FALSE
          )

          # Use cause_map() function to convert specific causes to broad causes
          tryCatch({
            death_matrix <- cause_map(df = df_causes, age_group = input_data$age_group)
            # Ensure column names match expected causes
            if (!all(colnames(death_matrix) %in% cause_names)) {
              # Reorder/subset columns to match expected causes
              death_matrix_aligned <- matrix(0, nrow = nrow(death_matrix), ncol = length(cause_names))
              colnames(death_matrix_aligned) <- cause_names
              rownames(death_matrix_aligned) <- rownames(death_matrix)

              for (col in colnames(death_matrix)) {
                if (col %in% cause_names) {
                  death_matrix_aligned[, col] <- death_matrix[, col]
                }
              }
              death_matrix <- death_matrix_aligned
            }
          }, error = function(e) {
            # Fallback to manual mapping if cause_map fails
            warning(paste("cause_map failed:", e$message, "- using fallback mapping"))
            death_matrix <- matrix(0, nrow = n_deaths, ncol = length(cause_names))
            colnames(death_matrix) <- cause_names
            rownames(death_matrix) <- df_causes$ID

            for (i in 1:n_deaths) {
              cause <- df_causes$cause[i]
              # Map specific cause to broad cause
              broad_cause <- map_specific_to_broad(cause, input_data$age_group)
              col_idx <- which(cause_names == broad_cause)
              if (length(col_idx) > 0) {
                death_matrix[i, col_idx] <- 1
              } else {
                # Default to "other"
                death_matrix[i, which(cause_names == "other")] <- 1
              }
            }
          })
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
          # Try to convert to matrix directly (binary matrix format)
          va_data[[algo_name]] <- as.matrix(algo_data)
          if (ncol(va_data[[algo_name]]) == length(cause_names)) {
            colnames(va_data[[algo_name]]) <- cause_names
          }
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

# Helper function to map specific causes to broad causes
map_specific_to_broad <- function(specific_cause, age_group) {
  # Mapping for neonate causes
  neonate_mapping <- list(
    "Birth asphyxia" = "ipre",
    "Neonatal sepsis" = "sepsis_meningitis_inf",
    "Neonatal pneumonia" = "pneumonia",
    "Prematurity" = "prematurity",
    "Congenital malformation" = "congenital_malformation",
    "Other and unspecified neonatal CoD" = "other",
    "Accid fall" = "other",
    "Road traffic accident" = "other"
  )

  # Mapping for child causes
  child_mapping <- list(
    "Malaria" = "malaria",
    "Pneumonia" = "pneumonia",
    "Diarrhea" = "diarrhea",
    "Severe malnutrition" = "severe_malnutrition",
    "HIV" = "hiv",
    "Injury" = "injury",
    "Other infections" = "other_infections",
    "Neonatal causes" = "nn_causes"
  )

  if (age_group == "neonate") {
    mapping <- neonate_mapping
  } else {
    mapping <- child_mapping
  }

  # Try exact match first
  if (specific_cause %in% names(mapping)) {
    return(mapping[[specific_cause]])
  }

  # Try case-insensitive match
  for (key in names(mapping)) {
    if (tolower(key) == tolower(specific_cause)) {
      return(mapping[[key]])
    }
  }

  # Default to "other"
  return("other")
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