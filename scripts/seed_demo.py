# © 2026 Manoj Mallick. LLMWatch.
"""Seed a rich, varied demo dataset across 3 models, then run the agent once.

Populates index=llmwatch with enough variety for ALL three dashboards:
  - 3 model versions with different token cost AND quality
  - a clean baseline (>1h ago) vs a current v2.3 regression (last 15m)
  - with-context and without-context events (for the context-impact panel)
Then runs one LLMWatchAgent cycle so the agent-action audit trail exists.

Requires: SPLUNK_USER, SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN (run setup_splunk.py first).
"""

from __future__ import annotations

import os
import sys
import time
import urllib3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llmwatch import Config, LLMWatchCollector, SplunkHostedJudge, LLMWatchAgent
from llmwatch.mcp_client import SplunkMCPClient
from llmwatch.actions import ActionExecutor
from llmwatch.splunk_rest import SplunkRestSearch

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# model -> (input_tokens, output_tokens) → distinct cost/call for the scatter
MODELS = {
    "gemini-2.0-flash-v2.3": (480, 180),   # cost ≈ $0.0102
    "gemini-2.0-flash-v2.2": (450, 150),   # cost ≈ $0.0090
    "gpt-4o-mini":           (300, 120),   # cost ≈ $0.0066
}
BASELINE_Q = {"gemini-2.0-flash-v2.3": 0.84, "gemini-2.0-flash-v2.2": 0.83, "gpt-4o-mini": 0.79}
CURRENT_Q = {
    "gemini-2.0-flash-v2.3": [0.61, 0.58, 0.31, 0.24, 0.27, 0.42],  # regression + hallucinations
    "gemini-2.0-flash-v2.2": [0.84, 0.82, 0.83],
    "gpt-4o-mini":           [0.80, 0.78, 0.79],
}


def _event(model, score, ctx, topic):
    tin, tout = MODELS[model]
    return {
        "app_name": "codeassist", "model_version": model,
        "prompt_hash": f"{topic[:3]}{int(score*100)}",
        "input_tokens": tin, "output_tokens": tout, "total_tokens": tin + tout,
        "latency_ms": 2300, "context_provided": str(ctx).lower(),
        "context_tokens": 400 if ctx else 0,
        "groundedness_score": score,
        "quality_band": "GOOD" if score >= 0.6 else "DEGRADED" if score >= 0.3 else "POOR",
        "is_hallucination": score < 0.3, "session_id": f"s-{topic}",
        "topic": topic, "response_length": 180, "judged_by": "heuristic",
    }


def seed(collector: LLMWatchCollector) -> int:
    now = time.time()
    n = 0
    # Baseline: healthy, > 1h ago, spread -180m .. -69m (18 buckets) for a clean trend.
    for model, base in BASELINE_Q.items():
        for i in range(18):
            s = round(base + ((i % 3) - 1) * 0.02, 3)       # gentle variation
            collector.log_raw(_event(model, s, True, "general"), now - 10800 + i * 370)
            n += 1
    # Current: last 15m. v2.3 regressed on auth topics; others stable.
    for model, scores in CURRENT_Q.items():
        for j, s in enumerate(scores):
            topic = "authentication" if (model.endswith("v2.3") and s < 0.6) else "general"
            collector.log_raw(_event(model, s, True, topic), now - 900 + j * 140)
            n += 1
    # Without-context events (for the context-impact panel): low groundedness.
    for model in MODELS:
        for k, s in enumerate((0.16, 0.18, 0.14)):
            collector.log_raw(_event(model, s, False, "general"), now - 600 + k * 90)
            n += 1
    print(f"  seeded {n} events across {len(MODELS)} models (baseline + regression + no-context)")
    return n


def main() -> None:
    for var in ("SPLUNK_PASSWORD", "SPLUNK_HEC_TOKEN"):
        if not os.environ.get(var):
            sys.exit(f"export {var} first (run scripts/setup_splunk.py for the token)")

    cfg = Config(demo_mode=False, live_search=True, judge_backend="heuristic", autonomous=True)
    cfg.hec_url = os.environ.get("SPLUNK_HEC_URL",
                                 "https://localhost:8088/services/collector/event")
    collector = LLMWatchCollector(cfg, "codeassist", "gemini-2.0-flash-v2.3",
                                  judge=SplunkHostedJudge(cfg))

    print("1 · seed rich demo data → Splunk (HEC)")
    target = seed(collector)

    print("2 · wait for indexing")
    rest = SplunkRestSearch(cfg)
    deadline = time.time() + 60
    while time.time() < deadline:
        rows = rest.run("index=llmwatch sourcetype=llm_events | stats count as c")
        if rows and int(rows[0].get("c", 0)) >= target:
            print(f"  indexed: {rows[0]['c']} events"); break
        time.sleep(3)

    print("3 · run the agent (produces the rollback audit row)")
    agent = LLMWatchAgent(cfg, mcp=SplunkMCPClient(cfg), judge=SplunkHostedJudge(cfg),
                          actions=ActionExecutor(cfg), collector=collector)
    decision = agent.run_cycle()
    print(f"  agent: {decision.status} — "
          f"{decision.action.get('display') if decision.action else 'no action'}")


if __name__ == "__main__":
    main()
