"""Render exact typed tool facts; never expose unvalidated LLM-generated prose."""
import json


def render_evidence(evidence: list) -> str:
    paragraphs = []
    for raw in evidence:
        try:
            output = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            continue
        if not isinstance(output, dict) or 'citation' not in output:
            continue
        citation = output['citation']
        name = citation.split('@')[0].lstrip('[')
        rows = output.get('rows', [])
        if name in {'correct_record', 'set_disruption'}:
            paragraphs.append(f'Input change preview only. Confirm or discard it in the Assistant tab. Active data is unchanged. {citation}')
        elif name == 'get_event_scope':
            paragraphs.append(f'{output["sku"]}: {output["claim"]} {citation}')
        elif not rows:
            paragraphs.append(f'Unverified: no matching evidence returned by {name}. {citation}')
        for row in rows[:12]:
            identity = f'{row.get("sku", "")} / {row.get("location", "")}'
            if name == 'get_stock_view':
                text = f'{identity}: available {row["available"]}, reserved {row["reserved"]}, incoming {row["incoming"]} units. Source {row["source_system"]}, timestamp {row["timestamp"]}. Quality: {row["data_quality"]}.'
            elif name == 'get_forecast':
                text = (f'{identity}: uncertain 30-day demand P10 {row["p10"]}, P50 {row["p50"]}, P90 {row["p90"]} units. '
                        f'Quality: {row["data_quality"]}. ' + ' '.join(row['assumptions']))
            elif name == 'get_imbalances':
                text = f'{identity}: {row["status"]}. Safety-adjusted gap {row["shortage_gap"]}, physical surplus {row["real_surplus"]}, aged units {row["aged_units"]}. Assumption-based demand P10 {row["p10"]}, P50 {row["p50"]}, P90 {row["p90"]}.'
            elif name == 'get_recommendations':
                text = (f'{row["sku"]}: propose {row["quantity"]} units from {row["from_location"]} to {row["to_location"]}; '
                        f'lead {row["lead_days"]} days; transfer cost AED {row["transfer_cost_aed"]}; estimated net benefit AED {row["net_benefit_aed"]}. {row["why"]}')
            elif name == 'explain_rejection':
                text = f'{row["sku"]}, {row["from_location"]} to {row["to_location"]}: {row["reason"]}'
            elif name == 'get_impact':
                text = (f'{row["plan"]}: expected shortage {row["shortage_units"]} units; ageing exposure {row["ageing_exposure_units"]} units; '
                        f'holding AED {row["holding_cost_aed"]}; transfer AED {row["transfer_cost_aed"]}; net benefit AED {row["net_benefit_aed"]}. '
                        'Assumption-based what-if; baseline demand differs. Net benefit compares after against before, not realised savings.')
            else:
                continue
            paragraphs.append(text + ' ' + citation)
        if len(rows) > 12:
            paragraphs.append('Additional rows are available in the tool evidence below.')
    if not paragraphs:
        return 'Unverified: no supported tool evidence was returned. Model prose was withheld. Use the planning tabs or ask about a specific SKU and location.'
    paragraphs.append('Nothing executed. Transfer decisions require the Recommendations tab’s human Approve/Reject review. The model selects tools; this explanation is rendered from exact tool fields, not model prose.')
    return '\n\n'.join(dict.fromkeys(paragraphs))
