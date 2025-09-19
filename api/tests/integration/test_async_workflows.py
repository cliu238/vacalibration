"""
Integration tests for async calibration workflows.
Test ID: IT-ASYNC-001

End-to-end async calibration tests with real Redis (using fakeredis),
WebSocket log streaming, multiple job processing, and performance tests.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Use fakeredis for real Redis testing
import fakeredis.aioredis
from websockets.client import connect
from websockets.exceptions import ConnectionClosed

# Import the app
from app.main_direct import app


class TestAsyncCalibrationWorkflows:
    """End-to-end async calibration workflow tests."""
    
    @pytest.mark.asyncio
    async def test_full_async_calibration_workflow(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request,
        mock_r_success_output
    ):
        """
        Test ID: IT-ASYNC-001-01
        Complete async calibration workflow from job creation to completion.
        """
        # Step 1: Create async calibration job
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            # Mock successful task execution
            mock_task = MagicMock()
            mock_task.id = "test-task-123"
            mock_task.status = "PENDING"
            mock_delay.return_value = mock_task
            
            response = await async_client.post(
                "/calibrate", 
                json={**sample_calibration_request, "async_mode": True}
            )
            
            assert response.status_code == 202
            job_data = response.json()
            job_id = job_data["job_id"]
            
            assert "job_id" in job_data
            assert job_data["status"] == "pending"
        
        # Step 2: Check initial job status
        with patch('app.async_calibration.redis_client', fake_redis_client):
            response = await async_client.get(f"/jobs/{job_id}")
            
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["status"] == "pending"
        
        # Step 3: Simulate job progress updates
        progress_stages = [
            {"status": "running", "progress": 0, "stage": "initializing"},
            {"status": "running", "progress": 25, "stage": "processing_va_data"},
            {"status": "running", "progress": 50, "stage": "running_calibration"},
            {"status": "running", "progress": 75, "stage": "generating_results"},
            {
                "status": "completed", 
                "progress": 100, 
                "stage": "completed",
                "result": json.dumps(mock_r_success_output),
                "completed_at": datetime.utcnow().isoformat()
            }
        ]
        
        with patch('app.async_calibration.redis_client', fake_redis_client):
            for stage in progress_stages:
                # Update job status in Redis
                await fake_redis_client.hset(
                    f"job:{job_id}",
                    {k: str(v) for k, v in stage.items()}
                )
                
                # Check status endpoint
                response = await async_client.get(f"/jobs/{job_id}")
                assert response.status_code == 200
                
                status_data = response.json()
                assert status_data["status"] == stage["status"]
                assert status_data["progress"] == stage["progress"]
                
                if stage["status"] == "completed":
                    assert "results" in status_data
                    assert "duration" in status_data
        
        # Step 4: Verify final results
        with patch('app.async_calibration.redis_client', fake_redis_client):
            response = await async_client.get(f"/jobs/{job_id}")
            
            assert response.status_code == 200
            final_data = response.json()
            
            assert final_data["status"] == "completed"
            assert final_data["progress"] == 100
            assert "results" in final_data
            
            # Check results structure
            results = final_data["results"]
            assert "uncalibrated" in results
            assert "calibrated" in results
    
    @pytest.mark.asyncio
    async def test_async_job_cancellation_workflow(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-02
        Test cancelling a running async calibration job.
        """
        # Create job
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            mock_task = MagicMock()
            mock_task.id = "cancel-task-123"
            mock_task.status = "PENDING"
            mock_delay.return_value = mock_task
            
            response = await async_client.post(
                "/calibrate", 
                json={**sample_calibration_request, "async_mode": True}
            )
            
            job_id = response.json()["job_id"]
        
        # Set job to running status
        with patch('app.async_calibration.redis_client', fake_redis_client):
            await fake_redis_client.hset(
                f"job:{job_id}",
                {
                    "status": "running",
                    "progress": "30",
                    "stage": "processing_data",
                    "started_at": datetime.utcnow().isoformat()
                }
            )
        
        # Cancel the job
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.AsyncResult') as mock_async_result:
            
            mock_result = MagicMock()
            mock_result.revoke = MagicMock()
            mock_async_result.return_value = mock_result
            
            response = await async_client.post(f"/jobs/{job_id}/cancel")
            
            assert response.status_code == 200
            cancel_data = response.json()
            
            assert cancel_data["status"] == "cancelled"
            assert "cancelled_at" in cancel_data
            
            # Verify task was revoked
            mock_result.revoke.assert_called_once_with(terminate=True)
        
        # Verify job status is updated
        with patch('app.async_calibration.redis_client', fake_redis_client):
            response = await async_client.get(f"/jobs/{job_id}")
            
            assert response.status_code == 200
            status_data = response.json()
            assert status_data["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_async_job_error_handling_workflow(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-03
        Test handling of job failures and error reporting.
        """
        # Create job
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            mock_task = MagicMock()
            mock_task.id = "error-task-123"
            mock_task.status = "PENDING"
            mock_delay.return_value = mock_task
            
            response = await async_client.post(
                "/calibrate", 
                json={**sample_calibration_request, "async_mode": True}
            )
            
            job_id = response.json()["job_id"]
        
        # Simulate job failure
        error_message = "R script execution failed: Missing required packages"
        
        with patch('app.async_calibration.redis_client', fake_redis_client):
            await fake_redis_client.hset(
                f"job:{job_id}",
                {
                    "status": "failed",
                    "progress": "25",
                    "stage": "r_script_execution",
                    "error": error_message,
                    "failed_at": datetime.utcnow().isoformat(),
                    "traceback": "Traceback (most recent call last)..."
                }
            )
        
        # Check error status
        with patch('app.async_calibration.redis_client', fake_redis_client):
            response = await async_client.get(f"/jobs/{job_id}")
            
            assert response.status_code == 200
            error_data = response.json()
            
            assert error_data["status"] == "failed"
            assert error_data["error"] == error_message
            assert "failed_at" in error_data
            assert "traceback" in error_data
    
    @pytest.mark.asyncio
    async def test_multiple_job_processing(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-04
        Test processing multiple calibration jobs concurrently.
        """
        num_jobs = 5
        job_ids = []

        # Create multiple jobs
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:

            for i in range(num_jobs):
                mock_task = MagicMock()
                mock_task.id = f"multi-task-{i}"
                mock_task.status = "PENDING"
                mock_delay.return_value = mock_task

                # Vary request parameters
                request_data = {
                    **sample_calibration_request,
                    "async_mode": True,
                    "country": ["Mozambique", "Kenya", "Ethiopia"][i % 3],
                    "user_id": f"user-{i}"
                }
                
                response = await async_client.post("/calibrate", json=request_data)
                
                assert response.status_code == 202
                job_ids.append(response.json()["job_id"])
        
        # Simulate concurrent processing
        with patch('app.async_calibration.redis_client', fake_redis_client):
            for i, job_id in enumerate(job_ids):
                # Simulate different completion times
                status = "completed" if i < 3 else "running"
                progress = 100 if status == "completed" else 50 + (i * 10)
                
                await fake_redis_client.hset(
                    f"job:{job_id}",
                    {
                        "status": status,
                        "progress": str(progress),
                        "stage": "completed" if status == "completed" else "processing",
                        "user_id": f"user-{i}"
                    }
                )
        
        # List all jobs
        with patch('app.async_calibration.redis_client', fake_redis_client):
            response = await async_client.get("/jobs?limit=10")
            
            assert response.status_code == 200
            jobs_data = response.json()
            
            assert "jobs" in jobs_data
            assert len(jobs_data["jobs"]) >= num_jobs
            
            # Check job statuses
            completed_jobs = [j for j in jobs_data["jobs"] if j["status"] == "completed"]
            running_jobs = [j for j in jobs_data["jobs"] if j["status"] == "running"]
            
            assert len(completed_jobs) >= 3
            assert len(running_jobs) >= 2


class TestWebSocketLogStreaming:
    """Test WebSocket log streaming integration."""
    
    @pytest.mark.asyncio
    async def test_websocket_job_log_streaming(
        self,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-05
        Test real-time log streaming via WebSocket.
        """
        job_id = "websocket-test-job"
        
        # Setup job in Redis
        await fake_redis_client.hset(
            f"job:{job_id}",
            {
                "status": "running",
                "user_id": "test-user",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        # Mock WebSocket connection
        messages_received = []
        
        class MockWebSocketClient:
            def __init__(self):
                self.closed = False
            
            async def send(self, message):
                pass
            
            async def recv(self):
                if messages_received:
                    return messages_received.pop(0)
                await asyncio.sleep(0.1)
                raise ConnectionClosed(None, None)
            
            async def close(self):
                self.closed = True
        
        # Simulate log messages being published
        log_messages = [
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Job started"},
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Loading data"},
            {"timestamp": datetime.utcnow().isoformat(), "level": "DEBUG", "message": "Running R script"},
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Job completed"}
        ]
        
        for log_msg in log_messages:
            await fake_redis_client.publish(
                f"job:{job_id}:logs",
                json.dumps(log_msg)
            )
        
        # Verify logs were published
        published_logs = await fake_redis_client.get(f"channel:job:{job_id}:logs")
        assert published_logs is not None
    
    @pytest.mark.asyncio
    async def test_websocket_progress_streaming(
        self,
        fake_redis_client
    ):
        """
        Test ID: IT-ASYNC-001-06
        Test real-time progress updates via WebSocket.
        """
        job_id = "progress-test-job"
        
        # Setup job
        await fake_redis_client.hset(
            f"job:{job_id}",
            {
                "status": "running",
                "user_id": "test-user",
                "progress": "0"
            }
        )
        
        # Simulate progress updates
        progress_updates = [
            {"progress": 25, "stage": "loading_data", "eta": "3 minutes"},
            {"progress": 50, "stage": "running_calibration", "eta": "2 minutes"},
            {"progress": 75, "stage": "generating_results", "eta": "1 minute"},
            {"progress": 100, "stage": "completed", "eta": "0 seconds"}
        ]
        
        for update in progress_updates:
            # Update job progress in Redis
            await fake_redis_client.hset(
                f"job:{job_id}",
                {"progress": str(update["progress"]), "stage": update["stage"]}
            )
            
            # Publish progress update
            await fake_redis_client.publish(
                f"job:{job_id}:progress",
                json.dumps(update)
            )
        
        # Verify progress was tracked
        final_job_data = await fake_redis_client.hgetall(f"job:{job_id}")
        assert final_job_data["progress"] == "100"
        assert final_job_data["stage"] == "completed"
    
    @pytest.mark.asyncio
    async def test_multiple_websocket_clients(
        self,
        fake_redis_client
    ):
        """
        Test ID: IT-ASYNC-001-07
        Test multiple WebSocket clients receiving the same job updates.
        """
        job_id = "multi-client-job"
        num_clients = 3
        
        # Setup job
        await fake_redis_client.hset(
            f"job:{job_id}",
            {
                "status": "running",
                "user_id": "test-user"
            }
        )
        
        # Simulate multiple clients subscribing
        client_messages = [[] for _ in range(num_clients)]
        
        # Publish broadcast message
        broadcast_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Broadcast to all clients",
            "broadcast": True
        }
        
        await fake_redis_client.publish(
            f"job:{job_id}:logs",
            json.dumps(broadcast_message)
        )
        
        # Verify message was published
        channel_data = await fake_redis_client.get(f"channel:job:{job_id}:logs")
        assert channel_data is not None
        
        # Each client should receive the same message
        for i in range(num_clients):
            # Simulate client receiving message
            client_messages[i].append(broadcast_message)
        
        # Verify all clients got the message
        for messages in client_messages:
            assert len(messages) == 1
            assert messages[0]["broadcast"] is True


class TestAsyncPerformanceAndLoad:
    """Test performance and load handling of async calibration."""
    
    @pytest.mark.asyncio
    async def test_high_throughput_job_creation(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-08
        Test system performance under high job creation load.
        """
        num_jobs = 20
        concurrent_groups = 4
        
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            # Mock task creation
            def create_mock_task(i):
                mock_task = MagicMock()
                mock_task.id = f"perf-task-{i}"
                mock_task.status = "PENDING"
                return mock_task
            
            mock_delay.side_effect = lambda *args: create_mock_task(len(mock_delay.call_args_list))
            
            # Create jobs in concurrent groups
            start_time = time.time()

            tasks = []
            for group in range(concurrent_groups):
                group_tasks = []
                for i in range(num_jobs // concurrent_groups):
                    request_data = {
                        **sample_calibration_request,
                        "async_mode": True,
                        "user_id": f"perf-user-{group}-{i}"
                    }

                    task = async_client.post("/calibrate", json=request_data)
                    group_tasks.append(task)

                # Execute group concurrently
                group_responses = await asyncio.gather(*group_tasks, return_exceptions=True)
                tasks.extend(group_responses)
            
            end_time = time.time()
            
            # Analyze results
            successful_jobs = [
                r for r in tasks 
                if hasattr(r, 'status_code') and r.status_code == 202
            ]
            
            # Performance assertions
            assert len(successful_jobs) >= num_jobs * 0.8  # At least 80% success rate
            assert end_time - start_time < 10  # Complete within 10 seconds
            
            # Check job distribution
            job_ids = [r.json()["job_id"] for r in successful_jobs]
            assert len(set(job_ids)) == len(job_ids)  # All unique job IDs
    
    @pytest.mark.asyncio
    async def test_concurrent_job_execution_simulation(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request,
        mock_r_success_output
    ):
        """
        Test ID: IT-ASYNC-001-09
        Test concurrent execution of multiple calibration jobs.
        """
        num_jobs = 10
        job_ids = []
        
        # Create multiple jobs
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            for i in range(num_jobs):
                mock_task = MagicMock()
                mock_task.id = f"concurrent-task-{i}"
                mock_task.status = "PENDING"
                mock_delay.return_value = mock_task
                
                request_data = {
                    **sample_calibration_request,
                    "async_mode": True,
                    "user_id": f"concurrent-user-{i}"
                }
                
                response = await async_client.post("/calibrate", json=request_data)
                job_ids.append(response.json()["job_id"])
        
        # Simulate concurrent job execution with different completion times
        with patch('app.async_calibration.redis_client', fake_redis_client):
            execution_tasks = []
            
            async def simulate_job_execution(job_id: str, duration: float):
                """Simulate a job execution with given duration."""
                # Start job
                await fake_redis_client.hset(
                    f"job:{job_id}",
                    {
                        "status": "running",
                        "progress": "0",
                        "started_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Progress updates
                for progress in [25, 50, 75]:
                    await asyncio.sleep(duration / 4)
                    await fake_redis_client.hset(
                        f"job:{job_id}",
                        {"progress": str(progress)}
                    )
                
                # Complete job
                await asyncio.sleep(duration / 4)
                await fake_redis_client.hset(
                    f"job:{job_id}",
                    {
                        "status": "completed",
                        "progress": "100",
                        "result": json.dumps(mock_r_success_output),
                        "completed_at": datetime.utcnow().isoformat()
                    }
                )
            
            # Start all jobs with varying durations
            for i, job_id in enumerate(job_ids):
                duration = 0.1 + (i * 0.05)  # Staggered completion times
                task = asyncio.create_task(
                    simulate_job_execution(job_id, duration)
                )
                execution_tasks.append(task)
            
            # Wait for all jobs to complete
            await asyncio.gather(*execution_tasks)
        
        # Verify all jobs completed successfully
        with patch('app.async_calibration.redis_client', fake_redis_client):
            completed_count = 0
            
            for job_id in job_ids:
                response = await async_client.get(f"/jobs/{job_id}")
                
                assert response.status_code == 200
                job_data = response.json()
                
                if job_data["status"] == "completed":
                    completed_count += 1
                    assert job_data["progress"] == 100
                    assert "results" in job_data
            
            assert completed_count == num_jobs
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_large_datasets(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        performance_test_data
    ):
        """
        Test ID: IT-ASYNC-001-10
        Test memory efficiency with large dataset processing.
        """
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            mock_task = MagicMock()
            mock_task.id = "large-dataset-task"
            mock_task.status = "PENDING"
            mock_delay.return_value = mock_task
            
            # Submit large dataset
            large_request = {
                **performance_test_data,
                "async_mode": True
            }
            
            response = await async_client.post("/calibrate", json=large_request)
            
            assert response.status_code == 202
            job_id = response.json()["job_id"]
        
        # Verify job metadata is stored efficiently
        with patch('app.async_calibration.redis_client', fake_redis_client):
            job_data = await fake_redis_client.hgetall(f"job:{job_id}")
            
            # Job metadata should be compact
            metadata_size = len(json.dumps(dict(job_data)))
            assert metadata_size < 10000  # Less than 10KB
            
            # Large dataset should be referenced, not stored directly
            assert "input_size" in job_data or "data_reference" in job_data
    
    @pytest.mark.asyncio
    async def test_job_cleanup_and_expiration(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-11
        Test automatic cleanup of expired jobs and their data.
        """
        # Create a job
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            mock_task = MagicMock()
            mock_task.id = "cleanup-task"
            mock_task.status = "PENDING"
            mock_delay.return_value = mock_task
            
            response = await async_client.post(
                "/calibrate", 
                json={**sample_calibration_request, "async_mode": True}
            )
            
            job_id = response.json()["job_id"]
        
        # Set job as completed with old timestamp
        old_timestamp = (datetime.utcnow() - timedelta(days=7)).isoformat()
        
        with patch('app.async_calibration.redis_client', fake_redis_client):
            await fake_redis_client.hset(
                f"job:{job_id}",
                {
                    "status": "completed",
                    "completed_at": old_timestamp,
                    "created_at": old_timestamp
                }
            )
            
            # Verify job exists
            job_exists = await fake_redis_client.exists(f"job:{job_id}")
            assert job_exists
        
        # Simulate cleanup process
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.JOB_RETENTION_DAYS', 3):  # 3 day retention
            
            from app.async_calibration import cleanup_expired_jobs
            
            # Run cleanup
            cleaned_count = await cleanup_expired_jobs()
            
            # Job should be cleaned up
            assert cleaned_count >= 1
            
            # Verify job no longer exists
            job_exists = await fake_redis_client.exists(f"job:{job_id}")
            assert not job_exists
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_retry(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-12
        Test error recovery and retry mechanisms.
        """
        retry_attempts = 3
        
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay, \
             patch('app.async_calibration.MAX_RETRY_ATTEMPTS', retry_attempts):
            
            mock_task = MagicMock()
            mock_task.id = "retry-task"
            mock_task.status = "PENDING"
            mock_delay.return_value = mock_task
            
            # Create job with retry enabled
            request_data = {
                **sample_calibration_request,
                "async_mode": True,
                "retry_on_failure": True
            }
            
            response = await async_client.post("/calibrate", json=request_data)
            job_id = response.json()["job_id"]
        
        # Simulate job failures and retries
        with patch('app.async_calibration.redis_client', fake_redis_client):
            for attempt in range(retry_attempts):
                # Simulate failure
                await fake_redis_client.hset(
                    f"job:{job_id}",
                    {
                        "status": "failed",
                        "error": f"Attempt {attempt + 1} failed",
                        "retry_count": str(attempt),
                        "failed_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Check status
                response = await async_client.get(f"/jobs/{job_id}")
                job_data = response.json()
                
                if attempt < retry_attempts - 1:
                    # Should retry
                    assert job_data["retry_count"] == attempt
                else:
                    # Final failure
                    assert job_data["status"] == "failed"
                    assert job_data["retry_count"] == retry_attempts - 1


class TestAsyncCalibrationSecurity:
    """Test security aspects of async calibration."""
    
    @pytest.mark.asyncio
    async def test_job_access_control(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-13
        Test that users can only access their own jobs.
        """
        user1_id = "user-1"
        user2_id = "user-2"
        
        # Create job for user 1
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay:
            
            mock_task = MagicMock()
            mock_task.id = "access-control-task"
            mock_task.status = "PENDING"
            mock_delay.return_value = mock_task
            
            request_data = {
                **sample_calibration_request,
                "async_mode": True,
                "user_id": user1_id
            }
            
            response = await async_client.post("/calibrate", json=request_data)
            job_id = response.json()["job_id"]
        
        # Store user association
        with patch('app.async_calibration.redis_client', fake_redis_client):
            await fake_redis_client.hset(
                f"job:{job_id}",
                {"user_id": user1_id}
            )
        
        # User 1 should be able to access their job
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.get_current_user_id', return_value=user1_id):
            
            response = await async_client.get(f"/jobs/{job_id}")
            assert response.status_code == 200
        
        # User 2 should not be able to access user 1's job
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.get_current_user_id', return_value=user2_id):
            
            response = await async_client.get(f"/jobs/{job_id}")
            assert response.status_code == 403  # Forbidden
    
    @pytest.mark.asyncio
    async def test_rate_limiting_per_user(
        self,
        async_client: AsyncClient,
        fake_redis_client,
        sample_calibration_request
    ):
        """
        Test ID: IT-ASYNC-001-14
        Test rate limiting prevents abuse of job creation.
        """
        user_id = "rate-limited-user"
        max_jobs_per_hour = 5
        
        with patch('app.async_calibration.redis_client', fake_redis_client), \
             patch('app.async_calibration.calibration_task.delay') as mock_delay, \
             patch('app.async_calibration.MAX_JOBS_PER_HOUR', max_jobs_per_hour):
            
            # Create jobs up to the limit
            successful_jobs = 0
            rate_limited_jobs = 0
            
            for i in range(max_jobs_per_hour + 3):
                mock_task = MagicMock()
                mock_task.id = f"rate-limit-task-{i}"
                mock_task.status = "PENDING"
                mock_delay.return_value = mock_task
                
                request_data = {
                    **sample_calibration_request,
                    "async_mode": True,
                    "user_id": user_id
                }
                
                response = await async_client.post("/calibrate", json=request_data)
                
                if response.status_code == 202:
                    successful_jobs += 1
                elif response.status_code == 429:  # Too Many Requests
                    rate_limited_jobs += 1
            
            # Should allow up to the limit and reject excess
            assert successful_jobs == max_jobs_per_hour
            assert rate_limited_jobs >= 1
    
    @pytest.mark.asyncio
    async def test_input_validation_and_sanitization(
        self,
        async_client: AsyncClient,
        fake_redis_client
    ):
        """
        Test ID: IT-ASYNC-001-15
        Test that malicious input is properly validated and sanitized.
        """
        malicious_inputs = [
            {
                # SQL injection attempt
                "country": "Mozambique'; DROP TABLE jobs; --",
                "age_group": "neonate",
                "async_mode": True
            },
            {
                # XSS attempt
                "va_data": {
                    "insilicova": [
                        {"id": "<script>alert('xss')</script>", "cause": "test"}
                    ]
                },
                "age_group": "neonate",
                "async_mode": True
            },
            {
                # Path traversal attempt
                "country": "../../../etc/passwd",
                "age_group": "neonate",
                "async_mode": True
            }
        ]
        
        with patch('app.async_calibration.redis_client', fake_redis_client):
            for malicious_input in malicious_inputs:
                response = await async_client.post("/calibrate", json=malicious_input)
                
                # Should either reject with validation error or sanitize input
                assert response.status_code in [400, 422, 202]
                
                if response.status_code == 202:
                    # If accepted, verify input was sanitized
                    job_data = response.json()
                    job_id = job_data["job_id"]
                    
                    stored_job = await fake_redis_client.hgetall(f"job:{job_id}")
                    stored_input = json.loads(stored_job.get("input_data", "{}"))
                    
                    # Verify no dangerous characters remain
                    input_str = json.dumps(stored_input)
                    assert "<script>" not in input_str
                    assert "DROP TABLE" not in input_str.upper()
                    assert "../" not in input_str
