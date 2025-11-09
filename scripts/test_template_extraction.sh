#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"

output_dir="${project_root}/temp/template-extraction-e2e"
rm -rf "${output_dir}"
mkdir -p "${output_dir}"

export UV_CACHE_DIR="${UV_CACHE_DIR:-.uv-cache}"

uv run pptx template "${project_root}/samples/templates/templates.pptx" --output "${output_dir}" >/tmp/template-extraction.log 2>&1 || {
  cat /tmp/template-extraction.log >&2
  echo "[template-extraction] uv run pptx template failed" >&2
  exit 1
}

python3 - <<'PY' "${output_dir}"
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
layouts_path = output_dir / "layouts.jsonl"
diagnostics_path = output_dir / "diagnostics.json"

if not layouts_path.exists():
    sys.exit("layouts.jsonl が生成されていません")

target_layout = None
with layouts_path.open(encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if payload.get("layout_id") == "one_column_detail":
            target_layout = payload
            break

if target_layout is None:
    sys.exit("one_column_detail レイアウトが抽出結果に存在しません")

usage_tags = target_layout.get("usage_tags", [])
if usage_tags != ["content"]:
    sys.exit(f"one_column_detail の usage_tags が期待と異なります: {usage_tags}")

if not diagnostics_path.exists():
    sys.exit("diagnostics.json が生成されていません")

diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
if diagnostics.get("errors"):
    sys.exit(f"テンプレート抽出でエラーが検出されました: {diagnostics['errors']}")
PY

echo "Template extraction test passed."
