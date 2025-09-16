## ----include = FALSE----------------------------------------------------------
knitr::opts_chunk$set(
  collapse = TRUE,
  comment = "#>"
)

## ----results='asis', echo=FALSE-----------------------------------------------
cat('
<style>
  h1 {
    font-size: 30px;
    margin-top: 50px;  /* increase spacing above headings */
  }
  h2 {
    font-size: 22px;
    margin-top: 22px;  /* increase spacing above headings */
  }
  h3 {
    font-size: 18px;
    margin-top: 18px;  /* increase spacing above headings */
  }
  body {
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
    font-size: 110%
  }
  pre {
    position: relative;
  }
  .copy-btn {
    position: absolute;
    top: 6px;
    right: 6px;
    background-color: #f0f0f0;
    border: 1px solid #ccc;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    cursor: pointer;
    opacity: 0.7;
    transition: opacity 0.3s ease;
  }
  .copy-btn:hover {
    opacity: 1;
  }
  #TOC {
    font-size: 16px; /* Adjust as needed for the overall TOC container */
  }
  #TOC ul li {
    font-size: 14px; /* Adjust as needed for individual list items */
  }
  #TOC ul li a {
    font-size: 20px; /* Adjust as needed for the links within the list items */
  }
  .tocify {
    width: 1000px !important; /* adjust width as needed */
  }
  #vignette {
    margin-left: 10px !important; /* match or slightly more than .tocify width */
  }
</style>

<script>
document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll("pre").forEach(function(pre) {
    const button = document.createElement("button");
    button.className = "copy-btn";
    button.textContent = "Copy";
    pre.style.position = "relative";
    pre.appendChild(button);

    button.addEventListener("click", function() {
      const code = pre.querySelector("code");
      if (!code) return;
      navigator.clipboard.writeText(code.innerText).then(() => {
        button.textContent = "Copied!";
        setTimeout(() => {
          button.textContent = "Copy";
        }, 1500);
      });
    });
  });
});
</script>
')

## ----eval=F-------------------------------------------------------------------
# install.packages("vacalibration") # install
# library(vacalibration) # load

## ----eval=F-------------------------------------------------------------------
# data(comsamoz_public_openVAout)  # load data in R environment
# 
# class(comsamoz_public_openVAout)  # list
# names(comsamoz_public_openVAout)  # different components
# 
# comsamoz_public_openVAout$age_group  # age group
# comsamoz_public_openVAout$va_algo  # algorithm
# head(comsamoz_public_openVAout$data)  # head of the specific COD data
# # for these 6 individuals, the causes of deaths are "Other and unspecified neonatal CoD",
# # "Birth asphyxia", "Neonatal sepsis", "Birth asphyxia", "Birth asphyxia", "Neonatal sepsis"

## ----eval=F-------------------------------------------------------------------
# data(comsamoz_public_broad)  # load data in R environment
# head(comsamoz_public_broad$data)  # head of the stored broad COD data
# # for these 6 individuals, the causes of deaths are "other", "ipre", "sepsis_meningitis_inf",
# # "ipre", "ipre", "sepsis_meningitis_inf"

## ----eval=F, results = 'hide', message = FALSE, warning = FALSE, fig.show = "hide"----
# calib_out_specific = vacalibration(va_data = setNames(list(comsamoz_public_openVAout$data),
#                                                       list(comsamoz_public_openVAout$va_algo)),
#                                    age_group = comsamoz_public_openVAout$age_group,
#                                    country = "Mozambique")

## ----eval=F-------------------------------------------------------------------
# round(calib_out_specific$p_uncalib, 3) # uncalibrated (rounded upto 3 significant digits)
# round(calib_out_specific$pcalib_postsumm["insilicova",,], 3) # calibrated (rounded upto 3 significant digits)

## ----eval=F, results = 'hide', message = FALSE, warning = FALSE, fig.show = "hide"----
# calib_out_broad = vacalibration(va_data = setNames(list(comsamoz_public_broad$data),
#                                                    list(comsamoz_public_broad$va_algo)),
#                                 age_group = comsamoz_public_broad$age_group,
#                                 country = "Mozambique")

## ----eval=F, results = 'hide', message = FALSE, warning = FALSE, fig.show = "hide"----
# calib_out_deathcount = vacalibration(va_data = setNames(list(colSums(comsamoz_public_broad$data)),
#                                                         list(comsamoz_public_broad$va_algo)),
#                                      age_group = comsamoz_public_broad$age_group,
#                                      country = "Mozambique")

## ----eval=F-------------------------------------------------------------------
# #################################### uncalibrated ####################################
# round(calib_out_specific$p_uncalib, 3)  # specific cause
# round(calib_out_broad$p_uncalib, 3)  # broad cause
# round(calib_out_deathcount$p_uncalib, 3)  # broad-cause-specific death count
# 
# 
# #################################### calibrated ####################################
# round(calib_out_specific$pcalib_postsumm["insilicova",,], 3)  # specific cause
# round(calib_out_broad$pcalib_postsumm["insilicova",,], 3)  # broad cause
# round(calib_out_deathcount$pcalib_postsumm["insilicova",,], 3)  # broad-cause-specific death count

## ----eval=F, results = 'hide', message = FALSE, warning = FALSE, fig.show = "hide"----
# # default
# calib_out_specific = vacalibration(va_data = setNames(list(comsamoz_public_openVAout$data),
#                                                       list(comsamoz_public_openVAout$va_algo)),
#                                    age_group = comsamoz_public_openVAout$age_group,
#                                    country = "Mozambique")
# 
# # misclassification estimates provided by user
# calib_out_specific_mmat = vacalibration(va_data = setNames(list(comsamoz_public_openVAout$data),
#                                                            list(comsamoz_public_openVAout$va_algo)),
#                                         Mmat.asDirich = setNames(list(Mmat_champs[[comsamoz_public_openVAout$age_group]][[comsamoz_public_openVAout$va_algo]]$asDirich[["Mozambique"]]),
#                                                            list(comsamoz_public_openVAout$va_algo)),
#                                    age_group = comsamoz_public_openVAout$age_group,
#                                    country = "Mozambique")

## ----eval=F-------------------------------------------------------------------
# #################################### uncalibrated ####################################
# round(calib_out_specific$p_uncalib, 3)  # default
# round(calib_out_specific_mmat$p_uncalib, 3)  # user provided misclassification estimate
# 
# 
# #################################### calibrated ####################################
# round(calib_out_specific$pcalib_postsumm["insilicova",,], 3)  # default
# round(calib_out_specific_mmat$pcalib_postsumm["insilicova",,], 3)  # user provided misclassification estimate

## ----eval=F-------------------------------------------------------------------
# va_data_example = list("eava" = c("congenital_malformation" = 40, "pneumonia" = 175,
#                                   "sepsis_meningitis_inf" = 265, "ipre" = 220,
#                                   "other" = 30, "prematurity" = 170),
#                        "insilicova" = c("congenital_malformation" = 5, "pneumonia" = 145,
#                                         "sepsis_meningitis_inf" = 370, "ipre" = 330,
#                                         "other" = 60, "prematurity" = 290))

## ----eval=F, results = 'hide', message = FALSE, warning = FALSE, fig.show = "hide"----
# calib_out_ensemble = vacalibration(va_data = va_data_example,
#                                    age_group = "neonate", country = "Mozambique")

## ----eval=F-------------------------------------------------------------------
# round(calib_out_ensemble$p_uncalib, 3) # uncalibrated
# round(calib_out_ensemble$pcalib_postsumm["eava",,], 3) # EAVA-specific calibration
# round(calib_out_ensemble$pcalib_postsumm["insilicova",,], 3) # InSilicoVA-specific calibration
# round(calib_out_ensemble$pcalib_postsumm["ensemble",,], 3) # Ensemble calibration

