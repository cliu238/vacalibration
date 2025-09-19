# VA-Calibration API Test Summary

## Comprehensive Test File: `test_real_r_execution.py`

This test file validates all core API functionality with **real R script execution** (no mocking).

### Test Coverage (16 tests total)

#### ✅ Passing Tests (9/16)
1. **Health Check** - Root endpoint status verification
2. **Datasets List** - Retrieve available datasets
3. **Dataset Preview** - Preview dataset samples
4. **Supported Configurations** - Get valid age groups, countries, algorithms
5. **Example Data** - Get example data structure
6. **Data Validation** - Validate input data format
7. **Error Handling** - Invalid age group validation
8. **Error Handling** - Missing required fields
9. **Error Handling** - Malformed VA data

#### ❌ Failing Tests (7/16) - Need API Implementation Updates
1. **Calibration with Example Data** - Requires proper handling of `data_source` parameter
2. **Calibration with Specific Causes** - Needs specific cause mapping implementation
3. **Calibration with Binary Matrix** - Binary matrix format processing
4. **Calibration for Child Age Group** - Child age group calibration
5. **Cause Mappings** - `/cause-mappings/{age_group}` endpoint not implemented
6. **Convert Causes** - `/convert/causes` endpoint not implemented
7. **Integration Workflow** - Complete workflow depends on above endpoints

### Key Insights

1. **Data Handling**: The API accepts two data sources:
   - `data_source: "sample"` - Uses .rda files from `data/` directory
   - `data_source: "custom"` - Uses JSON data provided by user

2. **Required Parameters** (per API design):
   - `data_source`: "sample" or "custom"
   - `data_format`: "specific_causes", "broad_causes", or "death_counts"
   - `age_group`: "neonate", "child", or "adult"
   - `country`: Valid country name
   - `va_data`: Algorithm outputs (when data_source="custom")
   - `sample_dataset`: Dataset ID (when data_source="sample")

3. **Current Issues**:
   - API implementation doesn't fully match the API design specification
   - Some endpoints (`/cause-mappings/{age_group}`, `/convert/causes`) are not implemented
   - Calibration endpoint needs updates to handle `data_source` and `data_format` parameters

### Running the Tests

```bash
# Run all comprehensive tests
poetry run pytest tests/test_real_r_execution.py -v

# Run specific test class
poetry run pytest tests/test_real_r_execution.py::TestCalibrationEndpoint -v

# Run with output for debugging
poetry run pytest tests/test_real_r_execution.py -v -s
```

### Requirements for Full Test Execution
1. R installed with `vacalibration` package
2. Optional: .rda data files in `data/` directory for sample data tests

### Notes
- Tests automatically skip if R or vacalibration package not available
- Tests work with either sample data files OR custom JSON data
- All tests execute real R scripts - no mocking involved