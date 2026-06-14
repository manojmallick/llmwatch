#!/usr/bin/env bash
# © 2026 LearnHubPlay BV. LLMWatch — one-command live run against real Splunk.
#
#   SPLUNK_USER=manoj SPLUNK_PASSWORD=*** ./run_live.sh
#
# Enables HEC + creates the token, then seeds events, runs the agent against
# live SPL, and prints the audit row read back from Splunk.
set -euo pipefail
cd "$(dirname "$0")"

: "${SPLUNK_USER:?set SPLUNK_USER}"
: "${SPLUNK_PASSWORD:?set SPLUNK_PASSWORD}"
export SPLUNK_REST_URL="${SPLUNK_REST_URL:-https://localhost:8089}"

echo "▶ 1/2  Splunk setup (index + HEC + token)"
TOKEN="$(python3 scripts/setup_splunk.py 2>/dev/null | sed -n 's/^HEC_TOKEN=//p')"
if [ -z "${TOKEN}" ]; then echo "setup failed — run scripts/setup_splunk.py directly to see why"; exit 1; fi
export SPLUNK_HEC_TOKEN="${TOKEN}"
echo "  HEC token acquired: ${TOKEN:0:8}***"

echo "▶ 2/2  Live end-to-end agent run"
python3 live_test.py 2>/dev/null
