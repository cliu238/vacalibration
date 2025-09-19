#!/usr/bin/env python3
"""
Redis pub/sub system for real-time message streaming
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone
import redis.asyncio as redis
from redis.asyncio.client import Redis, PubSub
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Set up logging
logger = logging.getLogger(__name__)


class RedisMessage(BaseModel):
    """Redis message model"""
    channel: str
    message_type: str
    job_id: str
    timestamp: datetime
    data: Dict[str, Any]
    retry_count: int = 0


class RedisPublisher:
    """Redis publisher for sending messages to channels"""

    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client

    async def publish_log(self, job_id: str, log_line: str, log_level: str = "info") -> None:
        """Publish a log message to the job's log channel"""
        message = RedisMessage(
            channel=f"job:{job_id}:logs",
            message_type="log",
            job_id=job_id,
            timestamp=datetime.now(timezone.utc),
            data={
                "line": log_line,
                "level": log_level,
                "source": "R_script"
            }
        )

        await self._publish_message(message)

    async def publish_progress(self, job_id: str, progress: float, stage: str = "") -> None:
        """Publish a progress update to the job's progress channel"""
        message = RedisMessage(
            channel=f"job:{job_id}:progress",
            message_type="progress",
            job_id=job_id,
            timestamp=datetime.now(timezone.utc),
            data={
                "progress": min(100.0, max(0.0, progress)),
                "stage": stage,
                "percentage": f"{progress:.1f}%"
            }
        )

        await self._publish_message(message)

    async def publish_status(self, job_id: str, status: str, message: str = "") -> None:
        """Publish a status update to the job's status channel"""
        redis_message = RedisMessage(
            channel=f"job:{job_id}:status",
            message_type="status",
            job_id=job_id,
            timestamp=datetime.now(timezone.utc),
            data={
                "status": status,
                "message": message
            }
        )

        await self._publish_message(redis_message)

    async def publish_result(self, job_id: str, result_data: Dict) -> None:
        """Publish final results to the job's result channel"""
        message = RedisMessage(
            channel=f"job:{job_id}:results",
            message_type="result",
            job_id=job_id,
            timestamp=datetime.now(timezone.utc),
            data={
                "results": result_data,
                "completed_at": datetime.now(timezone.utc).isoformat()
            }
        )

        await self._publish_message(message)

    async def publish_error(self, job_id: str, error: str, error_type: str = "general") -> None:
        """Publish an error message to the job's error channel"""
        message = RedisMessage(
            channel=f"job:{job_id}:errors",
            message_type="error",
            job_id=job_id,
            timestamp=datetime.now(timezone.utc),
            data={
                "error": error,
                "error_type": error_type
            }
        )

        await self._publish_message(message)

    async def _publish_message(self, message: RedisMessage) -> None:
        """Publish a message to its designated channel"""
        try:
            # Publish to specific channel
            await self.redis_client.publish(
                message.channel,
                message.model_dump_json()
            )

            # Also publish to general job channel for aggregated listening
            general_channel = f"job:{message.job_id}:all"
            await self.redis_client.publish(
                general_channel,
                message.model_dump_json()
            )

            logger.debug(f"Published {message.message_type} message to {message.channel}")

        except Exception as e:
            logger.error(f"Failed to publish message to {message.channel}: {e}")
            # Store failed message for retry
            await self._store_failed_message(message)

    async def _store_failed_message(self, message: RedisMessage) -> None:
        """Store failed message for retry"""
        try:
            key = f"failed_messages:{message.job_id}"
            message.retry_count += 1
            await self.redis_client.lpush(key, message.model_dump_json())
            await self.redis_client.expire(key, 3600)  # Expire after 1 hour

        except Exception as e:
            logger.error(f"Failed to store failed message: {e}")


class RedisSubscriber:
    """Redis subscriber for receiving messages from channels"""

    def __init__(self, redis_client: Redis):
        self.redis_client = redis_client
        self.subscriptions: Dict[str, PubSub] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def subscribe_to_job(self, job_id: str, message_handler: Callable) -> None:
        """Subscribe to all channels for a specific job"""
        patterns = [
            f"job:{job_id}:logs",
            f"job:{job_id}:progress",
            f"job:{job_id}:status",
            f"job:{job_id}:results",
            f"job:{job_id}:errors",
            f"job:{job_id}:all"
        ]

        for pattern in patterns:
            await self.subscribe_to_pattern(pattern, message_handler)

    async def subscribe_to_pattern(self, pattern: str, message_handler: Callable) -> None:
        """Subscribe to a specific channel pattern"""
        try:
            # Create new pubsub instance
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe(pattern)

            # Store subscription and handler
            self.subscriptions[pattern] = pubsub
            self.message_handlers[pattern] = message_handler

            # Start listening task
            task = asyncio.create_task(self._listen_to_channel(pattern, pubsub))
            self.running_tasks[pattern] = task

            logger.info(f"Subscribed to pattern: {pattern}")

        except Exception as e:
            logger.error(f"Failed to subscribe to pattern {pattern}: {e}")

    async def unsubscribe_from_pattern(self, pattern: str) -> None:
        """Unsubscribe from a specific channel pattern"""
        try:
            # Cancel listening task
            if pattern in self.running_tasks:
                self.running_tasks[pattern].cancel()
                del self.running_tasks[pattern]

            # Close pubsub connection
            if pattern in self.subscriptions:
                await self.subscriptions[pattern].unsubscribe(pattern)
                await self.subscriptions[pattern].close()
                del self.subscriptions[pattern]

            # Remove handler
            if pattern in self.message_handlers:
                del self.message_handlers[pattern]

            logger.info(f"Unsubscribed from pattern: {pattern}")

        except Exception as e:
            logger.error(f"Failed to unsubscribe from pattern {pattern}: {e}")

    async def unsubscribe_from_job(self, job_id: str) -> None:
        """Unsubscribe from all channels for a specific job"""
        patterns = [
            f"job:{job_id}:logs",
            f"job:{job_id}:progress",
            f"job:{job_id}:status",
            f"job:{job_id}:results",
            f"job:{job_id}:errors",
            f"job:{job_id}:all"
        ]

        for pattern in patterns:
            await self.unsubscribe_from_pattern(pattern)

    async def _listen_to_channel(self, pattern: str, pubsub: PubSub) -> None:
        """Listen to messages from a specific channel"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse Redis message
                        redis_message = RedisMessage.model_validate_json(message["data"])

                        # Call message handler
                        handler = self.message_handlers.get(pattern)
                        if handler:
                            await handler(redis_message)

                    except Exception as e:
                        logger.error(f"Error processing message from {pattern}: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error listening to channel {pattern}: {e}")

    async def close_all_subscriptions(self) -> None:
        """Close all active subscriptions"""
        patterns = list(self.subscriptions.keys())
        for pattern in patterns:
            await self.unsubscribe_from_pattern(pattern)


class RedisMessageBuffer:
    """Buffer for storing and retrieving recent messages"""

    def __init__(self, redis_client: Redis, buffer_size: int = 100, ttl: int = 3600):
        self.redis_client = redis_client
        self.buffer_size = buffer_size
        self.ttl = ttl

    async def store_message(self, job_id: str, message: RedisMessage) -> None:
        """Store a message in the buffer"""
        try:
            key = f"message_buffer:{job_id}"
            await self.redis_client.lpush(key, message.model_dump_json())
            await self.redis_client.ltrim(key, 0, self.buffer_size - 1)
            await self.redis_client.expire(key, self.ttl)

        except Exception as e:
            logger.error(f"Failed to store message in buffer for job {job_id}: {e}")

    async def get_recent_messages(self, job_id: str, count: int = None) -> List[RedisMessage]:
        """Get recent messages for a job"""
        try:
            key = f"message_buffer:{job_id}"
            if count is None:
                count = self.buffer_size

            messages_json = await self.redis_client.lrange(key, 0, count - 1)
            messages = []

            # Parse messages in chronological order
            for message_json in reversed(messages_json):
                try:
                    message = RedisMessage.model_validate_json(message_json)
                    messages.append(message)
                except Exception as e:
                    logger.error(f"Failed to parse buffered message: {e}")

            return messages

        except Exception as e:
            logger.error(f"Failed to retrieve messages for job {job_id}: {e}")
            return []

    async def clear_buffer(self, job_id: str) -> None:
        """Clear the message buffer for a job"""
        try:
            key = f"message_buffer:{job_id}"
            await self.redis_client.delete(key)

        except Exception as e:
            logger.error(f"Failed to clear buffer for job {job_id}: {e}")


class RedisManager:
    """Unified Redis manager for pub/sub operations"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[Redis] = None
        self.publisher: Optional[RedisPublisher] = None
        self.subscriber: Optional[RedisSubscriber] = None
        self.message_buffer: Optional[RedisMessageBuffer] = None

    async def initialize(self) -> None:
        """Initialize Redis connections and components"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

            # Test connection
            await self.redis_client.ping()

            # Initialize components
            self.publisher = RedisPublisher(self.redis_client)
            self.subscriber = RedisSubscriber(self.redis_client)
            self.message_buffer = RedisMessageBuffer(self.redis_client)

            logger.info("Redis manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Redis manager: {e}")
            raise

    async def close(self) -> None:
        """Close Redis connections"""
        try:
            if self.subscriber:
                await self.subscriber.close_all_subscriptions()

            if self.redis_client:
                await self.redis_client.close()

            logger.info("Redis manager closed")

        except Exception as e:
            logger.error(f"Error closing Redis manager: {e}")

    @asynccontextmanager
    async def get_manager(self):
        """Context manager for Redis operations"""
        await self.initialize()
        try:
            yield self
        finally:
            await self.close()


# Global Redis manager instance
redis_manager: Optional[RedisManager] = None


async def get_redis_manager() -> RedisManager:
    """Get or create the global Redis manager"""
    global redis_manager
    if redis_manager is None:
        redis_manager = RedisManager()
        await redis_manager.initialize()
    return redis_manager


async def publish_calibration_log(job_id: str, log_line: str, log_level: str = "info") -> None:
    """Convenience function to publish a calibration log"""
    manager = await get_redis_manager()
    if manager.publisher:
        await manager.publisher.publish_log(job_id, log_line, log_level)


async def publish_calibration_progress(job_id: str, progress: float, stage: str = "") -> None:
    """Convenience function to publish calibration progress"""
    manager = await get_redis_manager()
    if manager.publisher:
        await manager.publisher.publish_progress(job_id, progress, stage)


async def publish_calibration_status(job_id: str, status: str, message: str = "") -> None:
    """Convenience function to publish calibration status"""
    manager = await get_redis_manager()
    if manager.publisher:
        await manager.publisher.publish_status(job_id, status, message)


async def publish_calibration_result(job_id: str, result_data: Dict) -> None:
    """Convenience function to publish calibration results"""
    manager = await get_redis_manager()
    if manager.publisher:
        await manager.publisher.publish_result(job_id, result_data)


async def publish_calibration_error(job_id: str, error: str, error_type: str = "general") -> None:
    """Convenience function to publish calibration errors"""
    manager = await get_redis_manager()
    if manager.publisher:
        await manager.publisher.publish_error(job_id, error, error_type)