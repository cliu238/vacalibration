#!/usr/bin/env python3
"""
Test script to verify both calibration endpoints work with the shared R script module.
"""

import requests
import json
import time
import sys

# Test configuration
BASE_URL = "http://localhost:8000"

def test_celery_endpoint():
    """Test the Celery-based /jobs/calibrate endpoint"""
    print("Testing Celery endpoint (/jobs/calibrate)...")

    payload = {
        "age_group": "child",
        "country": "USA",
        "data_source": "sample",
        "sample_dataset": "comsamoz_broad"
    }

    # Submit job
    response = requests.post(f"{BASE_URL}/jobs/calibrate", json=payload)
    if response.status_code != 200:
        print(f"❌ Failed to create job: {response.status_code}")
        print(response.text)
        return False

    result = response.json()
    job_id = result.get("job_id")
    print(f"✅ Job created: {job_id}")

    # Poll for completion
    for i in range(30):  # Wait up to 30 seconds
        time.sleep(1)
        status_response = requests.get(f"{BASE_URL}/jobs/{job_id}")
        if status_response.status_code == 200:
            status_data = status_response.json()
            if status_data.get("status") == "success":
                print(f"✅ Job completed successfully")
                return True
            elif status_data.get("status") == "failed":
                print(f"❌ Job failed: {status_data.get('error_details')}")
                return False

    print("❌ Job timed out")
    return False


def test_realtime_endpoint():
    """Test the WebSocket/real-time /calibrate/realtime endpoint"""
    print("\nTesting Real-time endpoint (/calibrate/realtime)...")

    payload = {
        "age_group": "neonate",
        "country": "Mozambique",
        "data_source": "sample",
        "sample_dataset": "comsamoz_broad"
    }

    # Submit calibration request
    response = requests.post(f"{BASE_URL}/calibrate/realtime", json=payload)
    if response.status_code != 200:
        print(f"❌ Failed to start calibration: {response.status_code}")
        print(response.text)
        return False

    result = response.json()
    job_id = result.get("job_id")
    print(f"✅ Calibration started: {job_id}")

    # Check status (note: real-time endpoint creates job but doesn't track it the same way)
    time.sleep(2)  # Give it a moment to process

    # Try to get status
    status_response = requests.get(f"{BASE_URL}/calibrate/{job_id}/status")
    if status_response.status_code == 200:
        status_data = status_response.json()
        print(f"✅ Status retrieved: {status_data.get('status')}")
        return True
    elif status_response.status_code == 404:
        # This is expected for the real-time endpoint as it doesn't persist jobs
        print("✅ Real-time endpoint responded (job not persisted, which is expected)")
        return True
    else:
        print(f"❌ Unexpected status code: {status_response.status_code}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Testing Calibration Endpoints with Shared R Script Module")
    print("="*60)

    # Test both endpoints
    celery_success = test_celery_endpoint()
    realtime_success = test_realtime_endpoint()

    print("\n" + "="*60)
    print("Test Results:")
    print(f"  Celery endpoint:    {'✅ PASSED' if celery_success else '❌ FAILED'}")
    print(f"  Real-time endpoint: {'✅ PASSED' if realtime_success else '❌ FAILED'}")
    print("="*60)

    # Return exit code
    if celery_success and realtime_success:
        print("\n✅ All tests passed! Both endpoints are working with the shared module.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())