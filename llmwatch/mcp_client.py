# © 2026 LearnHubPlay BV. LLMWatch.
"""Splunk MCP Server client.

The agent does not just push events to Splunk — it *reads* from Splunk through
the Splunk MCP Server using the Model Context Protocol (JSON-RPC). This is what
makes LLMWatch agentic rather than a passive dashboard: an AI agent securely
queries Splunk data via MCP, reasons over it, and decides what to do.

In demo_mode the client returns a deterministic synthetic regression so the
whole loop runs offline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .config import Config


@dataclass
class QualitySignal:
    """Aggregated quality signal pulled from Splunk for a model version."""
    model_version: str
    current_avg: float
    baseline_avg: float
    current_calls: int

    @property
    def drop_pct(self) -> float:
        if self.baseline_avg == 0:
            return 0.0
        return round((1 - self.current_avg / self.baseline_avg) * 100, 1)


class SplunkMCPClient:
    """Talks to the Splunk MCP Server. Token-based auth (OAuth in CA)."""

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, config: Config):
        self.config = config
        self._rpc_id = 0
        self._session_id: str | None = None
        self._session_ready = False

    @property
    def transport_label(self) -> str:
        """Which Splunk read path is active — keeps logs honest across envs.

        Splunk Cloud → MCP Server; local Enterprise → REST search; demo → synthetic.
        """
        if self.config.demo_mode:
            return "demo"
        return "REST" if self.config.live_search else "MCP"

    # ── high-level operations the agent uses ─────────────────────────────────
    def quality_signal(self, baseline_hours: int = 24) -> list[QualitySignal]:
        """Run SPL via MCP: current-hour avg groundedness vs N-hour baseline."""
        spl = (
            "index=llmwatch sourcetype=llm_events "
            '| eval bucket=if(_time>=relative_time(now(),"-1h@h"),"current","baseline") '
            "| stats avg(groundedness_score) as avg_score count as calls "
            "by model_version bucket"
        )
        rows = self._run_splunk_query(spl)
        return self._fold_signal(rows)

    def failing_examples(self, model_version: str, limit: int = 8) -> list[dict]:
        """Pull recent low-groundedness calls for the regressing model via MCP."""
        spl = (
            f'index=llmwatch sourcetype=llm_events model_version="{model_version}" '
            "groundedness_score<0.3 "
            f"| head {limit} "
            "| table prompt_hash groundedness_score topic"
        )
        return self._run_splunk_query(spl)

    # ── MCP / JSON-RPC transport ─────────────────────────────────────────────
    def _run_splunk_query(self, spl: str) -> list[dict]:
        """Read Splunk. Cloud → MCP Server tool; local → REST search; demo → synthetic."""
        if self.config.demo_mode:
            return self._demo_rows(spl)
        if self.config.live_search:
            # Local Splunk Enterprise has no MCP Server — same SPL via REST API.
            from .splunk_rest import SplunkRestSearch
            return SplunkRestSearch(self.config).run(spl)
        return self._call_tool("run_splunk_query", {"query": spl, "earliest": "-24h"})

    def _ensure_session(self) -> None:
        """Perform the MCP `initialize` handshake once, then cache the session.

        Streamable-HTTP MCP requires `initialize` (the server returns an
        `Mcp-Session-Id`) followed by an `initialized` notification *before* any
        `tools/call`. Skipping this handshake is the #1 reason a client that
        "works" in demo mode fails against a live Splunk MCP Server.
        """
        if self._session_ready:
            return
        init = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "llmwatch-agent", "version": "1.0.0"},
            },
        })
        # The server hands back a session id in the response header; reuse it.
        self._session_id = init.headers.get("Mcp-Session-Id") or self._session_id
        # Acknowledge — notifications carry no id and expect no response body.
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"},
                   expect_response=False)
        self._session_ready = True

    def _call_tool(self, tool: str, arguments: dict) -> list[dict]:
        self._ensure_session()
        resp = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        })
        result = self._decode(resp).get("result", {})
        # MCP returns content blocks; the Splunk tool ships rows as JSON text.
        content = result.get("content", [])
        if content and content[0].get("type") == "text":
            return json.loads(content[0]["text"])
        return result.get("rows", [])

    def _post(self, body: dict, expect_response: bool = True):
        """POST one JSON-RPC message to the MCP Server, carrying the session."""
        import requests  # local import: demo_mode needs no network deps

        headers = {
            "Authorization": f"Bearer {self.config.mcp_token}",
            "Content-Type": "application/json",
            # Streamable HTTP servers may answer as JSON or as an SSE stream.
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.PROTOCOL_VERSION,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        resp = requests.post(self.config.mcp_url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _decode(resp) -> dict:
        """Parse a JSON-RPC reply that may arrive as JSON or an SSE stream."""
        if "text/event-stream" in resp.headers.get("Content-Type", ""):
            # SSE framing: the JSON-RPC message rides the last `data:` line.
            for line in reversed(resp.text.splitlines()):
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            return {}
        return resp.json() if resp.content else {}

    def _next_id(self) -> int:
        self._rpc_id += 1
        return self._rpc_id

    @staticmethod
    def _fold_signal(rows: list[dict]) -> list[QualitySignal]:
        by_model: dict[str, dict] = {}
        for r in rows:
            mv = r["model_version"]
            slot = by_model.setdefault(mv, {})
            slot[r["bucket"]] = (float(r["avg_score"]), int(r.get("calls", 0)))
        signals = []
        for mv, slot in by_model.items():
            cur, cur_calls = slot.get("current", (0.0, 0))
            base, _ = slot.get("baseline", (cur, 0))
            signals.append(QualitySignal(mv, round(cur, 3), round(base, 3), cur_calls))
        return signals

    # ── deterministic demo data (a real regression) ──────────────────────────
    @staticmethod
    def _demo_rows(spl: str) -> list[dict]:
        if "groundedness_score<0.3" in spl:
            return [
                {"prompt_hash": "a1b2", "prompt": "Where is JWT validation handled?",
                 "response": "Spring Security typically uses UsernamePasswordAuth...",
                 "groundedness_score": 0.31, "topic": "authentication"},
                {"prompt_hash": "c3d4", "prompt": "How are auth tokens refreshed?",
                 "response": "Generally, applications use a refresh token flow...",
                 "groundedness_score": 0.24, "topic": "authorization"},
                {"prompt_hash": "e5f6", "prompt": "Where are roles checked?",
                 "response": "Role-based access control is usually configured...",
                 "groundedness_score": 0.27, "topic": "authorization"},
            ]
        # quality signal: v2.3 regressed (0.61 vs 0.84 baseline), v2.2 stable.
        return [
            {"model_version": "gemini-2.0-flash-v2.3", "bucket": "current",
             "avg_score": 0.61, "calls": 423},
            {"model_version": "gemini-2.0-flash-v2.3", "bucket": "baseline",
             "avg_score": 0.84, "calls": 1180},
            {"model_version": "gemini-2.0-flash-v2.2", "bucket": "current",
             "avg_score": 0.83, "calls": 312},
            {"model_version": "gemini-2.0-flash-v2.2", "bucket": "baseline",
             "avg_score": 0.84, "calls": 990},
        ]
