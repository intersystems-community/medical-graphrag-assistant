#!/bin/bash
#
# Launch EC2 instance with FHIR AI Hackathon Kit
#
# This script:
# 1. Creates security group
# 2. Launches EC2 instance (m5.xlarge or g5.xlarge)
# 3. Installs Docker and docker-compose
# 4. Deploys IRIS (and optionally NIM on GPU instance)
# 5. Outputs connection details
#
# Prerequisites:
#   - AWS CLI configured
#   - EC2 key pair created (fhir-ai-key)
#   - Environment variables set (AWS_PROFILE, AWS_DEFAULT_REGION)
#
# Usage:
#   ./scripts/aws/launch-fhir-stack.sh [m5|g5]
#
# Arguments:
#   m5 - Launch m5.xlarge (no GPU, IRIS only) - DEFAULT
#   g5 - Launch g5.xlarge (GPU, IRIS + NIM)

set -e  # Exit on error

# Source environment variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Configuration
INSTANCE_TYPE="${1:-m5.xlarge}"  # Default to m5.xlarge
INSTANCE_NAME="fhir-ai-stack"
KEY_NAME="fhir-ai-key"
SECURITY_GROUP_NAME="fhir-ai-stack-sg"

# Determine AMI based on instance type
if [[ "$INSTANCE_TYPE" == "g5"* ]]; then
    # Deep Learning AMI for GPU instances
    AMI_ID="ami-0c55b159cbfafe1f0"  # Deep Learning AMI (Ubuntu 22.04) - UPDATE for your region
    INSTANCE_TYPE="g5.xlarge"
    USE_GPU=true
else
    # Ubuntu 22.04 LTS AMI for non-GPU instances
    AMI_ID="ami-0866a3c8686eaeeba"  # Ubuntu 22.04 LTS - us-east-1
    INSTANCE_TYPE="m5.xlarge"
    USE_GPU=false
fi

echo "========================================"
echo "FHIR AI Hackathon Kit - AWS Deployment"
echo "========================================"
echo ""
echo "Instance type: $INSTANCE_TYPE"
echo "GPU support: $USE_GPU"
echo "AMI: $AMI_ID"
echo "Key pair: $KEY_NAME"
echo ""

# Check for key pair
if [ ! -f "${KEY_NAME}.pem" ]; then
    echo "❌ Error: Key pair file ${KEY_NAME}.pem not found!"
    echo "Run: aws ec2 create-key-pair --key-name $KEY_NAME --query 'KeyMaterial' --output text > ${KEY_NAME}.pem"
    exit 1
fi

# Get your current IP for security group (prefer IPv4)
echo "Getting your IP address..."
MY_IP=$(curl -4 -s ifconfig.me 2>/dev/null || curl -s ifconfig.me)
if [[ "$MY_IP" == *":"* ]]; then
    # IPv6 address
    IS_IPV6=true
    IP_CIDR="${MY_IP}/128"
    echo "Your IP: $MY_IP (IPv6)"
else
    # IPv4 address
    IS_IPV6=false
    IP_CIDR="${MY_IP}/32"
    echo "Your IP: $MY_IP (IPv4)"
fi
echo ""

# Create security group if it doesn't exist
echo "Creating security group..."
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SECURITY_GROUP_NAME" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "None")

if [ "$SG_ID" == "None" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SECURITY_GROUP_NAME" \
        --description "FHIR AI Hackathon Kit - IRIS + NIM" \
        --query 'GroupId' \
        --output text)

    echo "✅ Security group created: $SG_ID"

    # Add security group rules
    echo "Adding security group rules..."

    if [ "$IS_IPV6" = true ]; then
        # IPv6 rules
        aws ec2 authorize-security-group-ingress \
            --group-id "$SG_ID" \
            --ip-permissions \
            IpProtocol=tcp,FromPort=22,ToPort=22,Ipv6Ranges="[{CidrIpv6=$IP_CIDR}]" \
            IpProtocol=tcp,FromPort=1972,ToPort=1972,Ipv6Ranges="[{CidrIpv6=$IP_CIDR}]" \
            IpProtocol=tcp,FromPort=52773,ToPort=52773,Ipv6Ranges="[{CidrIpv6=$IP_CIDR}]"

        if [ "$USE_GPU" = true ]; then
            aws ec2 authorize-security-group-ingress \
                --group-id "$SG_ID" \
                --ip-permissions IpProtocol=tcp,FromPort=8000,ToPort=8000,Ipv6Ranges="[{CidrIpv6=$IP_CIDR}]"
        fi
    else
        # IPv4 rules
        aws ec2 authorize-security-group-ingress \
            --group-id "$SG_ID" \
            --protocol tcp --port 22 --cidr "$IP_CIDR"

        aws ec2 authorize-security-group-ingress \
            --group-id "$SG_ID" \
            --protocol tcp --port 1972 --cidr "$IP_CIDR"

        aws ec2 authorize-security-group-ingress \
            --group-id "$SG_ID" \
            --protocol tcp --port 52773 --cidr "$IP_CIDR"

        if [ "$USE_GPU" = true ]; then
            aws ec2 authorize-security-group-ingress \
                --group-id "$SG_ID" \
                --protocol tcp --port 8000 --cidr "$IP_CIDR"
        fi
    fi

    echo "✅ Security group rules configured"
else
    echo "✅ Using existing security group: $SG_ID"
fi

echo ""

# Get default VPC subnet
echo "Getting default subnet..."
SUBNET_ID=$(aws ec2 describe-subnets \
    --filters "Name=default-for-az,Values=true" \
    --query 'Subnets[0].SubnetId' \
    --output text)
echo "Subnet: $SUBNET_ID"
echo ""

# Launch instance
echo "Launching EC2 instance..."
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id "$AMI_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --key-name "$KEY_NAME" \
    --security-group-ids "$SG_ID" \
    --subnet-id "$SUBNET_ID" \
    --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":100,"VolumeType":"gp3","DeleteOnTermination":false}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME},{Key=Project,Value=FHIR-AI}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo "✅ Instance launched: $INSTANCE_ID"
echo ""

# Wait for instance to be running
echo "Waiting for instance to start (this may take 1-2 minutes)..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

# Get public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "✅ Instance running at: $PUBLIC_IP"
echo ""

# Wait for SSH to be available
echo "Waiting for SSH to be available..."
sleep 30

# SSH into instance and set up Docker + stack
echo ""
echo "Setting up Docker and FHIR stack..."
echo ""

ssh -i "${KEY_NAME}.pem" -o StrictHostKeyChecking=no ubuntu@"$PUBLIC_IP" << 'ENDSSH'
set -e

echo "Updating system..."
sudo apt-get update -qq

echo "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker ubuntu
    rm get-docker.sh
fi

echo "Installing docker-compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

echo "✅ Docker and docker-compose installed"

# Create project directory
mkdir -p ~/fhir-ai-hackathon
cd ~/fhir-ai-hackathon

echo "✅ Project directory created at ~/fhir-ai-hackathon"
echo ""
echo "Next steps:"
echo "1. Copy docker-compose.aws.yml to the instance"
echo "2. Copy any necessary project files"
echo "3. Start the stack with: docker-compose -f docker-compose.aws.yml up -d"
ENDSSH

echo ""
echo "========================================"
echo "EC2 Instance Ready!"
echo "========================================"
echo ""
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Instance Type: $INSTANCE_TYPE"
echo "GPU Support: $USE_GPU"
echo ""
echo "IRIS Management Portal: http://$PUBLIC_IP:52773/csp/sys/UtilHome.csp"
echo "Credentials: _SYSTEM / ISCDEMO"
echo ""
echo "SSH into instance:"
echo "  ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Copy project files to instance:"
echo "  scp -i ${KEY_NAME}.pem docker-compose.aws.yml ubuntu@$PUBLIC_IP:~/fhir-ai-hackathon/"
echo "  scp -i ${KEY_NAME}.pem -r src/ ubuntu@$PUBLIC_IP:~/fhir-ai-hackathon/"
echo ""
echo "Start IRIS on instance:"
echo "  ssh -i ${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
echo "  cd ~/fhir-ai-hackathon"
echo "  docker-compose -f docker-compose.aws.yml up -d"
echo ""
echo "Save instance details to .env:"
echo "  echo 'FHIR_STACK_INSTANCE_ID=$INSTANCE_ID' >> .env"
echo "  echo 'FHIR_STACK_PUBLIC_IP=$PUBLIC_IP' >> .env"
echo ""
echo "To stop instance later (save costs):"
echo "  aws ec2 stop-instances --instance-ids $INSTANCE_ID"
echo ""
echo "To start instance later:"
echo "  aws ec2 start-instances --instance-ids $INSTANCE_ID"
echo ""
