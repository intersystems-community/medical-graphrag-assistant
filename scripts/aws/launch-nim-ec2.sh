#!/bin/bash
#
# Launch EC2 instance with NVIDIA NIM for embeddings.
#
# This script:
# 1. Launches g5.xlarge EC2 instance
# 2. Installs NVIDIA drivers and Docker
# 3. Pulls and runs NIM container
# 4. Outputs NIM endpoint URL
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - EC2 key pair created
#   - Security group allowing inbound on port 8000
#
# Usage:
#   ./scripts/aws/launch-nim-ec2.sh

set -e  # Exit on error

# Configuration
INSTANCE_TYPE="g5.xlarge"
AMI_ID="ami-0c55b159cbfafe1f0"  # Deep Learning AMI (Ubuntu) - UPDATE for your region
KEY_NAME="your-key-name"        # UPDATE with your key pair name
SECURITY_GROUP="sg-xxxxxxxxx"   # UPDATE with your security group ID
SUBNET_ID="subnet-xxxxxxxxx"    # UPDATE with your subnet ID
INSTANCE_NAME="nim-embeddings"
NGC_API_KEY="${NGC_API_KEY:-your-ngc-api-key}"  # Set NGC_API_KEY env var or update here

echo "========================================"
echo "Launching NIM EC2 Instance"
echo "========================================"
echo ""
echo "Instance type: $INSTANCE_TYPE"
echo "AMI: $AMI_ID"
echo "Key pair: $KEY_NAME"
echo ""

# Launch instance
echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SECURITY_GROUP" \
  --subnet-id "$SUBNET_ID" \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3"}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
  --query 'Instances[0].InstanceId' \
  --output text)

echo "✅ Instance launched: $INSTANCE_ID"

# Wait for instance to be running
echo ""
echo "Waiting for instance to start..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "✅ Instance running: $PUBLIC_IP"

# Wait for SSH to be available
echo ""
echo "Waiting for SSH to be available..."
sleep 30

# Install NIM container via SSH
echo ""
echo "Installing NIM container..."
ssh -i "$KEY_NAME.pem" -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" << 'EOF'
  # Update system
  sudo apt-get update

  # Install NVIDIA Container Toolkit (if not pre-installed)
  if ! command -v nvidia-container-toolkit &> /dev/null; then
    echo "Installing NVIDIA Container Toolkit..."
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
      sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    sudo apt-get update
    sudo apt-get install -y nvidia-container-toolkit
    sudo systemctl restart docker
  fi

  # Login to NGC registry
  echo "Logging into NGC registry..."
  echo "${NGC_API_KEY}" | docker login nvcr.io --username '$oauthtoken' --password-stdin

  # Pull NIM container
  echo "Pulling NIM container..."
  docker pull nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

  # Run NIM container
  echo "Starting NIM container..."
  docker run -d \
    --gpus all \
    --name nim-embeddings \
    --restart unless-stopped \
    -p 8000:8000 \
    -e NGC_API_KEY="${NGC_API_KEY}" \
    nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

  # Wait for container to be ready
  echo "Waiting for NIM to be ready..."
  sleep 30

  # Test endpoint
  curl -s http://localhost:8000/health || echo "Health check pending..."
EOF

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
echo "Test NIM endpoint:"
echo "  curl http://$PUBLIC_IP:8000/health"
echo ""
echo "To stop instance (save money):"
echo "  ./scripts/aws/stop-nim-ec2.sh"
echo ""
echo "To SSH into instance:"
echo "  ssh -i $KEY_NAME.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Save instance ID for later:"
echo "  echo \"INSTANCE_ID=$INSTANCE_ID\" >> .env"
