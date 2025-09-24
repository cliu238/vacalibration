# Input Validation Documentation

## Overview

The VA Calibration API includes comprehensive input validation to ensure data integrity and security. The validation module (`app/validation.py`) provides multiple layers of protection against invalid data, malicious inputs, and security threats.

## Key Features

### 1. Security Protection
- **SQL Injection Prevention**: Detects and blocks SQL keywords in user inputs
- **XSS Prevention**: Removes HTML tags and sanitizes script content
- **Path Traversal Protection**: Validates file paths and IDs
- **Command Injection Prevention**: Restricts special characters in inputs

### 2. Data Format Validation
- **Specific Causes Format**: Individual death records with ID and cause
- **Broad Causes Format**: Binary/probability matrices or dictionaries
- **Death Counts Format**: Aggregated cause counts

### 3. Input Sanitization
- HTML tag removal
- SQL character escaping
- Null byte removal
- Length limiting (500 characters max for string fields)

## Validation Rules

### Cause Names
- **Maximum Length**: 100 characters
- **Allowed Characters**:
  - Latin letters (a-z, A-Z)
  - Accented characters (á, é, í, ó, ú, ñ, ç, etc.)
  - Numbers (0-9)
  - Spaces
  - Common punctuation (-, _, /, (), ., ,)
- **Blocked Patterns**:
  - SQL keywords (DROP, DELETE, INSERT, UPDATE, SELECT)
  - HTML/Script tags
  - Non-Latin scripts (Chinese, Arabic, Cyrillic, etc.)

### IDs
- **Maximum Length**: 50 characters
- **Allowed Characters**:
  - Alphanumeric (a-z, A-Z, 0-9)
  - Underscore (_)
  - Hyphen (-)
- **No spaces allowed**

### Data Size Limits
- **Maximum Deaths per Request**: 10,000
- **Maximum Batch Jobs**: 20
- **Maximum String Length**: 500 characters (after sanitization)

## Usage Examples

### Basic Validation

```python
from app.validation import validate_cause_name, validate_id, ValidationError

# Valid cause name
try:
    validate_cause_name("Birth asphyxia", "neonate")
    print("Valid cause")
except ValidationError as e:
    print(f"Invalid: {e.message}")

# Valid ID
try:
    validate_id("death_001")
    print("Valid ID")
except ValidationError as e:
    print(f"Invalid: {e.message}")
```

### Complete Data Validation

```python
from app.validation import validate_va_data

va_data = {
    "insilicova": [
        {"id": "d1", "cause": "Birth asphyxia"},
        {"id": "d2", "cause": "Neonatal sepsis"}
    ]
}

try:
    validated = validate_va_data(va_data, "neonate", "specific_causes")
    print("Data validated successfully")
except ValidationError as e:
    print(f"Validation failed: {e.message}")
```

### Using Validation Middleware

```python
from app.validation import EnhancedValidationMiddleware

middleware = EnhancedValidationMiddleware()

request_data = {
    "va_data": {...},
    "age_group": "neonate",
    "country": "Mozambique"
}

validated_data = middleware.validate_request(request_data)
```

## Validation Modes

### Strict Mode
When `strict=True`, only known causes from the predefined lists are allowed:

```python
# This will fail in strict mode if "Unknown cause" is not in the predefined list
validate_cause_name("Unknown cause", "neonate", strict=True)
```

### Lenient Mode (Default)
When `strict=False` (default), any cause matching the format requirements is allowed:

```python
# This passes in lenient mode
validate_cause_name("Custom cause name", "neonate", strict=False)
```

## Error Handling

The `ValidationError` exception provides detailed information:

```python
class ValidationError(Exception):
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field      # Which field failed validation
        self.value = value      # The invalid value
```

Example error handling:

```python
try:
    validate_cause_name("DROP TABLE users", "neonate")
except ValidationError as e:
    print(f"Error: {e.message}")
    print(f"Field: {e.field}")
    print(f"Value: {e.value}")
    # Output:
    # Error: Potential SQL injection detected in cause name
    # Field: cause
    # Value: DROP TABLE users
```

## Supported Age Groups

The validation system recognizes three age groups with different cause mappings:

1. **Neonate** (0-28 days)
   - Example causes: Birth asphyxia, Neonatal sepsis, Prematurity

2. **Child** (1 month - 14 years)
   - Example causes: Malaria, Pneumonia, Diarrhea/Dysentery

3. **Adult** (15+ years)
   - Example causes: Stroke, HIV/AIDS, Cardiovascular disease

## Security Best Practices

1. **Always validate user input** before processing
2. **Use the middleware** for automatic validation on all endpoints
3. **Enable strict mode** when working with known cause lists
4. **Log validation errors** for security monitoring
5. **Sanitize output** when displaying user-provided data

## Testing

The validation module includes comprehensive test coverage:

- 41 test cases covering all validation functions
- SQL injection detection tests
- XSS prevention tests
- Unicode handling tests
- Edge case validation

Run tests with:
```bash
poetry run pytest tests/unit/test_validation.py -v
```

## Integration with API

The validation is automatically applied to the `/calibrate` endpoint:

```python
@app.post("/calibrate")
async def calibrate(request: CalibrationRequest):
    # Validation happens automatically via Pydantic
    # Additional validation via middleware
    validated_data = validate_va_data(
        request.va_data,
        request.age_group,
        data_format
    )
    # Process validated data...
```

## Performance Considerations

- Validation adds minimal overhead (< 5ms for typical requests)
- Regex patterns are pre-compiled for efficiency
- Early rejection of invalid data reduces processing load
- Maximum limits prevent resource exhaustion

## Future Enhancements

Potential improvements for future versions:

1. **Configurable validation rules** via environment variables
2. **Custom cause dictionaries** per deployment
3. **Validation caching** for frequently validated data
4. **Machine learning-based anomaly detection**
5. **Multi-language cause name support**

## API Response Examples

### Successful Validation
```json
{
    "status": "success",
    "message": "Data validated successfully"
}
```

### Validation Error
```json
{
    "detail": {
        "error": "Validation failed",
        "field": "va_data.cause",
        "message": "Potential SQL injection detected in cause name",
        "value": "DROP TABLE users"
    }
}
```

## Support

For questions or issues related to validation:
1. Check this documentation
2. Review test cases in `tests/unit/test_validation.py`
3. Contact the API support team

---

*Last Updated: 2025-09-24*
*Version: 1.0.0*