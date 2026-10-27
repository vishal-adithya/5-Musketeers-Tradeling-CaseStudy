from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
KEYS = ['sku', 'location']
COLUMNS = {
    'sku_master': ['sku', 'name', 'product_type', 'semiconductor_dependent', 'unit_margin_aed', 'unit_value_aed'],
    'sales_history': KEYS + ['date', 'units', 'stockout', 'order_type'],
    'inventory': KEYS + ['available', 'reserved'],
    'stock_age': KEYS + ['batch_id', 'units', 'age_days'],
    'safety_stock': KEYS + ['safety_stock'],
    'inbound_orders': KEYS + ['quantity', 'arrival_date', 'supplier_lead_days', 'shipping_route'],
    'transfer_costs': ['sku', 'from_location', 'to_location', 'lead_days', 'variable_cost_aed', 'fixed_cost_aed'],
    'holding_costs': ['sku', 'per_unit_day_aed', 'ageing_penalty_aed'],
    'events': ['scenario', 'label', 'affected_skus', 'shipping_route', 'demand_multiplier', 'delay_days', 'assumption'],
}
NUMERIC = {'units', 'available', 'reserved', 'age_days', 'safety_stock', 'quantity', 'supplier_lead_days',
           'lead_days', 'variable_cost_aed', 'fixed_cost_aed', 'per_unit_day_aed', 'ageing_penalty_aed',
           'unit_margin_aed', 'unit_value_aed', 'demand_multiplier', 'delay_days'}
INTEGER = {'units', 'available', 'reserved', 'age_days', 'safety_stock', 'quantity', 'supplier_lead_days', 'lead_days', 'delay_days'}


@dataclass
class DataSet:
    tables: dict[str, pd.DataFrame]
    as_of: pd.Timestamp

    def copy(self):
        return DataSet({name: frame.copy(deep=True) for name, frame in self.tables.items()}, self.as_of)


def load_data(directory: Path | str = ROOT / 'data') -> DataSet:
    directory = Path(directory)
    tables = {name: pd.read_csv(directory / f'{name}.csv', keep_default_na=False) for name in COLUMNS}
    data = DataSet(tables, pd.to_datetime(tables['sales_history']['date']).max().normalize())
    validate(data)
    return data


def validate(data: DataSet) -> None:
    for name, required in COLUMNS.items():
        if name not in data.tables:
            raise ValueError(f'Missing table: {name}')
        frame = data.tables[name]
        missing = set(required + ['row_id', 'timestamp', 'source_system']) - set(frame.columns)
        if missing:
            raise ValueError(f'{name}: missing columns {sorted(missing)}')
        if frame.row_id.duplicated().any() or frame.row_id.eq('').any():
            raise ValueError(f'{name}: row_id must be unique and nonempty')
        if frame.source_system.eq('').any():
            raise ValueError(f'{name}: source_system is required')
        if pd.to_datetime(frame.timestamp, utc=True, format='ISO8601', errors='raise').isna().any():
            raise ValueError(f'{name}: timestamp is required')
        for col in set(frame.columns) & NUMERIC:
            frame[col] = pd.to_numeric(frame[col], errors='raise')
            if not np.isfinite(frame[col]).all() or (frame[col] < 0).any():
                raise ValueError(f'{name}.{col}: finite nonnegative values required')
            if col in INTEGER and (frame[col] % 1 != 0).any():
                raise ValueError(f'{name}.{col}: whole units/days required')
        if 'sku' in frame and not frame.sku.isin(data.tables['sku_master'].sku).all():
            raise ValueError(f'{name}: unknown SKU')
    t = data.tables
    for name, keys in [('sku_master', ['sku']), ('inventory', KEYS), ('safety_stock', KEYS),
                       ('holding_costs', ['sku']), ('sales_history', KEYS + ['date']),
                       ('transfer_costs', ['sku', 'from_location', 'to_location'])]:
        if t[name].duplicated(keys).any():
            raise ValueError(f'{name}: duplicate business key')
    positions = set(map(tuple, t['inventory'][KEYS].values))
    for name in ['sales_history', 'stock_age', 'safety_stock', 'inbound_orders']:
        if not set(map(tuple, t[name][KEYS].values)) <= positions:
            raise ValueError(f'{name}: unknown SKU-location')
    if set(map(tuple, t['safety_stock'][KEYS].values)) != positions:
        raise ValueError('Every inventory position needs safety stock')
    if set(t['holding_costs'].sku) != set(t['sku_master'].sku):
        raise ValueError('Every SKU needs holding costs')
    for row in t['transfer_costs'].itertuples():
        if (row.sku, row.from_location) not in positions or (row.sku, row.to_location) not in positions or row.from_location == row.to_location or row.lead_days < 1:
            raise ValueError('Invalid transfer route or lead time')
    for name, col in [('sales_history', 'stockout'), ('sku_master', 'semiconductor_dependent')]:
        if not t[name][col].isin([True, False, 'True', 'False']).all():
            raise ValueError(f'{name}.{col}: boolean required')
        t[name][col] = t[name][col].map(lambda x: str(x).lower() == 'true')
    dates = pd.to_datetime(t['sales_history'].date, errors='raise')
    if dates.isna().any() or (dates > data.as_of).any():
        raise ValueError('Sales dates are required and cannot be after planning cutoff')
    arrivals = pd.to_datetime(t['inbound_orders'].arrival_date, errors='raise')
    if arrivals.isna().any() or (arrivals <= data.as_of).any():
        raise ValueError('Open inbound ETAs must be after planning cutoff; reconcile overdue orders first')
    if not t['sales_history'].order_type.isin(['regular', 'bulk']).all():
        raise ValueError('Unsupported order classification')
    events = t['events']
    if len(events) != 2 or set(events.scenario) != {'component_shortage', 'shipping_delay'}:
        raise ValueError('Exactly two named fictional scenarios are required')
    for event in events.itertuples():
        listed = event.affected_skus.split('|')
        if not listed or not set(listed) <= set(t['sku_master'].sku):
            raise ValueError('Event contains unknown or empty SKU whitelist')
        if 'FICTIONAL' not in event.label:
            raise ValueError('Events must be explicitly labelled FICTIONAL')
        if event.scenario == 'component_shortage':
            allowed = set(t['sku_master'].loc[t['sku_master'].semiconductor_dependent, 'sku'])
            if not set(listed) <= allowed or event.shipping_route:
                raise ValueError('Component event must list semiconductor-dependent SKUs only')
        elif event.shipping_route not in set(t['inbound_orders'].shipping_route) or event.demand_multiplier != 1:
            raise ValueError('Shipping event needs one supplied route and cannot change demand')


def refs(name: str, frame: pd.DataFrame) -> list[str]:
    return [f'{name}:{row_id}' for row_id in frame.row_id]


def stock_view(data: DataSet) -> pd.DataFrame:
    inventory = data.tables['inventory'].copy()
    inbound = data.tables['inbound_orders']
    incoming = inbound.groupby(KEYS).quantity.sum().rename('incoming')
    inventory = inventory.merge(incoming, on=KEYS, how='left').fillna({'incoming': 0})
    inventory['evidence'] = [refs('inventory', data.tables['inventory'].query('row_id == @row.row_id')) +
                             refs('inbound_orders', inbound[(inbound.sku == row.sku) & (inbound.location == row.location)])
                             for row in inventory.itertuples()]
    return inventory


def evidence_registry(data: DataSet) -> dict:
    return {f'{name}:{row["row_id"]}': {'table': name, **row}
            for name, frame in data.tables.items() for row in frame.to_dict('records')}
