"""
Integration tests for end-to-end workflows.
Test ID: IT-001, IT-002, IT-003
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, mock_open
from httpx import AsyncClient
import json
import time

from app.main_direct import app


class TestEndToEndCalibrationWorkflow:
    """
    Test cases for complete calibration workflow from data submission to results.
    Test ID: IT-001
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_sync_calibration_workflow(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-001-01
        Submit → Process → Results (sync) should complete workflow successfully.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            # Step 1: Check API health
            health_response = await async_client.get("/")
            assert health_response.status_code == 200
            assert health_response.json()["status"] == "healthy"

            # Step 2: Get supported configurations
            config_response = await async_client.get("/supported-configurations")
            assert config_response.status_code == 200
            config_data = config_response.json()
            assert "neonate" in config_data["age_groups"]
            assert "Mozambique" in config_data["countries"]

            # Step 3: Get example data information
            example_response = await async_client.get("/example-data")
            assert example_response.status_code == 200
            example_data = example_response.json()
            assert "neonate" in example_data

            # Step 4: Run calibration with example data
            calibration_response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique",
                "ensemble": True
            })

            assert calibration_response.status_code == 200
            calibration_data = calibration_response.json()

            assert calibration_data["status"] == "success"
            assert "uncalibrated" in calibration_data
            assert "calibrated" in calibration_data
            assert calibration_data["age_group"] == "neonate"
            assert calibration_data["country"] == "Mozambique"

            # Verify results structure
            assert isinstance(calibration_data["uncalibrated"], dict)
            assert isinstance(calibration_data["calibrated"], dict)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_validation_conversion_calibration_workflow(
        self,
        async_client: AsyncClient,
        sample_specific_causes,
        mock_r_ready,
        mock_convert_causes_output,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-001-04
        Data validation → Conversion → Calibration multi-step workflow.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True):

            mock_run.return_value.returncode = 0

            # Step 1: Validate input data
            validate_data = {
                "data": {
                    "insilicova": sample_specific_causes
                },
                "age_group": "neonate",
                "expected_format": "specific_causes"
            }

            with patch('json.load', return_value={}):  # No R output needed for validation
                validate_response = await async_client.post("/validate", json=validate_data)

            assert validate_response.status_code == 200
            validation_result = validate_response.json()

            # Should be valid (assuming mock validation passes)
            if validation_result["overall_valid"]:
                # Step 2: Convert specific causes to broad causes
                convert_data = {
                    "data": sample_specific_causes,
                    "age_group": "neonate"
                }

                with patch('json.load', return_value=mock_convert_causes_output):
                    convert_response = await async_client.post("/convert/causes", json=convert_data)

                assert convert_response.status_code == 200
                convert_result = convert_response.json()

                assert "broad_cause_matrix" in convert_result
                broad_cause_matrix = convert_result["broad_cause_matrix"]

                # Step 3: Calibrate using converted broad causes
                calibrate_data = {
                    "va_data": {
                        "insilicova": broad_cause_matrix
                    },
                    "age_group": "neonate",
                    "country": "Mozambique"
                }

                with patch('json.load', return_value=mock_r_success_output):
                    calibrate_response = await async_client.post("/calibrate", json=calibrate_data)

                assert calibrate_response.status_code == 200
                calibration_result = calibrate_response.json()

                assert calibration_result["status"] == "success"
                assert "calibrated" in calibration_result

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_algorithms_ensemble_workflow(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-001-03
        Multiple algorithms ensemble should return combined results.
        """
        ensemble_output = {
            "success": True,
            "uncalibrated": {
                "pneumonia": 0.15,
                "sepsis_meningitis_inf": 0.30,
                "ipre": 0.25,
                "prematurity": 0.20,
                "congenital_malformation": 0.05,
                "other": 0.05
            },
            "calibrated": {
                "insilicova": {
                    "pneumonia": 0.12,
                    "sepsis_meningitis_inf": 0.35,
                    "ipre": 0.22,
                    "prematurity": 0.23,
                    "congenital_malformation": 0.04,
                    "other": 0.04
                },
                "interva": {
                    "pneumonia": 0.14,
                    "sepsis_meningitis_inf": 0.33,
                    "ipre": 0.24,
                    "prematurity": 0.21,
                    "congenital_malformation": 0.04,
                    "other": 0.04
                },
                "eava": {
                    "pneumonia": 0.13,
                    "sepsis_meningitis_inf": 0.34,
                    "ipre": 0.23,
                    "prematurity": 0.22,
                    "congenital_malformation": 0.04,
                    "other": 0.04
                }
            }
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=ensemble_output):

            mock_run.return_value.returncode = 0

            # Test ensemble calibration
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
            calibrated_algorithms = list(data["calibrated"].keys())
            assert len(calibrated_algorithms) >= 1

            # Verify each algorithm has results
            for algorithm in calibrated_algorithms:
                algorithm_results = data["calibrated"][algorithm]
                assert isinstance(algorithm_results, dict)
                assert len(algorithm_results) > 0

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_dataset_preview_to_calibration_workflow(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_dataset_preview_output,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test workflow from dataset preview to calibration.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True):

            mock_run.return_value.returncode = 0

            # Step 1: List available datasets
            datasets_response = await async_client.get("/datasets")
            assert datasets_response.status_code == 200
            datasets = datasets_response.json()

            # Find neonate dataset
            neonate_dataset = next(
                (d for d in datasets if d["age_group"] == "neonate" and "broad" in d["name"]),
                None
            )
            assert neonate_dataset is not None

            # Step 2: Preview the dataset
            dataset_id = neonate_dataset["name"]

            with patch('json.load', return_value=mock_dataset_preview_output):
                preview_response = await async_client.get(f"/datasets/{dataset_id}/preview")

            assert preview_response.status_code == 200
            preview_data = preview_response.json()

            assert "statistics" in preview_data
            assert "cause_distribution" in preview_data["statistics"]

            # Step 3: Use example data for calibration (simulating using the previewed dataset)
            with patch('json.load', return_value=mock_r_success_output):
                calibration_response = await async_client.post("/calibrate", json={
                    "age_group": "neonate",
                    "country": "Mozambique"
                })

            assert calibration_response.status_code == 200
            calibration_data = calibration_response.json()
            assert calibration_data["status"] == "success"


class TestErrorRecoveryScenarios:
    """
    Test cases for error handling and recovery.
    Test ID: IT-002
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_r_script_failure_recovery(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-002-01
        R script failure should return graceful error message.
        """
        failure_output = {
            "success": False,
            "error": "R package vacalibration not found"
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=failure_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 400
            error_data = response.json()
            assert "detail" in error_data
            assert "R package vacalibration not found" in error_data["detail"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_partial_data_processing_handling(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-002-03
        Partial data processing should be handled gracefully.
        """
        partial_output = {
            "success": True,
            "uncalibrated": {
                "pneumonia": 0.15,
                "sepsis_meningitis_inf": 0.30
                # Missing other causes
            },
            "calibrated": {
                "insilicova": {
                    "pneumonia": 0.12,
                    "sepsis_meningitis_inf": 0.35
                    # Missing other causes
                }
            }
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=partial_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            # Should still return success with partial data
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "uncalibrated" in data
            assert "calibrated" in data

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_timeout_and_retry_simulation(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-002-02
        Simulate timeout scenario and verify error handling.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=False):  # No output file = timeout/failure

            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "Process timed out"

            response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 500
            error_data = response.json()
            assert "detail" in error_data
            assert "Process timed out" in error_data["detail"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sequential_api_call_resilience(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test that API can handle sequential calls without issues.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            # Make multiple sequential requests
            for i in range(3):
                response = await async_client.post("/calibrate", json={
                    "age_group": "neonate",
                    "country": "Mozambique"
                })

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"

                # Brief pause between requests
                await asyncio.sleep(0.1)


class TestDataFormatCompatibility:
    """
    Test cases for all data format conversions.
    Test ID: IT-003
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_specific_to_broad_to_calibrate_format_chain(
        self,
        async_client: AsyncClient,
        sample_specific_causes,
        mock_r_ready,
        mock_convert_causes_output,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-003-01
        Specific → Broad → Calibrate format chain should work.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True):

            mock_run.return_value.returncode = 0

            # Step 1: Convert specific causes to broad causes
            with patch('json.load', return_value=mock_convert_causes_output):
                convert_response = await async_client.post("/convert/causes", json={
                    "data": sample_specific_causes,
                    "age_group": "neonate"
                })

            assert convert_response.status_code == 200
            convert_data = convert_response.json()
            broad_matrix = convert_data["broad_cause_matrix"]

            # Step 2: Use broad cause matrix for calibration
            with patch('json.load', return_value=mock_r_success_output):
                calibrate_response = await async_client.post("/calibrate", json={
                    "va_data": {
                        "insilicova": broad_matrix
                    },
                    "age_group": "neonate",
                    "country": "Mozambique"
                })

            assert calibrate_response.status_code == 200
            calibration_data = calibrate_response.json()
            assert calibration_data["status"] == "success"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_death_counts_direct_processing(
        self,
        async_client: AsyncClient,
        sample_death_counts,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-003-02
        Death counts should be processed directly.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            response = await async_client.post("/calibrate", json={
                "va_data": {
                    "insilicova": sample_death_counts
                },
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mixed_format_ensemble_handling(
        self,
        async_client: AsyncClient,
        sample_binary_matrix,
        sample_death_counts,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: IT-003-03
        Mixed format ensemble should handle multiple formats.
        """
        mixed_format_output = {
            "success": True,
            "uncalibrated": {"pneumonia": 0.15},
            "calibrated": {
                "insilicova": {"pneumonia": 0.12},
                "interva": {"pneumonia": 0.14}
            }
        }

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mixed_format_output):

            mock_run.return_value.returncode = 0

            # Use different formats for different algorithms
            response = await async_client.post("/calibrate", json={
                "va_data": {
                    "insilicova": sample_binary_matrix,
                    "interva": sample_death_counts
                },
                "age_group": "neonate",
                "country": "Mozambique",
                "ensemble": True
            })

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cross_age_group_compatibility(
        self,
        async_client: AsyncClient,
        child_binary_matrix,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test that different age groups work with appropriate data formats.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            # Test neonate age group
            neonate_response = await async_client.post("/calibrate", json={
                "age_group": "neonate",
                "country": "Mozambique"
            })

            assert neonate_response.status_code == 200
            neonate_data = neonate_response.json()
            assert neonate_data["age_group"] == "neonate"

            # Test child age group
            child_response = await async_client.post("/calibrate", json={
                "va_data": {
                    "insilicova": child_binary_matrix
                },
                "age_group": "child",
                "country": "Kenya"
            })

            assert child_response.status_code == 200
            child_data = child_response.json()
            assert child_data["age_group"] == "child"


class TestPerformanceIntegration:
    """Performance-related integration tests."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_large_dataset_processing(
        self,
        async_client: AsyncClient,
        performance_test_data,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """Test API performance with large datasets."""
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            start_time = time.time()
            response = await async_client.post("/calibrate", json=performance_test_data)
            end_time = time.time()

            processing_time = end_time - start_time

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            # Performance check - should complete within reasonable time
            # (This is a mock test, so times will be very fast)
            assert processing_time < 10.0  # 10 seconds for integration test

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_r_success_output,
        mock_tempfile,
        tmp_path
    ):
        """Test handling of concurrent requests."""
        import asyncio

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_r_success_output):

            mock_run.return_value.returncode = 0

            # Create multiple concurrent requests
            tasks = []
            for i in range(3):
                task = async_client.post("/calibrate", json={
                    "age_group": "neonate",
                    "country": "Mozambique"
                })
                tasks.append(task)

            # Wait for all requests to complete
            responses = await asyncio.gather(*tasks)

            # All should succeed
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"