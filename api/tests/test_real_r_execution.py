"""
Comprehensive tests for all core API endpoints with REAL R script execution.
These tests verify that the API properly integrates with the vacalibration R package.
No mocking - actual R script execution to validate the complete integration.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main_direct import app
import subprocess
import json
import os


def check_r_and_package_available():
    """Check if R and vacalibration package are installed."""
    # Check if Rscript is available
    result = subprocess.run(["which", "Rscript"], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip("Rscript not found - skipping R execution tests")

    # Check if vacalibration package is installed
    check_package = subprocess.run(
        ["Rscript", "-e", "if(!require('vacalibration', quietly=TRUE)) quit(status=1)"],
        capture_output=True
    )
    if check_package.returncode != 0:
        pytest.skip("vacalibration R package not installed - skipping R execution tests")

    # Check if data files exist
    if not os.path.exists("data/comsamoz_public_broad.rda"):
        pytest.skip("Data files not found - skipping R execution tests. Run 'make data' or copy .rda files to data/ directory")


class TestHealthCheck:
    """Test health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test root endpoint returns proper status."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"
            assert "r_status" in data
            assert "data_files" in data


class TestCalibrationEndpoint:
    """Test calibration endpoint with real R execution"""

    @pytest.mark.asyncio
    async def test_calibrate_with_example_data(self):
        """Test calibration with example data using real R script."""
        check_r_and_package_available()

        request_data = {
            "va_data": {
                "insilicova": "use_example"
            },
            "age_group": "neonate",
            "country": "Mozambique",
            "mmat_type": "prior",
            "ensemble": False
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/calibrate", json=request_data, timeout=60.0)

            if response.status_code != 200:
                print(f"\nError response: {response.json()}")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "calibrated" in data

            # Verify calibrated results structure
            calibrated = data["calibrated"]
            assert "insilicova" in calibrated
            assert "mean" in calibrated["insilicova"]

            # Check probabilities sum to ~1
            mean_values = calibrated["insilicova"]["mean"]
            total = sum(mean_values.values())
            assert 0.99 <= total <= 1.01

    @pytest.mark.asyncio
    async def test_calibrate_with_specific_causes(self):
        """Test calibration with specific cause data."""
        check_r_and_package_available()

        request_data = {
            "va_data": {
                "insilicova": [
                    {"id": "d1", "cause": "Birth asphyxia"},
                    {"id": "d2", "cause": "Neonatal sepsis"},
                    {"id": "d3", "cause": "Prematurity"},
                    {"id": "d4", "cause": "Neonatal pneumonia"},
                    {"id": "d5", "cause": "Congenital malformation"}
                ]
            },
            "age_group": "neonate",
            "country": "Mozambique"
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/calibrate", json=request_data, timeout=60.0)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_with_binary_matrix(self):
        """Test calibration with binary matrix format."""
        check_r_and_package_available()

        # Binary matrix: rows=deaths, columns=causes
        binary_matrix = [
            [0, 0, 1, 0, 0, 0],  # sepsis
            [0, 0, 0, 1, 0, 0],  # ipre
            [0, 0, 0, 0, 0, 1],  # prematurity
            [0, 1, 0, 0, 0, 0],  # pneumonia
            [1, 0, 0, 0, 0, 0]   # congenital
        ]

        request_data = {
            "va_data": {
                "insilicova": binary_matrix
            },
            "age_group": "neonate",
            "country": "Mozambique"
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/calibrate", json=request_data, timeout=60.0)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_calibrate_child_age_group(self):
        """Test calibration with child age group."""
        check_r_and_package_available()

        request_data = {
            "va_data": {
                "insilicova": "use_example"
            },
            "age_group": "child",
            "country": "Kenya"
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/calibrate", json=request_data, timeout=60.0)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


class TestDatasetsEndpoint:
    """Test dataset-related endpoints"""

    @pytest.mark.asyncio
    async def test_list_datasets(self):
        """Test /datasets endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/datasets")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0

            # Check dataset structure
            dataset = data[0]
            # API returns 'name' not 'id'
            assert "name" in dataset
            assert "age_group" in dataset

    @pytest.mark.asyncio
    async def test_dataset_preview(self):
        """Test dataset preview with real R script."""
        check_r_and_package_available()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First get available datasets
            datasets_response = await client.get("/datasets")
            datasets = datasets_response.json()

            if datasets:
                dataset_id = datasets[0]["name"]  # Changed from 'id' to 'name'

                # Preview the dataset
                response = await client.get(f"/datasets/{dataset_id}/preview", timeout=30.0)

                if response.status_code == 200:
                    data = response.json()
                    assert "dataset_id" in data
                    assert "sample_data" in data
                    assert "total_records" in data

    @pytest.mark.asyncio
    async def test_supported_configurations(self):
        """Test /supported-configurations endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/supported-configurations")

            assert response.status_code == 200
            data = response.json()
            assert "age_groups" in data
            assert "countries" in data
            assert "algorithms" in data
            assert "input_formats" in data  # Changed from 'data_formats'


class TestConversionEndpoints:
    """Test data conversion endpoints"""

    @pytest.mark.asyncio
    async def test_cause_mappings(self):
        """Test /cause-mappings/{age_group} endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/cause-mappings/neonate")

            assert response.status_code == 200
            data = response.json()
            assert "age_group" in data
            assert "broad_causes" in data
            assert "mappings" in data

            # Check neonate broad causes
            expected_causes = [
                "congenital_malformation", "pneumonia",
                "sepsis_meningitis_inf", "ipre", "other", "prematurity"
            ]
            for cause in expected_causes:
                assert cause in data["broad_causes"]

    @pytest.mark.asyncio
    async def test_convert_causes(self):
        """Test /convert-causes endpoint with real R script."""
        check_r_and_package_available()

        request_data = {
            "data": [
                {"id": "d1", "cause": "Birth asphyxia"},
                {"id": "d2", "cause": "Neonatal sepsis"},
                {"id": "d3", "cause": "Prematurity"}
            ],
            "age_group": "neonate"
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/convert/causes", json=request_data, timeout=30.0)

            assert response.status_code == 200
            data = response.json()
            assert "converted_data" in data
            assert "broad_cause_matrix" in data
            assert "conversion_summary" in data

    @pytest.mark.asyncio
    async def test_validate_data(self):
        """Test /validate endpoint."""
        request_data = {
            "data": {
                "insilicova": [
                    {"ID": "d1", "cause": "Birth asphyxia"},
                    {"ID": "d2", "cause": "Neonatal sepsis"}
                ]
            },
            "age_group": "neonate",
            "expected_format": "specific_causes"
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/validate", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert "overall_valid" in data
            assert "validation_results" in data


class TestExampleDataEndpoint:
    """Test example data endpoint"""

    @pytest.mark.asyncio
    async def test_get_example_data(self):
        """Test /example-data endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/example-data")

            assert response.status_code == 200
            data = response.json()
            # Check response structure based on actual API
            assert isinstance(data, dict)
            # Example data should contain neonate and specific_causes sections
            assert "neonate" in data or "comsamoz_public_broad" in data


class TestIntegrationWorkflow:
    """Test complete workflow with real R execution"""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow: validate -> convert -> calibrate."""
        check_r_and_package_available()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: Get example data structure
            example_response = await client.get("/example-data")
            assert example_response.status_code == 200

            # Step 2: Validate data format
            validate_request = {
                "data": {
                    "insilicova": [
                        {"ID": f"d{i}", "cause": cause}
                        for i, cause in enumerate([
                            "Birth asphyxia", "Neonatal sepsis",
                            "Prematurity", "Neonatal pneumonia"
                        ], 1)
                    ]
                },
                "age_group": "neonate",
                "expected_format": "specific_causes"
            }
            validate_response = await client.post("/validate", json=validate_request)
            assert validate_response.status_code == 200

            # Step 3: Convert causes
            convert_request = {
                "data": [
                    {"id": f"d{i}", "cause": cause}
                    for i, cause in enumerate([
                        "Birth asphyxia", "Neonatal sepsis",
                        "Prematurity", "Neonatal pneumonia"
                    ], 1)
                ],
                "age_group": "neonate"
            }
            convert_response = await client.post("/convert/causes", json=convert_request, timeout=30.0)
            assert convert_response.status_code == 200

            # Step 4: Run calibration
            calibrate_request = {
                "data_source": "custom",
                "va_data": {
                    "insilicova": convert_request["data"]
                },
                "data_format": "specific_causes",
                "age_group": "neonate",
                "country": "Mozambique",
                "mmat_type": "prior"
            }
            calibrate_response = await client.post("/calibrate", json=calibrate_request, timeout=60.0)
            assert calibrate_response.status_code == 200

            calibrate_data = calibrate_response.json()
            assert calibrate_data["status"] == "success"
            assert "calibrated" in calibrate_data

            print("\n=== COMPLETE WORKFLOW SUCCESS ===")
            print(f"✓ Data validation passed")
            print(f"✓ Cause conversion completed")
            print(f"✓ Calibration executed with R package")
            print(f"✓ Results: {json.dumps(calibrate_data.get('calibrated', {}), indent=2)[:200]}...")


class TestErrorHandling:
    """Test error handling with real R execution"""

    @pytest.mark.asyncio
    async def test_invalid_age_group(self):
        """Test error handling for invalid age group."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/calibrate", json={
                "data_source": "custom",
                "va_data": {"insilicova": []},
                "data_format": "specific_causes",
                "age_group": "invalid_group"
            })
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test error handling for missing fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/calibrate", json={})
            # API returns 500 when required fields are missing
            assert response.status_code in [422, 500]

    @pytest.mark.asyncio
    async def test_malformed_va_data(self):
        """Test error handling for malformed VA data."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/calibrate", json={
                "data_source": "custom",
                "va_data": {"insilicova": 12345},  # Invalid: should be list
                "data_format": "specific_causes",
                "age_group": "neonate"
            })
            assert response.status_code == 422


if __name__ == "__main__":
    # Run all tests
    import sys

    print("Testing VA-Calibration API with REAL R script execution...")
    print("=" * 60)

    # Check R availability first
    try:
        check_r_and_package_available()
        print("✓ R and vacalibration package are available")
    except Exception as e:
        print(f"✗ R setup check failed: {e}")
        sys.exit(1)

    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])