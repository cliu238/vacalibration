"""
Shared test fixtures for VA-Calibration API tests.
Simplified version focusing on core functionality.
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport
from typing import Dict, List, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main_direct import app


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
def sample_death_counts() -> Dict[str, int]:
    """Sample death counts by broad cause (neonate)."""
    # Death counts format as per API design: dictionary with cause names as keys
    return {
        "congenital_malformation": 50,
        "pneumonia": 150,
        "sepsis_meningitis_inf": 300,
        "ipre": 250,
        "other": 100,
        "prematurity": 200
    }


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


# Global fixtures for mocking
@pytest.fixture(autouse=True)
def mock_file_exists(monkeypatch):
    """Mock os.path.exists to always return True for data files."""
    def mock_exists(path):
        if "data/" in path and path.endswith(".rda"):
            return True
        return False

    monkeypatch.setattr("os.path.exists", mock_exists)