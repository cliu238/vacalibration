#!/usr/bin/env Rscript

# Export data from vacalibration package to .rda files
library(vacalibration)

# Create data directory if it doesn't exist
if (!dir.exists("data")) {
  dir.create("data")
}

# Load and save each dataset
data(comsamoz_public_broad)
save(comsamoz_public_broad, file = "data/comsamoz_public_broad.rda")
cat("Exported comsamoz_public_broad.rda\n")

data(comsamoz_public_openVAout)
save(comsamoz_public_openVAout, file = "data/comsamoz_public_openVAout.rda")
cat("Exported comsamoz_public_openVAout.rda\n")

data(Mmat_champs)
save(Mmat_champs, file = "data/Mmat_champs.rda")
cat("Exported Mmat_champs.rda\n")

cat("All data files exported successfully!\n")