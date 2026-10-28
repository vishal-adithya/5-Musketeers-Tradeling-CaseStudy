"""Generate the fictional, reproducible GulfTrade demonstration input pack."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
AS_OF = pd.Timestamp('2026-10-26')
LOCATIONS = ['Dubai', 'Abu Dhabi', 'Sharjah']


def generate(output: Path = ROOT / 'data', seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    output.mkdir(parents=True, exist_ok=True)
    timestamp = '2026-10-26T18:00:00Z'
    types = ['USB-C chargers', 'phone cables', 'wireless mice', 'keyboards', 'power banks']
    master = []
    for i in range(20):
        product = types[i // 4]
        master.append(dict(sku=f'SKU{i+1:02}', name=f'{product} model {i % 4 + 1}',
                           product_type=product, semiconductor_dependent=product != 'phone cables',
                           unit_margin_aed=0.1 if i == 4 else [18, 5, 12, 20, 16][i // 4],
                           unit_value_aed=[40, 8, 25, 50, 35][i // 4]))
    inventory, sales, age, safety, inbound, costs, holding, truth = [], [], [], [], [], [], [], []
    dates = pd.date_range(end=AS_OF, periods=90)
    fixed = {('SKU01', 'Dubai'): 500, ('SKU01', 'Abu Dhabi'): 100, ('SKU01', 'Sharjah'): 300,
             ('SKU05', 'Dubai'): 220, ('SKU05', 'Abu Dhabi'): 15, ('SKU05', 'Sharjah'): 0,
             ('SKU09', 'Abu Dhabi'): 12, ('SKU13', 'Sharjah'): 10}
    other = [(m['sku'], loc) for m in master for loc in LOCATIONS if (m['sku'], loc) not in fixed]
    weights = rng.uniform(0.6, 1.4, len(other))
    allocation = np.floor(weights / weights.sum() * (5000 - sum(fixed.values()))).astype(int)
    allocation[:5000 - sum(fixed.values()) - allocation.sum()] += 1
    available = fixed | dict(zip(other, allocation.tolist()))
    planted_age = {('SKU01', 'Dubai'), ('SKU01', 'Sharjah'), ('SKU05', 'Dubai'),
                   ('SKU10', 'Dubai'), ('SKU17', 'Sharjah')}
    for m in master:
        sku = m['sku']
        holding.append(dict(sku=sku, per_unit_day_aed=0.015, ageing_penalty_aed=0.8))
        for loc in LOCATIONS:
            qty = available[sku, loc]
            stale = sku == 'SKU02' and loc == 'Sharjah'
            inventory.append(dict(sku=sku, location=loc, available=qty, reserved=int(rng.integers(2, 10)),
                                  timestamp='2026-10-15T09:00:00Z' if stale else timestamp,
                                  source_system='manual_sheet' if stale else 'mock_erp'))
            safety.append(dict(sku=sku, location=loc, safety_stock=20 if sku == 'SKU01' else 8))
            old = min(qty, 160 if sku == 'SKU01' else 40) if (sku, loc) in planted_age else 0
            age.append(dict(sku=sku, location=loc, batch_id=f'{sku}-{loc}-old', units=old, age_days=145))
            age.append(dict(sku=sku, location=loc, batch_id=f'{sku}-{loc}-fresh', units=qty-old, age_days=30))
            rate = rng.uniform(0.7, 2.1)
            if sku == 'SKU01':
                rate = {'Dubai': 200/30, 'Abu Dhabi': 350/30, 'Sharjah': 150/30}[loc]
            if (sku, loc) in {('SKU05', 'Abu Dhabi'), ('SKU09', 'Abu Dhabi'), ('SKU13', 'Sharjah')}:
                rate = 2.8
            if sku == 'SKU05' and loc == 'Sharjah':
                rate = 0.5
            for date in dates:
                factor = [1.06, 1.08, 1.02, 1.04, 0.96, 0.9, 0.94][date.dayofweek]
                demand = int(rng.poisson(rate * factor))
                stockout = ((sku, loc) == ('SKU01', 'Abu Dhabi') and AS_OF-pd.Timedelta(days=22) <= date <= AS_OF-pd.Timedelta(days=16)) or ((sku, loc) == ('SKU09', 'Abu Dhabi') and AS_OF-pd.Timedelta(days=48) <= date <= AS_OF-pd.Timedelta(days=42))
                if stockout:
                    demand = max(1, demand)
                bulk = (sku, loc, date) == ('SKU06', 'Dubai', AS_OF-pd.Timedelta(days=9))
                sales.append(dict(sku=sku, location=loc, date=date.date().isoformat(),
                                  units=0 if stockout else demand + (180 if bulk else 0),
                                  stockout=stockout, order_type='bulk' if bulk else 'regular'))
                truth.append(dict(case_id=f'truth-{sku}-{loc}-{date.date()}', kind='demand_truth',
                                  sku=sku, location=loc, start_date=str(date.date()), end_date=str(date.date()),
                                  expected=demand, note='Latent normal demand; evaluation only, never an engine input.'))
        for source in LOCATIONS:
            for destination in LOCATIONS:
                if source == destination:
                    continue
                costs.append(dict(sku=sku, from_location=source, to_location=destination,
                                  lead_days=2 if source == 'Dubai' else 3,
                                  variable_cost_aed=0.7 if source == 'Dubai' else 1.1,
                                  fixed_cost_aed=180 if sku == 'SKU05' else (8 if source == 'Dubai' else 15)))
    for sku, loc, units, days, route in [('SKU01', 'Abu Dhabi', 40, 5, 'Jebel Ali-Abu Dhabi'),
                                        ('SKU09', 'Abu Dhabi', 100, 45, 'Jebel Ali-Abu Dhabi'),
                                        ('SKU13', 'Sharjah', 110, 42, 'Jebel Ali-Sharjah'),
                                        ('SKU02', 'Dubai', 50, 12, 'Jebel Ali-Dubai'),
                                        ('SKU17', 'Sharjah', 50, 15, 'Jebel Ali-Sharjah')]:
        inbound.append(dict(sku=sku, location=loc, quantity=units,
                            arrival_date=str((AS_OF+pd.Timedelta(days=days)).date()),
                            supplier_lead_days=days, shipping_route=route))
    events = [dict(scenario='component_shortage', label='FICTIONAL: component shortage',
                   affected_skus='SKU01|SKU02|SKU09|SKU13|SKU17', shipping_route='',
                   demand_multiplier=1.0, delay_days=18,
                   assumption='Assumption: listed component-dependent inbound orders delayed 18 days; no demand uplift.'),
              dict(scenario='shipping_delay', label='FICTIONAL: shipping route delay',
                   affected_skus='SKU01|SKU09', shipping_route='Jebel Ali-Abu Dhabi',
                   demand_multiplier=1.0, delay_days=12,
                   assumption='Assumption: only listed SKUs on Jebel Ali-Abu Dhabi inbound route delayed 12 days.')]
    frames = dict(sku_master=pd.DataFrame(master), sales_history=pd.DataFrame(sales),
                  inventory=pd.DataFrame(inventory), stock_age=pd.DataFrame(age), safety_stock=pd.DataFrame(safety),
                  inbound_orders=pd.DataFrame(inbound), transfer_costs=pd.DataFrame(costs),
                  holding_costs=pd.DataFrame(holding), events=pd.DataFrame(events))
    for name, frame in frames.items():
        frame.insert(0, 'row_id', [f'{name}-{i+1:05}' for i in range(len(frame))])
        if 'timestamp' not in frame:
            frame['timestamp'] = timestamp
        if 'source_system' not in frame:
            frame['source_system'] = 'fictional_scenario' if name == 'events' else 'synthetic_seed_42'
    history = frames['sales_history']
    eligible = history.index[~history.stockout & history.order_type.eq('regular') & ~history.date.isin([str(dates[0].date()), str(dates[-1].date())])]
    missing = rng.choice(eligible, size=108, replace=False)
    frames['sales_history'] = history.drop(index=missing).reset_index(drop=True)
    cases = [dict(case_id='main-demo', kind='shortage', sku='SKU01', location='Abu Dhabi', expected=1,
                  note='Dubai 500 / Abu Dhabi 100 / Sharjah 300; underlying 30-day rates 200 / 350 / 150; Dubai transfer expected.'),
             dict(case_id='late-inbound-1', kind='late_inbound_shortage', sku='SKU09', location='Abu Dhabi', expected=1, note='Inbound on day 45 is too late.'),
             dict(case_id='late-inbound-2', kind='late_inbound_shortage', sku='SKU13', location='Sharjah', expected=1, note='Inbound on day 42 is too late.'),
             dict(case_id='uneconomic', kind='unprofitable_transfer', sku='SKU05', location='Abu Dhabi', expected=0, note='Low margin; every route costs more than the total recoverable benefit.'),
             dict(case_id='missing', kind='missing_rows', expected=108, note='Exactly 2% of the complete 5,400-row sales grid omitted.'),
             dict(case_id='bulk', kind='bulk_spike', sku='SKU06', location='Dubai', start_date='2026-10-17', expected=180, note='One extra bulk order; not recurring normal demand.'),
             dict(case_id='stale', kind='stale_record', sku='SKU02', location='Sharjah', expected=1, note='Old manual-sheet stock record.'),
             dict(case_id='stockout-1', kind='stockout', sku='SKU01', location='Abu Dhabi', start_date='2026-10-04', end_date='2026-10-10', expected=7, note='Observed zero; positive latent demand.'),
             dict(case_id='stockout-2', kind='stockout', sku='SKU09', location='Abu Dhabi', start_date='2026-09-08', end_date='2026-09-14', expected=7, note='Observed zero; positive latent demand.')]
    cases += [dict(case_id=f'age-{sku}-{loc}', kind='ageing', sku=sku, location=loc, expected=1, note='145-day batch.') for sku, loc in sorted(planted_age)]
    cases += [dict(case_id=e['scenario'], kind='event', expected=1, note=e['label']+'; whitelist: '+e['affected_skus']) for e in events]
    frames['answer_key'] = pd.DataFrame(cases + truth).fillna('')
    frames['answer_key']['version'] = '1.0'
    assert len(master) == 20 and len(inventory) == 60
    assert frames['inventory'].available.sum() == 5000
    assert len(frames['sales_history']) == 5292
    assert frames['sales_history'].stockout.sum() == 14
    assert frames['sales_history'].order_type.eq('bulk').sum() == 1
    assert frames['events'].scenario.tolist() == ['component_shortage', 'shipping_delay']
    assert frames['stock_age'].query('age_days > 120 and units > 0').shape[0] >= 4
    for name, frame in frames.items():
        frame.to_csv(output / f'{name}.csv', index=False)
    return frames


if __name__ == '__main__':
    result = generate()
    print(f'Generated {len(result)} CSV files: 20 SKUs, 60 stock positions, 5,000 available units, {len(result["sales_history"]):,} sales rows. Seed 42.')
