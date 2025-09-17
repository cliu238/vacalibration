# VA-Calibration Platform User Guide

## Overview

The VA-Calibration platform is a web-based application for calibrating computer-coded verbal autopsy (VA) algorithms using Bayesian methods and CHAMPS gold-standard data. This guide will walk you through using the platform to submit calibration jobs, monitor their progress, and analyze the results.

## Getting Started

### Prerequisites

Before using the platform, ensure:
1. The Docker container is built and running (`docker build -t vacalibration-r-engine .`)
2. The API server is running (`cd api && python -m uvicorn app.main_simple:app --reload --host 0.0.0.0 --port 8000`)
3. The frontend is running (`cd info-visual-scape && npm run dev`)

### Accessing the Platform

Open your web browser and navigate to: `http://localhost:8080`

## Main Features

### 1. Dashboard

The dashboard provides an overview of all your calibration jobs:
- **Total Jobs**: Overall count of submitted jobs
- **Completed**: Successfully processed calibrations
- **Running**: Jobs currently being processed
- **Pending**: Jobs waiting in the queue
- **Failed**: Jobs that encountered errors
- **Recent Jobs**: Quick access to your latest calibrations

### 2. Submitting a New Calibration

#### Step 1: Navigate to New Calibration
Click on "New Calibration" in the sidebar or the dashboard button.

#### Step 2: Configure Job Parameters

**Basic Configuration:**
- **Age Group** (Required): Select either:
  - Neonate (0-27 days)
  - Child (1-59 months)
- **Country** (Required): Select from available countries (Bangladesh, Ethiopia, Kenya, Mali, Mozambique, Sierra Leone, South Africa, or other)
- **Matrix Type**: Choose calibration method:
  - Mmat Prior (with uncertainty) - Recommended for most cases
  - Mmat Fixed (point estimates only)

**Options:**
- **Enable ensemble mode**: Combines multiple algorithms (checked by default)
- **Verbose output**: Provides detailed logging for debugging

#### Step 3: Select VA Algorithms

Choose one or more algorithms to calibrate:
- **EAVA**: Expert Algorithm for Verbal Autopsy
- **INSILICOVA**: Probabilistic method using Bayesian framework
- **INTERVA**: InterVA algorithm

*Note: At least one algorithm must be selected to proceed*

#### Step 4: Provide VA Data

You have three options for providing data:

**Option A: Use Example Data (Recommended for Testing)**
- Simply leave the VA Data field empty
- The system will use built-in example datasets:
  - `comsamoz_public_broad.rda` for broad cause categories
  - `comsamoz_public_openVAout.rda` for specific causes

**Option B: Provide Custom Data (JSON Format)**
- Select a data format from the dropdown:
  - **Specific Causes**: Individual-level data with ID and specific cause
  - **Broad Causes**: Binary matrix of broad cause categories
  - **Death Counts**: Aggregated death counts by cause

Example for Specific Causes (Neonate):
```json
[
  {"id": "10004", "cause": "Birth asphyxia"},
  {"id": "10006", "cause": "Neonatal sepsis"},
  {"id": "10008", "cause": "Prematurity"}
]
```

Available neonate-specific causes:
- Birth asphyxia
- Neonatal sepsis
- Neonatal pneumonia
- Prematurity
- Congenital malformation
- Other and unspecified neonatal CoD

Available child-specific causes:
- Malaria
- Pneumonia
- Diarrhea
- Severe malnutrition
- HIV
- Injury
- Other infections
- Neonatal causes

**Option C: File Upload (Coming Soon)**
- Future feature for uploading CSV/Excel files

#### Step 5: Submit the Job

Click "Submit Calibration Job" to start processing. You'll see a "Submitting..." status briefly.

### 3. Monitoring Job Progress

After submission, the system processes your job through these stages:
1. **Pending**: Job queued for processing
2. **Running**: Calibration algorithm executing (typically 30-60 seconds)
3. **Completed**: Results ready for viewing
4. **Failed**: An error occurred (check error details)

### 4. Viewing Results

Once a job is completed, click on it to view detailed results:

#### Results Page Components:

**Job Status Card:**
- Status indicator with completion time
- Runtime in seconds
- Unique Job ID

**Visualization:**
- Interactive bar chart comparing uncalibrated vs calibrated CSMFs
- Hover over bars to see exact percentages and confidence intervals
- Color-coded for easy differentiation

**Data Tables:**

**Uncalibrated CSMF:**
- Raw algorithm output before calibration
- Percentages for each cause of death

**Calibrated CSMF:**
- Bayesian-calibrated estimates
- 95% confidence intervals for each cause
- Accounts for uncertainty in the calibration process

**Example Interpretation:**
- Uncalibrated: sepsis_meningitis_inf = 30.5%
- Calibrated: sepsis_meningitis_inf = 55.9% (95% CI: 39.9% - 77.0%)

This shows the algorithm was underestimating sepsis/meningitis deaths, and the calibration corrects this bias.

### 5. Exporting Results

Click "Export Results" on any completed job to download:
- JSON file with complete calibration data
- Includes both uncalibrated and calibrated CSMFs
- Contains confidence intervals and metadata

### 6. Job History

Access all your calibration jobs from the "Job History" page:
- Search by Job ID
- Filter by status (All, Completed, Running, Pending, Failed)
- Sort by creation date
- Quick actions to view or delete jobs

## Demo Walkthrough

### Quick Demo: Running Your First Calibration

1. **Start the application** (if not already running):
   ```bash
   # Terminal 1: API
   cd api
   source .venv/bin/activate
   python -m uvicorn app.main_simple:app --reload --host 0.0.0.0 --port 8000

   # Terminal 2: Frontend
   cd info-visual-scape
   npm run dev
   ```

2. **Open browser**: Navigate to http://localhost:8080

3. **Create a test calibration**:
   - Click "New Calibration"
   - Select Age Group: "Neonate (0-27 days)"
   - Select Country: "Mozambique"
   - Keep Matrix Type as "Mmat Prior"
   - Check "INSILICOVA" algorithm
   - Leave VA Data empty (uses example data)
   - Click "Submit Calibration Job"

4. **View results**:
   - Wait 30-60 seconds for processing
   - The page will auto-refresh when complete
   - Review the calibration adjustments in the chart
   - Export results if needed

## Understanding the Calibration Process

### What Happens During Calibration?

1. **Data Validation**: Input data is validated and mapped to standard cause categories
2. **R Package Execution**: The `vacalibration` R package runs Bayesian calibration
3. **CHAMPS Integration**: Algorithm outputs are adjusted using CHAMPS gold-standard data
4. **Uncertainty Quantification**: Confidence intervals are calculated for each cause
5. **Results Generation**: Final CSMFs with uncertainty bounds are produced

### Interpreting Results

**Key Metrics:**
- **CSMF**: Cause-Specific Mortality Fraction (percentage of deaths from each cause)
- **Confidence Intervals**: Range of plausible values (95% credible intervals)
- **Calibration Adjustment**: Difference between uncalibrated and calibrated values

**Common Patterns:**
- Large confidence intervals indicate high uncertainty
- Significant adjustments suggest algorithm bias
- Narrow intervals with small adjustments indicate reliable algorithm performance

## Troubleshooting

### Common Issues and Solutions

**Job Stays in "Pending" Status:**
- Check if Docker container is running: `docker ps`
- Verify R package installation: `docker run vacalibration-r-engine R -e "library(vacalibration)"`

**Job Fails Immediately:**
- Check data format matches selected options
- Ensure at least one algorithm is selected
- Verify JSON syntax if providing custom data

**No Results Displayed:**
- Refresh the page (Ctrl+R or Cmd+R)
- Check browser console for errors (F12)
- Verify API is responding: `curl http://localhost:8000/`

**Export Not Working:**
- Check browser download permissions
- Try different browser if issue persists

## Advanced Features

### Using Custom Data

For research datasets, prepare your data in one of these formats:

**Individual-level specific causes:**
```json
[
  {"id": "patient_001", "cause": "Malaria"},
  {"id": "patient_002", "cause": "Pneumonia"}
]
```

**Binary cause matrix:**
```json
[
  [0, 0, 1, 0, 0, 0],  // Death from cause 3
  [1, 0, 0, 0, 0, 0],  // Death from cause 1
  [0, 0, 0, 0, 1, 0]   // Death from cause 5
]
```

**Aggregated counts:**
```json
{
  "malaria": 45,
  "pneumonia": 32,
  "diarrhea": 18,
  "other": 25
}
```

### API Integration

For programmatic access, use the REST API directly:

```bash
# Submit calibration
curl -X POST "http://localhost:8000/calibrate" \
  -H "Content-Type: application/json" \
  -d '{
    "va_data": {"insilicova": "use_example"},
    "age_group": "neonate",
    "country": "Mozambique"
  }'

# Check status
curl "http://localhost:8000/status/{job_id}"

# Get results
curl "http://localhost:8000/result/{job_id}"
```

## Best Practices

1. **Start with example data** to familiarize yourself with the system
2. **Use ensemble mode** when calibrating multiple algorithms
3. **Export results** for important calibrations as backup
4. **Monitor confidence intervals** - very wide intervals may indicate data quality issues
5. **Compare algorithms** by running them separately to understand their biases

## Support and Resources

- **Technical Documentation**: See `/docs/technical.md`
- **API Reference**: Available at `http://localhost:8000/docs`
- **R Package Documentation**: [vacalibration package on GitHub](https://github.com/your-org/vacalibration)
- **CHAMPS Network**: [champshealth.org](https://champshealth.org)

## Glossary

- **VA**: Verbal Autopsy - method to determine cause of death through interviews
- **CSMF**: Cause-Specific Mortality Fraction - proportion of deaths from specific causes
- **CHAMPS**: Child Health and Mortality Prevention Surveillance network
- **Bayesian Calibration**: Statistical method to adjust estimates using prior knowledge
- **Gold Standard**: Reference data from minimally invasive autopsy procedures
- **Ensemble Mode**: Combining multiple algorithms for improved accuracy