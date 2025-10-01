#!/usr/bin/env python3
"""
Test Celery endpoint with sample dataset parameters.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

payload = {
    "data_source": "sample",
    "sample_dataset": "comsamoz_broad",
    "age_group": "child",
    "country": "Mozambique",
    "mmat_type": "prior",
    "ensemble": False
}

print("Testing Celery endpoint with sample dataset...")
print(f"Payload: {json.dumps(payload, indent=2)}")

# Submit job
response = requests.post(f"{BASE_URL}/jobs/calibrate", json=payload)
print(f"\nStatus Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    job_id = response.json().get("job_id")
    print(f"\nPolling job {job_id}...")

    for i in range(30):
        time.sleep(1)
        status_response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"  Status: {status}")

            if status == "success":
                print("✅ Celery endpoint WORKS with sample dataset!")
                break
            elif status == "failed":
                print(f"❌ Job failed: {status_data}")
                break