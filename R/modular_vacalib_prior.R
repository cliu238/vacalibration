#' Modular VA-Calibration for Dirichlet Prior on Misclassification Matrix
#'
#' @import patchwork
#' @import rstan
#' @import ggplot2
#'
#' @importFrom stats quantile
#' @importFrom utils head
#' @importFrom MASS ginv
#'
modular_vacalib_prior <- function(va_unlabeled = NULL,
                                  Mmat_calib = NULL, studycause_map = NULL,
                                  donotcalib = NULL,
                                  donotcalib_type = c("learn", "fixed")[1], nocalib.threshold = 0.1,
                                  path_correction = TRUE, ensemble = NULL,
                                  # shrink_towards = c("calib", "uncalib")[2],
                                  shrink_strength = NULL, lambda_eBayes = NULL,
                                  nMCMC = 5000, nBurn = 5000, nThin = 1,
                                  nChain = 1, nCore = 1,
                                  adapt_delta_stan = .9, refresh.stan = NULL,
                                  seed = 1, verbose = TRUE, plot_it = TRUE){


  # saving all input
  input.list = as.list(environment())

  rstan::rstan_options(auto_write = TRUE)
  options(mc.cores = nCore)


  # va_data preparation for STAN implementation ----
  K = length(va_unlabeled) # number of algorithms

  for(k in 1:K){

    if(k==1){

      causes = names(va_unlabeled[[k]])
      nCause = length(causes)

      va_deaths = array(dim = c(K, nCause),
                        dimnames = list(names(va_unlabeled), causes))

    }

    va_deaths[k,] = va_unlabeled[[k]]

  }
  # print(va_deaths)


  ## observed uncalibrated csmf ----
  (puncalib = va_deaths/rowSums(va_deaths))
  # if(any(puncalib==0)){
  #
  #   puncalib[which.max(puncalib)] = puncalib[which.max(puncalib)] - 0.001
  #   puncalib[puncalib==0] = 0.001/sum(puncalib==0)
  #   puncalib[which.max(puncalib)] = 1 - sum(puncalib[-which.max(puncalib)])
  #
  # }


  # preparing misclassification matrix ----
  Mmat_calib_input = Mmat_calib
  if(is.null(studycause_map)){

    ## study causes are subset of CHAMPS causes ----
    Mmat_calib_study = lapply(1:length(va_unlabeled),
                              FUN = function(k){

                                tempmat = Mmat_calib_input[[k]][names(va_unlabeled[[k]]),names(va_unlabeled[[k]])]
                                rownames(tempmat) = colnames(tempmat) = names(va_unlabeled[[k]])
                                return(tempmat)

                              })
    names(Mmat_calib_study) = names(va_unlabeled)

  }else{

    ## study causes outside CHAMPS ----

    if(verbose){

      # cat("\n")
      message("Mapping study causes to CHAMPS causes ... ")

    }

    map.cause = data.frame('study' = names(va_unlabeled[[1]]),
                           'champs' = unname(studycause_map[names(va_unlabeled[[1]])]))

    eps = 0.001

    # champs cause frequencies to distribute false positives or maintain sensitivity
    champs_cause.freq = table(map.cause$champs)
    multiplied_champs_cause = names(champs_cause.freq)[champs_cause.freq>1]
    unique_champscause = unique(map.cause$champs)

    Mmat_calib_study = lapply(1:length(va_unlabeled),
                              FUN = function(k){

                                asDirich_champs_k = Mmat_calib_input[[k]][unique_champscause,unique_champscause]
                                rownames(asDirich_champs_k) = colnames(asDirich_champs_k) = unique_champscause
                                shapesumDirich_champs_k = rowSums(asDirich_champs_k)
                                mean_champs_k = asDirich_champs_k/shapesumDirich_champs_k

                                ## cause matching
                                Mmat_mean_k = mean_champs_k[map.cause$champs,map.cause$champs]
                                rownames(Mmat_mean_k) = colnames(Mmat_mean_k) = map.cause$study

                                ## expanding classification rates to study-specific causes
                                if(length(multiplied_champs_cause)>0){

                                  for(l in 1:length(multiplied_champs_cause)){

                                    (id_l = which(map.cause$champs %in% multiplied_champs_cause[l]))
                                    (idothers_l = which(!(map.cause$champs %in% multiplied_champs_cause[l])))

                                    tempmat = matrix(data = eps/(champs_cause.freq[multiplied_champs_cause[l]] - 1),
                                                     nrow = length(id_l), ncol = length(id_l))
                                    diag(tempmat) = 1 - eps
                                    Mmat_mean_k[id_l, id_l] = tempmat*Mmat_mean_k[id_l, id_l]

                                    Mmat_mean_k[idothers_l, id_l] =
                                      Mmat_mean_k[idothers_l, id_l]/champs_cause.freq[multiplied_champs_cause[l]]

                                  }

                                }

                                ## misclassification prior to use
                                Mmat_calib_study_k = shapesumDirich_champs_k[map.cause$champs]*Mmat_mean_k
                                rownames(Mmat_calib_study_k) = colnames(Mmat_calib_study_k) = map.cause$study

                                Mmat_calib_study_k

                              })
    names(Mmat_calib_study) = names(va_unlabeled)

    if(verbose){

      # cat("\n")
      message("Mapping study causes to CHAMPS causes ... Done.")
      message("")

    }

  }


  # causes not calibrated ----
  donotcalib_input = donotcalib
  if(is.null(studycause_map)){

    donotcalib_study = donotcalib_input

  }else{

    donotcalib_study = lapply(1:length(va_unlabeled),
                              FUN = function(k){

                                names(studycause_map)[studycause_map %in% donotcalib_input[[k]]]

                              })
    names(donotcalib_study) = names(va_unlabeled)

  }


  # calibration for each algorithm ----

  # storage
  donotcalib_study_asmat = donotcalib_tomodel_asmat = matrix(nrow = K, ncol = nCause)

  calibout = vector(mode = "list", length = K)

  calibrated = lambda_calibpath = rep(NA, K)

  rownames(donotcalib_study_asmat) = rownames(donotcalib_tomodel_asmat) =
    names(calibout) = names(Mmat_calib_study)
  colnames(donotcalib_study_asmat) = colnames(donotcalib_tomodel_asmat) = causes

  Mmat_calib_input_asarray =
    array(dim = c(K, dim(Mmat_calib_input[[1]])),
          dimnames = list(names(Mmat_calib_input),
                          rownames(Mmat_calib_input[[1]]),
                          colnames(Mmat_calib_input[[1]])))

  Mmat_calib_study_asarray =
    Mmat_calib_tomodel_asarray =
    array(dim = c(K, nCause, nCause),
          dimnames = list(names(Mmat_calib_study), causes, causes))

  va_deaths_calib = va_deaths

  pcalib_asarray = array(dim = c(K, nMCMC, nCause),
                         dimnames = list(names(Mmat_calib_study), NULL, causes))
  pcalib_postsumm_asarray = array(dim = c(K, 3, nCause),
                                  dimnames = list(names(Mmat_calib_study), c('postmean', 'lowcredI', 'upcredI'), causes))

  for(k in 1:K){

    donotcalib_study_asmat[k,] =
      donotcalib_tomodel_asmat[k,] =
      causes %in% donotcalib_study[[k]]


    # learn more causes not to calibrate
    if(donotcalib_type=="learn"){

      donotcalib_study_learn_k = apply(Mmat_calib_study[[k]]/rowSums(Mmat_calib_study[[k]]), 2,
                                       FUN = function(v){

                                         # mean(abs(v - mean(v)))
                                         diff(range(v))<=nocalib.threshold

                                       })
      donotcalib_tomodel_asmat[k,] = (donotcalib_study_asmat[k,]|donotcalib_study_learn_k)

    }


    ## calibration path correction ----
    Mmat_calib_input_asarray[k,,] = Mmat_calib_input[[k]]
    Mmat_calib_study_asarray[k,,] = Mmat_calib_study[[k]]

    if(sum(!donotcalib_tomodel_asmat[k,])<=1){

      ### no calibration ----

      calibrated[k] = FALSE

      Mmat_calib_tomodel_asarray[k,,] = Mmat_calib_study_asarray[k,,]

      #### calibration output ----
      MCMCout_k = list('p_calib' = matrix(data = puncalib[k,],
                                          nrow = nMCMC, ncol = nCause,
                                          byrow = TRUE),
                       # 'loglik' = NULL,
                       # 'mcmc.diagnostic' = NULL,
                       'p_calib_postsumm' = rbind(puncalib[k,],
                                                  puncalib[k,],
                                                  puncalib[k,]))

      # posterior summary of calibrated estimate
      colnames(MCMCout_k$p_calib) = causes
      rownames(MCMCout_k$p_calib_postsumm) = c('postmean', 'lowcredI', 'upcredI')

    }else{

      ### calibration ----

      calibrated[k] = TRUE

      idtocalib_k = which(!donotcalib_tomodel_asmat[k,])
      nTocalib_k = length(idtocalib_k)


      Mmat_calib_tomodel_asarray[k,,] = Mmat_calib_study_asarray[k,,]
      puncalib_k_sub = puncalib[k,!donotcalib_tomodel_asmat[k,]]/sum(puncalib[k,!donotcalib_tomodel_asmat[k,]])

      if(!path_correction){

        #### no path correction ----

        lambda_calibpath[k] = 0

      }else{

        #### path correction ----

        Mmat_calib_tomodel_sub_k = Mmat_calib_study_asarray[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]]
        Mmat_calib_tomodel_sub_shape_k = rowSums(Mmat_calib_tomodel_sub_k)
        Mmat_calib_tomodel_sub_mean_k = Mmat_calib_tomodel_sub_k/Mmat_calib_tomodel_sub_shape_k

        count_lambda_calibpath_k = 0
        got_it_k = FALSE
        while(!got_it_k){

          count_lambda_calibpath_k = count_lambda_calibpath_k + 1
          if(count_lambda_calibpath_k==1){

            lambda_calibpath[k] = .99

          }else{

            lambda_calibpath[k] = lambda_calibpath[k] - .01

          }

          # shrink towards identity
          Mmat_calib_tomodel_sub_mean_k_lambda =
            lambda_calibpath[k]*diag(nrow(Mmat_calib_tomodel_sub_mean_k)) +
            (1-lambda_calibpath[k])*Mmat_calib_tomodel_sub_mean_k

          # solving calibration eq
          puncalib_k_sub_lambda = as.numeric(MASS::ginv(t(Mmat_calib_tomodel_sub_mean_k_lambda)) %*%
                                               as.matrix(puncalib_k_sub))

          # pcalib_lambda = puncalib
          # pcalib_lambda[!donotcalib_tomodel_asmat[k,]] = (1-sum(puncalib[donotcalib_tomodel_asmat[k,]]))*pcalib_lambda

          # checking if within simplex
          outside_simplex_k = any(puncalib_k_sub_lambda<0)|any(puncalib_k_sub_lambda>1)
          got_it_k = outside_simplex_k|isTRUE(all.equal(lambda_calibpath[k], 0))

        }

        if(outside_simplex_k){

          lambda_calibpath[k] = min(lambda_calibpath[k] + .01, .99)

        }

        # shrink towards identity
        Mmat_calib_tomodel_sub_mean_k_lambda =
          lambda_calibpath[k]*diag(nrow(Mmat_calib_tomodel_sub_mean_k)) +
          (1-lambda_calibpath[k])*Mmat_calib_tomodel_sub_mean_k

        Mmat_calib_tomodel_asarray[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]] =
          Mmat_calib_tomodel_sub_shape_k*Mmat_calib_tomodel_sub_mean_k_lambda

      }

      ### calibration output ----

      # if(shrink_towards=="calib"){
      #
      #   p0 = project_simplex(MASS::ginv(t(Mmat_calib_study_asarray[k,,]/rowSums(Mmat_calib_study_asarray[k,,]))) %*% puncalib[k,])
      #
      # }else if(shrink_towards=="uncalib"){
      #
      #   p0 = puncalib[k,]
      #
      # }
      p0 = puncalib[k,]

      ### stan fit ----
      # print(list('nCause' = nCause,
      #            'nAlgo' = 1,
      #            'aj' = va_deaths[k,, drop = FALSE],
      #            'nTocalib' = as.array(nTocalib_k),
      #            'idtocalib' = idtocalib_k,
      #            'nCumtocalib' = c(0, cumsum(nTocalib_k)),
      #            'p0' = as.numeric(p0),
      #            'Mmatprior_asDirich' = Mmat_calib_tomodel_asarray[k,,, drop = FALSE],
      #            'pss' = shrink_strength,
      #            'lambda' = lambda_eBayes,
      #            'Imat' = diag(nCause)
      # ))
      # print(lambda_calibpath)
      stanfit_k = rstan::sampling(get_stan_seqcalib(),
                                  # pars = c('p_calib', 'loglik'),
                                  # include = TRUE,
                                  data = list('nCause' = nCause,
                                              'nAlgo' = 1,
                                              'aj' = va_deaths[k,, drop = FALSE],
                                              'nTocalib' = as.array(nTocalib_k),
                                              'idtocalib' = idtocalib_k,
                                              'nCumtocalib' = c(0, cumsum(nTocalib_k)),
                                              'p0' = as.numeric(p0),
                                              'Mmatprior_asDirich' = Mmat_calib_tomodel_asarray[k,,, drop = FALSE],
                                              'pss' = shrink_strength,
                                              'lambda' = lambda_eBayes,
                                              'Imat' = diag(nCause)
                                  ),
                                  chains = nChain, cores = nCore,
                                  iter = nBurn + nMCMC*nThin, warmup = nBurn, thin = nThin,
                                  control = list('adapt_delta' = adapt_delta_stan),
                                  seed = seed,
                                  refresh = refresh.stan#,
                                  # init = list(list('Mmat' = Mmat.init,
                                  #                  'p_calib' = puncalib))
      )

      MCMCout_k = c(list("stanfit" = stanfit_k), rstan::extract(stanfit_k)) # MCMC output
      # MCMCout_k$calibrated = calibrated_k
      # MCMCout_k$lambda = lambda_k

      ### mcmc diagnostic ----
      # max Rhat
      max_Rhat_k = max(apply(X = MCMCout_k$p_calib, 2,
                             FUN = function(v){

                               rstan::Rhat(v)

                             }))

      # min bulk ESS
      min_ess_bulk_k = min(apply(X = MCMCout_k$p_calib, 2,
                                 FUN = function(v){

                                   rstan::ess_bulk(v)

                                 }))/nMCMC

      # mcmc diagnostic summary
      MCMCout_k$mcmc.diagnostic = c('max_Rhat' = max_Rhat_k, 'min_ess_bulk' = min_ess_bulk_k,
                                    'num_divergent' = rstan::get_num_divergent(stanfit_k),
                                    'num_max_treedepth' = rstan::get_num_max_treedepth(stanfit_k))

      if(verbose){

        message("MCMC Diagnostic:")
        print(round(MCMCout_k$mcmc.diagnostic, 3))
        message("\n")

      }

      ### calibrated csmf for all causes ----
      # print(head(MCMCout$p_calib))
      if(sum(donotcalib_tomodel_asmat[k,])>0){

        # csmf
        p_calib_out_k = matrix(data = puncalib[k,],
                               nrow = nMCMC, ncol = nCause,
                               byrow = TRUE)
        # print(dim(p_calib_out[,donotcalib_touse, drop = F]))
        # p_calib_out[,donotcalib_touse] = matrix(data = puncalib[donotcalib_touse],
        #                                         nrow = nMCMC, ncol = sum(donotcalib_touse),
        #                                         byrow = T)
        p_calib_out_k[,!donotcalib_tomodel_asmat[k,]] =
          (1 - sum(puncalib[k,donotcalib_tomodel_asmat[k,]]))*
          (MCMCout_k$p_calib[,!donotcalib_tomodel_asmat[k,]]/rowSums(MCMCout_k$p_calib[,!donotcalib_tomodel_asmat[k,]]))
        MCMCout_k$p_calib = p_calib_out_k

      }
      colnames(MCMCout_k$p_calib) = causes
      # MCMCout$p_calib.postmean = colMeans(MCMCout$p_calib)
      # print(head(MCMCout$p_calib))

      # posterior summary of calibrated estimate
      MCMCout_k$p_calib_postsumm = apply(MCMCout_k$p_calib, 2,
                                         FUN = function(v){

                                           c(mean(v),
                                             quantile(x = v, probs = c(.025, .975)))

                                         })
      rownames(MCMCout_k$p_calib_postsumm) = c('postmean', 'lowcredI', 'upcredI')

    }



    ## MCMC output ----
    calibout[[k]] = MCMCout_k


    ## calibrated number of deaths ----
    va_deaths_calib_k = va_deaths[k,]
    if(calibrated[k]){

      va_deaths_calib_k[!donotcalib_tomodel_asmat[k,]] =
        round(colMeans(sum(va_deaths[k,!donotcalib_tomodel_asmat[k,]])*
                         (MCMCout_k$p_calib[,!donotcalib_tomodel_asmat[k,]]/(1 - sum(puncalib[k,donotcalib_tomodel_asmat[k,]])))))

      # exactly match total number of deaths
      if(isFALSE(all.equal(sum(va_deaths_calib_k), sum(va_deaths[k,])))){

        (adjust.amnt_k = sum(va_deaths_calib_k) - sum(va_deaths[k,]))

        adjust.vec_k = rep(0, nCause)
        (adjust.vec_k[!donotcalib_tomodel_asmat[k,]] = rep(floor(abs(adjust.amnt_k)/sum(!donotcalib_tomodel_asmat[k,])),
                                                           sum(!donotcalib_tomodel_asmat[k,])))

        id.extra.adjust_k = head(intersect(order(va_deaths_calib_k, decreasing = TRUE),
                                           which(!donotcalib_tomodel_asmat[k,])),
                                 n = abs(adjust.amnt_k) %% sum(!donotcalib_tomodel_asmat[k,]))
        adjust.vec_k[id.extra.adjust_k] = adjust.vec_k[id.extra.adjust_k] + 1
        adjust.vec_k

        if(adjust.amnt_k>0){

          va_deaths_calib_k = va_deaths_calib_k - adjust.vec_k

        }else{

          va_deaths_calib_k = va_deaths_calib_k + adjust.vec_k

        }

      }

    }

    va_deaths_calib[k,] = va_deaths_calib_k
    pcalib_asarray[k,,] = MCMCout_k$p_calib
    pcalib_postsumm_asarray[k,,] = MCMCout_k$p_calib_postsumm

  }# ending calibration for each algorithm


  # ensemble calibration  ----
  if(K==1){

    if(is.null(ensemble)){

      ensemble = FALSE

    }else{

      if(ensemble){

        ensemble = FALSE
        if(verbose){

          message("Nothing to ensemble. 'va_data' is provided for one algorithm provided.")
          stop("")

        }

      }

    }

  }else if(K>1){

    # defaulting to ensemble if multiple algorithms
    if(is.null(ensemble)) ensemble = TRUE

  }


  # performing ensemble calibration
  if(!ensemble){

    # output list
    input.list.now = as.list(environment())
    input.list = c(input.list.now[names(input.list)],
                   "K" = K, "nCause" = nCause, "causes" = causes)

    output = list("calib_MCMCout" = calibout,
                  "p_uncalib" = puncalib,
                  "p_calib" = pcalib_asarray,
                  "pcalib_postsumm" = pcalib_postsumm_asarray,
                  "va_deaths_uncalib" = va_deaths,
                  "va_deaths_calib_algo" = va_deaths_calib,
                  'Mmat_input' = Mmat_calib_input_asarray,
                  'Mmat_study' = Mmat_calib_study_asarray,
                  'Mmat_tomodel' = Mmat_calib_tomodel_asarray,
                  'donotcalib_study' = donotcalib_study_asmat,
                  'donotcalib_tomodel' = donotcalib_tomodel_asmat,
                  'calibrated' = calibrated,
                  'lambda_calibpath' = lambda_calibpath,
                  'input' = input.list)

  }else{

    # ensemble uncalibrated csmf
    puncalib = rbind(puncalib, colSums(va_deaths)/sum(va_deaths))

    donotcalib_ens = donotcalib_tomodel_asmat[1,]
    for(k in 2:K){

      donotcalib_ens = donotcalib_ens&donotcalib_tomodel_asmat[k,]

    }
    donotcalib_tomodel_asmat = rbind(donotcalib_tomodel_asmat,
                                     donotcalib_ens)

    rownames(puncalib) =
      rownames(donotcalib_tomodel_asmat) = c(names(va_unlabeled), 'ensemble')

    idtocalib_ens = nTocalib_ens = NULL
    for(k in 1:K){

      idtocalib_ens_k = which(!donotcalib_tomodel_asmat[k,])
      idtocalib_ens = c(idtocalib_ens, idtocalib_ens_k)
      nTocalib_ens = c(nTocalib_ens, length(idtocalib_ens_k))

    }

    calibrated = c(calibrated,
                   'ensemble' = (sum(!donotcalib_tomodel_asmat[K+1,])>1))
    if(!calibrated[K+1]){

      MCMCout_ens = list('p_calib' = matrix(data = puncalib[K+1,],
                                            nrow = nMCMC, ncol = nCause,
                                            byrow = TRUE),
                         # 'loglik' = NULL,
                         # "calibrated" = calibrated_ens,
                         # 'mcmc.diagnostic' = NULL,
                         'p_calib_postsumm' = rbind(puncalib[K+1,],
                                                    puncalib[K+1,],
                                                    puncalib[K+1,]))

      # posterior summary of calibrated estimate
      colnames(MCMCout_ens$p_calib) = causes
      rownames(MCMCout_ens$p_calib_postsumm) = c('postmean', 'lowcredI', 'upcredI')

    }else{

      # if(shrink_towards=="calib"){
      #
      #   M_neq = matrix(0, K, K)
      #   b_neq = numeric(K)
      #   for(k in 1:K){
      #
      #     Mtemp = diag(nCause)
      #     Mtemp[!donotcalib_tomodel_asmat[K+1,],!donotcalib_tomodel_asmat[K+1,]] =
      #       Mmat_calib_tomodel_asarray[k,!donotcalib_tomodel_asmat[K+1,],!donotcalib_tomodel_asmat[K+1,]]/rowSums(Mmat_calib_tomodel_asarray[k,!donotcalib_tomodel_asmat[K+1,],!donotcalib_tomodel_asmat[K+1,]])
      #
      #     M_neq = M_neq + tcrossprod(Mtemp)
      #     b_neq = b_neq + (Mtemp%*%puncalib[k,])
      #
      #   }
      #
      #   p0 = project_simplex(MASS::ginv(M_neq) %*% b_neq)
      #
      # }else if(shrink_towards=="uncalib"){
      #
      #   p0 = puncalib[K+1,]
      #
      # }
      p0 = puncalib[K+1,]

      ## stan fit ----
      stanfit_ens = rstan::sampling(get_stan_seqcalib(),
                                    # pars = c('p_calib', 'loglik'),
                                    # include = TRUE,
                                    data = list('nCause' = nCause,
                                                'nAlgo' = K,
                                                'aj' = va_deaths,
                                                'nTocalib' = nTocalib_ens,
                                                'idtocalib' = idtocalib_ens,
                                                'nCumtocalib' = c(0, cumsum(nTocalib_ens)),
                                                'p0' = as.numeric(p0),
                                                'Mmatprior_asDirich' = Mmat_calib_tomodel_asarray,
                                                'pss' = shrink_strength,
                                                'lambda' = lambda_eBayes,
                                                'Imat' = diag(nCause)
                                    ),
                                    chains = nChain, cores = nCore,
                                    iter = nBurn + nMCMC*nThin, warmup = nBurn, thin = nThin,
                                    control = list('adapt_delta' = adapt_delta_stan),
                                    seed = seed,
                                    refresh = refresh.stan#,
                                    # init = list(list('Mmat' = Mmat.init,
                                    #                  'p_calib' = puncalib))
      )

      MCMCout_ens = c(list("stanfit" = stanfit_ens),
                      rstan::extract(stanfit_ens)) # MCMC output
      # MCMCout_ens$calibrated = calibrated_ens

      ## mcmc diagnostic ----
      # max Rhat
      max_Rhat_ens = max(apply(X = MCMCout_ens$p_calib, 2,
                               FUN = function(v){

                                 rstan::Rhat(v)

                               }))

      # min bulk ESS
      min_ess_bulk_ens = min(apply(X = MCMCout_ens$p_calib, 2,
                                   FUN = function(v){

                                     rstan::ess_bulk(v)

                                   }))/nMCMC

      # mcmc diagnostic summary
      MCMCout_ens$mcmc.diagnostic = c('max_Rhat' = max_Rhat_ens, 'min_ess_bulk' = min_ess_bulk_ens,
                                      'num_divergent' = rstan::get_num_divergent(stanfit_ens),
                                      'num_max_treedepth' = rstan::get_num_max_treedepth(stanfit_ens))

      if(verbose){

        message("MCMC Diagnostic:")
        print(round(MCMCout_k$mcmc.diagnostic, 2))
        # message("\n")

      }

      ## calibrated posterior for all causes ----
      # print(head(MCMCout$p_calib))
      if(sum(donotcalib_tomodel_asmat[K+1,])>0){

        # csmf
        p_calib_out_ens = matrix(data = puncalib[K+1,],
                                 nrow = nMCMC, ncol = nCause,
                                 byrow = TRUE)
        # print(dim(p_calib_out[,donotcalib_touse, drop = F]))
        # p_calib_out[,donotcalib_touse] = matrix(data = puncalib[donotcalib_touse],
        #                                         nrow = nMCMC, ncol = sum(donotcalib_touse),
        #                                         byrow = T)
        p_calib_out_ens[,!donotcalib_tomodel_asmat[K+1,]] = (1 - sum(puncalib[K+1,donotcalib_tomodel_asmat[K+1,]]))*
          (MCMCout_ens$p_calib[,!donotcalib_tomodel_asmat[K+1,]]/rowSums(MCMCout_ens$p_calib[,!donotcalib_tomodel_asmat[K+1,]]))
        MCMCout_ens$p_calib = p_calib_out_ens

      }
      colnames(MCMCout_ens$p_calib) = causes
      # MCMCout$p_calib.postmean = colMeans(MCMCout$p_calib)
      # print(head(MCMCout$p_calib))

      # posterior summary of calibrated estimate
      MCMCout_ens$p_calib_postsumm = apply(MCMCout_ens$p_calib, 2,
                                           FUN = function(v){

                                             c(mean(v),
                                               quantile(x = v, probs = c(.025, .975)))

                                           })
      rownames(MCMCout_ens$p_calib_postsumm) = c('postmean', 'lowcredI', 'upcredI')

    }
    # print(1)

    ## calibrated number of deaths ----
    va_deaths_ens = va_deaths
    for(k in 1:K){

      va_deaths_ens_k = va_deaths[k,]

      if(calibrated[K+1]){

        # print(donotcalib_tomodel_asmat[K+1,])
        # print(va_deaths[k,!donotcalib_tomodel_asmat[K+1,]])
        va_deaths_ens_k[!donotcalib_tomodel_asmat[K+1,]] = round(colMeans(sum(va_deaths[k,!donotcalib_tomodel_asmat[K+1,]])*
                                                                            (MCMCout_ens$p_calib[,!donotcalib_tomodel_asmat[K+1,]]/(1 - sum(puncalib[K+1,donotcalib_tomodel_asmat[K+1,]])))))

        # exactly match total number of deaths
        if(isFALSE(all.equal(sum(va_deaths_ens_k), sum(va_deaths[k,])))){

          (adjust.amnt_ens_k = sum(va_deaths_ens_k) - sum(va_deaths[k,]))

          adjust.vec_ens_k = rep(0, nCause)
          (adjust.vec_ens_k[!donotcalib_tomodel_asmat[K+1,]] = rep(floor(abs(adjust.amnt_ens_k)/sum(!donotcalib_tomodel_asmat[K+1,])),
                                                                   sum(!donotcalib_tomodel_asmat[K+1,])))

          id.extra.adjust_ens_k = head(intersect(order(va_deaths_ens_k, decreasing = TRUE),
                                                 which(!donotcalib_tomodel_asmat[K+1,])),
                                       n = abs(adjust.amnt_ens_k) %% sum(!donotcalib_tomodel_asmat[K+1,]))
          adjust.vec_ens_k[id.extra.adjust_ens_k] = adjust.vec_ens_k[id.extra.adjust_ens_k] + 1
          adjust.vec_ens_k

          if(adjust.amnt_ens_k>0){

            va_deaths_ens_k = va_deaths_ens_k - adjust.vec_ens_k

          }else{

            va_deaths_ens_k = va_deaths_ens_k + adjust.vec_ens_k

          }

        }

      }

      va_deaths_ens[k,] = va_deaths_ens_k
      # print(k)

    }


    # ensemble calibration output
    calibout = c(calibout, list('ensemble' = MCMCout_ens))

    # puncalib = rbind(puncalib, puncalib[K+1,])
    # rownames(puncalib) = names(calibout)
    # colnames(puncalib) = causes


    pcalib_asarray_wens = array(dim = c(K+1, nMCMC, nCause),
                                dimnames = list(rownames(puncalib), NULL, causes))
    pcalib_asarray_wens[1:K,,] = pcalib_asarray
    pcalib_asarray_wens[K+1,,] = MCMCout_ens$p_calib

    pcalib_postsumm_asarray_wens = array(dim = c(K+1, 3, nCause),
                                         dimnames = list(rownames(puncalib),
                                                         dimnames(pcalib_postsumm_asarray)[[2]],
                                                         causes))
    pcalib_postsumm_asarray_wens[1:K,,] = pcalib_postsumm_asarray
    pcalib_postsumm_asarray_wens[K+1,,] = MCMCout_ens$p_calib_postsumm

    # donotcalib_wens = rbind(donotcalib_tomodel_asmat, donotcalib_tomodel_asmat[K+1,])
    # rownames(donotcalib_wens) = names(calibout)
    # colnames(donotcalib_wens) = causes


    # output list
    input.list.now = as.list(environment())
    input.list = input.list.now[names(input.list)]

    output = list("calib_MCMCout" = calibout,
                  "p_uncalib" = puncalib,
                  "p_calib" = pcalib_asarray_wens,
                  "pcalib_postsumm" = pcalib_postsumm_asarray_wens,
                  "va_deaths_uncalib" = va_deaths,
                  "va_deaths_calib_algo" = va_deaths_calib,
                  "va_deaths_calib_ensemble" = va_deaths_ens,
                  'Mmat_input' = Mmat_calib_input_asarray,
                  'Mmat_study' = Mmat_calib_study_asarray,
                  'Mmat_tomodel' = Mmat_calib_tomodel_asarray,
                  'donotcalib_study' = donotcalib_study_asmat,
                  'donotcalib_tomodel' = donotcalib_tomodel_asmat,
                  'calibrated' = calibrated,
                  'lambda_calibpath' = lambda_calibpath,
                  'input' = input.list)

    # print(dim(Mmat_input_asarray))
    # print(dim(Mmat_asarray))
    # print(dim(output$Mmat.fixed_input))
    # print(dim(output$Mmat.fixed))

    # end ensemble

  }

  # print("calibrated succesfully")



  # comparison plots ----
  if(plot_it){

    ## input misclassification ----
    # print(round(100*output$Mmat.fixed_input[1,,]))
    Mmat_toplot_input = output$Mmat_input
    # print(dim(Mmat_toplot_input))
    for(k in 1:dim(Mmat_toplot_input)[1]){

      Mmat_toplot_input[k,,] = round(100*(output$Mmat_input[k,,]/rowSums(output$Mmat_input[k,,])))

      for(i in 1:dim(Mmat_toplot_input)[2]){

        if(!any(is.nan(Mmat_toplot_input[k,i,]))){

          nonzerocauseid_ki = which.max(Mmat_toplot_input[k,i,])
          Mmat_toplot_input[k,i,nonzerocauseid_ki] = 100 - sum(Mmat_toplot_input[k,i,-nonzerocauseid_ki])

        }

      }

      # Mmat_toplot_input[k,donotcalib_tomodel_asmat[k,],] =
      #   Mmat_toplot_input[k,,donotcalib_tomodel_asmat[k,]] = NA

    }

    plotdf_Mmat_input = reshape2::melt(Mmat_toplot_input)
    head(plotdf_Mmat_input)
    value.labels_Mmat_input = plotdf_Mmat_input$value

    plotdf_Mmat_input$Var1 = factor(x = plotdf_Mmat_input$Var1, levels = dimnames(Mmat_toplot_input)[[1]])
    plotdf_Mmat_input$Var2 = factor(x = plotdf_Mmat_input$Var2, levels = rev(dimnames(output$Mmat_input)[[2]]))
    plotdf_Mmat_input$Var3 = factor(x = plotdf_Mmat_input$Var3, levels = dimnames(output$Mmat_input)[[2]])

    plotdf_Mmat_input$diag = plotdf_Mmat_input$Var2==plotdf_Mmat_input$Var3
    plotdf_Mmat_input$diag[!plotdf_Mmat_input$diag] = NA
    # print(head(plotdf_Mmat_input))
    # print(K)

    ggplot2_Mmat_input =
      ggplot2::ggplot(plotdf_Mmat_input, ggplot2::aes(Var3, Var2, fill = value)) +
      ggplot2::geom_tile(color="white", linewidth=.5) +
      ggplot2::geom_tile(data = plotdf_Mmat_input[!is.na(plotdf_Mmat_input$diag), ],
                         ggplot2::aes(Var3, Var2, fill = value, color = diag), linewidth = .7) +
      ggplot2::scale_color_manual(guide = "none", values = c(`TRUE` = "blue3")) +
      ggplot2::geom_text(ggplot2::aes(Var3, Var2, label = value.labels_Mmat_input,
                                      size = value^(1/2)),
                         color = "black",
                         fontface = 'bold') +
      # ggplot2::scale_size(range = c(0, 8)) +
      ggplot2::scale_fill_gradient(low="white", high="red3",
                                   breaks = seq(0, 100, 20), limits = c(0,100),
                                   name = 'Classification Percentage') +
      ggplot2::facet_grid(.~Var1) +
      ggplot2::theme(
        plot.title = ggplot2::element_text(face = "bold"),
        plot.subtitle = ggplot2::element_text(),
        # axis.title.x = ggplot2::element_blank(),
        axis.title.y = ggplot2::element_text(margin = ggplot2::margin(t = 0, r = 10, b = 0, l = 0)),
        axis.text.x = ggplot2::element_text(color = "black",
                                            angle = 30, hjust = 1, vjust = 1),
        axis.text.y = ggplot2::element_text(color = "black"),
        # axis.ticks.x = ggplot2::element_blank(),
        # axis.ticks.length.x = unit(.2, "cm"),
        # axis.ticks.y = ggplot2::element_line(linewidth = .5),
        # axis.ticks.length.y = ggplot2::unit(.2, "cm"),
        panel.background = ggplot2::element_blank(),
        panel.border = ggplot2::element_rect(color='black', linetype = "solid",
                                             fill = NA, linewidth = 1),
        panel.grid.major = ggplot2::element_line(linewidth = 0.2, linetype = 'solid',
                                                 colour = "grey90"),
        panel.grid.minor = ggplot2::element_line(linewidth = 0.2, linetype = 'solid',
                                                 colour = "grey90"),
        strip.text.x = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.text.y = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.background = ggplot2::element_rect(color="black", linewidth=1),
        legend.title = ggplot2::element_blank(),
        # legend.key.width = ggplot2::unit(.75, "cm"),
        # legend.key.height = ggplot2::unit(.75, "cm"),
        # legend.key.size = ggplot2::unit(.5, "cm"),
        # legend.spacing.x = ggplot2::unit(.5, 'cm'),
        # legend.text=ggplot2::element_text(size=22),
        legend.text=ggplot2::element_text(size=12),
        legend.position = 'none'
      )
    # print(ggplot2_Mmat_input)


    ## study-specific misclassification ----
    # print(round(100*output$Mmat.fixed_study[1,,]))
    Mmat_toplot_study = output$Mmat_study
    # print(dim(Mmat_toplot_study))
    for(k in 1:dim(Mmat_toplot_study)[1]){

      if(!output$calibrated[k]){

        Mmat_toplot_study[k,,] = NA*Mmat_toplot_study[k,,]

      }else{

        Mmat_toplot_study[k,,] = diag(nCause)
        Mmat_toplot_study[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]] =
          round(100*output$Mmat_study[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]]/rowSums(output$Mmat_study[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]]))

        for(i in 1:dim(Mmat_toplot_study)[2]){

          if(!any(is.nan(Mmat_toplot_study[k,i,]))){

            nonzerocauseid_ki = which.max(Mmat_toplot_study[k,i,])
            Mmat_toplot_study[k,i,nonzerocauseid_ki] = 100 - sum(Mmat_toplot_study[k,i,-nonzerocauseid_ki])

          }

        }

        Mmat_toplot_study[k,donotcalib_tomodel_asmat[k,],] =
          Mmat_toplot_study[k,,donotcalib_tomodel_asmat[k,]] = NA

      }

    }

    plotdf_Mmat_study = reshape2::melt(Mmat_toplot_study)
    head(plotdf_Mmat_study)
    value.labels_Mmat_study = plotdf_Mmat_study$value

    plotdf_Mmat_study$Var1 = factor(x = plotdf_Mmat_study$Var1, levels = dimnames(Mmat_toplot_study)[[1]])
    plotdf_Mmat_study$Var2 = factor(x = plotdf_Mmat_study$Var2, levels = rev(causes))
    plotdf_Mmat_study$Var3 = factor(x = plotdf_Mmat_study$Var3, levels = causes)

    plotdf_Mmat_study$diag = plotdf_Mmat_study$Var2==plotdf_Mmat_study$Var3
    plotdf_Mmat_study$diag[!plotdf_Mmat_study$diag] = NA
    # print(head(plotdf_Mmat_study))
    # print(K)

    ggplot2_Mmat_study =
      ggplot2::ggplot(plotdf_Mmat_study, ggplot2::aes(Var3, Var2, fill = value)) +
      ggplot2::geom_tile(color="white", linewidth=.5) +
      ggplot2::geom_tile(data = plotdf_Mmat_study[!is.na(plotdf_Mmat_study$diag), ],
                         ggplot2::aes(Var3, Var2, fill = value, color = diag), linewidth = .7) +
      ggplot2::scale_color_manual(guide = "none", values = c(`TRUE` = "blue3")) +
      ggplot2::geom_text(ggplot2::aes(Var3, Var2, label = value.labels_Mmat_study,
                                      size = value^(1/2)),
                         color = "black",
                         fontface = 'bold') +
      # ggplot2::scale_size(range = c(0, 8)) +
      ggplot2::scale_fill_gradient(low="white", high="red3",
                                   breaks = seq(0, 100, 20), limits = c(0,100),
                                   name = 'Classification Percentage') +
      ggplot2::facet_grid(.~Var1) +
      ggplot2::theme(
        plot.title = ggplot2::element_text(face = "bold"),
        plot.subtitle = ggplot2::element_text(),
        # axis.title.x = ggplot2::element_blank(),
        axis.title.y = ggplot2::element_text(margin = ggplot2::margin(t = 0, r = 10, b = 0, l = 0)),
        axis.text.x = ggplot2::element_text(color = "black",
                                            angle = 30, hjust = 1, vjust = 1),
        axis.text.y = ggplot2::element_text(color = "black"),
        # axis.ticks.x = ggplot2::element_blank(),
        # axis.ticks.length.x = unit(.2, "cm"),
        # axis.ticks.y = ggplot2::element_line(linewidth = .5),
        # axis.ticks.length.y = ggplot2::unit(.2, "cm"),
        panel.background = ggplot2::element_blank(),
        panel.border = ggplot2::element_rect(color='black', linetype = "solid",
                                             fill = NA, linewidth = 1),
        panel.grid.major = ggplot2::element_line(linewidth = 0.2, linetype = 'solid',
                                                 colour = "grey90"),
        panel.grid.minor = ggplot2::element_line(linewidth = 0.2, linetype = 'solid',
                                                 colour = "grey90"),
        strip.text.x = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.text.y = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.background = ggplot2::element_rect(color="black", linewidth=1),
        legend.title = ggplot2::element_blank(),
        # legend.key.width = ggplot2::unit(.75, "cm"),
        # legend.key.height = ggplot2::unit(.75, "cm"),
        # legend.key.size = ggplot2::unit(.5, "cm"),
        # legend.spacing.x = ggplot2::unit(.5, 'cm'),
        # legend.text=ggplot2::element_text(size=22),
        legend.text=ggplot2::element_text(size=12),
        legend.position = 'none'
      )
    # print(ggplot2_Mmat_study)


    ## misclassification used for calibration ----
    # print(round(100*output$Mmat.fixed_tomodel[1,,]))
    Mmat_toplot_tomodel = output$Mmat_tomodel
    # print(dim(Mmat_toplot_tomodel))
    for(k in 1:dim(Mmat_toplot_tomodel)[1]){

      if(!output$calibrated[k]){

        Mmat_toplot_tomodel[k,,] = NA*Mmat_toplot_tomodel[k,,]

      }else{

        Mmat_toplot_tomodel[k,,] = diag(nCause)
        Mmat_toplot_tomodel[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]] =
          round(100*output$Mmat_tomodel[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]]/rowSums(output$Mmat_tomodel[k,!donotcalib_tomodel_asmat[k,],!donotcalib_tomodel_asmat[k,]]))

        for(i in 1:dim(Mmat_toplot_tomodel)[2]){

          if(!any(is.nan(Mmat_toplot_tomodel[k,i,]))){

            nonzerocauseid_ki = which.max(Mmat_toplot_tomodel[k,i,])
            Mmat_toplot_tomodel[k,i,nonzerocauseid_ki] = 100 - sum(Mmat_toplot_tomodel[k,i,-nonzerocauseid_ki])

          }

        }

      }

      Mmat_toplot_tomodel[k,donotcalib_tomodel_asmat[k,],] =
        Mmat_toplot_tomodel[k,,donotcalib_tomodel_asmat[k,]] = NA

    }

    plotdf_Mmat_tomodel = reshape2::melt(Mmat_toplot_tomodel)
    head(plotdf_Mmat_tomodel)
    value.labels_Mmat_tomodel = plotdf_Mmat_tomodel$value

    plotdf_Mmat_tomodel$Var1 = factor(x = plotdf_Mmat_tomodel$Var1, levels = dimnames(Mmat_toplot_tomodel)[[1]])
    plotdf_Mmat_tomodel$Var2 = factor(x = plotdf_Mmat_tomodel$Var2, levels = rev(causes))
    plotdf_Mmat_tomodel$Var3 = factor(x = plotdf_Mmat_tomodel$Var3, levels = causes)

    plotdf_Mmat_tomodel$diag = plotdf_Mmat_tomodel$Var2==plotdf_Mmat_tomodel$Var3
    plotdf_Mmat_tomodel$diag[!plotdf_Mmat_tomodel$diag] = NA
    # print(head(plotdf_Mmat_tomodel))
    # print(K)

    ggplot2_Mmat_tomodel =
      ggplot2::ggplot(plotdf_Mmat_tomodel, ggplot2::aes(Var3, Var2, fill = value)) +
      ggplot2::geom_tile(color="white", linewidth=.5) +
      ggplot2::geom_tile(data = plotdf_Mmat_tomodel[!is.na(plotdf_Mmat_tomodel$diag), ],
                         ggplot2::aes(Var3, Var2, fill = value, color = diag), linewidth = .7) +
      ggplot2::scale_color_manual(guide = "none", values = c(`TRUE` = "blue3")) +
      ggplot2::geom_text(ggplot2::aes(Var3, Var2, label = value.labels_Mmat_tomodel,
                                      size = value^(1/2)),
                         color = "black",
                         fontface = 'bold') +
      # ggplot2::scale_size(range = c(0, 8)) +
      ggplot2::scale_fill_gradient(low="white", high="red3",
                                   breaks = seq(0, 100, 20), limits = c(0,100),
                                   name = 'Classification Percentage') +
      ggplot2::facet_grid(.~Var1) +
      ggplot2::theme(
        plot.title = ggplot2::element_text(face = "bold"),
        plot.subtitle = ggplot2::element_text(),
        # axis.title.x = ggplot2::element_blank(),
        axis.title.y = ggplot2::element_text(margin = ggplot2::margin(t = 0, r = 10, b = 0, l = 0)),
        axis.text.x = ggplot2::element_text(color = "black",
                                            angle = 30, hjust = 1, vjust = 1),
        axis.text.y = ggplot2::element_text(color = "black"),
        # axis.ticks.x = ggplot2::element_blank(),
        # axis.ticks.length.x = unit(.2, "cm"),
        # axis.ticks.y = ggplot2::element_line(linewidth = .5),
        # axis.ticks.length.y = ggplot2::unit(.2, "cm"),
        panel.background = ggplot2::element_blank(),
        panel.border = ggplot2::element_rect(color='black', linetype = "solid",
                                             fill = NA, linewidth = 1),
        panel.grid.major = ggplot2::element_line(linewidth = 0.2, linetype = 'solid',
                                                 colour = "grey90"),
        panel.grid.minor = ggplot2::element_line(linewidth = 0.2, linetype = 'solid',
                                                 colour = "grey90"),
        strip.text.x = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.text.y = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.background = ggplot2::element_rect(color="black", linewidth=1),
        legend.title = ggplot2::element_blank(),
        # legend.key.width = ggplot2::unit(.75, "cm"),
        # legend.key.height = ggplot2::unit(.75, "cm"),
        # legend.key.size = ggplot2::unit(.5, "cm"),
        # legend.spacing.x = ggplot2::unit(.5, 'cm'),
        # legend.text=ggplot2::element_text(size=22),
        legend.text=ggplot2::element_text(size=12),
        legend.position = 'none'
      )
    # print(ggplot2_Mmat_tomodel)



    ## calibrated vs uncalibrated csmf ----
    plotdf_pcalib = NULL
    for(k in 1:dim(output$pcalib_postsumm)[1]){

      plotdf_pcalib = rbind.data.frame(plotdf_pcalib,
                                       cbind.data.frame(rbind.data.frame(data.frame('causes' = dimnames(output$pcalib_postsumm)[[3]],
                                                                                    'value' = unname(output$pcalib_postsumm[k,'postmean',]),
                                                                                    'llim' = unname(output$pcalib_postsumm[k,'lowcredI',]),
                                                                                    'ulim' = unname(output$pcalib_postsumm[k,'upcredI',]),
                                                                                    'calib_type' = 'Calibrated'),
                                                                         data.frame('causes' = colnames(output$p_uncalib),
                                                                                    'value' = unname(output$p_uncalib[k,]),
                                                                                    'llim' = NA,
                                                                                    'ulim' = NA,
                                                                                    'calib_type' = 'Uncalibrated')),
                                                        'vaalgo' = (rownames(output$p_uncalib))[k]))

    }
    head(plotdf_pcalib)

    plotdf_pcalib$causes = factor(x = plotdf_pcalib$causes,
                                  levels = colnames(output$p_uncalib))
    plotdf_pcalib$calib_type = factor(x = plotdf_pcalib$calib_type,
                                      levels = c("Uncalibrated", "Calibrated"))
    plotdf_pcalib$vaalgo = factor(x = plotdf_pcalib$vaalgo,
                                  levels = rownames(output$p_uncalib))
    head(plotdf_pcalib)

    ggplot2_pcalib =
      ggplot2::ggplot(data = plotdf_pcalib) +
      ggplot2::facet_grid(.~vaalgo) +
      ggplot2::coord_cartesian(ylim = c(0,1), expand = TRUE, default = FALSE, clip = 'on') +
      ggplot2::geom_col(ggplot2::aes(x = causes, y = value,
                                     fill = calib_type, color = calib_type),
                        linewidth = .3, alpha = .5, #color = "black",
                        position = ggplot2::position_dodge(width = .6), width = 0.5) +
      ggplot2::geom_errorbar(ggplot2::aes(x = causes, ymin = llim, ymax = ulim,
                                          color = calib_type),
                             # color = "black",
                             width = .3, linewidth = 1,
                             position = ggplot2::position_dodge(width = .6)) +
      ggplot2::theme(
        plot.title = ggplot2::element_text(face = "bold"),
        axis.title.x = ggplot2::element_text(margin = ggplot2::margin(t = 10, r = 0, b = 0, l = 0)),
        axis.title.y = ggplot2::element_text(margin = ggplot2::margin(t = 0, r = 10, b = 0, l = 0)),
        axis.text.x = ggplot2::element_text(color = "black",
                                            angle = 30, hjust = 1, vjust = 1),
        axis.text.y = ggplot2::element_text(color = "black"),
        # axis.ticks.x = ggplot2::element_line(linewidth = .5),
        # axis.ticks.length.x = ggplot2::unit(.2, "cm"),
        # axis.ticks.y = ggplot2::element_line(linewidth = .5),
        # axis.ticks.length.y = ggplot2::unit(.2, "cm"),
        panel.background = ggplot2::element_blank(),
        panel.border = ggplot2::element_rect(color='black', linetype = "solid",
                                             fill = NA, linewidth = 1),
        panel.grid.major = ggplot2::element_line(linewidth = 0.5, linetype = 'solid',
                                                 colour = "grey90"),
        panel.grid.minor = ggplot2::element_line(linewidth = 0.5, linetype = 'solid',
                                                 colour = "grey90"),
        strip.text.x = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.text.y = ggplot2::element_text(
          size = 13,
          face = "bold"
        ),
        strip.background = ggplot2::element_rect(color="black", linewidth=1),
        legend.title = ggplot2::element_blank(),
        # legend.key.width = ggplot2::unit(1.5, "cm"),
        # legend.key.height = ggplot2::unit(.75, "cm"),
        # legend.key.spacing.x = ggplot2::unit(1, 'cm'),
        # legend.text=ggplot2::element_text(size=20),
        legend.text=ggplot2::element_text(size=12),
        legend.position = 'bottom'
      ) +
      ggplot2::guides(fill = ggplot2::guide_legend(nrow = 1, byrow=FALSE),
                      color = "none") +
      ggplot2::labs(title = 'Cause-Specific Mortality Fractions (CSMF)',
                    x = "Cause",
                    y = 'Estimate')
    # ggplot2_pcalib


    ## printing plots ----
    if(isTRUE(all.equal(K,1))){

      if(!is.null(studycause_map)){

        if(path_correction){

          ggplot2_Mmat_input = ggplot2_Mmat_input +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_study = ggplot2_Mmat_study +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Study-Specific",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          print((ggplot2_Mmat_input | ggplot2_Mmat_study | ggplot2_Mmat_tomodel | ggplot2_pcalib))

        }else{

          ggplot2_Mmat_input = ggplot2_Mmat_input +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          print((ggplot2_Mmat_input | ggplot2_Mmat_tomodel | ggplot2_pcalib))

        }

      }else{

        if(path_correction){

          ggplot2_Mmat_input = ggplot2_Mmat_input +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          print((ggplot2_Mmat_input | ggplot2_Mmat_tomodel | ggplot2_pcalib))

        }else{

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input and Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          print((ggplot2_Mmat_tomodel | ggplot2_pcalib))

        }

      }

    }else if(K>1){

      if(!is.null(studycause_map)){

        if(path_correction){

          ggplot2_Mmat_input = ggplot2_Mmat_input +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_study = ggplot2_Mmat_study +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Study-Specific",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          if(ensemble){

            print(((ggplot2_Mmat_input | NULL) + plot_layout(widths = c(K, 1))) / ((ggplot2_Mmat_study | NULL) + plot_layout(widths = c(K, 1))) / ((ggplot2_Mmat_tomodel | NULL) + plot_layout(widths = c(K, 1))) / ggplot2_pcalib)

          }else{

            print(ggplot2_Mmat_input / ggplot2_Mmat_study / ggplot2_Mmat_tomodel / ggplot2_pcalib)

          }

        }else{

          ggplot2_Mmat_input = ggplot2_Mmat_input +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          if(ensemble){

            print(((ggplot2_Mmat_input | NULL) + plot_layout(widths = c(K, 1))) / ((ggplot2_Mmat_tomodel | NULL) + plot_layout(widths = c(K, 1))) / ggplot2_pcalib)

          }else{

            print(ggplot2_Mmat_input / ggplot2_Mmat_tomodel / ggplot2_pcalib)

          }

        }

      }else{

        if(path_correction){

          ggplot2_Mmat_input = ggplot2_Mmat_input +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          if(ensemble){

            print(((ggplot2_Mmat_input | NULL) + plot_layout(widths = c(K, 1))) / ((ggplot2_Mmat_tomodel | NULL) + plot_layout(widths = c(K, 1))) / ggplot2_pcalib)

          }else{

            print(ggplot2_Mmat_input / ggplot2_Mmat_tomodel/ ggplot2_pcalib)

          }

        }else{

          ggplot2_Mmat_tomodel = ggplot2_Mmat_tomodel +
            ggplot2::labs(title = "Prior Mean of Misclassification Matrix",
                          subtitle = "Input and Used For Calibration",
                          x = 'VA Cause', y = 'CHAMPS Cause')

          if(ensemble){

            print(((ggplot2_Mmat_tomodel | NULL) + plot_layout(widths = c(K, 1))) / ggplot2_pcalib)

          }else{

            print(ggplot2_Mmat_tomodel / ggplot2_pcalib)

          }

        }

      }

    }

  }

  return(output)

}
