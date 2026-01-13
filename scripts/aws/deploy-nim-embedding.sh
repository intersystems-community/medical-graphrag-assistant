#!/bin/bash
#
# Deploy NVIDIA NIM Embedding Service to AWS EC2
# Uses AWS Systems Manager Session Manager (no SSH key needed)
#
# Usage: ./deploy-nim-embedding.sh
#

set -e

INSTANCE_ID="i-0432eba10b98c4949"
AWS_PROFILE="AWS_ACCOUNT_ID_PowerUserPlusAccess"

echo "=========================================="
echo "NVIDIA NIM Embedding Service Deployment"
echo "=========================================="
echo "Instance: $INSTANCE_ID"
echo "Service: nv-embedqa-e5-v5 (1024-dim)"
echo "Port: 8080"
echo ""

# Deployment script to run on EC2
DEPLOY_SCRIPT='
#!/bin/bash
set -e

echo "→ Checking Docker status..."
sudo systemctl status docker --no-pager || sudo systemctl start docker

echo "→ Pulling NVIDIA NIM embedding image..."
# Use the NIM embedding container
# Note: This requires NGC API key set on the instance
sudo docker pull nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest || {
    echo "⚠️  Pull failed - checking if NGC_API_KEY is set..."
    if [ -z "$NGC_API_KEY" ]; then
        echo "❌ NGC_API_KEY not set. Please set it first:"
        echo "   export NGC_API_KEY=your_key_here"
        exit 1
    fi
}

echo "→ Stopping any existing NIM embedding container..."
sudo docker stop nim-embedding 2>/dev/null || true
sudo docker rm nim-embedding 2>/dev/null || true

echo "→ Starting NVIDIA NIM Embedding Service..."
sudo docker run -d \
    --name nim-embedding \
    --gpus all \
    --restart unless-stopped \
    -p 8080:8000 \
    -e NGC_API_KEY="${NGC_API_KEY}" \
    nvcr.io/nim/nvidia/nv-embedqa-e5-v5:latest

echo "→ Waiting for service to be ready..."
sleep 10

echo "→ Checking service status..."
sudo docker logs nim-embedding --tail 20

echo "→ Testing embedding endpoint..."
curl -s http://localhost:8080/v1/models || echo "Service starting up..."

echo ""
echo "✅ NVIDIA NIM Embedding Service deployed!"
echo "   Endpoint: http://3.84.250.46:8080/v1/embeddings"
echo "   Model: nvidia/nv-embedqa-e5-v5"
echo "   Dimensions: 1024"
'

echo "→ Sending deployment script to EC2 instance..."

# Use AWS SSM to run the script
AWS_PROFILE=$AWS_PROFILE aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters "commands=[\"$DEPLOY_SCRIPT\"]" \
    --output json \
    --query 'Command.CommandId' \
    --output text > /tmp/nim-deploy-command-id.txt

COMMAND_ID=$(cat /tmp/nim-deploy-command-id.txt)
echo "✅ Command sent: $COMMAND_ID"
echo ""
echo "→ Waiting for deployment to complete (this may take 2-3 minutes)..."

# Wait for command to complete
sleep 5
for i in {1..60}; do
    STATUS=$(AWS_PROFILE=$AWS_PROFILE aws ssm list-command-invocations \
        --command-id "$COMMAND_ID" \
        --details \
        --query 'CommandInvocations[0].Status' \
        --output text 2>/dev/null || echo "Pending")

    if [ "$STATUS" = "Success" ]; then
        echo "✅ Deployment successful!"
        break
    elif [ "$STATUS" = "Failed" ]; then
        echo "❌ Deployment failed!"
        AWS_PROFILE=$AWS_PROFILE aws ssm get-command-invocation \
            --command-id "$COMMAND_ID" \
            --instance-id "$INSTANCE_ID"
        exit 1
    fi

    echo "   Status: $STATUS (attempt $i/60)"
    sleep 5
done

echo ""
echo "→ Fetching deployment output..."
AWS_PROFILE=$AWS_PROFILE aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --query 'StandardOutputContent' \
    --output text

echo ""
echo "=========================================="
echo "✅ NVIDIA NIM Embedding Service Ready!"
echo "=========================================="
echo "Endpoint: http://3.84.250.46:8080/v1/embeddings"
echo "Model: nvidia/nv-embedqa-e5-v5"
echo "Dimensions: 1024"
echo ""
echo "Test with:"
echo "curl -X POST http://3.84.250.46:8080/v1/embeddings \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"input\": \"test\", \"model\": \"nvidia/nv-embedqa-e5-v5\"}'"
