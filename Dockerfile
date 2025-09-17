FROM rocker/r-ver:4.3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the package files
COPY . /app
WORKDIR /app

# Install core dependencies first
RUN R -e "install.packages(c('Rcpp', 'ggplot2', 'plyr', 'stringr', 'jsonlite'), repos='https://cloud.r-project.org/')"

# Install remaining dependencies
RUN R -e "install.packages(c('rstan', 'patchwork', 'reshape2', 'LaplacesDemon'), repos='https://cloud.r-project.org/')"

# Install the vacalibration package
RUN R CMD INSTALL . --no-docs --no-multiarch --no-demo

# Run the example
CMD ["Rscript", "run_example.R"]