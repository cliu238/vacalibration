#!/usr/bin/env python3
"""
Test WebSocket connection for real-time calibration logs
"""

import asyncio
import websockets
import json
import sys

async def test_websocket(job_id):
    uri = f"ws://localhost:8000/ws/calibrate/{job_id}/logs"
    print(f"Connecting to: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket!")
            print("Waiting for messages...")

            # Send initial message if needed
            await websocket.send(json.dumps({"type": "subscribe"}))

            # Listen for messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"[{data.get('type', 'unknown')}] {data.get('message', message)}")

                    # Exit when job completes
                    if data.get('type') == 'status' and data.get('status') in ['completed', 'failed']:
                        print(f"Job {data.get('status')}!")
                        break

                except json.JSONDecodeError:
                    print(f"Raw message: {message}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        print("Creating a new job first...")
        import requests
        response = requests.post(
            "http://localhost:8000/calibrate/realtime",
            json={
                "va_data": {"insilicova": "use_example"},
                "age_group": "neonate",
                "country": "Mozambique"
            }
        )
        result = response.json()
        job_id = result['job_id']
        print(f"Created job: {job_id}")

    asyncio.run(test_websocket(job_id))