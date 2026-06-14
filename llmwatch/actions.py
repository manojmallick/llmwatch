# © 2026 Manoj Mallick. LLMWatch.
"""Actions the agent can take to remediate a quality regression.

Responsible agentic ops: destructive actions (rollback, reroute) carry
`requires_approval=True`. When the agent runs non-autonomously, it stages the
action and waits for a human to approve — it never silently mutates production.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ActionPlan:
    kind: str                       # rollback | reroute | file_incident | add_context
    target: str                     # the model version being acted ON (e.g. the regressed one)
    rationale: str
    requires_approval: bool = True
    params: dict = field(default_factory=dict)

    @property
    def destination(self) -> str:
        """Where the action moves traffic TO — distinct from `target`, which is
        the version being acted on. For rollback/reroute this is a healthy model;
        for incident/add_context there is no move, so it equals `target`."""
        return self.params.get("rollback_to") or self.params.get("route_to") or self.target

    @property
    def display(self) -> str:
        """Human-readable 'what → where', e.g. 'rollback v2.3 → v2.2'. Avoids the
        misleading 'rollback → v2.3' (which names the broken version as the target)."""
        if self.destination != self.target:
            return f"{self.kind} {self.target} → {self.destination}"
        return f"{self.kind} {self.target}"


@dataclass
class ActionResult:
    kind: str
    status: str                     # executed | staged_for_approval | failed
    detail: str


class ActionExecutor:
    """Executes remediation. In demo_mode it simulates side effects."""

    def __init__(self, config, model_registry: dict[str, str] | None = None):
        self.config = config
        # active model per app; rollback flips this.
        self.registry = model_registry or {"default": "gemini-2.0-flash-v2.3"}

    def execute(self, plan: ActionPlan) -> ActionResult:
        if plan.requires_approval and not self.config.autonomous:
            return ActionResult(plan.kind, "staged_for_approval",
                                f"Awaiting human approval: {plan.display}")
        handler = getattr(self, f"_do_{plan.kind}", None)
        if handler is None:
            return ActionResult(plan.kind, "failed", f"Unknown action: {plan.kind}")
        return handler(plan)

    def _do_rollback(self, plan: ActionPlan) -> ActionResult:
        prev = plan.params.get("rollback_to", "gemini-2.0-flash-v2.2")
        self.registry["default"] = prev
        return ActionResult("rollback", "executed",
                            f"Active model {plan.target} -> {prev}. Traffic restored.")

    def _do_reroute(self, plan: ActionPlan) -> ActionResult:
        healthy = plan.params.get("route_to", "gpt-4o-mini")
        self.registry["default"] = healthy
        return ActionResult("reroute", "executed", f"Routed traffic to {healthy}.")

    def _do_file_incident(self, plan: ActionPlan) -> ActionResult:
        ticket = plan.params.get("ticket_id", "LLMW-DEMO-001")
        return ActionResult("file_incident", "executed",
                            f"Incident {ticket} filed with SPL evidence attached.")

    def _do_add_context(self, plan: ActionPlan) -> ActionResult:
        return ActionResult("add_context", "executed",
                            f"Enabled retrieval context for topic '{plan.params.get('topic')}'.")
