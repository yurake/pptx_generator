#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "${BASE_DIR}/.env" ]]; then
  echo "[ERROR] .env が見つかりません。scripts/export_sonar_issues.py 実行前に .env を作成してください。" >&2
  exit 1
fi

cd "${BASE_DIR}"

uv run --with requests --with python-dotenv python scripts/export_sonar_issues.py "$@"
