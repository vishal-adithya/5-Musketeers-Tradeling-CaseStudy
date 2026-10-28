# GulfTrade evaluation report

Generated UTC: 2026-10-27T11:17:50.066467+00:00. Seed 42; answer-key version 1.0. No data or parameters tuned to this holdout.

## Fixed 60/30-day backtest
Training: 2026-07-29 through 2026-09-26 (60 days). Holdout: 2026-09-27 through 2026-10-26 (30 days), 60 SKU-location series. Model uses only earlier sales, with trailing 28-day cleaning and weekday factors. No events or latent truth enter the forecast. Current stock metadata is not used to fit demand; this is a forecast backtest, not a historical inventory replay.

Primary target is synthetic latent normal demand stored separately in the answer key. This excludes the planted bulk order and retains hidden demand on stockout/missing days. Real deployments do not have this ground truth. Observed-sales errors are also shown, omitting absent observations and retaining stockout zeros and bulk sales.

| model | target | MAPE_pct | WAPE_pct | observations | zero_actual_excluded_from_MAPE |
| --- | --- | --- | --- | --- | --- |
| Cleaned weekday model | Daily latent normal demand | 46.82 | 62.37 | 1800 | 473 |
| Cleaned weekday model | Daily observed sales (missing omitted) | 46.95 | 68.22 | 1766 | 475 |
| Cleaned weekday model | 30-day latent totals per position | 17.03 | 14.48 | 60 | 0 |
| Raw trailing-28 mean baseline | Daily latent normal demand | 43.12 | 60.00 | 1800 | 473 |
| Raw trailing-28 mean baseline | Daily observed sales (missing omitted) | 43.10 | 65.94 | 1766 | 475 |
| Raw trailing-28 mean baseline | 30-day latent totals per position | 17.47 | 15.16 | 60 | 0 |

The cleaned model **does not outperform** the baseline on daily latent WAPE (62.37% vs 60.00%). Improvement is not promised. MAPE excludes zero actuals; WAPE includes their absolute errors. Aggregate metrics score 30-day totals per position; daily metrics score individual days.

P10–P90 coverage of held-out 30-day latent totals: **56.67%** (nominal 80%). Intervals use independent residual variance without parameter uncertainty; poor coverage signals under-calibration, not certainty. There is only one split and a small synthetic sample.

## Planted-case and constraint checks
**30/30 checks passed.**

| check | passed | detail |
| --- | --- | --- |
| main-demo | True | SKU01 / Abu Dhabi: shortage and late-inbound classification |
| late-inbound-1 | True | SKU09 / Abu Dhabi: shortage and late-inbound classification |
| late-inbound-2 | True | SKU13 / Sharjah: shortage and late-inbound classification |
| uneconomic | True | Economically unattractive: expected benefit AED 19.06 minus transfer cost AED 231.80 gives net AED -212.74 <= 0. |
| missing | True | 108 missing grid dates detected |
| bulk | True | Non-recurring bulk spike winsorised |
| stale | True | Manual/old snapshot flagged |
| stockout-1 | True | Stockout zeros flagged and imputed, not treated as no demand |
| stockout-2 | True | Stockout zeros flagged and imputed, not treated as no demand |
| age-SKU01-Dubai | True | SKU01 / Dubai: old batch exposed |
| age-SKU01-Sharjah | True | SKU01 / Sharjah: old batch exposed |
| age-SKU05-Dubai | True | SKU05 / Dubai: old batch exposed |
| age-SKU10-Dubai | True | SKU10 / Dubai: old batch exposed |
| age-SKU17-Sharjah | True | SKU17 / Sharjah: old batch exposed |
| None: source budgets | True | Aggregated outbound <= physical surplus after forecast + safety; inbound never exported |
| None: lead times | True | Every transfer arrives strictly before first projected stockout |
| None: positive economics | True | No nonpositive-net proposal accepted |
| None: impact reconciliation | True | Marginal proposal benefits sum to network before/after benefit |
| component_shortage: source budgets | True | Aggregated outbound <= physical surplus after forecast + safety; inbound never exported |
| component_shortage: lead times | True | Every transfer arrives strictly before first projected stockout |
| component_shortage: positive economics | True | No nonpositive-net proposal accepted |
| component_shortage: impact reconciliation | True | Marginal proposal benefits sum to network before/after benefit |
| component_shortage: forecast whitelist | True | Unlisted SKU forecasts and evidence unchanged |
| component_shortage: inbound whitelist and route | True | Only listed SKU AND supplied route ETAs delayed |
| shipping_delay: source budgets | True | Aggregated outbound <= physical surplus after forecast + safety; inbound never exported |
| shipping_delay: lead times | True | Every transfer arrives strictly before first projected stockout |
| shipping_delay: positive economics | True | No nonpositive-net proposal accepted |
| shipping_delay: impact reconciliation | True | Marginal proposal benefits sum to network before/after benefit |
| shipping_delay: forecast whitelist | True | Unlisted SKU forecasts and evidence unchanged |
| shipping_delay: inbound whitelist and route | True | Only listed SKU AND supplied route ETAs delayed |

## Current 30-day normal-plan impact (AED / units)
| plan | shortage_units | ageing_exposure_units | holding_cost_aed | ageing_exposure_aed | lost_margin_aed | ending_units | transfer_cost_aed | net_benefit_aed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline: raw mean, no transfers | 531.66 | 5.79 | 1637.07 | 4.63 | 5732.83 | 2484.35 | 0.00 | 0.00 |
| Before: cleaned forecast, no transfers | 452.16 | 2.42 | 1664.85 | 1.93 | 6432.36 | 2568.69 | 0.00 | 0.00 |
| After: all proposals, not executed | 96.50 | 2.42 | 1605.93 | 1.93 | 209.35 | 2213.03 | 370.30 | 5911.64 |

Baseline and cleaned demand differ, so baseline-to-before differences are not causal transfer savings. Net benefit is after-versus-before under the same cleaned P50 demand, less variable and fixed route costs. After assumes every proposal, not approval or execution. Daily stock flow preserves shortages before late receipts. Transit holding is included. Ageing savings use the fixed initially-over-120-day cohort, only crediting consumption rather than relocation; no negative exposure or double credit. Replenishment is unpriced and excluded.

## Limitations and unverified capabilities
Greedy, single-hop, unconstrained warehouse capacity; no service-level optimisation or robust stochastic inventory policy. P10/P90 are approximate and not independently calibrated. FEFO, constant margins, constant unit holding and ageing penalties, and all fictional event settings are assumptions. Reservations are already excluded from available. Corrected available counts can conflict with batch totals and are flagged/capped. No real supplier availability or live event claims. Human approvals are local intent logs, not permission enforcement or stock movements. LLM tool orchestration is exercised with fake model responses in pytest; live provider accuracy, latency and costs require API-enabled testing. UI interaction tests run without a provider. No production readiness is claimed.
