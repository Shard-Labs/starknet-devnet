import json
import pytest

from starknet_devnet.server import app

def get_state_update():
    """Get state update"""
    return app.test_client().get(
        "/feeder_gateway/get_state_update",
        content_type="application/json",
    )

@pytest.mark.state_update
def test_initial_state_update():
    """Test initial state update"""
    response = get_state_update()

    assert json.loads(response.data) is None
