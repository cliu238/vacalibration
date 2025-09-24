"""
Enhanced input validation for VA calibration API
"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator
import re
from enum import Enum

# Valid cause names for different age groups
VALID_NEONATE_CAUSES = {
    # Broad causes
    "congenital_malformation", "pneumonia", "sepsis_meningitis_inf",
    "ipre", "other", "prematurity",
    # Specific causes
    "Birth asphyxia", "Neonatal sepsis", "Neonatal pneumonia",
    "Prematurity", "Congenital malformation",
    "Other and unspecified neonatal CoD", "Road traffic accident",
    "Accid fall"
}

VALID_CHILD_CAUSES = {
    # Broad causes
    "malaria", "pneumonia", "diarrhea", "severe_malnutrition",
    "hiv", "injury", "other", "other_infections", "nn_causes",
    # Specific causes
    "Malaria", "Pneumonia", "Diarrhea/Dysentery", "Severe malnutrition",
    "HIV/AIDS related death", "Injury", "Measles", "Meningitis",
    "Tuberculosis", "Other infections", "Other non-infectious"
}

VALID_ADULT_CAUSES = {
    # Common adult causes
    "Stroke", "HIV/AIDS related death", "Digestive neoplasms",
    "Other and unspecified cardiac dis", "Renal failure",
    "Diabetes", "Tuberculosis", "Chronic obstructive pulmonary disease",
    "Cardiovascular disease", "Cancer", "Injury", "Suicide",
    "Maternal death", "Other infections", "Other non-communicable"
}

# Data size limits
MAX_DEATHS_PER_REQUEST = 10000
MAX_BATCH_JOBS = 20
MAX_CAUSE_NAME_LENGTH = 100
MAX_ID_LENGTH = 50

# Patterns for validation
ID_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
# Allow Latin letters (including accented), numbers, spaces, and common punctuation
# Explicitly list allowed characters to exclude Chinese/Arabic/etc.
CAUSE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_/(),.áéíóúñÁÉÍÓÚÑàèìòùÀÈÌÒÙäëïöüÄËÏÖÜâêîôûÂÊÎÔÛçÇãÃõÕ]+$')


class ValidationError(Exception):
    """Custom validation error with detailed information"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


def validate_cause_name(cause: str, age_group: str, strict: bool = False) -> bool:
    """
    Validate that a cause name is valid for the given age group

    Args:
        cause: The cause name to validate
        age_group: The age group (neonate, child, adult)
        strict: If True, only allow known causes. If False, allow any valid format

    Returns:
        True if valid, raises ValidationError otherwise
    """
    # Check length
    if len(cause) > MAX_CAUSE_NAME_LENGTH:
        raise ValidationError(
            f"Cause name too long (max {MAX_CAUSE_NAME_LENGTH} characters)",
            field="cause",
            value=cause
        )

    # Check for SQL injection patterns first (before format check)
    if any(keyword in cause.upper() for keyword in ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT']):
        raise ValidationError(
            "Potential SQL injection detected in cause name",
            field="cause",
            value=cause
        )

    # Check format
    if not CAUSE_NAME_PATTERN.match(cause):
        raise ValidationError(
            "Invalid cause name format. Only alphanumeric, spaces, and common punctuation allowed",
            field="cause",
            value=cause
        )

    # In strict mode, validate against known causes
    if strict:
        valid_causes = set()
        if age_group == "neonate":
            valid_causes = VALID_NEONATE_CAUSES
        elif age_group == "child":
            valid_causes = VALID_CHILD_CAUSES
        elif age_group == "adult":
            valid_causes = VALID_ADULT_CAUSES

        if valid_causes and cause not in valid_causes:
            raise ValidationError(
                f"Unknown cause '{cause}' for age group '{age_group}'",
                field="cause",
                value=cause
            )

    return True


def validate_id(id_value: str) -> bool:
    """
    Validate that an ID is in proper format

    Args:
        id_value: The ID to validate

    Returns:
        True if valid, raises ValidationError otherwise
    """
    # Check length
    if len(id_value) > MAX_ID_LENGTH:
        raise ValidationError(
            f"ID too long (max {MAX_ID_LENGTH} characters)",
            field="id",
            value=id_value
        )

    # Check format
    if not ID_PATTERN.match(id_value):
        raise ValidationError(
            "Invalid ID format. Only alphanumeric, underscore, and hyphen allowed",
            field="id",
            value=id_value
        )

    return True


def validate_va_data(va_data: Dict[str, Any], age_group: str, data_format: str) -> Dict[str, Any]:
    """
    Comprehensive validation of VA data

    Args:
        va_data: The VA data to validate
        age_group: The age group for validation
        data_format: The expected data format

    Returns:
        Validated and cleaned data
    """
    validated = {}

    for algo_name, data in va_data.items():
        # Check algorithm name
        if not algo_name.replace("_", "").isalnum():
            raise ValidationError(
                f"Invalid algorithm name: {algo_name}",
                field="va_data",
                value=algo_name
            )

        # Special case for example data
        if data == "use_example":
            validated[algo_name] = data
            continue

        # Validate based on format
        if data_format == "specific_causes":
            validated[algo_name] = validate_specific_causes(data, age_group)
        elif data_format == "broad_causes":
            validated[algo_name] = validate_broad_causes(data, age_group)
        elif data_format == "death_counts":
            validated[algo_name] = validate_death_counts(data, age_group)
        else:
            raise ValidationError(
                f"Unknown data format: {data_format}",
                field="data_format",
                value=data_format
            )

    return validated


def validate_specific_causes(data: List[Dict], age_group: str) -> List[Dict]:
    """
    Validate specific cause format data

    Args:
        data: List of death records with ID and cause
        age_group: Age group for validation

    Returns:
        Validated data
    """
    if not isinstance(data, list):
        raise ValidationError(
            "Specific causes data must be a list",
            field="va_data",
            value=type(data).__name__
        )

    if len(data) > MAX_DEATHS_PER_REQUEST:
        raise ValidationError(
            f"Too many deaths in request (max {MAX_DEATHS_PER_REQUEST})",
            field="va_data",
            value=len(data)
        )

    validated_data = []
    seen_ids = set()

    for i, record in enumerate(data):
        if not isinstance(record, dict):
            raise ValidationError(
                f"Record {i} must be a dictionary",
                field=f"va_data[{i}]",
                value=type(record).__name__
            )

        # Check required fields
        id_field = record.get('id') or record.get('ID')
        cause_field = record.get('cause')

        if not id_field:
            raise ValidationError(
                f"Record {i} missing 'id' or 'ID' field",
                field=f"va_data[{i}]",
                value=record
            )

        if not cause_field:
            raise ValidationError(
                f"Record {i} missing 'cause' field",
                field=f"va_data[{i}]",
                value=record
            )

        # Validate ID
        validate_id(str(id_field))

        # Check for duplicate IDs
        if id_field in seen_ids:
            raise ValidationError(
                f"Duplicate ID: {id_field}",
                field=f"va_data[{i}].id",
                value=id_field
            )
        seen_ids.add(id_field)

        # Validate cause (with lenient mode by default)
        validate_cause_name(cause_field, age_group, strict=False)

        validated_data.append({
            'id': str(id_field),
            'cause': cause_field
        })

    return validated_data


def validate_broad_causes(data: Union[List[List], Dict], age_group: str) -> Union[List[List], Dict]:
    """
    Validate broad cause format (binary matrix or dict)

    Args:
        data: Binary matrix or dictionary of probabilities
        age_group: Age group for validation

    Returns:
        Validated data
    """
    if isinstance(data, list):
        # Binary matrix format
        if not all(isinstance(row, list) for row in data):
            raise ValidationError(
                "Broad causes matrix must be a list of lists",
                field="va_data",
                value="mixed types in matrix"
            )

        if len(data) > MAX_DEATHS_PER_REQUEST:
            raise ValidationError(
                f"Too many deaths in matrix (max {MAX_DEATHS_PER_REQUEST})",
                field="va_data",
                value=len(data)
            )

        # Check matrix consistency
        if data:
            row_length = len(data[0])
            for i, row in enumerate(data):
                if len(row) != row_length:
                    raise ValidationError(
                        f"Inconsistent row length in matrix at row {i}",
                        field=f"va_data[{i}]",
                        value=len(row)
                    )

                # Validate values (should be 0 or 1 for binary, or probabilities)
                for j, val in enumerate(row):
                    if not isinstance(val, (int, float)):
                        raise ValidationError(
                            f"Invalid value type at [{i}][{j}]",
                            field=f"va_data[{i}][{j}]",
                            value=type(val).__name__
                        )

                    # Check if binary or probability
                    if val < 0 or val > 1:
                        raise ValidationError(
                            f"Value must be between 0 and 1 at [{i}][{j}]",
                            field=f"va_data[{i}][{j}]",
                            value=val
                        )

    elif isinstance(data, dict):
        # Dictionary format (cause -> list of values)
        for cause, values in data.items():
            validate_cause_name(cause, age_group, strict=False)

            if not isinstance(values, list):
                raise ValidationError(
                    f"Values for cause '{cause}' must be a list",
                    field=f"va_data.{cause}",
                    value=type(values).__name__
                )

            if len(values) > MAX_DEATHS_PER_REQUEST:
                raise ValidationError(
                    f"Too many values for cause '{cause}' (max {MAX_DEATHS_PER_REQUEST})",
                    field=f"va_data.{cause}",
                    value=len(values)
                )
    else:
        raise ValidationError(
            "Broad causes must be a matrix (list of lists) or dictionary",
            field="va_data",
            value=type(data).__name__
        )

    return data


def validate_death_counts(data: Dict[str, int], age_group: str) -> Dict[str, int]:
    """
    Validate death counts format

    Args:
        data: Dictionary of cause -> count
        age_group: Age group for validation

    Returns:
        Validated data
    """
    if not isinstance(data, dict):
        raise ValidationError(
            "Death counts must be a dictionary",
            field="va_data",
            value=type(data).__name__
        )

    total_deaths = 0
    validated = {}

    for cause, count in data.items():
        validate_cause_name(cause, age_group, strict=False)

        if not isinstance(count, int):
            raise ValidationError(
                f"Count for cause '{cause}' must be an integer",
                field=f"va_data.{cause}",
                value=type(count).__name__
            )

        if count < 0:
            raise ValidationError(
                f"Count for cause '{cause}' cannot be negative",
                field=f"va_data.{cause}",
                value=count
            )

        total_deaths += count
        validated[cause] = count

    if total_deaths > MAX_DEATHS_PER_REQUEST:
        raise ValidationError(
            f"Total death count exceeds maximum ({MAX_DEATHS_PER_REQUEST})",
            field="va_data",
            value=total_deaths
        )

    return validated


def sanitize_input(value: str) -> str:
    """
    Sanitize input string to prevent injection attacks

    Args:
        value: Input string to sanitize

    Returns:
        Sanitized string
    """
    # Remove any HTML/script tags
    value = re.sub(r'<[^>]*>', '', value)

    # Escape special characters
    value = value.replace("'", "''")  # SQL escape
    value = value.replace('"', '""')
    value = value.replace('\\', '\\\\')

    # Remove null bytes
    value = value.replace('\x00', '')

    # Limit length
    if len(value) > 500:
        value = value[:500]

    return value


class EnhancedValidationMiddleware:
    """
    Middleware to apply enhanced validation to all requests
    """

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode

    def validate_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize request data

        Args:
            request_data: Raw request data

        Returns:
            Validated and sanitized data
        """
        validated = {}

        # Validate VA data if present
        if 'va_data' in request_data:
            age_group = request_data.get('age_group', 'adult')
            data_format = request_data.get('data_format', 'specific_causes')

            validated['va_data'] = validate_va_data(
                request_data['va_data'],
                age_group,
                data_format
            )

        # Sanitize string fields
        for field in ['country', 'age_group', 'mmat_type']:
            if field in request_data:
                validated[field] = sanitize_input(str(request_data[field]))

        # Copy boolean fields
        for field in ['ensemble', 'async']:
            if field in request_data:
                validated[field] = bool(request_data[field])

        return validated