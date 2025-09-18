#!/usr/bin/env Rscript
# Script to demonstrate openVA output formats for API documentation

library(openVA)

# Load sample data from openVA package
data(RandomVA5)

# Show the structure of the input data
cat("\n=== Input Data Structure ===\n")
cat("Dimensions:", dim(RandomVA5), "\n")
cat("First 5 columns:\n")
print(head(RandomVA5[, 1:5], 3))

# Run InSilicoVA with minimal iterations for demonstration
cat("\n=== Running InSilicoVA ===\n")
fit_insilico <- codeVA(data = RandomVA5[1:100,],
                       data.type = "WHO2016",
                       model = "InSilicoVA",
                       Nsim = 100,
                       auto.length = FALSE,
                       warning.write = FALSE)

# Extract individual cause assignments
cat("\n=== InSilicoVA Individual Outputs ===\n")
indiv_prob <- getIndivProb(fit_insilico)
cat("Individual probability matrix dimensions:", dim(indiv_prob), "\n")
cat("First 3 individuals, top 5 causes:\n")
print(head(indiv_prob[1:3, 1:5], 3))

# Get top causes for each individual
cat("\n=== Top Cause Assignments ===\n")
top_causes <- getTopCOD(fit_insilico)
cat("Structure of top causes output:\n")
print(head(top_causes, 5))

# Get CSMF (Cause-Specific Mortality Fractions)
cat("\n=== CSMF Summary ===\n")
csmf <- getCSMF(fit_insilico)
cat("Top 10 causes by CSMF:\n")
print(head(sort(csmf, decreasing = TRUE), 10))

# Convert to the format needed by vacalibration (ID + cause)
cat("\n=== Converting for vacalibration API ===\n")
# Method 1: Using most probable cause
ids <- rownames(top_causes)
causes <- top_causes$cause1
va_api_format <- data.frame(
  ID = ids,
  cause = causes,
  stringsAsFactors = FALSE
)
cat("Format for API (ID + cause):\n")
print(head(va_api_format, 10))

# Save as JSON format
cat("\n=== JSON Format for API ===\n")
library(jsonlite)
json_output <- toJSON(va_api_format[1:5,], pretty = TRUE)
cat(json_output, "\n")

# Run InterVA5 for comparison
cat("\n=== Running InterVA5 ===\n")
fit_interva <- codeVA(data = RandomVA5[1:100,],
                      data.type = "WHO2016",
                      model = "InterVA",
                      version = "5",
                      HIV = "l",
                      Malaria = "h",
                      write = FALSE)

# Extract InterVA results
interva_cod <- getTopCOD(fit_interva)
cat("\nInterVA5 top causes:\n")
print(head(interva_cod, 5))

# Show how to prepare multiple algorithms for ensemble calibration
cat("\n=== Ensemble Format for Multiple Algorithms ===\n")
ensemble_data <- list(
  insilicova = va_api_format[, c("ID", "cause")],
  interva = data.frame(
    ID = rownames(interva_cod),
    cause = interva_cod$cause1,
    stringsAsFactors = FALSE
  )
)
cat("Structure for ensemble calibration:\n")
str(ensemble_data)