"""
Comprehensive tests for input validation module
"""

import pytest
from app.validation import (
    validate_cause_name,
    validate_id,
    validate_va_data,
    validate_specific_causes,
    validate_broad_causes,
    validate_death_counts,
    sanitize_input,
    ValidationError,
    EnhancedValidationMiddleware
)


class TestCauseValidation:
    """Test cause name validation"""

    def test_valid_cause_names(self):
        """Test valid cause names pass validation"""
        # Valid neonate causes
        assert validate_cause_name("Birth asphyxia", "neonate")
        assert validate_cause_name("Neonatal sepsis", "neonate")
        assert validate_cause_name("Prematurity", "neonate")

        # Valid child causes
        assert validate_cause_name("Malaria", "child")
        assert validate_cause_name("Pneumonia", "child")
        assert validate_cause_name("Diarrhea/Dysentery", "child")

        # Valid adult causes
        assert validate_cause_name("Stroke", "adult")
        assert validate_cause_name("HIV/AIDS related death", "adult")
        assert validate_cause_name("Cardiovascular disease", "adult")

    def test_invalid_cause_format(self):
        """Test invalid cause formats are rejected"""
        with pytest.raises(ValidationError) as exc_info:
            validate_cause_name("Cause@#$%", "neonate")
        assert "Invalid cause name format" in str(exc_info.value)

    def test_cause_too_long(self):
        """Test overly long cause names are rejected"""
        long_cause = "A" * 101
        with pytest.raises(ValidationError) as exc_info:
            validate_cause_name(long_cause, "neonate")
        assert "too long" in str(exc_info.value)

    def test_sql_injection_detection(self):
        """Test SQL injection attempts are caught"""
        sql_attempts = [
            "DROP TABLE users",
            "DELETE FROM deaths",
            "'; INSERT INTO admin",
            "UPDATE causes SET",
            "SELECT * FROM passwords"
        ]

        for attempt in sql_attempts:
            with pytest.raises(ValidationError) as exc_info:
                validate_cause_name(attempt, "neonate")
            assert "SQL injection" in str(exc_info.value)

    def test_strict_mode_validation(self):
        """Test strict mode only allows known causes"""
        # Valid known cause
        assert validate_cause_name("Birth asphyxia", "neonate", strict=True)

        # Unknown cause should fail in strict mode
        with pytest.raises(ValidationError) as exc_info:
            validate_cause_name("Unknown cause xyz", "neonate", strict=True)
        assert "Unknown cause" in str(exc_info.value)


class TestIDValidation:
    """Test ID validation"""

    def test_valid_ids(self):
        """Test valid IDs pass validation"""
        valid_ids = [
            "death_001",
            "D-123",
            "case_2024_01",
            "ID123456",
            "test-id-1"
        ]

        for id_val in valid_ids:
            assert validate_id(id_val)

    def test_invalid_id_format(self):
        """Test invalid ID formats are rejected"""
        invalid_ids = [
            "id@123",
            "death#001",
            "case with spaces",
            "id/123",
            "test\\id"
        ]

        for id_val in invalid_ids:
            with pytest.raises(ValidationError) as exc_info:
                validate_id(id_val)
            assert "Invalid ID format" in str(exc_info.value)

    def test_id_too_long(self):
        """Test overly long IDs are rejected"""
        long_id = "A" * 51
        with pytest.raises(ValidationError) as exc_info:
            validate_id(long_id)
        assert "too long" in str(exc_info.value)


class TestSpecificCausesValidation:
    """Test specific causes format validation"""

    def test_valid_specific_causes(self):
        """Test valid specific causes data"""
        data = [
            {"id": "death_001", "cause": "Birth asphyxia"},
            {"id": "death_002", "cause": "Neonatal sepsis"}
        ]

        result = validate_specific_causes(data, "neonate")
        assert len(result) == 2
        assert result[0]["id"] == "death_001"
        assert result[0]["cause"] == "Birth asphyxia"

    def test_accepts_uppercase_id_field(self):
        """Test that 'ID' (uppercase) is accepted"""
        data = [
            {"ID": "death_001", "cause": "Birth asphyxia"}
        ]

        result = validate_specific_causes(data, "neonate")
        assert result[0]["id"] == "death_001"

    def test_missing_required_fields(self):
        """Test missing required fields are caught"""
        # Missing ID
        with pytest.raises(ValidationError) as exc_info:
            validate_specific_causes([{"cause": "Birth asphyxia"}], "neonate")
        assert "missing 'id'" in str(exc_info.value)

        # Missing cause
        with pytest.raises(ValidationError) as exc_info:
            validate_specific_causes([{"id": "death_001"}], "neonate")
        assert "missing 'cause'" in str(exc_info.value)

    def test_duplicate_ids_rejected(self):
        """Test duplicate IDs are rejected"""
        data = [
            {"id": "death_001", "cause": "Birth asphyxia"},
            {"id": "death_001", "cause": "Neonatal sepsis"}
        ]

        with pytest.raises(ValidationError) as exc_info:
            validate_specific_causes(data, "neonate")
        assert "Duplicate ID" in str(exc_info.value)

    def test_max_deaths_limit(self):
        """Test maximum deaths limit is enforced"""
        data = [{"id": f"death_{i}", "cause": "Birth asphyxia"} for i in range(10001)]

        with pytest.raises(ValidationError) as exc_info:
            validate_specific_causes(data, "neonate")
        assert "Too many deaths" in str(exc_info.value)

    def test_invalid_data_types(self):
        """Test invalid data types are caught"""
        # Not a list
        with pytest.raises(ValidationError):
            validate_specific_causes("not a list", "neonate")

        # Not dictionaries
        with pytest.raises(ValidationError):
            validate_specific_causes(["not", "dictionaries"], "neonate")


class TestBroadCausesValidation:
    """Test broad causes format validation"""

    def test_valid_binary_matrix(self):
        """Test valid binary matrix format"""
        matrix = [
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [1, 1, 0, 0]
        ]

        result = validate_broad_causes(matrix, "neonate")
        assert result == matrix

    def test_valid_probability_matrix(self):
        """Test valid probability matrix format"""
        matrix = [
            [0.8, 0.1, 0.05, 0.05],
            [0.2, 0.6, 0.1, 0.1],
            [0.3, 0.3, 0.2, 0.2]
        ]

        result = validate_broad_causes(matrix, "neonate")
        assert result == matrix

    def test_inconsistent_row_lengths(self):
        """Test inconsistent row lengths are caught"""
        matrix = [
            [1, 0, 1, 0],
            [0, 1, 0],  # Wrong length
            [1, 1, 0, 0]
        ]

        with pytest.raises(ValidationError) as exc_info:
            validate_broad_causes(matrix, "neonate")
        assert "Inconsistent row length" in str(exc_info.value)

    def test_invalid_values(self):
        """Test invalid values are caught"""
        # Value > 1
        matrix = [[1, 0, 2, 0]]
        with pytest.raises(ValidationError) as exc_info:
            validate_broad_causes(matrix, "neonate")
        assert "between 0 and 1" in str(exc_info.value)

        # Negative value
        matrix = [[1, 0, -0.5, 0]]
        with pytest.raises(ValidationError) as exc_info:
            validate_broad_causes(matrix, "neonate")
        assert "between 0 and 1" in str(exc_info.value)

    def test_valid_dictionary_format(self):
        """Test valid dictionary format"""
        data = {
            "Birth asphyxia": [0.8, 0.1, 0.2],
            "Neonatal sepsis": [0.1, 0.7, 0.3]
        }

        result = validate_broad_causes(data, "neonate")
        assert result == data

    def test_dictionary_invalid_values(self):
        """Test dictionary with invalid values"""
        data = {
            "Birth asphyxia": "not a list"
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_broad_causes(data, "neonate")
        assert "must be a list" in str(exc_info.value)


class TestDeathCountsValidation:
    """Test death counts format validation"""

    def test_valid_death_counts(self):
        """Test valid death counts"""
        data = {
            "Birth asphyxia": 10,
            "Neonatal sepsis": 25,
            "Prematurity": 15
        }

        result = validate_death_counts(data, "neonate")
        assert result == data

    def test_invalid_count_type(self):
        """Test non-integer counts are rejected"""
        data = {
            "Birth asphyxia": "ten"
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_death_counts(data, "neonate")
        assert "must be an integer" in str(exc_info.value)

    def test_negative_counts(self):
        """Test negative counts are rejected"""
        data = {
            "Birth asphyxia": -5
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_death_counts(data, "neonate")
        assert "cannot be negative" in str(exc_info.value)

    def test_total_deaths_limit(self):
        """Test total deaths limit is enforced"""
        data = {
            "Birth asphyxia": 5000,
            "Neonatal sepsis": 5001
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_death_counts(data, "neonate")
        assert "exceeds maximum" in str(exc_info.value)


class TestSanitization:
    """Test input sanitization"""

    def test_html_tags_removed(self):
        """Test HTML tags are removed"""
        # Note: single quotes get escaped to double single quotes for SQL safety
        assert sanitize_input("<script>alert('xss')</script>") == "alert(''xss'')"
        assert sanitize_input("<b>bold</b>text") == "boldtext"

    def test_sql_escaping(self):
        """Test SQL special characters are escaped"""
        assert sanitize_input("O'Brien") == "O''Brien"
        assert sanitize_input('Say "hello"') == 'Say ""hello""'

    def test_null_bytes_removed(self):
        """Test null bytes are removed"""
        assert sanitize_input("test\x00string") == "teststring"

    def test_length_limiting(self):
        """Test strings are truncated at 500 chars"""
        long_string = "A" * 600
        result = sanitize_input(long_string)
        assert len(result) == 500


class TestVADataValidation:
    """Test complete VA data validation"""

    def test_specific_causes_format(self):
        """Test specific causes format validation"""
        va_data = {
            "insilicova": [
                {"id": "d1", "cause": "Birth asphyxia"},
                {"id": "d2", "cause": "Neonatal sepsis"}
            ]
        }

        result = validate_va_data(va_data, "neonate", "specific_causes")
        assert "insilicova" in result
        assert len(result["insilicova"]) == 2

    def test_use_example_special_case(self):
        """Test 'use_example' passes through"""
        va_data = {
            "insilicova": "use_example"
        }

        result = validate_va_data(va_data, "neonate", "specific_causes")
        assert result["insilicova"] == "use_example"

    def test_invalid_algorithm_name(self):
        """Test invalid algorithm names are rejected"""
        va_data = {
            "invalid@algo": [{"id": "d1", "cause": "Birth asphyxia"}]
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_va_data(va_data, "neonate", "specific_causes")
        assert "Invalid algorithm name" in str(exc_info.value)

    def test_unknown_data_format(self):
        """Test unknown data formats are rejected"""
        va_data = {
            "insilicova": []
        }

        with pytest.raises(ValidationError) as exc_info:
            validate_va_data(va_data, "neonate", "unknown_format")
        assert "Unknown data format" in str(exc_info.value)


class TestValidationMiddleware:
    """Test validation middleware"""

    def test_middleware_validates_va_data(self):
        """Test middleware validates VA data"""
        middleware = EnhancedValidationMiddleware()

        request_data = {
            "va_data": {
                "insilicova": [
                    {"id": "d1", "cause": "Birth asphyxia"}
                ]
            },
            "age_group": "neonate",
            "data_format": "specific_causes"
        }

        result = middleware.validate_request(request_data)
        assert "va_data" in result
        assert result["va_data"]["insilicova"][0]["id"] == "d1"

    def test_middleware_sanitizes_strings(self):
        """Test middleware sanitizes string fields"""
        middleware = EnhancedValidationMiddleware()

        request_data = {
            "country": "Mozambique<script>",
            "age_group": "neonate'--",
            "mmat_type": "prior\x00"
        }

        result = middleware.validate_request(request_data)
        assert result["country"] == "Mozambique"
        assert result["age_group"] == "neonate''--"
        assert "\x00" not in result["mmat_type"]

    def test_middleware_preserves_booleans(self):
        """Test middleware preserves boolean fields"""
        middleware = EnhancedValidationMiddleware()

        request_data = {
            "ensemble": True,
            "async": False
        }

        result = middleware.validate_request(request_data)
        assert result["ensemble"] is True
        assert result["async"] is False


class TestXSSPrevention:
    """Test XSS prevention"""

    def test_xss_in_cause_names(self):
        """Test XSS attempts in cause names are sanitized"""
        data = [
            {"id": "d1", "cause": "<img src=x onerror=alert(1)>"}
        ]

        # Should not raise error, but cause should be validated
        with pytest.raises(ValidationError) as exc_info:
            validate_specific_causes(data, "neonate")
        assert "Invalid cause name format" in str(exc_info.value)

    def test_javascript_urls(self):
        """Test javascript: URLs are caught"""
        cause = "javascript:alert(1)"

        # The colon makes it invalid format
        with pytest.raises(ValidationError) as exc_info:
            validate_cause_name(cause, "neonate")
        # Should fail format validation due to special chars


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_data(self):
        """Test empty data handling"""
        # Empty list
        result = validate_specific_causes([], "neonate")
        assert result == []

        # Empty dictionary
        result = validate_death_counts({}, "neonate")
        assert result == {}

    def test_unicode_handling(self):
        """Test Unicode characters are handled"""
        # Valid Unicode in cause names (accented characters are allowed)
        assert validate_cause_name("Pneumonía", "child")  # Spanish with accent
        assert validate_cause_name("Infecção", "adult")  # Portuguese

        # Chinese characters should fail format validation
        with pytest.raises(ValidationError):
            validate_cause_name("肺炎", "child")  # Chinese characters not in allowed pattern

    def test_case_sensitivity(self):
        """Test case sensitivity in validation"""
        # Algorithm names should be case-insensitive for alphanumeric check
        va_data = {
            "InSilicoVA": "use_example"
        }
        result = validate_va_data(va_data, "neonate", "specific_causes")
        assert "InSilicoVA" in result

    def test_whitespace_handling(self):
        """Test whitespace in inputs"""
        # Cause names can have spaces
        assert validate_cause_name("Birth asphyxia", "neonate")

        # IDs should not have spaces
        with pytest.raises(ValidationError):
            validate_id("death 001")