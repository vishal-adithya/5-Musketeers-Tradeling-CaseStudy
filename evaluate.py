"""Honest fixed-split backtest and versioned planted-case checks; never tunes data."""
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from engine.data_loader import load_data, ROOT
from engine.quality import assess_quality
from engine.forecast import forecast, baseline_paths
from engine.state import run_pipeline


def error_metrics(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    valid = np.isfinite(actual) & np.isfinite(predicted)
    actual, predicted = actual[valid], predicted[valid]
    positive = actual > 0
    return {'MAPE_pct': float(np.mean(np.abs(actual[positive]-predicted[positive])/actual[positive])*100) if positive.any() else np.nan,
            'WAPE_pct': float(np.abs(actual-predicted).sum()/actual.sum()*100) if actual.sum() else np.nan,
            'observations': len(actual), 'zero_actual_excluded_from_MAPE': int((~positive).sum())}


def backtest(data, answer_key):
    train = data.copy()
    cutoff = data.as_of - pd.Timedelta(days=30)
    history = train.tables['sales_history']
    train.tables['sales_history'] = history[pd.to_datetime(history.date).le(cutoff)].copy()
    train.as_of = cutoff
    cleaned, quality = assess_quality(train)
    summary, prediction = forecast(train, cleaned, quality)
    baseline = baseline_paths(cleaned, prediction)
    truth = answer_key[answer_key.kind.eq('demand_truth')].copy()
    truth['date'] = pd.to_datetime(truth.start_date)
    truth['actual'] = pd.to_numeric(truth.expected)
    truth = truth[truth.date.gt(cutoff) & truth.date.le(data.as_of)]
    keys = ['sku', 'location', 'date']
    joined = prediction.merge(truth[keys + ['actual']], on=keys, validate='one_to_one')
    joined = joined.merge(baseline[keys + ['p50']].rename(columns={'p50': 'baseline'}), on=keys, validate='one_to_one')
    observed = data.tables['sales_history'].copy()
    observed['date'] = pd.to_datetime(observed.date)
    joined = joined.merge(observed[keys + ['units']].rename(columns={'units': 'observed'}), on=keys, how='left', validate='one_to_one')
    if len(joined) != 60 * 30:
        raise ValueError('Expected complete latent holdout truth for 60 SKU-locations and 30 days')
    metrics = []
    for model, col in [('Cleaned weekday model', 'p50'), ('Raw trailing-28 mean baseline', 'baseline')]:
        metrics.append(dict(model=model, target='Daily latent normal demand', **error_metrics(joined.actual, joined[col])))
        metrics.append(dict(model=model, target='Daily observed sales (missing omitted)', **error_metrics(joined.observed, joined[col])))
        aggregate = joined.groupby(['sku', 'location'])[['actual', col]].sum()
        metrics.append(dict(model=model, target='30-day latent totals per position', **error_metrics(aggregate.actual, aggregate[col])))
    aggregate_actual = joined.groupby(['sku', 'location']).actual.sum().rename('actual')
    intervals = summary.merge(aggregate_actual, on=['sku', 'location'])
    coverage = float(((intervals.actual >= intervals.p10) & (intervals.actual <= intervals.p90)).mean() * 100)
    return pd.DataFrame(metrics), coverage, cutoff, joined


def check_cases(data, results, answer_key):
    base = results['None']
    checks = []
    def add(name, passed, detail):
        checks.append({'check': name, 'passed': bool(passed), 'detail': detail})
    for case in answer_key[~answer_key.kind.eq('demand_truth')].itertuples():
        mask = base.imbalances.sku.eq(case.sku) & base.imbalances.location.eq(case.location)
        positions = base.imbalances[mask]
        if case.kind in {'shortage', 'late_inbound_shortage'}:
            passed = len(positions) == 1 and positions.shortage_gap.iloc[0] > 0
            if case.kind == 'late_inbound_shortage':
                passed &= positions.incoming_in_time.iloc[0] == 0 and positions.late_incoming.iloc[0] > 0
            add(case.case_id, passed, f'{case.sku} / {case.location}: shortage and late-inbound classification')
        elif case.kind == 'unprofitable_transfer':
            rejected = base.rejections.query('sku == @case.sku and to_location == @case.location')
            add(case.case_id, not base.recommendations.sku.eq(case.sku).any() and len(rejected) > 0 and rejected.net_benefit_aed.le(0).all(),
                rejected.reason.iloc[0] if len(rejected) else 'No matching rejection')
        elif case.kind == 'missing_rows':
            add(case.case_id, base.quality.missing_days.sum() == int(case.expected), f'{base.quality.missing_days.sum()} missing grid dates detected')
        elif case.kind == 'bulk_spike':
            date = pd.Timestamp(case.start_date)
            rows = base.cleaned_sales.query('sku == @case.sku and location == @case.location and date == @date')
            add(case.case_id, len(rows) == 1 and rows.spike.iloc[0] and rows.clean_units.iloc[0] < rows.units.iloc[0], 'Non-recurring bulk spike winsorised')
        elif case.kind == 'stockout':
            rows = base.cleaned_sales.query('sku == @case.sku and location == @case.location and date >= @case.start_date and date <= @case.end_date')
            add(case.case_id, rows.stockout_distorted.sum() == int(case.expected) and rows.clean_units.gt(0).all(), 'Stockout zeros flagged and imputed, not treated as no demand')
        elif case.kind == 'ageing':
            add(case.case_id, len(positions) == 1 and positions.aged_units.iloc[0] > 0, f'{case.sku} / {case.location}: old batch exposed')
        elif case.kind == 'stale_record':
            row = base.quality.query('sku == @case.sku and location == @case.location')
            add(case.case_id, row.stale.iloc[0], 'Manual/old snapshot flagged')
    for name, result in results.items():
        recs = result.recommendations
        budgets = result.imbalances.set_index(['sku', 'location']).real_surplus
        quantity_ok = all(group.quantity.sum() <= budgets.loc[key] for key, group in recs.groupby(['sku', 'from_location']))
        lead_ok = (recs.lead_days < recs.stockout_day).all() and recs.lead_days.le(30).all()
        add(f'{name}: source budgets', quantity_ok, 'Aggregated outbound <= physical surplus after forecast + safety; inbound never exported')
        add(f'{name}: lead times', lead_ok, 'Every transfer arrives strictly before first projected stockout')
        add(f'{name}: positive economics', recs.net_benefit_aed.gt(0).all(), 'No nonpositive-net proposal accepted')
        add(f'{name}: impact reconciliation', np.isclose(recs.net_benefit_aed.sum(), result.impact.iloc[2].net_benefit_aed), 'Marginal proposal benefits sum to network before/after benefit')
        if name == 'None':
            continue
        event = result.event
        listed = event['affected_skus'].split('|')
        unaffected = base.forecasts[~base.forecasts.sku.isin(listed)].reset_index(drop=True)
        altered = result.forecasts[~result.forecasts.sku.isin(listed)].reset_index(drop=True)
        add(f'{name}: forecast whitelist', unaffected.equals(altered), 'Unlisted SKU forecasts and evidence unchanged')
        original_orders = data.tables['inbound_orders'].set_index('row_id')
        changed_orders = result.data.tables['inbound_orders'].set_index('row_id')
        scope_ok = True
        for row in original_orders.itertuples():
            eligible = row.sku in listed and (not event['shipping_route'] or row.shipping_route == event['shipping_route'])
            delta = (pd.Timestamp(changed_orders.loc[row.Index, 'arrival_date']) - pd.Timestamp(row.arrival_date)).days
            scope_ok &= delta == (event['delay_days'] if eligible else 0)
        add(f'{name}: inbound whitelist and route', scope_ok, 'Only listed SKU AND supplied route ETAs delayed')
    return pd.DataFrame(checks)


def markdown_table(frame):
    def cell(value):
        if isinstance(value, (float, np.floating)):
            return 'undefined' if not np.isfinite(value) else f'{value:.2f}'
        return str(value).replace('|', '/').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(frame.columns) + ' |', '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |'] +
                     ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None)])


def evaluate(output: Path = ROOT / 'eval_report.md'):
    data = load_data()
    answer_key = pd.read_csv(ROOT / 'data' / 'answer_key.csv', keep_default_na=False)
    metrics, coverage, cutoff, joined = backtest(data, answer_key)
    results = {name: run_pipeline(data, scenario=name) for name in ['None', 'component_shortage', 'shipping_delay']}
    checks = check_cases(data, results, answer_key)
    daily = metrics[metrics.target.eq('Daily latent normal demand')].set_index('model')
    engine_wape = daily.loc['Cleaned weekday model', 'WAPE_pct']
    baseline_wape = daily.loc['Raw trailing-28 mean baseline', 'WAPE_pct']
    verdict = 'outperforms' if engine_wape < baseline_wape else 'does not outperform'
    report = f'''# GulfTrade evaluation report

Generated UTC: {datetime.now(timezone.utc).isoformat()}. Seed 42; answer-key version 1.0. No data or parameters tuned to this holdout.

## Fixed 60/30-day backtest
Training: {joined.date.min() - pd.Timedelta(days=60):%Y-%m-%d} through {cutoff:%Y-%m-%d} (60 days). Holdout: {cutoff + pd.Timedelta(days=1):%Y-%m-%d} through {data.as_of:%Y-%m-%d} (30 days), 60 SKU-location series. Model uses only earlier sales, with trailing 28-day cleaning and weekday factors. No events or latent truth enter the forecast. Current stock metadata is not used to fit demand; this is a forecast backtest, not a historical inventory replay.

Primary target is synthetic latent normal demand stored separately in the answer key. This excludes the planted bulk order and retains hidden demand on stockout/missing days. Real deployments do not have this ground truth. Observed-sales errors are also shown, omitting absent observations and retaining stockout zeros and bulk sales.

{markdown_table(metrics)}

The cleaned model **{verdict}** the baseline on daily latent WAPE ({engine_wape:.2f}% vs {baseline_wape:.2f}%). Improvement is not promised. MAPE excludes zero actuals; WAPE includes their absolute errors. Aggregate metrics score 30-day totals per position; daily metrics score individual days.

P10–P90 coverage of held-out 30-day latent totals: **{coverage:.2f}%** (nominal 80%). Intervals use independent residual variance without parameter uncertainty; poor coverage signals under-calibration, not certainty. There is only one split and a small synthetic sample.

## Planted-case and constraint checks
**{int(checks.passed.sum())}/{len(checks)} checks passed.**

{markdown_table(checks)}

## Current 30-day normal-plan impact (AED / units)
{markdown_table(results['None'].impact)}

Baseline and cleaned demand differ, so baseline-to-before differences are not causal transfer savings. Net benefit is after-versus-before under the same cleaned P50 demand, less variable and fixed route costs. After assumes every proposal, not approval or execution. Daily stock flow preserves shortages before late receipts. Transit holding is included. Ageing savings use the fixed initially-over-120-day cohort, only crediting consumption rather than relocation; no negative exposure or double credit. Replenishment is unpriced and excluded.

## Limitations and unverified capabilities
Greedy, single-hop, unconstrained warehouse capacity; no service-level optimisation or robust stochastic inventory policy. P10/P90 are approximate and not independently calibrated. FEFO, constant margins, constant unit holding and ageing penalties, and all fictional event settings are assumptions. Reservations are already excluded from available. Corrected available counts can conflict with batch totals and are flagged/capped. No real supplier availability or live event claims. Human approvals are local intent logs, not permission enforcement or stock movements. LLM tool orchestration is exercised with fake model responses in pytest; live provider accuracy, latency and costs require API-enabled testing. UI interaction tests run without a provider. No production readiness is claimed.
'''
    output.write_text(report, encoding='utf-8')
    print(f'Report: {output.name}; checks {int(checks.passed.sum())}/{len(checks)}; model daily WAPE {engine_wape:.2f}%; baseline {baseline_wape:.2f}%; interval coverage {coverage:.2f}%.')
    return metrics, checks


if __name__ == '__main__':
    _, checks = evaluate()
    raise SystemExit(0 if checks.passed.all() else 1)
