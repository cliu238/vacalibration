#!/usr/bin/env python3
"""Test Celery endpoint with caching disabled"""
import requests
import time
import json

# Test Celery endpoint WITHOUT caching
payload = {
    "data_source": "sample",
    "sample_dataset": "comsamoz_broad",
    "age_group": "neonate",
    "country": "Mozambique",
    "mmat_type": "prior",
    "ensemble": False,
    "use_cache": False  # Disable caching to force fresh R script execution
}

print("Testing Celery /jobs/calibrate endpoint (no cache)...")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

# Submit job
response = requests.post("http://localhost:8000/jobs/calibrate", json=payload)
print(f"Submit Status Code: {response.status_code}")

if response.status_code != 200:
    print(f"Error: {response.text}")
    exit(1)

job_data = response.json()
job_id = job_data.get('job_id')
print(f"Job ID: {job_id}\n")

# Poll for results
print("Waiting for job completion...")
for i in range(30):  # Wait up to 30 seconds
    time.sleep(1)
    result_response = requests.get(f"http://localhost:8000/jobs/{job_id}")
    result = result_response.json()

    status = result.get('status')
    print(f"[{i+1}s] Status: {status}")

    if status == 'completed':
        print("\n✅ Job completed successfully!")
        print(f"Result: {json.dumps(result.get('result'), indent=2)}")
        break
    elif status == 'failed':
        print(f"\n❌ Job failed: {result.get('error')}")
        break
else:
    print("\n⚠️ Timeout waiting for job completion")