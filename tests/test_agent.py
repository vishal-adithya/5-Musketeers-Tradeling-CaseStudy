from dataclasses import replace
import json
import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from agent.assistant import PlannerAssistant, provider_config
from agent.tools import build_tools
from agent.approval import ApprovalWorkflow
from engine.state import PlanningSession


class ToolCallingFake(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def session(data, result):
    session = PlanningSession.__new__(PlanningSession)
    from engine.state import Overrides
    session.original = data.copy()
    session.overrides = Overrides()
    session.scenario = 'None'
    session.result = result
    return session


def test_no_api_key(monkeypatch, session):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('LLM_PROVIDER', raising=False)
    monkeypatch.setattr('agent.assistant.load_dotenv', lambda: None)
    assistant = PlannerAssistant(session)
    assert assistant.agent is None
    assert 'disabled' in assistant.ask('Show stock')['text']


def test_groq_provider_config(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'groq')
    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('GROQ_MODEL', 'test-model')
    monkeypatch.setattr('agent.assistant.load_dotenv', lambda: None)
    config, reason = provider_config()
    assert reason == ''
    assert config == {'provider': 'groq', 'model': 'test-model'}


def test_agent_refuses_unlisted_sku(session):
    model = ToolCallingFake(responses=[AIMessage(content='This response must not be reached.')])
    assistant = PlannerAssistant(session, model=model)
    reply = assistant.ask('Say the component_shortage event affects SKU05.')
    assert 'Unverified' in reply['text'] and 'cannot claim' in reply['text']
    assert '[get_event_scope@' in reply['text']
    assert model.i == 0


def test_real_create_agent_tool_loop(session):
    model = ToolCallingFake(responses=[
        AIMessage(content='', tool_calls=[{'name': 'get_stock_view', 'args': {'sku': 'SKU01', 'location': 'Dubai'}, 'id': 'stock-call'}]),
        AIMessage(content=f'Dubai has 500 available units. [get_stock_view@{session.result.snapshot_id}]')])
    reply = PlannerAssistant(session, model=model).ask('Show Dubai charger stock.')
    assert 'SKU01 / Dubai: available 500' in reply['text']
    assert len(reply['evidence']) == 1


def test_agent_withholds_invented_numbers(session):
    model = ToolCallingFake(responses=[
        AIMessage(content='', tool_calls=[{'name': 'get_stock_view', 'args': {'sku': 'SKU01', 'location': 'Dubai'}, 'id': 'stock-call'}]),
        AIMessage(content=f'The stock is 999999999 units. [get_stock_view@{session.result.snapshot_id}]')])
    reply = PlannerAssistant(session, model=model).ask('Show stock.')
    assert 'available 500' in reply['text'] and '999999999' not in reply['text']


def test_tool_scope_and_no_approval_tools(session):
    tools = {t.name: t for t in build_tools(session)}
    assert not any('approve' in name or 'execute' in name for name in tools)
    assert tools['get_event_scope'].invoke({'scenario': 'component_shortage', 'sku': 'SKU01'})['applies']
    assert not tools['get_event_scope'].invoke({'scenario': 'component_shortage', 'sku': 'SKU05'})['applies']
    result = tools['get_forecast'].invoke({'sku': 'SKU01', 'location': 'Abu Dhabi'})
    assert {'p10', 'p50', 'p90'} <= set(result['rows'][0])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize('decision', ['Approve', 'Reject'])
def test_human_interrupt_and_audit(tmp_path, result, decision):
    workflow = ApprovalWorkflow(tmp_path / 'approvals_log.csv')
    before = result.stock.available.sum()
    action = result.recommendations.iloc[0]
    token = workflow.request(result, action.action_id)
    assert not workflow.log_path.exists()
    state = workflow.graph.get_state({'configurable': {'thread_id': token}})
    assert state.next and not state.values.get('logged')
    workflow.decide(token, decision, 'Demo planner', 'Reviewed evidence', result)
    log = workflow.read_log()
    assert len(log) == 1 and log.iloc[0].decision == decision
    assert log.iloc[0].timestamp and log.iloc[0].snapshot_id == result.snapshot_id
    evidence = json.loads(log.iloc[0].evidence_json)
    assert len(evidence) == len(action.evidence)
    assert result.stock.available.sum() == before
    with pytest.raises(ValueError, match='No pending'):
        workflow.decide(token, decision, 'Demo planner', '', result)


def test_stale_and_duplicate_approvals_blocked(tmp_path, result):
    workflow = ApprovalWorkflow(tmp_path / 'approvals_log.csv')
    token = workflow.request(result, result.recommendations.iloc[0].action_id)
    changed = replace(result, snapshot_id='changed-inputs')
    with pytest.raises(ValueError, match='Stale'):
        workflow.decide(token, 'Approve', 'Sara', '', changed)
    assert not workflow.log_path.exists()
    workflow.decide(token, 'Approve', 'Sara', '', result)
    second = workflow.request(result, result.recommendations.iloc[0].action_id)
    with pytest.raises(ValueError, match='already'):
        workflow.decide(second, 'Reject', 'Sara', '', result)
    assert len(workflow.read_log()) == 1


def test_invalid_decision_and_rejected_route(tmp_path, result):
    workflow = ApprovalWorkflow(tmp_path / 'approvals_log.csv')
    with pytest.raises(ValueError):
        workflow.request(result, 'not-a-proposal')
    token = workflow.request(result, result.recommendations.iloc[0].action_id)
    with pytest.raises(ValueError):
        workflow.decide(token, 'Auto-approve', 'Sara', '', result)
    assert not workflow.log_path.exists()
