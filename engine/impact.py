import pandas as pd
from engine.data_loader import DataSet
from engine.forecast import baseline_paths
from engine.simulation import simulate, totals


def calculate_impact(data: DataSet, cleaned: pd.DataFrame, daily: pd.DataFrame,
                     recommendations: pd.DataFrame) -> pd.DataFrame:
    baseline = totals(simulate(data, baseline_paths(cleaned, daily)))
    before = totals(simulate(data, daily))
    after = totals(simulate(data, daily, recommendations.to_dict('records')))
    cost = float(recommendations.transfer_cost_aed.sum()) if len(recommendations) else 0.0
    benefit = (before['lost_margin_aed'] - after['lost_margin_aed'] + before['holding_cost_aed'] - after['holding_cost_aed']
               + before['ageing_exposure_aed'] - after['ageing_exposure_aed'] - cost)
    baseline.update(transfer_cost_aed=0.0, net_benefit_aed=0.0)
    before.update(transfer_cost_aed=0.0, net_benefit_aed=0.0)
    after.update(transfer_cost_aed=cost, net_benefit_aed=benefit)
    result = pd.DataFrame({'Baseline: raw mean, no transfers': baseline,
                           'Before: cleaned forecast, no transfers': before,
                           'After: all proposals, not executed': after}).T
    result.index.name = 'plan'
    return result.reset_index()
