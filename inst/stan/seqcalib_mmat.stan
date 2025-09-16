
data {

  int<lower=2> nCause;
  int<lower=1> nAlgo;
  int<lower=0> aj[nAlgo,nCause];

  simplex[nCause] p0;
  simplex[nCause] Mmat_bysimplex[nAlgo,nCause];
  real<lower=0> pss;
  real<lower=0,upper=1> lambda;
  matrix[nCause,nCause] Imat;

}

parameters {

  simplex[nCause] p_calib;

}

transformed parameters {

  matrix[nCause,nCause] Mmat[nAlgo];

  for(k in 1:nAlgo){

    for(i in 1:nCause){

      Mmat[k][i,] = Mmat_bysimplex[k,i]';

    }

  }

}

model {

  target += dirichlet_lpdf(p_calib | 1 + nCause*pss*p0);

  for(k in 1:nAlgo){

    target += multinomial_lpmf(aj[k,] | ((lambda*Imat + (1-lambda)*Mmat[k])')*p_calib);

  }

}

generated quantities {

  vector[nAlgo] loglik;

  for(k in 1:nAlgo){

    loglik[k] = multinomial_lpmf(aj[k,] | ((lambda*Imat + (1-lambda)*Mmat[k])')*p_calib);

  }

}
