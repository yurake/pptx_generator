#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
env_file="${project_root}/.env"

if [[ -f "${env_file}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
else
  echo "[layout-providers] .env が存在しないためスキップします" >&2
  exit 0
fi

export UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"
mkdir -p "${UV_CACHE_DIR}"

providers=("openai" "azure" "anthropic" "aws-claude")

for provider in "${providers[@]}"; do
  echo "=== Testing provider: ${provider} ==="
  PPTX_LLM_PROVIDER="${provider}" \
    uv run pptx --debug compose \
      .pptx/extract/jobspec.json \
      --brief-cards .pptx/prepare/prepare_card.json \
      --layouts .pptx/extract/layouts.jsonl || {
      echo "provider ${provider} failed" >&2
      exit 1
    }
done
