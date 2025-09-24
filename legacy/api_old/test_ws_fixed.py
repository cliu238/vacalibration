#!/usr/bin/env python3
"""
Fixed WebSocket test that properly extracts message content
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_fixed(job_id):
    uri = f"ws://localhost:8000/ws/calibrate/{job_id}/logs"
    print(f"Connecting to: {uri}")
    print("=" * 60)

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected to WebSocket!")
            print("\nReal-time logs:")
            print("-" * 60)

            # Send initial message if needed
            await websocket.send(json.dumps({"type": "subscribe"}))

            # Listen for messages
            async for message in websocket:
                try:
                    msg = json.loads(message)
                    msg_type = msg.get('type', 'unknown')
                    data = msg.get('data', {})
                    timestamp = msg.get('timestamp', '')

                    # Display message based on type
                    if msg_type == 'connection':
                        print(f"[CONNECTION] {data.get('message', '')}")

                    elif msg_type == 'log':
                        log_line = data.get('line', data.get('message', ''))
                        log_level = data.get('level', 'info')
                        if log_line:  # Only print if there's content
                            print(f"[LOG-{log_level.upper()}] {log_line}")

                    elif msg_type == 'progress':
                        progress = data.get('progress', 0)
                        stage = data.get('stage', '')
                        if stage:  # Only print if there's a stage
                            print(f"[PROGRESS] {progress:.1f}% - {stage}")

                    elif msg_type == 'status':
                        status = data.get('status', '')
                        message = data.get('message', '')
                        if status or message:  # Only print if there's content
                            print(f"[STATUS] {status} - {message}")

                    elif msg_type == 'result':
                        print(f"[RESULT] Calibration completed!")
                        result = data.get('result', data)
                        if result:
                            print(json.dumps(result, indent=2))
                        break

                    elif msg_type == 'error':
                        error = data.get('error', data.get('message', 'Unknown error'))
                        print(f"[ERROR] {error}")
                        break

                    elif msg_type == 'heartbeat':
                        # Silently ignore heartbeats
                        pass

                    else:
                        # Show unknown messages for debugging
                        if data:  # Only show if there's data
                            print(f"[{msg_type.upper()}] {json.dumps(data)}")

                    # Exit on completion
                    if data.get('status') in ['completed', 'failed']:
                        print(f"\n[DONE] Job {data.get('status')}!")
                        break

                except json.JSONDecodeError:
                    print(f"[RAW] {message}")

    except Exception as e:
        print(f"[ERROR] {e}")

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
        print(f"✓ Created job: {job_id}")
        print()

    asyncio.run(test_websocket_fixed(job_id))