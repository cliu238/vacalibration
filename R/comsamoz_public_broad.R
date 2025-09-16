#' COMSA-Mozambique: Example Individual-Level Broad Cause of Death Data (Publicly Available Version)
#'
#' Example individual‑level neonatal cause‑of‑death data using InSilicoVA. This is obtained after broad cause mapping of \code{comsamoz_public_openVAout$data} using \code{cause_map()} function in this package.
#'
#' This shows how individual level broad cause of death data can be an input in the \code{vacalibration()} function for calibration.
#'
#' @format A list of 4 components.
#' \describe{
#'   \item{data}{Binary matrix. Contains the data. Rows are individuals. Columns are broad causes. Matrix elements are 0 or 1, with 1 indicating the cause of death for an individual.}
#'   \item{age_group}{Character. Indicate age group. "neonate" (for 0-27 days) for this data}
#'   \item{va_algo}{Character. Indicate CCVA algorithm. "insilicova" for this data}
#'   \item{version}{Character. Date stamp for version control of tracking updates. Only for package maintainers.}
#' }
#'
#' @details
#' \code{comsamoz_public_broad$data[i,j]} is a binary indicator of whether broad cause \code{j} is the cause of death for individual \code{i}.
#' 1 indicates it is, and 0 indicates it is not.
#'
#' Broad causes for "neonate" are
#' \itemize{
#'   \item "congenital_malformation",
#'   \item "pneumonia",
#'   \item "sepsis_meningitis_inf" (sepsis/meningitis/infections),
#'   \item "ipre" (intrapartum-related events),
#'   \item "other", and
#'   \item "prematurity".
#' }
#'
#' For "child", the broad causes are
#' \itemize{
#'   \item "malaria",
#'   \item "pneumonia",
#'   \item "diarrhea",
#'   \item "severe_malnutrition",
#'   \item "hiv",
#'   \item "injury",
#'   \item "other",
#'   \item "other_infections", and
#'   \item "nn_causes" (neonatal causes; consists of IPRE, congenital malformation, and prematurity).
#' }
#'
#' @references
#' Macicame, I, et al. (2023). *Countrywide Mortality Surveillance for Action in Mozambique: Results from a National Sample-Based Vital Statistics System for Mortality and Cause of Death*.
#' American Journal of Tropical Medicine and Hygiene, 108(Suppl 5), pp. 5–16.
#'
#' @examples
#'
#' \donttest{
#'
#' ## using the data
#' data(comsamoz_public_broad)
#' head(comsamoz_public_broad$data)  # head of the data
#' comsamoz_public_broad$data[1,]  # binary vector indicating cause of death for individual 1
#'
#' ## mapped to national death counts
#' comsamoz_public_asdeathcount = colSums(comsamoz_public_broad$data)
#'
#' ## VA-calibration for the "neonate" age group and InSilicoVA algorithm
#' ## input as broad cause
#' calib_out_asbroad = vacalibration(va_data = setNames(list(comsamoz_public_broad$data),
#'                                                      list(comsamoz_public_broad$va_algo)),
#'                                      age_group = comsamoz_public_broad$age_group,
#'                                      country = "Mozambique")
#'
#' ## input as specific cause
#' calib_out_asdeathcount = vacalibration(va_data = setNames(list(comsamoz_public_asdeathcount),
#'                                                           list(comsamoz_public_broad$va_algo)),
#'                                        age_group = comsamoz_public_broad$age_group,
#'                                        country = "Mozambique")
#'
#' ## comparing uncalibrated CSMF estimates and posterior summary of calibrated CSMF estimates
#' ## all are the same
#' calib_out_asbroad$p_uncalib
#' calib_out_asbroad$pcalib_postsumm[1,,]
#'
#' calib_out_asdeathcount$p_uncalib
#' calib_out_asdeathcount$pcalib_postsumm[1,,]
#'
#' }
#'
"comsamoz_public_broad"
