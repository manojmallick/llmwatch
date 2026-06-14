# © 2026 Manoj Mallick. LLMWatch.
"""The LLMWatch Agent — the agentic core.

This is what turns LLMWatch from a passive dashboard into Agentic Ops. On each
cycle the agent runs a closed loop entirely on Splunk infrastructure:

    SENSE      query Splunk via the MCP Server (current vs baseline quality)
    DETECT     decide whether a regression breached the threshold
    INVESTIGATE pull failing examples via MCP, root-cause via a Splunk hosted model
    DECIDE     choose a remediation (rollback / reroute / incident / add-context)
    ACT        execute — with a human-approval gate for destructive actions
    LOG        write the decision + action back to Splunk for audit

It is intentionally a real control loop, not a one-shot script: call run_cycle()
on a schedule (Splunk modular input / cron) and it continuously guards quality.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .config import Config, BAND_GOOD
from .mcp_client import SplunkMCPClient, QualitySignal
from .judge import SplunkHostedJudge
from .actions import ActionExecutor, ActionPlan, ActionResult
from .collector import LLMWatchCollector


@dataclass
class AgentDecision:
    status: str                         # healthy | regression_remediated | awaiting_approval
    regression: dict | None = None
    root_cause: dict | None = None
    action: dict | None = None
    result: dict | None = None
    narrative: list[str] = field(default_factory=list)

    def as_event(self) -> dict:
        d = asdict(self)
        d["component"] = "llmwatch_agent"
        return d


class LLMWatchAgent:
    def __init__(self, config: Config, mcp: SplunkMCPClient | None = None,
                 judge: SplunkHostedJudge | None = None,
                 actions: ActionExecutor | None = None,
                 collector: LLMWatchCollector | None = None):
        self.config = config
        self.mcp = mcp or SplunkMCPClient(config)
        self.judge = judge or SplunkHostedJudge(config)
        self.actions = actions or ActionExecutor(config)
        self.collector = collector

    def run_cycle(self) -> AgentDecision:
        log: list[str] = []

        # 1. SENSE — read quality signal from Splunk through the MCP Server.
        signals = self.mcp.quality_signal(baseline_hours=24)
        log.append(f"SENSE  · pulled {len(signals)} model signals from Splunk "
                   f"[{self.mcp.transport_label}]")

        # 2. DETECT — find the worst breaching regression.
        regressing = self._detect(signals)
        if regressing is None:
            log.append("DETECT · all models within threshold — no action")
            return AgentDecision(status="healthy", narrative=log)
        # The current window can still sit in the GOOD band while having dropped
        # sharply vs baseline — that "silent drift" (no error, no red dashboard)
        # is exactly what LLMWatch exists to catch.
        silent = " (still in GOOD band — silent drift)" if regressing.current_avg >= BAND_GOOD else ""
        log.append(
            f"DETECT · {regressing.model_version} dropped {regressing.drop_pct}% "
            f"({regressing.baseline_avg} -> {regressing.current_avg}){silent} — REGRESSION")

        # 3. INVESTIGATE — pull failing examples (MCP) and root-cause (hosted model).
        examples = self.mcp.failing_examples(regressing.model_version)
        log.append(f"INVESTIGATE · fetched {len(examples)} failing calls "
                   f"[{self.mcp.transport_label}]")
        summary = (f"Model {regressing.model_version} groundedness "
                   f"{regressing.baseline_avg} -> {regressing.current_avg} "
                   f"over {regressing.current_calls} calls.")
        root_cause = self.judge.root_cause_analysis(summary, examples)
        log.append(f"INVESTIGATE · {self.config.hosted_model} root cause: "
                   f"{root_cause.get('topic_cluster')} "
                   f"[{root_cause.get('confidence')}] -> "
                   f"{root_cause.get('recommended_action')}")

        # 4. DECIDE — translate the root cause into a concrete action plan.
        plan = self._decide(regressing, root_cause)
        log.append(f"DECIDE · {plan.display} "
                   f"(approval_required={plan.requires_approval})")

        # 5. ACT — execute with the human-approval gate.
        result = self.actions.execute(plan)
        log.append(f"ACT    · {result.status}: {result.detail}")

        # 6. LOG — write the full decision back to Splunk for audit.
        decision = AgentDecision(
            status="awaiting_approval" if result.status == "staged_for_approval"
            else "regression_remediated",
            regression={"model_version": regressing.model_version,
                        "drop_pct": regressing.drop_pct,
                        "current": regressing.current_avg,
                        "baseline": regressing.baseline_avg},
            root_cause=root_cause,
            action={"kind": plan.kind, "target": plan.target,
                    "destination": plan.destination, "display": plan.display,
                    "rationale": plan.rationale, "params": plan.params},
            result={"status": result.status, "detail": result.detail},
            narrative=log,
        )
        if self.collector is not None:
            self.collector.log_agent_action(decision.as_event())
            log.append("LOG    · agent decision written to index=llmwatch (audit trail)")
        return decision

    # ── decision logic ───────────────────────────────────────────────────────
    def _detect(self, signals: list[QualitySignal]) -> QualitySignal | None:
        breaching = [
            s for s in signals
            if s.baseline_avg > 0 and s.current_avg < s.baseline_avg * self.config.regression_threshold
        ]
        return max(breaching, key=lambda s: s.drop_pct) if breaching else None

    def _decide(self, sig: QualitySignal, root_cause: dict) -> ActionPlan:
        action = root_cause.get("recommended_action", "investigate")
        if action == "rollback":
            prev = self._previous_version(sig.model_version)
            return ActionPlan(
                kind="rollback", target=sig.model_version,
                rationale=f"Restore quality by reverting to {prev} "
                          f"(est. +{sig.drop_pct}% recovery).",
                requires_approval=True,
                params={"rollback_to": prev})
        if action == "reroute":
            return ActionPlan(kind="reroute", target=sig.model_version,
                              rationale="Route around the degraded model version.",
                              requires_approval=True, params={"route_to": "gpt-4o-mini"})
        if action == "add_context":
            return ActionPlan(kind="add_context", target=sig.model_version,
                              rationale="Inject retrieval context for the failing topic.",
                              requires_approval=False,
                              params={"topic": root_cause.get("topic_cluster")})
        # default: non-destructive — file an incident with evidence for a human.
        return ActionPlan(kind="file_incident", target=sig.model_version,
                          rationale="Ambiguous cause — escalate with SPL evidence.",
                          requires_approval=False,
                          params={"ticket_id": "LLMW-AUTO"})

    @staticmethod
    def _previous_version(version: str) -> str:
        # naive semantic predecessor: v2.3 -> v2.2
        if version.endswith("v2.3"):
            return version[:-1] + "2"
        return version + "-prev"
