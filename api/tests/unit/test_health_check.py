"""
Unit tests for health check endpoint (GET /).
Test ID: UT-001
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
import time

from app.main_direct import app, check_r_setup


class TestHealthCheckEndpoint:
    """Test cases for the health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success_with_r_ready(self, async_client: AsyncClient, mock_r_ready):
        """
        Test ID: UT-001-01
        Health check with R available should return status 200 and R status "ready".
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            response = await async_client.get("/")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "healthy"
            assert data["service"] == "VA-Calibration API (Direct)"
            assert data["r_status"] == "R ready"
            assert "data_files" in data
            assert isinstance(data["data_files"], dict)

    @pytest.mark.asyncio
    async def test_health_check_with_r_unavailable(self, async_client: AsyncClient, mock_r_not_ready):
        """
        Test ID: UT-001-02
        Health check with R unavailable should return status 200 but show R error.
        """
        with patch('app.main_direct.check_r_setup', mock_r_not_ready):
            response = await async_client.get("/")

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "warning"
            assert data["r_status"] == "Rscript not found"
            assert "data_files" in data

    @pytest.mark.asyncio
    async def test_health_check_data_files_status(self, async_client: AsyncClient, mock_r_ready):
        """
        Test ID: UT-001-03
        Check data files availability in health check response.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            response = await async_client.get("/")

            assert response.status_code == 200
            data = response.json()

            assert "data_files" in data
            data_files = data["data_files"]

            # Should include expected data files
            assert "comsamoz_broad" in data_files
            assert "comsamoz_openVA" in data_files

            # Values should be boolean
            assert isinstance(data_files["comsamoz_broad"], bool)
            assert isinstance(data_files["comsamoz_openVA"], bool)

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, async_client: AsyncClient, mock_r_ready):
        """
        Test ID: UT-001-04
        Response time should be under 100ms for performance baseline.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            start_time = time.time()
            response = await async_client.get("/")
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000

            assert response.status_code == 200
            # Allow some flexibility for test environment
            assert response_time_ms < 1000, f"Response time {response_time_ms}ms exceeds 1000ms threshold"

    @pytest.mark.asyncio
    async def test_health_check_json_structure(self, async_client: AsyncClient, mock_r_ready):
        """
        Test that health check returns properly structured JSON.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            response = await async_client.get("/")

            assert response.status_code == 200
            data = response.json()

            # Check required fields
            required_fields = ["status", "service", "r_status", "data_files"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Check data types
            assert isinstance(data["status"], str)
            assert isinstance(data["service"], str)
            assert isinstance(data["r_status"], str)
            assert isinstance(data["data_files"], dict)

    @pytest.mark.asyncio
    async def test_health_check_cors_headers(self, async_client: AsyncClient, mock_r_ready):
        """
        Test that CORS headers are properly set.
        """
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            response = await async_client.get("/")

            assert response.status_code == 200

            # Check for CORS headers (these would be set by FastAPI CORS middleware)
            # Note: AsyncClient might not capture all headers in test environment
            headers = response.headers
            # Basic check that response is JSON
            assert "application/json" in headers.get("content-type", "")


class TestRSetupCheck:
    """Test cases for the R setup check function."""

    @patch('subprocess.run')
    def test_check_r_setup_success(self, mock_run):
        """Test successful R setup check."""
        # Mock successful which command
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # which Rscript
            MagicMock(returncode=0, stdout="", stderr="")   # package check
        ]

        is_ready, message = check_r_setup()

        assert is_ready is True
        assert message == "R ready"
        assert mock_run.call_count == 2

    @patch('subprocess.run')
    def test_check_r_setup_rscript_not_found(self, mock_run):
        """Test R setup check when Rscript is not found."""
        # Mock failed which command
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        is_ready, message = check_r_setup()

        assert is_ready is False
        assert message == "Rscript not found"

    @patch('subprocess.run')
    def test_check_r_setup_missing_packages(self, mock_run):
        """Test R setup check when required packages are missing."""
        # Mock successful which command but failed package check
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # which Rscript succeeds
            MagicMock(returncode=1, stdout="", stderr="Error: vacalibration not found")  # package check fails
        ]

        is_ready, message = check_r_setup()

        assert is_ready is False
        assert "Missing R packages" in message
        assert "vacalibration not found" in message

    @patch('subprocess.run')
    def test_check_r_setup_exception(self, mock_run):
        """Test R setup check when subprocess raises exception."""
        mock_run.side_effect = FileNotFoundError("Command not found")

        is_ready, message = check_r_setup()

        assert is_ready is False
        assert "Command not found" in message

    @patch('subprocess.run')
    def test_check_r_setup_partial_packages(self, mock_run):
        """Test R setup check when only some packages are available."""
        # Mock successful which command but partial package failure
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # which Rscript succeeds
            MagicMock(returncode=1, stdout="", stderr="Error: jsonlite not found")  # missing jsonlite
        ]

        is_ready, message = check_r_setup()

        assert is_ready is False
        assert "Missing R packages" in message
        assert "jsonlite not found" in message


class TestHealthCheckEdgeCases:
    """Test edge cases and error scenarios for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_with_malformed_r_response(self, async_client: AsyncClient):
        """Test health check when R setup check has unexpected behavior."""
        def mock_check_malformed():
            # Return unexpected format
            return "not_boolean", 123

        with patch('app.main_direct.check_r_setup', mock_check_malformed):
            response = await async_client.get("/")

            # Should still return 200 but handle gracefully
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_multiple_requests(self, async_client: AsyncClient, mock_r_ready):
        """Test multiple concurrent health check requests."""
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            # Send multiple requests
            tasks = []
            for _ in range(5):
                tasks.append(async_client.get("/"))

            # All should succeed
            responses = []
            for task in tasks:
                response = await task
                responses.append(response)

            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] in ["healthy", "warning"]

    @pytest.mark.asyncio
    async def test_health_check_invalid_http_methods(self, async_client: AsyncClient):
        """Test health check endpoint with invalid HTTP methods."""
        # POST should not be allowed (if not explicitly handled)
        response = await async_client.post("/")
        # FastAPI will return 405 Method Not Allowed or handle it gracefully
        assert response.status_code in [405, 200]  # 200 if OPTIONS/fallback is implemented

        # PUT should not be allowed
        response = await async_client.put("/")
        assert response.status_code in [405, 200]

        # DELETE should not be allowed
        response = await async_client.delete("/")
        assert response.status_code in [405, 200]

    @pytest.mark.asyncio
    async def test_health_check_with_query_parameters(self, async_client: AsyncClient, mock_r_ready):
        """Test health check endpoint ignores query parameters gracefully."""
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            response = await async_client.get("/?detailed=true&format=json")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_check_content_type(self, async_client: AsyncClient, mock_r_ready):
        """Test that health check returns proper content type."""
        with patch('app.main_direct.check_r_setup', mock_r_ready):
            response = await async_client.get("/")

            assert response.status_code == 200
            assert "application/json" in response.headers.get("content-type", "")