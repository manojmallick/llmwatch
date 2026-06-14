# © 2026 LearnHubPlay BV. LLMWatch.
"""Configuration. All secrets come from the environment — never hardcoded."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


# Validated groundedness benchmark used consistently across the whole project.
# Source: SigMap judge methodology (LLM-as-judge groundedness, 0-1 scale).
GROUNDEDNESS_WITH_CONTEXT = 0.621
GROUNDEDNESS_WITHOUT_CONTEXT = 0.158

# Quality bands.
BAND_GOOD = 0.60
BAND_DEGRADED = 0.30

# Regression: current window must drop below this fraction of the baseline.
REGRESSION_THRESHOLD = 0.85


@dataclass
class Config:
    """Runtime config. `demo_mode` makes everything runnable with zero network."""

    # Splunk HEC (ingestion).
    hec_url: str = field(default_factory=lambda: os.environ.get(
        "SPLUNK_HEC_URL", "https://localhost:8088/services/collector/event"))
    hec_token: str = field(default_factory=lambda: os.environ.get("SPLUNK_HEC_TOKEN", ""))
    index: str = "llmwatch"

    # Splunk MCP Server (the agent reads/queries Splunk through this on Cloud).
    mcp_url: str = field(default_factory=lambda: os.environ.get(
        "SPLUNK_MCP_URL", "https://localhost:8089/services/mcp"))
    mcp_token: str = field(default_factory=lambda: os.environ.get("SPLUNK_MCP_TOKEN", ""))

    # Live REST transport (local Splunk Enterprise has no MCP — read via 8089).
    rest_url: str = field(default_factory=lambda: os.environ.get(
        "SPLUNK_REST_URL", "https://localhost:8089"))
    splunk_user: str = field(default_factory=lambda: os.environ.get("SPLUNK_USER", "admin"))
    splunk_password: str = field(default_factory=lambda: os.environ.get("SPLUNK_PASSWORD", ""))
    live_search: bool = field(default_factory=lambda: os.environ.get("LLMWATCH_LIVE") == "1")
    # Local Splunk ships a self-signed cert; verification is off by default.
    verify_tls: bool = field(default_factory=lambda: os.environ.get("SPLUNK_VERIFY_TLS") == "1")

    # Judge backend: auto | heuristic | hosted | ollama
    judge_backend: str = field(default_factory=lambda: os.environ.get(
        "LLMWATCH_JUDGE", "auto"))

    # Splunk hosted model (LLM-as-judge + root-cause reasoning).
    hosted_model: str = field(default_factory=lambda: os.environ.get(
        "SPLUNK_HOSTED_MODEL", "gpt-oss-120b"))
    hosted_model_url: str = field(default_factory=lambda: os.environ.get(
        "SPLUNK_HOSTED_MODEL_URL", "https://localhost:8089/services/ml/v1/chat/completions"))

    # Agent behaviour.
    autonomous: bool = False        # if False, destructive actions need human approval
    regression_threshold: float = REGRESSION_THRESHOLD

    # Demo mode: no network calls, deterministic synthetic data. CLAUDE.md Rule 5.
    demo_mode: bool = field(default_factory=lambda: os.environ.get(
        "LLMWATCH_DEMO", "1") == "1")

    def mask_token(self, token: str) -> str:
        """Mask secrets for logs/CLI. Never print a raw token."""
        if not token:
            return "<unset>"
        return token[:4] + "***" if len(token) > 4 else "***"
