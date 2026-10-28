import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4
import pandas as pd
from filelock import FileLock
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from agent.tools import json_safe

COLUMNS = ['timestamp', 'decision_id', 'snapshot_id', 'action_id', 'decision', 'planner', 'note',
           'sku', 'from_location', 'to_location', 'quantity', 'proposal_json', 'evidence_json']


class HumanDecision(BaseModel):
    decision: Literal['Approve', 'Reject']
    planner: str = Field(min_length=1)
    note: str = ''


class ApprovalState(TypedDict, total=False):
    proposal: dict
    snapshot_id: str
    evidence: dict
    decision_id: str
    logged: bool


class ApprovalWorkflow:
    """Interrupt first; log only after an explicit human decision. No execution node exists."""
    def __init__(self, log_path: Path | str = 'approvals_log.csv'):
        self.log_path = Path(log_path)

        def await_human(state: ApprovalState):
            decision = HumanDecision.model_validate(interrupt({
                'message': 'Planner decision required. Approval records intent only; no stock is moved.',
                'proposal': state['proposal'], 'snapshot_id': state['snapshot_id']}))
            if not decision.planner.strip():
                raise ValueError('Planner name is required')
            proposal = state['proposal']
            row = dict(timestamp=datetime.now(timezone.utc).isoformat(), decision_id=state['decision_id'],
                       snapshot_id=state['snapshot_id'], action_id=proposal['action_id'],
                       **decision.model_dump(), sku=proposal['sku'], from_location=proposal['from_location'],
                       to_location=proposal['to_location'], quantity=proposal['quantity'],
                       proposal_json=json.dumps(json_safe(proposal), allow_nan=False),
                       evidence_json=json.dumps(json_safe(state['evidence']), allow_nan=False))
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with FileLock(str(self.log_path) + '.lock'):
                existing = self.read_log()
                if len(existing) and ((existing.snapshot_id == state['snapshot_id']) & (existing.action_id == proposal['action_id'])).any():
                    raise ValueError('This proposal snapshot already has a recorded decision')
                with self.log_path.open('a', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=COLUMNS)
                    if file.tell() == 0:
                        writer.writeheader()
                    writer.writerow(row)
            return {'logged': True}

        graph = StateGraph(ApprovalState)
        graph.add_node('human_review', await_human)
        graph.add_edge(START, 'human_review')
        graph.add_edge('human_review', END)
        self.graph = graph.compile(checkpointer=InMemorySaver())

    def read_log(self):
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            return pd.DataFrame(columns=COLUMNS)
        return pd.read_csv(self.log_path, dtype=str, keep_default_na=False)

    def request(self, result, action_id: str) -> str:
        rows = result.recommendations[result.recommendations.action_id.eq(action_id)]
        if len(rows) != 1:
            raise ValueError('Only an existing accepted proposal can be reviewed')
        proposal = json_safe(rows.iloc[0].to_dict())
        token = str(uuid4())
        state = self.graph.invoke(dict(proposal=proposal, snapshot_id=result.snapshot_id, decision_id=token,
                                       evidence={ref: json_safe(result.evidence[ref]) for ref in proposal['evidence']}),
                                  config={'configurable': {'thread_id': token}})
        if '__interrupt__' not in state:
            raise RuntimeError('Approval graph did not interrupt')
        return token

    def decide(self, token: str, decision: str, planner: str, note: str, current_result):
        value = HumanDecision(decision=decision, planner=planner, note=note)
        config = {'configurable': {'thread_id': token}}
        pending = self.graph.get_state(config)
        if not pending.next:
            raise ValueError('No pending human review for this token')
        if pending.values['snapshot_id'] != current_result.snapshot_id:
            raise ValueError('Stale proposal: inputs changed. Review the recomputed recommendation before deciding.')
        return self.graph.invoke(Command(resume=value.model_dump()), config=config)
