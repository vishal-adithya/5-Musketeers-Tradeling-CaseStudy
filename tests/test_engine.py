import math
import numpy as np
import pandas as pd
import pytest
from make_data import generate
from engine.data_loader import load_data, validate
from engine.quality import assess_quality
from engine.forecast import forecast
from engine.state import run_pipeline, Correction, Overrides, apply_corrections, PlanningSession
from engine.scenarios import apply_scenario
from engine.simulation import simulate


def test_seed_reproducibility(tmp_path, data):
    first = generate(tmp_path / 'one')
    second = generate(tmp_path / 'two')
    assert all(first[k].equals(second[k]) for k in first)
    assert first['inventory'].available.sum() == 5000
    assert len(first['sales_history']) == 5292
    assert 'answer_key' not in data.tables
    assert load_data(tmp_path / 'one').tables['inventory'].equals(data.tables['inventory'])


@pytest.mark.parametrize('table,field,value', [('inventory', 'available', -1), ('inventory', 'reserved', np.nan),
                                              ('transfer_costs', 'lead_days', 0), ('safety_stock', 'safety_stock', 1.2)])
def test_invalid_values(data, table, field, value):
    invalid = data.copy()
    invalid.tables[table][field] = invalid.tables[table][field].astype(float)
    invalid.tables[table].loc[0, field] = value
    with pytest.raises(ValueError):
        validate(invalid)


def test_duplicate_and_unknown_keys(data):
    bad = data.copy()
    bad.tables['inventory'] = pd.concat([bad.tables['inventory'], bad.tables['inventory'].iloc[[0]]])
    with pytest.raises(ValueError, match='unique'):
        validate(bad)
    bad = data.copy()
    bad.tables['inbound_orders'].loc[0, 'sku'] = 'invented'
    with pytest.raises(ValueError, match='unknown'):
        validate(bad)


def test_unified_stock(result, data):
    assert len(result.stock) == 60
    assert result.stock.available.sum() == 5000
    assert result.stock.incoming.sum() == data.tables['inbound_orders'].quantity.sum()
    assert {'source_system', 'timestamp', 'reserved', 'evidence', 'data_quality'} <= set(result.stock)


def test_quality_and_cleaning(result):
    assert result.quality.missing_days.sum() == 108
    assert result.quality.stockout_days.sum() == 14
    assert result.quality.spike_days.sum() >= 1
    assert result.quality.query('sku == "SKU02" and location == "Sharjah"').stale.iloc[0]
    stockout = result.cleaned_sales.query('stockout_distorted')
    assert stockout.units.eq(0).all() and stockout.clean_units.gt(0).all()
    bulk = result.cleaned_sales.query('order_type == "bulk"').iloc[0]
    assert bulk.clean_units < bulk.units / 3
    assert not result.cleaned_sales.clean_units.isna().any()


def test_forecast_intervals_and_demo(result):
    f = result.forecasts
    assert len(f) == 60 and len(result.daily_forecasts) == 1800
    assert (f.p10 >= 0).all() and (f.p10 <= f.p50).all() and (f.p50 <= f.p90).all()
    demo = f.query('sku == "SKU01"').set_index('location')
    for loc, expected in [('Dubai', 200), ('Abu Dhabi', 350), ('Sharjah', 150)]:
        assert abs(demo.loc[loc, 'p50'] - expected) < expected * 0.25
    assert all(any('Assumption' in s for s in row) for row in f.assumptions)
    aggregate = result.daily_forecasts.groupby(['sku', 'location']).p50.sum()
    assert np.allclose(aggregate, f.set_index(['sku', 'location']).p50.sort_index())


def test_planted_imbalances(result):
    for sku, loc in [('SKU01', 'Abu Dhabi'), ('SKU09', 'Abu Dhabi'), ('SKU13', 'Sharjah')]:
        row = result.imbalances.set_index(['sku', 'location']).loc[(sku, loc)]
        assert row.shortage_gap > 0 and row.shortage_units > 0
        if sku != 'SKU01':
            assert row.incoming_in_time == 0 and row.late_incoming > 0
    assert result.imbalances.aged_units.gt(0).sum() >= 4


def test_transfer_constraints(result):
    recs = result.recommendations
    assert recs.net_benefit_aed.gt(0).all()
    assert recs.net_benefit_aed.is_monotonic_decreasing
    for key, group in recs.groupby(['sku', 'from_location']):
        source = result.imbalances.set_index(['sku', 'location']).loc[key]
        assert group.quantity.sum() <= source.real_surplus
        assert source.available - group.quantity.sum() >= source.p50 + source.safety_stock
        assert group.aged_quantity.sum() <= source.aged_units
    assert (recs.lead_days < recs.stockout_day).all()
    assert (recs.quantity % 1 == 0).all()
    assert not recs.sku.eq('SKU05').any()
    assert recs.query('sku == "SKU01" and from_location == "Dubai" and to_location == "Abu Dhabi"').shape[0] == 1


def test_rejected_transfer_and_replenishment(result):
    rejected = result.rejections.query('sku == "SKU05" and to_location == "Abu Dhabi"')
    assert len(rejected) and rejected.net_benefit_aed.le(0).all()
    assert rejected.reason.str.contains('Economically unattractive').all()
    assert len(result.replenishment.query('sku == "SKU05" and location == "Abu Dhabi"')) == 1


def test_impact_reconciles(result):
    before, after = result.impact.iloc[1], result.impact.iloc[2]
    assert after.shortage_units <= before.shortage_units
    assert after.net_benefit_aed == pytest.approx(result.recommendations.net_benefit_aed.sum())
    assert after.transfer_cost_aed == pytest.approx(result.recommendations.transfer_cost_aed.sum())
    assert before.ending_units - after.ending_units == pytest.approx(before.shortage_units - after.shortage_units)
    assert after.ageing_exposure_units >= 0
    assert 'not executed' in after.plan


@pytest.mark.parametrize('scenario_fixture', ['component', 'shipping'])
def test_events_strictly_scoped(data, result, request, scenario_fixture):
    changed = request.getfixturevalue(scenario_fixture)
    listed = changed.event['affected_skus'].split('|')
    pd.testing.assert_frame_equal(result.forecasts.query('sku not in @listed').reset_index(drop=True),
                                  changed.forecasts.query('sku not in @listed').reset_index(drop=True))
    original = data.tables['inbound_orders'].set_index('row_id')
    altered = changed.data.tables['inbound_orders'].set_index('row_id')
    for key in original.index:
        eligible = original.loc[key, 'sku'] in listed
        if scenario_fixture == 'shipping':
            eligible &= original.loc[key, 'shipping_route'] == changed.event['shipping_route']
        days = (pd.Timestamp(altered.loc[key, 'arrival_date']) - pd.Timestamp(original.loc[key, 'arrival_date'])).days
        assert days == (changed.event['delay_days'] if eligible else 0)
    assert not changed.forecasts.query('sku == "SKU05"').event_applied.ne('None').any()


def test_scenario_is_not_cumulative(data):
    a, _ = apply_scenario(data, 'component_shortage')
    b, _ = apply_scenario(data, 'component_shortage')
    pd.testing.assert_frame_equal(a.tables['inbound_orders'], b.tables['inbound_orders'])
    assert data.tables['inbound_orders'].arrival_date.iloc[0] == '2026-10-31'
    with pytest.raises(ValueError):
        apply_scenario(data, 'invented')
    with pytest.raises(ValueError):
        apply_scenario(data, 'shipping_delay', demand_multiplier=1.4)


def test_explicit_demand_assumption_whitelist(data, result):
    changed, event = apply_scenario(data, 'component_shortage', demand_multiplier=1.2)
    f, _ = forecast(changed, result.cleaned_sales, result.quality, event)
    base = result.forecasts.set_index(['sku', 'location']).p50
    altered = f.set_index(['sku', 'location']).p50
    for key in base.index:
        assert altered[key] == pytest.approx(base[key] * (1.2 if key[0] in event['affected_skus'].split('|') else 1))


def test_correction_recomputes_atomically(data, result):
    original = data.tables['inventory'].query('sku == "SKU01" and location == "Abu Dhabi"').iloc[0]
    correction = Correction(table='inventory', row_id=original.row_id, field='available', value=400, reason='Reconciled planner count')
    revised = run_pipeline(data, {'records': [correction.model_dump()]})
    assert revised.snapshot_id != result.snapshot_id
    assert revised.recommendations.query('sku == "SKU01"').empty
    assert revised.impact.iloc[1].shortage_units < result.impact.iloc[1].shortage_units
    assert data.tables['inventory'].query('row_id == @original.row_id').available.iloc[0] == 100
    ref = revised.evidence[f'inventory:{original.row_id}']
    assert ref['source_system'] == 'planner_correction' and ref['original_source_system'] == 'mock_erp'
    invalid = correction.model_copy(update={'value': -10})
    with pytest.raises(ValueError):
        apply_corrections(data, [invalid])


def test_sales_correction_changes_forecast(data, result):
    sales = data.tables['sales_history']
    row = sales.query('sku == "SKU01" and location == "Abu Dhabi" and stockout').iloc[0]
    corrected = apply_corrections(data, [Correction(table='sales_history', row_id=row.row_id, field='stockout', value=False, reason='Demo: confirmed closure rather than stockout')])
    cleaned, quality = assess_quality(corrected)
    f, _ = forecast(corrected, cleaned, quality)
    assert f.query('sku == "SKU01" and location == "Abu Dhabi"').p50.iloc[0] != result.forecasts.query('sku == "SKU01" and location == "Abu Dhabi"').p50.iloc[0]


def test_every_recommendation_traceable(result):
    for action in result.recommendations.itertuples():
        assert len(action.evidence) > 10
        for ref in action.evidence:
            row = result.evidence[ref]
            assert row['row_id'] and row['timestamp'] and row['source_system']
        tables = {result.evidence[ref]['table'] for ref in action.evidence}
        assert {'inventory', 'sales_history', 'transfer_costs', 'holding_costs', 'sku_master', 'safety_stock', 'stock_age'} <= tables


def test_all_zero_sales_safe(data):
    zero = data.copy()
    zero.tables['sales_history']['units'] = 0
    zero.tables['sales_history']['stockout'] = False
    zero.tables['sales_history']['order_type'] = 'regular'
    clean, quality = assess_quality(zero)
    f, daily = forecast(zero, clean, quality)
    assert f[['p10', 'p50', 'p90']].eq(0).all().all()
    assert simulate(zero, daily).shortage_units.eq(0).all()


def test_late_arrival_does_not_erase_lost_sales(data, result):
    altered = data.copy()
    orders = altered.tables['inbound_orders']
    mask = orders.sku.eq('SKU09')
    orders.loc[mask, 'arrival_date'] = '2026-11-15'
    projection = simulate(altered, result.daily_forecasts)
    row = projection.query('sku == "SKU09" and location == "Abu Dhabi"').iloc[0]
    assert row.stockout_day < 20 and row.shortage_units > 0 and row.ending_units > 0
