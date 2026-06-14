# © 2026 LearnHubPlay BV. LLMWatch — live end-to-end test against real Splunk.
"""Proves the full loop against a live Splunk Enterprise instance:

    1. seed realistic events to Splunk via HEC (baseline + a current regression)
    2. wait for indexing
    3. run the agent — it READS live SPL via the REST API (8089), root-causes,
       and remediates with a rollback
    4. show the live agent-action audit row from Splunk

Requires HEC enabled + a token (run scripts/setup_splunk.py first) and:
    SPLUNK_PASSWORD, SPLUNK_HEC_TOKEN   (HEC url/host default to localhost)
"""

from __future__ import annotations

import os
import sys
import time
import urllib3

from llmwatch import Config, LLMWatchCollector, SplunkHostedJudge, LLMWatchAgent
from llmwatch.mcp_client import SplunkMCPClient
from llmwatch.actions import ActionExecutor
from llmwatch.splunk_rest import SplunkRestSearch

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def banner(t: str) -> None:
    print(f"\n\033[1;32m{'─' * 64}\n{t}\n{'─' * 64}\033[0m")


def seed(collector: LLMWatchCollector) -> None:
    now = time.time()
    base_t = now - 7200    # 2h ago  → baseline bucket
    cur_t = now - 120      # 2m ago  → current bucket

    def ev(model, score, ctx, topic):
        return {"app_name": "codeassist", "model_version": model,
                "prompt_hash": f"{topic[:3]}{int(score*100)}",
                "input_tokens": 120, "output_tokens": 80, "total_tokens": 200,
                "latency_ms": 2300, "context_provided": str(ctx).lower(),
                "context_tokens": 400 if ctx else 0,
                "groundedness_score": score,
                "quality_band": "GOOD" if score >= 0.6 else "DEGRADED" if score >= 0.3 else "POOR",
                "is_hallucination": score < 0.3, "session_id": f"s-{topic}",
                "topic": topic, "response_length": 180, "judged_by": "heuristic"}

    # Baseline: v2.3 healthy (0.84) and v2.2 healthy — 2h ago.
    for i in range(8):
        collector.log_raw(ev("gemini-2.0-flash-v2.3", 0.84, True, "general"), base_t - i)
        collector.log_raw(ev("gemini-2.0-flash-v2.2", 0.83, True, "general"), base_t - i)
    # Current: v2.3 regressed on auth topics (incl. hallucinations <0.3) — 2m ago.
    for s in (0.61, 0.58, 0.31, 0.24, 0.27):
        collector.log_raw(ev("gemini-2.0-flash-v2.3", s, True, "authentication"), cur_t)
    collector.log_raw(ev("gemini-2.0-flash-v2.2", 0.83, True, "general"), cur_t)
    print("  seeded 22 events (baseline 2h ago + current regression 2m ago)")


def wait_indexed(cfg: Config, timeout: int = 60) -> bool:
    rest = SplunkRestSearch(cfg)
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = rest.run("index=llmwatch sourcetype=llm_events | stats count as c")
        if rows and int(rows[0].get("c", 0)) >= 22:
            print(f"  indexed: {rows[0]['c']} events searchable")
            return True
        time.sleep(3)
    print("  [!] timed out waiting for indexing")
    return False


def main() -> None:
    if not os.environ.get("SPLUNK_PASSWORD"):
        sys.exit("export SPLUNK_PASSWORD first")
    if not os.environ.get("SPLUNK_HEC_TOKEN"):
        sys.exit("export SPLUNK_HEC_TOKEN first (run scripts/setup_splunk.py)")

    cfg = Config(demo_mode=False, live_search=True, judge_backend="heuristic",
                 autonomous=True)
    cfg.hec_url = os.environ.get("SPLUNK_HEC_URL",
                                 "https://localhost:8088/services/collector/event")

    banner("1 · SEED events to Splunk via HEC")
    collector = LLMWatchCollector(cfg, "codeassist", "gemini-2.0-flash-v2.3",
                                  judge=SplunkHostedJudge(cfg))
    seed(collector)

    banner("2 · WAIT for indexing")
    if not wait_indexed(cfg):
        sys.exit(1)

    banner("3 · AGENT reads live SPL (REST 8089) → root-cause → remediate")
    agent = LLMWatchAgent(cfg, mcp=SplunkMCPClient(cfg), judge=SplunkHostedJudge(cfg),
                          actions=ActionExecutor(cfg), collector=collector)
    decision = agent.run_cycle()
    for line in decision.narrative:
        print(f"  {line}")

    banner(f"4 · RESULT = {decision.status}")
    if decision.action:
        print(f"  action  : {decision.action.get('display', decision.action['kind'])}")
        print(f"  result  : {decision.result['detail']}")

    banner("5 · LIVE audit row from Splunk (sourcetype=llm_agent_actions)")
    audit = SplunkRestSearch(cfg).run(
        "index=llmwatch sourcetype=llm_agent_actions "
        "| head 1 | table status action.kind action.target result.detail")
    print(f"  {audit if audit else '(none yet — indexing lag, re-query in a few seconds)'}")


if __name__ == "__main__":
    main()
