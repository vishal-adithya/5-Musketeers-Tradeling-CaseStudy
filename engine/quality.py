import numpy as np
import pandas as pd
from engine.data_loader import DataSet, KEYS, refs


def assess_quality(data: DataSet) -> tuple[pd.DataFrame, pd.DataFrame]:
    sales = data.tables['sales_history'].copy()
    sales['date'] = pd.to_datetime(sales.date)
    dates = pd.date_range(sales.date.min(), data.as_of)
    daily, summaries = [], []
    for stock in data.tables['inventory'].itertuples():
        subset = sales[(sales.sku == stock.sku) & (sales.location == stock.location)]
        grid = subset.set_index('date').reindex(dates).rename_axis('date').reset_index()
        grid['sku'], grid['location'] = stock.sku, stock.location
        grid['missing'] = grid.row_id.isna()
        grid['stockout_distorted'] = grid.stockout.eq(True)
        valid = grid.loc[~grid.missing & ~grid.stockout_distorted & grid.order_type.ne('bulk'), 'units']
        median = float(valid.median()) if len(valid) else 0.0
        mad = float((valid - median).abs().median()) if len(valid) else 0.0
        threshold = max(median + 6 * max(mad, 1), median * 4, 10)
        grid['spike'] = grid.units.gt(threshold) | grid.order_type.eq('bulk')
        trusted = grid.units.mask(grid.missing | grid.stockout_distorted | grid.spike)
        recent = trusted.iloc[-28:]
        fill = float(recent.mean()) if recent.notna().any() else (float(trusted.mean()) if trusted.notna().any() else 0.0)
        dow = grid.date.dt.dayofweek
        means = trusted.groupby(dow).mean()
        imputation = dow.map(means).fillna(fill)
        cap = float(valid.quantile(0.95)) if len(valid) else fill
        grid['clean_units'] = grid.units.mask(grid.missing | grid.stockout_distorted, imputation).clip(upper=max(cap, 0)).fillna(fill)
        grid['was_imputed'] = grid.missing | grid.stockout_distorted
        flags = []
        for col, label in [('stockout_distorted', 'stockout-distorted'), ('missing', 'missing sales'), ('spike', 'bulk/spike winsorised')]:
            if grid[col].any():
                flags.append(label)
        stale = stock.source_system == 'manual_sheet' or (data.as_of.tz_localize('UTC') + pd.Timedelta(days=1) - pd.Timestamp(stock.timestamp)).days > 3
        if stale:
            flags.append('stale/manual stock')
        batches = data.tables['stock_age']
        aged_total = batches.loc[(batches.sku == stock.sku) & (batches.location == stock.location), 'units'].sum()
        if aged_total != stock.available:
            flags.append('batch/available mismatch: assumption capped to available')
        if trusted.notna().sum() < 14:
            flags.append('insufficient history: unverified')
        summaries.append(dict(sku=stock.sku, location=stock.location,
                              missing_days=int(grid.missing.sum()), stockout_days=int(grid.stockout_distorted.sum()),
                              spike_days=int(grid.spike.sum()), stale=stale,
                              data_quality='; '.join(flags) or 'OK', evidence=refs('sales_history', subset)+[f'inventory:{stock.row_id}']))
        daily.append(grid)
    return pd.concat(daily, ignore_index=True), pd.DataFrame(summaries)
