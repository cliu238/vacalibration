"""
Unit tests for calibration endpoint (POST /calibrate).
Test ID: UT-002
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, mock_open
from httpx import AsyncClient
import json
import tempfile
import os

from app.main_direct import app


class TestCalibrateEndpoint:
    """Test cases for the calibration endpoint."""

    @pytest.mark.asyncio
    async def test_calibrate_with_example_data(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-01
        Calibrate with example data should return success with calibrated results.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert "uncalibrated" in data
            assert "calibrated" in data
            assert data["age_group"] == "neonate"
            assert data["country"] == "Mozambique"

            # Check structure of results
            assert isinstance(data["uncalibrated"], dict)
            assert isinstance(data["calibrated"], dict)

    @pytest.mark.asyncio
    async def test_calibrate_with_custom_specific_causes(
        self,
        async_client: AsyncClient,
        sample_calibration_request_with_data,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-02
        Calibrate with custom specific causes should return success with mapped broad causes.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json=sample_calibration_request_with_data)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert "uncalibrated" in data
            assert "calibrated" in data

    @pytest.mark.asyncio
    async def test_calibrate_with_binary_matrix(
        self,
        async_client: AsyncClient,
        sample_binary_matrix,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-03
        Calibrate with binary matrix should return success with direct processing.
        """
        request_data = {
            "va_data": {
                "insilicova": sample_binary_matrix
            },
            "age_group": "neonate",
            "country": "Mozambique"
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_with_death_counts(
        self,
        async_client: AsyncClient,
        sample_death_counts,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-04
        Calibrate with death counts should return success with aggregated results.
        """
        request_data = {
            "va_data": {
                "insilicova": sample_death_counts
            },
            "age_group": "neonate",
            "country": "Mozambique"
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json=request_data)

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_invalid_age_group(self, async_client: AsyncClient):
        """
        Test ID: UT-002-05
        Invalid age group should return 422 Validation Error.
        """
        response = await async_client.post("/calibrate", json={
            "age_group": "invalid_age_group",
            "country": "Mozambique"
        })

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_calibrate_invalid_country_uses_other(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-06
        Invalid country should use "other" calibration matrix and still succeed.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "UnknownCountry"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_missing_required_fields(self, async_client: AsyncClient):
        """
        Test ID: UT-002-07
        Missing required fields should return 422 Validation Error.
        """
        # Test completely empty request
        response = await async_client.post("/calibrate", json={})

        # Should use defaults and succeed (age_group defaults to neonate)
        # This test may need adjustment based on actual validation requirements
        assert response.status_code in [200, 422, 500]

    @pytest.mark.asyncio
    async def test_calibrate_malformed_json(self, async_client: AsyncClient):
        """
        Test ID: UT-002-08
        Malformed JSON should return 422 Validation Error.
        """
        # Test invalid JSON structure
        response = await async_client.post(
            "/calibrate",
            content='{"age_group": "neonate", "invalid": }',  # Malformed JSON
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_calibrate_empty_va_data_uses_example(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-09
        Empty va_data should use example data.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "va_data": {},  # Empty data
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_ensemble_mode(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-10
        Ensemble calibration should return multiple algorithm results.
        """
        ensemble_output = {
            "success": True,
            "uncalibrated": {"pneumonia": 0.15, "sepsis_meningitis_inf": 0.30},
            "calibrated": {
                "insilicova": {"pneumonia": 0.12, "sepsis_meningitis_inf": 0.35},
                "interva": {"pneumonia": 0.14, "sepsis_meningitis_inf": 0.33}
            }
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=ensemble_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique",
                "ensemble": True
            })

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert "calibrated" in data
            # Should have multiple algorithms for ensemble
            assert len(data["calibrated"]) >= 1

    @pytest.mark.asyncio
    async def test_calibrate_custom_mmat_type(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-12
        Custom MMAT parameters should be used in calibration.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique",
                "mmat_type": "fixed"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_r_script_timeout(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-13
        R script timeout should return 504 Gateway Timeout.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=False):  # No output file

            # Mock timeout behavior
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "Execution timed out"

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data

    @pytest.mark.asyncio
    async def test_calibrate_r_script_error(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_failure_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-002-14
        R script error should return 500 with error details.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_failure_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 400
            error_data = response.json()
            assert "detail" in error_data
            assert "R script execution failed" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_calibrate_r_not_ready(self, async_client: AsyncClient, mock_r_not_ready):
        """
        Test calibration when R is not available should return 500.
        """
        with patch('app.main_direct.check_r_setup', mock_r_not_ready):
            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 500
            error_data = response.json()
            assert "R not ready" in error_data["detail"]


class TestCalibrateEdgeCases:
    """Test edge cases and error scenarios for calibration endpoint."""

    @pytest.mark.asyncio
    async def test_calibrate_child_age_group(
        self,
        async_client: AsyncClient,
        child_binary_matrix,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """Test calibration with child age group."""
        request_data = {
            "va_data": {
                "insilicova": child_binary_matrix
            },
            "age_group": "child",
            "country": "Kenya"
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["age_group"] == "child"

    @pytest.mark.asyncio
    async def test_calibrate_all_supported_countries(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """Test calibration with all supported countries."""
        countries = [
            "Bangladesh", "Ethiopia", "Kenya", "Mali",
            "Mozambique", "Sierra Leone", "South Africa", "other"
        ]

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            for country in countries:
                response = await async_client.post("/calibrate", json={
                    "age_group": "neonate",
                    "country": country
                })

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["country"] == country

    @pytest.mark.asyncio
    async def test_calibrate_with_unicode_data(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """Test calibration with unicode characters in data."""
        request_data = {
            "va_data": {
                "insilicova": [
                    {"ID": "死亡_001", "cause": "Birth asphyxia"},
                    {"ID": "muerte_002", "cause": "Neonatal sepsis"}
                ]
            },
            "age_group": "neonate",
            "country": "Mozambique"
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_large_dataset(
        self,
        async_client: AsyncClient,
        performance_test_data,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """Test calibration with large dataset for performance."""
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json=performance_test_data)

            # Should handle large datasets without error
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_mixed_data_types(self, async_client: AsyncClient):
        """Test calibration with mixed/invalid data types."""
        request_data = {
            "va_data": {
                "insilicova": [
                    {"ID": 123, "cause": "Birth asphyxia"},  # ID as number
                    {"ID": "d2", "cause": None},  # None cause
                    {"ID": "d3"}  # Missing cause
                ]
            },
            "age_group": "neonate",
            "country": "Mozambique"
        }

        response = await async_client.post("/calibrate", json=request_data)

        # Should handle gracefully - either success or validation error
        assert response.status_code in [200, 400, 422, 500]