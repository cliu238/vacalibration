#!/usr/bin/env python3
"""
Usage examples for async calibration API
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any


class AsyncCalibrationClient:
    """Client for interacting with async calibration API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    async def start_calibration(self, request_data: Dict[str, Any]) -> str:
        """Start async calibration and return job ID"""
        response = await self.client.post(
            f"{self.base_url}/jobs/calibrate",
            json=request_data
        )
        response.raise_for_status()
        result = response.json()
        return result["job_id"]

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status and results"""
        response = await self.client.get(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    async def get_job_output(self, job_id: str, start_line: int = 0) -> Dict[str, Any]:
        """Get job output for streaming"""
        response = await self.client.get(
            f"{self.base_url}/jobs/{job_id}/output",
            params={"start_line": start_line}
        )
        response.raise_for_status()
        return response.json()

    async def wait_for_completion(self, job_id: str, poll_interval: int = 2) -> Dict[str, Any]:
        """Wait for job completion with progress monitoring"""
        print(f"Monitoring job {job_id}...")

        output_line = 0
        while True:
            # Get status
            status = await self.get_job_status(job_id)
            print(f"Status: {status['status']}, Progress: {status['progress']}%")

            # Get new output
            output_data = await self.get_job_output(job_id, start_line=output_line)
            if output_data["r_output"]:
                for line in output_data["r_output"]:
                    print(f"R: {line}")
                output_line += len(output_data["r_output"])

            # Check if completed
            if status["status"] in ["completed", "failed", "cancelled"]:
                print(f"Job {job_id} finished with status: {status['status']}")
                return status

            await asyncio.sleep(poll_interval)

    async def list_jobs(self, limit: int = 10, status: str = None) -> Dict[str, Any]:
        """List recent jobs"""
        params = {"limit": limit}
        if status:
            params["status"] = status

        response = await self.client.get(f"{self.base_url}/jobs", params=params)
        response.raise_for_status()
        return response.json()


async def example_basic_async_calibration():
    """Example: Basic async calibration"""
    print("=== Basic Async Calibration Example ===")

    client = AsyncCalibrationClient()

    try:
        # Start calibration job
        request = {
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate",
            "country": "Mozambique"
        }

        job_id = await client.start_calibration(request)
        print(f"Started job: {job_id}")

        # Wait for completion
        result = await client.wait_for_completion(job_id)

        if result["status"] == "completed":
            print("\n=== Calibration Results ===")
            print(json.dumps(result["result"], indent=2))
        else:
            print(f"Job failed: {result.get('error', 'Unknown error')}")

    finally:
        await client.close()


async def example_multiple_jobs():
    """Example: Managing multiple jobs"""
    print("=== Multiple Jobs Example ===")

    client = AsyncCalibrationClient()

    try:
        # Start multiple jobs
        jobs = []
        for i, age_group in enumerate(["neonate", "child"]):
            request = {
                "va_data": {"insilicova": "use_example"},
                "age_group": age_group,
                "country": "Mozambique"
            }

            job_id = await client.start_calibration(request)
            jobs.append((job_id, age_group))
            print(f"Started job {i+1}: {job_id} ({age_group})")

        # Monitor all jobs
        print("\nMonitoring jobs...")
        completed_jobs = []

        while len(completed_jobs) < len(jobs):
            for job_id, age_group in jobs:
                if job_id in completed_jobs:
                    continue

                status = await client.get_job_status(job_id)
                print(f"Job {job_id} ({age_group}): {status['status']} - {status['progress']}%")

                if status["status"] in ["completed", "failed", "cancelled"]:
                    completed_jobs.append(job_id)

            await asyncio.sleep(3)

        print(f"\nAll {len(jobs)} jobs completed!")

        # Show results
        for job_id, age_group in jobs:
            status = await client.get_job_status(job_id)
            print(f"\n=== Results for {age_group} (Job {job_id}) ===")
            if status["status"] == "completed":
                print("Success!")
            else:
                print(f"Failed: {status.get('error', 'Unknown error')}")

    finally:
        await client.close()


async def example_streaming_output():
    """Example: Real-time output streaming"""
    print("=== Streaming Output Example ===")

    client = AsyncCalibrationClient()

    try:
        # Start calibration
        request = {
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate",
            "country": "Mozambique"
        }

        job_id = await client.start_calibration(request)
        print(f"Started job: {job_id}")
        print("Streaming R output...\n")

        # Stream output in real-time
        output_line = 0
        while True:
            status = await client.get_job_status(job_id)

            # Get new output
            output_data = await client.get_job_output(job_id, start_line=output_line)
            if output_data["r_output"]:
                for line in output_data["r_output"]:
                    print(f"[{time.strftime('%H:%M:%S')}] R: {line}")
                output_line += len(output_data["r_output"])

            # Check completion
            if status["status"] in ["completed", "failed", "cancelled"]:
                print(f"\n✓ Job finished: {status['status']}")
                if status["status"] == "completed":
                    print(f"Execution time: {status.get('execution_time', 0):.2f} seconds")
                break

            await asyncio.sleep(1)

    finally:
        await client.close()


async def example_synchronous_vs_async():
    """Example: Compare sync vs async execution"""
    print("=== Synchronous vs Async Comparison ===")

    # Test sync execution
    print("Testing synchronous execution...")
    sync_start = time.time()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/calibrate",
            json={
                "va_data": {"insilicova": "use_example"},
                "age_group": "neonate",
                "async_mode": False
            }
        )
        sync_time = time.time() - sync_start
        print(f"Sync execution completed in {sync_time:.2f} seconds")

    # Test async execution
    print("\nTesting asynchronous execution...")
    async_client = AsyncCalibrationClient()

    try:
        async_start = time.time()

        job_id = await async_client.start_calibration({
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate"
        })

        print(f"Async job started immediately (job_id: {job_id})")
        result = await async_client.wait_for_completion(job_id, poll_interval=1)

        async_time = time.time() - async_start
        print(f"Async execution completed in {async_time:.2f} seconds")

        print(f"\nComparison:")
        print(f"  Sync:  {sync_time:.2f}s (blocking)")
        print(f"  Async: {async_time:.2f}s (non-blocking start)")

    finally:
        await async_client.close()


async def main():
    """Run all examples"""
    examples = [
        ("Basic Async Calibration", example_basic_async_calibration),
        ("Multiple Jobs", example_multiple_jobs),
        ("Streaming Output", example_streaming_output),
        ("Sync vs Async", example_synchronous_vs_async),
    ]

    print("VA-Calibration Async API Examples")
    print("=================================\n")

    for i, (name, func) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\nEnter example number (1-4) or 'all' to run all: ", end="")
    choice = input().strip()

    if choice.lower() == "all":
        for name, func in examples:
            print(f"\n{'='*50}")
            print(f"Running: {name}")
            print('='*50)
            try:
                await func()
            except Exception as e:
                print(f"Error: {e}")
            print("\n" + "="*50)
    else:
        try:
            index = int(choice) - 1
            if 0 <= index < len(examples):
                name, func = examples[index]
                print(f"\nRunning: {name}")
                await func()
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())