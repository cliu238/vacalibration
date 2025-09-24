# How to Generate OpenVA Output for Calibration

This guide explains how to generate Verbal Autopsy (VA) outputs using the openVA package, which can then be used as input for the VA-Calibration API.

## Prerequisites

1. **R Installation**: Ensure R is installed (version 3.6+)
2. **openVA Package**: Install the openVA package in R:
```r
install.packages("openVA")
```

## Overview

The VA-Calibration API calibrates already-computed VA results. You must first run openVA algorithms separately, then provide those results to this API for calibration. The API does NOT run openVA itself.

## Supported OpenVA Algorithms

1. **InSilicoVA**: Bayesian probabilistic method
2. **InterVA (4 & 5)**: Probabilistic expert algorithm
3. **Tariff**: Machine learning approach
4. **NBC**: Naive Bayes Classifier

## Step-by-Step Guide

### 1. Prepare Your VA Data

Your input data should follow the WHO 2012 or WHO 2016 verbal autopsy questionnaire format.

```r
library(openVA)

# Load your VA data
# Example: va_data <- read.csv("your_va_data.csv")
# Or use example data:
data(RandomVA5, package = "openVA")
va_data <- RandomVA5
```

### 2. Run OpenVA Algorithms

#### Option A: InSilicoVA
```r
# Run InSilicoVA algorithm
fit_insilico <- codeVA(
  data = va_data,
  data.type = "WHO2016",  # or "WHO2012"
  model = "InSilicoVA",
  Nsim = 1000,  # Number of iterations
  auto.length = FALSE
)

# Extract top cause of death for each individual
top_cod_insilico <- getTopCOD(fit_insilico)
```

#### Option B: InterVA5
```r
# Run InterVA5 algorithm
fit_interva <- codeVA(
  data = va_data,
  data.type = "WHO2016",
  model = "InterVA",
  version = "5"
)

# Extract top cause
top_cod_interva <- getTopCOD(fit_interva)
```

#### Option C: Tariff
```r
# Run Tariff algorithm
fit_tariff <- codeVA(
  data = va_data,
  data.type = "WHO2016",
  model = "Tariff"
)

# Extract top cause
top_cod_tariff <- getTopCOD(fit_tariff)
```

### 3. Format Results for Calibration API

The calibration API expects VA results in JSON format with specific structure:

#### For Individual Cause Assignments
```r
# Convert to API format
library(jsonlite)

# Create data frame with required structure
api_input <- data.frame(
  id = rownames(top_cod_insilico),
  cause = top_cod_insilico$cause1,
  stringsAsFactors = FALSE
)

# Convert to JSON
api_json <- toJSON(api_input, auto_unbox = TRUE)
```

#### For Multiple Algorithms (Ensemble)
```r
# Combine results from multiple algorithms
ensemble_input <- list(
  insilicova = data.frame(
    id = rownames(top_cod_insilico),
    cause = top_cod_insilico$cause1
  ),
  interva = data.frame(
    id = rownames(top_cod_interva),
    cause = top_cod_interva$cause1
  ),
  tariff = data.frame(
    id = rownames(top_cod_tariff),
    cause = top_cod_tariff$cause1
  )
)

# Convert to JSON
ensemble_json <- toJSON(ensemble_input, auto_unbox = TRUE)
```

### 4. Send to Calibration API

#### Using R
```r
library(httr)

# Prepare calibration request
calibration_request <- list(
  data_source = "custom",
  va_data = list(
    insilicova = api_input  # Your openVA results
  ),
  data_format = "specific_causes",
  age_group = "neonate",  # or "child", "adult"
  country = "Mozambique",  # or other supported country
  mmat_type = "prior"  # or "fixed"
)

# Send to API
response <- POST(
  url = "http://localhost:8000/calibrate",
  body = toJSON(calibration_request, auto_unbox = TRUE),
  content_type_json(),
  encode = "raw"
)

# Get calibrated results
calibrated_results <- content(response, "parsed")
```

#### Using Python
```python
import pandas as pd
import requests

# Assume you have openVA results in a DataFrame
openva_results = pd.DataFrame({
    'id': ['d1', 'd2', 'd3'],
    'cause': ['Stroke', 'Pneumonia', 'Malaria']
})

# Send to calibration API
response = requests.post(
    'http://localhost:8000/calibrate',
    json={
        'data_source': 'custom',
        'va_data': {
            'insilicova': openva_results.to_dict('records')
        },
        'data_format': 'specific_causes',
        'age_group': 'adult',
        'country': 'Kenya'
    }
)

calibrated = response.json()
```

## Alternative: Use Probability Matrices

Instead of top causes, you can send the full probability matrix:

```r
# Get individual probabilities
prob_matrix <- getIndivProb(fit_insilico)

# Convert to list format for API
prob_list <- as.list(as.data.frame(prob_matrix))

# Send as broad_causes format
calibration_request <- list(
  data_source = "custom",
  va_data = list(insilicova = prob_list),
  data_format = "broad_causes",
  age_group = "neonate",
  country = "Mozambique"
)
```

## Working with Different Age Groups

The calibration matrices are age-specific:

- **Neonates** (0-28 days): Limited cause list
- **Children** (1 month - 5 years): Childhood-specific causes
- **Adults** (>5 years): Full cause list

Example cause mappings:
- Neonate causes: `Birth asphyxia`, `Neonatal sepsis`, `Prematurity`, etc.
- Child causes: `Malaria`, `Pneumonia`, `Diarrhea`, etc.
- Adult causes: `Stroke`, `HIV/AIDS`, `Diabetes`, etc.

## Tips and Best Practices

1. **Data Quality**: Ensure your VA data is complete and follows WHO standards
2. **Algorithm Selection**: Different algorithms may perform better for different populations
3. **Ensemble Approach**: Using multiple algorithms can improve accuracy
4. **Country Selection**: Choose the calibration country closest to your study population
5. **Validation**: Always validate calibrated results against known data when possible

## Troubleshooting

### Common Issues

1. **Cause Names Don't Match**: The API uses standardized cause names. Check `/cause-mappings/{age_group}` endpoint for valid causes.

2. **Missing Data**: Ensure all required fields are present:
   - `id`: Unique identifier for each death
   - `cause`: Cause of death from openVA

3. **Age Group Mismatch**: Ensure the age group matches your population and the causes are appropriate.

## Example: Complete Workflow

```r
# 1. Load openVA
library(openVA)
library(httr)
library(jsonlite)

# 2. Load data
data(RandomVA5)

# 3. Run openVA
fit <- codeVA(
  data = RandomVA5[1:100,],  # Use subset for example
  data.type = "WHO2016",
  model = "InSilicoVA",
  Nsim = 1000
)

# 4. Extract results
top_cod <- getTopCOD(fit)

# 5. Format for API
api_data <- data.frame(
  id = rownames(top_cod),
  cause = top_cod$cause1
)

# 6. Send to calibration API
request_body <- list(
  data_source = "custom",
  va_data = list(insilicova = api_data),
  data_format = "specific_causes",
  age_group = "adult",
  country = "Mozambique",
  mmat_type = "prior"
)

response <- POST(
  "http://localhost:8000/calibrate",
  body = toJSON(request_body, auto_unbox = TRUE),
  content_type_json()
)

# 7. Get calibrated results
calibrated <- content(response, "parsed")
print(calibrated$calibrated$insilicova$mean)
```

## Additional Resources

- [OpenVA Documentation](https://cran.r-project.org/package=openVA)
- [WHO Verbal Autopsy Standards](https://www.who.int/standards/classifications/other-classifications/verbal-autopsy-standards)
- [VA-Calibration API Documentation](/api/docs)

## Support

For issues with:
- **OpenVA package**: See the [openVA GitHub repository](https://github.com/verbal-autopsy-software/openVA)
- **Calibration API**: See the [API documentation](/api-design.md) or submit issues to the project repository