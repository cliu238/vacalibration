#' Broad Cause Mapping
#'
#' Maps individual-level specific (high resolution) cause of death (\code{codEAVA()} function
#' in \code{EAVA} and \code{crossVA()} function in \code{openVA}) to broad causes.
#'
#' @param df Data frame. Outputs from \code{crossVA()} function in \code{openVA} for EAVA and \code{crossVA()} function in \code{openVA} for InSilicoVA and InterVA
#'
#' @param age_group Character. The age group of interest. "neonate" for deaths between 0-27 days, and "child" for 1-59 months.
#'
#' @return Matrix. Rows are individuals. Columns are broad causes.
#'         This is a binary matrix (entries 0 or 1) with 1 indicating the broad cause of death for the individual.
#'
#' @importFrom reshape2 dcast
#'
#' @examples
#'
#' ## COMSA-Mozambique Publicly Available Version
#' ## Example Individual-Level Specific (High-Resolution) Cause of Death Data
#' data(comsamoz_public_openVAout)
#' head(comsamoz_public_openVAout$data)  # head of the data
#' comsamoz_public_openVAout$data[1,]  # ID and specific cause of death for individual 1
#'
#' ## mapped to broad cause
#' ## same as comsamoz_public_broad$data
#' comsamoz_public_asbroad = cause_map(df = comsamoz_public_openVAout$data, age_group = "neonate")
#' head(comsamoz_public_asbroad)
#'
#' ### store broad cause map of the data
#' data(comsamoz_public_broad)
#' head(comsamoz_public_broad$data) # identical to head(comsamoz_public_asbroad)
#'
#' @importFrom stats model.matrix quantile setNames
#' @importFrom utils head
#'
#' @export
cause_map <- function(df,age_group){

  if(ncol(df)==2 && "cause" %in% colnames(df)){
    df <- subset(df, cause != "Unspecified")
    df$cause <- tolower(df$cause)
    df <- reshape2::dcast(df,ID~cause,fun.aggregate = function(x){as.integer(length(x) > 0)}) # Put EAVA in wide format to match output of getIndivProb()
    row.names(df) <- df$ID
    df$ID <- NULL
  }

  if(ncol(df)==2 && "cause1" %in% colnames(df)){
    df <- subset(df, cause1 != "Unspecified")
    df$cause1 <- tolower(df$cause1)
    df <- reshape2::dcast(df,ID~cause1,fun.aggregate = function(x){as.integer(length(x) > 0)}) # Put EAVA in wide format to match output of getIndivProb()
    names(df)[names(df) == "cause1"] <- "cause"
    row.names(df) <- df$ID
    df$ID <- NULL
  }


  df <- as.matrix(df)
  colnames(df) <- tolower(colnames(df))
  age_group <- tolower(age_group)

  if(age_group=="neonate"){

    # NEONATAL CAUSES
    congenital_malformation <- c("congenital malformation","malformation")

    pneumonia <- c("neonatal pneumonia",
                   "acute resp infect incl pneumonia",
                   "pneumonia")

    sepsis_meningitis_inf <- c("neonatal sepsis",
                               "pregnancy-related sepsis",
                               "sepsis (non-obstetric)",
                               "meningitis and encephalitis",
                               "dengue fever",
                               "diarrhoeal diseases",
                               "diarrhea",
                               "haemorrhagic fever (non-dengue)",
                               "hiv/aids related death",
                               "malaria",
                               "measles",
                               "other and unspecified infect dis",
                               "pertussis",
                               "pulmonary tuberculosis",
                               "tetanus",
                               "sepsis",
                               "meningitis",
                               "nnt")

    ipre <- c("birth asphyxia","intrapartum")

    other <- c("abortion-related death",
               "accid poisoning & noxious subs",
               "anaemia of pregnancy",
               "assault",
               "asthma",
               "accid drowning and submersion",
               "accid expos to smoke fire & flame",
               "accid fall",
               "acute abdomen",
               "acute cardiac disease",
               "breast neoplasms",
               "chronic obstructive pulmonary dis",
               "contact with venomous plant/animal",
               "diabetes mellitus",
               "digestive neoplasms",
               "ectopic pregnancy",
               "epilepsy",
               "exposure to force of nature",
               "fresh stillbirth",
               "intentional self-harm",
               "liver cirrhosis",
               "macerated stillbirth",
               "obstetric haemorrhage",
               "obstructed labour",
               "oral neoplasms",
               "other and unspecified cardiac dis",
               "other and unspecified external cod",
               "other and unspecified maternal cod",
               "other and unspecified neonatal cod",
               "other and unspecified neoplasms",
               "other transport accident",
               "other and unspecified ncd",
               "pregnancy-induced hypertension",
               "renal failure",
               "reproductive neoplasms mf",
               "respiratory neoplasms",
               "road traffic accident",
               "ruptured uterus",
               "severe anaemia",
               "severe malnutrition",
               "sickle cell with crisis",
               "stroke",
               "other")

    prematurity <- c("prematurity",
                     "preterm")

    cause_map <- data.frame(causes = c(congenital_malformation, pneumonia, sepsis_meningitis_inf,
                                       ipre, other, prematurity),
                            broad_cause = rep(c("congenital_malformation", "pneumonia", "sepsis_meningitis_inf",
                                                "ipre", "other", "prematurity"),
                                              c(length(congenital_malformation), length(pneumonia), length(sepsis_meningitis_inf),
                                                length(ipre), length(other), length(prematurity))))

    causes <- c("congenital_malformation", "pneumonia", "sepsis_meningitis_inf","ipre", "other", "prematurity")
    C <- length(causes)
  }


  if(age_group=="child"){

    # 1 TO 59m CAUSES
    malaria <- c("malaria")
    pneumonia <- c("acute resp infect incl pneumonia",
                   "neonatal pneumonia",
                   "pneumonia")
    diarrhea <- c("diarrhoeal diseases",
                  "diarrhea/dysentery")
    severe_malnutrition <- c("severe malnutrition",
                             "malnutrition")
    hiv <- c("hiv/aids related death",
             "aids")
    injury <- c("accid drowning and submersion",
                "accid expos to smoke fire & flame",
                "accid fall",
                "accid poisoning & noxious subs",
                "assault",
                "exposure to force of nature",
                "intentional self-harm",
                "other and unspecified external cod",
                "other transport accident",
                "road traffic accident",
                "injury")
    other <- c("abortion-related death",
               "acute abdomen",
               "acute cardiac disease",
               "anaemia of pregnancy",
               "asthma",
               "breast neoplasms",
               "chronic obstructive pulmonary dis",
               "contact with venomous plant/animal",
               "diabetes mellitus",
               "digestive neoplasms",
               "ectopic pregnancy",
               "epilepsy",
               "fresh stillbirth",
               "liver cirrhosis",
               "macerated stillbirth",
               "obstetric haemorrhage",
               "obstructed labour",
               "oral neoplasms",
               "other and unspecified cardiac dis",
               "other and unspecified maternal cod",
               "other and unspecified ncd",
               "other and unspecified neonatal cod",
               "other and unspecified neoplasms",
               "pregnancy-induced hypertension",
               "renal failure",
               "reproductive neoplasms mf",
               "respiratory neoplasms",
               "ruptured uterus",
               "severe anaemia",
               "sickle cell with crisis",
               "stroke")

    other_infections <- c("dengue fever",
                          "haemorrhagic fever (non-dengue)",
                          "measles",
                          "meningitis and encephalitis",
                          "neonatal sepsis",
                          "other and unspecified infect dis",
                          "pertussis",
                          "pregnancy-related sepsis",
                          "pulmonary tuberculosis",
                          "sepsis (non-obstetric)",
                          "tetanus",
                          "measles",
                          "meningitis/encephalitis",
                          "other infections")

    nn_causes <- c("congenital malformation","birth asphyxia","prematurity",
                   "malformation","intrapartum","preterm")

    cause_map <- data.frame(causes = c(malaria, pneumonia, diarrhea,
                                       severe_malnutrition, hiv, injury, other, other_infections,
                                       nn_causes),
                            broad_cause = rep(c("malaria", "pneumonia",
                                                "diarrhea", "severe_malnutrition", "hiv", "injury", "other","other_infections",
                                                "nn_causes"),
                                              c(length(malaria), length(pneumonia),
                                                length(diarrhea), length(severe_malnutrition),
                                                length(hiv), length(injury), length(other), length(other_infections),
                                                length(nn_causes))))

    causes <- c("malaria", "pneumonia","diarrhea", "severe_malnutrition", "hiv", "injury", "other",
                "other_infections","nn_causes")
    C <- length(causes)
  }


  ### map individual causes into broad groups - generalize for child and neonate

  model_broad_probs <- df
  colnames(model_broad_probs) <- cause_map$broad_cause[match(colnames(model_broad_probs),cause_map$causes)]
  mn <- model.matrix(~ colnames(model_broad_probs) + 0)
  model_broad_probs <- model_broad_probs %*% mn
  colnames(model_broad_probs) <- gsub("colnames\\(model_broad_probs\\)", "",
                                      colnames(model_broad_probs))

  for (cause in causes) {
    if (!(cause %in% colnames(model_broad_probs))) {
      model_broad_probs <- cbind(model_broad_probs,
                                 setNames(data.frame(rep(0, nrow(model_broad_probs))), cause))
    }
  }

  model_broad_probs <- model_broad_probs[,causes]

  model_broad_probs <- as.data.frame(model_broad_probs)

  names <- colnames(model_broad_probs)
  model_broad_probs <- t(apply(model_broad_probs, 1, function(x) as.numeric(x == max(x))))
  colnames(model_broad_probs) <- names

  return(as.matrix(model_broad_probs, stringsAsFactors = FALSE))

}
