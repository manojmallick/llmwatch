# © 2026 LearnHubPlay BV. LLMWatch.
"""Live Splunk transport via the management REST API (port 8089).

On Splunk Cloud the agent reads through the MCP Server. On a local Splunk
Enterprise instance (no MCP), this transport runs the same SPL through the
REST search API (`/services/search/jobs/export`), giving a true end-to-end
test against real indexed data. Same SPL, different transport.
"""

from __future__ import annotations

import json

from .config import Config


class SplunkRestSearch:
    """Runs SPL via the Splunk REST search API and returns rows as dicts."""

    def __init__(self, config: Config):
        self.config = config

    def run(self, spl: str, earliest: str = "-24h", latest: str = "now") -> list[dict]:
        import requests

        query = spl if spl.strip().startswith("|") or spl.strip().lower().startswith("search") \
            else f"search {spl}"
        resp = requests.post(
            f"{self.config.rest_url}/services/search/jobs/export",
            auth=(self.config.splunk_user, self.config.splunk_password),
            data={
                "search": query,
                "earliest_time": earliest,
                "latest_time": latest,
                "output_mode": "json",
                "exec_mode": "oneshot",
            },
            verify=False,
            timeout=60,
        )
        resp.raise_for_status()
        rows: list[dict] = []
        for line in resp.text.splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            result = obj.get("result")
            if result:
                rows.append(result)
        return rows
