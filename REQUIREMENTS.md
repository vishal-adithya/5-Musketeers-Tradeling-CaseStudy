# Requirements extracted from the supplied case study

Source: `Tradeling_Hackathon_Case_Study.pdf`, all three pages, read with pdfplumber. The requested `tradeling.pdf` is not present. The PDF is the business brief; the user's detailed specification adds implementation requirements.

## Business and journey (page 1)
GulfTrade Supplies is a fictional UAE B2B seller. Sara plans roughly 5,000 units, 20 SKUs, five product types, three locations (Dubai, Abu Dhabi, Sharjah), with 90 days of history and a 30-day horizon. This is seller decision support, not an assumption that a marketplace owns inventory.

1. Understand inventory: accept SKU, location, sales, inbound and stock-age records; unify available, reserved and incoming stock while retaining sources and timestamps.
2. Forecast demand: 30-day SKU-location demand, supplied signals, assumptions, uncertainty and quality limitations.
3. Identify imbalances: shortages, excess, ageing and misleading stockout/missing sales history.
4. Recommend actions: quantities, routes and replenishment changes constrained by availability, safety stock, lead times and transfer economics.
5. Explain impact and next steps: rank actions; compare shortages, ageing, holding and transfer costs; require planner approval.

A single correction or changed disruption assumption must update the entire journey.

## Demonstration and scope (page 2)
Normal journey: USB-C charger availability Dubai 500, Abu Dhabi 100, Sharjah 300; indicative 30-day demand 200, 350, 150. Evaluate a Dubai-to-Abu Dhabi transfer only after safety, inbound, lead-time and economic checks. Difficult journey: semiconductor-related supply constraints affect only explicitly listed SKUs. Include two fictional scenarios: component shortage and one shipping-route delay. Include missing records, stockouts, ageing and an economically unattractive transfer, with a separate versioned answer key.

## Trust boundary (pages 2–3)
- No invented demand signals or unsupported event-to-SKU relationships.
- Forecasts are uncertain; this implementation always presents P10/P50/P90.
- Unsupported conclusions are marked assumption or unverified.
- Nothing executes: proposals require explicit human Approve/Reject with a dated audit record.
- This implementation computes every forecast, quantity, cost and impact deterministically in pandas/numpy; the LLM only calls tools and explains evidence.
- Retain source-row identifiers, timestamps and source systems through recommendations.
- Synthetic or explicitly approved anonymised data only; no production credentials or identifiable customer/supplier data.
- Permissions and basic operating arrangements are assumed for the demonstration. Real purchasing, warehouse movements, bookings, production integration and comprehensive regulatory assessment are out of scope.

## Success metrics (page 2)
Compare against recent-average demand with no proactive transfers on the same inventory: forecast error; expected shortage reduction; avoidable excess and ageing; net economic benefit after transfer costs; constraint compliance; clear, cautious explanations. Larger transfers or savings unsupported by evidence are not success.

## Judging criteria (pages 2–3)
| Criterion | Weight | Evidence in this prototype |
|---|---:|---|
| Business relevance and value | 30% | Commercial constraints and before/after impact |
| AI quality and evidence | 25% | Backtest, uncertainty, row-level provenance, scoped events |
| Working prototype | 20% | End-to-end journey and difficult planted cases |
| Seller / planner experience | 15% | Plain-language UI, explanations and editable records |
| Responsible design and scalability | 10% | Human approvals, privacy, permissions and pilot limitations |

## Submission deliverables (pages 2–3)
Working prototype, reproducible source and setup instructions, five-minute normal-and-difficult-case demo, and a short support note describing the business problem, datasets, method, test results, limitations and real-world pilot requirements.

## Implementation acceptance criteria (user specification)
- Python 3.11+, pandas, numpy, pydantic, LangChain current tool-calling API; LangGraph exclusively for approval interrupts; Streamlit seven-tab UI.
- Seed-42 CSV generator; assertions; exact two-event whitelist; separate answer key.
- Unified loader, quality flags, cleaned trailing-28-day/DOW forecast, deterministic uncertainty, imbalances, greedy feasible economic transfers, replenishment suggestions, impact and atomic pipeline reruns.
- Configurable Groq/OpenAI/Anthropic; all numbers and UI work offline; chat clearly disabled without a key.
- Approval CSV with timestamp, proposal identity and pipeline snapshot; record corrections trigger recomputation.
- Pytest coverage, last-30-day holdout evaluation, honest MAPE/WAPE versus baseline and planted-case checks.
- README, DEMO_SCRIPT, SUPPORT_NOTE, requirements.txt, .env.example and generated eval_report.md.
