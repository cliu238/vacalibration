#!/usr/bin/env Rscript

# Simple example of VA-calibration package
library(vacalibration)

cat("========================================\n")
cat("VA-Calibration Example\n")
cat("========================================\n\n")

# Load example data
data(comsamoz_public_broad)

cat("Data loaded:\n")
cat("- Age group:", comsamoz_public_broad$age_group, "\n")
cat("- Algorithm:", comsamoz_public_broad$va_algo, "\n")
cat("- Deaths:", nrow(comsamoz_public_broad$data), "\n\n")

# Run calibration
cat("Running calibration...\n")
result <- vacalibration(
  va_data = setNames(
    list(comsamoz_public_broad$data),
    list(comsamoz_public_broad$va_algo)
  ),
  age_group = comsamoz_public_broad$age_group,
  country = "Mozambique",
  verbose = FALSE,
  plot_it = FALSE
)

# Show results
cat("\n========================================\n")
cat("RESULTS\n")
cat("========================================\n\n")

cat("Uncalibrated CSMF estimates:\n")
print(round(result$p_uncalib, 3))

cat("\nCalibrated CSMF estimates (posterior mean with 95% CrI):\n")
if (!is.null(result$pcalib_postsumm)) {
  # Extract just the posterior means
  postmean <- result$pcalib_postsumm["insilicova", "postmean", ]
  lowCI <- result$pcalib_postsumm["insilicova", "lowcredI", ]
  upCI <- result$pcalib_postsumm["insilicova", "upcredI", ]

  # Display results in a formatted table
  calib_table <- data.frame(
    cause = names(postmean),
    mean = round(postmean, 3),
    CI_lower = round(lowCI, 3),
    CI_upper = round(upCI, 3)
  )
  print(calib_table, row.names = FALSE)
} else {
  cat("(Calibrated results not available - may require longer MCMC run)\n")
}

cat("\n========================================\n")
cat("Example complete!\n")
cat("========================================\n")