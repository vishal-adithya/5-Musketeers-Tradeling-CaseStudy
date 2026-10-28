from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from engine.data_loader import DataSet, validate, stock_view, evidence_registry
from engine.quality import assess_quality
from engine.forecast import forecast
from engine.scenarios import apply_scenario
from engine.imbalance import find_imbalances
from engine.optimizer import optimize
from engine.impact import calculate_impact

EDITABLE = {'inventory': {'available', 'reserved'}, 'sales_history': {'units', 'stockout', 'order_type'},
            'inbound_orders': {'quantity', 'arrival_date'}, 'safety_stock': {'safety_stock'},
            'stock_age': {'units', 'age_days'}}


class Correction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    table: str
    row_id: str
    field: str
    value: Any
    reason: str = Field(min_length=3)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Overrides(BaseModel):
    model_config = ConfigDict(extra='forbid')
    records: list[Correction] = Field(default_factory=list)
    event_delay_days: int | None = Field(default=None, ge=0, le=90)
    event_multiplier: float | None = Field(default=None, ge=0.1, le=3)


@dataclass
class PipelineResult:
    data: DataSet
    stock: pd.DataFrame
    quality: pd.DataFrame
    cleaned_sales: pd.DataFrame
    forecasts: pd.DataFrame
    daily_forecasts: pd.DataFrame
    imbalances: pd.DataFrame
    recommendations: pd.DataFrame
    rejections: pd.DataFrame
    replenishment: pd.DataFrame
    impact: pd.DataFrame
    evidence: dict
    snapshot_id: str
    scenario: str
    event: dict | None
    corrections: list[dict]


def apply_corrections(data: DataSet, records: list[Correction]) -> DataSet:
    working = data.copy()
    for correction in records:
        if correction.table not in EDITABLE or correction.field not in EDITABLE[correction.table]:
            raise ValueError('Field is not editable')
        table = working.tables[correction.table]
        mask = table.row_id.eq(correction.row_id)
        if mask.sum() != 1:
            raise ValueError('Correction must identify exactly one existing source row')
        if correction.field == 'stockout' and not isinstance(correction.value, bool):
            raise ValueError('stockout correction must be boolean')
        if 'original_timestamp' not in table:
            table['original_timestamp'] = table.timestamp
            table['original_source_system'] = table.source_system
        original_field = f'original_{correction.field}'
        if original_field not in table:
            table[original_field] = table[correction.field]
        table.loc[mask, correction.field] = correction.value
        table.loc[mask, 'timestamp'] = correction.timestamp
        table.loc[mask, 'source_system'] = 'planner_correction'
        table.loc[mask, 'correction_reason'] = correction.reason
    validate(working)
    return working


def run_pipeline(data: DataSet, overrides: Overrides | dict | None = None,
                 scenario: str | None = None) -> PipelineResult:
    options = overrides if isinstance(overrides, Overrides) else Overrides.model_validate(overrides or {})
    corrected = apply_corrections(data, options.records)
    working, event = apply_scenario(corrected, scenario, options.event_delay_days, options.event_multiplier)
    validate(working)
    cleaned, quality = assess_quality(working)
    stock = stock_view(working).merge(quality.drop(columns='evidence'), on=['sku', 'location'])
    forecasts, daily = forecast(working, cleaned, quality, event)
    imbalances = find_imbalances(working, stock, forecasts.drop(columns='data_quality'), daily)
    recommendations, rejections, replenishment = optimize(working, imbalances, daily)
    impact = calculate_impact(working, cleaned, daily, recommendations)
    corrections = [record.model_dump() for record in options.records]
    payload = {name: frame.to_json(orient='split', date_format='iso') for name, frame in working.tables.items()}
    payload.update(as_of=str(working.as_of), scenario=scenario or 'None', algorithm='gulftrade-v1')
    snapshot = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    return PipelineResult(working, stock, quality, cleaned, forecasts, daily, imbalances,
                          recommendations, rejections, replenishment, impact, evidence_registry(working),
                          snapshot, scenario or 'None', event, corrections)


class PlanningSession:
    def __init__(self, data: DataSet):
        self.original = data.copy()
        self.overrides = Overrides()
        self.scenario = 'None'
        self.result = run_pipeline(self.original)
        self.pending_update = None

    def stage_update(self, options: Overrides, scenario: str):
        preview = run_pipeline(self.original, options, scenario)
        self.pending_update = {'options': options, 'scenario': scenario, 'base_snapshot': self.result.snapshot_id,
                               'preview_snapshot': preview.snapshot_id}
        return preview

    def confirm_pending_update(self):
        pending = self.pending_update
        if not pending or pending['base_snapshot'] != self.result.snapshot_id:
            self.pending_update = None
            raise ValueError('Pending change is absent or stale. Request a new preview.')
        result = self.update(pending['options'], pending['scenario'])
        self.pending_update = None
        return result

    def update(self, overrides: Overrides | dict | None = None, scenario: str | None = None):
        options = self.overrides if overrides is None else Overrides.model_validate(overrides)
        chosen = self.scenario if scenario is None else scenario
        result = run_pipeline(self.original, options, chosen)
        self.overrides, self.scenario, self.result = options, chosen, result
        return result

    def correct(self, correction: Correction):
        options = self.overrides.model_copy(deep=True)
        options.records.append(correction)
        return self.update(options)
