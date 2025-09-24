#!/usr/bin/env python3
"""
Demo script showing real-time calibration with WebSocket logs
"""

import asyncio
import aiohttp
import json
import time

async def demo_realtime_calibration():
    """Demo real-time calibration with WebSocket monitoring"""

    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # Step 1: Create calibration job
        print("=" * 60)
        print("STEP 1: Creating calibration job...")
        print("=" * 60)

        payload = {
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate",
            "country": "Mozambique"
        }

        async with session.post(f"{base_url}/calibrate/realtime", json=payload) as resp:
            result = await resp.json()
            job_id = result["job_id"]
            print(f"✓ Job created: {job_id}")
            print(f"  Status: {result['status']}")
            print(f"  Message: {result['message']}")
            print()

        # Step 2: Check job status
        print("=" * 60)
        print("STEP 2: Checking job status...")
        print("=" * 60)

        async with session.get(f"{base_url}/calibrate/{job_id}/status") as resp:
            status = await resp.json()
            print(f"✓ Job Status:")
            print(f"  Status: {status['status']}")
            print(f"  Progress: {status['progress']}%")
            print(f"  Stage: {status['stage']}")
            print()

        # Step 3: Connect to WebSocket for real-time logs
        print("=" * 60)
        print("STEP 3: Connecting to WebSocket for real-time logs...")
        print("=" * 60)

        ws_url = f"ws://localhost:8000/ws/calibrate/{job_id}/logs"
        print(f"WebSocket URL: {ws_url}")
        print("\nReal-time logs:")
        print("-" * 40)

        try:
            async with session.ws_connect(ws_url) as ws:
                # Send initial subscription
                await ws.send_str(json.dumps({"type": "subscribe"}))

                # Set a timeout for receiving messages
                timeout_seconds = 30
                start_time = time.time()

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            msg_type = data.get('type', 'unknown')

                            # Format output based on message type
                            if msg_type == 'log':
                                print(f"📝 LOG: {data.get('message', '')}")
                            elif msg_type == 'progress':
                                print(f"⏳ PROGRESS: {data.get('progress', 0)}% - {data.get('stage', '')}")
                            elif msg_type == 'status':
                                print(f"📊 STATUS: {data.get('status', '')} - {data.get('message', '')}")
                            elif msg_type == 'result':
                                print(f"✅ RESULT: Job completed!")
                                print(json.dumps(data.get('result', {}), indent=2))
                                break
                            elif msg_type == 'error':
                                print(f"❌ ERROR: {data.get('message', '')}")
                                break
                            else:
                                print(f"📨 {msg_type.upper()}: {data}")

                            # Check for completion
                            if data.get('status') in ['completed', 'failed']:
                                break

                        except json.JSONDecodeError:
                            print(f"Raw message: {msg.data}")

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f'WebSocket error: {ws.exception()}')
                        break

                    # Check timeout
                    if time.time() - start_time > timeout_seconds:
                        print(f"\n⏱️ Timeout after {timeout_seconds} seconds")
                        break

        except Exception as e:
            print(f"WebSocket connection error: {e}")

        # Step 4: Final job status check
        print("\n" + "=" * 60)
        print("STEP 4: Final job status...")
        print("=" * 60)

        async with session.get(f"{base_url}/calibrate/{job_id}/status") as resp:
            if resp.status == 200:
                final_status = await resp.json()
                print(f"✓ Final Status:")
                print(f"  Status: {final_status['status']}")
                print(f"  Progress: {final_status['progress']}%")
                print(f"  Stage: {final_status['stage']}")
                if final_status.get('has_result'):
                    print(f"  Result: Available")
            else:
                print(f"Job status not available (HTTP {resp.status})")

        # Step 5: Check WebSocket stats
        print("\n" + "=" * 60)
        print("STEP 5: WebSocket Statistics...")
        print("=" * 60)

        async with session.get(f"{base_url}/websocket/stats") as resp:
            stats = await resp.json()
            print(f"✓ WebSocket Stats:")
            print(f"  Total Jobs: {stats['websocket_connections']['total_jobs']}")
            print(f"  Total Connections: {stats['websocket_connections']['total_connections']}")
            print(f"  Server Time: {stats['server_time']}")

if __name__ == "__main__":
    print("\n🚀 VA Calibration Real-time Demo")
    print("This demo shows real-time calibration with WebSocket log streaming\n")

    try:
        asyncio.run(demo_realtime_calibration())
        print("\n✅ Demo completed successfully!")
    except KeyboardInterrupt:
        print("\n\n⛔ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")