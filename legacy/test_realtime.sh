#!/bin/bash

# Create a calibration job
echo "Creating calibration job..."
RESPONSE=$(curl -s -X POST http://localhost:8000/calibrate/realtime \
  -H "Content-Type: application/json" \
  -d '{"va_data": {"insilicova": "use_example"}, "age_group": "neonate", "country": "Mozambique"}')

echo "Response: $RESPONSE"

# Extract job ID
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# Check WebSocket stats
echo ""
echo "WebSocket stats:"
curl -s http://localhost:8000/websocket/stats | jq .

# Check job status
echo ""
echo "Job status:"
curl -s http://localhost:8000/calibrate/$JOB_ID/status 2>/dev/null | jq . || echo "Job status endpoint not available"

# Connect to WebSocket
echo ""
echo "Connecting to WebSocket at ws://localhost:8000/ws/calibrate/$JOB_ID/logs"
echo "Press Ctrl+C to stop..."
wscat -c ws://localhost:8000/ws/calibrate/$JOB_ID/logs