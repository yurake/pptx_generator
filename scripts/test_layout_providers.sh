#!/usr/bin/env bash
set -euo pipefail

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
