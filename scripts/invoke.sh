#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
outputs="${project_dir}/.evidence/stack-outputs.json"
prompt="${1:-What can you help me with?}"
customer_id="${2:-CUST-123}"
session_id="${3:-$(uuidgen | tr '[:upper:]' '[:lower:]')}"
runtime_session_id="$(uuidgen | tr '[:upper:]' '[:lower:]')"
runtime_arn="$(jq -r '.[] | select(.OutputKey=="RuntimeArn") | .OutputValue' "${outputs}")"
payload="$(jq -nc --arg prompt "${prompt}" --arg customer_id "${customer_id}" --arg session_id "${session_id}" '{prompt:$prompt,customer_id:$customer_id,session_id:$session_id}')"

aws bedrock-agentcore invoke-agent-runtime \
  --region us-east-1 \
  --cli-binary-format raw-in-base64-out \
  --agent-runtime-arn "${runtime_arn}" \
  --runtime-session-id "${runtime_session_id}" \
  --qualifier DEFAULT \
  --payload "${payload}" \
  /dev/stdout
