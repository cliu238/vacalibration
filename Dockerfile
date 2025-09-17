FROM rocker/r-ver:4.3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the package files
COPY . /app
WORKDIR /app

# Install R dependencies and the package
RUN R -e "options(repos='https://cloud.r-project.org/'); \
          install.packages(c('rstan', 'ggplot2', 'patchwork', 'reshape2', 'LaplacesDemon', 'MASS'), \
                          dependencies=TRUE)" && \
    R -e "install.packages('.', repos=NULL, type='source')"

# Run the example
CMD ["Rscript", "run_example.R"]