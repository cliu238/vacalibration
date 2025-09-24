#!/usr/bin/env python3
"""
Example WebSocket client for testing real-time calibration logs
"""

import asyncio
import json
import logging
from datetime import datetime
import websockets
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalibrationWebSocketClient:
    """WebSocket client for real-time calibration monitoring"""

    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.job_id = None
        self.websocket = None

    async def start_calibration(self, calibration_request: dict) -> str:
        """Start a new calibration job and return job ID"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/calibrate/realtime",
                json=calibration_request
            )
            response.raise_for_status()
            result = response.json()
            self.job_id = result["job_id"]
            logger.info(f"Started calibration job: {self.job_id}")
            return self.job_id

    async def connect_websocket(self, job_id: str = None):
        """Connect to WebSocket for real-time updates"""
        if job_id:
            self.job_id = job_id

        if not self.job_id:
            raise ValueError("No job ID specified")

        ws_endpoint = f"{self.ws_url}/ws/calibrate/{self.job_id}/logs"
        logger.info(f"Connecting to WebSocket: {ws_endpoint}")

        try:
            self.websocket = await websockets.connect(ws_endpoint)
            logger.info("WebSocket connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            raise

    async def listen_for_updates(self):
        """Listen for real-time updates from the calibration job"""
        if not self.websocket:
            raise ValueError("WebSocket not connected")

        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message: {e}")
                    logger.debug(f"Raw message: {message}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error listening for updates: {e}")

    async def _handle_message(self, data: dict):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        job_id = data.get("job_id")
        timestamp = data.get("timestamp")
        payload = data.get("data", {})
        sequence = data.get("sequence")

        logger.info(f"[{sequence}] {message_type.upper()} - {job_id}")

        if message_type == "connection":
            print(f"🔗 Connected to job {job_id}")
            print(f"   Status: {payload.get('status')}")
            print(f"   Message: {payload.get('message')}")

        elif message_type == "log":
            level = payload.get("level", "info")
            line = payload.get("line", "")
            source = payload.get("source", "")

            level_emoji = {
                "info": "ℹ️",
                "error": "❌",
                "warning": "⚠️",
                "debug": "🐛"
            }.get(level, "📝")

            print(f"{level_emoji} [{source}] {line}")

        elif message_type == "progress":
            progress = payload.get("progress", 0)
            stage = payload.get("stage", "")
            percentage = payload.get("percentage", "")

            print(f"📊 Progress: {percentage} - {stage}")
            self._print_progress_bar(progress)

        elif message_type == "status":
            status = payload.get("status")
            message = payload.get("message", "")

            status_emoji = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫"
            }.get(status, "📋")

            print(f"{status_emoji} Status: {status.upper()}")
            if message:
                print(f"   {message}")

        elif message_type == "result":
            print("🎉 CALIBRATION COMPLETED!")
            results = payload.get("results", {})
            completed_at = payload.get("completed_at")

            print(f"   Completed at: {completed_at}")
            print("   Results summary:")

            if "uncalibrated" in results:
                print("   📊 Uncalibrated CSMF:")
                for cause, value in results["uncalibrated"].items():
                    print(f"      {cause}: {value:.3f}")

            if "calibrated" in results:
                print("   🎯 Calibrated results:")
                for algo, data in results["calibrated"].items():
                    print(f"      Algorithm: {algo}")
                    if "mean" in data:
                        for cause, value in data["mean"].items():
                            print(f"         {cause}: {value:.3f}")

        elif message_type == "error":
            error = payload.get("error", "")
            error_type = payload.get("error_type", "general")

            print(f"❌ ERROR ({error_type}): {error}")

        elif message_type == "heartbeat":
            print("💓 Heartbeat")

        else:
            print(f"🔍 Unknown message type: {message_type}")
            print(f"   Data: {payload}")

        print()  # Add blank line for readability

    def _print_progress_bar(self, progress: float, width: int = 50):
        """Print a visual progress bar"""
        filled = int(width * progress / 100)
        bar = "█" * filled + "░" * (width - filled)
        print(f"   [{bar}] {progress:.1f}%")

    async def close(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            logger.info("WebSocket connection closed")


async def example_usage():
    """Example usage of the WebSocket client"""
    client = CalibrationWebSocketClient()

    # Example calibration request
    calibration_request = {
        "va_data": {"insilicova": "use_example"},
        "age_group": "neonate",
        "country": "Mozambique",
        "mmat_type": "prior",
        "ensemble": True,
        "async": True
    }

    try:
        # Start calibration
        print("🚀 Starting calibration job...")
        job_id = await client.start_calibration(calibration_request)

        # Connect to WebSocket
        print("🔌 Connecting to WebSocket...")
        await client.connect_websocket(job_id)

        # Listen for updates
        print("👂 Listening for real-time updates...\n")
        await client.listen_for_updates()

    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()


async def monitor_existing_job(job_id: str):
    """Monitor an existing calibration job"""
    client = CalibrationWebSocketClient()

    try:
        print(f"🔌 Connecting to existing job: {job_id}")
        await client.connect_websocket(job_id)

        print("👂 Listening for updates...\n")
        await client.listen_for_updates()

    except KeyboardInterrupt:
        print("\n⏹️ Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Monitor existing job
        job_id = sys.argv[1]
        asyncio.run(monitor_existing_job(job_id))
    else:
        # Start new calibration and monitor
        asyncio.run(example_usage())