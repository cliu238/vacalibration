#!/usr/bin/env python3
"""
WebSocket handler for real-time calibration logs and progress updates
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

# Try to import Redis - make it optional for testing
try:
    import redis.asyncio as redis
    from redis.asyncio.client import Redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    Redis = None
    REDIS_AVAILABLE = False
from enum import Enum

# Set up logging
logger = logging.getLogger(__name__)

# Create router for WebSocket endpoints
websocket_router = APIRouter()


class MessageType(str, Enum):
    """WebSocket message types"""
    LOG = "log"
    PROGRESS = "progress"
    STATUS = "status"
    RESULT = "result"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    CONNECTION = "connection"


class JobStatus(str, Enum):
    """Job status types"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WebSocketMessage(BaseModel):
    """WebSocket message model"""
    type: MessageType = Field(description="Message type")
    job_id: str = Field(description="Calibration job ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict = Field(default_factory=dict, description="Message payload")
    sequence: Optional[int] = Field(default=None, description="Message sequence number")


class ConnectionManager:
    """Manages WebSocket connections for calibration jobs"""

    def __init__(self, redis_client: Redis):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        self.redis_client = redis_client
        self.message_sequence: Dict[str, int] = {}
        self.heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """Accept a new WebSocket connection for a specific job"""
        await websocket.accept()

        # Initialize job connections if not exists
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
            self.message_sequence[job_id] = 0

        # Add connection
        self.active_connections[job_id].add(websocket)

        # Store metadata
        self.connection_metadata[websocket] = {
            "job_id": job_id,
            "connected_at": datetime.now(timezone.utc),
            "last_heartbeat": datetime.now(timezone.utc)
        }

        # Start heartbeat task
        self.heartbeat_tasks[websocket] = asyncio.create_task(
            self._heartbeat_loop(websocket, job_id)
        )

        # Send connection confirmation
        await self.send_message(websocket, WebSocketMessage(
            type=MessageType.CONNECTION,
            job_id=job_id,
            data={
                "status": "connected",
                "message": f"Connected to job {job_id}",
                "server_time": datetime.now(timezone.utc).isoformat()
            }
        ))

        # Send any buffered messages for late connections
        await self._send_buffered_messages(websocket, job_id)

        logger.info(f"WebSocket connected for job {job_id}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection"""
        if websocket not in self.connection_metadata:
            return

        job_id = self.connection_metadata[websocket]["job_id"]

        # Remove from active connections
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)

            # Clean up empty job entries
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
                if job_id in self.message_sequence:
                    del self.message_sequence[job_id]

        # Cancel heartbeat task
        if websocket in self.heartbeat_tasks:
            self.heartbeat_tasks[websocket].cancel()
            del self.heartbeat_tasks[websocket]

        # Clean up metadata
        del self.connection_metadata[websocket]

        logger.info(f"WebSocket disconnected for job {job_id}")

    async def send_message(self, websocket: WebSocket, message: WebSocketMessage) -> None:
        """Send message to a specific WebSocket connection"""
        try:
            # Add sequence number
            if message.job_id in self.message_sequence:
                self.message_sequence[message.job_id] += 1
                message.sequence = self.message_sequence[message.job_id]

            # Send message
            await websocket.send_text(message.model_dump_json())

        except Exception as e:
            logger.error(f"Failed to send message to WebSocket: {e}")
            await self.disconnect(websocket)

    async def broadcast_to_job(self, job_id: str, message: WebSocketMessage) -> None:
        """Broadcast message to all connections for a specific job"""
        if job_id not in self.active_connections:
            # Buffer message if no active connections
            await self._buffer_message(job_id, message)
            return

        # Add sequence number
        if job_id in self.message_sequence:
            self.message_sequence[job_id] += 1
            message.sequence = self.message_sequence[job_id]

        # Send to all active connections
        disconnected = []
        for websocket in self.active_connections[job_id].copy():
            try:
                await websocket.send_text(message.model_dump_json())
            except Exception as e:
                logger.error(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(websocket)

        # Clean up disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)

        # Also buffer the message for late connections
        await self._buffer_message(job_id, message)

    async def get_job_connections(self, job_id: str) -> int:
        """Get number of active connections for a job"""
        return len(self.active_connections.get(job_id, set()))

    async def _heartbeat_loop(self, websocket: WebSocket, job_id: str) -> None:
        """Send periodic heartbeat messages"""
        try:
            while True:
                await asyncio.sleep(30)  # 30 second heartbeat

                if websocket in self.connection_metadata:
                    await self.send_message(websocket, WebSocketMessage(
                        type=MessageType.HEARTBEAT,
                        job_id=job_id,
                        data={"timestamp": datetime.now(timezone.utc).isoformat()}
                    ))

                    self.connection_metadata[websocket]["last_heartbeat"] = datetime.now(timezone.utc)
                else:
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error for job {job_id}: {e}")

    async def _buffer_message(self, job_id: str, message: WebSocketMessage) -> None:
        """Buffer message in Redis for late connections"""
        try:
            # Store last 100 messages per job
            key = f"ws_buffer:{job_id}"
            await self.redis_client.lpush(key, message.model_dump_json())
            await self.redis_client.ltrim(key, 0, 99)  # Keep only last 100
            await self.redis_client.expire(key, 3600)  # Expire after 1 hour

        except Exception as e:
            logger.error(f"Failed to buffer message for job {job_id}: {e}")

    async def _send_buffered_messages(self, websocket: WebSocket, job_id: str) -> None:
        """Send buffered messages to a newly connected client"""
        try:
            key = f"ws_buffer:{job_id}"
            messages = await self.redis_client.lrange(key, 0, -1)

            # Send in chronological order (reverse since we used lpush)
            for message_json in reversed(messages):
                try:
                    message_data = json.loads(message_json)
                    await websocket.send_text(message_json)
                except Exception as e:
                    logger.error(f"Failed to send buffered message: {e}")

        except Exception as e:
            logger.error(f"Failed to retrieve buffered messages for job {job_id}: {e}")


# Global connection manager instance
connection_manager: Optional[ConnectionManager] = None


async def get_connection_manager() -> ConnectionManager:
    """Get or create the global connection manager"""
    global connection_manager
    if connection_manager is None:
        # Initialize Redis client
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        connection_manager = ConnectionManager(redis_client)
    return connection_manager


async def validate_job_exists(job_id: str) -> bool:
    """Validate that a job exists (placeholder implementation)"""
    # TODO: Implement actual job validation logic
    # For now, accept any non-empty job_id
    return bool(job_id and len(job_id) > 0)


@websocket_router.websocket("/calibrate/{job_id}/logs")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time calibration logs and progress updates

    Args:
        websocket: WebSocket connection
        job_id: Calibration job identifier

    Message Types:
        - log: R script output lines
        - progress: Percentage completion updates
        - status: Job status changes (pending/running/completed/failed)
        - result: Final calibration results
        - error: Error messages and exceptions
        - heartbeat: Keep-alive messages
        - connection: Connection status messages
    """
    manager = await get_connection_manager()

    # Validate job exists
    if not await validate_job_exists(job_id):
        await websocket.close(code=4004, reason="Job not found")
        return

    try:
        # Accept connection and add to manager
        await manager.connect(websocket, job_id)

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await websocket.receive_text()

                # Handle client messages if needed
                try:
                    client_message = json.loads(data)
                    if client_message.get("type") == "ping":
                        await manager.send_message(websocket, WebSocketMessage(
                            type=MessageType.HEARTBEAT,
                            job_id=job_id,
                            data={"pong": True}
                        ))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {data}")

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error for job {job_id}: {e}")
                break

    finally:
        await manager.disconnect(websocket)


async def send_log_message(job_id: str, log_line: str, log_level: str = "info") -> None:
    """Send a log message to all connected clients for a job"""
    manager = await get_connection_manager()

    message = WebSocketMessage(
        type=MessageType.LOG,
        job_id=job_id,
        data={
            "line": log_line,
            "level": log_level,
            "source": "R_script"
        }
    )

    await manager.broadcast_to_job(job_id, message)


async def send_progress_update(job_id: str, progress: float, stage: str = "") -> None:
    """Send a progress update to all connected clients for a job"""
    manager = await get_connection_manager()

    message = WebSocketMessage(
        type=MessageType.PROGRESS,
        job_id=job_id,
        data={
            "progress": min(100.0, max(0.0, progress)),  # Clamp between 0-100
            "stage": stage,
            "percentage": f"{progress:.1f}%"
        }
    )

    await manager.broadcast_to_job(job_id, message)


async def send_status_update(job_id: str, status: JobStatus, message: str = "") -> None:
    """Send a job status update to all connected clients"""
    manager = await get_connection_manager()

    ws_message = WebSocketMessage(
        type=MessageType.STATUS,
        job_id=job_id,
        data={
            "status": status.value,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    await manager.broadcast_to_job(job_id, ws_message)


async def send_result_message(job_id: str, result_data: Dict) -> None:
    """Send final calibration results to all connected clients"""
    manager = await get_connection_manager()

    message = WebSocketMessage(
        type=MessageType.RESULT,
        job_id=job_id,
        data={
            "results": result_data,
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    )

    await manager.broadcast_to_job(job_id, message)


async def send_error_message(job_id: str, error: str, error_type: str = "general") -> None:
    """Send an error message to all connected clients for a job"""
    manager = await get_connection_manager()

    message = WebSocketMessage(
        type=MessageType.ERROR,
        job_id=job_id,
        data={
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

    await manager.broadcast_to_job(job_id, message)


async def get_connection_stats() -> Dict:
    """Get statistics about active WebSocket connections"""
    manager = await get_connection_manager()

    stats = {
        "total_jobs": len(manager.active_connections),
        "total_connections": sum(len(connections) for connections in manager.active_connections.values()),
        "jobs": {}
    }

    for job_id, connections in manager.active_connections.items():
        stats["jobs"][job_id] = {
            "connections": len(connections),
            "last_sequence": manager.message_sequence.get(job_id, 0)
        }

    return stats