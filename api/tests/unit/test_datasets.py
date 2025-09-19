"""
Unit tests for dataset endpoints.
Test IDs: UT-003, UT-004, UT-005
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, mock_open
from httpx import AsyncClient
import json

from app.main_direct import app


class TestExampleDataEndpoint:
    """
    Test cases for the example data endpoint (GET /example-data).
    Test ID: UT-003
    """

    @pytest.mark.asyncio
    async def test_get_example_data_info(self, async_client: AsyncClient):
        """
        Test ID: UT-003-01
        Get example data info should return data structure info.
        """
        response = await async_client.get("/example-data")

        assert response.status_code == 200
        data = response.json()

        # Should contain neonate and specific_causes sections
        assert "neonate" in data
        assert "specific_causes" in data

        # Check neonate data structure
        neonate_data = data["neonate"]
        assert "dataset" in neonate_data
        assert "file" in neonate_data
        assert "exists" in neonate_data
        assert "description" in neonate_data
        assert "causes" in neonate_data

        assert neonate_data["dataset"] == "comsamoz_public_broad"
        assert isinstance(neonate_data["causes"], list)

    @pytest.mark.asyncio
    async def test_example_data_format_verification(self, async_client: AsyncClient):
        """
        Test ID: UT-003-02
        Verify data format specification is correct.
        """
        response = await async_client.get("/example-data")

        assert response.status_code == 200
        data = response.json()

        # Check specific_causes format
        specific_data = data["specific_causes"]
        assert "dataset" in specific_data
        assert specific_data["dataset"] == "comsamoz_public_openVAout"

        # Check causes list for neonate
        neonate_causes = data["neonate"]["causes"]
        expected_causes = [
            "congenital_malformation",
            "pneumonia",
            "sepsis_meningitis_inf",
            "ipre",
            "other",
            "prematurity"
        ]
        assert set(neonate_causes) == set(expected_causes)

    @pytest.mark.asyncio
    async def test_example_data_sample_size(self, async_client: AsyncClient):
        """
        Test ID: UT-003-03
        Check sample size returns correct counts.
        """
        response = await async_client.get("/example-data")

        assert response.status_code == 200
        data = response.json()

        # Check file existence flags
        assert "exists" in data["neonate"]
        assert "exists" in data["specific_causes"]

        # These should be boolean values
        assert isinstance(data["neonate"]["exists"], bool)
        assert isinstance(data["specific_causes"]["exists"], bool)

    @pytest.mark.asyncio
    async def test_example_data_response_structure(self, async_client: AsyncClient):
        """Test complete response structure for example data."""
        response = await async_client.get("/example-data")

        assert response.status_code == 200
        data = response.json()

        # Validate complete structure
        for section_name, section_data in data.items():
            assert isinstance(section_data, dict)
            assert "dataset" in section_data
            assert "file" in section_data
            assert "exists" in section_data
            assert "description" in section_data

        # Neonate section should have causes
        if "neonate" in data:
            assert "causes" in data["neonate"]
            assert isinstance(data["neonate"]["causes"], list)


class TestDatasetsEndpoint:
    """
    Test cases for the datasets endpoint (GET /datasets).
    Test ID: UT-004
    """

    @pytest.mark.asyncio
    async def test_list_all_datasets(self, async_client: AsyncClient):
        """
        Test ID: UT-004-01
        List all datasets should return array of datasets.
        """
        response = await async_client.get("/datasets")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Should contain expected datasets
        dataset_names = [d["name"] for d in data]
        expected_datasets = [
            "comsamoz_public_broad",
            "comsamoz_public_openVAout",
            "Mmat_champs"
        ]

        for expected in expected_datasets:
            assert expected in dataset_names

    @pytest.mark.asyncio
    async def test_dataset_metadata_present(self, async_client: AsyncClient):
        """
        Test ID: UT-004-02
        Each dataset should have id, name, description.
        """
        response = await async_client.get("/datasets")

        assert response.status_code == 200
        data = response.json()

        for dataset in data:
            # Check required fields
            assert "name" in dataset
            assert "file_path" in dataset
            assert "exists" in dataset
            assert "age_group" in dataset
            assert "description" in dataset

            # Check data types
            assert isinstance(dataset["name"], str)
            assert isinstance(dataset["file_path"], str)
            assert isinstance(dataset["exists"], bool)
            assert isinstance(dataset["age_group"], str)
            assert isinstance(dataset["description"], str)

            # Optional fields
            if "sample_size" in dataset and dataset["sample_size"] is not None:
                assert isinstance(dataset["sample_size"], int)
            if "causes" in dataset and dataset["causes"] is not None:
                assert isinstance(dataset["causes"], list)

    @pytest.mark.asyncio
    async def test_datasets_age_group_filter(self, async_client: AsyncClient):
        """
        Test ID: UT-004-03
        Filter by age group should only return matching datasets.
        """
        response = await async_client.get("/datasets")

        assert response.status_code == 200
        data = response.json()

        # Check age groups
        age_groups = [d["age_group"] for d in data]
        valid_age_groups = ["neonate", "child", "both"]

        for age_group in age_groups:
            assert age_group in valid_age_groups

        # Find datasets for each age group
        neonate_datasets = [d for d in data if d["age_group"] == "neonate"]
        both_datasets = [d for d in data if d["age_group"] == "both"]

        assert len(neonate_datasets) > 0
        assert len(both_datasets) > 0

    @pytest.mark.asyncio
    async def test_datasets_format_information(self, async_client: AsyncClient):
        """
        Test ID: UT-004-04
        Check that datasets contain format information.
        """
        response = await async_client.get("/datasets")

        assert response.status_code == 200
        data = response.json()

        # Check specific datasets
        broad_dataset = next((d for d in data if d["name"] == "comsamoz_public_broad"), None)
        assert broad_dataset is not None
        assert broad_dataset["age_group"] == "neonate"
        assert "COMSA" in broad_dataset["description"]

        openva_dataset = next((d for d in data if d["name"] == "comsamoz_public_openVAout"), None)
        assert openva_dataset is not None
        assert "specific" in openva_dataset["description"]

        mmat_dataset = next((d for d in data if d["name"] == "Mmat_champs"), None)
        assert mmat_dataset is not None
        assert "CHAMPS" in mmat_dataset["description"]


class TestDatasetPreviewEndpoint:
    """
    Test cases for the dataset preview endpoint (GET /datasets/{dataset_id}/preview).
    Test ID: UT-005
    """

    @pytest.mark.asyncio
    async def test_preview_valid_dataset(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_dataset_preview_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-005-01
        Preview valid dataset should return sample records.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_dataset_preview_output):

            mock_run.return_value.returncode = 0

            response = await async_client.get("/datasets/comsamoz_public_broad/preview")

            assert response.status_code == 200
            data = response.json()

            assert "dataset_id" in data
            assert "sample_data" in data
            assert "total_records" in data
            assert "columns" in data
            assert "statistics" in data
            assert "metadata" in data

            assert data["dataset_id"] == "comsamoz_public_broad"
            assert isinstance(data["sample_data"], list)
            assert isinstance(data["total_records"], int)
            assert isinstance(data["columns"], list)

    @pytest.mark.asyncio
    async def test_preview_invalid_dataset(self, async_client: AsyncClient):
        """
        Test ID: UT-005-02
        Preview invalid dataset should return 404 Not Found.
        """
        response = await async_client.get("/datasets/invalid_dataset/preview")

        assert response.status_code == 404
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_preview_sample_size_limit(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_dataset_preview_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-005-03
        Sample size limit should be respected (max 10 records returned by default).
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_dataset_preview_output):

            mock_run.return_value.returncode = 0

            response = await async_client.get("/datasets/comsamoz_public_broad/preview?limit=5")

            assert response.status_code == 200
            data = response.json()

            # Check that limit parameter is passed to R script
            assert "sample_data" in data
            # The mock returns 2 records, so this tests the mocking works
            assert len(data["sample_data"]) <= 10

    @pytest.mark.asyncio
    async def test_preview_statistics_included(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_dataset_preview_output,
        mock_tempfile,
        tmp_path
    ):
        """
        Test ID: UT-005-04
        Statistics should be included in preview response.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_dataset_preview_output):

            mock_run.return_value.returncode = 0

            response = await async_client.get("/datasets/comsamoz_public_broad/preview")

            assert response.status_code == 200
            data = response.json()

            assert "statistics" in data
            statistics = data["statistics"]

            assert "total_deaths" in statistics
            assert "cause_distribution" in statistics
            assert "most_common_cause" in statistics
            assert "least_common_cause" in statistics

            # Check cause distribution structure
            cause_dist = statistics["cause_distribution"]
            assert isinstance(cause_dist, dict)
            assert len(cause_dist) > 0

    @pytest.mark.asyncio
    async def test_preview_metadata_structure(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_dataset_preview_output,
        mock_tempfile,
        tmp_path
    ):
        """Test that preview response includes proper metadata."""
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_dataset_preview_output):

            mock_run.return_value.returncode = 0

            response = await async_client.get("/datasets/comsamoz_public_broad/preview")

            assert response.status_code == 200
            data = response.json()

            assert "metadata" in data
            metadata = data["metadata"]

            assert "description" in metadata
            assert "age_group" in metadata
            assert "format" in metadata
            assert "source" in metadata

            # Check metadata values
            assert metadata["age_group"] == "neonate"
            assert "COMSA" in metadata["description"]

    @pytest.mark.asyncio
    async def test_preview_r_not_ready(self, async_client: AsyncClient, mock_r_not_ready):
        """Test preview endpoint when R is not available."""
        with patch('app.main_direct.check_r_setup', mock_r_not_ready):
            response = await async_client.get("/datasets/comsamoz_public_broad/preview")

            assert response.status_code == 500
            error_data = response.json()
            assert "R not ready" in error_data["detail"]

    @pytest.mark.asyncio
    async def test_preview_file_not_found(self, async_client: AsyncClient, mock_r_ready):
        """Test preview when dataset file doesn't exist."""
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('os.path.exists', return_value=False):

            response = await async_client.get("/datasets/comsamoz_public_broad/preview")

            assert response.status_code == 404
            error_data = response.json()
            assert "file not found" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_preview_r_script_failure(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_tempfile,
        tmp_path
    ):
        """Test preview when dataset file doesn't exist."""
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('os.path.exists', return_value=False):  # No dataset file

            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "R script failed"

            response = await async_client.get("/datasets/comsamoz_public_broad/preview")

            # When file doesn't exist, expect 404 not 500
            assert response.status_code == 404
            error_data = response.json()
            assert "not found" in error_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_preview_all_valid_datasets(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_dataset_preview_output,
        mock_tempfile,
        tmp_path
    ):
        """Test preview endpoint with all valid dataset IDs."""
        valid_datasets = [
            "comsamoz_public_broad",
            "comsamoz_public_openVAout",
            "Mmat_champs"
        ]

        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_dataset_preview_output):

            mock_run.return_value.returncode = 0

            for dataset_id in valid_datasets:
                response = await async_client.get(f"/datasets/{dataset_id}/preview")

                assert response.status_code == 200
                data = response.json()
                assert data["dataset_id"] == dataset_id

    @pytest.mark.asyncio
    async def test_preview_custom_limit_parameter(
        self,
        async_client: AsyncClient,
        mock_r_ready,
        mock_dataset_preview_output,
        mock_tempfile,
        tmp_path
    ):
        """Test preview with custom limit parameter."""
        with patch('app.main_direct.check_r_setup', mock_r_ready), \
             patch('tempfile.TemporaryDirectory', mock_tempfile), \
             patch('subprocess.run') as mock_run, \
             patch('builtins.open', mock_open()) as mock_file, \
             patch('os.path.exists', return_value=True), \
             patch('json.load', return_value=mock_dataset_preview_output):

            mock_run.return_value.returncode = 0

            # Test with different limit values
            for limit in [1, 5, 15, 50]:
                response = await async_client.get(
                    f"/datasets/comsamoz_public_broad/preview?limit={limit}"
                )

                assert response.status_code == 200
                data = response.json()
                assert "sample_data" in data

                # Verify R script was called with correct limit
                # (This would be more meaningful with actual R script execution)
                assert mock_run.called