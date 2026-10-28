from engine.data_loader import DataSet

SCENARIOS = ['component_shortage', 'shipping_delay']


def apply_scenario(data: DataSet, scenario: str | None, delay_days: int | None = None,
                   demand_multiplier: float | None = None) -> tuple[DataSet, dict | None]:
    import pandas as pd
    adjusted = data.copy()
    if scenario in (None, 'None'):
        if delay_days is not None or demand_multiplier is not None:
            raise ValueError('Choose a scenario before overriding disruption assumptions')
        return adjusted, None
    if scenario not in SCENARIOS:
        raise ValueError(f'Unknown scenario: {scenario}')
    idx = adjusted.tables['events'].index[adjusted.tables['events'].scenario.eq(scenario)][0]
    events = adjusted.tables['events']
    if delay_days is not None:
        if not 0 <= delay_days <= 90:
            raise ValueError('Assumption delay must be 0–90 days')
        events.loc[idx, 'delay_days'] = delay_days
    if demand_multiplier is not None:
        if scenario == 'shipping_delay' and demand_multiplier != 1:
            raise ValueError('Shipping scenario changes route supply only, not demand')
        if not 0.1 <= demand_multiplier <= 3:
            raise ValueError('Assumption multiplier must be 0.1–3')
        events.loc[idx, 'demand_multiplier'] = demand_multiplier
    event = events.loc[idx].to_dict()
    event['assumption'] = f'Assumption: fictional {scenario}; listed inbound delayed {event["delay_days"]} days; listed demand multiplier {event["demand_multiplier"]}. Not a verified market signal.'
    events.loc[idx, 'assumption'] = event['assumption']
    inbound = adjusted.tables['inbound_orders']
    mask = inbound.sku.isin(event['affected_skus'].split('|'))
    if event['shipping_route']:
        mask &= inbound.shipping_route.eq(event['shipping_route'])
    inbound['pre_scenario_arrival_date'] = inbound.arrival_date
    inbound.loc[mask, 'arrival_date'] = (pd.to_datetime(inbound.loc[mask, 'arrival_date']) + pd.Timedelta(days=int(event['delay_days']))).dt.strftime('%Y-%m-%d')
    inbound['event_ref'] = ''
    inbound.loc[mask, 'event_ref'] = f'events:{event["row_id"]}'
    return adjusted, event


def rerun_scenario(data, scenario, overrides=None):
    from engine.state import run_pipeline
    return run_pipeline(data, overrides, scenario)
