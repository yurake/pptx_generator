#!/usr/bin/env bash

# edit を API 経由で実行し、succeeded まで待機して成果物 PPTX をダウンロードする。
# 前提: /edit エンドポイント実装済み、Bearer 認証（または HMAC）設定済み。

set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
TOKEN=${TOKEN:-${PPTX_API_BEARER_TOKEN:-}}
PPTX_PATH=${PPTX_PATH:-samples/templates/edit_sample.pptx}
EDITS_JSON=${EDITS_JSON:-}  # 指定すると LLM を呼ばずに適用
OUTPUT=${OUTPUT:-}          # 任意指定。省略時はサーバ側既定

if [[ -z "${TOKEN}" ]]; then
  echo "TOKEN (または PPTX_API_BEARER_TOKEN) を設定してください" >&2
  exit 1
fi

curl_json() {
  local method=$1; shift
  local url=$1; shift
  curl -sS -X "${method}" "${url}" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    "$@"
}

wait_job() {
  local job_id=$1
  while true; do
    local body status
    body=$(curl_json GET "${BASE_URL}/jobs/${job_id}")
    status=$(echo "$body" | jq -r '.status')
    if [[ "$status" == "succeeded" ]]; then
      echo "job ${job_id} succeeded"
      echo "$body"
      return 0
    elif [[ "$status" == "failed" ]]; then
      echo "job ${job_id} failed" >&2
      echo "$body" >&2
      return 1
    elif [[ "$status" == "pending" || "$status" == "running" ]]; then
      sleep 1
    else
      echo "job ${job_id} unexpected status: ${status}" >&2
      echo "$body" >&2
      return 1
    fi
  done
}

payload="{\"pptx_path\":\"${PPTX_PATH}\""
if [[ -n "${EDITS_JSON}" ]]; then
  payload+=",\"edits_json\":\"${EDITS_JSON}\""
fi
if [[ -n "${OUTPUT}" ]]; then
  payload+=",\"output\":\"${OUTPUT}\""
fi
payload+="}"

echo "[1/1] edit"
edit_resp=$(curl_json POST "${BASE_URL}/edit" -d "${payload}")
echo "$edit_resp"
edit_job=$(echo "$edit_resp" | jq -r .job_id)
tx=$(echo "$edit_resp" | jq -r .transaction_id)
wait_job "$edit_job"
echo ""

pptx_url=$(echo "$edit_resp" | jq -r .artifacts.pptx_url)
if [[ -z "${pptx_url}" || "${pptx_url}" == "null" ]]; then
  pptx_url="/jobs/${edit_job}/artifacts/pptx"
fi

outfile="/tmp/${tx}_edit.pptx"
if curl -sS "${BASE_URL}${pptx_url}" -H "Authorization: Bearer ${TOKEN}" -o "${outfile}"; then
  size=$(stat -f%z "${outfile}" 2>/dev/null || stat -c%s "${outfile}" 2>/dev/null)
  echo "[ok] downloaded pptx size=${size:-unknown} -> ${outfile}"
else
  echo "[error] failed to download pptx" >&2
  exit 1
fi

echo "done: transaction=${tx}, job=${edit_job}"
