# LLMWatch — Devpost Submission

**Track:** Observability · **Splunk Agentic Ops Hackathon**

---

## Elevator pitch

Your LLM got worse last night. Splunk saw it — and rolled it back. LLMWatch is
an **agent** that runs on Splunk and autonomously detects, root-causes, and
remediates silent LLM quality regressions in production.

## Inspiration

LLM answer quality degrades **silently**. A model update, a prompt change, or a
drifting RAG index can drop groundedness 20–30% with no exception, no red
dashboard, no alert. Teams find out from customer complaints — days later. Two
years building production LLM systems (RAG, semantic cache, guardrails) taught
us that the metric that matters — *groundedness* — is never monitored. Splunk
already watches infrastructure at terabyte scale; LLMWatch points that same
machinery at LLM answer quality, and adds an agent that acts.

## What it does

LLMWatch instruments every LLM call into Splunk, then runs a closed agentic
control loop:

1. **SENSE** — reads quality signal from Splunk (current hour vs 24h baseline).
2. **DETECT** — flags regressions, including *silent drift* (a sharp drop that's
   still inside the "good" band — the case nothing else catches).
3. **INVESTIGATE** — pulls failing calls and root-causes them with a Splunk
   hosted model (LLM-as-judge / SRE analyst).
4. **DECIDE** — picks a remediation: rollback, reroute, add-context, or incident.
5. **ACT** — executes, behind a human-approval gate for destructive actions.
6. **LOG** — writes its decision back to Splunk as an audit trail.

## How we used Splunk

| Splunk capability | How LLMWatch uses it |
|---|---|
| **HTTP Event Collector (HEC)** | Privacy-safe ingestion of every LLM call (prompts hashed) |
| **SPL** | Quality trends, regression detection, hallucination rate, cost/quality |
| **Splunk MCP Server** | The agent reads Splunk securely over MCP (Cloud); the same SPL runs over the REST search API on local Enterprise |
| **Splunk Hosted Models** (`gpt-oss`) | LLM-as-judge groundedness scoring **and** root-cause analysis |
| **Alerts / modular input** | Fires the agent's `run_cycle` on a schedule |
| **Dashboard Studio** | Real-time Quality Observatory + Regression Investigation views |

## Proof it's real (verified on a live Splunk instance)

This is not a mock. On a live Splunk Enterprise instance we seeded events via
HEC and ran the agent against **live SPL**:

```
SENSE  · pulled 2 model signals from Splunk [REST]
DETECT · gemini-2.0-flash-v2.3 dropped 52.1% (0.84 -> 0.402) — REGRESSION
INVESTIGATE · fetched 4 failing calls [REST]
INVESTIGATE · gpt-oss root cause: authentication/authorization [HIGH] -> rollback
DECIDE · rollback gemini-2.0-flash-v2.3 → gemini-2.0-flash-v2.2
ACT    · executed: Active model v2.3 -> v2.2. Traffic restored.
```

The agent's decision, read back out of Splunk (`sourcetype=llm_agent_actions`):

```json
{"status":"regression_remediated","action.kind":"rollback",
 "action.target":"gemini-2.0-flash-v2.3",
 "result.detail":"Active model gemini-2.0-flash-v2.3 -> gemini-2.0-flash-v2.2. Traffic restored."}
```

## The quality metric

Groundedness (0–1) via LLM-as-judge. Validated against a labelled benchmark:
**0.621** with retrieval context vs **0.158** without. This single score feeds
both Splunk anomaly detection and the agent's detection step.

## How we built it

Python package (`llmwatch/`): `collector` (HEC), `judge` (hosted-model
LLM-as-judge), `mcp_client` (MCP / REST read), `agent` (the loop), `actions`
(remediation + approval gate). The MCP client performs the streamable-HTTP
`initialize` handshake and parses JSON or SSE replies. Secrets come only from
the environment and are masked in logs; prompts are hashed before ingestion.

## Run it

```bash
python demo.py --auto                     # full loop, zero network, ~5s
SPLUNK_USER=… SPLUNK_PASSWORD=… ./run_live.sh   # live against real Splunk
python -m pytest tests/ -q                # 9 logic tests
```

## What's next

Multi-signal scoring (latency + cost + groundedness), per-tenant baselines,
and a Splunk app package so any team enables LLM quality observability in minutes.

## Built with

`splunk` · `splunk-hec` · `spl` · `splunk-mcp-server` · `splunk-hosted-models`
· `dashboard-studio` · `python`
