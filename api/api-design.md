# VA-Calibration API Design Document

## Executive Summary

This document outlines the design for a comprehensive REST API that interfaces with the `vacalibration` R package. The API enables users to calibrate computer-coded verbal autopsy (CCVA) algorithm outputs, either using sample data or their own openVA outputs. The calibration process improves the accuracy of cause-specific mortality fraction (CSMF) estimates by applying misclassification corrections based on CHAMPS gold-standard data.

**Important Note**: This API does not run the openVA package directly. Users must run openVA algorithms separately and provide the resulting cause assignments as input to this calibration API. The API's sole purpose is to calibrate already-computed VA results using the vacalibration R package.

## Research Findings

### 1. Data Structures

#### 1.1 comsamoz_public_broad.rda
- **Structure**: Binary matrix (rows = individuals, columns = broad causes)
- **Content**: 1190 neonatal deaths from Mozambique COMSA study
- **Format**:
  ```r
  list(
    data = matrix[1190 x 6],  # Binary matrix (0/1 values)
    age_group = "neonate",
    va_algo = "insilicova",
    version = "20241220"
  )
  ```

- **Column Structure** (Broad Causes for Neonates):
  1. `congenital_malformation`
  2. `pneumonia`
  3. `sepsis_meningitis_inf` (sepsis/meningitis/infections)
  4. `ipre` (intrapartum-related events)
  5. `other`
  6. `prematurity`

- **Actual Data Sample** (first 5 rows):
  ```
  ID    | congenital_malformation | pneumonia | sepsis_meningitis_inf | ipre | other | prematurity
  ------|------------------------|-----------|----------------------|------|-------|------------
  10004 | 0                      | 0         | 0                    | 0    | 1     | 0
  10006 | 0                      | 0         | 0                    | 1    | 0     | 0
  10008 | 0                      | 0         | 1                    | 0    | 0     | 0
  10036 | 0                      | 0         | 0                    | 1    | 0     | 0
  10046 | 0                      | 0         | 0                    | 1    | 0     | 0
  ```

- **As JSON Array Format**:
  ```json
  [
    [0, 0, 0, 0, 1, 0],  // ID: 10004 - "other"
    [0, 0, 0, 1, 0, 0],  // ID: 10006 - "ipre" (Birth asphyxia)
    [0, 0, 1, 0, 0, 0],  // ID: 10008 - "sepsis_meningitis_inf"
    [0, 0, 0, 1, 0, 0],  // ID: 10036 - "ipre"
    [0, 0, 0, 1, 0, 0]   // ID: 10046 - "ipre"
  ]
  ```

- **Cause Distribution** (Total Deaths = 1190):
  ```
  congenital_malformation:    1 (0.08%)
  pneumonia:                148 (12.44%)
  sepsis_meningitis_inf:    363 (30.50%)
  ipre:                     327 (27.48%)
  other:                     62 (5.21%)
  prematurity:              289 (24.29%)
  ```

#### 1.2 comsamoz_public_openVAout.rda
- **Structure**: Data frame with specific cause assignments
- **Content**: Same 1190 neonatal deaths with high-resolution causes
- **Format**:
  ```r
  list(
    data = data.frame(
      ID = character[1190],      # Individual identifiers
      cause = character[1190]     # Specific cause names
    ),
    age_group = "neonate",
    va_algo = "insilicova",
    version = "20241220"
  )
  ```

- **Actual Data Sample** (first 10 rows):
  ```
  ID    | cause
  ------|-------------------------------------
  10004 | Other and unspecified neonatal CoD
  10006 | Birth asphyxia
  10008 | Neonatal sepsis
  10036 | Birth asphyxia
  10046 | Birth asphyxia
  10051 | Neonatal sepsis
  10059 | Prematurity
  10060 | Neonatal pneumonia
  10067 | Prematurity
  10073 | Neonatal sepsis
  ```

- **As JSON Format**:
  ```json
  [
    {"id": "10004", "cause": "Other and unspecified neonatal CoD"},
    {"id": "10006", "cause": "Birth asphyxia"},
    {"id": "10008", "cause": "Neonatal sepsis"},
    {"id": "10036", "cause": "Birth asphyxia"},
    {"id": "10046", "cause": "Birth asphyxia"},
    {"id": "10051", "cause": "Neonatal sepsis"},
    {"id": "10059", "cause": "Prematurity"},
    {"id": "10060", "cause": "Neonatal pneumonia"},
    {"id": "10067", "cause": "Prematurity"},
    {"id": "10073", "cause": "Neonatal sepsis"}
  ]
  ```

- **Specific Cause Distribution** (Total Deaths = 1190):
  ```
  Birth asphyxia:                      327 (27.48%)
  Neonatal sepsis:                     363 (30.50%)
  Neonatal pneumonia:                  148 (12.44%)
  Prematurity:                         289 (24.29%)
  Other and unspecified neonatal CoD:   56 (4.71%)
  Road traffic accident:                  4 (0.34%)
  Accid fall:                            2 (0.17%)
  Congenital malformation:                1 (0.08%)
  ```

- **Cause Mapping** (Specific → Broad):
  ```
  Birth asphyxia                     → ipre
  Neonatal sepsis                    → sepsis_meningitis_inf
  Neonatal pneumonia                 → pneumonia
  Prematurity                        → prematurity
  Congenital malformation            → congenital_malformation
  Other and unspecified neonatal CoD → other
  Road traffic accident              → other
  Accid fall                         → other
  ```

### 2. OpenVA Output Format (Input to this API)

The openVA package provides multiple VA coding algorithms through its `codeVA()` function. **Note: This API expects the output from openVA as input - it does not run openVA itself.**

#### 2.1 Supported Algorithms
- **InSilicoVA**: Bayesian probabilistic approach
- **InterVA** (4 & 5): Probabilistic expert algorithm
- **Tariff**: Machine learning approach
- **NBC**: Naive Bayes Classifier

#### 2.2 How to Generate OpenVA Output

See [how-to-generate-openva-output.md](./how-to-generate-openva-output.md) for detailed instructions on generating OpenVA outputs.

#### 2.3 Actual OpenVA Output Examples

##### Individual Cause Assignments (getTopCOD output)
```
  ID                            cause1                            cause2
1 d1                            Stroke                   Digestive neoplasms
2 d2 Other and unspecified cardiac dis                     Renal failure
3 d3 Other and unspecified cardiac dis            HIV/AIDS related death
4 d4               Digestive neoplasms                            Stroke
5 d5            HIV/AIDS related death               Respiratory neoplasms
```

##### Converted to API Input Format
```json
[
  {"ID": "d1", "cause": "Stroke"},
  {"ID": "d2", "cause": "Other and unspecified cardiac dis"},
  {"ID": "d3", "cause": "Other and unspecified cardiac dis"},
  {"ID": "d4", "cause": "Digestive neoplasms"},
  {"ID": "d5", "cause": "HIV/AIDS related death"}
]
```

##### Individual Probability Matrix (getIndivProb output)
```
       Sepsis    Pneumonia    HIV/AIDS    Diarrhea     Malaria    ...
d1  6.697e-06  2.163e-07   1.260e-06   1.173e-05   7.133e-06
d2  7.240e-09  6.156e-05   1.875e-04   3.053e-13   5.802e-08
d3  2.965e-05  2.164e-03   5.021e-03   5.142e-10   1.443e-06
```

##### Population CSMF (getCSMF output)
```
Stroke                              0.0881
Other and unspecified cardiac dis  0.0850
Digestive neoplasms                 0.0806
HIV/AIDS related death              0.0686
Renal failure                       0.0636
```

#### 2.4 Using OpenVA Output with Calibration API

For detailed integration examples, see the [Integration with OpenVA](#integration-with-openva) section below.

### 3. Vacalibration Library Functions

#### 3.1 Main Functions

##### vacalibration()
**Purpose**: Main calibration function
**Input Parameters**:
```r
vacalibration(
  va_data,        # Named list of algorithm outputs
  age_group,      # "neonate" or "child"
  country,        # Country for calibration
  Mmat_type,      # "prior" or "fixed"
  ensemble,       # TRUE/FALSE for ensemble calibration
  verbose,        # TRUE/FALSE for output verbosity
  plot_it         # TRUE/FALSE for plotting
)
```

**Accepted Input Formats for va_data**:
1. **Specific causes**: Data frame with ID and cause columns
2. **Broad causes**: Binary matrix (individuals × causes)
3. **Death counts**: Integer vector of cause-specific counts

**Output Structure**:
```r
list(
  p_uncalib = vector,           # Uncalibrated CSMF
  pcalib_postsumm = array,      # Calibrated CSMF with uncertainty
  # [algorithm, statistic, cause] where statistic = {postmean, lowcredI, upcredI}
)
```

##### cause_map()
**Purpose**: Maps specific causes to broad causes
**Input**: Data frame with ID and specific cause
**Output**: Binary matrix of broad causes

## API Design Specification

### Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Client App    │────▶│   FastAPI        │────▶│  R Package       │
│                 │◀────│   (Python)       │◀────│  (vacalibration) │
└─────────────────┘     └──────────────────┘     └──────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌──────────────────┐     ┌──────────────────┐
                        │  Sample Data     │     │  openVA Package  │
                        │  (.rda files)    │     │  Integration     │
                        └──────────────────┘     └──────────────────┘
```

### Core API Endpoints

#### 1. POST /calibrate
**Purpose**: Perform VA calibration on provided data by executing R scripts (does NOT run openVA algorithms)

**Execution Mode**: This endpoint executes the vacalibration R package, which can take 5-60 seconds depending on dataset size. Supports both synchronous and asynchronous execution modes.

**Request Body**:
```json
{
  "data_source": "sample|custom",
  "sample_dataset": "string",
  "va_data": {
    "algorithm_name": []
  },
  "data_format": "string",
  "age_group": "string",
  "country": "string",
  "mmat_type": "string",
  "ensemble": "boolean",
  "async": "boolean",
  "options": {}
}
```

**Parameter Documentation**:

| Parameter | Type | Required | Description | Valid Values | Default |
|-----------|------|----------|-------------|--------------|--------|
| `data_source` | string | Yes | Specifies the source of VA data | `"sample"`, `"custom"` | - |
| `sample_dataset` | string | Conditional | ID of the sample dataset to use. Required when `data_source="sample"` | `"comsamoz_broad"`, `"comsamoz_specific"` | - |
| `va_data` | object | Conditional | Contains pre-computed VA algorithm outputs (from running openVA separately). Required when `data_source="custom"` | Object with algorithm names as keys (e.g., `"insilicova"`, `"interva"`, `"eava"`) and arrays of death records as values | - |
| `data_format` | string | Yes | Format of the input data | `"specific_causes"` (individual cause names), `"broad_causes"` (binary matrix), `"death_counts"` (aggregated counts) | - |
| `age_group` | string | Yes | Age group for calibration matrices | `"neonate"` (0-28 days), `"child"` (1 month - 5 years), `"adult"` (>5 years) | - |
| `country` | string | Yes | Country for calibration matrix selection | `"Mozambique"`, `"Bangladesh"`, `"Ethiopia"`, `"Kenya"`, `"Mali"`, `"Sierra Leone"`, `"South Africa"`, `"other"` | - |
| `mmat_type` | string | No | Calibration method type | `"prior"` (Dirichlet prior with uncertainty), `"fixed"` (fixed misclassification matrix) | `"prior"` |
| `ensemble` | boolean | No | Whether to perform ensemble calibration across multiple algorithms | `true`, `false` | `false` |
| `async` | boolean | No | Execute calibration asynchronously with real-time log streaming | `true`, `false` | `false` |
| `options` | object | No | Additional calibration options | Object containing optional parameters | `{}` |
| `options.verbose` | boolean | No | Enable detailed output logging | `true`, `false` | `false` |
| `options.nMCMC` | integer | No | Number of MCMC iterations | Positive integer (recommended: 5000-10000) | `5000` |
| `options.nBurn` | integer | No | Number of burn-in iterations for MCMC | Positive integer (recommended: 5000-10000) | `5000` |

**Conditional Parameter Rules**:
- When `data_source="sample"`: Only `sample_dataset` is required, `va_data` should be omitted
- When `data_source="custom"`: Only `va_data` is required, `sample_dataset` should be omitted
- When `ensemble=true`: `va_data` must contain outputs from multiple algorithms

**Response (Synchronous Mode - async=false)**:
```json
{
  "status": "success",
  "results": {
    "uncalibrated": {
      "congenital_malformation": 0.0008,
      "pneumonia": 0.1244,
      "sepsis_meningitis_inf": 0.305,
      "ipre": 0.2748,
      "other": 0.0521,
      "prematurity": 0.2429
    },
    "calibrated": {
      "algorithm_name": {
        "mean": {
          "congenital_malformation": 0.0008,
          "pneumonia": 0.1086,
          "sepsis_meningitis_inf": 0.5602,
          "ipre": 0.1983,
          "other": 0.0521,
          "prematurity": 0.08
        },
        "lower_ci": {/* ... */},
        "upper_ci": {/* ... */}
      }
    }
  },
  "metadata": {
    "age_group": "neonate",
    "country": "Mozambique",
    "total_deaths": 1190,
    "algorithms_used": ["insilicova"],
    "calibration_method": "prior"
  }
}
```

**Response (Asynchronous Mode - async=true)**:
```json
{
  "status": "accepted",
  "job_id": "cal_20240115_abc123xyz",
  "message": "Calibration job started. Connect to WebSocket or poll status endpoint for updates.",
  "urls": {
    "status": "/calibrate/cal_20240115_abc123xyz/status",
    "websocket": "ws://localhost:8000/calibrate/cal_20240115_abc123xyz/logs"
  },
  "estimated_duration_seconds": 15
}
```

#### 2. GET /datasets
**Purpose**: List available sample datasets

**Response**:
```json
{
  "datasets": [
    {
      "id": "comsamoz_broad",
      "name": "COMSA Mozambique - Broad Causes",
      "description": "1190 neonatal deaths with broad cause assignments",
      "age_group": "neonate",
      "algorithm": "insilicova",
      "format": "broad_causes",
      "causes": ["congenital_malformation", "pneumonia", "sepsis_meningitis_inf", "ipre", "other", "prematurity"]
    },
    {
      "id": "comsamoz_specific",
      "name": "COMSA Mozambique - Specific Causes",
      "description": "1190 neonatal deaths with specific cause assignments",
      "age_group": "neonate",
      "algorithm": "insilicova",
      "format": "specific_causes",
      "sample_causes": ["Birth asphyxia", "Neonatal sepsis", "Neonatal pneumonia", "Prematurity"]
    }
  ]
}
```

#### 3. GET /datasets/{dataset_id}/preview
**Purpose**: Preview sample data structure

**Response**:
```json
{
  "dataset_id": "comsamoz_specific",
  "total_records": 1190,
  "sample": [
    {"id": "10004", "cause": "Other and unspecified neonatal CoD"},
    {"id": "10006", "cause": "Birth asphyxia"},
    {"id": "10008", "cause": "Neonatal sepsis"}
  ],
  "statistics": {
    "cause_distribution": {
      "Birth asphyxia": 327,
      "Neonatal sepsis": 363,
      "Other and unspecified neonatal CoD": 62,
      /* ... */
    }
  }
}
```

#### 4. POST /convert/causes
**Purpose**: Convert specific causes to broad causes (expose cause_map function)

**Request Body**:
```json
{
  "data": [
    {"id": "001", "cause": "Birth asphyxia"},
    {"id": "002", "cause": "Neonatal sepsis"}
  ],
  "age_group": "neonate"
}
```

**Response**:
```json
{
  "broad_causes": [
    {"id": "001", "causes": {"ipre": 1, "pneumonia": 0, "sepsis_meningitis_inf": 0, /* ... */}},
    {"id": "002", "causes": {"ipre": 0, "pneumonia": 0, "sepsis_meningitis_inf": 1, /* ... */}}
  ],
  "matrix_format": [
    [0, 0, 0, 1, 0, 0],  // ID 001: ipre
    [0, 0, 1, 0, 0, 0]   // ID 002: sepsis_meningitis_inf
  ],
  "cause_labels": ["congenital_malformation", "pneumonia", "sepsis_meningitis_inf", "ipre", "other", "prematurity"]
}
```

#### 5. POST /validate
**Purpose**: Validate input data format before calibration

**Request Body**:
```json
{
  "data": {/* user data */},
  "format": "specific_causes|broad_causes|death_counts",
  "age_group": "neonate|child"
}
```

**Response**:
```json
{
  "valid": true|false,
  "errors": [],
  "warnings": ["25 records have unknown cause mappings"],
  "summary": {
    "total_records": 500,
    "valid_records": 475,
    "unique_causes": 12
  }
}
```

#### 6. GET /cause-mappings/{age_group}
**Purpose**: Get mapping between specific and broad causes

**Response**:
```json
{
  "age_group": "neonate",
  "broad_causes": ["congenital_malformation", "pneumonia", /* ... */],
  "mappings": {
    "Birth asphyxia": "ipre",
    "Neonatal sepsis": "sepsis_meningitis_inf",
    "Neonatal pneumonia": "pneumonia",
    /* ... */
  }
}
```

#### 7. GET /supported-configurations
**Purpose**: Get supported countries, age groups, and algorithms

**Response**:
```json
{
  "age_groups": ["neonate", "child"],
  "countries": {
    "supported": ["Bangladesh", "Ethiopia", "Kenya", "Mali", "Mozambique", "Sierra Leone", "South Africa"],
    "default": "other"
  },
  "algorithms": {
    "calibratable": ["eava", "insilicova", "interva"],
    "description": {
      "eava": "Expert Algorithm for Verbal Autopsy",
      "insilicova": "Bayesian probabilistic method",
      "interva": "Probabilistic expert algorithm"
    }
  },
  "calibration_methods": {
    "prior": "Propagates uncertainty using Dirichlet prior",
    "fixed": "Uses fixed misclassification matrix",
    "samples": ???????????
  }
}
```

#### 8. GET /calibrate/{job_id}/status
**Purpose**: Check the status of an asynchronous calibration job

**Parameters**:
- `job_id` (path): The job ID returned from async POST /calibrate request

**Response**:
```json
{
  "job_id": "cal_20240115_abc123xyz",
  "status": "running|completed|failed",
  "progress": 45,
  "progress_message": "Running MCMC iterations...",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:15Z",
  "logs": [
    {"timestamp": "2024-01-15T10:30:01Z", "level": "INFO", "message": "Starting calibration for neonate age group"},
    {"timestamp": "2024-01-15T10:30:02Z", "level": "INFO", "message": "Loading misclassification matrix for Mozambique"},
    {"timestamp": "2024-01-15T10:30:05Z", "level": "INFO", "message": "Running MCMC with 5000 iterations"},
    {"timestamp": "2024-01-15T10:30:15Z", "level": "INFO", "message": "MCMC iteration 2500/5000 (50%)"}
  ],
  "result": null  // Will contain the calibration results when status="completed"
}
```

#### 9. WebSocket /calibrate/{job_id}/logs
**Purpose**: Real-time streaming of R script execution logs during calibration

**Connection URL**: `ws://host:port/calibrate/{job_id}/logs`

**Message Format (Server → Client)**:
```json
{
  "type": "log|progress|status|result|error",
  "timestamp": "2024-01-15T10:30:15.123Z",
  "data": {
    // For type="log"
    "level": "INFO|WARN|ERROR",
    "message": "MCMC iteration 2500/5000",
    "source": "R"

    // For type="progress"
    "percentage": 50,
    "message": "Processing MCMC iterations"

    // For type="status"
    "status": "running|completed|failed"

    // For type="result"
    "results": {/* Full calibration results */}

    // For type="error"
    "error": "Error message",
    "details": {/* Error details */}
  }
}
```

**Client → Server Messages**:
```json
{
  "type": "ping|subscribe|unsubscribe",
  "data": {}
}
```

**Connection Lifecycle**:
1. Client connects to WebSocket endpoint with job_id
2. Server validates job_id and starts streaming logs
3. Server sends real-time logs as R script executes
4. Server sends progress updates periodically
5. Server sends final results or error when complete
6. Connection closes automatically after completion

### Additional Implemented Endpoints (Not in Original Design)

The implementation includes several additional endpoints beyond the original design specification to enhance functionality:

#### 10. POST /api/v1/calibrate/batch
**Purpose**: Process multiple calibration jobs in a single request
**Request Body**:
```json
{
  "jobs": [
    {
      "va_data": {"insilicova": "use_example"},
      "age_group": "neonate",
      "country": "Mozambique"
    },
    {
      "va_data": {"interva": [...]},
      "age_group": "child",
      "country": "Kenya"
    }
  ]
}
```
**Response**: Batch job ID with individual job tracking

#### 11. GET /api/v1/cache/stats
**Purpose**: Get cache statistics and memory usage
**Response**: Cache hit rates, memory usage, TTL information

#### 12. POST /api/v1/cache/clear
**Purpose**: Clear cached results (admin operation)
**Response**: Confirmation with number of entries cleared

#### 13. GET /api/v1/jobs/metrics
**Purpose**: Get performance metrics across all jobs
**Response**: Average processing time, success rate, queue depth

#### 14. POST /api/v1/jobs/retry/{job_id}
**Purpose**: Retry a failed calibration job
**Response**: New job ID for retried execution

#### 15. GET /jobs
**Purpose**: List all jobs with filtering capabilities
**Query Parameters**:
- `status`: Filter by job status (pending, running, completed, failed)
- `limit`: Maximum number of results
- `offset`: Pagination offset
**Response**: Paginated list of jobs with metadata

### Data Format Examples

#### Specific Causes Format
```json
[{"id": "d1", "cause": "Birth asphyxia"}, {"id": "d2", "cause": "Neonatal sepsis"}]
```

#### Broad Causes Format (Binary Matrix)
```json
[[0, 0, 1, 0, 0, 0], [0, 1, 0, 0, 0, 0]]  // Row per death, column per cause
```

#### Death Counts Format
```json
{"congenital_malformation": 5, "pneumonia": 148, "sepsis_meningitis_inf": 363}
```

### R Script Execution & Log Streaming

**Implementation Details**:

The calibration API executes R scripts from the vacalibration package. During execution:

1. **R Script Invocation**: The API spawns an R subprocess using `Rscript` to run the vacalibration functions
2. **Log Capture**: All R console output (stdout/stderr) is captured in real-time
3. **Progress Tracking**: The R script emits progress messages during MCMC iterations
4. **Real-time Streaming**: Logs are streamed to clients via WebSocket or stored for polling

**Log Types Generated**:
- **Initialization**: Loading data, setting up calibration parameters
- **Matrix Loading**: Loading country-specific misclassification matrices
- **MCMC Progress**: Iteration counts and convergence metrics
- **Warnings**: Data quality issues or convergence warnings
- **Results**: Final CSMF calculations and uncertainty intervals
- **Errors**: R execution errors or data validation failures

**Example R Script Output Stream**:
```
[INFO] Starting VA calibration v2.1.0
[INFO] Age group: neonate, Country: Mozambique
[INFO] Loading misclassification matrix from CHAMPS data
[INFO] Input data: 1190 deaths across 6 causes
[INFO] Starting MCMC with 5000 iterations, 5000 burn-in
[PROGRESS] MCMC iteration 1000/10000 (10%)
[PROGRESS] MCMC iteration 2000/10000 (20%)
[INFO] Checking convergence diagnostics...
[INFO] Gelman-Rubin statistic: 1.02 (converged)
[INFO] Calculating posterior summaries...
[SUCCESS] Calibration completed successfully
```

### Integration with OpenVA

**Prerequisites**: Users must first run openVA algorithms separately to obtain cause assignments. This API only performs calibration on those results.

#### R Integration Example

```r
library(openVA)
library(jsonlite)
library(httr)

# STEP 1: Run OpenVA algorithm SEPARATELY (not part of this API)
fit <- codeVA(
  data = va_data,
  data.type = "WHO2016",
  model = "InSilicoVA",
  Nsim = 1000
)

# STEP 2: Extract openVA results to use as input for calibration API
top_cod <- getTopCOD(fit)
api_input <- data.frame(
  id = rownames(top_cod),
  cause = top_cod$cause1
)

# STEP 3: Send openVA results to calibration API
request_body <- toJSON(list(
  data_source = "custom",
  va_data = list(insilicova = api_input),  # Pre-computed openVA output
  data_format = "specific_causes",
  age_group = "neonate",
  country = "Mozambique",
  mmat_type = "prior"
), auto_unbox = TRUE)

response <- POST(
  url = "http://localhost:8000/calibrate",
  body = request_body,
  content_type_json(),
  encode = "raw"
)

# STEP 4: Receive calibrated results
result <- content(response, "parsed")
calibrated_csmf <- result$results$calibrated$insilicova$mean
```

#### Python Integration Example

```python
import requests
import pandas as pd

# PREREQUISITE: Assume you have already run openVA separately and have the results
# This API does not run openVA - it only calibrates existing results
openva_results = pd.DataFrame({
    'ID': ['n001', 'n002', 'n003'],
    'cause': ['Neonatal sepsis', 'Birth asphyxia', 'Neonatal pneumonia']
})

# Send pre-computed openVA results to calibration API
response = requests.post(
    'http://localhost:8000/calibrate',
    json={
        "data_source": "custom",
        "va_data": {"insilicova": openva_results.to_dict('records')},  # Pre-computed results
        "data_format": "specific_causes",
        "age_group": "neonate",
        "country": "Mozambique"
    }
)

# Receive calibrated results
if response.status_code == 200:
    calibrated = response.json()['results']['calibrated']['insilicova']['mean']
    print("Calibrated CSMF:", calibrated)
```

#### Ensemble Calibration Example

```python
# PREREQUISITE: Multiple algorithm outputs obtained by running openVA separately
# This API calibrates these pre-computed results, it does not run the algorithms
ensemble_request = {
    "data_source": "custom",
    "va_data": {
        "insilicova": [{"id": "d1", "cause": "Stroke"}, ...],  # From running InSilicoVA
        "interva": [{"id": "d1", "cause": "Stroke"}, ...],     # From running InterVA
        "eava": [{"id": "d1", "cause": "CVD"}, ...]            # From running EAVA
    },
    "data_format": "specific_causes",
    "age_group": "adult",
    "country": "Mozambique",
    "ensemble": True
}

response = requests.post('http://localhost:8000/calibrate', json=ensemble_request)
```

### Error Handling

#### Standard Error Response:
```json
{
  "status": "error",
  "error_code": "INVALID_DATA_FORMAT",
  "message": "The provided data format does not match the specified type",
  "details": {
    "expected": "Array of objects with 'id' and 'cause' fields",
    "received": "Array of numbers"
  }
}
```

#### Error Codes:
- `INVALID_DATA_FORMAT`: Data doesn't match specified format
- `UNSUPPORTED_AGE_GROUP`: Age group not supported
- `UNKNOWN_CAUSES`: Causes in data not recognized
- `CALIBRATION_FAILED`: R package error during calibration
- `MISSING_REQUIRED_FIELD`: Required parameter missing

### Performance Considerations

#### Expected Performance:
- **Small datasets** (< 1000 deaths): 5-10 seconds
- **Medium datasets** (1000-5000 deaths): 10-30 seconds
- **Large datasets** (> 5000 deaths): 30-60 seconds
- **MCMC iterations**: Processing time scales linearly with nMCMC parameter

#### Synchronous vs Asynchronous Mode:

**Use Synchronous Mode (async=false) when**:
- Dataset is small (< 1000 deaths)
- Quick response is needed (< 10 seconds)
- Simple integration without WebSocket support

**Use Asynchronous Mode (async=true) when**:
- Dataset is large (> 1000 deaths)
- Real-time progress feedback is desired
- Running multiple calibrations concurrently
- Better user experience with progress indicators
- Need to prevent HTTP timeouts on long operations

#### Benefits of Real-time Log Streaming:
1. **User Feedback**: Users see progress instead of waiting blindly
2. **Debugging**: Real-time visibility into R script execution
3. **Progress Tracking**: Accurate progress percentages during MCMC
4. **Early Error Detection**: Immediate notification of failures
5. **Better UX**: Frontend can show progress bars and status updates

#### Optimization Strategies (Implementation Status):
1. **Caching**: ✅ Implemented - Redis-based caching with configurable TTL
2. **Parallel Processing**: ✅ Implemented - Concurrent job execution support
3. **Batch Processing**: ✅ Implemented - `/api/v1/calibrate/batch` endpoint
4. **Async Operations**: ✅ Implemented - Full async with WebSocket real-time streaming
5. **Resource Management**: ✅ Implemented - Job queue and worker pool management

### Security & Authentication

#### Implementation Status (Updated 2025-09-24):
1. **API Keys**: ✅ Implemented - Header (`X-API-Key`) and query parameter (`api_key`) support
2. **Rate Limiting**: ✅ Implemented - 60 requests/minute per API key/IP (configurable)
3. **Input Validation**: ✅ Implemented - Pydantic models with comprehensive validation
4. **Data Privacy**: ✅ Implemented - No permanent storage, temp files cleaned after use
5. **HTTPS Only**: ⚠️ Ready - TLS enforcement via reverse proxy recommended
6. **Security Headers**: ✅ Implemented - XSS, clickjacking, and content-type protection

#### Configuration:
Security features are controlled via environment variables:
```bash
ENABLE_API_KEY_AUTH=true    # Enable API key authentication
API_KEYS=key1,key2,key3     # Comma-separated list of valid keys
RATE_LIMIT_PER_MINUTE=60    # Requests per minute limit
ENVIRONMENT=production       # Set to 'development' for test keys
```

### Versioning Strategy

#### API Versioning:
- URL path versioning: `/v1/calibrate`
- Version in response headers: `X-API-Version: 1.0.0`
- Backward compatibility for 2 major versions

#### Data Format Versions:
- Support WHO2012, WHO2016 questionnaire formats
- Version field in sample datasets for tracking updates

## Implementation & Testing

- **Implementation Roadmap**: See [api-todo.md](./api-todo.md) for detailed implementation status and task tracking
- **Test Design**: See [api-test.md](./api-test.md) for comprehensive testing strategy, test cases, and test infrastructure requirements

## Conclusion

This API design provides a comprehensive interface to the vacalibration R package, supporting both sample data exploration and custom VA data calibration. The design emphasizes:

1. **Flexibility**: Multiple input formats and data sources
2. **Integration**: Seamless connection with openVA outputs
3. **Usability**: Clear endpoints with validation and preview features
4. **Reliability**: Robust error handling and validation
5. **Performance**: Optimized for various dataset sizes

The API bridges the gap between VA coding algorithms and calibration methodology, making advanced calibration techniques accessible to a broader audience of researchers and public health professionals.