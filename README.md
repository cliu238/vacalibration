# VA-Calibration

Calibration of Computer-Coded Verbal Autopsy (CCVA) algorithms using gold-standard data from the CHAMPS project.

## Quick Start with Docker

### Build the Docker image
```bash
docker build -t vacalib .
```

### Run the example
```bash
docker run --rm vacalib
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

## Package Details

- **Version**: 2.1
- **License**: GPL-2
- **Authors**: Sandipan Pramanik et al.
- **Supported algorithms**: EAVA, InSilicoVA, InterVA
- **Age groups**: Neonates (0-27 days), Children (1-59 months)