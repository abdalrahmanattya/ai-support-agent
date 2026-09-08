#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
uv_bin="${project_dir}/.tools/bin/uv"
build_dir="${project_dir}/.build"

if [[ ! -x "${uv_bin}" ]]; then
  python3 -m pip install --quiet --prefix "${project_dir}/.tools" uv
fi

"${uv_bin}" lock
"${uv_bin}" sync --frozen --all-groups
rm -rf "${build_dir}/runtime" "${build_dir}/lambda"
mkdir -p "${build_dir}/runtime" "${build_dir}/lambda/lambdas" "${build_dir}/lambda/support_agent"

"${uv_bin}" export --quiet --frozen --no-dev --no-emit-project --format requirements-txt \
  --output-file "${build_dir}/runtime-requirements.txt"
"${uv_bin}" pip install --quiet --target "${build_dir}/runtime" \
  --python-platform aarch64-manylinux_2_28 --python-version 3.13 \
  --requirements "${build_dir}/runtime-requirements.txt"

cp "${project_dir}/main.py" "${build_dir}/runtime/main.py"
cp -R "${project_dir}/support_agent" "${build_dir}/runtime/support_agent"
find "${build_dir}/runtime" -type d -name __pycache__ -prune -exec rm -rf {} +

"${uv_bin}" pip install --quiet --target "${build_dir}/lambda" \
  --python-platform aarch64-manylinux_2_28 --python-version 3.13 'pydantic>=2.13,<3'
cp "${project_dir}/lambdas/"*.py "${build_dir}/lambda/lambdas/"
cp "${project_dir}/support_agent/__init__.py" "${build_dir}/lambda/support_agent/"
cp "${project_dir}/support_agent/schemas.py" "${build_dir}/lambda/support_agent/"
find "${build_dir}/lambda" -type d -name __pycache__ -prune -exec rm -rf {} +

(cd "${build_dir}/runtime" && zip -qr "${build_dir}/runtime.zip" .)
(cd "${build_dir}/lambda" && zip -qr "${build_dir}/orders.zip" .)
cp "${build_dir}/orders.zip" "${build_dir}/refunds.zip"

echo "Built Runtime and Lambda ARM64/Python 3.13 artifacts in ${build_dir}."
