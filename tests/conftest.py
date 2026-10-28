import pytest
from engine.data_loader import load_data
from engine.state import run_pipeline


@pytest.fixture(scope='session')
def data():
    return load_data()


@pytest.fixture(scope='session')
def result(data):
    return run_pipeline(data)


@pytest.fixture(scope='session')
def component(data):
    return run_pipeline(data, scenario='component_shortage')


@pytest.fixture(scope='session')
def shipping(data):
    return run_pipeline(data, scenario='shipping_delay')
