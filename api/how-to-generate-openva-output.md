# How to Generate OpenVA Output

## Step 1: Install and Load OpenVA
```r
# Install openVA package
install.packages("openVA")
library(openVA)
```

## Step 2: Prepare VA Data
OpenVA accepts data in several formats:
- **WHO2016**: WHO 2016 questionnaire format
- **WHO2012**: WHO 2012 questionnaire format
- **PHMRC**: PHMRC format
- **customize**: Custom dichotomized format

Example input structure (WHO2016 format):
```
  ID i004a i004b i019a i019b ...
1 d1     .     .     y     .
2 d2     .     .     .     y
3 d3     .     .     y     .
```

## Step 3: Run VA Coding Algorithm
```r
# Example: Run InSilicoVA
fit_insilico <- codeVA(
  data = va_data,           # Your VA survey data
  data.type = "WHO2016",    # Data format
  model = "InSilicoVA",     # Algorithm choice
  Nsim = 1000,             # Number of iterations
  auto.length = FALSE
)

# Example: Run InterVA-5
fit_interva <- codeVA(
  data = va_data,
  data.type = "WHO2016",
  model = "InterVA",
  version = "5",
  HIV = "l",               # HIV prevalence (h/l/v)
  Malaria = "h"            # Malaria prevalence (h/l/v)
)
```

## Step 4: Extract Results for API
```r
# Get top cause assignments
top_causes <- getTopCOD(fit_insilico)

# Convert to API format (ID + cause)
api_input <- data.frame(
  ID = rownames(top_causes),
  cause = top_causes$cause1,
  stringsAsFactors = FALSE
)
```