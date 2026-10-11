"""
Test Suite for DrainPilot API Integration (Phases 2 & 3).

Validates:
- POST /drainpilot/detect: anomaly detection, nominal flows, input validation errors
- GET  /drainpilot/incidents: lists only DrainPilot incidents (system isolation)
- GET  /drainpilot/incidents/<incident_id>: retrieval, 404 handling, cross-system isolation
- POST /drainpilot/incidents/<incident_id>/investigate: agent investigation, 404, 400 wrong-system, 409 invalid state
- POST /drainpilot/incidents/<incident_id>/dispatch: maintenance dispatch, assignment to Drainage & Civils, 404, 400, 409
- GET  /drainpilot/work-orders: list only DrainPilot work orders
- GET  /drainpilot/work-orders/<work_order_id>: retrieve DrainPilot work order, 404 for PipeSense work orders
- POST /drainpilot/work-orders/<work_order_id>/complete: technician completion claim, moves to VERIFYING (does not close)
- POST /drainpilot/work-orders/<work_order_id>/verify: post-maintenance verification (rejection -> escalation, pass -> closure)
- POST /drainpilot/work-orders/<work_order_id>/repair: second maintenance attempt from ESCALATED
- GET  /drainpilot/summary: drainage operational metrics including work orders
- Full closed-loop resolution verification
- Coexistence with existing PipeSense routes without conflicts
"""

import pytest
from backend_v2.api.main import app
from backend_v2.repository.db import db
from backend_v2.domain.models import IncidentState

@pytest.fixture
def client():
    """Flask test client fixture with clean demo database state."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        db.reset_demo_state()
        yield client
        db.reset_demo_state()

# ----------------------------------------------------------------------
# 1. POST /drainpilot/detect
# ----------------------------------------------------------------------

def test_01_detect_anomaly_success(client):
    """Anomalous telemetry creates an incident with HTTP 201."""
    payload = {
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 88.0,
        "rate_of_rise_cm_per_hr": 16.5,
        "pump_status": "OFF"
    }
    res = client.post("/drainpilot/detect", json=payload)
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "ANOMALY_DETECTED"
    assert data["system"] == "DRAIN"
    assert data["zone"] == "DRAIN-NORTH-01"
    assert data["state"] == IncidentState.ANOMALY.value
    assert data["severity"] == "CRITICAL"
    assert data["priority"] == "P1"
    assert data["is_simulated"] is True
    assert data["metadata"]["overflow_risk_flag"] is True

def test_02_detect_nominal_success(client):
    """Nominal telemetry returns HTTP 200 with no incident created."""
    payload = {
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 25.0,
        "rate_of_rise_cm_per_hr": 1.0,
        "pump_status": "OFF"
    }
    res = client.post("/drainpilot/detect", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "NOMINAL"
    assert "within safe operating parameters" in data["message"]
    assert data["is_simulated"] is True

def test_03_detect_invalid_telemetry_missing_depth(client):
    """Missing required depth returns HTTP 400."""
    payload = {
        "zone": "DRAIN-NORTH-01",
        "water_level_cm": 50.0
    }
    res = client.post("/drainpilot/detect", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data
    assert "chamber_depth_cm" in data["error"]
    assert data["is_simulated"] is True

def test_04_detect_invalid_telemetry_negative_level(client):
    """Negative water level returns HTTP 400."""
    payload = {
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": -12.0
    }
    res = client.post("/drainpilot/detect", json=payload)
    assert res.status_code == 400
    data = res.get_json()
    assert "cannot be negative" in data["error"]
    assert data["is_simulated"] is True

def test_05_detect_empty_or_non_json_payload(client):
    """Non-JSON or empty body returns HTTP 400."""
    res = client.post("/drainpilot/detect", data="not json", content_type="text/plain")
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data
    assert data["is_simulated"] is True

# ----------------------------------------------------------------------
# 2. GET /drainpilot/incidents (System Isolation)
# ----------------------------------------------------------------------

def test_06_list_drain_incidents_only(client):
    """Lists only incidents with system='DRAIN', isolating from PipeSense."""
    res_initial = client.get("/drainpilot/incidents")
    assert res_initial.status_code == 200
    assert len(res_initial.get_json()) == 0

    client.post("/drainpilot/detect", json={
        "zone": "DRAIN-CULVERT-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 75.0
    })
    client.post("/drainpilot/detect", json={
        "zone": "DRAIN-CULVERT-02",
        "chamber_depth_cm": 120.0,
        "water_level_cm": 90.0
    })

    res = client.get("/drainpilot/incidents")
    assert res.status_code == 200
    incidents = res.get_json()
    assert len(incidents) == 2
    for inc in incidents:
        assert inc["system"] == "DRAIN"

# ----------------------------------------------------------------------
# 3. GET /drainpilot/incidents/<incident_id>
# ----------------------------------------------------------------------

def test_07_get_drain_incident_by_id(client):
    """Retrieves an existing DrainPilot incident by ID."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]

    res = client.get(f"/drainpilot/incidents/{inc_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["incident_id"] == inc_id
    assert data["system"] == "DRAIN"

def test_08_get_drain_incident_not_found(client):
    """Returns HTTP 404 for non-existent incident ID."""
    res = client.get("/drainpilot/incidents/INC-NONEXISTENT")
    assert res.status_code == 404
    data = res.get_json()
    assert "not found" in data["error"]
    assert data["is_simulated"] is True

def test_09_get_drain_incident_rejects_pipesense_incident(client):
    """Returns HTTP 404 when querying a PipeSense incident on DrainPilot route."""
    res = client.get("/drainpilot/incidents/INC-1002")
    assert res.status_code == 404
    data = res.get_json()
    assert "not found" in data["error"]

# ----------------------------------------------------------------------
# 4. POST /drainpilot/incidents/<incident_id>/investigate
# ----------------------------------------------------------------------

def test_10_investigate_drain_incident_success(client):
    """Executes agent investigation on an existing anomaly."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]

    res_inv = client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    assert res_inv.status_code == 200
    data = res_inv.get_json()
    assert data["incident_id"] == inc_id
    assert data["state"] == IncidentState.INVESTIGATING.value
    assert data["diagnosis"] == "INTERNAL_SILT_BLOCKAGE"
    assert data["confidence"] == 0.96
    assert data["metadata"]["confidence_type"] == "DEMO_ESTIMATE"
    assert len(data["metadata"]["agent_evidence"]) == 4

def test_11_investigate_nonexistent_incident(client):
    """Returns HTTP 404 when investigating a missing incident."""
    res = client.post("/drainpilot/incidents/INC-NONEXISTENT/investigate")
    assert res.status_code == 404
    assert "not found" in res.get_json()["error"]

def test_12_investigate_pipesense_incident_rejected(client):
    """Returns HTTP 400 when attempting to investigate a PipeSense incident."""
    res = client.post("/drainpilot/incidents/INC-1002/investigate")
    assert res.status_code == 400
    data = res.get_json()
    assert "belongs to system 'PIPE'" in data["error"]

def test_13_investigate_invalid_state_transition(client):
    """Returns HTTP 409 when investigating an incident not in ANOMALY state."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]

    res_1 = client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    assert res_1.status_code == 200

    res_2 = client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    assert res_2.status_code == 409
    data = res_2.get_json()
    assert "Invalid state transition" in data["error"]

# ----------------------------------------------------------------------
# 5. Work Order Dispatch & Retrieval
# ----------------------------------------------------------------------

def test_14_dispatch_work_order_success(client):
    """Dispatches a work order for an investigated incident with HTTP 201."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")

    res_dispatch = client.post(f"/drainpilot/incidents/{inc_id}/dispatch")
    assert res_dispatch.status_code == 201
    wo = res_dispatch.get_json()
    assert wo["incident_id"] == inc_id
    assert wo["assigned_role"] == "Drainage & Civils"
    assert "Manoj Sharma" in wo["assigned_person"]
    assert wo["status"] == "ASSIGNED"
    assert wo["is_simulated"] is True

def test_15_dispatch_nonexistent_incident(client):
    """Returns HTTP 404 when dispatching on missing incident."""
    res = client.post("/drainpilot/incidents/INC-NONEXISTENT/dispatch")
    assert res.status_code == 404

def test_16_dispatch_pipesense_incident_rejected(client):
    """Returns HTTP 400 when dispatching on a PipeSense incident."""
    res = client.post("/drainpilot/incidents/INC-1002/dispatch")
    assert res.status_code == 400
    assert "belongs to system 'PIPE'" in res.get_json()["error"]

def test_17_list_drain_work_orders_only(client):
    """Lists only DrainPilot work orders, maintaining system isolation."""
    # Seed contains 0 drain work orders initially
    res_init = client.get("/drainpilot/work-orders")
    assert res_init.status_code == 200
    assert len(res_init.get_json()) == 0

    # Create 1 drain work order
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    client.post(f"/drainpilot/incidents/{inc_id}/dispatch")

    res = client.get("/drainpilot/work-orders")
    assert res.status_code == 200
    wos = res.get_json()
    assert len(wos) == 1
    assert wos[0]["incident_id"] == inc_id

def test_18_get_drain_work_order_by_id(client):
    """Retrieves single work order by ID."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    wo_id = client.post(f"/drainpilot/incidents/{inc_id}/dispatch").get_json()["work_order_id"]

    res = client.get(f"/drainpilot/work-orders/{wo_id}")
    assert res.status_code == 200
    assert res.get_json()["work_order_id"] == wo_id

def test_19_get_drain_work_order_rejects_pipesense_wo(client):
    """Returns HTTP 404 when querying a PipeSense work order on Drain route."""
    # Create a PipeSense work order
    from backend_v2.services.pipesense_service import PipeSenseService
    ps = PipeSenseService()
    p_inc = ps.detect_anomaly("BLDG-04", 64.2, 18.4)
    ps.run_investigation(p_inc.incident_id)
    p_wo = ps.dispatch_work_order(p_inc.incident_id)

    res = client.get(f"/drainpilot/work-orders/{p_wo.work_order_id}")
    assert res.status_code == 404

# ----------------------------------------------------------------------
# 6. Maintenance Completion & Resolution Verification
# ----------------------------------------------------------------------

def test_20_complete_work_order_moves_to_verifying(client):
    """Completion claim transitions incident to VERIFYING without closing."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    wo_id = client.post(f"/drainpilot/incidents/{inc_id}/dispatch").get_json()["work_order_id"]

    res_comp = client.post(f"/drainpilot/work-orders/{wo_id}/complete")
    assert res_comp.status_code == 200
    data = res_comp.get_json()
    assert data["state"] == IncidentState.VERIFYING.value
    assert data["incident_id"] == inc_id

def test_21_complete_work_order_duplicate_claim_rejected(client):
    """Duplicate completion claim returns HTTP 409."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    wo_id = client.post(f"/drainpilot/incidents/{inc_id}/dispatch").get_json()["work_order_id"]
    client.post(f"/drainpilot/work-orders/{wo_id}/complete")

    # Second claim fails
    res_dup = client.post(f"/drainpilot/work-orders/{wo_id}/complete")
    assert res_dup.status_code == 409

def test_22_verify_resolution_failure_escalates(client):
    """Failed post-maintenance telemetry escalates incident to supervisor."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    wo_id = client.post(f"/drainpilot/incidents/{inc_id}/dispatch").get_json()["work_order_id"]
    client.post(f"/drainpilot/work-orders/{wo_id}/complete")

    # Post-maintenance reading remains at 72 cm (72% > 45% safe threshold)
    res_verif = client.post(f"/drainpilot/work-orders/{wo_id}/verify", json={
        "water_level_cm": 72.0,
        "rate_of_rise_cm_per_hr": 7.0,
        "pump_status": "OFF"
    })
    assert res_verif.status_code == 200
    data = res_verif.get_json()
    assert data["state"] == IncidentState.ESCALATED.value
    assert "failed_verification_telemetry" in data["metadata"]

    # Verify work order status updated
    wo_data = client.get(f"/drainpilot/work-orders/{wo_id}").get_json()
    assert wo_data["status"] == "ESCALATED"
    assert wo_data["assigned_role"] == "Senior Civil Supervisor"

def test_23_verify_resolution_invalid_payload(client):
    """Missing or negative water level in verify returns HTTP 400."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    wo_id = client.post(f"/drainpilot/incidents/{inc_id}/dispatch").get_json()["work_order_id"]
    client.post(f"/drainpilot/work-orders/{wo_id}/complete")

    # Missing water_level_cm
    res_err1 = client.post(f"/drainpilot/work-orders/{wo_id}/verify", json={})
    assert res_err1.status_code == 400

    # Negative water_level_cm
    res_err2 = client.post(f"/drainpilot/work-orders/{wo_id}/verify", json={"water_level_cm": -5.0})
    assert res_err2.status_code == 400

# ----------------------------------------------------------------------
# 7. Second Repair & Full Closed-Loop Flow
# ----------------------------------------------------------------------

def test_24_full_closed_loop_workflow(client):
    """
    Executes complete closed-loop lifecycle:
    1. Detect Anomaly
    2. Investigate
    3. Dispatch Work Order
    4. Technician Claims Complete
    5. Telemetry Fails -> Escalates to Senior Supervisor
    6. Supervisor Starts Second Repair (REPAIRING)
    7. Supervisor Claims Complete
    8. Telemetry Passes -> Incident CLOSED & Capacity Restored
    """
    # 1. Detect
    res_1 = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 85.0
    })
    assert res_1.status_code == 201
    inc_id = res_1.get_json()["incident_id"]

    # 2. Investigate
    res_2 = client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    assert res_2.status_code == 200
    assert res_2.get_json()["diagnosis"] == "INTERNAL_SILT_BLOCKAGE"

    # 3. Dispatch
    res_3 = client.post(f"/drainpilot/incidents/{inc_id}/dispatch")
    assert res_3.status_code == 201
    wo_id = res_3.get_json()["work_order_id"]

    # 4. First completion claim
    res_4 = client.post(f"/drainpilot/work-orders/{wo_id}/complete")
    assert res_4.status_code == 200
    assert res_4.get_json()["state"] == IncidentState.VERIFYING.value

    # 5. First verification fails
    res_5 = client.post(f"/drainpilot/work-orders/{wo_id}/verify", json={
        "water_level_cm": 75.0,
        "rate_of_rise_cm_per_hr": 8.0
    })
    assert res_5.status_code == 200
    assert res_5.get_json()["state"] == IncidentState.ESCALATED.value

    # 6. Supervisor initiates second repair
    res_6 = client.post(f"/drainpilot/work-orders/{wo_id}/repair")
    assert res_6.status_code == 200
    assert res_6.get_json()["state"] == IncidentState.REPAIRING.value

    # 7. Supervisor claims complete
    res_7 = client.post(f"/drainpilot/work-orders/{wo_id}/complete")
    assert res_7.status_code == 200
    assert res_7.get_json()["state"] == IncidentState.VERIFYING.value

    # 8. Second verification passes
    res_8 = client.post(f"/drainpilot/work-orders/{wo_id}/verify", json={
        "water_level_cm": 22.0,
        "rate_of_rise_cm_per_hr": 1.2,
        "pump_status": "OFF"
    })
    assert res_8.status_code == 200
    closed_data = res_8.get_json()
    assert closed_data["state"] == IncidentState.CLOSED.value
    assert closed_data["metadata"]["verified_stormwater_capacity_restored_liters"] > 0

    # Verify work order final state
    wo_final = client.get(f"/drainpilot/work-orders/{wo_id}").get_json()
    assert wo_final["status"] == "CLOSED"
    assert wo_final["verification_status"] == "PASSED"

# ----------------------------------------------------------------------
# 8. GET /drainpilot/summary with Work Orders
# ----------------------------------------------------------------------

def test_25_drain_summary_metrics_with_work_orders(client):
    """Returns drainage operational metrics correctly including work orders."""
    res_detect = client.post("/drainpilot/detect", json={
        "zone": "DRAIN-CRITICAL-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 90.0
    })
    inc_id = res_detect.get_json()["incident_id"]
    client.post(f"/drainpilot/incidents/{inc_id}/investigate")
    client.post(f"/drainpilot/incidents/{inc_id}/dispatch")

    res = client.get("/drainpilot/summary")
    assert res.status_code == 200
    summary = res.get_json()
    assert summary["total_drain_incidents"] == 1
    assert summary["total_work_orders"] == 1
    assert summary["active_work_orders"] == 1
    assert summary["is_simulated"] is True

# ----------------------------------------------------------------------
# 9. Coexistence with PipeSense Endpoints
# ----------------------------------------------------------------------

def test_26_pipesense_endpoints_remain_operational(client):
    """Verifies that existing PipeSense routes remain fully operational."""
    res_ps_inc = client.get("/pipesense/incidents")
    assert res_ps_inc.status_code == 200
    assert len(res_ps_inc.get_json()) == 5

    res_ps_sum = client.get("/pipesense/summary")
    assert res_ps_sum.status_code == 200
    assert "total_zones" in res_ps_sum.get_json()

    res_ps_wo = client.get("/work-orders")
    assert res_ps_wo.status_code == 200
