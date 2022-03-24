"""
Test restart endpoint
"""

import pytest
import requests

from .settings import APP_URL
from .util import run_devnet_in_background

@pytest.fixture(autouse=True)
def run_before_and_after_test():
    """Run devnet before and kill it after the test run"""
    # before test
    devnet_proc = run_devnet_in_background()

    yield

    # after test
    devnet_proc.kill()

def get_restart_response():
    """Get restart response"""
    print(f"{APP_URL}/restart")
    return requests.get(f"{APP_URL}/restart")

@pytest.mark.restart
def test_restart_on_initial_state():
    """Checks restart endpoint when there were no changes"""
    res = get_restart_response()
    assert res.status_code == 200
