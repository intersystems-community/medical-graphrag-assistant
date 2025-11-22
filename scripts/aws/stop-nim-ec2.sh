#!/bin/bash
#
# Stop NIM EC2 instance to save money.
#
# This script:
# 1. Stops the running EC2 instance
# 2. Waits for it to be stopped
# 3. Shows cost savings
#
# Savings: ~$24/day when stopped (g5.xlarge)
#
# Usage:
#   ./scripts/aws/stop-nim-ec2.sh

set -e  # Exit on error

# Configuration
INSTANCE_ID="${INSTANCE_ID:-i-xxxxxxxxxxxx}"  # UPDATE or set INSTANCE_ID env var

if [ "$INSTANCE_ID" = "i-xxxxxxxxxxxx" ]; then
  echo "❌ Error: INSTANCE_ID not set"
  echo ""
  echo "Set INSTANCE_ID environment variable:"
  echo "  export INSTANCE_ID='i-xxxxxxxxxxxx'"
  echo ""
  echo "Or update scripts/aws/stop-nim-ec2.sh with your instance ID"
  exit 1
fi

echo "========================================"
echo "Stopping NIM EC2 Instance"
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

if [ "$CURRENT_STATE" = "stopped" ]; then
  echo "✅ Instance already stopped!"
elif [ "$CURRENT_STATE" = "running" ]; then
  echo ""
  echo "Stopping instance..."
  aws ec2 stop-instances --instance-ids "$INSTANCE_ID"

  echo "Waiting for instance to stop..."
  aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID"

  echo "✅ Instance stopped!"
else
  echo "⚠️ Instance in unexpected state: $CURRENT_STATE"
  echo "Please check AWS console"
  exit 1
fi

echo ""
echo "========================================"
echo "Instance Stopped (Saving Money!)"
echo "========================================"
echo ""
echo "Cost savings:"
echo "  g5.xlarge hourly rate: \$1.006/hour"
echo "  Daily savings (24hrs): ~\$24.14/day"
echo "  Monthly savings (30d): ~\$724.32/month"
echo ""
echo "To restart for next demo:"
echo "  ./scripts/aws/start-nim-ec2.sh"
echo ""
echo "Recommended usage pattern:"
echo "  - Run 8 hours/day × 20 days/month = \$160.96/month"
echo "  - vs 24/7 = \$724.32/month"
echo "  - Savings: \$563.36/month (78%)"
echo ""
echo "Set a reminder to stop after demos!"
