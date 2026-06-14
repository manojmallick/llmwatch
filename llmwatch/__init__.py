# © 2026 LearnHubPlay BV. LLMWatch — Production LLM Quality Observatory.
# Splunk Agentic Ops Hackathon — Observability track.
"""LLMWatch: agentic quality observability for production LLM apps on Splunk.

Pipeline:  instrument -> log to Splunk (HEC) -> agent senses via MCP Server ->
roots-cause via Splunk hosted model -> acts (rollback / incident) -> logs back.
"""

__version__ = "1.0.0"

from .config import Config
from .collector import LLMWatchCollector
from .judge import SplunkHostedJudge, QualityScore
from .mcp_client import SplunkMCPClient
from .agent import LLMWatchAgent, AgentDecision

__all__ = [
    "Config",
    "LLMWatchCollector",
    "SplunkHostedJudge",
    "QualityScore",
    "SplunkMCPClient",
    "LLMWatchAgent",
    "AgentDecision",
]
