# © 2026 Manoj Mallick. LLMWatch.
"""Seed synthetic LLM telemetry into Splunk via HEC so the LLMWatch dashboards
(dashboards/*.json) render. Models a real quality regression: model v2.3 drops
to ~0.61 groundedness in the last ~2h while v2.2 stays ~0.84.

Usage:
    export SPLUNK_HEC_URL=https://localhost:8088/services/collector/event   # default
    export SPLUNK_HEC_TOKEN=<your-hec-token>
    python scripts/seed_splunk.py [--events 60] [--hours 30]

Writes to  index=llmwatch  sourcetype=llm_events  (+ a few llm_agent_actions).
No secrets hardcoded — token from the environment only.
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.request

STABLE = "gemini-2.0-flash-v2.2"
REGRESSED = "gemini-2.0-flash-v2.3"
TOPICS = ["authentication", "authorization", "billing", "search", "general"]


def groundedness(model: str, age_h: float, i: int) -> float:
    jitter = ((i * 7) % 9 - 4) / 100.0          # ±0.04 deterministic jitter
    if model == REGRESSED and age_h <= 2.0:     # the silent regression window
        return round(0.61 + jitter, 3)
    return round(0.84 + jitter, 3)              # healthy baseline


def event(i: int, now: float, span_h: float) -> dict:
    model = STABLE if i % 2 == 0 else REGRESSED
    # cluster ~1/3 of events into the last 2h so the regression is visible "now"
    age_h = (i % 3 == 0) and (i / 30.0) or span_h * (i / 60.0)
    age_h = min(age_h, span_h)
    g = groundedness(model, age_h, i)
    ctx = (i % 4 != 0)                           # 75% have retrieval context
    itok, otok = 120 + (i * 11) % 80, 60 + (i * 7) % 60
    return {
        "time": round(now - age_h * 3600.0, 3),
        "host": "llmwatch-demo", "source": "llmwatch",
        "sourcetype": "llm_events", "index": "llmwatch",
        "event": {
            "app_name": "codeassist", "model_version": model,
            "groundedness_score": g, "quality_band": "GOOD" if g >= 0.6 else "DEGRADED",
            "is_hallucination": g < 0.3, "context_provided": "true" if ctx else "false",
            "input_tokens": itok, "output_tokens": otok, "total_tokens": itok + otok,
            "latency_ms": 1800 + (i * 37) % 1400, "topic": TOPICS[i % len(TOPICS)],
        },
    }


def agent_action(i: int, now: float) -> dict:
    staged = i % 2 == 0
    return {
        "time": round(now - (i + 1) * 1800.0, 3),
        "host": "llmwatch-demo", "source": "llmwatch_agent",
        "sourcetype": "llm_agent_actions", "index": "llmwatch",
        "event": {
            "component": "llmwatch_agent",
            "status": "awaiting_approval" if staged else "regression_remediated",
            "model_version": REGRESSED, "drop_pct": 27.4,
            "action": {"kind": "rollback", "target": REGRESSED,
                       "destination": STABLE},
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=60)
    ap.add_argument("--hours", type=float, default=30.0)
    ap.add_argument("--actions", type=int, default=4)
    args = ap.parse_args()

    url = os.environ.get("SPLUNK_HEC_URL", "https://localhost:8088/services/collector/event")
    token = os.environ.get("SPLUNK_HEC_TOKEN", "")
    if not token:
        print("ERROR: set SPLUNK_HEC_TOKEN (and optionally SPLUNK_HEC_URL).", file=sys.stderr)
        return 2

    now = time.time()
    docs = [event(i, now, args.hours) for i in range(args.events)]
    docs += [agent_action(i, now) for i in range(args.actions)]
    body = "\n".join(json.dumps(d) for d in docs)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        url, data=body.encode(),
        headers={"Authorization": f"Splunk {token}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            print(f"HEC {resp.status}: {resp.read().decode()[:120]}")
    except Exception as e:  # noqa: BLE001
        print(f"ERROR posting to HEC: {e}", file=sys.stderr)
        return 1
    print(f"Seeded {args.events} llm_events + {args.actions} llm_agent_actions → "
          f"index=llmwatch (v2.3 regression in the last ~2h). Open the LLMWatch dashboards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
