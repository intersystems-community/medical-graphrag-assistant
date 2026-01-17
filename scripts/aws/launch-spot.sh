#!/bin/bash
set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-PowerUserPlusAccess-122293094970}"
INSTANCE_TYPE="${INSTANCE_TYPE:-g5.xlarge}"
REGION="${AWS_REGION:-us-east-1}"
KEY_NAME="${KEY_NAME:-fhir-ai-key-recovery}"
MAX_PRICE="${MAX_PRICE:-0.50}"

AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*" \
              "Name=state,Values=available" \
              "Name=architecture,Values=x86_64" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE")

if [ -z "$AMI_ID" ] || [ "$AMI_ID" = "None" ]; then
    echo "Error: Could not find Deep Learning AMI" >&2
    exit 1
fi

VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE")

SUBNET_ID=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query 'Subnets[0].SubnetId' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE")

SG_NAME="fhir-graphrag-spot-sg"
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE" 2>/dev/null || echo "None")

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
    echo "Creating security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name "$SG_NAME" \
        --description "FHIR GraphRAG spot instance" \
        --vpc-id "$VPC_ID" \
        --query 'GroupId' \
        --output text \
        --region "$REGION" \
        --profile "$AWS_PROFILE")
    
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp --port 22 --cidr 0.0.0.0/0 \
        --region "$REGION" --profile "$AWS_PROFILE" >/dev/null
    
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp --port 1972 --cidr 0.0.0.0/0 \
        --region "$REGION" --profile "$AWS_PROFILE" >/dev/null
    
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp --port 52773 --cidr 0.0.0.0/0 \
        --region "$REGION" --profile "$AWS_PROFILE" >/dev/null
    
    aws ec2 authorize-security-group-ingress \
        --group-id "$SG_ID" \
        --protocol tcp --port 8001-8002 --cidr 0.0.0.0/0 \
        --region "$REGION" --profile "$AWS_PROFILE" >/dev/null
fi

echo "Requesting spot instance..."
echo "  Type: $INSTANCE_TYPE"
echo "  AMI: $AMI_ID"
echo "  Max price: \$$MAX_PRICE/hour"

SPOT_REQUEST_ID=$(aws ec2 request-spot-instances \
    --instance-count 1 \
    --type "one-time" \
    --launch-specification "{
        \"ImageId\": \"$AMI_ID\",
        \"InstanceType\": \"$INSTANCE_TYPE\",
        \"KeyName\": \"$KEY_NAME\",
        \"SecurityGroupIds\": [\"$SG_ID\"],
        \"SubnetId\": \"$SUBNET_ID\",
        \"BlockDeviceMappings\": [{
            \"DeviceName\": \"/dev/sda1\",
            \"Ebs\": {\"VolumeSize\": 100, \"VolumeType\": \"gp3\", \"DeleteOnTermination\": true}
        }]
    }" \
    --spot-price "$MAX_PRICE" \
    --query 'SpotInstanceRequests[0].SpotInstanceRequestId' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE")

echo "Spot request: $SPOT_REQUEST_ID"
echo "Waiting for fulfillment..."

for i in {1..30}; do
    STATUS=$(aws ec2 describe-spot-instance-requests \
        --spot-instance-request-ids "$SPOT_REQUEST_ID" \
        --query 'SpotInstanceRequests[0].Status.Code' \
        --output text \
        --region "$REGION" \
        --profile "$AWS_PROFILE")
    
    if [ "$STATUS" = "fulfilled" ]; then
        break
    elif [ "$STATUS" = "price-too-low" ] || [ "$STATUS" = "capacity-not-available" ]; then
        echo "Error: $STATUS" >&2
        exit 1
    fi
    sleep 5
done

INSTANCE_ID=$(aws ec2 describe-spot-instance-requests \
    --spot-instance-request-ids "$SPOT_REQUEST_ID" \
    --query 'SpotInstanceRequests[0].InstanceId' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE")

aws ec2 create-tags \
    --resources "$INSTANCE_ID" \
    --tags "Key=Name,Value=fhir-graphrag-spot" \
    --region "$REGION" \
    --profile "$AWS_PROFILE"

echo "Waiting for instance to run..."
aws ec2 wait instance-running \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --profile "$AWS_PROFILE"

PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE")

SPOT_PRICE=$(aws ec2 describe-spot-price-history \
    --instance-types "$INSTANCE_TYPE" \
    --product-descriptions "Linux/UNIX" \
    --max-items 1 \
    --query 'SpotPriceHistory[0].SpotPrice' \
    --output text \
    --region "$REGION" \
    --profile "$AWS_PROFILE")

echo ""
echo "========================================"
echo "Spot Instance Ready"
echo "========================================"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP:   $PUBLIC_IP"
echo "Spot Price:  \$$SPOT_PRICE/hour (vs \$1.006 on-demand)"
echo ""
echo "Connect:"
echo "  ssh -i ~/.ssh/${KEY_NAME}.pem ubuntu@$PUBLIC_IP"
echo ""
echo "Set environment:"
echo "  export EC2_HOST=$PUBLIC_IP"
echo ""
echo "Health check:"
echo "  EC2_HOST=$PUBLIC_IP python -m src.cli --env aws check-health"
echo ""
echo "Terminate when done:"
echo "  ./scripts/aws/terminate-spot.sh $INSTANCE_ID"
