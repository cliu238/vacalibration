"""
Shared test fixtures and configuration for VA-Calibration API tests.
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from typing import Dict, List, Any
import asyncio
import json
from datetime import datetime, timedelta

# Import fakeredis for Redis testing
import fakeredis.aioredis

# Import the app using absolute import from project root
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main_direct import app

# Note: Mock classes will be defined here instead of importing from test files
# to avoid circular dependencies


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for testing FastAPI endpoints."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_specific_causes() -> List[Dict[str, str]]:
    """Sample specific cause data for testing."""
    return [
        {"ID": "d1", "cause": "Birth asphyxia"},
        {"ID": "d2", "cause": "Neonatal sepsis"},
        {"ID": "d3", "cause": "Prematurity"},
        {"ID": "d4", "cause": "Pneumonia"},
        {"ID": "d5", "cause": "Congenital malformation"}
    ]


@pytest.fixture
def sample_binary_matrix() -> List[List[int]]:
    """Sample binary matrix data for broad causes (neonate)."""
    # Columns: congenital_malformation, pneumonia, sepsis_meningitis_inf, ipre, other, prematurity
    return [
        [0, 0, 1, 0, 0, 0],  # sepsis
        [0, 0, 0, 1, 0, 0],  # ipre
        [0, 0, 0, 0, 0, 1],  # prematurity
        [0, 1, 0, 0, 0, 0],  # pneumonia
        [1, 0, 0, 0, 0, 0]   # congenital malformation
    ]


@pytest.fixture
def sample_death_counts() -> List[int]:
    """Sample death counts by broad cause (neonate)."""
    # Order: congenital_malformation, pneumonia, sepsis_meningitis_inf, ipre, other, prematurity
    return [50, 150, 300, 250, 100, 200]


@pytest.fixture
def child_binary_matrix() -> List[List[int]]:
    """Sample binary matrix for child age group."""
    # Columns: malaria, pneumonia, diarrhea, severe_malnutrition, hiv, injury, other, other_infections, nn_causes
    return [
        [1, 0, 0, 0, 0, 0, 0, 0, 0],  # malaria
        [0, 1, 0, 0, 0, 0, 0, 0, 0],  # pneumonia
        [0, 0, 1, 0, 0, 0, 0, 0, 0],  # diarrhea
        [0, 0, 0, 1, 0, 0, 0, 0, 0],  # severe malnutrition
        [0, 0, 0, 0, 1, 0, 0, 0, 0],  # hiv
    ]


@pytest.fixture
def mock_r_success_output():
    """Mock successful R script output."""
    return {
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
            }
        }
    }


@pytest.fixture
def mock_r_failure_output():
    """Mock failed R script output."""
    return {
        "success": False,
        "error": "R script execution failed: Missing required data"
    }


@pytest.fixture
def mock_subprocess_success():
    """Mock successful subprocess run for R script execution."""
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = ""
    mock.stderr = ""
    return mock


@pytest.fixture
def mock_subprocess_failure():
    """Mock failed subprocess run for R script execution."""
    mock = MagicMock()
    mock.returncode = 1
    mock.stdout = ""
    mock.stderr = "Error: vacalibration package not found"
    return mock


@pytest.fixture
def mock_r_ready():
    """Mock R setup check returning ready status."""
    def mock_check():
        return True, "R ready"
    return mock_check


@pytest.fixture
def mock_r_not_ready():
    """Mock R setup check returning not ready status."""
    def mock_check():
        return False, "Rscript not found"
    return mock_check


@pytest.fixture
def sample_calibration_request():
    """Sample calibration request data."""
    return {
        "age_group": "neonate",
        "country": "Mozambique",
        "mmat_type": "prior",
        "ensemble": True
    }


@pytest.fixture
def sample_calibration_request_with_data():
    """Sample calibration request with VA data."""
    return {
        "va_data": {
            "insilicova": [
                {"ID": "d1", "cause": "Birth asphyxia"},
                {"ID": "d2", "cause": "Neonatal sepsis"}
            ]
        },
        "age_group": "neonate",
        "country": "Mozambique",
        "mmat_type": "prior",
        "ensemble": True
    }


@pytest.fixture
def sample_convert_request():
    """Sample convert causes request."""
    return {
        "data": [
            {"id": "d1", "cause": "Birth asphyxia"},
            {"id": "d2", "cause": "Neonatal sepsis"},
            {"id": "d3", "cause": "Prematurity"}
        ],
        "age_group": "neonate"
    }


@pytest.fixture
def sample_validate_request():
    """Sample validation request."""
    return {
        "data": {
            "insilicova": [
                {"ID": "d1", "cause": "Birth asphyxia"},
                {"ID": "d2", "cause": "Neonatal sepsis"}
            ]
        },
        "age_group": "neonate",
        "expected_format": "specific_causes"
    }


@pytest.fixture
def mock_dataset_preview_output():
    """Mock dataset preview output."""
    return {
        "success": True,
        "sample_data": [
            {"id": "death_001", "pneumonia": 0, "sepsis_meningitis_inf": 1, "ipre": 0, "prematurity": 0, "congenital_malformation": 0, "other": 0},
            {"id": "death_002", "pneumonia": 1, "sepsis_meningitis_inf": 0, "ipre": 0, "prematurity": 0, "congenital_malformation": 0, "other": 0}
        ],
        "total_records": 1190,
        "columns": ["pneumonia", "sepsis_meningitis_inf", "ipre", "prematurity", "congenital_malformation", "other"],
        "statistics": {
            "total_deaths": 1190,
            "cause_distribution": {
                "pneumonia": 180,
                "sepsis_meningitis_inf": 420,
                "ipre": 290,
                "prematurity": 200,
                "congenital_malformation": 60,
                "other": 40
            },
            "most_common_cause": "sepsis_meningitis_inf",
            "least_common_cause": "other"
        },
        "metadata": {
            "description": "Mozambique COMSA study with broad cause assignments",
            "age_group": "neonate",
            "format": "binary_matrix",
            "source": "COMSA study"
        }
    }


@pytest.fixture
def mock_cause_mappings_output():
    """Mock cause mappings output."""
    return {
        "success": True,
        "age_group": "neonate",
        "broad_causes": ["congenital_malformation", "pneumonia", "sepsis_meningitis_inf", "ipre", "other", "prematurity"],
        "mappings": [
            {"specific_cause": "Birth asphyxia", "broad_cause": "ipre"},
            {"specific_cause": "Neonatal sepsis", "broad_cause": "sepsis_meningitis_inf"},
            {"specific_cause": "Prematurity", "broad_cause": "prematurity"},
            {"specific_cause": "Pneumonia", "broad_cause": "pneumonia"},
            {"specific_cause": "Congenital malformation", "broad_cause": "congenital_malformation"}
        ]
    }


@pytest.fixture
def mock_convert_causes_output():
    """Mock convert causes output."""
    return {
        "success": True,
        "converted_data": [
            {"id": "d1", "specific_cause": "Birth asphyxia", "broad_cause": "ipre"},
            {"id": "d2", "specific_cause": "Neonatal sepsis", "broad_cause": "sepsis_meningitis_inf"},
            {"id": "d3", "specific_cause": "Prematurity", "broad_cause": "prematurity"}
        ],
        "broad_cause_matrix": {
            "congenital_malformation": [0, 0, 0],
            "pneumonia": [0, 0, 0],
            "sepsis_meningitis_inf": [0, 1, 0],
            "ipre": [1, 0, 0],
            "other": [0, 0, 0],
            "prematurity": [0, 0, 1]
        },
        "conversion_summary": {
            "congenital_malformation": 0,
            "pneumonia": 0,
            "sepsis_meningitis_inf": 1,
            "ipre": 1,
            "other": 0,
            "prematurity": 1
        },
        "unmapped_causes": []
    }


# Async infrastructure fixtures
@pytest_asyncio.fixture
async def fake_redis_client():
    """Provide a real fakeredis client for integration testing."""
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis_client
    await redis_client.flushall()
    await redis_client.aclose()


@pytest.fixture
def mock_redis_client():
    """Provide a mock Redis client for unit testing."""
    return MockRedisClient()


@pytest.fixture
def mock_celery_app():
    """Mock Celery application for testing."""
    mock_app = MagicMock()
    mock_app.control.inspect.active.return_value = {}
    mock_app.control.inspect.reserved.return_value = {}
    return mock_app


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    def create_task(task_id: str = "test-task", status: str = "PENDING"):
        return MockCeleryResult(task_id, status)
    return create_task


@pytest_asyncio.fixture
async def websocket_client():
    """Provide a mock WebSocket client for testing."""
    return MockWebSocket()


@pytest.fixture
def redis_subscriber():
    """Provide a mock Redis subscriber for testing."""
    return MockRedisSubscriber()


# Async test utilities
@pytest_asyncio.fixture
async def async_test_timeout():
    """Provide a timeout for async tests."""
    return 10.0  # 10 seconds


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# WebSocket testing fixtures
@pytest_asyncio.fixture
async def websocket_test_server():
    """Mock WebSocket test server."""
    class MockWebSocketServer:
        def __init__(self):
            self.connections = []
            self.messages = []

        async def connect(self, websocket):
            self.connections.append(websocket)
            await websocket.accept()

        async def disconnect(self, websocket):
            if websocket in self.connections:
                self.connections.remove(websocket)

        async def broadcast(self, message: str):
            for ws in self.connections:
                await ws.send_text(message)

        def get_connection_count(self):
            return len(self.connections)

    return MockWebSocketServer()


# Performance testing fixtures
@pytest.fixture
def performance_metrics():
    """Track performance metrics during tests."""
    class PerformanceTracker:
        def __init__(self):
            self.start_times = {}
            self.durations = {}
            self.memory_usage = {}

        def start_timer(self, name: str):
            self.start_times[name] = datetime.utcnow()

        def end_timer(self, name: str):
            if name in self.start_times:
                duration = datetime.utcnow() - self.start_times[name]
                self.durations[name] = duration.total_seconds()

        def get_duration(self, name: str) -> float:
            return self.durations.get(name, 0.0)

        def record_memory(self, name: str, usage: int):
            self.memory_usage[name] = usage

    return PerformanceTracker()


# Concurrent testing fixtures
@pytest_asyncio.fixture
async def concurrent_client_pool(async_client):
    """Provide multiple HTTP clients for concurrent testing."""
    clients = []
    for i in range(5):
        async with AsyncClient(app=app, base_url="http://test") as client:
            clients.append(client)

    yield clients

    # Cleanup is handled by context manager


# Security testing fixtures
@pytest.fixture
def security_test_inputs():
    """Provide security test inputs for validation testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE jobs; --",
            "1; DELETE FROM users WHERE id=1; --",
            "admin'/**/OR/**/1=1/**/--"
        ],
        "xss_payloads": [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>"
        ],
        "path_traversal": [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow"
        ],
        "command_injection": [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)"
        ]
    }


# Load testing fixtures
@pytest.fixture
def load_test_config():
    """Configuration for load testing."""
    return {
        "max_concurrent_requests": 50,
        "request_timeout": 30.0,
        "ramp_up_duration": 5.0,
        "test_duration": 60.0,
        "success_rate_threshold": 0.95
    }


# Global fixtures for mocking
@pytest.fixture(autouse=True)
def mock_file_exists(monkeypatch):
    """Mock os.path.exists to always return True for data files."""
    def mock_exists(path):
        if "data/" in path and path.endswith(".rda"):
            return True
        return False

    monkeypatch.setattr("os.path.exists", mock_exists)


# Async calibration mock fixtures
@pytest.fixture
def mock_async_calibration_service():
    """Mock async calibration service."""
    class MockAsyncCalibrationService:
        def __init__(self):
            self.jobs = {}
            self.job_counter = 0

        async def create_job(self, request_data: Dict[str, Any]) -> str:
            self.job_counter += 1
            job_id = f"mock-job-{self.job_counter}"

            self.jobs[job_id] = {
                "job_id": job_id,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "progress": 0,
                "stage": "queued",
                "request_data": request_data
            }

            return job_id

        async def get_job_status(self, job_id: str) -> Dict[str, Any]:
            return self.jobs.get(job_id)

        async def update_job_status(self, job_id: str, updates: Dict[str, Any]):
            if job_id in self.jobs:
                self.jobs[job_id].update(updates)

        async def cancel_job(self, job_id: str) -> bool:
            if job_id in self.jobs:
                self.jobs[job_id]["status"] = "cancelled"
                self.jobs[job_id]["cancelled_at"] = datetime.utcnow().isoformat()
                return True
            return False

        async def delete_job(self, job_id: str) -> bool:
            if job_id in self.jobs:
                del self.jobs[job_id]
                return True
            return False

        def list_jobs(self, limit: int = 50, status: str = None) -> List[Dict[str, Any]]:
            jobs = list(self.jobs.values())

            if status:
                jobs = [job for job in jobs if job["status"] == status]

            return jobs[:limit]

    return MockAsyncCalibrationService()


# WebSocket testing utilities
@pytest.fixture
def websocket_test_utils():
    """Utilities for WebSocket testing."""
    class WebSocketTestUtils:
        @staticmethod
        async def simulate_connection(websocket, job_id: str, duration: float = 1.0):
            """Simulate a WebSocket connection for testing."""
            await websocket.accept()

            # Send some test messages
            messages = [
                {"type": "log", "message": "Job started", "timestamp": datetime.utcnow().isoformat()},
                {"type": "progress", "progress": 25, "stage": "processing"},
                {"type": "progress", "progress": 50, "stage": "calibrating"},
                {"type": "log", "message": "Job completed", "timestamp": datetime.utcnow().isoformat()}
            ]

            for msg in messages:
                await websocket.send_json(msg)
                await asyncio.sleep(duration / len(messages))

        @staticmethod
        async def collect_messages(websocket, timeout: float = 5.0):
            """Collect messages from WebSocket with timeout."""
            messages = []

            try:
                while True:
                    message = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=timeout
                    )
                    messages.append(message)
            except asyncio.TimeoutError:
                pass

            return messages

    return WebSocketTestUtils()


@pytest.fixture
def mock_tempfile(tmp_path):
    """Mock tempfile.TemporaryDirectory to use pytest tmp_path."""
    def mock_temp_dir(*args, **kwargs):
        class MockTempDir:
            def __init__(self, path):
                self.path = str(path)

            def __enter__(self):
                return self.path

            def __exit__(self, *args):
                pass

        return MockTempDir(tmp_path)

    return mock_temp_dir


class MockFileHandler:
    """Helper class for mocking file operations in tests."""

    def __init__(self):
        self.files = {}

    def write_json(self, filepath: str, data: Dict[str, Any]):
        """Mock writing JSON to file."""
        self.files[filepath] = data

    def read_json(self, filepath: str) -> Dict[str, Any]:
        """Mock reading JSON from file."""
        return self.files.get(filepath, {})

    def file_exists(self, filepath: str) -> bool:
        """Mock file existence check."""
        return filepath in self.files


@pytest.fixture
def mock_file_handler():
    """Fixture providing mock file handler."""
    return MockFileHandler()


# Performance test fixtures
@pytest.fixture
def performance_test_data():
    """Large dataset for performance testing."""
    return {
        "va_data": {
            "insilicova": [
                {"ID": f"death_{i:06d}", "cause": "Birth asphyxia" if i % 2 == 0 else "Neonatal sepsis"}
                for i in range(1000)
            ]
        },
        "age_group": "neonate",
        "country": "Mozambique"
    }


# Error scenarios
@pytest.fixture
def malicious_input_data():
    """Test data for security testing."""
    return {
        "sql_injection": {
            "data": [{"id": "'; DROP TABLE users; --", "cause": "test"}],
            "age_group": "neonate"
        },
        "command_injection": {
            "country": "Mozambique; rm -rf /",
            "age_group": "neonate"
        },
        "oversized_data": {
            "va_data": {
                "insilicova": [{"ID": f"d{i}", "cause": "test"} for i in range(100000)]
            }
        }
    }


@pytest.fixture
def edge_case_data():
    """Edge case test data."""
    return {
        "empty_data": {"data": [], "age_group": "neonate"},
        "missing_fields": {"data": [{"ID": "d1"}], "age_group": "neonate"},
        "invalid_age_group": {"age_group": "invalid"},
        "unknown_country": {"country": "Unknown", "age_group": "neonate"},
        "negative_counts": {"data": [-1, -2, -3], "age_group": "neonate"}
    }


# Async-specific fixtures for async calibration testing
@pytest.fixture
def async_calibration_request():
    """Sample async calibration request."""
    return {
        "va_data": {
            "insilicova": [
                {"ID": "async_d1", "cause": "Birth asphyxia"},
                {"ID": "async_d2", "cause": "Neonatal sepsis"}
            ]
        },
        "age_group": "neonate",
        "country": "Mozambique",
        "mmat_type": "prior",
        "ensemble": True,
        "user_id": "test-async-user"
    }


@pytest.fixture
def websocket_test_messages():
    """Sample WebSocket messages for testing."""
    return [
        {
            "type": "log",
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Starting calibration process"
        },
        {
            "type": "progress",
            "progress": 25,
            "stage": "data_loading",
            "eta": "2 minutes"
        },
        {
            "type": "log",
            "timestamp": datetime.utcnow().isoformat(),
            "level": "DEBUG",
            "message": "Running R script with parameters"
        },
        {
            "type": "progress",
            "progress": 50,
            "stage": "calibration_running",
            "eta": "1 minute"
        },
        {
            "type": "status",
            "status": "completed",
            "results": {
                "uncalibrated": {"pneumonia": 0.15},
                "calibrated": {"insilicova": {"pneumonia": 0.12}}
            }
        }
    ]


@pytest.fixture
def concurrent_job_requests(sample_calibration_request):
    """Generate multiple calibration requests for concurrent testing."""
    def generate_requests(count: int = 10):
        requests = []
        for i in range(count):
            request = {
                **sample_calibration_request,
                "async_mode": True,
                "user_id": f"concurrent-user-{i}",
                "country": ["Mozambique", "Kenya", "Ethiopia"][i % 3]
            }
            requests.append(request)
        return requests

    return generate_requests


# Cleanup fixtures
@pytest_asyncio.fixture(autouse=True)
async def cleanup_async_resources():
    """Automatically cleanup async resources after each test."""
    # Before test
    yield

    # After test cleanup
    # Cancel any running tasks
    tasks = [task for task in asyncio.all_tasks() if not task.done()]
    for task in tasks:
        if not task.cancelled():
            task.cancel()

    # Wait for tasks to complete
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@pytest.fixture(autouse=True)
def reset_mock_state():
    """Reset mock state between tests."""
    # Reset any global mock state here
    yield
    # Cleanup after test