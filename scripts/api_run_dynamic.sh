#!/usr/bin/env bash

# Dynamic template → prepare → compose → gen を一気通貫で実行し、
# 各ジョブが succeeded になるまで待機する。失敗した時点で非0終了。

set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8000}
TOKEN=${TOKEN:-${PPTX_API_BEARER_TOKEN:-}}
TEMPLATE_PATH=${TEMPLATE_PATH:-samples/templates/dynamic_template.pptx}
PREPARE_SOURCE=${PREPARE_SOURCE:-samples/input/pitch.md}

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
      sleep 0.5
    else
      echo "job ${job_id} unexpected status: ${status}" >&2
      echo "$body" >&2
      return 1
    fi
  done
}

echo "[1/4] template"
tpl_resp=$(curl_json POST "${BASE_URL}/templates" \
  -d "{\"template_path\":\"${TEMPLATE_PATH}\",\"mode\":\"dynamic\"}")
echo "$tpl_resp"
tpl_job=$(echo "$tpl_resp" | jq -r .job_id)
tx=$(echo "$tpl_resp" | jq -r .transaction_id)
wait_job "$tpl_job"
echo ""

echo "[2/4] prepare"
prep_resp=$(curl_json POST "${BASE_URL}/prepare" \
  -d "{\"transaction_id\":\"${tx}\",\"prepare_sources\":[\"${PREPARE_SOURCE}\"],\"mode\":\"dynamic\"}")
echo "$prep_resp"
prep_job=$(echo "$prep_resp" | jq -r .job_id)
wait_job "$prep_job"
echo ""

echo "[3/4] compose"
cmp_resp=$(curl_json POST "${BASE_URL}/compose" -d "{\"transaction_id\":\"${tx}\"}")
echo "$cmp_resp"
cmp_job=$(echo "$cmp_resp" | jq -r .job_id)
wait_job "$cmp_job"
echo ""

echo "[4/4] gen"
gen_resp=$(curl_json POST "${BASE_URL}/gen" -d "{\"transaction_id\":\"${tx}\",\"export_pdf\":false}")
echo "$gen_resp"
gen_job=$(echo "$gen_resp" | jq -r .job_id)
wait_job "$gen_job"
echo ""

echo "done: transaction=${tx}"
