#' VA-calibration function
#'
#' @param va_data A named list. Algorithm-specific unlabeled VA-only data.
#'
#' For example, \code{list("algo1" = algo1_output, "algo2" = algo2_output, ...)}.
#'
#' Algorithm names (\code{"algo1"}, \code{"algo2"}, ...) can be "eava", "insilicova", or "interva".
#'
#' Data (\code{algo1_output}, \code{algo2_output}, ...) can be specific causes (output from \code{codEAVA()} function in \code{EAVA} and \code{crossVA()} function in \code{openVA}), or broad causes (output from the \code{cause_map()} function in this package), or broad-cause-specific death counts (integer vector).
#'
#' Can be different for different algorithms.
#'
#' Total number of deaths for different algorithms can be different.
#'
#'
#' @param age_group Character. Age-group of interest.
#'
#' \code{"neonate"} or \code{"child"}.
#'
#' \code{"neonate"} ages between 0-27 days, or \code{"child"} ages between 1-59 months.
#'
#'
#' @param country Character. The country \code{va_data} is from.
#'
#' Country-specific calibration is possible for "Bangladesh", "Ethiopia", "Kenya", "Mali", "Mozambique", "Sierra Leone", "South Africa".
#'
#' Any other country is matched with "other".
#'
#'
#' @param Mmat A named list. Similarly structured as \code{va_data}.
#'
#' Needed only if \code{calibmodel.type = "Mmatprior"} (propagates uncertainty).
#'
#' For example, \code{list("algo1" = Mmat.asDirich_algo1, "algo2" = Mmat.asDirich_algo2, ...)}.
#'
#' List of algorithm-specific Dirichlet prior on misclassification matrix to be used for calibration.
#'
#' Names and length must be identical to \code{va_data}.
#'
#' If algorithm names (\code{"algo1"}, \code{"algo2"}, ...) are \code{"eava"}, \code{"insilicova"} or \code{"interva"}, and \code{Mmat.asDirich} is missing, it by default uses the CHAMPS-based estimates (Dirichlet approximation of posterior) stored in \code{Mmat_champs} in this package.
#'
#' See \code{Mmat_champs} for details.
#'
#' If \code{Mmat.asDirich} is not missing, whatever provided is used.
#'
#' If any algorithm name (\code{"algo1"}, \code{"algo2"}, ...) is different from \code{"eava"}, \code{"insilicova"} or \code{"interva"}, \code{Mmat.asDirich} must be provided.
#'
#' \code{Mmat.asDirich_algo1} is a matrix of dimension CHAMPS ("gold standard") cause X VA cause.
#'
#' \code{Dirichlet(Mmat.asDirich_algo1[i,])} is used as informative prior on classification rates for CHAMPS cause \code{i}.
#'
#'
#' @param Mmat_type Character. How to utilize misclassification estimates.
#'
#' \code{"Mmatprior"} (default). Propagates uncertainty in the misclassification matrix estimates.
#'
#' \code{"Mmatfixed"}. Uses fixed (default: posterior mean) misclassification matrix estimates.
#'
#'
#' @param studycause_map Character vector. A character vector specifying the mapping of study-specific causes to CHAMPS causes.
#'
#' This argument is required when study causes differ from, and are not a subset of, CHAMPS causes.
#'
#' The input should be provided in the format: \code{c("study_cause1" = "pneumonia", "study_cause2" = "ipre", "study_cause3" = "other", "study_cause4" = "other")}.
#'
#'
#' @param donotcalib A named list. Similarly structured as \code{va_data}, \code{Mmat.asDirich}, or \code{Mmat.fixed}.
#'
#' List of broad causes for each CCVA algorithm that we do not want to calibrate
#'
#' Default: \code{list("eava"="other", "insilicova"="other", "interva"="other")}. That is, \code{"other"} cause is not calibrated.
#'
#' For neonates, the broad causes are \code{"congenital_malformation"}, \code{"pneumonia"}, \code{"sepsis_meningitis_inf"}, \code{"ipre"}, \code{"other"}, or \code{"prematurity"}.
#'
#' For children, the broad causes are \code{"malaria"}, \code{"pneumonia"}, \code{"diarrhea"}, \code{"severe_malnutrition"}, \code{"hiv"}, \code{"injury"}, \code{"other"}, \code{"other_infections"}, \code{"nn_causes"} (neonatal causes).
#'
#' Set \code{list("eava" = NULL, "insilicova" = NULL, "interva" = NULL)} if you want to calibrate all causes.
#'
#'
#' @param donotcalib_type Character. \code{"fixed"} or \code{"learn"} (default).
#'
#' For \code{"fixed"}, only broad causes that are provided in \code{"donotcalib"} are not calibrated.
#'
#' For \code{"learn"}, it learns from \code{"Mmat.fixed"} or \code{"Mmat.asDirich"} if any other causes cannot be calibrated.
#'
#' For \code{"learn"}, it identifies VA causes for which the misclassification rates do not vary across CHAMPS causes.
#'
#' In that case, the calibration equation becomes ill-conditioned (see the footnote below Section 3.8 in Pramanik et al. (2025)). Currently, we address this by not calibrating VA causes for which the misclassification rates are similar along the rows (CHAMPS causes). VA causes (Columns) for which the rates along the rows (CHAMPS causes) do not vary more that \code{"nocalib.threshold"} are not calibrated. \code{"donotcalib"} is accordingly updated for each CCVA algorithm.
#'
#'
#' @param nocalib.threshold Numeric between 0 and 1. The value used for screening VA causes that cannot be calibrated when \code{donotcalib_type = "learn"}. Default: 0.1.
#'
#'
#' @param path_correction Logical. \code{TRUE} (default) or \code{FALSE}. Setting \code{TRUE} improves stability in calibration.
#'
#'
#' @param ensemble Logical. \code{TRUE} (default) or \code{FALSE}.
#'
#' Whether to perform ensemble calibration when outputs from multiple algorithms are provided.
#'
#'
#' @param shrink_strength Positive numeric. Degree of shrinkage of calibrated cause-specific mortality fraction (CSMF) estimate towards uncalibrated estimates.
#'
#' Always 0 when \code{path_correction=TRUE}. Defaults to 4 when \code{path_correction=FALSE}.
#'
#'
#' @param lambda_eBayes Numeric between 0 and 1. The value used for screening VA causes that cannot be calibrated when \code{donotcalib_type = "learn"}. Default: 0.1.
#'
#'
#' @param nMCMC Positive integer. Total number of posterior samples to perform inference on.
#'
#' Total number of iterations are \code{nBurn + nMCMC*nThin}.
#'
#' Default 5000.
#'
#' @param nBurn Positive integer. Total burn-in in posterior sampling.
#'
#' Total number of iterations are \code{nBurn + nMCMC*nThin}.
#'
#' Default 5000.
#'
#' @param nThin Positive integer. Number of thinning in posterior sampling.
#'
#' Total number of iterations are \code{nBurn + nMCMC*nThin}.
#'
#' Default 1.
#'
#' @param nChain Positive integer. Number of chains for STAN sampling.
#'
#' Default 1.
#'
#' @param nCore Positive integer. Number of cores to run multiple chains in parallel for STAN sampling.
#'
#' Default 1.
#'
#'
#' @param adapt_delta_stan Positive numeric between 0 and 1. \code{"adapt_delta"} parameter in \code{rstan}.
#'
#' Influences the behavior of the No-U-Turn Sampler (NUTS), the primary MCMC sampling algorithm in Stan.
#'
#' Default 0.9.
#'
#'
#' @param refresh.stan Positive integer. Report progress at every \code{refresh.stan}-th iteration.
#'
#' Default \code{(nBurn + nMCMC*nThin)/10}, that is at every 10% progress.
#'
#'
#' @param seed Numeric. \code{"seed"} parameter in rstan.
#'
#' Default 1.
#'
#'
#' @param verbose Logical. Reports progress or not.
#'
#' \code{TRUE} (default) or \code{FALSE}.
#'
#'
#' @param saveoutput Logical. Save output or not.
#'
#' \code{TRUE} (default) or \code{FALSE}.
#'
#'
#' @param output_filename Character. Output name to save as.
#'
#' Default \code{paste0("calibratedva_", calibmodel.type)}. That is \code{"calibratedva_Mmatprior"} or \code{"calibratedva_Mmatfixed"}.
#'
#'
#' @param output_dir Output directory or file path to save at.
#'
#'
#' @param plot_it Logical. Whether to return comparison plot for summary.
#'
#' \code{TRUE} (default) or \code{FALSE}.
#'
#' @return A named list:
#'  \describe{
#'      \item{input}{A named list of input data}
#'      \item{p_uncalib}{Uncalibrated cause-specific mortality fractions (CSMF) estimates as observed in the data}
#'      \item{p_calib}{Posterior samples of calibrated CSMF estimates}
#'      \item{pcalib_postsumm}{Posterior summaries (mean and 95% credible interval) of calibrated CSMF estimates}
#'      \item{va_deaths_uncalib}{Uncalibrated cause-specific death counts as observed in the data}
#'      \item{va_deaths_calib_algo}{Algorithm-specific calibrated cause-specific death counts}
#'      \item{va_deaths_calib_ensemble}{Ensemble calibrated cause-specific death counts}
#'      \item{donotcalib}{A logical indicator of causes that are not calibrated for each algorithm}
#'      \item{causes_notcalibrated}{Causes that are not calibrated for each algorithm}
#'  }
#'
#' @examples
#'
#' \donttest{
#'
#' ######### VA input as specific causes #########
#' # output from codEAVA() function in the EAVA package and crossVA() function in openVA package
#'
#' # COMSA-Mozambique: Example (Publicly Available Version)
#' # Individual-Level Specific (High-Resolution) Cause of Death Data
#' data(comsamoz_public_openVAout)
#' head(comsamoz_public_openVAout$data)  # head of the data
#' comsamoz_public_openVAout$data[1,]  # ID and specific cause of death for individual 1
#'
#' # VA-calibration for the "neonate" age group and InSilicoVA algorithm
#' calib_out_specific = vacalibration(va_data = setNames(list(comsamoz_public_openVAout$data),
#'                                                      list(comsamoz_public_openVAout$va_algo)),
#'                                    age_group = comsamoz_public_openVAout$age_group,
#'                                    country = "Mozambique")
#'
#' ### comparing uncalibrated CSMF estimates and posterior summary of calibrated CSMF estimates
#' calib_out_specific$p_uncalib # uncalibrated
#' calib_out_specific$pcalib_postsumm["insilicova",,]
#'
#' ######### VA input as broad causes (output from cause_map()) #########
#'
#' # COMSA-Mozambique: Example (Publicly Available Version)
#' # Individual-Level Broad Cause of Death Data
#' data(comsamoz_public_broad)
#' head(comsamoz_public_broad$data)
#' comsamoz_public_broad$data[1,]  # binary vector indicating cause of death for individual 1
#'
#' # VA-calibration for the "neonate" age group and InSilicoVA algorithm
#' calib_out_broad = vacalibration(va_data = setNames(list(comsamoz_public_broad$data),
#'                                                    list(comsamoz_public_broad$va_algo)),
#'                                 age_group = comsamoz_public_broad$age_group,
#'                                 country = "Mozambique")
#'
#' ### comparing uncalibrated CSMF estimates and posterior summary of calibrated CSMF estimates
#' calib_out_broad$p_uncalib # uncalibrated
#' calib_out_broad$pcalib_postsumm["insilicova",,]
#'
#' ######### VA input as national death counts for different broad causes #########
#' calib_out_asdeathcount = vacalibration(va_data = setNames(list(colSums(comsamoz_public_broad$data)),
#'                                                     list(comsamoz_public_broad$va_algo)),
#'                                        age_group = comsamoz_public_broad$age_group,
#'                                        country = "Mozambique")
#'
#' ### comparing uncalibrated CSMF estimates and posterior summary of calibrated CSMF estimates
#' calib_out_asdeathcount$p_uncalib # uncalibrated
#' calib_out_asdeathcount$pcalib_postsumm["insilicova",,]
#'
#'
#' ######### Example of data based on EAVA and InSilicoVA for neonates in Mozambique #########
#' ## example VA national death count data from EAVA and InSilicoVA
#' va_data_example = list("eava" = c("congenital_malformation" = 40, "pneumonia" = 175,
#'                                   "sepsis_meningitis_inf" = 265, "ipre" = 220,
#'                                   "other" = 30, "prematurity" = 170),
#'                        "insilicova" = c("congenital_malformation" = 5, "pneumonia" = 145,
#'                                         "sepsis_meningitis_inf" = 370, "ipre" = 330,
#'                                         "other" = 60, "prematurity" = 290))
#'
#' ## algorithm-specific and ensemble calibration of EAVA and InSilicoVA
#' calib_out_ensemble = vacalibration(va_data = va_data_example,
#'                                    age_group = "neonate",
#'                                    country = "Mozambique")
#'
#' ### comparing uncalibrated CSMF estimates and posterior summary of calibrated CSMF estimates
#' calib_out_ensemble$p_uncalib # uncalibrated
#' calib_out_ensemble$pcalib_postsumm["eava",,] # EAVA-specific calibration
#' calib_out_ensemble$pcalib_postsumm["insilicova",,] # InSilicoVA-specific calibration
#' calib_out_ensemble$pcalib_postsumm["ensemble",,] # Ensemble calibration
#'
#' }
#'
#' @importFrom stats nlminb
#' @importFrom LaplacesDemon ddirichlet
#'
#' @export
vacalibration <- function(va_data = NULL, age_group = NULL, country = NULL,
                          Mmat = NULL, Mmat_type = c("prior", "fixed", "samples")[1],
                          studycause_map = NULL,
                          donotcalib = NULL,
                          donotcalib_type = c("learn", "fixed")[1], nocalib.threshold = 0.1,
                          path_correction = TRUE, ensemble = NULL,
                          # shrink_towards = c("calib", "uncalib")[2],
                          shrink_strength = NULL, lambda_eBayes = 0,
                          nMCMC = 5000, nBurn = 5000, nThin = 1,
                          nChain = 1, nCore = 1,
                          adapt_delta_stan = .9, refresh.stan = NULL,
                          seed = 1, verbose = TRUE, saveoutput = FALSE,
                          output_filename = NULL, output_dir = NULL,
                          plot_it = TRUE){


  input.list = as.list(environment())

  # default
  # how frequently print stan sampling status
  if(is.null(refresh.stan)){

    if(verbose){

      refresh.stan = max((nBurn + nMCMC*nThin)/10, 1)

    }else{

      refresh.stan = 0

    }

  }

  # default shrinkage towards uncalibrated csmf estimate
  if(path_correction){

    shrink_strength = 0

  }else{

    if(is.null(shrink_strength)) shrink_strength = 4

  }


  # va_data preparation for input into modular_vacalib() ----
  # rewriting as a list of broad-cause-specific death count vector
  if(is.null(va_data)){

    message("Need 'va_data' input.")
    message("")
    message("Provide VA-only (or unlabeled) data in 'va_data' to calibrate.")
    message("For example, 'va_data'=list('eava'=eava_output, 'insilicova'=insilicova_output, 'interva'=interva_output).")
    message("")
    message("For VA calibration, supply a list of outputs from CCVA algorithms:")
    message("     1. For EAVA, provide output from the codEAVA() function in EAVA package.")
    message("     2. For InSilicoVA and InteVA, provide outputs from the openVA package.")
    stop("")

  }else if(!is.list(va_data)){

    message("'va_data' must be a list.")
    message("For example, 'va_data'=list('eava'=eava_output, 'insilicova'=insilicova_output, 'interva'=interva_output).")
    message("")
    message("For VA-calibration:")
    message("     1. For EAVA, provide output from the codEAVA() function in EAVA package.")
    message("     2. For InSilicoVA and InteVA, provide outputs from the openVA package.")
    stop("")

  }else if(is.null(names(va_data))){

    message("'va_data' must be a named list. Component names indicate CCVA algorithms.")
    message("For example, 'va_data'=list('eava'=eava_output, 'insilicova'=insilicova_output, 'interva'=interva_output).")
    stop("")

  }else{

    if(verbose){

      message("Preparing 'va_data' for calibration ...")

    }

    va_data_tomodel = va_data
    # print(length(va_data))
    # pb = txtProgressBar(min = 1, max = length(va_data), style = 3)
    for(k in 1:length(va_data)){

      if(length(dim(va_data[[k]]))==2){

        if((ncol(va_data[[k]])==2)&&(isTRUE(all.equal(sort(colnames(va_data[[k]])), sort(c("ID", "cause")))))){

          # outputs from EAVA and OpenVA

          ## hard check: whether has columns names like cause_map() outputs
          if(is.null(colnames(va_data[[k]]))){

            message(paste0("'va_data' for ", names(va_data)[k], " algorithm matches output from EAVA or OpenVA."))
            message("Must have 'ID' and 'cause' as column names.")
            stop("")
          }

          # broad-cause specific death count vector
          va_data_tomodel[[k]] = colSums(cause_map(df = va_data[[k]], age_group = age_group))

        }else{

          # outputs from cause_map()

          ## hard checks
          ### whether has column names
          if(is.null(colnames(va_data[[k]]))){

            message(paste0("'va_data' for ", names(va_data)[k], " algorithm matches broad cause mapping."))
            message("Must have broad causes as column names.")
            stop("")
          }

          # ### whether has rownames
          # if(is.null(rownames(va_data[[k]]))){
          #
          #   message("")
          #   message(paste0("Note: Rows of 'va_data' for ", names(va_data)[k], " algorithm doesn't have names."))
          #   message("Assuming they correspond to separate individuals.")
          #   message("")
          #
          # }

          ### whether single-cause
          singlecause.check = apply(X = va_data[[k]], 1,
                                    FUN = function(v){

                                      isFALSE(all.equal(sum(v), 1))|(sum(v!=0)>1)

                                    })

          if(sum(singlecause.check)>=2){

            message(va_data[[k]][singlecause.check,])
            message(paste0("'va_data' for ", names(va_data)[k], " algorithm for these rows does not look like single-cause predictions."))
            stop("")

          }

          # broad-cause specific death count vector
          va_data_tomodel[[k]] = colSums(va_data[[k]])

        }

      }else if(length(dim(va_data[[k]]))==0){

        # broad-cause-specific death counts

        ## hard checks: whether is a count vector
        count.check = sum(va_data[[k]])==sum(floor(va_data[[k]]))
        if(!count.check) {

          message(paste0("'va_data' for ", names(va_data)[k], " algorithm must be a vector of death counts for each broad cause."))
          stop("")

        }


        # broad-cause specific death count vector
        va_data_tomodel[[k]] = va_data[[k]]

      }else{

        message(paste0("Unknown format of 'va_data' for ", names(va_data)[k], " algorithm."))
        message("")
        message("Valid input formats for 'va_data' by algorithm:")
        message("     1. For EAVA: Output of codEAVA() in the EAVA package.")
        message("        For InSilicoVA and InterVA: Output of crossVA() in the openVA package.")
        message("        Matrix structured as individuals X 2")
        message("")
        message("     2. Output of cause_map() function in this package.")
        message("        They are broad cause mapping of outputs from codEAVA(), or crossVA().")
        message("        Matrix structured as individual X broad causes")
        message("")
        message("     3. Vector of broad-cause-specific death counts (column sums of output from cause_map()).")
        stop("")

      }

      if(k>1){

        if(isTRUE(all.equal(sort(names(va_data_tomodel[[1]])), sort(names(va_data_tomodel[[k]]))))){

          va_data_tomodel[[k]] = va_data_tomodel[[k]][names(va_data_tomodel[[1]])]

        }else{

          message("Causes specified in 'va_data':")
          message(paste0("For algorithm ", names(va_data_tomodel)[1], ": ", paste0(names(va_data_tomodel[[1]]), collapse = ', ')))
          message(paste0("For algorithm ", names(va_data_tomodel)[k], ": ", paste0(names(va_data_tomodel[[k]]), collapse = ', ')))
          message("Causes in 'va_data' for algorithms ", names(va_data_tomodel)[1]," and ", names(va_data_tomodel)[k]," do not match.")
          stop("")

        }

      }

      # if(verbose){setTxtProgressBar(pb, k)}

    } # end of k loop to prepare va data

    if(verbose){

      message("Preparing 'va_data' for calibration ... Done.")
      message("")

    }

  }


  # misclassification matrix for calibration ----
  # Mmat.asDirich_study = Mmat.fixed_tomodel = NULL
  if(!(Mmat_type %in% c("fixed", "prior", "samples"))){

    message("Below are valid options for 'Mmat_type':")
    message("     1. 'fixed': Fixed misclassification matrix.")
    message("                 Has nonnegative entries, and each row sums to 1.")
    message("")
    message("     2. 'prior': Prior on the misclassification matrix.")
    message("                 A matrix specifying the Dirichlet prior row by row.")
    message("                 Each row specifies the scale parameters for that row of the misclassification matrix.")
    message("")
    message("     3. 'samples': Misclassification matrix samples.")
    message("                   A 3-dimensional array.")
    message("                   Dimensions respectively represent:")
    message("                       (1) samples,")
    message("                       (2) row of misclassification matrix, and")
    message("                       (3) column of misclassification matrix.")
    stop("")

  }else if(Mmat_type=="fixed"){

    ## fixed misclassification matrix ----

    if(is.null(Mmat)){

      ### default: CHAMPS ----

      utils::data("Mmat_champs", package = "vacalibration", envir = environment())

      if(is.null(age_group)){

        message("Since 'Mmat' is not provided, provide the age group.")
        message("Must be 'neonate' (for 0-27 days) or 'child' (for 1-59 months).")
        message("Otherwise specify your own misclassification matrix with algorithm names in 'Mmat'.")
        message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
        stop("")

      }

      if(is.null(country)){

        message("Since 'Mmat' is not provided, specify the country of for the 'va_data'")
        message("Must be 'Bangladesh', 'Ethiopia', 'Kenya', 'Mali', 'Mozambique', 'Sierra Leone', or 'South Africa'.")
        message("Otherwise treated as 'other'.")
        message("If this is not desired, specify your own misclassification matrix with algorithm names in 'Mmat'.")
        message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
        stop("")

      }

      if(!all(names(va_data_tomodel) %in% c("eava", "insilicova", "interva"))){

        message("Since 'Mmat' is not provided, algorithm names must be either 'eava', 'insilicova', or 'interva' to use stored CHAMPS-based estimates.")
        message("Otherwise specify your own misclassification matrix in 'Mmat'.")
        message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
        stop("")

      }

      country_tomodel = ifelse(country %in% names(Mmat_champs[[1]][[1]]$postmean), country, "other")
      # print(country_tomodel)

      Mmat.fixed_input = lapply(1:length(va_data_tomodel),
                                FUN = function(k){

                                  Mmat_champs[[age_group]][[names(va_data_tomodel)[k]]]$postmean[[country_tomodel]]

                                })
      names(Mmat.fixed_input) = names(va_data_tomodel)
      # print(Mmat.asDirich)
      # print(Mmat_champs[[age_group]][[names(va_data)[k]]]$asDirich[[ifelse(country %in% Mmat_champs[[age_group]][[names(va_data)[k]]]$asDirich, country, "other")]])

      if(isTRUE(all.equal(max(table(names(va_data_tomodel[[1]]))), 1))&all(names(va_data_tomodel[[1]]) %in% colnames(Mmat.fixed_input[[1]]))){

        # ## study causes subset of CHAMPS ----
        # Mmat.fixed_tomodel = lapply(1:length(va_data_tomodel),
        #                             FUN = function(k){
        #
        #                               tempmat = Mmat.fixed[[k]][names(va_data_tomodel[[k]]),names(va_data_tomodel[[k]])]
        #                               tempmat = tempmat/rowSums(tempmat)
        #                               rownames(tempmat) = colnames(tempmat) = names(va_data_tomodel[[k]])
        #                               return(tempmat)
        #
        #                             })
        # names(Mmat.fixed_tomodel) = names(va_data_tomodel)

      }else{

        ## study causes outside CHAMPS ----

        if(is.null(studycause_map)){

          message(paste0("Study causes: ", names(va_data_tomodel[[1]])))
          message(paste0("CHAMPS causes: ", colnames(Mmat_champs[[1]][[1]]$postmean[[1]])))
          message("Study causes are not a subset of CHAMPS causes.")
          message("Either map study causes to CHAMPS causes.")
          message("    For example, 'studycause_map' = c('study_cause1' = 'pneumonia', 'study_cause2' = 'ipre', 'study_cause3' = 'other', ...).")
          message("Or specify your own misclassification matrix in 'Mmat'.")
          message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
          stop("")

        }

        if(!is.character(studycause_map)){

          message("'studycause_map' must be of the format: c('study_cause1' = 'pneumonia', 'study_cause2' = 'ipre', 'study_cause3' = 'other', ...)}.")
          stop("")

        }

        if(isFALSE(all(names(va_data_tomodel[[1]]) %in% names(studycause_map)))){

          message(paste0("Match not provided for ", paste0(names(va_data_tomodel[[1]])[which(!(names(va_data_tomodel[[1]]) %in% names(studycause_map)))], collapse = ', ')))
          stop("")

        }

      }

    }else{

      ### user provided ----

      # hard checks
      if(!is.list(Mmat)){

        message("'Mmat' must be a named list like 'va_data', providing algorithm-specific fixed for misclassification matrices.")
        stop("")

      }else if(is.null(names(Mmat))||isFALSE(all.equal(sort(names(Mmat)), sort(names(va_data_tomodel))))){

        message("The list 'Mmat' must have the same names as 'va_data', representing the algorithms.")
        stop("")

      }else{

        Mmat = Mmat[names(va_data_tomodel)]

        for(k in 1:length(Mmat)){

          nonsimplex.entries = apply(Mmat[[k]], 1,
                                     FUN = function(v){

                                       any(v<0)||isFALSE(all.equal(sum(v), 1))

                                     })
          if(sum(nonsimplex.entries)>0){

            message(paste0("Row index in misclassification matrix: ", paste0(which(nonsimplex.entries), collapse = ", "), "."))
            message(paste0("The above rows in the fixed misclassification matrix provided for ", names(va_data_tomodel)[k], " algorithm are not in the simplex."))
            message("Each row of the matrix must be non-negative and sum to 1.")
            stop("")

          }

          if(!is.matrix(Mmat[[k]])) stop(paste0("Fixed misclassification matrix for ", names(Mmat)[k]," algorithm must be a matrix."))
          if(is.null(rownames(Mmat[[k]]))) stop(paste0("Fixed misclassification matrix for ", names(Mmat)[k], " algorithm must have causes as row names."))
          if(is.null(colnames(Mmat[[k]]))) stop(paste0("Fixed misclassification matrix for ", names(Mmat)[k], " algorithm must have causes as column names."))
          if(isFALSE(all.equal(rownames(Mmat[[k]]), colnames(Mmat[[k]]), names(va_data_tomodel[[k]])))) stop("Causes specified in rows and columns of 'Mmat' do not match.")

        }

        Mmat.fixed_input = Mmat

      }

    }

  }else if(Mmat_type=="prior"){

    ## prior on misclassification matrix ----

    if(is.null(Mmat)){

      ### default: CHAMPS ----

      utils::data("Mmat_champs", package = "vacalibration", envir = environment())
      # print(Mmat_champs$neonate$eava$postmean$Mozambique)
      # print(Mmat_champs$neonate$eava$asDirich$Mozambique)

      if(is.null(age_group)){

        message("Since 'Mmat' is not provided, provide the age group.")
        message("Must be 'neonate' (for 0-27 days) or 'child' (for 1-59 months).")
        message("Otherwise specify your own misclassification matrix with algorithm names in 'Mmat'.")
        message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
        stop("")

      }

      if(is.null(country)){

        message("Since 'Mmat' is not provided, specify the country of for the 'va_data'")
        message("Must be 'Bangladesh', 'Ethiopia', 'Kenya', 'Mali', 'Mozambique', 'Sierra Leone', or 'South Africa'.")
        message("Otherwise treated as 'other'.")
        message("If this is not desired, specify your own misclassification matrix with algorithm names in 'Mmat'.")
        message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
        stop("")

      }

      if(!all(names(va_data_tomodel) %in% c("eava", "insilicova", "interva"))){

        message("Since 'Mmat' is not provided, algorithm names must be either 'eava', 'insilicova', or 'interva' to use stored CHAMPS-based estimates.")
        message("Otherwise specify your own misclassification matrix in 'Mmat'.")
        message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
        stop("")

      }

      country_tomodel = ifelse(country %in% names(Mmat_champs[[1]][[1]]$asDirich), country, "other")
      # print(country_tomodel)

      # print(1:length(va_data_tomodel))
      # print(names(va_data_tomodel))
      # print(Mmat_champs[[age_group]][[names(va_data_tomodel)[1]]]$asDirich[[country_tomodel]])
      Mmat.asDirich_input = lapply(1:length(va_data_tomodel),
                                   FUN = function(k){

                                     # print(k)
                                     # print(Mmat_champs[[age_group]][[names(va_data_tomodel)[k]]]$asDirich)
                                     # print(ifelse(country %in% names(Mmat_champs[[age_group]][[names(va_data_tomodel)[k]]]$asDirich), country, "other"))
                                     # return(Mmat_champs[[age_group]][[names(va_data_tomodel)[k]]]$asDirich[[country_tomodel]])

                                     Mmat_champs[[age_group]][[names(va_data_tomodel)[k]]]$asDirich[[country_tomodel]]

                                   })
      # print(Mmat.asDirich)
      names(Mmat.asDirich_input) = names(va_data_tomodel)
      # print(Mmat.asDirich)
      # print(Mmat_champs[[age_group]][[names(va_data)[k]]]$asDirich[[ifelse(country %in% Mmat_champs[[age_group]][[names(va_data)[k]]]$asDirich, country, "other")]])

      # print(va_data_tomodel)
      if(isTRUE(all.equal(max(table(names(va_data_tomodel[[1]]))), 1))&all(names(va_data_tomodel[[1]]) %in% colnames(Mmat.asDirich_input[[1]]))){

        # ## study causes subset of CHAMPS ----
        # Mmat.asDirich_study = lapply(1:length(va_data_tomodel),
        #                              FUN = function(k){
        #
        #                                tempmat = Mmat.asDirich_input[[k]][names(va_data_tomodel[[k]]),names(va_data_tomodel[[k]])]
        #                                rownames(tempmat) = colnames(tempmat) = names(va_data_tomodel[[k]])
        #                                return(tempmat)
        #
        #                              })
        # names(Mmat.asDirich_study) = names(va_data_tomodel)

      }else{

        ## study causes outside CHAMPS ----

        if(is.null(studycause_map)){

          message(paste0("Study causes: ", names(va_data_tomodel[[1]])))
          message(paste0("CHAMPS causes: ", colnames(Mmat_champs[[1]][[1]]$asDirich[[1]])))
          message("Study causes are not a subset of CHAMPS causes.")
          message("Either map study causes to CHAMPS causes.")
          message("    For example, 'studycause_map' = c('study_cause1' = 'pneumonia', 'study_cause2' = 'ipre', 'study_cause3' = 'other', ...).")
          message("Or specify your own misclassification matrix in 'Mmat'.")
          message("    For example, 'Mmat' = list('algo1' = Mmat1, 'algo2' = Mmat2, ...).")
          stop("")

        }

        if(!is.character(studycause_map)){

          message("'studycause_map' must be of the format: c('study_cause1' = 'pneumonia', 'study_cause2' = 'ipre', 'study_cause3' = 'other', ...)}.")
          stop("")

        }

        if(isFALSE(all(names(va_data_tomodel[[1]]) %in% names(studycause_map)))){

          message(paste0("Match not provided for ", paste0(names(va_data_tomodel[[1]])[which(!(names(va_data_tomodel[[1]]) %in% names(studycause_map)))], collapse = ', ')))
          stop("")

        }

        # if(verbose){
        #
        #   # cat("\n")
        #   message("Mapping study causes to CHAMPS causes ... ")
        #
        # }
        #
        # map.cause = data.frame('study' = names(va_data_tomodel[[1]]),
        #                        'champs' = unname(studycause_map[names(va_data_tomodel[[1]])]))
        #
        # eps = 0.001
        #
        # # champs cause frequencies to distribute false positives or maintain sensitivity
        # champs_cause.freq = table(map.cause$champs)
        # multiplied_champs_cause = names(champs_cause.freq)[champs_cause.freq>1]
        # unique_champscause = unique(map.cause$champs)
        #
        # Mmat.asDirich_study = lapply(1:length(va_data_tomodel),
        #                                FUN = function(k){
        #
        #                                  asDirich_champs_k = Mmat.asDirich_input[[k]][unique_champscause,unique_champscause]
        #                                  rownames(asDirich_champs_k) = colnames(asDirich_champs_k) = unique_champscause
        #                                  shapesumDirich_champs_k = rowSums(asDirich_champs_k)
        #                                  meanDirich_champs_k = asDirich_champs_k/shapesumDirich_champs_k
        #                                  # print(meanDirich_champs_k)
        #                                  # print(shapesumDirich_champs_k)
        #
        #                                  ## cause matching
        #                                  # print(map.cause)
        #                                  Mmat_meanDirich_k = meanDirich_champs_k[map.cause$champs,map.cause$champs]
        #                                  # print(Mmat_meanDirich_k)
        #                                  # print(dim(Mmat_meanDirich_k))
        #                                  # print(map.cause$study)
        #                                  # print(length(map.cause$study))
        #                                  # print(rownames(Mmat_meanDirich_k))
        #                                  # print(colnames(Mmat_meanDirich_k))
        #                                  # dimnames(Mmat_meanDirich_k) = list(map.cause$study,map.cause$study)
        #                                  rownames(Mmat_meanDirich_k) = colnames(Mmat_meanDirich_k) = map.cause$study
        #                                  # print(Mmat_meanDirich_k)
        #
        #                                  ## expanding classification rates to study-specific causes
        #                                  if(length(multiplied_champs_cause)>0){
        #
        #                                    for(l in 1:length(multiplied_champs_cause)){
        #
        #                                      (id_l = which(map.cause$champs %in% multiplied_champs_cause[l]))
        #                                      (idothers_l = which(!(map.cause$champs %in% multiplied_champs_cause[l])))
        #
        #                                      tempmat = matrix(data = eps/(champs_cause.freq[multiplied_champs_cause[l]] - 1),
        #                                                       nrow = length(id_l), ncol = length(id_l))
        #                                      diag(tempmat) = 1 - eps
        #                                      Mmat_meanDirich_k[id_l, id_l] = tempmat*Mmat_meanDirich_k[id_l, id_l]
        #
        #                                      Mmat_meanDirich_k[idothers_l, id_l] =
        #                                        Mmat_meanDirich_k[idothers_l, id_l]/champs_cause.freq[multiplied_champs_cause[l]]
        #
        #                                    }
        #
        #                                  }
        #
        #                                  ## misclassification prior to use
        #
        #                                  ## misclassification prior to use
        #                                  Mmat.asDirich_study_k = shapesumDirich_champs_k[map.cause$champs]*Mmat_meanDirich_k
        #                                  rownames(Mmat.asDirich_study_k) = colnames(Mmat.asDirich_study_k) = map.cause$study
        #
        #                                  Mmat.asDirich_study_k
        #
        #                                })
        # names(Mmat.asDirich_study) = names(va_data_tomodel)
        #
        # if(verbose){
        #
        #   # cat("\n")
        #   message("Mapping study causes to CHAMPS causes ... Done.")
        #
        # }

      }

    }else{

      ### user provided ----

      # hard checks
      if(!is.list(Mmat)){

        message("'Mmat' must be a named list like 'va_data', providing algorithm-specific prior for misclassification matrices.")
        stop("")

      }else if(is.null(names(Mmat))||isFALSE(all.equal(sort(names(Mmat)), sort(names(va_data_tomodel))))){

        message("The list 'Mmat' must have the same names as 'va_data', representing the algorithms.")
        stop("")

      }else{

        Mmat = Mmat[names(va_data_tomodel)]

        for(k in 1:length(Mmat)){

          nonpositive.entries = apply(Mmat[[k]], 1, FUN = function(v){sum(v<=0)>0})
          if(sum(nonpositive.entries)>0){

            message(paste0("Row index in misclassification matrix: ", paste0(which(nonpositive.entries), collapse = ", "), "."))
            message(paste0("The above rows in the prior misclassification matrix provided for ", names(va_data_tomodel)[k], " algorithm are not Dirichlet"))
            message("Each row of the matrix must be strictly positive.")
            stop("")

          }

          if(!is.matrix(Mmat[[k]])) stop(paste0("Prior for ", names(Mmat)[k]," algorithm must be a matrix."))
          if(is.null(rownames(Mmat[[k]]))) stop(paste0("Prior for ", names(Mmat)[k], " algorithm must have causes as row names."))
          if(is.null(colnames(Mmat[[k]]))) stop(paste0("Prior for ", names(Mmat)[k], " algorithm must have causes as column names."))
          if(isFALSE(all.equal(rownames(Mmat[[k]]), colnames(Mmat[[k]]), names(va_data_tomodel[[k]])))) stop("Causes specified in rows and columns of 'Mmat' do not match.")

        }

        Mmat.asDirich_input = Mmat

      }

    }

  }else if(Mmat_type=="samples"){

    ## misclassification matrix samples ----

    if(is.null(Mmat)){

      stop("Need to provide samples of misclassification matrix for 'Mmat_type'='samples'.")

    }else{

      # hard checks
      if(!is.list(Mmat)){

        message("'Mmat' must be a named list like 'va_data', providing algorithm-specific misclassification matrix samples.")
        stop("")

      }else if(is.null(names(Mmat))){

        stop("The list 'Mmat' must have identical names as 'va_data' indicating algorithms.")

      }else if(is.null(names(Mmat))||isFALSE(all.equal(sort(names(Mmat)), sort(names(va_data_tomodel))))){

        message("The list 'Mmat' must have the same names as 'va_data', representing the algorithms.")
        stop("")

      }else{

        Mmat = Mmat[names(va_data_tomodel)]

        Mmat.asDirich_input = va_data_tomodel
        for(k in 1:length(Mmat)){

          if(!is.array(Mmat[[k]])){

            message(paste0("Samples for ", names(Mmat)[k]," algorithm must be a 3-dimensional array."))
            message("     Dimensions respectively represent:")
            message("         (1) samples,")
            message("         (2) row of misclassification matrix, and")
            message("         (3) column of misclassification matrix.")
            stop("")

          }

          if(is.null(dimnames(Mmat[[k]])[[2]])) stop(paste0("Misclassification matrix samples for ", names(Mmat)[k], " algorithm must have causes as row names."))

          if(is.null(dimnames(Mmat[[k]])[[3]])) stop(paste0("Misclassification matrix samples for ", names(Mmat)[k], " algorithm must have causes as column names."))

          if(isFALSE(all.equal(dimnames(Mmat[[k]])[[2]], dimnames(Mmat[[k]])[[3]]))){

            message(paste0("Row names: ", paste0(dimnames(Mmat[[k]])[[2]], collapse = ", ")))
            message(paste0("Column names: ", paste0(dimnames(Mmat[[k]])[[3]], collapse = ", ")))
            message(paste0("Causes specified in rows and columns of misclassification matrix samples for ", names(Mmat)[k], " algorithm do not match."))
            stop("")

          }

          Mmat[[k]] = Mmat[[k]][,names(va_data_tomodel[[k]]),names(va_data_tomodel[[k]])]

          nonsimplex.entries = apply(Mmat[[k]], 1:2,
                                     FUN = function(v){

                                       any(v<0)||isFALSE(all.equal(sum(v), 1))

                                     })

          if(sum(nonsimplex.entries)>0){

            arr.ind = which(nonsimplex.entries, arr.ind = T)

            message(paste0("Sample index: ", paste0(arr.ind[,"row"], collapse = ", "), "."))
            message(paste0("Rows in misclassification matrix: ", paste0(arr.ind[,"col"], collapse = ", "), "."))
            message("Above misclassification matrix samples are not in the simplex.")
            message("For each sample, each row of misclassification matrix must be non-negative and sum to 1.")
            stop("")

          }

          if(isFALSE(all.equal(dimnames(Mmat[[k]])[[2]], names(va_data_tomodel[[k]])))){

            message(paste0("Causes in misclassification samples: ", paste0(dimnames(Mmat[[k]])[[2]], collapse = ", ")))
            message(paste0("Causes in 'va_data': ", paste0(names(va_data_tomodel[[k]]), collapse = ", ")))
            message(paste0("Causes specified in misclassification matrix samples and 'va_data' for ", names(Mmat)[k], " algorithm do not match."))
            stop("")

          }

          # posterior mean
          Mmat.mean = apply(Mmat[[k]], 2:3, mean)

          Mmat.asDirich_input[[k]] = do.call("rbind",
                                               lapply(1:dim(Mmat[[k]])[2],
                                                      FUN = function(i){

                                                        mle.out = nlminb(start = 1,
                                                                         lower = 0,
                                                                         upper = Inf,
                                                                         objective = function(lambda_mmat){

                                                                           -sum(LaplacesDemon::ddirichlet(x = (Mmat[[k]])[,i,],
                                                                                                          alpha = dim(Mmat[[k]])[2]*lambda_mmat*Mmat.mean[i,],
                                                                                                          log = T))

                                                                         })

                                                        dim(Mmat[[k]])[2]*mle.out$par*Mmat.mean[i,]

                                                      }))
          rownames(Mmat.asDirich_input[[k]]) = colnames(Mmat.asDirich_input[[k]]) = colnames(Mmat.mean)

        }

      }

    }

  }


  # causes not calibrated ----
  if(is.null(donotcalib)){

    donotcalib = lapply(1:length(va_data_tomodel),
                        FUN = function(k){

                          'other'

                        })
    names(donotcalib) = names(va_data_tomodel)

  }else{

    if(!is.list(donotcalib)){

      stop("'donotcalib' must be a named list like 'va_data', indicating algorithm-specific causes that will not be calibrated.")

    }else if(is.null(names(donotcalib))||isFALSE(all.equal(names(donotcalib), names(va_data_tomodel)))){

      stop("The list 'donotcalib' must have the same names as 'va_data', representing the algorithms.")

    }else{

      for(k in 1:length(va_data_tomodel)){

        if((!is.null(donotcalib[[k]]))&(!all(donotcalib[[k]] %in% names(va_data_tomodel[[k]])))){

          message(paste0(donotcalib[[k]][!(donotcalib[[k]] %in% names(va_data_tomodel[[k]]))], collapse = ', '))
          message(paste0("The above causes listed in 'donotcalib' for ", names(va_data_tomodel)[k], " algorithm are not present in its 'va_data'."))
          stop("")

        }

      }

    }

  }



  # run calibration ----
  if(verbose){

    # cat("\n")
    message("Calibrating ...")

  }

  if(Mmat_type %in% c('prior', 'samples')){

    modular_vacalib_output = modular_vacalib_prior(va_unlabeled = va_data_tomodel,
                                                   Mmat_calib = Mmat.asDirich_input, studycause_map = studycause_map,
                                                   donotcalib = donotcalib,
                                                   donotcalib_type = donotcalib_type, nocalib.threshold = nocalib.threshold,
                                                   path_correction = path_correction, ensemble = ensemble,
                                                   # shrink_towards = shrink_towards,
                                                   shrink_strength = shrink_strength, lambda_eBayes = lambda_eBayes,
                                                   nMCMC = nMCMC, nBurn = nBurn, nThin = nThin,
                                                   nChain = nChain, nCore = nCore,
                                                   adapt_delta_stan = adapt_delta_stan, refresh.stan = refresh.stan,
                                                   seed = seed, verbose = verbose, plot_it = plot_it)

  }else if(Mmat_type %in% c('fixed')){

    modular_vacalib_output = modular_vacalib_fixed(va_unlabeled = va_data_tomodel,
                                                   Mmat_calib = Mmat.fixed_input, studycause_map = studycause_map,
                                                   donotcalib = donotcalib,
                                                   donotcalib_type = donotcalib_type, nocalib.threshold = nocalib.threshold,
                                                   path_correction = path_correction, ensemble = ensemble,
                                                   # shrink_towards = shrink_towards,
                                                   shrink_strength = shrink_strength, lambda_eBayes = lambda_eBayes,
                                                   nMCMC = nMCMC, nBurn = nBurn, nThin = nThin,
                                                   nChain = nChain, nCore = nCore,
                                                   adapt_delta_stan = adapt_delta_stan, refresh.stan = refresh.stan,
                                                   seed = seed, verbose = verbose, plot_it = plot_it)

  }

  if(verbose){

    message("Done.")

  }


  # return output ----
  class(modular_vacalib_output) = "vacalibration"

  if(saveoutput){

    if(is.null(output_filename)){output_filename = "vacalibration_out"}

    if(is.null(output_dir)){

      saveRDS(modular_vacalib_output, file.path(tempdir(), output_filename))

    }else{saveRDS(modular_vacalib_output, file.path(output_dir, output_filename))}

  }else{

    return(modular_vacalib_output)

  }

}


