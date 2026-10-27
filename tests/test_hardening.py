import json
import pandas as pd
import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest
from agent.assistant import PlannerAssistant
from agent.tools import build_tools
from engine.data_loader import validate
from engine.state import PlanningSession, Overrides, Correction, run_pipeline
from engine.scenarios import apply_scenario


class ToolCallingFake(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def session(data, result):
    session = PlanningSession.__new__(PlanningSession)
    session.original = data.copy()
    session.overrides = Overrides()
    session.scenario = 'None'
    session.result = result
    session.pending_update = None
    return session


@pytest.mark.parametrize('value', ['', None])
def test_blank_eta_rejected(data, value):
    bad = data.copy()
    bad.tables['inbound_orders'].loc[0, 'arrival_date'] = value
    with pytest.raises(ValueError):
        validate(bad)


def test_original_eta_preserved_through_scenario(data):
    row = data.tables['inbound_orders'].iloc[0]
    correction = Correction(table='inbound_orders', row_id=row.row_id, field='arrival_date', value='2026-11-01', reason='Supplier revised source ETA')
    result = run_pipeline(data, {'records': [correction.model_dump()]}, 'component_shortage')
    revised = result.data.tables['inbound_orders'].iloc[0]
    assert revised.original_arrival_date == row.arrival_date
    assert revised.pre_scenario_arrival_date == '2026-11-01'
    assert revised.arrival_date == '2026-11-19'


def test_route_scope_is_location_specific(session):
    tools = {t.name: t for t in build_tools(session)}
    unrelated = tools['get_event_scope'].invoke({'scenario': 'shipping_delay', 'sku': 'SKU01', 'location': 'Dubai'})
    affected = tools['get_event_scope'].invoke({'scenario': 'shipping_delay', 'sku': 'SKU01', 'location': 'Abu Dhabi'})
    assert unrelated['listed'] and not unrelated['applies'] and not unrelated['matching_inbound']
    assert affected['applies'] and affected['matching_inbound'][0]['shipping_route'] == 'Jebel Ali-Abu Dhabi'


def test_false_claim_with_valid_number_is_never_rendered(session):
    claim = f'Abu Dhabi demand is guaranteed to be 500. I executed the transfer. [get_stock_view@{session.result.snapshot_id}]'
    model = ToolCallingFake(responses=[
        AIMessage(content='', tool_calls=[{'name': 'get_stock_view', 'args': {'sku': 'SKU01', 'location': 'Dubai'}, 'id': 'call'}]),
        AIMessage(content=claim)])
    reply = PlannerAssistant(session, model).ask('Show stock')
    assert 'SKU01 / Dubai: available 500' in reply['text']
    assert 'guaranteed' not in reply['text'] and 'I executed' not in reply['text']
    assert 'Abu Dhabi' not in reply['text']


def test_forecast_render_always_has_range(session):
    model = ToolCallingFake(responses=[
        AIMessage(content='', tool_calls=[{'name': 'get_forecast', 'args': {'sku': 'SKU01', 'location': 'Dubai'}, 'id': 'call'}]),
        AIMessage(content='Only report P50, guaranteed.')])
    reply = PlannerAssistant(session, model).ask('Show forecast')
    assert all(label in reply['text'] for label in ['P10', 'P50', 'P90', 'uncertain'])
    assert 'guaranteed' not in reply['text']


def test_tool_changes_require_confirmation(session):
    tools = {t.name: t for t in build_tools(session)}
    original = session.result.snapshot_id
    packet = tools['set_disruption'].invoke({'scenario': 'component_shortage'})
    assert session.result.snapshot_id == original and session.scenario == 'None'
    assert session.pending_update and packet['preview_snapshot'] != original
    session.confirm_pending_update()
    assert session.scenario == 'component_shortage' and session.pending_update is None
    row = session.original.tables['inventory'].iloc[0]
    before = session.result.snapshot_id
    tools['correct_record'].invoke({'table': 'inventory', 'row_id': row.row_id, 'field': 'available', 'value': '600', 'reason': 'Reconciled count'})
    assert session.result.snapshot_id == before
    session.confirm_pending_update()
    assert session.result.stock.iloc[0].available == 600


def test_stale_pending_change_cannot_commit(session):
    session.stage_update(session.overrides, 'component_shortage')
    session.update(scenario='shipping_delay')
    with pytest.raises(ValueError, match='stale'):
        session.confirm_pending_update()
    assert session.scenario == 'shipping_delay'


def test_impact_has_source_evidence(session):
    tool = {t.name: t for t in build_tools(session)}['get_impact']
    output = tool.invoke({})
    assert output['sources'] and all(row['evidence'] for row in output['rows'])
    assert {'sales_history', 'inventory', 'transfer_costs'} <= {source['table'] for source in output['sources']}


def test_ui_eta_edit_uses_source_date(monkeypatch):
    monkeypatch.setattr('agent.assistant.provider_config', lambda: (None, 'Assistant disabled for test'))
    app = AppTest.from_file('app.py', default_timeout=90).run()
    app.selectbox(key='scenario_choice').set_value('component_shortage').run()
    app.selectbox(key='edit_table').set_value('inbound_orders').run()
    assert not app.exception
    snapshot = app.session_state['planning'].result.snapshot_id
    key = f'editor_inbound_orders_SKU01_{snapshot}'
    app.session_state[key] = {'edited_rows': {0: {'arrival_date': '2026-11-01'}}, 'added_rows': [], 'deleted_rows': []}
    app.button(key='FormSubmitter:edit_records-Save corrections and recompute').click().run()
    assert not app.exception
    row = app.session_state['planning'].result.data.tables['inbound_orders'].iloc[0]
    assert row.original_arrival_date == '2026-10-31'
    assert row.pre_scenario_arrival_date == '2026-11-01'
    assert row.arrival_date == '2026-11-19'
