import numpy as np
import pandas as pd
from engine.data_loader import DataSet, KEYS, refs
from engine.simulation import simulate


def find_imbalances(data: DataSet, stock: pd.DataFrame, forecast: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    base = stock.drop(columns=['evidence']).merge(forecast, on=KEYS).merge(
        data.tables['safety_stock'][KEYS + ['safety_stock']], on=KEYS)
    projection = simulate(data, daily)[KEYS + ['stockout_day', 'shortage_units']]
    base = base.merge(projection, on=KEYS)
    age = data.tables['stock_age'].query('age_days > 120').groupby(KEYS).units.sum().rename('aged_units')
    base = base.merge(age, on=KEYS, how='left').fillna({'aged_units': 0})
    inbound = data.tables['inbound_orders']
    timely, late, evidence = [], [], []
    for row in base.itertuples():
        orders = inbound[(inbound.sku == row.sku) & (inbound.location == row.location)]
        days = (pd.to_datetime(orders.arrival_date)-data.as_of).dt.days
        mask = days.le(30) & days.lt(row.stockout_day)
        timely.append(float(orders.loc[mask, 'quantity'].sum()))
        late.append(float(orders.loc[~mask, 'quantity'].sum()))
        ev = list(row.evidence)
        for name in ['inventory', 'safety_stock', 'stock_age', 'inbound_orders']:
            table = data.tables[name]
            ev += refs(name, table[(table.sku == row.sku) & (table.location == row.location)])
        evidence.append(sorted(set(ev)))
    base['incoming_in_time'], base['late_incoming'], base['evidence'] = timely, late, evidence
    base['shortage_gap'] = (base.p50 + base.safety_stock - base.available - base.incoming_in_time).clip(lower=0)
    base['real_surplus'] = (base.available - base.p50 - base.safety_stock).clip(lower=0).apply(np.floor)
    base['excess_units'] = (base.available + base.incoming_in_time - base.p50 - base.safety_stock).clip(lower=0)
    base['aged_units'] = np.minimum(base.aged_units, base.available)
    base['status'] = [', '.join(filter(None, ['Shortage' if r.shortage_gap > 0 else '',
                     'Excess' if r.excess_units > 0 else '', 'Ageing' if r.aged_units > 0 else ''])) or 'Balanced'
                     for r in base.itertuples()]
    return base
