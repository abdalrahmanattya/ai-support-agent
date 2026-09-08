#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_dir}"
if [[ ! -f .env.local ]]; then
  echo "Create .env.local from .env.example after deploying AWS resources." >&2
  exit 1
fi
set -a
source .env.local
set +a
exec .venv/bin/uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
