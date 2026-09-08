#!/usr/bin/env bash
set -euo pipefail

region="${AWS_REGION:-}"
if [[ "${region}" != "us-east-1" ]]; then
  echo "AWS_REGION must be us-east-1; source refresh-credentials.sh first." >&2
  exit 1
fi

account_id="$(aws sts get-caller-identity --query Account --output text)"
caller_arn="$(aws sts get-caller-identity --query Arn --output text)"

if [[ -n "${EXPECTED_AWS_ACCOUNT_ID:-}" && "${account_id}" != "${EXPECTED_AWS_ACCOUNT_ID}" ]]; then
  echo "AWS account does not match EXPECTED_AWS_ACCOUNT_ID." >&2
  exit 1
fi

if [[ -n "${EXPECTED_AWS_ROLE_NAME:-}" \
  && "${caller_arn}" != *":assumed-role/${EXPECTED_AWS_ROLE_NAME}/"* ]]; then
  echo "AWS role does not match EXPECTED_AWS_ROLE_NAME." >&2
  exit 1
fi

aws cloudformation list-stacks --max-items 1 >/dev/null
aws bedrock-agentcore-control list-agent-runtimes --max-results 1 >/dev/null
aws bedrock-agent list-knowledge-bases --max-results 1 >/dev/null
aws s3vectors list-vector-buckets --max-results 1 >/dev/null
aws lambda list-functions --max-items 1 >/dev/null
aws apigateway get-rest-apis --limit 1 >/dev/null
echo "AWS preflight passed in us-east-1."
