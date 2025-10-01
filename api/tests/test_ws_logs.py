#!/usr/bin/env python3
"""
Test WebSocket log streaming for calibration jobs
"""
import asyncio
import json
import requests
import websockets
from datetime import datetime

async def test_websocket_logs():
    """Test WebSocket log streaming"""

    # 1. Create a calibration job
    print("Creating calibration job...")

    # Use the format expected by the API (from frontend code)
    calibration_data = {
        "deaths": {
            "death_1": 1,
            "death_2": 0,
            "death_3": 1
        },
        "dataset": "comsamoz_broad",
        "ageGroup": "neonate",
        "country": "Mozambique",
        "algorithm": "InSilicoVA",
        "ensemble": False,
        "asyncMode": True
    }

    response = requests.post(
        "http://localhost:8000/calibrate",
        json=calibration_data,
        timeout=10
    )

    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code != 200:
        print("Failed to create job!")
        return

    result = response.json()
    job_id = result.get("job_id")

    if not job_id:
        print("No job_id in response!")
        return

    print(f"\nJob created: {job_id}")
    print(f"Connecting to WebSocket: ws://localhost:8000/ws/calibrate/{job_id}/logs\n")

    # 2. Connect to WebSocket and listen for logs
    uri = f"ws://localhost:8000/ws/calibrate/{job_id}/logs"

    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected! Listening for messages...\n")
            print("=" * 80)

            # Listen for messages (with timeout)
            message_count = 0
            start_time = datetime.now()

            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=30)
                    message_count += 1

                    # Parse and display message
                    try:
                        data = json.loads(message)
                        msg_type = data.get("type", "unknown")
                        timestamp = data.get("timestamp", "")

                        print(f"[{message_count}] Type: {msg_type}")

                        if msg_type == "log":
                            log_data = data.get("data", {})
                            log_line = log_data.get("line", "")
                            log_level = log_data.get("level", "info")
                            print(f"    Level: {log_level}")
                            print(f"    Log: {log_line}")

                        elif msg_type == "status":
                            status_data = data.get("data", {})
                            print(f"    Status: {status_data.get('status')}")
                            print(f"    Message: {status_data.get('message')}")

                        elif msg_type == "connection":
                            print(f"    {data.get('data', {}).get('message')}")

                        print(f"    Timestamp: {timestamp}")
                        print("-" * 80)

                    except json.JSONDecodeError:
                        print(f"Raw message: {message}")
                        print("-" * 80)

                except asyncio.TimeoutError:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f"\nNo messages for 30s (total time: {elapsed:.1f}s)")
                    print(f"Total messages received: {message_count}")
                    break

                except websockets.exceptions.ConnectionClosed:
                    print("\nWebSocket connection closed")
                    print(f"Total messages received: {message_count}")
                    break

    except Exception as e:
        print(f"\nError: {e}")

    print("\nTest complete!")

if __name__ == "__main__":
    asyncio.run(test_websocket_logs())