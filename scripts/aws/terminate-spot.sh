#!/bin/bash
set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-PowerUserPlusAccess-122293094970}"
REGION="${AWS_REGION:-us-east-1}"

if [ $# -eq 0 ]; then
    echo "Usage: $0 <instance-id>"
    echo ""
    echo "List running spot instances:"
    aws ec2 describe-instances \
        --filters "Name=instance-lifecycle,Values=spot" "Name=instance-state-name,Values=running" \
        --query 'Reservations[*].Instances[*].[InstanceId,PublicIpAddress,Tags[?Key==`Name`].Value|[0]]' \
        --output table \
        --region "$REGION" \
        --profile "$AWS_PROFILE"
    exit 1
fi

INSTANCE_ID="$1"

echo "Terminating spot instance: $INSTANCE_ID"

aws ec2 terminate-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --profile "$AWS_PROFILE" \
    --query 'TerminatingInstances[0].CurrentState.Name' \
    --output text

echo "Instance terminated. EBS volume deleted automatically."
