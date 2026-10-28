import json
import math
import pandas as pd
from langchain_core.tools import tool
from engine.state import PlanningSession, Correction


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, 'item'):
        return json_safe(value.item())
    return value


def packet(session, name, frame=None, **extra):
    result = session.result
    rows = json_safe(frame.round(2).to_dict('records')) if frame is not None else []
    references = sorted({ref for row in rows for ref in row.get('evidence', [])})
    sources = {}
    for ref in references:
        evidence = result.evidence[ref]
        key = (evidence['table'], evidence['source_system'], evidence['timestamp'])
        sources.setdefault(key, []).append(evidence['row_id'])
    return json_safe(dict(citation=f'[{name}@{result.snapshot_id}]', snapshot_id=result.snapshot_id,
                          scenario=result.scenario, as_of=str(result.data.as_of.date()), rows=rows,
                          sources=[dict(table=k[0], source_system=k[1], timestamp=k[2], row_ids=v) for k, v in sources.items()],
                          trust='Assumption-based deterministic estimates, not guarantees. Nothing executed. Unsupported claims are unverified.', **extra))


def build_tools(session: PlanningSession):
    @tool
    def get_stock_view(sku: str = '', location: str = '') -> dict:
        """Get available (net of reserved), reserved and incoming stock, source timestamps and quality flags."""
        frame = session.result.stock
        if sku:
            frame = frame[frame.sku.eq(sku)]
        if location:
            frame = frame[frame.location.eq(location)]
        return packet(session, 'get_stock_view', frame)

    @tool
    def get_forecast(sku: str, location: str) -> dict:
        """Get deterministic 30-day P10/P50/P90, assumptions and original sales-row provenance. Never calculate a forecast."""
        frame = session.result.forecasts
        return packet(session, 'get_forecast', frame[frame.sku.eq(sku) & frame.location.eq(location)])

    @tool
    def get_imbalances(sku: str = '') -> dict:
        """Get shortage, real surplus, ageing and late inbound risk, including stockout-distorted history warnings."""
        frame = session.result.imbalances
        if sku:
            frame = frame[frame.sku.eq(sku)]
        return packet(session, 'get_imbalances', frame)

    @tool
    def get_recommendations(sku: str = '') -> dict:
        """Get ranked feasible transfers; quantities and economics are computed by the engine, not the assistant."""
        frame = session.result.recommendations
        replenishment = session.result.replenishment
        if sku:
            frame, replenishment = frame[frame.sku.eq(sku)], replenishment[replenishment.sku.eq(sku)]
        return packet(session, 'get_recommendations', frame, replenishment=json_safe(replenishment.round(2).to_dict('records')))

    @tool
    def explain_rejection(sku: str, location: str) -> dict:
        """Get recorded why-not economics and lead-time reasons for a destination. An absent record is unverified."""
        frame = session.result.rejections
        frame = frame[frame.sku.eq(sku) & frame.to_location.eq(location)]
        return packet(session, 'explain_rejection', frame,
                      limitation='No recorded rejection is not proof a transfer is feasible; unverified.' if frame.empty else '')

    @tool
    def get_impact() -> dict:
        """Get expected before/after and raw-average baseline estimates. After means all proposals, not approved or executed stock."""
        frame = session.result.impact.copy()
        frame['evidence'] = [sorted(session.result.evidence)] * len(frame)
        return packet(session, 'get_impact', frame,
                      action_ids=session.result.recommendations.action_id.tolist(),
                      assumptions=['Fixed margins/costs; daily FEFO; fixed initially-over-120-day cohort.',
                                   'Holding includes transit. Ageing is exposure, not guaranteed write-off savings.',
                                   'Different baseline demand means baseline-vs-before is not a causal saving. Net benefit is after-vs-before only.'])

    @tool
    def set_disruption(scenario: str) -> dict:
        """Preview None/component_shortage/shipping_delay, recomputing all stages. Human confirmation in the UI is required to apply; only one preview is pending."""
        options = session.overrides.model_copy(deep=True)
        options.event_delay_days, options.event_multiplier = None, None
        try:
            preview = session.stage_update(options, scenario)
        except ValueError as exc:
            return {'status': 'unverified', 'error': str(exc)}
        return packet(session, 'set_disruption', preview_snapshot=preview.snapshot_id,
                      proposed_scenario=scenario, note='Preview only. Confirm the pending change in Assistant to apply. No active inputs changed.')

    @tool
    def correct_record(table: str, row_id: str, field: str, value: str, reason: str) -> dict:
        """Preview one source correction; value is JSON. Source ETAs exclude scenario delays. Human UI confirmation is required to apply; only one preview is pending."""
        try:
            correction = Correction(table=table, row_id=row_id, field=field, value=json.loads(value), reason=reason)
            options = session.overrides.model_copy(deep=True)
            options.records.append(correction)
            preview = session.stage_update(options, session.scenario)
        except (ValueError, TypeError) as exc:
            return {'status': 'unverified', 'error': str(exc)}
        return packet(session, 'correct_record', preview_snapshot=preview.snapshot_id,
                      proposed_correction=correction.model_dump(), note='Preview only. Confirm the pending change in Assistant to apply. No active inputs changed.')

    @tool
    def get_event_scope(scenario: str, sku: str, location: str = '') -> dict:
        """Verify exact SKU eligibility and actual inbound route/location scope using supplied rows; do not infer market effects."""
        events = session.result.data.tables['events']
        selected = events[events.scenario.eq(scenario)]
        if selected.empty or sku not in set(session.result.data.tables['sku_master'].sku):
            return {'status': 'unverified', 'claim': 'Unknown event or SKU; no supported effect.'}
        event = selected.iloc[0]
        listed = sku in event.affected_skus.split('|')
        orders = session.result.data.tables['inbound_orders']
        mask = orders.sku.eq(sku) & listed
        if location:
            mask &= orders.location.eq(location)
        if event.shipping_route:
            mask &= orders.shipping_route.eq(event.shipping_route)
        matching = orders[mask]
        applies = listed and (not location or not matching.empty or event.demand_multiplier != 1)
        selected = selected.copy()
        selected['evidence'] = [[f'events:{event.row_id}'] + [f'inbound_orders:{r}' for r in matching.row_id]]
        claim = ('Assumption: SKU is listed; only the matching inbound rows shown are delayed. Demand changes only if an explicit multiplier differs from one.' if applies else
                 'Unverified: no supported effect for this SKU/location. SKU is unlisted or no matching route/order exists.')
        return packet(session, 'get_event_scope', selected, sku=sku, location=location, applies=applies,
                      listed=listed, matching_inbound=matching.to_dict('records'), claim=claim)

    return [get_stock_view, get_forecast, get_imbalances, get_recommendations, explain_rejection,
            get_impact, set_disruption, correct_record, get_event_scope]
