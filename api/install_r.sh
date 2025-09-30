#!/bin/bash
# R Installation script for Render.com deployment
# This script installs R and required packages

set -e

echo "Installing R and dependencies..."

# Install R
apt-get update
apt-get install -y r-base r-base-dev

# Install R packages needed for VA calibration
Rscript -e "install.packages(c('openVA', 'InSilicoVA', 'InterVA5', 'nbc4va'), repos='https://cloud.r-project.org/')"

echo "R installation complete!"
