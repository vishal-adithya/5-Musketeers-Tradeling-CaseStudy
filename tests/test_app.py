import pytest
from streamlit.testing.v1 import AppTest
from agent.approval import ApprovalWorkflow


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.setattr('agent.assistant.load_dotenv', lambda: None)
    at = AppTest.from_file('app.py', default_timeout=90).run()
    at.session_state['approvals'] = ApprovalWorkflow(tmp_path / 'approvals_log.csv')
    assert not at.exception
    return at


def test_seven_tabs_offline(app):
    assert len(app.tabs) == 7
    assert any('Assistant disabled' in item.value for item in app.info)
    assert app.chat_input[0].disabled
    assert len(app.session_state['planning'].result.recommendations) > 0


def test_scenario_controls_refresh(app):
    old = app.session_state['planning'].result.snapshot_id
    app.selectbox(key='scenario_choice').set_value('component_shortage').run()
    assert not app.exception
    result = app.session_state['planning'].result
    assert result.scenario == 'component_shortage' and result.snapshot_id != old
    app.number_input(key='delay_component_shortage').set_value(25)
    app.button(key='FormSubmitter:disruption_assumptions-Apply disruption assumption').click().run()
    assert not app.exception
    assert app.session_state['planning'].result.event['delay_days'] == 25
    app.selectbox(key='scenario_choice').set_value('None').run()
    assert not app.exception
    assert app.session_state['planning'].result.snapshot_id == old


@pytest.mark.parametrize('decision', ['approve', 'reject'])
def test_ui_human_decision(app, decision):
    app.button(key='open_review').click().run()
    assert not app.exception
    assert app.session_state['approvals'].read_log().empty
    app.button(key=decision).click().run()
    assert not app.exception
    log = app.session_state['approvals'].read_log()
    assert len(log) == 1 and log.iloc[0].decision.lower() == decision
    assert app.session_state['planning'].result.stock.available.sum() == 5000


def test_editor_save_recomputes_all_tabs(app):
    session = app.session_state['planning']
    old = session.result.snapshot_id
    key = f'editor_inventory_SKU01_{old}'
    app.session_state[key] = {'edited_rows': {1: {'available': 400}}, 'added_rows': [], 'deleted_rows': []}
    app.button(key='FormSubmitter:edit_records-Save corrections and recompute').click().run()
    assert not app.exception
    revised = app.session_state['planning'].result
    assert revised.snapshot_id != old
    assert revised.stock.query('sku == "SKU01" and location == "Abu Dhabi"').available.iloc[0] == 400
    assert revised.recommendations.query('sku == "SKU01"').empty
    assert revised.corrections
