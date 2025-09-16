# zzz.R - Initialization code for vacalibration package

# Declare global variables to avoid R CMD check NOTES
# These variables are used in non-standard evaluation (e.g., data.table, dplyr, etc.)

if (getRversion() >= "2.15.1") {
  utils::globalVariables(c(
    "cause",
    "Var2",
    "Var3",
    "value",
    "calib_type",
    "llim",
    "ulim",
    "Mmat_champs",
    "stanfitq_k",
    "va_data_tomodel",
    "calibrated_ens",
    "title_Mmat_tomodel",
    "subtitle_Mmat_tomodel",
    "age_group"
  ))
}

.onLoad <- function(libname, pkgname) {
  rstan::rstan_options(auto_write = TRUE)
  options(mc.cores = parallel::detectCores())
}
