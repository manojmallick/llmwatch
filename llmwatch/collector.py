# © 2026 Manoj Mallick. LLMWatch.
"""Instrumentation collector. Logs every LLM call to Splunk via HEC.

Privacy: prompts are hashed, raw content is sampled and truncated. Never logs
secrets. This is the ingestion side; the agent reads back via MCP (mcp_client).
"""

from __future__ import annotations

import hashlib
import time
from typing import Optional

from .config import Config
from .judge import SplunkHostedJudge, QualityScore


class LLMWatchCollector:
    def __init__(self, config: Config, app_name: str, model_version: str,
                 judge: Optional[SplunkHostedJudge] = None):
        self.config = config
        self.app_name = app_name
        self.model_version = model_version
        self.judge = judge or SplunkHostedJudge(config)
        self._buffer: list[dict] = []  # demo_mode keeps events in memory

    def log_call(self, prompt: str, response: str, *, input_tokens: int,
                 output_tokens: int, latency_ms: float, context_provided: bool = False,
                 context_tokens: int = 0, session_id: Optional[str] = None,
                 topic: str = "general") -> QualityScore:
        score = self.judge.score(prompt, response, context_provided)
        event = {
            "time": time.time(),
            "source": "llmwatch",
            "sourcetype": "llm_events",
            "index": self.config.index,
            "event": {
                "app_name": self.app_name,
                "model_version": self.model_version,
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "latency_ms": latency_ms,
                "context_provided": str(context_provided).lower(),
                "context_tokens": context_tokens,
                "groundedness_score": score.groundedness,
                "quality_band": score.band,
                "is_hallucination": score.is_hallucination,
                "session_id": session_id or "unknown",
                "topic": topic,
                "response_length": len(response),
                "judged_by": score.judged_by,
            },
        }
        self._emit(event)
        return score

    def log_raw(self, fields: dict, ts: Optional[float] = None) -> None:
        """Emit a pre-scored event at an explicit timestamp (seeding/testing)."""
        self._emit({
            "time": ts if ts is not None else time.time(),
            "source": "llmwatch",
            "sourcetype": "llm_events",
            "index": self.config.index,
            "event": fields,
        })

    def log_agent_action(self, decision: dict) -> None:
        """Audit trail: the agent logs its own actions back to Splunk."""
        self._emit({
            "time": time.time(),
            "source": "llmwatch_agent",
            "sourcetype": "llm_agent_actions",
            "index": self.config.index,
            "event": decision,
        })

    def _emit(self, event: dict) -> None:
        if self.config.demo_mode:
            self._buffer.append(event)
            return
        import requests
        requests.post(
            self.config.hec_url,
            headers={"Authorization": f"Splunk {self.config.hec_token}"},
            json=event,
            timeout=5,
            verify=self.config.verify_tls,
        )

    @property
    def events(self) -> list[dict]:
        return self._buffer
