# © 2026 Manoj Mallick. LLMWatch.
"""LLM-as-judge groundedness scoring backed by a Splunk hosted model.

This replaces the demo placeholder. It makes a real chat-completions call to a
Splunk hosted model (e.g. gpt-oss-120b) and parses a 0-1 groundedness score.
In demo_mode it falls back to a deterministic heuristic so the repo runs
end-to-end with zero network access (CLAUDE.md air-gapped rule).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import Config, BAND_GOOD, BAND_DEGRADED

JUDGE_SYSTEM_PROMPT = (
    "You are a strict groundedness evaluator for a production LLM monitoring "
    "system. Given a user question and an AI response, score how grounded the "
    "response is in concrete, verifiable specifics on a 0.0-1.0 scale.\n"
    "0.8-1.0 = specific, cites concrete files/identifiers/values\n"
    "0.5-0.8 = partially specific, mostly accurate\n"
    "0.3-0.5 = generic but plausible\n"
    "0.0-0.3 = hallucinated, vague, or irrelevant.\n"
    'Return ONLY JSON: {"groundedness": <float>, "reason": "<short>"}'
)


@dataclass
class QualityScore:
    groundedness: float
    band: str
    reason: str
    judged_by: str

    @property
    def is_hallucination(self) -> bool:
        return self.groundedness < BAND_DEGRADED


def _band(score: float) -> str:
    if score >= BAND_GOOD:
        return "GOOD"
    if score >= BAND_DEGRADED:
        return "DEGRADED"
    return "POOR"


class SplunkHostedJudge:
    """Scores response groundedness using a Splunk hosted foundation model."""

    def __init__(self, config: Config):
        self.config = config
        self.model = config.hosted_model

    def score(self, prompt: str, response: str, context_provided: bool) -> QualityScore:
        """Evaluate a single (prompt, response) pair. Truncates inputs for privacy."""
        if self.config.demo_mode or self.config.judge_backend == "heuristic":
            return self._demo_score(prompt, response, context_provided)
        try:
            raw = self._call_hosted_model(
                JUDGE_SYSTEM_PROMPT,
                f"Question: {prompt[:300]}\nResponse: {response[:800]}\n"
                f"Context was {'PROVIDED' if context_provided else 'NOT provided'}.",
            )
            parsed = self._parse(raw)
            g = max(0.0, min(1.0, float(parsed["groundedness"])))
            return QualityScore(g, _band(g), parsed.get("reason", ""), self.model)
        except (KeyError, ValueError, json.JSONDecodeError, OSError):
            # Never crash the host app on a judge failure — degrade gracefully.
            return self._demo_score(prompt, response, context_provided)

    def root_cause_analysis(self, summary: str, failing_examples: list[dict]) -> dict:
        """Agentic step: ask the hosted model to root-cause a regression."""
        if self.config.demo_mode or self.config.judge_backend == "heuristic":
            return self._demo_root_cause(failing_examples)
        examples = "\n".join(
            f"- Q: {e.get('prompt','')[:120]} | A: {e.get('response','')[:160]} "
            f"(score {e.get('groundedness')})"
            for e in failing_examples[:8]
        )
        raw = self._call_hosted_model(
            "You are an SRE root-cause analyst for LLM quality regressions. "
            "Identify the most likely cause and a recommended action. Return JSON: "
            '{"hypothesis": "...", "topic_cluster": "...", "confidence": "HIGH|MED|LOW", '
            '"recommended_action": "rollback|reroute|add_context|investigate"}',
            f"Regression summary:\n{summary}\n\nFailing examples:\n{examples}",
        )
        return self._parse(raw)

    # ── hosted model transport ───────────────────────────────────────────────
    def _call_hosted_model(self, system: str, user: str) -> str:
        import requests  # local import so demo_mode needs no dependency

        resp = requests.post(
            self.config.hosted_model_url,
            headers={"Authorization": f"Bearer {self.config.mcp_token}",
                     "Content-Type": "application/json"},
            json={
                "model": self.model,
                "temperature": 0.0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _parse(raw: str) -> dict:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(match.group(0) if match else raw)

    # ── deterministic demo fallback (no network) ─────────────────────────────
    def _demo_score(self, prompt: str, response: str, context_provided: bool) -> QualityScore:
        # Reward concrete specifics (file refs, identifiers, code), punish hedging.
        specifics = len(re.findall(r"[A-Za-z]+\.(java|py|ts|go)|[A-Z][a-z]+[A-Z]\w+|\(\)", response))
        generic = len(re.findall(r"typically|generally|usually|in general|often", response.lower()))
        base = 0.621 if context_provided else 0.158
        score = base + 0.05 * specifics - 0.06 * generic
        score = max(0.0, min(1.0, round(score, 3)))
        return QualityScore(score, _band(score),
                            "demo-heuristic: specifics vs generic hedging", "demo-judge")

    @staticmethod
    def _demo_root_cause(failing_examples: list[dict]) -> dict:
        return {
            "hypothesis": "v2.3 deployment changed handling of security-domain prompts; "
                          "responses cite framework docs instead of codebase context.",
            "topic_cluster": "authentication / authorization",
            "confidence": "HIGH",
            "recommended_action": "rollback",
        }
