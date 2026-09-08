#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export AWS_EC2_METADATA_DISABLED=true
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-local-check}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-local-check}"

if [[ "$("${project_dir}/.venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.13" ]]; then
  echo "Run scripts/build.sh to create the required Python 3.13 environment." >&2
  exit 1
fi

"${project_dir}/.venv/bin/pytest" -q
"${project_dir}/.venv/bin/ruff" check "${project_dir}"
"${project_dir}/.venv/bin/mypy" \
  "${project_dir}/main.py" "${project_dir}/support_agent" "${project_dir}/lambdas" \
  "${project_dir}/domain" "${project_dir}/apps/api"
"${project_dir}/.venv/bin/cfn-lint" "${project_dir}"/infrastructure/*.yaml
npm --prefix "${project_dir}/apps/web" test
npm --prefix "${project_dir}/apps/web" run lint
npm --prefix "${project_dir}/apps/web" run build
