#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${project_dir}/.build"
evidence_dir="${project_dir}/.evidence"
region="us-east-1"

"${project_dir}/scripts/preflight.sh"
"${project_dir}/scripts/build.sh"
mkdir -p "${evidence_dir}"

aws cloudformation deploy \
  --region "${region}" \
  --stack-name ai-support-agent-bootstrap \
  --template-file "${project_dir}/infrastructure/bootstrap.yaml" \
  --no-fail-on-empty-changeset

bucket="$(aws cloudformation describe-stacks --region "${region}" \
  --stack-name ai-support-agent-bootstrap \
  --query 'Stacks[0].Outputs[?OutputKey==`ArtifactBucketName`].OutputValue' --output text)"
source_hash="$(shasum -a 256 "${build_dir}/runtime.zip" "${build_dir}/orders.zip" "${build_dir}/refunds.zip" | shasum -a 256 | cut -d' ' -f1)"
runtime_key="artifacts/${source_hash}/runtime.zip"
order_key="artifacts/${source_hash}/orders.zip"
refund_key="artifacts/${source_hash}/refunds.zip"

aws s3 cp "${build_dir}/runtime.zip" "s3://${bucket}/${runtime_key}" --only-show-errors
aws s3 cp "${build_dir}/orders.zip" "s3://${bucket}/${order_key}" --only-show-errors
aws s3 cp "${build_dir}/refunds.zip" "s3://${bucket}/${refund_key}" --only-show-errors
aws s3 cp "${project_dir}/knowledge/circuitcare-support.md" \
  "s3://${bucket}/knowledge/circuitcare-support.md" --only-show-errors

aws cloudformation deploy \
  --region "${region}" \
  --stack-name ai-support-agent-data \
  --template-file "${project_dir}/infrastructure/data.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    ArtifactBucket="${bucket}"

aws cloudformation describe-stacks --region "${region}" --stack-name ai-support-agent-data \
  --query 'Stacks[0].Outputs' --output json >"${evidence_dir}/data-outputs.json"
knowledge_base_id="$(jq -r '.[] | select(.OutputKey=="KnowledgeBaseId") | .OutputValue' "${evidence_dir}/data-outputs.json")"
knowledge_base_arn="$(jq -r '.[] | select(.OutputKey=="KnowledgeBaseArn") | .OutputValue' "${evidence_dir}/data-outputs.json")"
data_source_id="$(jq -r '.[] | select(.OutputKey=="DataSourceId") | .OutputValue' "${evidence_dir}/data-outputs.json")"
memory_id="$(jq -r '.[] | select(.OutputKey=="MemoryId") | .OutputValue' "${evidence_dir}/data-outputs.json")"

aws cloudformation deploy \
  --region "${region}" \
  --stack-name ai-support-agent-tools \
  --template-file "${project_dir}/infrastructure/tools.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    ArtifactBucket="${bucket}" \
    OrderCodeKey="${order_key}" \
    RefundCodeKey="${refund_key}"

aws cloudformation describe-stacks --region "${region}" --stack-name ai-support-agent-tools \
  --query 'Stacks[0].Outputs' --output json >"${evidence_dir}/tools-outputs.json"
gateway_url="$(jq -r '.[] | select(.OutputKey=="GatewayUrl") | .OutputValue' "${evidence_dir}/tools-outputs.json")"

aws cloudformation deploy \
  --region "${region}" \
  --stack-name ai-support-agent-runtime \
  --template-file "${project_dir}/infrastructure/runtime.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    ArtifactBucket="${bucket}" \
    RuntimeCodeKey="${runtime_key}" \
    GatewayUrl="${gateway_url}" \
    KnowledgeBaseId="${knowledge_base_id}" \
    KnowledgeBaseArn="${knowledge_base_arn}" \
    MemoryId="${memory_id}"

aws cloudformation describe-stacks --region "${region}" --stack-name ai-support-agent-runtime \
  --query 'Stacks[0].Outputs' --output json >"${evidence_dir}/runtime-outputs.json"
jq -s 'add' "${evidence_dir}/data-outputs.json" "${evidence_dir}/tools-outputs.json" \
  "${evidence_dir}/runtime-outputs.json" >"${evidence_dir}/stack-outputs.json"

job_id="$(aws bedrock-agent start-ingestion-job --region "${region}" \
  --knowledge-base-id "${knowledge_base_id}" --data-source-id "${data_source_id}" \
  --query ingestionJob.ingestionJobId --output text)"
while true; do
  status="$(aws bedrock-agent get-ingestion-job --region "${region}" \
    --knowledge-base-id "${knowledge_base_id}" --data-source-id "${data_source_id}" \
    --ingestion-job-id "${job_id}" --query ingestionJob.status --output text)"
  case "${status}" in
    COMPLETE) break ;;
    FAILED|STOPPED) echo "Knowledge ingestion ended with ${status}." >&2; exit 1 ;;
    *) sleep 10 ;;
  esac
done

echo "Four-stack deployment and knowledge ingestion completed."
echo "Combined outputs: ${evidence_dir}/stack-outputs.json"
