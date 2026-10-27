"""Daily lost-sales and fixed-age-cohort simulation shared by economics and impact."""
import numpy as np
import pandas as pd
from engine.data_loader import DataSet


def simulate(data: DataSet, daily: pd.DataFrame, actions: list[dict] | None = None) -> pd.DataFrame:
    actions = actions or []
    t = data.tables
    costs = t['holding_costs'].set_index('sku')
    margins = t['sku_master'].set_index('sku').unit_margin_aed
    inbound_by = {key: group for key, group in t['inbound_orders'].groupby(['sku', 'location'])}
    demand_by = {key: group.sort_values('day').p50.to_numpy() for key, group in daily.groupby(['sku', 'location'])}
    old_by = t['stock_age'].loc[t['stock_age'].age_days.gt(120)].groupby(['sku', 'location']).units.sum()
    results = []
    for stock in t['inventory'].itertuples():
        key = (stock.sku, stock.location)
        demand = demand_by[key]
        available = float(stock.available)
        aged = min(available, float(old_by.get(key, 0)))
        receipts = np.zeros(len(demand))
        old_receipts = receipts.copy()
        for order in inbound_by.get(key, pd.DataFrame()).itertuples():
            day = (pd.Timestamp(order.arrival_date) - data.as_of).days
            if 1 <= day <= len(demand):
                receipts[day-1] += order.quantity
        transit_holding = 0.0
        for action in actions:
            if action['sku'] != stock.sku:
                continue
            quantity = action['quantity']
            old = action['aged_quantity']
            if action['from_location'] == stock.location:
                available -= quantity
                aged -= old
                transit_holding += quantity * (action['lead_days'] - 1) * costs.loc[stock.sku, 'per_unit_day_aed']
            if action['to_location'] == stock.location:
                receipts[action['lead_days']-1] += quantity
                old_receipts[action['lead_days']-1] += old
        if available < -1e-8 or aged < -1e-8:
            raise ValueError('Proposals exceed physical or aged stock')
        lost, holding, first_stockout = 0.0, transit_holding, float('inf')
        for day, wanted in enumerate(demand, start=1):
            available += receipts[day-1]
            aged += old_receipts[day-1]
            sold = min(available, wanted)
            missed = wanted - sold
            if missed > 1e-8 and first_stockout == float('inf'):
                first_stockout = day
            lost += missed
            available -= sold
            aged = max(0.0, aged - sold)
            holding += available * costs.loc[stock.sku, 'per_unit_day_aed']
        results.append(dict(sku=stock.sku, location=stock.location, shortage_units=lost,
                            ageing_exposure_units=aged, holding_cost_aed=holding, ending_units=available,
                            ageing_exposure_aed=aged * costs.loc[stock.sku, 'ageing_penalty_aed'],
                            lost_margin_aed=lost * margins.loc[stock.sku], stockout_day=first_stockout))
    return pd.DataFrame(results)


def totals(simulation: pd.DataFrame) -> dict:
    return simulation[['shortage_units', 'ageing_exposure_units', 'holding_cost_aed',
                       'ageing_exposure_aed', 'lost_margin_aed', 'ending_units']].sum().to_dict()
