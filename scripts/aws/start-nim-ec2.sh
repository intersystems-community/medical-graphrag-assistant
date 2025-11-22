#!/bin/bash
#
# Start NIM EC2 instance for demo/testing.
#
# This script:
# 1. Starts the stopped EC2 instance
# 2. Waits for it to be running
# 3. Retrieves public IP
# 4. Outputs NIM endpoint URL
#
# Usage:
#   ./scripts/aws/start-nim-ec2.sh

set -e  # Exit on error

# Configuration
INSTANCE_ID="${INSTANCE_ID:-i-xxxxxxxxxxxx}"  # UPDATE or set INSTANCE_ID env var

if [ "$INSTANCE_ID" = "i-xxxxxxxxxxxx" ]; then
  echo "❌ Error: INSTANCE_ID not set"
  echo ""
  echo "Set INSTANCE_ID environment variable:"
  echo "  export INSTANCE_ID='i-xxxxxxxxxxxx'"
  echo ""
  echo "Or update scripts/aws/start-nim-ec2.sh with your instance ID"
  exit 1
fi

echo "========================================"
echo "Starting NIM EC2 Instance"
echo "========================================"
echo ""
echo "Instance ID: $INSTANCE_ID"
echo ""

# Check current state
CURRENT_STATE=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)

echo "Current state: $CURRENT_STATE"

if [ "$CURRENT_STATE" = "running" ]; then
  echo "✅ Instance already running!"
elif [ "$CURRENT_STATE" = "stopped" ]; then
  echo ""
  echo "Starting instance..."
  aws ec2 start-instances --instance-ids "$INSTANCE_ID"

  echo "Waiting for instance to start..."
  aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

  echo "✅ Instance started!"
else
  echo "⚠️ Instance in unexpected state: $CURRENT_STATE"
  echo "Please check AWS console"
  exit 1
fi

# Get public IP
echo ""
echo "Retrieving public IP..."
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

if [ "$PUBLIC_IP" = "None" ] || [ -z "$PUBLIC_IP" ]; then
  echo "❌ No public IP assigned"
  echo "Please check instance configuration"
  exit 1
fi

# Wait for NIM container to be ready (startup time)
echo ""
echo "Waiting for NIM container to be ready (30 seconds)..."
sleep 30

# Test endpoint
echo ""
echo "Testing NIM endpoint..."
if curl -s --max-time 10 "http://$PUBLIC_IP:8000/health" > /dev/null 2>&1; then
  echo "✅ NIM endpoint is ready!"
else
  echo "⚠️ NIM endpoint not ready yet (may need more time)"
  echo "Wait 30 seconds and try again:"
  echo "  curl http://$PUBLIC_IP:8000/health"
fi

echo ""
echo "========================================"
echo "NIM Instance Ready!"
echo "========================================"
echo ""
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "NIM Endpoint: http://$PUBLIC_IP:8000/v1/embeddings"
echo ""
echo "Set environment variables:"
echo "  export NIM_ENDPOINT=\"http://$PUBLIC_IP:8000/v1/embeddings\""
echo "  export EMBEDDINGS_PROVIDER=\"nim\""
echo ""
echo "Test endpoint:"
echo "  curl http://$PUBLIC_IP:8000/health"
echo ""
echo "Run vectorization:"
echo "  python src/setup/vectorize_documents.py"
echo ""
echo "Stop instance when done (save ~\$24/day):"
echo "  ./scripts/aws/stop-nim-ec2.sh"
