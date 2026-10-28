import numpy as np
import pandas as pd
from engine.data_loader import DataSet, refs

HORIZON = 30
Z80 = 1.281551565545


def forecast(data: DataSet, cleaned: pd.DataFrame, quality: pd.DataFrame,
             event: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries, paths = [], []
    future = pd.date_range(data.as_of + pd.Timedelta(days=1), periods=HORIZON)
    for (sku, location), history in cleaned.groupby(['sku', 'location'], sort=True):
        recent = history.tail(28)
        level = float(recent.clean_units.mean())
        dow_means = recent.groupby(recent.date.dt.dayofweek).clean_units.mean()
        factors = (dow_means / level).clip(0.5, 1.5) if level > 0 else pd.Series(1.0, index=range(7))
        factors = factors / factors.mean()
        fitted = recent.date.dt.dayofweek.map(factors).fillna(1).to_numpy() * level
        residual = recent.clean_units.to_numpy() - fitted
        sigma = max(float(np.std(residual, ddof=1)) if len(residual) > 1 else 0.0, np.sqrt(level) * 0.25)
        multiplier = float(event['demand_multiplier']) if event and sku in event['affected_skus'].split('|') else 1.0
        daily_mean = future.dayofweek.map(factors).fillna(1).to_numpy() * level * multiplier
        sigma *= multiplier
        p50 = float(daily_mean.sum())
        width = Z80 * sigma * np.sqrt(HORIZON)
        quality_row = quality[(quality.sku == sku) & (quality.location == location)].iloc[0]
        assumptions = ['Assumption: cleaned trailing 28-day demand and bounded weekday pattern persist for 30 days.',
                       'Assumption: stockout and missing days use historical same-weekday estimates, not observed demand.',
                       'Assumption: 95th-percentile winsorisation removes non-recurring bulk/spike effects.',
                       'Assumption: independent residual errors; P10/P90 are approximate, not calibrated guarantees.',
                       'Limitation: quality flags and zero-history cases make estimates less reliable; no external demand feed.']
        evidence = [f'sales_history:{v}' for v in history.row_id.dropna()]
        event_in_scope = False
        if event and sku in event['affected_skus'].split('|'):
            orders = data.tables['inbound_orders']
            affected = orders.sku.eq(sku) & orders.location.eq(location)
            if event['shipping_route']:
                affected &= orders.shipping_route.eq(event['shipping_route'])
            event_in_scope = multiplier != 1 or affected.any()
            if event_in_scope:
                assumptions.append(event['assumption'])
                assumptions.append('Supply ETA changes do not change demand forecasts when the multiplier is one.')
                evidence.append(f'events:{event["row_id"]}')
        summaries.append(dict(sku=sku, location=location, p10=max(0, p50-width), p50=p50, p90=p50+width,
                              residual_std=sigma, data_quality=quality_row.data_quality,
                              event_applied=event['scenario'] if event_in_scope else 'None',
                              assumptions=assumptions, evidence=evidence))
        for day, (date, mean) in enumerate(zip(future, daily_mean), start=1):
            paths.append(dict(sku=sku, location=location, date=date, day=day,
                              p10=max(0, mean-Z80*sigma), p50=float(mean), p90=float(mean+Z80*sigma)))
    return pd.DataFrame(summaries), pd.DataFrame(paths)


def baseline_paths(cleaned: pd.DataFrame, paths: pd.DataFrame) -> pd.DataFrame:
    baseline = paths.copy()
    means = cleaned.groupby(['sku', 'location'], sort=False).tail(28).groupby(['sku', 'location']).units.mean().fillna(0)
    baseline['p50'] = [float(means.loc[(r.sku, r.location)]) for r in baseline.itertuples()]
    return baseline
