# LLMWatch — UI Design Prototype

High-fidelity, interactive HTML prototype of the LLMWatch product UI (Stitch
design system, Tailwind + Material Symbols). These three screens define the
target product experience; the **functional** equivalents run live on Splunk
Dashboard Studio (see [`../dashboards/`](../dashboards/)).

| Screen | File | Live Splunk dashboard |
|---|---|---|
| Quality Observatory | [observatory.html](observatory.html) | `llmwatch_observatory` |
| Regression Investigation | [investigation.html](investigation.html) | `llmwatch_regression` |
| Quality & Cost (30-day) | [trends.html](trends.html) | `llmwatch_quality_cost` |

The three screens are cross-linked — the top tabs and left sidebar navigate
between them. Open [observatory.html](observatory.html) (or `index.html`) to start.

**Static captures** for the submission/deck: `observatory.png`, `investigation.png`,
`trends.png` (full renders) and `*_ref.png` (original Stitch references).

**Design system:** see [DESIGN.md](DESIGN.md) — Enterprise Observability palette
(Splunk green `#65e075`, dark surfaces, quality red/amber/green bands), Inter +
JetBrains Mono type.

> Prototype data is illustrative; the live Splunk dashboards render the same
> views from real `index=llmwatch` events.
