#!/usr/bin/env python3
"""
Test the synchronous /calibrate endpoint specifically.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_sync_calibrate():
    """Test the synchronous /calibrate endpoint"""
    print("Testing synchronous /calibrate endpoint...")

    payload = {
        "data_source": "sample",
        "sample_dataset": "comsamoz_broad",
        "age_group": "neonate",  # Fixed: comsamoz_broad is neonate data
        "country": "Mozambique",
        "mmat_type": "prior",
        "ensemble": False,
        "async": False  # Force synchronous execution
    }

    print(f"Payload: {json.dumps(payload, indent=2)}")

    response = requests.post(f"{BASE_URL}/calibrate", json=payload)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    test_sync_calibrate()