#!/usr/bin/env python3
"""
Test to show WebSocket stats behavior
"""

import asyncio
import aiohttp
import json
import time

async def test_stats():
    base_url = "http://localhost:8000"

    async with aiohttp.ClientSession() as session:
        # Step 1: Check initial stats
        print("1. Initial WebSocket stats (no jobs):")
        async with session.get(f"{base_url}/websocket/stats") as resp:
            stats = await resp.json()
            print(f"   Total jobs with connections: {stats['websocket_connections']['total_jobs']}")
            print(f"   Total connections: {stats['websocket_connections']['total_connections']}")
            print()

        # Step 2: Create a job
        print("2. Creating calibration job...")
        payload = {
            "va_data": {"insilicova": "use_example"},
            "age_group": "neonate",
            "country": "Mozambique"
        }
        async with session.post(f"{base_url}/calibrate/realtime", json=payload) as resp:
            result = await resp.json()
            job_id = result["job_id"]
            print(f"   Job created: {job_id}")
            print()

        # Step 3: Check stats immediately after job creation (no WebSocket connected yet)
        print("3. Stats immediately after job creation (no WebSocket connected):")
        async with session.get(f"{base_url}/websocket/stats") as resp:
            stats = await resp.json()
            print(f"   Total jobs with connections: {stats['websocket_connections']['total_jobs']}")
            print(f"   Total connections: {stats['websocket_connections']['total_connections']}")
            print()

        # Step 4: Connect WebSocket and check stats
        print("4. Connecting to WebSocket...")
        ws_url = f"ws://localhost:8000/ws/calibrate/{job_id}/logs"

        async with session.ws_connect(ws_url) as ws:
            print("   WebSocket connected!")

            # Step 5: Check stats while WebSocket is connected
            print("\n5. Stats while WebSocket is connected:")
            async with session.get(f"{base_url}/websocket/stats") as resp:
                stats = await resp.json()
                print(f"   Total jobs with connections: {stats['websocket_connections']['total_jobs']}")
                print(f"   Total connections: {stats['websocket_connections']['total_connections']}")
                print(f"   Jobs details: {stats['websocket_connections']['jobs']}")
                print()

            # Step 6: Connect a second WebSocket to same job
            print("6. Connecting second WebSocket to same job...")
            async with session.ws_connect(ws_url) as ws2:
                print("   Second WebSocket connected!")

                # Check stats with two connections
                print("\n7. Stats with two WebSocket connections to same job:")
                async with session.get(f"{base_url}/websocket/stats") as resp:
                    stats = await resp.json()
                    print(f"   Total jobs with connections: {stats['websocket_connections']['total_jobs']}")
                    print(f"   Total connections: {stats['websocket_connections']['total_connections']}")
                    print(f"   Jobs details: {stats['websocket_connections']['jobs']}")
                    print()

                # Close second WebSocket
                await ws2.close()

            print("8. Stats after closing second WebSocket (one still connected):")
            async with session.get(f"{base_url}/websocket/stats") as resp:
                stats = await resp.json()
                print(f"   Total jobs with connections: {stats['websocket_connections']['total_jobs']}")
                print(f"   Total connections: {stats['websocket_connections']['total_connections']}")
                print()

            # Close first WebSocket
            await ws.close()

        # Step 7: Check stats after all WebSockets closed
        print("9. Stats after all WebSockets closed:")
        async with session.get(f"{base_url}/websocket/stats") as resp:
            stats = await resp.json()
            print(f"   Total jobs with connections: {stats['websocket_connections']['total_jobs']}")
            print(f"   Total connections: {stats['websocket_connections']['total_connections']}")
            print()

        # Check if job still exists via status endpoint
        print("10. Job still exists? Checking job status endpoint:")
        async with session.get(f"{base_url}/calibrate/{job_id}/status") as resp:
            if resp.status == 200:
                status = await resp.json()
                print(f"    Yes - Job status: {status['status']}")
            else:
                print(f"    No - Job not found (HTTP {resp.status})")

if __name__ == "__main__":
    print("WebSocket Stats Behavior Test")
    print("=" * 60)
    print("This test demonstrates that websocket/stats only shows")
    print("jobs with ACTIVE WebSocket connections, not all jobs.")
    print("=" * 60)
    print()

    asyncio.run(test_stats())