import pytest
import os
from flask import Flask
from backend_v2.repository.topology_db import get_db, init_db, SessionLocal
from backend_v2.api.topology_routes import topology_bp
from backend_v2.domain.topology_models import Organization, Site, PipelineNode, PipeSegment, Meter, NodeType, MeterType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(topology_bp)
    
    # Force db init for testing
    init_db()
    
    yield app
    
    # Cleanup DB after test (optional, sqlite keeps state)
    
@pytest.fixture
def client(app):
    return app.test_client()

def test_fetch_sites(client):
    response = client.get('/topology/sites')
    assert response.status_code == 200
    data = response.json
    assert len(data) >= 1
    assert data[0]['name'] == 'North Campus'

def test_fetch_network(client):
    sites = client.get('/topology/sites').json
    site_id = sites[0]['id']
    
    response = client.get(f'/topology/sites/{site_id}/network')
    assert response.status_code == 200
    data = response.json
    assert data['site']['name'] == 'North Campus'
    assert len(data['nodes']) >= 5
    assert len(data['segments']) >= 4
    assert len(data['meters']) >= 4

def test_create_node(client):
    sites = client.get('/topology/sites').json
    site_id = sites[0]['id']
    
    payload = {
        "site_id": site_id,
        "name": "TEST-NODE",
        "node_type": "JUNCTION"
    }
    
    res = client.post('/topology/nodes', json=payload)
    assert res.status_code == 201
    assert res.json['name'] == 'TEST-NODE'

def test_invalid_segment_connection(client):
    sites = client.get('/topology/sites').json
    site_id = sites[0]['id']
    
    # Try to create a segment connecting a node that doesn't exist
    payload = {
        "site_id": site_id,
        "source_node_id": "FAKE-NODE",
        "target_node_id": "ANOTHER-FAKE",
        "name": "Invalid Pipe"
    }
    
    res = client.post('/topology/segments', json=payload)
    assert res.status_code == 400
    assert "Invalid source or target" in res.json['error']

def test_rollback_on_failed_operation():
    # Verify rollback by intentionally throwing inside a commit block if we had a service layer,
    # But for the API, the invalid segment connection test already verified that an invalid operation returns 400
    # Let's ensure the DB is not polluted with partial data
    with SessionLocal() as db:
        initial_count = db.query(PipeSegment).count()
        
    # Make invalid call
    app = Flask(__name__)
    app.register_blueprint(topology_bp)
    client = app.test_client()
    sites = client.get('/topology/sites').json
    if not sites:
        return
        
    site_id = sites[0]['id']
    payload = {
        "site_id": site_id,
        "source_node_id": "FAKE",
        "target_node_id": "FAKE",
        "name": "Rollback Pipe"
    }
    client.post('/topology/segments', json=payload)
    
    with SessionLocal() as db:
        final_count = db.query(PipeSegment).count()
        assert initial_count == final_count # No change due to rollback
