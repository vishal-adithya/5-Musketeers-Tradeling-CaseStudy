from pathlib import Path
import json
import altair as alt
import pandas as pd
import streamlit as st
from engine.data_loader import load_data, ROOT
from engine.state import PlanningSession, Correction, EDITABLE
from agent.assistant import PlannerAssistant
from agent.approval import ApprovalWorkflow
from agent.tools import json_safe

st.set_page_config(page_title='GulfTrade | Inventory planner', page_icon=None, layout='wide')
st.markdown('''<style>
.stApp {background:#f5f7fb;color:#14233b}
[data-testid="stSidebar"] {background:#eaf0f8}
h1,h2,h3 {letter-spacing:-.025em}
[data-testid="stMetric"] {background:white;border:1px solid #dfe6ef;border-radius:12px;padding:16px}
[data-testid="stTabs"] button {font-weight:600}
.block-container {padding-top:2rem;max-width:1500px}
</style>''', unsafe_allow_html=True)


def table(frame, **kwargs):
    shown = frame.drop(columns=['evidence', 'assumptions'], errors='ignore').copy()
    shown = shown.replace([float('inf'), float('-inf')], None)
    st.dataframe(shown, hide_index=True, width='stretch', **kwargs)


def evidence_view(references, result):
    rows = [result.evidence[ref] for ref in references if ref in result.evidence]
    st.caption('Exact source rows used by this estimate. Corrections preserve original source, time and values.')
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')


def flash(message):
    st.session_state['flash'] = message
    st.rerun()


if 'planning' not in st.session_state:
    try:
        with st.spinner('Building the deterministic planning view...'):
            st.session_state.planning = PlanningSession(load_data())
    except (FileNotFoundError, ValueError) as exc:
        st.error(f'Cannot load demo data: {exc}')
        st.info('From the project folder, run: python make_data.py')
        st.stop()
if 'approvals' not in st.session_state:
    st.session_state.approvals = ApprovalWorkflow(ROOT / 'approvals_log.csv')
if 'pending_reviews' not in st.session_state:
    st.session_state.pending_reviews = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
session = st.session_state.planning
workflow = st.session_state.approvals
if st.session_state.pop('sync_scenario', False):
    st.session_state.scenario_choice = session.scenario
if 'flash' in st.session_state:
    st.success(st.session_state.pop('flash'))

st.sidebar.title('GulfTrade Supplies')
st.sidebar.caption('Sara’s planning workspace · fictional data')
chosen = st.sidebar.selectbox('Disruption scenario', ['None', 'component_shortage', 'shipping_delay'], key='scenario_choice')
if chosen != session.scenario:
    options = session.overrides.model_copy(deep=True)
    options.event_delay_days = options.event_multiplier = None
    with st.spinner('Recomputing forecast, actions and impact...'):
        session.update(options, chosen)
    st.rerun()
if chosen != 'None':
    event = session.result.event
    st.sidebar.warning(event['label'])
    st.sidebar.caption('Affected SKUs: ' + event['affected_skus'].replace('|', ', '))
    if event['shipping_route']:
        st.sidebar.caption('Inbound route only: ' + event['shipping_route'])
    with st.sidebar.form('disruption_assumptions'):
        delay = st.number_input('Assumed inbound delay (days)', 0, 90, int(event['delay_days']), key=f'delay_{chosen}')
        multiplier = st.number_input('Assumed demand multiplier', 0.1, 3.0, float(event['demand_multiplier']), 0.1,
                                     disabled=chosen == 'shipping_delay', key=f'multiplier_{chosen}')
        if st.form_submit_button('Apply disruption assumption'):
            options = session.overrides.model_copy(deep=True)
            options.event_delay_days, options.event_multiplier = delay, multiplier
            session.update(options)
            flash('Disruption assumption updated across every planning tab.')
result = session.result
quality = result.quality
st.sidebar.divider()
st.sidebar.subheader('Data quality')
st.sidebar.metric('Positions needing review', int(quality.data_quality.ne('OK').sum()))
st.sidebar.write(f'Missing days: **{quality.missing_days.sum():,}**')
st.sidebar.write(f'Stockout-distorted days: **{quality.stockout_days.sum():,}**')
st.sidebar.write(f'Stale/manual positions: **{quality.stale.sum():,}**')
st.sidebar.caption('Planning cutoff: ' + str(result.data.as_of.date()))
st.sidebar.caption('Snapshot: ' + result.snapshot_id)
st.sidebar.info('Decision support only. No orders or stock movements are executed.')

st.caption('INVENTORY INTELLIGENCE / 30-DAY WORKSPACE')
st.title('Right stock. Right place. Reviewed by you.')
st.write('Review uncertain demand, spot misplaced stock and compare feasible actions before making a decision.')
a, b, c, d = st.columns(4)
a.metric('Available units', f'{result.stock.available.sum():,.0f}')
b.metric('Positions at shortage risk', int(result.imbalances.shortage_gap.gt(0).sum()))
c.metric('Feasible transfer proposals', len(result.recommendations))
d.metric('Estimated proposal net benefit', f'AED {result.impact.iloc[2].net_benefit_aed:,.2f}')
st.caption('All numbers are deterministic estimates from supplied data. Benefits assume all proposals; approval does not change inventory.')

tabs = st.tabs(['Stock overview', 'Forecast', 'Imbalances', 'Recommendations', 'Impact', 'Edit records', 'Assistant'])
with tabs[0]:
    st.subheader('One view of your stock')
    st.caption('Available is net of reservations. Incoming includes all open orders, even those arriving too late.')
    stock_filter = st.selectbox('Stock product', ['All'] + result.data.tables['sku_master'].sku.tolist(), key='stock_product')
    frame = result.stock if stock_filter == 'All' else result.stock[result.stock.sku.eq(stock_filter)]
    table(frame[['sku', 'location', 'available', 'reserved', 'incoming', 'source_system', 'timestamp', 'data_quality']])
    with st.expander('Stock and inbound source evidence'):
        evidence_view(sorted({ref for refs in frame.evidence for ref in refs}), result)
    st.download_button('Download stock view', frame.drop(columns='evidence').to_csv(index=False), 'stock_view.csv', 'text/csv')

with tabs[1]:
    st.subheader('Demand is a range—not a promise')
    left, right = st.columns(2)
    sku = left.selectbox('Forecast SKU', result.data.tables['sku_master'].sku, key='forecast_sku')
    location = right.selectbox('Forecast location', ['Abu Dhabi', 'Dubai', 'Sharjah'], key='forecast_location')
    forecast_row = result.forecasts[result.forecasts.sku.eq(sku) & result.forecasts.location.eq(location)].iloc[0]
    lo, mid, hi = st.columns(3)
    lo.metric('30-day P10 · lower estimate', f'{forecast_row.p10:,.1f} units')
    mid.metric('30-day P50 · central estimate', f'{forecast_row.p50:,.1f} units')
    hi.metric('30-day P90 · upper estimate', f'{forecast_row.p90:,.1f} units')
    daily = result.daily_forecasts.query('sku == @sku and location == @location')
    base = alt.Chart(daily).encode(x=alt.X('date:T', title='Planning date'))
    band = base.mark_area(opacity=0.18, color='#3375dd').encode(y=alt.Y('p10:Q', title='Daily demand units'), y2='p90:Q')
    line = base.mark_line(color='#1851a5', strokeWidth=3).encode(y='p50:Q', tooltip=['date:T', 'p10:Q', 'p50:Q', 'p90:Q'])
    st.altair_chart((band + line).properties(height=280), use_container_width=True)
    st.caption('Daily uncertainty band. The 30-day interval uses aggregated residual variance, not the sum of daily interval bounds.')
    if forecast_row.data_quality != 'OK':
        st.warning('Review history: ' + forecast_row.data_quality)
    for assumption in forecast_row.assumptions:
        st.write('- ' + assumption)
    with st.expander('See how distorted sales were corrected'):
        history = result.cleaned_sales.query('sku == @sku and location == @location')
        st.line_chart(history.set_index('date')[['units', 'clean_units']], color=['#a1aec2', '#1851a5'])
        st.caption('Observed sales versus deterministic cleaned demand. Stockout/missing imputations are assumptions, not newly observed demand.')
        table(history[['date', 'units', 'clean_units', 'missing', 'stockout_distorted', 'spike', 'row_id']])
    with st.expander('Forecast source rows'):
        evidence_view(forecast_row.evidence, result)

with tabs[2]:
    st.subheader('Where attention is needed')
    st.info('Shortage gap includes safety stock. Expected lost sales use the daily P50 stock-flow simulation; these are different measures.')
    if quality.stockout_days.sum():
        st.warning('Stockout-distorted history is present. Observed zero sales are not proof of zero demand; see the Forecast tab’s corrected history.')
    table(result.imbalances[['sku', 'location', 'status', 'available', 'p10', 'p50', 'p90', 'safety_stock',
                              'incoming_in_time', 'late_incoming', 'shortage_gap', 'shortage_units', 'stockout_day',
                              'real_surplus', 'aged_units', 'data_quality']])

with tabs[3]:
    st.subheader('Commercially justified. Human reviewed.')
    st.caption('Greedy proposals ranked by expected net benefit. A decision is logged, never dispatched to a warehouse.')
    log = workflow.read_log()
    table(result.recommendations[['rank', 'action_id', 'sku', 'from_location', 'to_location', 'quantity', 'lead_days',
                                  'margin_saved_aed', 'holding_saved_aed', 'ageing_saved_aed', 'transfer_cost_aed', 'net_benefit_aed']])
    if not result.recommendations.empty:
        actions = result.recommendations.set_index('action_id')
        action_id = st.selectbox('Review a proposal', actions.index.tolist(),
                                 format_func=lambda k: f'{actions.loc[k, "sku"]} · {actions.loc[k, "from_location"]} to {actions.loc[k, "to_location"]} · {actions.loc[k, "quantity"]} units', key='review_action')
        action = actions.loc[action_id]
        with st.expander('Why this transfer?', expanded=True):
            st.write(action.why)
            st.caption('Net benefit = avoided lost-sales margin + network holding saved + ageing exposure saved − variable and fixed transfer cost. All are estimates, not guaranteed savings.')
        with st.expander('Recommendation evidence and timestamps'):
            evidence_view(action.evidence, result)
        existing = log[(log.snapshot_id == result.snapshot_id) & (log.action_id == action_id)]
        review_key = result.snapshot_id + ':' + action_id
        if len(existing):
            st.success(f'Decision recorded: {existing.iloc[0].decision}. No stock moved.')
        else:
            planner = st.text_input('Planner name (demo alias)', 'Sara (demo)', key='planner_name')
            note = st.text_input('Decision note', key='decision_note')
            if review_key not in st.session_state.pending_reviews:
                if st.button('Open human review', key='open_review'):
                    st.session_state.pending_reviews[review_key] = workflow.request(result, action_id)
                    st.rerun()
            else:
                st.warning('Human review paused at the approval gate. Choose explicitly below.')
                approve_col, reject_col, _ = st.columns([1, 1, 3])
                decision = None
                if approve_col.button('Approve', type='primary', key='approve'):
                    decision = 'Approve'
                if reject_col.button('Reject', key='reject'):
                    decision = 'Reject'
                if decision:
                    try:
                        workflow.decide(st.session_state.pending_reviews[review_key], decision, planner, note, result)
                        del st.session_state.pending_reviews[review_key]
                        flash(f'{decision} decision logged with timestamp and evidence. No stock was moved.')
                    except ValueError as exc:
                        st.error(str(exc))
    with st.expander('Why not? Rejected transfer candidates', expanded=True):
        table(result.rejections[['sku', 'from_location', 'to_location', 'quantity', 'net_benefit_aed', 'reason']])
        st.caption('Rows show examined candidates with surplus and a remaining gap. Missing routes are not proof of feasibility.')
    with st.expander('Replenishment changes to review'):
        table(result.replenishment)
    with st.expander('Approval audit log'):
        table(log.drop(columns=['proposal_json', 'evidence_json'], errors='ignore'))
        st.caption('Old snapshot decisions remain historical records; they do not approve a recomputed proposal.')
        st.download_button('Download full approval audit', log.to_csv(index=False), 'approvals_log.csv', 'text/csv')

with tabs[4]:
    st.subheader('Expected impact, with the baseline in view')
    st.warning('“After” assumes all listed proposals—not only approved ones. It is a what-if estimate, not realised savings.')
    table(result.impact.round(2))
    metric = st.selectbox('Compare measure', ['shortage_units', 'ageing_exposure_units', 'holding_cost_aed',
                                            'transfer_cost_aed', 'net_benefit_aed'],
                          format_func=lambda s: s.replace('_', ' ').capitalize(), key='impact_measure')
    st.bar_chart(result.impact.set_index('plan')[[metric]], color='#1851a5', horizontal=True)
    st.caption('Baseline: raw observed trailing-28-day mean, no transfers. Before: cleaned forecast, no transfers. After: same cleaned forecast with proposals. Only after-versus-before is used for net benefit; different forecast demand makes baseline differences non-causal.')
    st.write('Assumptions: FEFO consumption, constant margin and costs, no execution friction, transit holding included. Ageing exposure tracks the initially over-120-day cohort; moving stock alone creates no ageing benefit. Replenishment suggestions are not priced or included in impact.')

with tabs[5]:
    st.subheader('Correct once. Refresh every planning step.')
    st.caption('Edits are session-local. Source row IDs are stable; original timestamps, source systems and changed values remain available. Nothing is written back to an ERP.')
    edit_table = st.selectbox('Dataset to correct', list(EDITABLE), key='edit_table')
    edit_sku = st.selectbox('SKU to correct', result.data.tables['sku_master'].sku, key='edit_sku')
    source = result.data.tables[edit_table].copy()
    if edit_table == 'inbound_orders' and 'pre_scenario_arrival_date' in source:
        source['scenario_arrival_date'] = source.arrival_date
        source['arrival_date'] = source.pre_scenario_arrival_date
        st.info('Edit the source ETA before disruption. The active scenario delay is applied once afterward; the effective ETA is shown below.')
        table(source[['row_id', 'sku', 'location', 'arrival_date', 'scenario_arrival_date']])
    view = source.loc[source.sku.eq(edit_sku)].copy()
    fields = [c for c in source.columns if c in EDITABLE[edit_table]]
    identity = [c for c in ['row_id', 'sku', 'location', 'date', 'batch_id'] if c in view]
    editable = view[identity + fields].reset_index(drop=True)
    with st.form('edit_records'):
        edited = st.data_editor(editable, disabled=identity, hide_index=True, width='stretch',
                                key=f'editor_{edit_table}_{edit_sku}_{result.snapshot_id}', num_rows='fixed')
        reason = st.text_input('Reason for correction', 'Planner reconciled source record', key='correction_reason')
        save = st.form_submit_button('Save corrections and recompute', type='primary')
    if save:
        options = session.overrides.model_copy(deep=True)
        changes = []
        for idx, row in edited.iterrows():
            for field in fields:
                if row[field] != editable.loc[idx, field]:
                    changes.append(dict(table=edit_table, row_id=row.row_id, field=field,
                                        value=json_safe(row[field]), reason=reason))
        if not changes:
            st.info('No records changed.')
        else:
            try:
                options.records.extend(Correction(**change) for change in changes)
                with st.spinner('Validating and recomputing all planning stages...'):
                    session.update(options)
                flash('Corrections saved for this session. All forecasts, imbalances, proposals and impact refreshed.')
            except (ValueError, TypeError) as exc:
                st.error(f'Correction rejected; previous plan preserved. {exc}')
    st.download_button('Export current dataset', source.to_csv(index=False), f'{edit_table}_corrected.csv', 'text/csv')
    with st.expander('Session correction trail'):
        table(pd.DataFrame(result.corrections))

with tabs[6]:
    st.subheader('Ask the planning assistant')
    st.caption('The assistant calls deterministic tools; it does not calculate or execute. Live provider use sends selected synthetic records to that provider and may incur charges.')
    if 'assistant' not in st.session_state:
        try:
            st.session_state.assistant = PlannerAssistant(session)
        except Exception:
            st.error('Assistant could not initialise. Check optional provider configuration; planning remains available.')
    assistant = st.session_state.get('assistant')
    if assistant is not None and assistant.agent is None:
        st.info(assistant.disabled_reason)
    st.caption('Try: “Explain the SKU01 Abu Dhabi forecast and proposed transfer.” Or: “Why is the SKU05 transfer rejected?” Each question uses current data; prior chat is display-only, so name the SKU explicitly.')
    for message in st.session_state.chat_history:
        with st.chat_message(message['role']):
            st.write(message['text'])
            if message.get('evidence'):
                with st.expander('Tool evidence'):
                    for item in message['evidence']:
                        try:
                            st.json(json.loads(item))
                        except (ValueError, TypeError):
                            st.write(item)
    pending = getattr(session, 'pending_update', None)
    if pending:
        st.warning('Assistant proposed a change. Active inputs are unchanged until you confirm. Only the latest preview is pending.')
        st.json({'scenario': pending['scenario'], 'overrides': pending['options'].model_dump(),
                 'base_snapshot': pending['base_snapshot'], 'preview_snapshot': pending['preview_snapshot']})
        confirm, discard = st.columns(2)
        if confirm.button('Confirm proposed input change', key='confirm_input_change'):
            try:
                session.confirm_pending_update()
                st.session_state.sync_scenario = True
                flash('Input change confirmed. Every planning stage refreshed; no stock moved.')
            except ValueError as exc:
                st.error(str(exc))
        if discard.button('Discard proposed input change', key='discard_input_change'):
            session.pending_update = None
            st.rerun()
    prompt = st.chat_input('Ask about the current plan', disabled=assistant is None or assistant.agent is None)
    if prompt:
        st.session_state.chat_history.append({'role': 'user', 'text': prompt})
        with st.spinner('Retrieving grounded planning evidence...'):
            reply = assistant.ask(prompt)
        st.session_state.chat_history.append({'role': 'assistant', **reply})
        st.session_state.sync_scenario = True
        st.rerun()
