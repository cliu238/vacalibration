"""
Unit tests for async calibration features.
Test ID: UT-ASYNC-001

Tests async job creation, status updates, error handling,
and job cancellation with mocked Redis and Celery.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Import the app (assuming async endpoints will be added)
from app.main_direct import app


class MockCeleryResult:
    """Mock Celery AsyncResult for testing."""
    
    def __init__(self, task_id: str, status: str = "PENDING", result: Any = None, traceback: str = None):
        self.id = task_id
        self.status = status
        self.result = result
        self.traceback = traceback
        self.ready_value = status in ["SUCCESS", "FAILURE", "REVOKED"]
    
    def ready(self) -> bool:
        return self.ready_value
    
    def successful(self) -> bool:
        return self.status == "SUCCESS"
    
    def failed(self) -> bool:
        return self.status == "FAILURE"
    
    def revoke(self, terminate: bool = False):
        self.status = "REVOKED"
        self.ready_value = True
    
    def get(self, timeout: float = None, propagate: bool = True):
        if self.status == "SUCCESS":
            return self.result
        elif self.status == "FAILURE" and propagate:
            raise Exception("Task failed")
        elif self.status == "REVOKED":
            raise Exception("Task was revoked")
        else:
            raise Exception("Task not ready")


class MockRedisClient:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.data = {}
        self.expiry = {}
    
    async def set(self, key: str, value: str, ex: int = None):
        self.data[key] = value
        if ex:
            self.expiry[key] = datetime.utcnow() + timedelta(seconds=ex)
        return True
    
    async def get(self, key: str):
        if key in self.expiry and datetime.utcnow() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data.get(key)
    
    async def delete(self, key: str):
        self.data.pop(key, None)
        self.expiry.pop(key, None)
        return True
    
    async def exists(self, key: str):
        return key in self.data
    
    async def hset(self, name: str, mapping: Dict[str, Any]):
        if name not in self.data:
            self.data[name] = {}
        self.data[name].update(mapping)
        return len(mapping)
    
    async def hget(self, name: str, key: str):
        hash_data = self.data.get(name, {})
        return hash_data.get(key)
    
    async def hgetall(self, name: str):
        return self.data.get(name, {})
    
    async def hdel(self, name: str, *keys):
        hash_data = self.data.get(name, {})
        deleted = 0
        for key in keys:
            if key in hash_data:
                del hash_data[key]
                deleted += 1
        return deleted
    
    async def publish(self, channel: str, message: str):
        # Mock publishing - just store for testing
        channel_key = f"channel:{channel}"
        if channel_key not in self.data:
            self.data[channel_key] = []
        self.data[channel_key].append(message)
        return 1


class TestAsyncCalibrationJobs:
    """Test cases for async calibration job management."""
    
    @pytest.mark.asyncio
    async def test_create_calibration_job_success(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app,
        sample_calibration_request
    ):
        """
        Test ID: UT-ASYNC-001-01
        Creating a calibration job should return job ID and initial status.
        """
        job_id = "test-job-123"
        mock_task = MockCeleryResult(job_id, "PENDING")
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.calibration_task.delay', return_value=mock_task) as mock_delay:
            
            response = await async_client.post("/calibrate/async", json=sample_calibration_request)
            
            assert response.status_code == 202  # Accepted
            data = response.json()
            
            assert "job_id" in data
            assert data["status"] == "pending"
            assert "created_at" in data
            assert "estimated_duration" in data
            
            # Verify task was scheduled
            mock_delay.assert_called_once()
            
            # Verify job stored in Redis
            job_data = await mock_redis_client.hgetall(f"job:{data['job_id']}")
            assert job_data is not None
    
    @pytest.mark.asyncio
    async def test_get_job_status_pending(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app
    ):
        """
        Test ID: UT-ASYNC-001-02
        Getting status of pending job should return current progress.
        """
        job_id = "test-job-pending"
        
        # Setup job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "progress": "0",
            "stage": "queued"
        })
        
        mock_result = MockCeleryResult(job_id, "PENDING")
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.AsyncResult', return_value=mock_result):
            
            response = await async_client.get(f"/calibrate/async/{job_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["job_id"] == job_id
            assert data["status"] == "pending"
            assert "progress" in data
            assert "stage" in data
            assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_get_job_status_running(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app
    ):
        """
        Test ID: UT-ASYNC-001-03
        Getting status of running job should return progress details.
        """
        job_id = "test-job-running"
        
        # Setup running job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
            "started_at": datetime.utcnow().isoformat(),
            "progress": "45",
            "stage": "processing_va_data",
            "current_algorithm": "insilicova"
        })
        
        mock_result = MockCeleryResult(job_id, "PROGRESS", {
            "current": 45,
            "total": 100,
            "stage": "processing_va_data"
        })
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.AsyncResult', return_value=mock_result):
            
            response = await async_client.get(f"/calibrate/async/{job_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["job_id"] == job_id
            assert data["status"] == "running"
            assert data["progress"] == 45
            assert data["stage"] == "processing_va_data"
            assert "started_at" in data
            assert "estimated_completion" in data
    
    @pytest.mark.asyncio
    async def test_get_job_status_completed(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app,
        mock_r_success_output
    ):
        """
        Test ID: UT-ASYNC-001-04
        Getting status of completed job should return results.
        """
        job_id = "test-job-completed"
        completed_at = datetime.utcnow().isoformat()
        
        # Setup completed job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "completed",
            "created_at": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
            "started_at": (datetime.utcnow() - timedelta(minutes=4)).isoformat(),
            "completed_at": completed_at,
            "progress": "100",
            "stage": "completed",
            "result": json.dumps(mock_r_success_output)
        })
        
        mock_result = MockCeleryResult(job_id, "SUCCESS", mock_r_success_output)
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.AsyncResult', return_value=mock_result):
            
            response = await async_client.get(f"/calibrate/async/{job_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["job_id"] == job_id
            assert data["status"] == "completed"
            assert data["progress"] == 100
            assert data["completed_at"] == completed_at
            assert "results" in data
            assert "duration" in data
            
            # Check results structure
            results = data["results"]
            assert "uncalibrated" in results
            assert "calibrated" in results
    
    @pytest.mark.asyncio
    async def test_get_job_status_failed(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app
    ):
        """
        Test ID: UT-ASYNC-001-05
        Getting status of failed job should return error details.
        """
        job_id = "test-job-failed"
        error_message = "R script execution failed: Missing required packages"
        
        # Setup failed job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "failed",
            "created_at": (datetime.utcnow() - timedelta(minutes=3)).isoformat(),
            "started_at": (datetime.utcnow() - timedelta(minutes=2)).isoformat(),
            "failed_at": datetime.utcnow().isoformat(),
            "progress": "25",
            "stage": "r_script_execution",
            "error": error_message,
            "traceback": "Traceback (most recent call last)..."
        })
        
        mock_result = MockCeleryResult(job_id, "FAILURE", traceback="Traceback...")
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.AsyncResult', return_value=mock_result):
            
            response = await async_client.get(f"/calibrate/async/{job_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["job_id"] == job_id
            assert data["status"] == "failed"
            assert data["error"] == error_message
            assert "failed_at" in data
            assert "traceback" in data
    
    @pytest.mark.asyncio
    async def test_get_job_status_not_found(
        self,
        async_client: AsyncClient,
        mock_redis_client
    ):
        """
        Test ID: UT-ASYNC-001-06
        Getting status of non-existent job should return 404.
        """
        job_id = "non-existent-job"
        
        with patch('app.async_calibration.redis_client', mock_redis_client):
            response = await async_client.get(f"/calibrate/async/{job_id}/status")
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_cancel_job_success(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app
    ):
        """
        Test ID: UT-ASYNC-001-07
        Canceling a running job should revoke task and update status.
        """
        job_id = "test-job-to-cancel"
        
        # Setup running job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "created_at": datetime.utcnow().isoformat(),
            "started_at": datetime.utcnow().isoformat(),
            "progress": "30",
            "stage": "r_script_execution"
        })
        
        mock_result = MockCeleryResult(job_id, "PROGRESS")
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.AsyncResult', return_value=mock_result) as mock_async_result:
            
            response = await async_client.post(f"/calibrate/async/{job_id}/cancel")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["job_id"] == job_id
            assert data["status"] == "cancelled"
            assert "cancelled_at" in data
            
            # Verify task was revoked
            mock_result.revoke.assert_called_once_with(terminate=True)
            
            # Verify status updated in Redis
            job_data = await mock_redis_client.hgetall(f"job:{job_id}")
            assert job_data["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_cancel_completed_job(
        self,
        async_client: AsyncClient,
        mock_redis_client
    ):
        """
        Test ID: UT-ASYNC-001-08
        Attempting to cancel completed job should return error.
        """
        job_id = "test-job-completed"
        
        # Setup completed job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "progress": "100"
        })
        
        with patch('app.async_calibration.redis_client', mock_redis_client):
            response = await async_client.post(f"/calibrate/async/{job_id}/cancel")
            
            assert response.status_code == 400
            data = response.json()
            assert "cannot be cancelled" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_list_user_jobs(
        self,
        async_client: AsyncClient,
        mock_redis_client
    ):
        """
        Test ID: UT-ASYNC-001-09
        Listing user jobs should return paginated results.
        """
        user_id = "test-user-123"
        
        # Setup multiple jobs for user
        for i in range(5):
            job_id = f"job-{i}"
            await mock_redis_client.hset(f"job:{job_id}", {
                "user_id": user_id,
                "status": "completed" if i < 3 else "running",
                "created_at": (datetime.utcnow() - timedelta(hours=i)).isoformat(),
                "age_group": "neonate",
                "country": "Mozambique"
            })
            
            # Add to user's job list
            await mock_redis_client.hset(f"user:{user_id}:jobs", {job_id: "1"})
        
        with patch('app.async_calibration.redis_client', mock_redis_client):
            response = await async_client.get(
                f"/calibrate/async/jobs?user_id={user_id}&limit=3"
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "jobs" in data
            assert "total" in data
            assert "page" in data
            assert "limit" in data
            
            assert len(data["jobs"]) <= 3
            assert data["total"] == 5
    
    @pytest.mark.asyncio
    async def test_job_progress_updates(
        self,
        async_client: AsyncClient,
        mock_redis_client
    ):
        """
        Test ID: UT-ASYNC-001-10
        Job progress should be updated during execution.
        """
        job_id = "test-job-progress"
        
        # Setup job with initial progress
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "progress": "0",
            "stage": "initializing"
        })
        
        # Simulate progress updates
        progress_stages = [
            (10, "validating_input"),
            (25, "processing_va_data"),
            (50, "running_calibration"),
            (75, "generating_results"),
            (100, "completed")
        ]
        
        with patch('app.async_calibration.redis_client', mock_redis_client):
            for progress, stage in progress_stages:
                # Update progress
                await mock_redis_client.hset(f"job:{job_id}", {
                    "progress": str(progress),
                    "stage": stage,
                    "status": "completed" if progress == 100 else "running"
                })
                
                response = await async_client.get(f"/calibrate/async/{job_id}/status")
                assert response.status_code == 200
                
                data = response.json()
                assert data["progress"] == progress
                assert data["stage"] == stage


class TestAsyncCalibrationErrorHandling:
    """Test error handling in async calibration."""
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(
        self,
        async_client: AsyncClient,
        sample_calibration_request
    ):
        """
        Test ID: UT-ASYNC-001-11
        Redis connection error should be handled gracefully.
        """
        mock_redis_error = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        with patch('app.async_calibration.redis_client.hset', mock_redis_error):
            response = await async_client.post("/calibrate/async", json=sample_calibration_request)
            
            assert response.status_code == 503  # Service Unavailable
            data = response.json()
            assert "redis" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_celery_broker_error(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: UT-ASYNC-001-12
        Celery broker error should be handled gracefully.
        """
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.calibration_task.delay', side_effect=Exception("Broker unreachable")):
            
            response = await async_client.post("/calibrate/async", json=sample_calibration_request)
            
            assert response.status_code == 503  # Service Unavailable
            data = response.json()
            assert "broker" in data["detail"].lower() or "celery" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_invalid_job_data(
        self,
        async_client: AsyncClient,
        mock_redis_client
    ):
        """
        Test ID: UT-ASYNC-001-13
        Corrupted job data in Redis should be handled.
        """
        job_id = "corrupted-job"
        
        # Setup corrupted job data
        await mock_redis_client.set(f"job:{job_id}", "invalid-json-data")
        
        with patch('app.async_calibration.redis_client', mock_redis_client):
            response = await async_client.get(f"/calibrate/async/{job_id}/status")
            
            assert response.status_code == 500
            data = response.json()
            assert "corrupted" in data["detail"].lower() or "invalid" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_job_timeout_handling(
        self,
        async_client: AsyncClient,
        mock_redis_client
    ):
        """
        Test ID: UT-ASYNC-001-14
        Jobs running longer than timeout should be marked as failed.
        """
        job_id = "timeout-job"
        
        # Setup job that started 2 hours ago (past timeout)
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "started_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "progress": "30",
            "stage": "r_script_execution"
        })
        
        mock_result = MockCeleryResult(job_id, "PENDING")  # Still shows as pending
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.AsyncResult', return_value=mock_result), \
             patch('app.async_calibration.JOB_TIMEOUT_SECONDS', 3600):  # 1 hour timeout
            
            response = await async_client.get(f"/calibrate/async/{job_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "failed"
            assert "timeout" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_job_limit(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: UT-ASYNC-001-15
        Creating jobs beyond concurrent limit should be rejected.
        """
        user_id = "test-user-limit"
        
        # Setup multiple running jobs for user (at limit)
        for i in range(3):  # Assume limit is 3
            job_id = f"running-job-{i}"
            await mock_redis_client.hset(f"job:{job_id}", {
                "user_id": user_id,
                "status": "running",
                "created_at": datetime.utcnow().isoformat()
            })
            await mock_redis_client.hset(f"user:{user_id}:running_jobs", {job_id: "1"})
        
        request_data = {**sample_calibration_request, "user_id": user_id}
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.MAX_CONCURRENT_JOBS_PER_USER', 3):
            
            response = await async_client.post("/calibrate/async", json=request_data)
            
            assert response.status_code == 429  # Too Many Requests
            data = response.json()
            assert "limit" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_malformed_request_data(
        self,
        async_client: AsyncClient
    ):
        """
        Test ID: UT-ASYNC-001-16
        Malformed request data should return validation error.
        """
        invalid_requests = [
            {},  # Empty request
            {"age_group": "invalid"},  # Invalid age group
            {"va_data": "not_a_dict"},  # Invalid va_data type
            {"country": None},  # None values
        ]
        
        for invalid_request in invalid_requests:
            response = await async_client.post("/calibrate/async", json=invalid_request)
            
            assert response.status_code in [400, 422]  # Bad Request or Validation Error


class TestAsyncCalibrationPerformance:
    """Test performance aspects of async calibration."""
    
    @pytest.mark.asyncio
    async def test_high_throughput_job_creation(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app,
        sample_calibration_request
    ):
        """
        Test ID: UT-ASYNC-001-17
        System should handle multiple concurrent job creation requests.
        """
        num_jobs = 10
        
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.calibration_task.delay', 
                   return_value=MockCeleryResult("test-job", "PENDING")):
            
            # Create multiple jobs concurrently
            tasks = []
            for i in range(num_jobs):
                request_data = {**sample_calibration_request, "user_id": f"user-{i}"}
                task = async_client.post("/calibrate/async", json=request_data)
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Most requests should succeed
            successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 202]
            assert len(successful_responses) >= num_jobs * 0.8  # At least 80% success rate
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(
        self,
        async_client: AsyncClient,
        mock_redis_client,
        mock_celery_app,
        performance_test_data
    ):
        """
        Test ID: UT-ASYNC-001-18
        Large datasets should not cause excessive memory usage.
        """
        with patch('app.async_calibration.redis_client', mock_redis_client), \
             patch('app.async_calibration.calibration_task.delay', 
                   return_value=MockCeleryResult("large-job", "PENDING")):
            
            response = await async_client.post("/calibrate/async", json=performance_test_data)
            
            assert response.status_code == 202
            
            # Verify job data was compressed/optimized in Redis
            job_id = response.json()["job_id"]
            job_data = await mock_redis_client.hgetall(f"job:{job_id}")
            
            # Job metadata should be stored, but large dataset should be referenced
            assert "input_size" in job_data  # Should track input size
            assert len(str(job_data)) < 10000  # Metadata should be small
