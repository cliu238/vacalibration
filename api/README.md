# VA-Calibration API

FastAPI-based web service for the VA-Calibration package, providing RESTful endpoints for calibrating computer-coded verbal autopsy (CCVA) algorithms.

## Features

- 🚀 **Direct Processing**: Immediate calibration results without job queuing
- 🔧 **Local R Integration**: Runs R package directly without Docker
- 📊 **Multiple Input Formats**: Supports specific causes, binary matrices, and example data
- 🔄 **Ensemble Support**: Calibrate multiple algorithms simultaneously
- 📈 **Confidence Intervals**: Returns calibrated estimates with uncertainty bounds
- ⚡ **Lightweight**: Simple API without job storage or external dependencies

## Prerequisites

### 1. Install R and Dependencies

```bash
# Install required R packages
Rscript -e "install.packages(c('rstan', 'LaplacesDemon', 'reshape2', 'MASS', 'jsonlite'), repos='https://cloud.r-project.org/')"

# Install vacalibration package from project root
cd ..
R CMD INSTALL . --no-multiarch --with-keep.source
```

**Note**: If you encounter issues with ggplot2/patchwork dependencies, they have been removed from the package as they're only needed for plotting.

### 2. Install Python Dependencies

```bash
# Using Poetry (recommended)
cd api
poetry install

# Or using pip
pip install fastapi uvicorn
```

## Running the API

### Local Development

```bash
# Using Poetry (recommended)
cd api
poetry run python app/main_direct.py

# Or directly with Python
python app/main_direct.py
```

The API will be available at `http://localhost:8000`

### Test the Installation

```bash
# Check health status
curl http://localhost:8000/

# Should return:
{
  "status": "healthy",
  "service": "VA-Calibration API (Direct)",
  "r_status": "R ready",
  "data_files": {
    "comsamoz_broad": true,
    "comsamoz_openVA": true
  }
}
```

## API Endpoints

### `GET /` - Health Check
Returns the API status and checks R installation.

### `POST /calibrate` - Run Calibration
Performs calibration and returns results immediately.

**Request Body:**
```json
{
  "va_data": {
    "insilicova": "use_example"  // or actual data
  },
  "age_group": "neonate",        // "neonate" or "child"
  "country": "Mozambique",       // Country name
  "mmat_type": "prior",          // "prior" or "fixed"
  "ensemble": true               // true for multiple algorithms
}
```

**Response:**
```json
{
  "status": "success",
  "uncalibrated": [0.0008, 0.1244, 0.305, ...],
  "calibrated": {
    "insilicova": {
      "mean": {
        "congenital_malformation": 0.0008,
        "pneumonia": 0.1086,
        "sepsis_meningitis_inf": 0.5602,
        "ipre": 0.1983,
        "other": 0.0521,
        "prematurity": 0.08
      },
      "lower_ci": {...},
      "upper_ci": {...}
    }
  },
  "age_group": "neonate",
  "country": "Mozambique"
}
```

### `GET /example-data` - Get Example Data Info
Returns information about available example datasets.

## Data Formats

### Input Formats

The API accepts several formats for VA data:

1. **Use Example Data** (simplest for testing):
```json
{"va_data": {"insilicova": "use_example"}}
```

2. **Specific Causes** (list of deaths with causes):
```json
{
  "va_data": {
    "insilicova": [
      {"cause": "Birth asphyxia", "id": "death_001"},
      {"cause": "Neonatal sepsis", "id": "death_002"}
    ]
  }
}
```

3. **Binary Matrix** (rows = deaths, columns = broad causes):
```json
{
  "va_data": {
    "insilicova": [
      [0, 0, 1, 0, 0, 0],  // Death 1: sepsis
      [0, 1, 0, 0, 0, 0]   // Death 2: pneumonia
    ]
  }
}
```

### Cause Categories

#### Neonates (0-27 days)
- `congenital_malformation`
- `pneumonia`
- `sepsis_meningitis_inf`
- `ipre` (intrapartum-related events)
- `other`
- `prematurity`

#### Children (1-59 months)
- `malaria`
- `pneumonia`
- `diarrhea`
- `severe_malnutrition`
- `hiv`
- `injury`
- `other`
- `other_infections`
- `nn_causes` (neonatal causes)

## Example Usage

### Python Client

```python
import requests
import json

# Simple test with example data
response = requests.post(
    "http://localhost:8000/calibrate",
    json={
        "va_data": {"insilicova": "use_example"},
        "age_group": "neonate",
        "country": "Mozambique"
    }
)

result = response.json()
print(json.dumps(result, indent=2))
```

### Command Line

```bash
# Test with example data
curl -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{"va_data": {"insilicova": "use_example"}, "age_group": "neonate", "country": "Mozambique"}' \
  | python3 -m json.tool

# Test with specific causes
curl -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {
      "insilicova": [
        {"cause": "Birth asphyxia", "id": "001"},
        {"cause": "Neonatal sepsis", "id": "002"},
        {"cause": "Prematurity", "id": "003"}
      ]
    },
    "age_group": "neonate",
    "country": "Mozambique"
  }' | python3 -m json.tool
```

## Available API Implementations

The API directory contains multiple implementations:

- **`main_direct.py`**: Direct execution without job storage (recommended for local use)
- **`main_simple.py`**: Simplified version with mock data fallback
- **`main.py`**: Full version with background job processing (for production)

## Project Structure

```
api/
├── app/
│   ├── main_direct.py    # Direct execution API (current)
│   ├── main_simple.py     # Simplified mock version
│   └── main.py           # Full production version
├── r_scripts/
│   └── run_calibration.R # R integration script
├── pyproject.toml        # Poetry dependencies
└── README.md            # This file
```

## Performance Notes

- **Startup time**: 2-3 seconds
- **Calibration time**: 10-30 seconds for typical datasets (uses MCMC sampling)
- **Memory usage**: ~200MB including R runtime
- **Concurrent requests**: Limited by R's single-threaded nature

## Troubleshooting

### R Package Not Found
```bash
# Reinstall the package
cd ..
R CMD INSTALL . --no-multiarch --with-keep.source
```

### Missing R Dependencies
```bash
# Install all required packages
Rscript -e "install.packages(c('rstan', 'LaplacesDemon', 'reshape2', 'MASS', 'jsonlite'))"
```

### Data Files Not Found
Ensure you're running from the `api/` directory so the relative paths `../data/*.rda` work correctly.

## Development

### Running with Auto-reload
```bash
poetry run uvicorn app.main_direct:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables
- No environment variables required for local development
- The API automatically detects and uses local R installation

## License

GPL-2 (same as VA-calibration R package)

## Support

For issues or questions, please refer to the main [VA-calibration repository](../).