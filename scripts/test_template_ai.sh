#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"

template_path="${project_root}/samples/templates/templates.pptx"
policy_path="${project_root}/samples/policies/template_ai_mock.json"
output_dir="${project_root}/temp/template-ai-e2e"

if [[ ! -f "${template_path}" ]]; then
  echo "[template-ai] samples/templates/templates.pptx が見つかりません" >&2
  exit 0
fi
if [[ ! -f "${policy_path}" ]]; then
  echo "[template-ai] モックポリシーが存在しないためスキップします: ${policy_path}" >&2
  exit 0
fi

rm -rf "${output_dir}"
mkdir -p "${output_dir}"

export UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"
mkdir -p "${UV_CACHE_DIR}"

log_path="$(mktemp "${output_dir}/tpl-extract-XXXX.log")"

if ! uv run pptx tpl-extract \
  --template "${template_path}" \
  --output "${output_dir}" \
  --template-ai-policy "${policy_path}" \
  >"${log_path}" 2>&1; then
  cat "${log_path}" >&2
  echo "[template-ai] uv run pptx tpl-extract が失敗しました" >&2
  exit 1
fi

python3 - <<'PY' "${output_dir}"
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
layouts_path = output_dir / "layouts.jsonl"
diagnostics_path = output_dir / "diagnostics.json"

if not layouts_path.exists():
    sys.exit("[template-ai] layouts.jsonl が生成されていません")

summary_tags = None
with layouts_path.open(encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if payload.get("layout_id") == "executive_summary":
            summary_tags = payload.get("usage_tags")
            break

if summary_tags is None:
    sys.exit("[template-ai] executive_summary レイアウトが抽出結果に存在しません")

if ["content", "overview"] != summary_tags:
    sys.exit(f"[template-ai] executive_summary の usage_tags が期待と異なります: {summary_tags}")

if not diagnostics_path.exists():
    sys.exit("[template-ai] diagnostics.json が生成されていません")

diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
stats = diagnostics.get("stats", {})
if stats.get("template_ai_invoked", 0) == 0:
    sys.exit("[template-ai] template_ai_invoked が 0 のため AI が呼び出されていません")
if stats.get("template_ai_failed", 0) != 0:
    sys.exit("[template-ai] template_ai_failed が 0 ではありません")

entries = diagnostics.get("template_ai", [])
if not entries:
    sys.exit("[template-ai] diagnostics に template_ai エントリが記録されていません")

PY

echo "Template AI extraction test passed."
