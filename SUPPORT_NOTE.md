# GulfTrade support note

## Business problem

GulfTrade Supplies is a fictional UAE B2B electronics distributor balancing approximately 5,000 units across 20 SKUs and Dubai, Abu Dhabi and Sharjah. Planners need to identify shortage risk, stranded stock and ageing exposure while avoiding transfers that are too late, consume source safety stock or cost more than their expected commercial benefit.

## Dataset

The project uses a fully synthetic, seeded input pack. It contains master SKU data, 90 days of sales, inventory, safety stock, ageing batches, inbound orders, transfer costs, holding costs, two fictional disruption scenarios and a separate answer key used only for evaluation. Every operational source row has a stable row ID, timestamp and source-system label. See `data/README.md` for data grain and planted cases.

The source pack is canonical CSV. `build_sqlite.py` creates `gulftrade.db` from the same CSVs using `database/schema.sql` for inspection or integration tests. The SQLite artifact is a derived read model, not the application’s operational system of record.

## Method

1. Validate CSV schemas, uniqueness, dates, numeric domains, position relationships, event whitelist and inbound-route scope.
2. Clean the sales grid by marking missing records, stockout-distorted days and non-recurring bulk spikes. Cleaning is disclosed as an assumption rather than treated as observation.
3. Forecast each SKU/location with a trailing, weekday-aware deterministic model and produce P10, P50 and P90 values.
4. Combine available stock, safety stock, forecast demand, timed inbound supply and ageing batches to flag shortages and real surplus.
5. Produce greedy, single-hop transfer recommendations only when source budgets, arrival timing and positive net economics all hold.
6. Compare no-transfer versus proposed-transfer outcomes, with transfer cost and a conservative ageing treatment.
7. Hold every proposal at an explicit human approval interrupt. Decisions are locally logged but never executed.

## Validation results

Run `python evaluate.py` to regenerate `eval_report.md`. The evaluation uses a fixed 60-day training and 30-day holdout split against synthetic latent normal demand held separately from engine inputs. It reports MAPE/WAPE, interval coverage and planted-case/constraint checks. The checked scenarios include the primary charger imbalance, late inbound orders, stockouts, missing sales rows, a bulk spike, stale data, ageing positions, unprofitable transfers and strict disruption whitelists.

Use `python -m pytest` for unit, workflow, UI and hardening coverage. Use `python build_sqlite.py` to check SQLite foreign keys, integrity and core source-table row counts.

## Limitations

- All data, events and supplier references are fictional.
- P10/P50/P90 estimates are uncertain and not independently calibrated.
- Optimisation is greedy and single-hop; it does not model capacity, multi-echelon replenishment, service-level optimisation or execution friction.
- Approvals are local records of planner intent, not permissions or operational movements.
- UI corrections are session-local unless exported.
- The optional LLM is limited to tool-grounded explanation; provider accuracy, latency, cost and security need separate production evaluation.

## Production pilot requirements

A real pilot would require governed ERP/WMS and supplier feeds, role-based access, approval ownership, data freshness SLAs, reconciliation controls, warehouse capacity and transport constraints, supplier commitment data, audit retention, encrypted secrets, monitoring, forecast calibration, alert thresholds, rollback procedures and legal/compliance review. Recommendations must remain human-reviewed until performance and safety controls are validated in production operations.
