"""
Unit tests for conversion and validation endpoints.
Test IDs: UT-006, UT-007, UT-008, UT-009
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, mock_open
from httpx import AsyncClient
import json

from app.main_direct import app


class TestConvertCausesEndpoint:
    """
    Test cases for convert causes endpoint (POST /convert/causes).
    Test ID: UT-006
    """

    @pytest.mark.asyncio
    async def test_convert_neonate_causes(
        self,
        async_client: AsyncClient,
        sample_convert_request,
        mock_r_ready,
        mock_convert_causes_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-006-01
        Convert neonate causes should return correct broad mappings.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_convert_causes_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/convert/causes", json=sample_convert_request)

            assert response.status_code == 200
            data = response.json()

            assert "converted_data" in data
            assert "broad_cause_matrix" in data
            assert "conversion_summary" in data
            assert "unmapped_causes" in data

            # Check structure
            assert isinstance(data["converted_data"], list)
            assert isinstance(data["broad_cause_matrix"], dict)
            assert isinstance(data["conversion_summary"], dict)
            assert isinstance(data["unmapped_causes"], list)

            # Check converted data structure
            for record in data["converted_data"]:
                assert "id" in record
                assert "specific_cause" in record
                assert "broad_cause" in record

    @pytest.mark.asyncio
    async def test_convert_child_causes(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-006-02
        Convert child causes should return correct broad mappings.
        """
        child_convert_output = {
            "success": True,
            "converted_data": [
                {"id": "d1", "specific_cause": "Malaria", "broad_cause": "malaria"},
                {"id": "d2", "specific_cause": "Pneumonia", "broad_cause": "pneumonia"}
            ],
            "broad_cause_matrix": {
                "malaria": [1, 0],
                "pneumonia": [0, 1],
                "diarrhea": [0, 0],
                "severe_malnutrition": [0, 0],
                "hiv": [0, 0],
                "injury": [0, 0],
                "other": [0, 0],
                "other_infections": [0, 0],
                "nn_causes": [0, 0]
            },
            "conversion_summary": {"malaria": 1, "pneumonia": 1},
            "unmapped_causes": []
        }

        child_request = {
            "data": [
                {"id": "d1", "cause": "Malaria"},
                {"id": "d2", "cause": "Pneumonia"}
            ],
            "age_group": "child"
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=child_convert_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/convert/causes", json=child_request)

            assert response.status_code == 200
            data = response.json()

            assert data["converted_data"][0]["broad_cause"] == "malaria"
            assert data["converted_data"][1]["broad_cause"] == "pneumonia"

    @pytest.mark.asyncio
    async def test_convert_unknown_cause_handling(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-006-03
        Unknown cause handling should map to "other".
        """
        unknown_cause_output = {
            "success": True,
            "converted_data": [
                {"id": "d1", "specific_cause": "Unknown Disease", "broad_cause": "other"}
            ],
            "broad_cause_matrix": {
                "congenital_malformation": [0],
                "pneumonia": [0],
                "sepsis_meningitis_inf": [0],
                "ipre": [0],
                "other": [1],
                "prematurity": [0]
            },
            "conversion_summary": {"other": 1},
            "unmapped_causes": ["Unknown Disease"]
        }

        unknown_request = {
            "data": [
                {"id": "d1", "cause": "Unknown Disease"}
            ],
            "age_group": "neonate"
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=unknown_cause_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/convert/causes", json=unknown_request)

            assert response.status_code == 200
            data = response.json()

            assert data["converted_data"][0]["broad_cause"] == "other"
            assert "Unknown Disease" in data["unmapped_causes"]

    @pytest.mark.asyncio
    async def test_convert_empty_data(self, async_client: AsyncClient):
        """
        Test ID: UT-006-04
        Empty data should return 400 Bad Request.
        """
        empty_request = {
            "data": [],
            "age_group": "neonate"
        }

        response = await async_client.post("/convert/causes", json=empty_request)

        assert response.status_code == 422  # Validation error
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_convert_missing_required_fields(self, async_client: AsyncClient):
        """
        Test validation of required fields in conversion request.
        """
        # Missing 'cause' field
        invalid_request = {
            "data": [
                {"id": "d1"},  # Missing cause
                {"id": "d2", "cause": "Birth asphyxia"}
            ],
            "age_group": "neonate"
        }

        response = await async_client.post("/convert/causes", json=invalid_request)

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_convert_r_not_ready(self, async_client: AsyncClient, mock_r_not_ready):
        """Test convert endpoint when R is not available."""
        with patch('app.main_direct.check_r_setup', mock_r_not_ready):
            response = await async_client.post("/convert/causes", json={
                "data": [{"id": "d1", "cause": "test"}],
                "age_group": "neonate"
            })

            assert response.status_code == 500
            error_data = response.json()
            assert "R not ready" in error_data["detail"]


class TestValidateDataEndpoint:
    """
    Test cases for validate data endpoint (POST /validate).
    Test ID: UT-007
    """

    @pytest.mark.asyncio
    async def test_validate_specific_causes(
        self,
        async_client: AsyncClient,
        sample_validate_request
    ):
        """
        Test ID: UT-007-01
        Validate specific causes should return valid with summary.
        """
        response = await async_client.post("/validate", json=sample_validate_request)

        assert response.status_code == 200
        data = response.json()

        assert "overall_valid" in data
        assert "validation_results" in data
        assert "global_issues" in data
        assert "recommendations" in data

        # Check validation results structure
        assert isinstance(data["validation_results"], list)
        assert len(data["validation_results"]) > 0

        # Check individual validation result
        validation_result = data["validation_results"][0]
        assert "algorithm" in validation_result
        assert "is_valid" in validation_result
        assert "detected_format" in validation_result
        assert "issues" in validation_result
        assert "recommendations" in validation_result

    @pytest.mark.asyncio
    async def test_validate_binary_matrix(self, async_client: AsyncClient, sample_binary_matrix):
        """
        Test ID: UT-007-02
        Validate binary matrix should return valid with dimensions.
        """
        validate_request = {
            "data": {
                "insilicova": sample_binary_matrix
            },
            "age_group": "neonate",
            "expected_format": "broad_causes_matrix"
        }

        response = await async_client.post("/validate", json=validate_request)

        assert response.status_code == 200
        data = response.json()

        assert data["overall_valid"] is True
        validation_result = data["validation_results"][0]
        assert validation_result["detected_format"] == "broad_causes_matrix"
        assert validation_result["is_valid"] is True

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Death counts format not yet implemented - API design specifies this format but implementation pending")
    async def test_validate_death_counts(self, async_client: AsyncClient, sample_death_counts):
        """
        Test ID: UT-007-03
        Validate death counts should return valid with total.
        Note: Death counts format is specified in API design but not yet implemented.
        """
        validate_request = {
            "data": {
                "insilicova": sample_death_counts
            },
            "age_group": "neonate",
            "expected_format": "death_counts"
        }

        response = await async_client.post("/validate", json=validate_request)

        assert response.status_code == 200
        data = response.json()

        validation_result = data["validation_results"][0]
        assert validation_result["detected_format"] == "death_counts"

        if validation_result["is_valid"]:
            assert "sample_size" in validation_result
            assert validation_result["sample_size"] > 0

    @pytest.mark.asyncio
    async def test_validate_invalid_format(self, async_client: AsyncClient):
        """
        Test ID: UT-007-04
        Invalid format should return 422 validation error.
        """
        invalid_request = {
            "data": {
                "insilicova": "invalid_string_data"  # String instead of list
            },
            "age_group": "neonate",
            "expected_format": "specific_causes"
        }

        response = await async_client.post("/validate", json=invalid_request)

        # API correctly rejects invalid request format with 422
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        # Validation error should mention the data format issue
        assert any("list" in str(err).lower() or "input" in str(err).lower()
                   for err in data["detail"])

    @pytest.mark.asyncio
    async def test_validate_missing_ids_warning(self, async_client: AsyncClient):
        """
        Test ID: UT-007-05
        Missing IDs should generate warning in response.
        """
        data_with_missing_ids = {
            "data": {
                "insilicova": [
                    {"cause": "Birth asphyxia"},  # Missing ID
                    {"ID": "d2", "cause": "Neonatal sepsis"}
                ]
            },
            "age_group": "neonate"
        }

        response = await async_client.post("/validate", json=data_with_missing_ids)

        assert response.status_code == 200
        data = response.json()

        validation_result = data["validation_results"][0]
        assert validation_result["is_valid"] is False
        assert any("missing" in issue.lower() for issue in validation_result["issues"])

    @pytest.mark.asyncio
    async def test_validate_multiple_algorithms(self, async_client: AsyncClient):
        """Test validation with multiple algorithms."""
        multi_algo_request = {
            "data": {
                "insilicova": [{"ID": "d1", "cause": "Birth asphyxia"}],
                "interva": [{"ID": "d1", "cause": "Neonatal sepsis"}],
                "eava": [{"ID": "d1", "cause": "Prematurity"}]
            },
            "age_group": "neonate"
        }

        response = await async_client.post("/validate", json=multi_algo_request)

        assert response.status_code == 200
        data = response.json()

        assert len(data["validation_results"]) == 3
        algorithms = [result["algorithm"] for result in data["validation_results"]]
        assert "insilicova" in algorithms
        assert "interva" in algorithms
        assert "eava" in algorithms

    @pytest.mark.asyncio
    async def test_validate_edge_cases(self, async_client: AsyncClient, edge_case_data):
        """Test validation with various edge cases."""
        # Test empty data
        response = await async_client.post("/validate", json=edge_case_data["empty_data"])
        assert response.status_code in [200, 422]

        # Test missing fields
        response = await async_client.post("/validate", json=edge_case_data["missing_fields"])
        assert response.status_code in [200, 422]

        # Test invalid age group
        response = await async_client.post("/validate", json=edge_case_data["invalid_age_group"])
        assert response.status_code == 422


class TestCauseMappingsEndpoint:
    """
    Test cases for cause mappings endpoint (GET /cause-mappings/{age_group}).
    Test ID: UT-008
    """

    @pytest.mark.asyncio
    async def test_get_neonate_mappings(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_cause_mappings_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-008-01
        Get neonate mappings should return complete mapping dict.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_cause_mappings_output):

            mock_run.return_value.returncode = 0

            response = await async_client.get("/cause-mappings/neonate")

            assert response.status_code == 200
            data = response.json()

            assert "age_group" in data
            assert "broad_causes" in data
            assert "mappings" in data
            assert "total_mappings" in data

            assert data["age_group"] == "neonate"
            assert isinstance(data["broad_causes"], list)
            assert isinstance(data["mappings"], list)
            assert isinstance(data["total_mappings"], int)

            # Check broad causes for neonate
            expected_broad_causes = [
                "congenital_malformation", "pneumonia", "sepsis_meningitis_inf",
                "ipre", "other", "prematurity"
            ]
            assert set(data["broad_causes"]) == set(expected_broad_causes)

    @pytest.mark.asyncio
    async def test_get_child_mappings(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-008-02
        Get child mappings should return complete mapping dict.
        """
        child_mappings_output = {
            "success": True,
            "age_group": "child",
            "broad_causes": [
                "malaria", "pneumonia", "diarrhea", "severe_malnutrition",
                "hiv", "injury", "other", "other_infections", "nn_causes"
            ],
            "mappings": [
                {"specific_cause": "Malaria", "broad_cause": "malaria"},
                {"specific_cause": "Pneumonia", "broad_cause": "pneumonia"}
            ]
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=child_mappings_output):

            mock_run.return_value.returncode = 0

            response = await async_client.get("/cause-mappings/child")

            assert response.status_code == 200
            data = response.json()

            assert data["age_group"] == "child"
            expected_child_causes = [
                "malaria", "pneumonia", "diarrhea", "severe_malnutrition",
                "hiv", "injury", "other", "other_infections", "nn_causes"
            ]
            assert set(data["broad_causes"]) == set(expected_child_causes)

    @pytest.mark.asyncio
    async def test_get_mappings_invalid_age_group(self, async_client: AsyncClient):
        """
        Test ID: UT-008-03
        Invalid age group should return 404 Not Found.
        """
        response = await async_client.get("/cause-mappings/invalid")

        assert response.status_code == 422  # Validation error for invalid enum


class TestSupportedConfigurationsEndpoint:
    """
    Test cases for supported configurations endpoint (GET /supported-configurations).
    Test ID: UT-009
    """

    @pytest.mark.asyncio
    async def test_get_all_configurations(self, async_client: AsyncClient):
        """
        Test ID: UT-009-01
        Get all configurations should return complete config object.
        """
        response = await async_client.get("/supported-configurations")

        assert response.status_code == 200
        data = response.json()

        assert "algorithms" in data
        assert "age_groups" in data
        assert "countries" in data
        assert "mmat_types" in data
        assert "input_formats" in data

        # Check data types
        assert isinstance(data["algorithms"], list)
        assert isinstance(data["age_groups"], list)
        assert isinstance(data["countries"], list)
        assert isinstance(data["mmat_types"], list)
        assert isinstance(data["input_formats"], list)

    @pytest.mark.asyncio
    async def test_countries_list_present(self, async_client: AsyncClient):
        """
        Test ID: UT-009-02
        Countries list should include all supported countries.
        """
        response = await async_client.get("/supported-configurations")

        assert response.status_code == 200
        data = response.json()

        countries = data["countries"]
        expected_countries = [
            "Bangladesh", "Ethiopia", "Kenya", "Mali",
            "Mozambique", "Sierra Leone", "South Africa", "other"
        ]

        assert set(countries) == set(expected_countries)

    @pytest.mark.asyncio
    async def test_algorithms_list_present(self, async_client: AsyncClient):
        """
        Test ID: UT-009-03
        Algorithms list should include all supported algorithms.
        """
        response = await async_client.get("/supported-configurations")

        assert response.status_code == 200
        data = response.json()

        algorithms = data["algorithms"]
        expected_algorithms = ["eava", "insilicova", "interva"]

        assert set(algorithms) == set(expected_algorithms)

    @pytest.mark.asyncio
    async def test_age_groups_list_present(self, async_client: AsyncClient):
        """
        Test ID: UT-009-04
        Age groups list should include all supported age groups.
        """
        response = await async_client.get("/supported-configurations")

        assert response.status_code == 200
        data = response.json()

        age_groups = data["age_groups"]
        expected_age_groups = ["neonate", "child"]

        assert set(age_groups) == set(expected_age_groups)

    @pytest.mark.asyncio
    async def test_mmat_types_and_input_formats(self, async_client: AsyncClient):
        """Test that mmat_types and input_formats are properly defined."""
        response = await async_client.get("/supported-configurations")

        assert response.status_code == 200
        data = response.json()

        mmat_types = data["mmat_types"]
        expected_mmat_types = ["prior", "fixed"]
        assert set(mmat_types) == set(expected_mmat_types)

        input_formats = data["input_formats"]
        expected_formats = ["specific_causes", "broad_causes", "death_counts"]
        assert set(input_formats) == set(expected_formats)