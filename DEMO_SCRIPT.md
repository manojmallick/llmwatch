# LLMWatch — 3-Minute Demo Script

**Goal:** show the agent detect and *roll back* a real LLM quality regression on
a live Splunk instance. Record the terminal + the Splunk UI (`localhost:8989`).

> Pre-roll setup (off camera): `SPLUNK_USER=… SPLUNK_PASSWORD=… ./run_live.sh`
> once so the index/HEC/token exist. Then record a clean run.

---

### [0:00–0:15] HOOK
> *"Your LLM was updated last night. Its answers got 50% less grounded. No error
> fired. No dashboard turned red. Your customers noticed before you did."*

Show the Splunk Quality Observatory dashboard, v2.3 line dropping off a cliff.

### [0:15–0:45] THE INSTRUMENTATION
> *"LLMWatch logs every LLM call into Splunk through HEC — prompt hashed,
> groundedness scored. This is real ingestion into `index=llmwatch`."*

Run `./run_live.sh`. As it seeds, cut to Splunk Search:
`index=llmwatch sourcetype=llm_events | stats avg(groundedness_score) by model_version bucket`
— show the live table: **v2.3 current 0.40 vs baseline 0.84.**

### [0:45–1:30] THE AGENT SENSES + ROOT-CAUSES
Show the terminal narrative live:
```
SENSE  · pulled 2 model signals from Splunk [REST]
DETECT · gemini-2.0-flash-v2.3 dropped 52.1% (0.84 -> 0.402) — REGRESSION
INVESTIGATE · fetched 4 failing calls [REST]
INVESTIGATE · gpt-oss root cause: authentication/authorization [HIGH] -> rollback
```
> *"The agent reads Splunk itself — over the MCP Server in Cloud, the REST
> search API here. It pulls the failing calls and asks a Splunk hosted model:
> what broke? Answer: the v2.3 update degraded security-domain answers."*

### [1:30–2:15] THE AGENT ACTS — this is the moment
```
DECIDE · rollback gemini-2.0-flash-v2.3 → gemini-2.0-flash-v2.2
ACT    · executed: Active model v2.3 -> v2.2. Traffic restored.
LOG    · agent decision written to index=llmwatch (audit trail)
```
> *"It doesn't just alert a human. It rolls back the bad model — and because
> rollback is destructive, in non-autonomous mode it waits for one click of
> approval. Responsible autonomy."*

Cut to Splunk: `index=llmwatch sourcetype=llm_agent_actions` — show the agent's
own decision logged in Splunk. *"Full audit trail. The agent shows its work."*

### [2:15–2:40] THE ARCHITECTURE
One diagram: HEC → SPL → agent (MCP/REST read → hosted-model root-cause →
action) → audit back to Splunk → Dashboard + Alerts.
> *"LLM-as-judge groundedness, validated 0.62 with context vs 0.16 without.
> Splunk scale. One agent closing the loop."*

### [2:40–3:00] CLOSE
> *"LLMWatch. Your production AI, observed — and defended. Built on Splunk:
> HEC, SPL, the MCP Server, and Splunk hosted models."*

`github.com/manojmallick/llmwatch`

---

**Recording checklist**
- [ ] Terminal font large; colors on (the narrative is color-coded).
- [ ] Show at least one *live SPL query in the Splunk UI* (proves it's real).
- [ ] Show the `llm_agent_actions` audit row — the agent's decision in Splunk.
- [ ] Keep under 3:00. The rollback moment (1:30–2:15) is the whole pitch.
