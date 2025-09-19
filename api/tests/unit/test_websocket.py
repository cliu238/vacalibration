"""
Unit tests for WebSocket functionality.
Test ID: UT-WS-001

Tests WebSocket connection lifecycle, message streaming,
multiple client connections, and error scenarios.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect
import websockets

# Import the app (assuming WebSocket endpoints will be added)
from app.main_direct import app


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.messages_received = []
        self.closed = False
        self.close_code = None
        self.accept_called = False
    
    async def accept(self):
        self.accept_called = True
    
    async def send_text(self, data: str):
        if self.closed:
            raise WebSocketDisconnect(code=1000)
        self.messages_sent.append(data)
    
    async def send_json(self, data: Dict[str, Any]):
        if self.closed:
            raise WebSocketDisconnect(code=1000)
        self.messages_sent.append(json.dumps(data))
    
    async def receive_text(self) -> str:
        if self.closed:
            raise WebSocketDisconnect(code=1000)
        if self.messages_received:
            return self.messages_received.pop(0)
        # Simulate waiting for message
        await asyncio.sleep(0.1)
        raise WebSocketDisconnect(code=1000, reason="No more messages")
    
    async def receive_json(self) -> Dict[str, Any]:
        text = await self.receive_text()
        return json.loads(text)
    
    async def close(self, code: int = 1000):
        self.closed = True
        self.close_code = code
    
    def add_message(self, message: str):
        """Add a message to be received."""
        self.messages_received.append(message)


class MockRedisSubscriber:
    """Mock Redis pub/sub subscriber."""
    
    def __init__(self):
        self.channels = []
        self.messages = []
        self.subscribed = False
    
    async def subscribe(self, *channels):
        self.channels.extend(channels)
        self.subscribed = True
    
    async def unsubscribe(self, *channels):
        for channel in channels:
            if channel in self.channels:
                self.channels.remove(channel)
    
    async def get_message(self, timeout=None, ignore_subscribe_messages=False):
        if self.messages:
            return self.messages.pop(0)
        if timeout:
            await asyncio.sleep(min(timeout, 0.1))
        return None
    
    def add_message(self, channel: str, data: str, message_type: str = "message"):
        """Add a message to be received."""
        self.messages.append({
            'type': message_type,
            'channel': channel.encode() if isinstance(channel, str) else channel,
            'data': data.encode() if isinstance(data, str) else data
        })


class TestWebSocketConnection:
    """Test WebSocket connection lifecycle."""
    
    @pytest.mark.asyncio
    async def test_websocket_connect_success(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-01
        WebSocket connection should be accepted and authenticated.
        """
        websocket = MockWebSocket()
        job_id = "test-job-123"
        
        # Setup job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user",
            "created_at": datetime.utcnow().isoformat()
        })
        
        with patch('app.websocket.redis_client', mock_redis_client):
            from app.websocket import handle_job_logs_connection
            
            # Simulate connection
            await handle_job_logs_connection(websocket, job_id)
            
            assert websocket.accept_called
            assert not websocket.closed
    
    @pytest.mark.asyncio
    async def test_websocket_connect_invalid_job(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-02
        WebSocket connection with invalid job ID should be rejected.
        """
        websocket = MockWebSocket()
        job_id = "non-existent-job"
        
        with patch('app.websocket.redis_client', mock_redis_client):
            from app.websocket import handle_job_logs_connection
            
            try:
                await handle_job_logs_connection(websocket, job_id)
                assert False, "Should have raised an exception"
            except WebSocketDisconnect:
                assert websocket.close_code == 4004  # Not Found
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_cleanup(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-03
        WebSocket disconnect should clean up resources.
        """
        websocket = MockWebSocket()
        job_id = "test-job-disconnect"
        
        # Setup job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber):
            
            from app.websocket import handle_job_logs_connection
            
            # Start connection and then disconnect
            websocket.closed = True
            
            try:
                await handle_job_logs_connection(websocket, job_id)
            except WebSocketDisconnect:
                pass
            
            # Verify cleanup - subscriber should be unsubscribed
            assert len(mock_subscriber.channels) == 0


class TestWebSocketMessageStreaming:
    """Test WebSocket message streaming functionality."""
    
    @pytest.mark.asyncio
    async def test_stream_job_logs(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-04
        Job logs should be streamed to WebSocket clients.
        """
        websocket = MockWebSocket()
        job_id = "test-job-streaming"
        
        # Setup job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        # Add some log messages
        log_messages = [
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Job started"},
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": "Processing data"},
            {"timestamp": datetime.utcnow().isoformat(), "level": "DEBUG", "message": "Running R script"}
        ]
        
        for log_msg in log_messages:
            mock_subscriber.add_message(
                f"job:{job_id}:logs",
                json.dumps(log_msg)
            )
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber):
            
            from app.websocket import stream_job_logs
            
            # Stream messages
            await stream_job_logs(websocket, job_id, max_messages=3)
            
            # Verify messages were sent
            assert len(websocket.messages_sent) == 3
            
            # Check message content
            for i, sent_message in enumerate(websocket.messages_sent):
                sent_data = json.loads(sent_message)
                assert sent_data["type"] == "log"
                assert "timestamp" in sent_data
                assert "level" in sent_data
                assert "message" in sent_data
    
    @pytest.mark.asyncio
    async def test_stream_job_progress(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-05
        Job progress updates should be streamed to WebSocket clients.
        """
        websocket = MockWebSocket()
        job_id = "test-job-progress"
        
        # Setup job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user",
            "progress": "25",
            "stage": "processing_data"
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        # Add progress update messages
        progress_updates = [
            {"progress": 30, "stage": "running_calibration", "eta": "2 minutes"},
            {"progress": 60, "stage": "generating_results", "eta": "1 minute"},
            {"progress": 100, "stage": "completed", "eta": "0 seconds"}
        ]
        
        for update in progress_updates:
            mock_subscriber.add_message(
                f"job:{job_id}:progress",
                json.dumps(update)
            )
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber):
            
            from app.websocket import stream_job_progress
            
            # Stream progress updates
            await stream_job_progress(websocket, job_id, max_updates=3)
            
            # Verify progress updates were sent
            assert len(websocket.messages_sent) == 3
            
            # Check progress update content
            for i, sent_message in enumerate(websocket.messages_sent):
                sent_data = json.loads(sent_message)
                assert sent_data["type"] == "progress"
                assert "progress" in sent_data
                assert "stage" in sent_data
                assert "eta" in sent_data
    
    @pytest.mark.asyncio
    async def test_stream_job_completion(
        self,
        mock_redis_client,
        mock_r_success_output
    ):
        """
        Test ID: UT-WS-001-06
        Job completion should send final results via WebSocket.
        """
        websocket = MockWebSocket()
        job_id = "test-job-completion"
        
        # Setup completed job in Redis
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "completed",
            "user_id": "test-user",
            "progress": "100",
            "result": json.dumps(mock_r_success_output)
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        # Add completion message
        completion_message = {
            "status": "completed",
            "results": mock_r_success_output,
            "duration": 180,  # 3 minutes
            "completed_at": datetime.utcnow().isoformat()
        }
        
        mock_subscriber.add_message(
            f"job:{job_id}:status",
            json.dumps(completion_message)
        )
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber):
            
            from app.websocket import stream_job_status
            
            # Stream status updates
            await stream_job_status(websocket, job_id, max_updates=1)
            
            # Verify completion message was sent
            assert len(websocket.messages_sent) == 1
            
            sent_data = json.loads(websocket.messages_sent[0])
            assert sent_data["type"] == "status"
            assert sent_data["status"] == "completed"
            assert "results" in sent_data
            assert "duration" in sent_data
    
    @pytest.mark.asyncio
    async def test_stream_real_time_logs(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-07
        Real-time logs should be streamed as they are generated.
        """
        websocket = MockWebSocket()
        job_id = "test-job-realtime"
        
        # Setup running job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber):
            
            from app.websocket import handle_job_logs_connection
            
            # Start streaming in background
            stream_task = asyncio.create_task(
                handle_job_logs_connection(websocket, job_id)
            )
            
            # Simulate real-time log generation
            await asyncio.sleep(0.1)  # Let connection establish
            
            # Add log messages dynamically
            log_entries = [
                "Starting calibration process",
                "Loading VA data",
                "Running R script",
                "Calibration completed"
            ]
            
            for log_entry in log_entries:
                log_message = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": log_entry
                }
                mock_subscriber.add_message(
                    f"job:{job_id}:logs",
                    json.dumps(log_message)
                )
                await asyncio.sleep(0.05)  # Small delay between messages
            
            # Wait for messages to be processed
            await asyncio.sleep(0.2)
            
            # Stop streaming
            stream_task.cancel()
            
            try:
                await stream_task
            except asyncio.CancelledError:
                pass
            
            # Verify logs were streamed
            assert len(websocket.messages_sent) >= len(log_entries)


class TestWebSocketMultipleClients:
    """Test WebSocket with multiple concurrent clients."""
    
    @pytest.mark.asyncio
    async def test_multiple_clients_same_job(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-08
        Multiple clients should be able to watch the same job.
        """
        job_id = "test-job-multi-client"
        num_clients = 3
        
        # Setup job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        # Create multiple WebSocket connections
        websockets_list = [MockWebSocket() for _ in range(num_clients)]
        subscribers = [MockRedisSubscriber() for _ in range(num_clients)]
        
        # Add the same log message to all subscribers
        log_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Processing completed"
        }
        
        for subscriber in subscribers:
            subscriber.add_message(
                f"job:{job_id}:logs",
                json.dumps(log_message)
            )
        
        with patch('app.websocket.redis_client', mock_redis_client):
            # Simulate multiple clients connecting
            tasks = []
            for i, (ws, sub) in enumerate(zip(websockets_list, subscribers)):
                with patch('app.websocket.redis_client.pubsub', return_value=sub):
                    from app.websocket import stream_job_logs
                    task = asyncio.create_task(
                        stream_job_logs(ws, job_id, max_messages=1)
                    )
                    tasks.append(task)
            
            # Wait for all clients to process messages
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all clients received the message
            for ws in websockets_list:
                assert len(ws.messages_sent) == 1
                sent_data = json.loads(ws.messages_sent[0])
                assert sent_data["message"] == "Processing completed"
    
    @pytest.mark.asyncio
    async def test_client_disconnect_doesnt_affect_others(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-09
        One client disconnecting shouldn't affect other clients.
        """
        job_id = "test-job-disconnect-isolation"
        
        # Setup job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        # Create two WebSocket connections
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        
        sub1 = MockRedisSubscriber()
        sub2 = MockRedisSubscriber()
        
        # Add messages to both subscribers
        log_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Test message"
        }
        
        sub1.add_message(f"job:{job_id}:logs", json.dumps(log_message))
        sub2.add_message(f"job:{job_id}:logs", json.dumps(log_message))
        
        with patch('app.websocket.redis_client', mock_redis_client):
            from app.websocket import stream_job_logs
            
            # Start streaming for both clients
            with patch('app.websocket.redis_client.pubsub', return_value=sub1):
                task1 = asyncio.create_task(
                    stream_job_logs(ws1, job_id, max_messages=1)
                )
            
            with patch('app.websocket.redis_client.pubsub', return_value=sub2):
                task2 = asyncio.create_task(
                    stream_job_logs(ws2, job_id, max_messages=1)
                )
            
            # Disconnect first client
            ws1.closed = True
            
            # Wait for both tasks
            results = await asyncio.gather(task1, task2, return_exceptions=True)
            
            # First client should have disconnected, second should work
            assert isinstance(results[0], (WebSocketDisconnect, Exception))
            assert len(ws2.messages_sent) == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-10
        Broadcasting messages should reach all connected clients.
        """
        job_id = "test-job-broadcast"
        num_clients = 5
        
        # Setup job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        # Create multiple clients
        clients = [MockWebSocket() for _ in range(num_clients)]
        subscribers = [MockRedisSubscriber() for _ in range(num_clients)]
        
        # Broadcast message to all subscribers
        broadcast_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "Broadcast to all clients",
            "broadcast": True
        }
        
        for subscriber in subscribers:
            subscriber.add_message(
                f"job:{job_id}:logs",
                json.dumps(broadcast_message)
            )
        
        with patch('app.websocket.redis_client', mock_redis_client):
            # Start all clients
            tasks = []
            for i, (client, subscriber) in enumerate(zip(clients, subscribers)):
                with patch('app.websocket.redis_client.pubsub', return_value=subscriber):
                    from app.websocket import stream_job_logs
                    task = asyncio.create_task(
                        stream_job_logs(client, job_id, max_messages=1)
                    )
                    tasks.append(task)
            
            # Wait for all clients to receive the message
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all clients received the broadcast
            for client in clients:
                assert len(client.messages_sent) >= 1
                sent_data = json.loads(client.messages_sent[0])
                assert sent_data["broadcast"] is True
                assert "Broadcast to all clients" in sent_data["message"]


class TestWebSocketErrorScenarios:
    """Test WebSocket error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection_timeout(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-11
        WebSocket connections should timeout after inactivity.
        """
        websocket = MockWebSocket()
        job_id = "test-job-timeout"
        
        # Setup job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber), \
             patch('app.websocket.WEBSOCKET_TIMEOUT', 0.1):  # Short timeout for testing
            
            from app.websocket import handle_job_logs_connection
            
            # Connection should timeout due to no messages
            start_time = asyncio.get_event_loop().time()
            
            try:
                await handle_job_logs_connection(websocket, job_id)
            except (WebSocketDisconnect, asyncio.TimeoutError):
                pass
            
            end_time = asyncio.get_event_loop().time()
            
            # Should have timed out within reasonable time
            assert end_time - start_time < 0.5
    
    @pytest.mark.asyncio
    async def test_redis_connection_error_in_websocket(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-12
        Redis connection errors should be handled gracefully in WebSocket.
        """
        websocket = MockWebSocket()
        job_id = "test-job-redis-error"
        
        # Mock Redis error
        mock_redis_client.hgetall = AsyncMock(side_effect=Exception("Redis connection failed"))
        
        with patch('app.websocket.redis_client', mock_redis_client):
            from app.websocket import handle_job_logs_connection
            
            try:
                await handle_job_logs_connection(websocket, job_id)
                assert False, "Should have raised an exception"
            except (WebSocketDisconnect, Exception):
                assert websocket.closed or websocket.close_code == 1011  # Internal Error
    
    @pytest.mark.asyncio
    async def test_malformed_message_handling(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-13
        Malformed messages should be handled without crashing.
        """
        websocket = MockWebSocket()
        job_id = "test-job-malformed"
        
        # Setup job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        # Add malformed messages
        mock_subscriber.add_message(f"job:{job_id}:logs", "invalid-json")
        mock_subscriber.add_message(f"job:{job_id}:logs", json.dumps({"incomplete": "data"}))
        mock_subscriber.add_message(f"job:{job_id}:logs", "")
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber):
            
            from app.websocket import stream_job_logs
            
            # Should handle malformed messages gracefully
            try:
                await stream_job_logs(websocket, job_id, max_messages=3)
            except Exception as e:
                # Should not crash on malformed messages
                assert "json" not in str(e).lower()
            
            # Should still be connected
            assert not websocket.closed
    
    @pytest.mark.asyncio
    async def test_websocket_message_size_limit(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-14
        Large messages should be handled or rejected appropriately.
        """
        websocket = MockWebSocket()
        job_id = "test-job-large-message"
        
        # Setup job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "test-user"
        })
        
        mock_subscriber = MockRedisSubscriber()
        
        # Create very large message
        large_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": "x" * (1024 * 1024),  # 1MB message
            "large_data": list(range(10000))  # Large array
        }
        
        mock_subscriber.add_message(
            f"job:{job_id}:logs",
            json.dumps(large_message)
        )
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.redis_client.pubsub', return_value=mock_subscriber), \
             patch('app.websocket.MAX_MESSAGE_SIZE', 1024):  # 1KB limit
            
            from app.websocket import stream_job_logs
            
            # Large message should be handled (truncated or rejected)
            await stream_job_logs(websocket, job_id, max_messages=1)
            
            # Should either truncate message or send error message
            if websocket.messages_sent:
                sent_data = json.loads(websocket.messages_sent[0])
                # Message should be truncated or be an error message
                assert len(json.dumps(sent_data)) <= 2048  # Reasonable size
    
    @pytest.mark.asyncio
    async def test_unauthorized_websocket_access(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-15
        Unauthorized access to job logs should be rejected.
        """
        websocket = MockWebSocket()
        job_id = "test-job-unauthorized"
        
        # Setup job for different user
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": "other-user"  # Different user
        })
        
        with patch('app.websocket.redis_client', mock_redis_client):
            from app.websocket import handle_job_logs_connection
            
            # Should reject unauthorized access
            try:
                await handle_job_logs_connection(
                    websocket, 
                    job_id, 
                    user_id="unauthorized-user"  # Wrong user
                )
                assert False, "Should have raised an exception"
            except WebSocketDisconnect:
                assert websocket.close_code == 4003  # Forbidden
    
    @pytest.mark.asyncio
    async def test_websocket_rate_limiting(
        self,
        mock_redis_client
    ):
        """
        Test ID: UT-WS-001-16
        WebSocket connections should be rate limited per user.
        """
        job_id = "test-job-rate-limit"
        user_id = "test-user-rate-limit"
        
        # Setup job
        await mock_redis_client.hset(f"job:{job_id}", {
            "status": "running",
            "user_id": user_id
        })
        
        # Try to create many connections rapidly
        max_connections = 5
        websockets_list = [MockWebSocket() for _ in range(max_connections + 2)]
        
        with patch('app.websocket.redis_client', mock_redis_client), \
             patch('app.websocket.MAX_CONNECTIONS_PER_USER', max_connections):
            
            from app.websocket import handle_job_logs_connection
            
            # Start multiple connections
            tasks = []
            for ws in websockets_list:
                task = asyncio.create_task(
                    handle_job_logs_connection(ws, job_id, user_id=user_id)
                )
                tasks.append(task)
            
            # Wait briefly
            await asyncio.sleep(0.1)
            
            # Cancel all tasks
            for task in tasks:
                task.cancel()
            
            # Some connections should be rejected due to rate limiting
            rejected_count = sum(1 for ws in websockets_list 
                               if ws.close_code == 4008)  # Policy Violation
            
            assert rejected_count >= 2  # At least 2 should be rejected
