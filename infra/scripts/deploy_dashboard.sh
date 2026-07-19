#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --api-base-url HTTPS_ORIGIN [--stack-name NAME] [--profile PROFILE] [--region REGION]" >&2
}

api_base_url=""
stack_name="proofloop-dashboard-dev"
aws_profile="proofloop-deployer"
aws_region="ap-south-1"

while (($#)); do
  case "$1" in
    --api-base-url) api_base_url=${2:-}; shift 2 ;;
    --stack-name) stack_name=${2:-}; shift 2 ;;
    --profile) aws_profile=${2:-}; shift 2 ;;
    --region) aws_region=${2:-}; shift 2 ;;
    *) usage; exit 2 ;;
  esac
done

if [[ -z "$api_base_url" ]]; then
  usage
  exit 2
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repository_root=$(cd "$script_dir/../.." && pwd)
template="$repository_root/infra/web-template.yaml"
dashboard_dir="$repository_root/dashboard"
temporary_dir=$(mktemp -d "${TMPDIR:-/tmp}/proofloop-dashboard.XXXXXX")
trap 'rm -rf "$temporary_dir"' EXIT
account_id=$(aws sts get-caller-identity \
  --profile "$aws_profile" --region "$aws_region" --query Account --output text)
service_role_arn="arn:aws:iam::$account_id:role/ProofLoopDashboardCloudFormationServiceRole"

aws cloudformation validate-template \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --template-body "file://$template" >/dev/null

aws cloudformation deploy \
  --profile "$aws_profile" \
  --region "$aws_region" \
  --stack-name "$stack_name" \
  --template-file "$template" \
  --role-arn "$service_role_arn" \
  --parameter-overrides "ApiBaseUrl=$api_base_url" \
  --no-fail-on-empty-changeset >/dev/null

dashboard_bucket=$(aws cloudformation describe-stacks \
  --profile "$aws_profile" --region "$aws_region" --stack-name "$stack_name" \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardBucketName'].OutputValue | [0]" \
  --output text)
distribution_id=$(aws cloudformation describe-stacks \
  --profile "$aws_profile" --region "$aws_region" --stack-name "$stack_name" \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardDistributionId'].OutputValue | [0]" \
  --output text)
dashboard_url=$(aws cloudformation describe-stacks \
  --profile "$aws_profile" --region "$aws_region" --stack-name "$stack_name" \
  --query "Stacks[0].Outputs[?OutputKey=='DashboardUrl'].OutputValue | [0]" \
  --output text)

python3 "$script_dir/render_dashboard_runtime_config.py" \
  "$api_base_url" "$temporary_dir/runtime-config.js"

aws s3 sync "$dashboard_dir" "s3://$dashboard_bucket" \
  --profile "$aws_profile" --region "$aws_region" --delete \
  --exclude "runtime-config.js" --exclude ".DS_Store" \
  --cache-control "public,max-age=300,must-revalidate" \
  --only-show-errors
aws s3 cp "$dashboard_dir/index.html" "s3://$dashboard_bucket/index.html" \
  --profile "$aws_profile" --region "$aws_region" \
  --content-type "text/html; charset=utf-8" \
  --cache-control "no-cache,max-age=0,must-revalidate" \
  --only-show-errors
aws s3 cp "$temporary_dir/runtime-config.js" "s3://$dashboard_bucket/runtime-config.js" \
  --profile "$aws_profile" --region "$aws_region" \
  --content-type "application/javascript; charset=utf-8" \
  --cache-control "no-store,max-age=0" \
  --only-show-errors
aws cloudfront create-invalidation \
  --profile "$aws_profile" \
  --distribution-id "$distribution_id" \
  --paths "/*" >/dev/null

printf '%s\n' "$dashboard_url"
