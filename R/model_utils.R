#' @keywords internal
get_stan_seqcalib_mmat <- local({
  seqcalib_mmat_model <- NULL
  function() {
    if (is.null(seqcalib_mmat_model)) {
      seqcalib_mmat_stan_file <- system.file("stan", "seqcalib_mmat.stan", package = "vacalibration")
      seqcalib_mmat_model <<- rstan::stan_model(file = seqcalib_mmat_stan_file)
    }
    seqcalib_mmat_model
  }
})
get_stan_seqcalib <- local({
  seqcalib_model <- NULL
  function() {
    if (is.null(seqcalib_model)) {
      seqcalib_stan_file <- system.file("stan", "seqcalib.stan", package = "vacalibration")
      seqcalib_model <<- rstan::stan_model(file = seqcalib_stan_file)
    }
    seqcalib_model
  }
})
get_stan_seqcalib_q <- local({
  seqcalib_q_model <- NULL
  function() {
    if (is.null(seqcalib_q_model)) {
      seqcalib_q_stan_file <- system.file("stan", "seqcalib_q.stan", package = "vacalibration")
      seqcalib_q_model <<- rstan::stan_model(file = seqcalib_q_stan_file)
    }
    seqcalib_q_model
  }
})
