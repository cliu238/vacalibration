#!/usr/bin/env python3
"""
Comprehensive Integration Example for Job Management Endpoints
Demonstrates all features including batch processing, caching, and monitoring
"""

import asyncio
import httpx
import json
import time
from datetime import datetime
from typing import List, Dict, Any


class VACalibrationJobClient:
    """Client for interacting with VA-Calibration job management API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = httpx.AsyncClient(timeout=60.0)

    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()

    async def create_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calibration job"""
        url = f"{self.base_url}/api/v1/calibrate/async"
        response = await self.session.post(url, json=job_data)
        response.raise_for_status()
        return response.json()

    async def create_batch_jobs(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a batch of calibration jobs"""
        url = f"{self.base_url}/api/v1/calibrate/batch"
        response = await self.session.post(url, json=batch_data)
        response.raise_for_status()
        return response.json()

    async def get_job_status(self, job_id: str, log_level: str = None, log_limit: int = 100) -> Dict[str, Any]:
        """Get comprehensive job status"""
        url = f"{self.base_url}/api/v1/calibrate/{job_id}/status"
        params = {"log_limit": log_limit}
        if log_level:
            params["log_level"] = log_level

        response = await self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_job_result(self, job_id: str) -> Dict[str, Any]:
        """Get final job results"""
        url = f"{self.base_url}/api/v1/calibrate/{job_id}/result"
        response = await self.session.get(url)
        response.raise_for_status()
        return response.json()

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job"""
        url = f"{self.base_url}/api/v1/calibrate/{job_id}"
        response = await self.session.delete(url)
        response.raise_for_status()
        return response.json()

    async def list_jobs(self, **filters) -> Dict[str, Any]:
        """List jobs with filtering"""
        url = f"{self.base_url}/api/v1/jobs"
        response = await self.session.get(url, params=filters)
        response.raise_for_status()
        return response.json()

    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get batch processing status"""
        url = f"{self.base_url}/api/v1/calibrate/batch/{batch_id}/status"
        response = await self.session.get(url)
        response.raise_for_status()
        return response.json()

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        url = f"{self.base_url}/api/v1/cache/stats"
        response = await self.session.get(url)
        response.raise_for_status()
        return response.json()

    async def clear_cache(self, confirm: bool = True, **filters) -> Dict[str, Any]:
        """Clear cache with confirmation"""
        url = f"{self.base_url}/api/v1/cache/clear"
        params = {"confirm": confirm, **filters}
        response = await self.session.delete(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_system_health(self) -> Dict[str, Any]:
        """Get job system health"""
        url = f"{self.base_url}/api/v1/jobs/health"
        response = await self.session.get(url)
        response.raise_for_status()
        return response.json()


async def demo_single_job_workflow():
    """Demonstrate single job creation, monitoring, and result retrieval"""
    print("=== Single Job Workflow Demo ===")

    client = VACalibrationJobClient()

    try:
        # 1. Create a calibration job
        job_request = {
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate",
            "country": "Mozambique",
            "mmat_type": "prior",
            "ensemble": True,
            "priority": 7,
            "timeout_minutes": 30,
            "use_cache": True
        }

        print("Creating calibration job...")
        job_response = await client.create_job(job_request)
        job_id = job_response["job_id"]
        print(f"✓ Job created: {job_id}")

        # 2. Monitor job progress
        print("\nMonitoring job progress...")
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            status_response = await client.get_job_status(job_id, log_level="info")
            status = status_response["status"]

            print(f"  Status: {status}")

            if status_response.get("progress"):
                progress = status_response["progress"]
                print(f"  Progress: {progress['progress_percentage']:.1f}% - {progress['step_name']}")

            if len(status_response["logs"]) > 0:
                latest_log = status_response["logs"][0]
                print(f"  Latest: {latest_log['message']}")

            if status in ["success", "failed", "cancelled"]:
                break

            attempt += 1
            await asyncio.sleep(2)

        # 3. Get final results
        if status == "success":
            print("\nRetrieving results...")
            result_response = await client.get_job_result(job_id)

            print("✓ Calibration completed successfully!")
            print(f"  Algorithms processed: {len(result_response['result'].get('calibrated', {}))}")

            if result_response.get("cache_info"):
                print("  ✓ Result was cached for future use")

        else:
            print(f"✗ Job completed with status: {status}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


async def demo_batch_processing():
    """Demonstrate batch job processing with different configurations"""
    print("\n=== Batch Processing Demo ===")

    client = VACalibrationJobClient()

    try:
        # 1. Create batch with different countries and age groups
        batch_request = {
            "jobs": [
                {
                    "va_data": {"insilicova": "use_example"},
                    "age_group": "neonate",
                    "country": "Mozambique",
                    "priority": 8
                },
                {
                    "va_data": {"insilicova": "use_example"},
                    "age_group": "neonate",
                    "country": "Kenya",
                    "priority": 7
                },
                {
                    "va_data": {"insilicova": "use_example"},
                    "age_group": "child",
                    "country": "Bangladesh",
                    "priority": 6
                },
                {
                    "va_data": {"insilicova": "use_example"},
                    "age_group": "child",
                    "country": "Mali",
                    "priority": 5
                }
            ],
            "batch_name": "Multi-country comparison",
            "parallel_limit": 3,
            "fail_fast": False
        }

        print("Creating batch with 4 calibration jobs...")
        batch_response = await client.create_batch_jobs(batch_request)
        batch_id = batch_response["batch_id"]
        job_ids = batch_response["job_ids"]

        print(f"✓ Batch created: {batch_id}")
        print(f"  Job IDs: {', '.join(job_ids)}")

        # 2. Monitor batch progress
        print("\nMonitoring batch progress...")
        max_attempts = 60
        attempt = 0

        while attempt < max_attempts:
            batch_status = await client.get_batch_status(batch_id)

            print(f"  Batch Status: {batch_status['batch_status']}")
            print(f"  Progress: {batch_status['completed_jobs']}/{batch_status['total_jobs']} completed")
            print(f"  Running: {batch_status['running_jobs']}, Failed: {batch_status['failed_jobs']}")

            if batch_status["batch_status"] in ["completed", "failed", "partial"]:
                break

            attempt += 1
            await asyncio.sleep(3)

        # 3. Show individual job results
        print("\nIndividual job results:")
        for i, job_id in enumerate(job_ids):
            try:
                status = await client.get_job_status(job_id)
                job_status = status["status"]
                country = batch_request["jobs"][i]["country"]
                age_group = batch_request["jobs"][i]["age_group"]

                print(f"  {country} ({age_group}): {job_status}")

                if job_status == "success":
                    result = await client.get_job_result(job_id)
                    algorithms = len(result["result"].get("calibrated", {}))
                    print(f"    ✓ {algorithms} algorithms processed")

            except Exception as e:
                print(f"    ✗ Error getting result: {e}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


async def demo_cache_management():
    """Demonstrate cache management and statistics"""
    print("\n=== Cache Management Demo ===")

    client = VACalibrationJobClient()

    try:
        # 1. Get initial cache statistics
        print("Getting cache statistics...")
        cache_stats = await client.get_cache_stats()

        print(f"  Cached results: {cache_stats['total_cached_results']}")
        print(f"  Cache size: {cache_stats['total_cache_size_mb']:.2f} MB")
        print(f"  Hit rate: {cache_stats['cache_hit_rate']:.1f}%")

        # 2. Create a job that should create cache entry
        print("\nCreating job to test caching...")
        job_request = {
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate",
            "country": "Mozambique",
            "use_cache": True
        }

        job_response = await client.create_job(job_request)
        job_id = job_response["job_id"]

        # Wait for completion
        for _ in range(30):
            status = await client.get_job_status(job_id)
            if status["status"] in ["success", "failed"]:
                break
            await asyncio.sleep(2)

        # 3. Create identical job to test cache hit
        if status["status"] == "success":
            print("Creating identical job to test cache...")
            start_time = time.time()

            cached_job_response = await client.create_job(job_request)
            cached_job_id = cached_job_response["job_id"]

            # This should complete much faster due to caching
            for _ in range(10):
                cached_status = await client.get_job_status(cached_job_id)
                if cached_status["status"] in ["success", "failed"]:
                    break
                await asyncio.sleep(1)

            end_time = time.time()

            if cached_status["status"] == "success":
                result = await client.get_job_result(cached_job_id)
                if result.get("cache_info"):
                    print(f"  ✓ Cache hit! Completed in {end_time - start_time:.1f} seconds")
                    print(f"    Original job: {result['cache_info']['source_job_id']}")

        # 4. Get updated cache statistics
        print("\nUpdated cache statistics...")
        new_cache_stats = await client.get_cache_stats()
        print(f"  Cached results: {new_cache_stats['total_cached_results']}")
        print(f"  Cache size: {new_cache_stats['total_cache_size_mb']:.2f} MB")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


async def demo_job_filtering_and_management():
    """Demonstrate job listing, filtering, and management"""
    print("\n=== Job Management Demo ===")

    client = VACalibrationJobClient()

    try:
        # 1. Create several jobs for demonstration
        print("Creating test jobs...")
        job_ids = []

        countries = ["Mozambique", "Kenya", "Bangladesh"]
        age_groups = ["neonate", "child"]

        for country in countries:
            for age_group in age_groups:
                job_request = {
                    "va_data": {"insilicova": "use_example"},
                    "age_group": age_group,
                    "country": country,
                    "priority": 5
                }

                response = await client.create_job(job_request)
                job_ids.append(response["job_id"])

        print(f"✓ Created {len(job_ids)} test jobs")

        # 2. List all jobs
        print("\nListing all jobs...")
        all_jobs = await client.list_jobs(page=1, page_size=20)
        print(f"  Total jobs: {all_jobs['total_count']}")
        print(f"  Current page: {len(all_jobs['jobs'])} jobs")

        # 3. Filter by status
        print("\nFiltering by status...")
        pending_jobs = await client.list_jobs(status="pending")
        running_jobs = await client.list_jobs(status="running")

        print(f"  Pending jobs: {pending_jobs['total_count']}")
        print(f"  Running jobs: {running_jobs['total_count']}")

        # 4. Filter by age group
        print("\nFiltering by age group...")
        neonate_jobs = await client.list_jobs(age_group="neonate")
        child_jobs = await client.list_jobs(age_group="child")

        print(f"  Neonate jobs: {neonate_jobs['total_count']}")
        print(f"  Child jobs: {child_jobs['total_count']}")

        # 5. Cancel some jobs for demonstration
        if len(job_ids) >= 2:
            print(f"\nCancelling job: {job_ids[0]}")
            cancel_response = await client.cancel_job(job_ids[0])
            print(f"  Status: {cancel_response['status']}")

        # 6. Show updated job counts
        await asyncio.sleep(1)  # Give time for status updates
        updated_jobs = await client.list_jobs()
        print(f"\nUpdated job count: {updated_jobs['total_count']}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


async def demo_system_monitoring():
    """Demonstrate system health and monitoring"""
    print("\n=== System Monitoring Demo ===")

    client = VACalibrationJobClient()

    try:
        # 1. Check system health
        print("Checking system health...")
        health = await client.get_system_health()

        print(f"  Overall status: {health['status']}")
        print(f"  Redis: {health['redis']}")
        print(f"  Celery: {health['celery']}")

        if "queue_stats" in health:
            stats = health["queue_stats"]
            if isinstance(stats, dict) and "error" not in stats:
                print(f"  Pending jobs: {stats.get('pending_jobs', 'N/A')}")
                print(f"  Cached results: {stats.get('cached_results', 'N/A')}")

        # 2. Show cache statistics
        print("\nCache performance...")
        cache_stats = await client.get_cache_stats()
        print(f"  Total cached: {cache_stats['total_cached_results']}")
        print(f"  Cache size: {cache_stats['total_cache_size_mb']:.2f} MB")

        if cache_stats.get('oldest_cached_result'):
            print(f"  Oldest result: {cache_stats['oldest_cached_result']}")
        if cache_stats.get('newest_cached_result'):
            print(f"  Newest result: {cache_stats['newest_cached_result']}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        await client.close()


async def main():
    """Run all demonstrations"""
    print("VA-Calibration Job Management API Integration Demo")
    print("=" * 50)

    try:
        # Run demonstrations in sequence
        await demo_single_job_workflow()
        await demo_batch_processing()
        await demo_cache_management()
        await demo_job_filtering_and_management()
        await demo_system_monitoring()

        print("\n" + "=" * 50)
        print("✓ All demonstrations completed successfully!")

    except Exception as e:
        print(f"\n✗ Demo failed: {e}")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(main())