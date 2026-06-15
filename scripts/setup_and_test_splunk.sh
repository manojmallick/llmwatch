#!/usr/bin/env bash
# © 2026 Manoj Mallick. LLMWatch — one-command Splunk setup + test.
#
# Creates an HEC token for index=llmwatch, seeds LLM telemetry (with a v2.3
# regression), and verifies the key dashboard queries against live data.
#
# Usage (run from the llmwatch/ repo root; creds stay in YOUR shell only):
#   SPLUNK_USER=manoj SPLUNK_PASSWORD='***' bash scripts/setup_and_test_splunk.sh
set -euo pipefail

HOST=${SPLUNK_HOST:-localhost}
MGMT=${SPLUNK_MGMT:-https://$HOST:8089}
HEC=${SPLUNK_HEC_URL:-https://$HOST:8088/services/collector/event}
: "${SPLUNK_USER:?set SPLUNK_USER}"
: "${SPLUNK_PASSWORD:?set SPLUNK_PASSWORD}"
A=(-sk -u "$SPLUNK_USER:$SPLUNK_PASSWORD")

echo "▶ 1/4 enabling HEC + ensuring token 'llmwatch' (index=llmwatch)…"
curl "${A[@]}" "$MGMT/servicesNS/nobody/splunk_httpinput/data/inputs/http/http" -d disabled=0 >/dev/null 2>&1 || true
curl "${A[@]}" "$MGMT/servicesNS/nobody/splunk_httpinput/data/inputs/http" \
  -d name=llmwatch -d index=llmwatch -d indexes=llmwatch >/dev/null 2>&1 || true
TOKEN=$(curl "${A[@]}" \
  "$MGMT/servicesNS/nobody/splunk_httpinput/data/inputs/http/llmwatch?output_mode=json" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["entry"][0]["content"]["token"])')
echo "   token: ${TOKEN:0:8}…"

echo "▶ 2/4 seeding LLM telemetry (60 events + agent actions, v2.3 regression)…"
SPLUNK_HEC_TOKEN="$TOKEN" SPLUNK_HEC_URL="$HEC" python3 scripts/seed_splunk.py --events 60 --hours 30

echo "▶ 3/4 waiting for indexing…"; sleep 4

echo "▶ 4/4 verifying key panels:"
run() { curl "${A[@]}" -d output_mode=csv -d exec_mode=oneshot \
  --data-urlencode "search=$1" "$MGMT/services/search/jobs/export" | tail -n +2; }
printf "   • Total llm_events              : "; run 'search index=llmwatch sourcetype=llm_events | stats count as n | fields n'
printf "   • v2.3 avg groundedness (last 1h): "; run 'search index=llmwatch sourcetype=llm_events model_version="gemini-2.0-flash-v2.3" earliest=-1h | stats avg(groundedness_score) as g | eval g=round(g,2) | fields g'
printf "   • v2.2 avg groundedness         : "; run 'search index=llmwatch sourcetype=llm_events model_version="gemini-2.0-flash-v2.2" | stats avg(groundedness_score) as g | eval g=round(g,2) | fields g'
printf "   • agent actions logged          : "; run 'search index=llmwatch sourcetype=llm_agent_actions | stats count as n | fields n'

echo ""
echo "✅ Non-empty values above = dashboards will render. Now import them:"
echo "   SPLUNK_USER=$SPLUNK_USER SPLUNK_PASSWORD=*** bash scripts/import_dashboards.sh"
