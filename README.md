# GulfTrade Supplies — Inventory Intelligence Prototype

A reproducible, fictional decision-support prototype for a UAE B2B electronics distributor. It unifies SKU/location stock, sales history, inbound supply, ageing, transfer costs and scoped disruption scenarios into a 30-day planning view.

The application is advisory only: it never creates purchase orders, dispatches stock or changes an external system. A planner must explicitly approve or reject each recommendation; that decision is logged locally.

## What is included

- Seven-tab Streamlit planner for stock, forecasts, imbalances, recommendations, impact, source corrections and grounded assistant chat.
- Deterministic forecasting with P10/P50/P90 ranges, stockout and missing-history treatment, and data-quality flags.
- Feasible, economics-aware transfer proposals and replenishment suggestions.
- Two explicitly fictional disruption scenarios with SKU/route whitelists.
- Human approval interruption and local, append-only decision audit log.
- Seeded synthetic CSV source pack plus an optional SQLite export.
- Automated tests and a fixed-split evaluation report.

## Requirements

- Python 3.11 or later.
- `pip`.
- Optional: a Groq, OpenAI, or Anthropic API key for the Assistant tab. The complete deterministic planner works offline without one.

## Quick start

```bash
cd /Users/zaydankhan/Desktop/5-Musketeers-Tradeling-CaseStudy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python make_data.py
python build_sqlite.py
streamlit run app.py
```

Open the local Streamlit URL printed by the final command. The generated data is deterministic because `make_data.py` uses seed 42.

### Optional Assistant configuration

Copy the example file, then set only one provider key:

```bash
cp .env.example .env
```

For Groq, set `LLM_PROVIDER=groq`, `GROQ_API_KEY=...`, and optionally `GROQ_MODEL=openai/gpt-oss-120b`. OpenAI uses `LLM_PROVIDER=openai` with `OPENAI_API_KEY=...`; Anthropic uses `LLM_PROVIDER=anthropic` with `ANTHROPIC_API_KEY=...`. You may override the model with the provider-specific setting or generic `LLM_MODEL`. Never commit `.env`.

The Assistant only invokes deterministic tools over the current fictional planning snapshot. Provider use may incur cost and transmits selected fictional records to that provider. Without valid configuration, the Assistant tab remains disabled while every other tab works.

## Data and SQLite export

`data/` is the canonical input pack used by the Streamlit app. `make_data.py` rewrites its synthetic CSV files but does not modify approval records.

`build_sqlite.py` imports the canonical CSVs into `gulftrade.db` using `database/schema.sql`, then verifies SQLite integrity and key row counts. It is a reproducible read model for SQL inspection and integration; the live demo app intentionally continues to load CSVs so source-row provenance and test fixtures stay simple.

Useful commands:

```bash
python build_sqlite.py
sqlite3 gulftrade.db ".tables"
sqlite3 gulftrade.db "SELECT sku, location, available FROM inventory WHERE sku = 'SKU01';"
```

The generated `gulftrade.db` is safe to delete and rebuild. `data/README.md` describes the input grain, planted cases and modelling assumptions.

## Validation and evaluation

```bash
python -m pytest
python evaluate.py
```

`evaluate.py` produces `eval_report.md` from a fixed 60-day training and 30-day holdout split. It reports honest MAPE/WAPE comparisons, interval coverage and planted-case/constraint checks. Do not interpret synthetic backtest results as evidence of production performance.

## Operating model and limitations

- Available inventory is already net of reservations; reserved units are shown separately.
- Corrections made in the UI are session-local and trigger a full recomputation. Export a corrected dataset if it must be retained.
- Approval logs are local CSV audit records in `approvals_log.csv`; they record planner intent only and never execute movements.
- Events are fictional assumptions. They affect only their supplied SKU whitelist and, where applicable, the supplied inbound route.
- The transfer optimiser is greedy and single-hop. Warehouse capacity, real-time supplier availability, production integrations, service-level optimisation and real operational permissions are out of scope.

See `DEMO_SCRIPT.md` for the five-minute walkthrough and `SUPPORT_NOTE.md` for the business, method, results and pilot considerations.
