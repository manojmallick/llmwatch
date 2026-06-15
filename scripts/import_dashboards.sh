#!/usr/bin/env bash
# © 2026 Manoj Mallick. LLMWatch — import ALL Studio dashboards via REST.
#
# Creates/updates every dashboards/*.json as a Dashboard Studio view — no UI.
#
# Usage (creds stay in YOUR shell only):
#   SPLUNK_USER=manoj SPLUNK_PASSWORD='***' bash scripts/import_dashboards.sh
set -euo pipefail

HOST=${SPLUNK_HOST:-localhost}
MGMT=${SPLUNK_MGMT:-https://$HOST:8089}
WEB_PORT=${SPLUNK_WEB_PORT:-8989}
APP=${SPLUNK_APP:-search}
: "${SPLUNK_USER:?set SPLUNK_USER}"
: "${SPLUNK_PASSWORD:?set SPLUNK_PASSWORD}"
A=(-sk -u "$SPLUNK_USER:$SPLUNK_PASSWORD")

shopt -s nullglob 2>/dev/null || true
for JSON in dashboards/*.json; do
  NAME=$(basename "$JSON" .json)
  WRAP=$(mktemp /tmp/lw_view.XXXXXX.xml)
  python3 - "$JSON" > "$WRAP" <<'PY'
import json, sys, html
d = json.load(open(sys.argv[1]))
label = d.get("title", "LLMWatch")
print(f'''<dashboard version="2" theme="dark">
  <label>{html.escape(label)}</label>
  <definition><![CDATA[
{json.dumps(d)}
  ]]></definition>
  <meta type="hiddenElements"><![CDATA[
{{"hideEdit": false, "hideOpenInSearch": false, "hideExport": false}}
  ]]></meta>
</dashboard>''')
PY
  CODE=$(curl "${A[@]}" -o /dev/null -w "%{http_code}" \
    "$MGMT/servicesNS/$SPLUNK_USER/$APP/data/ui/views" \
    -d name="$NAME" --data-urlencode "eai:data@$WRAP" || true)
  if [ "$CODE" != "201" ]; then
    CODE=$(curl "${A[@]}" -o /dev/null -w "%{http_code}" \
      "$MGMT/servicesNS/$SPLUNK_USER/$APP/data/ui/views/$NAME" \
      --data-urlencode "eai:data@$WRAP" || true)
    echo "↻ $NAME — updated (HTTP $CODE)"
  else
    echo "✓ $NAME — created (HTTP 201)"
  fi
  echo "    http://$HOST:$WEB_PORT/en-US/app/$APP/$NAME"
  rm -f "$WRAP"
done
echo ""
echo "✅ Done. Open any link above; set the time picker to 'Last 24 hours'."
