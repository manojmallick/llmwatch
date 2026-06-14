# © 2026 LearnHubPlay BV. LLMWatch — unit tests (no network; demo transport).
"""Fast logic tests for the agentic core. Run: python -m pytest tests/ -q"""

from llmwatch import Config, LLMWatchAgent, SplunkHostedJudge
from llmwatch.mcp_client import SplunkMCPClient, QualitySignal
from llmwatch.actions import ActionPlan, ActionExecutor


def _cfg(**kw):
    return Config(demo_mode=True, **kw)


# ── detection ────────────────────────────────────────────────────────────────
def test_detects_worst_regression():
    agent = LLMWatchAgent(_cfg())
    signals = [
        QualitySignal("stable", 0.83, 0.84, 100),       # within threshold
        QualitySignal("regressed", 0.61, 0.84, 423),    # -27%
        QualitySignal("worse", 0.40, 0.84, 200),        # -52% → worst
    ]
    worst = agent._detect(signals)
    assert worst is not None and worst.model_version == "worse"


def test_no_regression_when_stable():
    agent = LLMWatchAgent(_cfg())
    assert agent._detect([QualitySignal("ok", 0.84, 0.84, 100)]) is None


def test_silent_drift_still_in_good_band_is_caught():
    # Dropped >15% but current avg still ≥ GOOD band → the silent case.
    agent = LLMWatchAgent(_cfg())
    sig = QualitySignal("drift", 0.70, 0.84, 100)  # -16.7%, still 0.70
    assert agent._detect([sig]) is not None


# ── decision + action labelling ──────────────────────────────────────────────
def test_rollback_plan_targets_broken_moves_to_previous():
    agent = LLMWatchAgent(_cfg())
    sig = QualitySignal("gemini-2.0-flash-v2.3", 0.61, 0.84, 423)
    plan = agent._decide(sig, {"recommended_action": "rollback"})
    assert plan.kind == "rollback"
    assert plan.target == "gemini-2.0-flash-v2.3"
    assert plan.destination == "gemini-2.0-flash-v2.2"
    assert plan.display == "rollback gemini-2.0-flash-v2.3 → gemini-2.0-flash-v2.2"


def test_approval_gate_blocks_destructive_action_when_not_autonomous():
    ex = ActionExecutor(_cfg(autonomous=False))
    plan = ActionPlan("rollback", "v2.3", "x", requires_approval=True,
                      params={"rollback_to": "v2.2"})
    assert ex.execute(plan).status == "staged_for_approval"


def test_autonomous_executes_rollback_and_flips_registry():
    ex = ActionExecutor(_cfg(autonomous=True))
    plan = ActionPlan("rollback", "v2.3", "x", requires_approval=True,
                      params={"rollback_to": "v2.2"})
    assert ex.execute(plan).status == "executed"
    assert ex.registry["default"] == "v2.2"


# ── judge + transport label ──────────────────────────────────────────────────
def test_judge_scores_context_higher_than_no_context():
    judge = SplunkHostedJudge(_cfg())
    grounded = judge.score("q", "validateToken() in JwtTokenProvider.java", True)
    vague = judge.score("q", "Generally applications typically handle this.", False)
    assert grounded.groundedness > vague.groundedness
    assert vague.is_hallucination


def test_transport_label_reflects_environment():
    assert SplunkMCPClient(Config(demo_mode=True)).transport_label == "demo"
    assert SplunkMCPClient(Config(demo_mode=False, live_search=True)).transport_label == "REST"
    assert SplunkMCPClient(Config(demo_mode=False, live_search=False)).transport_label == "MCP"


def test_full_cycle_demo_remediates():
    agent = LLMWatchAgent(_cfg(autonomous=True))
    decision = agent.run_cycle()
    assert decision.status == "regression_remediated"
    assert decision.action["kind"] == "rollback"
