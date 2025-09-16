
data {

  int<lower=2> nCause;
  int<lower=1> nAlgo;
  int<lower=0> aj[nAlgo,nCause];
  int<lower=2> nTocalib[nAlgo];
  int<lower=1,upper=nCause> idtocalib[sum(nTocalib)];
  int<lower=0,upper=(nAlgo*nCause)> nCumtocalib[nAlgo+1];

  simplex[nCause] p0;
  vector<lower=0>[nCause] Mmatprior_asDirich[nAlgo,nCause];
  real<lower=0> pss;
  real<lower=0,upper=1> lambda;
  matrix[nCause,nCause] Imat;

}

parameters {

  simplex[nCause] Mmat_bysimplex[nAlgo,nCause];
  simplex[nCause] p_calib;

}

transformed parameters {

  matrix[nCause,nCause] Mmat[nAlgo];

  for(k in 1:nAlgo){

    Mmat[k] = Imat;

    for(i in 1:nTocalib[k]){

      Mmat[k][idtocalib[nCumtocalib[k]+i],idtocalib[(nCumtocalib[k]+1):nCumtocalib[k+1]]] = ((Mmat_bysimplex[k,idtocalib[nCumtocalib[k]+i]])[idtocalib[(nCumtocalib[k]+1):nCumtocalib[k+1]]]/sum((Mmat_bysimplex[k, idtocalib[nCumtocalib[k]+i]])[idtocalib[(nCumtocalib[k]+1):nCumtocalib[k+1]]]))';

    }

  }

}

model {

  target += dirichlet_lpdf(p_calib | 1 + nCause*pss*p0);

  for(k in 1:nAlgo){

    for(i in 1:nCause){

      target += dirichlet_lpdf(Mmat_bysimplex[k,i] | Mmatprior_asDirich[k,i]);

    }

    target += multinomial_lpmf(aj[k,] | ((lambda*Imat + (1-lambda)*Mmat[k])')*p_calib);

  }

}

generated quantities {

  vector[nAlgo] loglik;

  for(k in 1:nAlgo){

    loglik[k] = multinomial_lpmf(aj[k,] | ((lambda*Imat + (1-lambda)*Mmat[k])')*p_calib);

  }

}
