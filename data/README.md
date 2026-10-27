# Fictional input pack

Generated with `python make_data.py`, numpy seed 42. All records are synthetic, in AED and units. No live systems, people or market feeds are represented. Snapshot: 2026-10-26 18:00 UTC. Sales: 2026-07-29 through 2026-10-26 inclusive. Forecast: 2026-10-27 through 2026-11-25.

| File | Grain / contents |
|---|---|
| sku_master.csv | 20 products, type, semiconductor flag, value and margin |
| sales_history.csv | SKU/location/date, observed units, stockout flag, bulk classification; 108 missing rows |
| inventory.csv | 60 SKU/location records; available is already NET of reservations; reserved is additional committed stock |
| stock_age.csv | Available-stock batches, units and age (reserved stock excluded) |
| safety_stock.csv | SKU/location buffer |
| inbound_orders.csv | Open quantity, ETA, supplier lead, shipping route |
| transfer_costs.csv | SKU and directed location pair, lead, fixed and per-unit AED costs |
| holding_costs.csv | SKU/unit/day holding cost and one-time ageing exposure penalty |
| events.csv | Exactly two dated FICTIONAL scenarios; pipe-separated SKU whitelist |
| answer_key.csv | Versioned planted-case checklist and latent regular daily demand, for evaluation ONLY |

Source tables carry `row_id`, `timestamp`, `source_system`. Row IDs remain stable when sales rows are omitted. Missing grid dates are synthetic imputation placeholders, never observations. The engine never loads `answer_key.csv`.

Planted cases are listed individually in the answer key: main charger imbalance, two stockout intervals, 108 absent sales rows, one bulk order (+180), five old-batch positions, two inbound-too-late shortages, low-margin SKU05 with uneconomic routes, one stale manual record, and two fictional events. Latent demand excludes the non-recurring bulk order. The main demo's 200/350/150 demand values are generating rates, not guaranteed fitted forecasts.

Assumptions: available excludes reserved; stock-age batches describe available stock only; FEFO consumption; constant margins/costs; fixed event delays move inbound ETAs, never unlisted products; no demand uplift in the supplied scenarios. Events do not alter internal transfer lead times. Shipping delay is scoped to listed SKUs AND the single supplied inbound route. Generation rewrites the demo input CSVs but never executes or changes approvals. Planner corrections are session-local; export corrected tables from the UI if needed.
