# LLMWatch Dashboards (Splunk Dashboard Studio)

Three dashboards drive the demo. Build them in Dashboard Studio against
`index=llmwatch`. Design specs and Stitch prompts live in the project doc
(`SPLUNK_Track1_LLMWatch.md`).

| Dashboard | Purpose | Key panels (SPL in `../spl/queries.spl`) |
|---|---|---|
| **1 · Quality Observatory** | Real-time health | Overall quality gauge, hallucination rate, context-impact split, per-model table |
| **2 · Regression Investigation** | Drill-down + root cause | 1-hour timeline, hosted-model root-cause panel, before/after response comparison, **agent action audit** |
| **3 · Quality & Cost** | 30-day efficiency | Quality-vs-cost scatter, quality-per-dollar ranking, context-impact bars |

**Palette (enterprise dark):** bg `#0B0D12` · surface `#151820` · Splunk green
`#65E075` · good `#34C759` · degraded `#FF9500` · poor `#FF3B30`.

Dashboard 2 should include a panel on `sourcetype=llm_agent_actions` so judges
see the agent's decisions and remediations alongside the regression it fixed.
