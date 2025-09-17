# VA-Calibration

Calibration of Computer-Coded Verbal Autopsy (CCVA) algorithms using gold-standard data from the CHAMPS project.

## Quick Start Options

### Option 1: R Package with Docker
```bash
# Build and run the R package directly
docker build -t vacalib .
docker run --rm vacalib
```

### Option 2: Web API with Docker Compose (Recommended)
```bash
# Start the web API and all services
docker-compose up -d

# Submit a calibration job
curl -X POST http://localhost:8000/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": []},
    "age_group": "neonate",
    "country": "Mozambique",
    "mmat_type": "Mmatfixed"
  }'
```

## What it does

This R package calibrates cause-specific mortality fractions (CSMF) from verbal autopsy algorithms like InSilicoVA, InterVA, and EAVA. It uses Bayesian methods to correct systematic biases in VA algorithms by leveraging gold-standard cause of death data from CHAMPS (Child Health and Mortality Prevention Surveillance).

## Example Output

The package takes uncalibrated CSMF estimates and produces calibrated estimates with uncertainty intervals:

**Before calibration:**
- Sepsis/meningitis: 30.5%
- Prematurity: 24.3%
- Pneumonia: 12.4%

**After calibration:**
- Sepsis/meningitis: 55.9% (95% CI: 39.8-77.0%)
- Prematurity: 8.0% (95% CI: 0.4-18.2%)
- Pneumonia: 10.5% (95% CI: 0.5-27.9%)

## Web Interface & API

### Frontend Dashboard
A React-based web interface is available for visual interaction with the calibration service:
- **URL**: http://localhost:8080 (when running locally)
- **Features**:
  - Submit calibration jobs through an intuitive UI
  - Real-time job status monitoring
  - Interactive visualization of calibration results
  - Export results as JSON
- **Tech Stack**: React, TypeScript, Vite, TailwindCSS, shadcn/ui

### API Service
The package includes a FastAPI-based web service for programmatic integration:

**API Endpoints:**
- `POST /calibrate` - Submit calibration job
- `GET /status/{job_id}` - Check job status
- `GET /result/{job_id}` - Get calibration results
- `GET /jobs` - List all jobs
- `DELETE /jobs/{job_id}` - Delete job record

### Running the Full Stack
```bash
# Start API server
cd api
poetry run uvicorn app.main_simple:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (in a separate terminal)
cd info-visual-scape
npm install
npm run dev
```

### Example API Response
```json
{
  "uncalibrated_csmf": {
    "sepsis_meningitis_inf": 0.39,
    "pneumonia": 0.10,
    "prematurity": 0.16
  },
  "calibrated_csmf": {
    "insilicova": {
      "mean": {
        "sepsis_meningitis_inf": 0.594,
        "pneumonia": 0.055,
        "prematurity": 0.044
      },
      "lower_ci": {...},
      "upper_ci": {...}
    }
  }
}
```

See [api/README.md](api/README.md) for detailed API documentation.

## Project Structure

```
vacalibration/
├── api/                    # FastAPI backend service
│   ├── app/               # Python application code
│   ├── r_scripts/         # R integration scripts
│   └── pyproject.toml     # Poetry dependencies
├── info-visual-scape/      # React frontend dashboard
│   ├── src/               # TypeScript/React source
│   ├── package.json       # NPM dependencies
│   └── vite.config.ts     # Vite configuration
├── R/                      # Core R package
├── data/                   # CHAMPS gold-standard data
├── inst/                   # Stan models
└── docker-compose.yml      # Container orchestration
```

## Package Details

- **Version**: 2.1
- **License**: GPL-2
- **Authors**: Sandipan Pramanik et al.
- **Supported algorithms**: EAVA, InSilicoVA, InterVA
- **Age groups**: Neonates (0-27 days), Children (1-59 months)
- **Backend**: FastAPI with Python 3.12+ and Poetry
- **Frontend**: React 18+ with TypeScript and Vite