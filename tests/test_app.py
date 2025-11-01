import pytest
from bgp_defense_tool import create_app

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    yield app

@pytest.fixture
def client(app, mocker):
    """A test client for the app."""
    # Mock the database connection for all tests in this file
    mocker.patch('bgp_defense_tool.blueprints.main.get_db_connection')
    return app.test_client()

def test_index_route(client):
    """Test that the index route returns a 200 OK response."""
    response = client.get('/')
    assert response.status_code == 200

def test_neighbors_route(client):
    """Test that the neighbors route returns a 200 OK response."""
    response = client.get('/neighbors')
    assert response.status_code == 200

def test_auditing_route(client, mocker):
    """Test that the auditing route returns a 200 OK response."""
    # Mock the router call to avoid a live connection
    mocker.patch('bgp_defense_tool.blueprints.main.send_config_to_router', return_value="")
    response = client.get('/auditing')
    assert response.status_code == 200

def test_automation_log_route(client):
    """Test that the automation_log route returns a 200 OK response."""
    response = client.get('/automation_log')
    assert response.status_code == 200

def test_history_route(client):
    """Test that the history route returns a 200 OK response."""
    response = client.get('/history')
    assert response.status_code == 200

def test_analytics_route(client):
    """Test that the analytics route returns a 200 OK response."""
    response = client.get('/analytics')
    assert response.status_code == 200

def test_on_router_defense_route(client):
    """Test that the on_router_defense route returns a 200 OK response."""
    response = client.get('/on_router_defense')
    assert response.status_code == 200

def test_rpki_helper_route(client):
    """Test that the rpki_helper route returns a 200 OK response."""
    response = client.get('/rpki_helper')
    assert response.status_code == 200
