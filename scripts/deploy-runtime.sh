#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${project_dir}/.build"
evidence_dir="${project_dir}/.evidence"
region="us-east-1"

"${project_dir}/scripts/preflight.sh"
"${project_dir}/scripts/build.sh"
bucket="$(aws cloudformation describe-stacks --stack-name ai-support-agent-bootstrap \
  --query 'Stacks[0].Outputs[?OutputKey==`ArtifactBucketName`].OutputValue' --output text)"
source_hash="$(shasum -a 256 "${build_dir}/runtime.zip" | cut -d' ' -f1)"
runtime_key="artifacts/${source_hash}/runtime.zip"
aws s3 cp "${build_dir}/runtime.zip" "s3://${bucket}/${runtime_key}" --only-show-errors

aws cloudformation describe-stacks --stack-name ai-support-agent-data \
  --query 'Stacks[0].Outputs' --output json >"${evidence_dir}/data-outputs.json"
aws cloudformation describe-stacks --stack-name ai-support-agent-tools \
  --query 'Stacks[0].Outputs' --output json >"${evidence_dir}/tools-outputs.json"
knowledge_base_id="$(jq -r '.[] | select(.OutputKey=="KnowledgeBaseId") | .OutputValue' "${evidence_dir}/data-outputs.json")"
knowledge_base_arn="$(jq -r '.[] | select(.OutputKey=="KnowledgeBaseArn") | .OutputValue' "${evidence_dir}/data-outputs.json")"
memory_id="$(jq -r '.[] | select(.OutputKey=="MemoryId") | .OutputValue' "${evidence_dir}/data-outputs.json")"
gateway_url="$(jq -r '.[] | select(.OutputKey=="GatewayUrl") | .OutputValue' "${evidence_dir}/tools-outputs.json")"

aws cloudformation deploy \
  --region "${region}" \
  --stack-name ai-support-agent-runtime \
  --template-file "${project_dir}/infrastructure/runtime.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    ArtifactBucket="${bucket}" RuntimeCodeKey="${runtime_key}" \
    GatewayUrl="${gateway_url}" KnowledgeBaseId="${knowledge_base_id}" \
    KnowledgeBaseArn="${knowledge_base_arn}" MemoryId="${memory_id}"

aws cloudformation describe-stacks --stack-name ai-support-agent-runtime \
  --query 'Stacks[0].Outputs' --output json >"${evidence_dir}/runtime-outputs.json"
jq -s 'add' "${evidence_dir}/data-outputs.json" "${evidence_dir}/tools-outputs.json" \
  "${evidence_dir}/runtime-outputs.json" >"${evidence_dir}/stack-outputs.json"
echo "Runtime stack updated without rebuilding data or tool stacks."
