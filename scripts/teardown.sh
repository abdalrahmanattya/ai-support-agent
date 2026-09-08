#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
region="us-east-1"
"${project_dir}/scripts/preflight.sh"

bucket="$(aws cloudformation describe-stacks --region "${region}" \
  --stack-name ai-support-agent-bootstrap \
  --query 'Stacks[0].Outputs[?OutputKey==`ArtifactBucketName`].OutputValue' \
  --output text 2>/dev/null || true)"

for component in runtime tools data; do
  stack="ai-support-agent-${component}"
  if aws cloudformation describe-stacks --region "${region}" --stack-name "${stack}" >/dev/null 2>&1; then
    aws cloudformation delete-stack --region "${region}" --stack-name "${stack}"
    aws cloudformation wait stack-delete-complete --region "${region}" --stack-name "${stack}"
  fi
done

if [[ -n "${bucket}" && "${bucket}" != "None" ]]; then
  aws s3 rm "s3://${bucket}" --recursive --only-show-errors
  manifest="$(mktemp)"
  aws s3api list-object-versions --bucket "${bucket}" \
    | jq '{Objects: ([.Versions[]?, .DeleteMarkers[]?] | map({Key, VersionId})), Quiet: true}' >"${manifest}"
  if jq -e '.Objects | length > 0' "${manifest}" >/dev/null; then
    aws s3api delete-objects --bucket "${bucket}" --delete "file://${manifest}"
  fi
  aws s3api delete-bucket --bucket "${bucket}" --region "${region}"
  rm "${manifest}"
fi

for component in bootstrap identity; do
  stack="ai-support-agent-${component}"
  if aws cloudformation describe-stacks --region "${region}" --stack-name "${stack}" >/dev/null 2>&1; then
    aws cloudformation delete-stack --region "${region}" --stack-name "${stack}"
    aws cloudformation wait stack-delete-complete --region "${region}" --stack-name "${stack}"
  fi
done

echo "Stack deletion completed. Run a tagged-resource and log-group audit before closing the AWS cycle."
