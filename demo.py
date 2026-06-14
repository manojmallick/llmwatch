# © 2026 Manoj Mallick. LLMWatch — runnable end-to-end demo.
"""Run the full LLMWatch agentic loop with zero network access.

    python demo.py            # staged action (human-approval gate ON)
    python demo.py --auto     # autonomous remediation (gate OFF)

It (1) instruments a handful of LLM calls and logs them, (2) runs the agent,
which senses a quality regression via the (simulated) Splunk MCP Server,
root-causes it with a Splunk hosted model, and remediates with a rollback.
"""

from __future__ import annotations

import sys

from llmwatch import Config, LLMWatchCollector, SplunkHostedJudge, LLMWatchAgent
from llmwatch.mcp_client import SplunkMCPClient
from llmwatch.actions import ActionExecutor


def banner(text: str) -> None:
    print(f"\n\033[1;32m{'─' * 64}\n{text}\n{'─' * 64}\033[0m")


def main() -> None:
    autonomous = "--auto" in sys.argv
    config = Config(demo_mode=True, autonomous=autonomous)
    judge = SplunkHostedJudge(config)

    banner("LLMWatch · instrumenting LLM calls → Splunk HEC")
    collector = LLMWatchCollector(config, app_name="codeassist",
                                  model_version="gemini-2.0-flash-v2.3", judge=judge)
    samples = [
        ("Where is JWT validation handled?",
         "In JwtTokenProvider.java, validateToken() verifies the signature.", True),
        ("Where is JWT validation handled?",
         "Spring Security typically uses UsernamePasswordAuthenticationFilter...", True),
        ("How are roles checked?",
         "Role-based access control is usually configured in a SecurityConfig.", True),
    ]
    for prompt, response, ctx in samples:
        score = collector.log_call(prompt, response, input_tokens=120,
                                   output_tokens=80, latency_ms=2300,
                                   context_provided=ctx, topic="authentication")
        print(f"  logged · groundedness={score.groundedness:<5} band={score.band}")
    print(f"  {len(collector.events)} events buffered for index=llmwatch")

    banner("LLMWatch Agent · closed-loop remediation"
           f"  (autonomous={autonomous})")
    agent = LLMWatchAgent(
        config,
        mcp=SplunkMCPClient(config),
        judge=judge,
        actions=ActionExecutor(config),
        collector=collector,
    )
    decision = agent.run_cycle()

    for line in decision.narrative:
        print(f"  {line}")

    banner(f"RESULT · status = {decision.status}")
    if decision.action:
        print(f"  action      : {decision.action['display']}")
        print(f"  rationale   : {decision.action['rationale']}")
        print(f"  result      : {decision.result['detail']}")
    if decision.status == "awaiting_approval":
        print("\n  ▶ Human-approval gate held the rollback. Re-run with --auto to "
              "let the agent remediate autonomously.")


if __name__ == "__main__":
    main()
