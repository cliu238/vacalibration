#!/usr/bin/env python3
"""
WebSocket test for VA calibration API
"""

import asyncio
import websockets
import json
import requests
import sys

async def test_websocket():
    """Test WebSocket connection and messages"""

    # First, create a real-time calibration job
    print("1. Creating real-time calibration job...")
    response = requests.post(
        "http://localhost:8000/calibrate/realtime",
        json={
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate",
            "country": "Mozambique"
        }
    )

    if response.status_code != 200:
        print(f"Failed to create job: {response.text}")
        return

    job_data = response.json()
    job_id = job_data.get("job_id")
    print(f"Created job: {job_id}")

    # Connect to WebSocket
    ws_url = f"ws://localhost:8000/ws/calibrate/{job_id}/logs"
    print(f"\n2. Connecting to WebSocket: {ws_url}")

    try:
        async with websockets.connect(ws_url) as websocket:
            print("Connected! Receiving messages...")
            print("-" * 50)

            message_count = 0
            while True:
                try:
                    # Set timeout to avoid hanging forever
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    message_count += 1

                    # Parse and display message
                    try:
                        msg_data = json.loads(message)
                        msg_type = msg_data.get("type", "unknown")

                        # Extract relevant data based on message type
                        if msg_type == "connection":
                            print(f"[{msg_type.upper()}] {msg_data['data'].get('message', '')}")
                        elif msg_type == "log":
                            print(f"[LOG] {msg_data['data'].get('line', '')}")
                        elif msg_type == "progress":
                            progress = msg_data['data'].get('progress', 0)
                            stage = msg_data['data'].get('stage', '')
                            print(f"[PROGRESS] {progress:.1f}% - {stage}")
                        elif msg_type == "status":
                            status = msg_data['data'].get('status', '')
                            msg = msg_data['data'].get('message', '')
                            print(f"[STATUS] {status}: {msg}")
                        elif msg_type == "result":
                            print(f"[RESULT] Calibration completed!")
                            # Pretty print a sample of results
                            if 'data' in msg_data and 'result' in msg_data['data']:
                                result = msg_data['data']['result']
                                if 'calibrated' in result:
                                    print("Sample calibrated values:")
                                    for algo, values in result['calibrated'].items():
                                        if 'mean' in values:
                                            print(f"  {algo}: {list(values['mean'].items())[:3]}...")
                                        break
                            break  # Exit after receiving results
                        elif msg_type == "error":
                            print(f"[ERROR] {msg_data['data'].get('error', 'Unknown error')}")
                            break
                        else:
                            print(f"[{msg_type.upper()}] {msg_data.get('data', {})}")

                    except json.JSONDecodeError:
                        print(f"[RAW] {message}")

                except asyncio.TimeoutError:
                    print("\nTimeout waiting for messages. Job may have completed.")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("\nWebSocket connection closed.")
                    break

            print("-" * 50)
            print(f"Received {message_count} messages total")

    except Exception as e:
        print(f"WebSocket error: {e}")

    # Check final job status
    print(f"\n3. Checking final job status...")
    status_response = requests.get(f"http://localhost:8000/calibrate/{job_id}/status")
    if status_response.status_code == 200:
        status = status_response.json()
        print(f"Job status: {status.get('status', 'unknown')}")
        if status.get('result'):
            print("Calibration completed successfully!")
    else:
        print(f"Failed to get status: {status_response.text}")

if __name__ == "__main__":
    print("VA Calibration WebSocket Test")
    print("=" * 50)
    asyncio.run(test_websocket())
    print("\nTest completed!")