import numpy as np
import pandas as pd
import pytest
from engine.data_loader import ROOT
from evaluate import error_metrics, backtest, check_cases


def test_zero_and_missing_metric_denominators():
    result = error_metrics([0, 10, np.nan], [2, 8, 100])
    assert result['MAPE_pct'] == pytest.approx(20)
    assert result['WAPE_pct'] == pytest.approx(40)
    assert result['observations'] == 2
    assert result['zero_actual_excluded_from_MAPE'] == 1
    assert np.isnan(error_metrics([0], [1])['WAPE_pct'])


def test_holdout_has_no_future_sales_leakage(data):
    answer = pd.read_csv(ROOT / 'data' / 'answer_key.csv', keep_default_na=False)
    metrics, coverage, cutoff, joined = backtest(data, answer)
    changed = data.copy()
    history = changed.tables['sales_history']
    history.loc[pd.to_datetime(history.date).gt(cutoff), 'units'] = 9999
    _, _, _, second = backtest(changed, answer)
    assert joined.p50.equals(second.p50)
    assert joined.baseline.equals(second.baseline)
    assert joined.date.min() > cutoff and len(joined) == 1800
    assert len(metrics) == 6 and 0 <= coverage <= 100


def test_answer_key_checks(data, result, component, shipping):
    answer = pd.read_csv(ROOT / 'data' / 'answer_key.csv', keep_default_na=False)
    checks = check_cases(data, {'None': result, 'component_shortage': component, 'shipping_delay': shipping}, answer)
    assert checks.passed.all(), checks[~checks.passed].to_string(index=False)
