#!/usr/bin/env bash
set -euo pipefail

stack_name="proofloop-dashboard-dev"
aws_profile="proofloop-deployer"
aws_region="ap-south-1"

while (($#)); do
  case "$1" in
    --stack-name) stack_name=${2:-}; shift 2 ;;
    --profile) aws_profile=${2:-}; shift 2 ;;
    --region) aws_region=${2:-}; shift 2 ;;
    *) echo "Usage: $0 [--stack-name NAME] [--profile PROFILE] [--region REGION]" >&2; exit 2 ;;
  esac
done

dashboard_bucket=$(aws cloudformation describe-stacks \
  --profile "$aws_profile" --region "$aws_region" --stack-name "$stack_name" \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardBucketName'].OutputValue | [0]" \
  --output text)

aws s3 rm "s3://$dashboard_bucket" \
  --profile "$aws_profile" --region "$aws_region" --recursive --only-show-errors
aws cloudformation delete-stack \
  --profile "$aws_profile" --region "$aws_region" --stack-name "$stack_name"
aws cloudformation wait stack-delete-complete \
  --profile "$aws_profile" --region "$aws_region" --stack-name "$stack_name"

printf 'Deleted dashboard stack %s.\n' "$stack_name"
