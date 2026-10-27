import hashlib
import math
import pandas as pd
from engine.data_loader import DataSet, refs
from engine.simulation import simulate, totals

ACTION_COLUMNS = ['action_id', 'rank', 'sku', 'from_location', 'to_location', 'quantity', 'aged_quantity',
                  'lead_days', 'stockout_day', 'source_surplus_before', 'avoided_lost_units',
                  'margin_saved_aed', 'holding_saved_aed', 'ageing_saved_aed', 'transfer_cost_aed',
                  'net_benefit_aed', 'why', 'evidence']
REJECTION_COLUMNS = ['sku', 'from_location', 'to_location', 'quantity', 'net_benefit_aed', 'reason', 'evidence']


def optimize(data: DataSet, imbalances: pd.DataFrame, daily: pd.DataFrame):
    positions = imbalances.set_index(['sku', 'location'])
    surplus = positions.real_surplus.to_dict()
    gaps = positions.shortage_gap.to_dict()
    old = positions.aged_units.to_dict()
    actions, rejections = [], []
    routes = data.tables['transfer_costs']
    initial = totals(simulate(data, daily))
    current = initial
    remaining = set(routes.index)
    while remaining:
        candidates, rejected = [], []
        for idx in sorted(remaining):
            route = routes.loc[idx]
            sku, source, dest = route.sku, route.from_location, route.to_location
            src_key, dst_key = (sku, source), (sku, dest)
            if gaps[dst_key] <= 0 or surplus[src_key] < 1:
                continue
            target = positions.loc[dst_key]
            qty = min(int(surplus[src_key]), math.ceil(gaps[dst_key]))
            evidence = list(positions.loc[src_key, 'evidence']) + list(target.evidence)
            evidence += refs('transfer_costs', routes.loc[[idx]])
            for name in ['sku_master', 'holding_costs']:
                evidence += refs(name, data.tables[name].loc[data.tables[name].sku.eq(sku)])
            proposal = dict(sku=sku, from_location=source, to_location=dest, quantity=qty,
                            aged_quantity=min(qty, old[src_key]), lead_days=int(route.lead_days),
                            stockout_day=float(target.stockout_day), source_surplus_before=surplus[src_key],
                            evidence=sorted(set(evidence)))
            reason = ''
            if route.lead_days >= target.stockout_day or route.lead_days > 30:
                reason = f'Lead time {route.lead_days} days does not beat projected first stockout day {target.stockout_day:g} (or exceeds horizon).'
                proposal['net_benefit_aed'] = 0.0
            else:
                after = totals(simulate(data, daily, actions + [proposal]))
                proposal['avoided_lost_units'] = current['shortage_units'] - after['shortage_units']
                proposal['margin_saved_aed'] = current['lost_margin_aed'] - after['lost_margin_aed']
                proposal['holding_saved_aed'] = current['holding_cost_aed'] - after['holding_cost_aed']
                proposal['ageing_saved_aed'] = current['ageing_exposure_aed'] - after['ageing_exposure_aed']
                proposal['transfer_cost_aed'] = qty * route.variable_cost_aed + route.fixed_cost_aed
                proposal['net_benefit_aed'] = proposal['margin_saved_aed'] + proposal['holding_saved_aed'] + proposal['ageing_saved_aed'] - proposal['transfer_cost_aed']
                if proposal['net_benefit_aed'] <= 0:
                    reason = f'Economically unattractive: expected benefit AED {proposal["net_benefit_aed"] + proposal["transfer_cost_aed"]:.2f} minus transfer cost AED {proposal["transfer_cost_aed"]:.2f} gives net AED {proposal["net_benefit_aed"]:.2f} <= 0.'
                else:
                    candidates.append((idx, proposal, after))
            if reason:
                rejected.append((idx, {**proposal, 'reason': reason}))
        if not candidates:
            rejections.extend(value for _, value in rejected)
            break
        idx, best, after = max(candidates, key=lambda item: (item[1]['net_benefit_aed'], -item[0]))
        best['why'] = (f'Assumption-based P50 proposal: {best["quantity"]} units from physical surplus '
                       f'{best["source_surplus_before"]:g}; source keeps its own forecast plus safety. '
                       f'Arrival day {best["lead_days"]} precedes first stockout day {best["stockout_day"]:g}. '
                       'FEFO daily simulation values avoided lost sales and network holding/ageing savings. Nothing executes.')
        key = f'{best["sku"]}|{best["from_location"]}|{best["to_location"]}|{best["quantity"]}'
        best['action_id'] = hashlib.sha256(key.encode()).hexdigest()[:12]
        actions.append(best)
        surplus[best['sku'], best['from_location']] -= best['quantity']
        old[best['sku'], best['from_location']] -= best['aged_quantity']
        gaps[best['sku'], best['to_location']] = max(0, gaps[best['sku'], best['to_location']] - best['quantity'])
        current = after
        remaining.remove(idx)
    accepted = pd.DataFrame(actions).reindex(columns=ACTION_COLUMNS)
    if not accepted.empty:
        accepted = accepted.sort_values('net_benefit_aed', ascending=False).reset_index(drop=True)
        accepted['rank'] = range(1, len(accepted)+1)
    rejected = pd.DataFrame(rejections).reindex(columns=REJECTION_COLUMNS)
    replenish = []
    for key, gap in sorted(gaps.items()):
        if gap > 0:
            row = positions.loc[key]
            replenish.append(dict(sku=key[0], location=key[1], quantity=math.ceil(gap),
                                  needed_before_day=row.stockout_day,
                                  reason='Assumption: expedite or revise replenishment; transfers cannot economically cover the safety-adjusted gap. Supplier availability, price and feasibility unverified. No order placed.',
                                  evidence=row.evidence))
    return accepted, rejected, pd.DataFrame(replenish, columns=['sku', 'location', 'quantity', 'needed_before_day', 'reason', 'evidence'])
