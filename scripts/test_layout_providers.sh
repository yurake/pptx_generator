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

default_providers=("azure")
cards_path=".pptx/prepare/prepare_card.json"
brief_log_path=".pptx/prepare/brief_log.json"
brief_meta_path=".pptx/prepare/ai_generation_meta.json"
providers=()

print_usage() {
  cat <<USAGE
Usage: scripts/test_layout_providers.sh [options] [provider ...]

Options:
  --cards <path>       使用する prepare_card.json のパス (既定: ${cards_path})
  --brief-log <path>   使用する brief_log.json のパス (既定: ${brief_log_path})
  --brief-meta <path>  使用する ai_generation_meta.json のパス (既定: ${brief_meta_path})
  -h, --help           このヘルプを表示

引数にプロバイダーを指定しない場合は ${default_providers[*]} を実行します。
指定した場合はその順に実行します。
USAGE
}

while [[ ${#} -gt 0 ]]; do
  case "${1}" in
    -h|--help)
      print_usage
      exit 0
      ;;
    --cards)
      if [[ ${#} -lt 2 ]]; then
        echo "[layout-providers] --cards requires a path" >&2
        exit 2
      fi
      cards_path="${2}"
      shift 2
      ;;
    --brief-log)
      if [[ ${#} -lt 2 ]]; then
        echo "[layout-providers] --brief-log requires a path" >&2
        exit 2
      fi
      brief_log_path="${2}"
      shift 2
      ;;
    --brief-meta)
      if [[ ${#} -lt 2 ]]; then
        echo "[layout-providers] --brief-meta requires a path" >&2
        exit 2
      fi
      brief_meta_path="${2}"
      shift 2
      ;;
    --*)
      echo "[layout-providers] 未知のオプションです: ${1}" >&2
      print_usage >&2
      exit 2
      ;;
    *)
      providers+=("${1}")
      shift
      ;;
  esac
done

if [[ ${#providers[@]} -eq 0 ]]; then
  providers=("${default_providers[@]}")
fi

for provider in "${providers[@]}"; do
  case "${provider}" in
    openai|azure|anthropic|aws-claude)
      ;;
    *)
      echo "[layout-providers] 未対応のプロバイダーが指定されました: ${provider}" >&2
      print_usage >&2
      exit 2
      ;;
  esac
done

for provider in "${providers[@]}"; do
  echo "=== Testing provider: ${provider} ==="
  PPTX_LLM_PROVIDER="${provider}" \
    uv run pptx --debug compose \
      .pptx/extract/jobspec.json \
      --brief-cards "${cards_path}" \
      --brief-log "${brief_log_path}" \
      --brief-meta "${brief_meta_path}" \
      --layouts .pptx/extract/layouts.jsonl || {
      echo "provider ${provider} failed" >&2
      exit 1
    }
done
