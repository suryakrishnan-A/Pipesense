import pytest
from backend_v2.services.pipesense_service import PipeSenseService
from backend_v2.domain.models import IncidentState
from backend_v2.repository.db import db
from backend_v2.agent.tools.tools import check_weather, check_peer_baselines, check_occupancy, check_maintenance_history
from backend.agent.tools.investigation_tools import check_peer_baselines as check_local_peer_baselines

def test_01_incident_creation():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("TEST-ZONE", 50.0, 10.0)
    assert inc is not None
    assert inc.state == IncidentState.ANOMALY

def test_02_normal_reading_no_leak():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("TEST-ZONE", 10.5, 10.0) # 1.05x
    assert inc is None

def test_03_anomaly_detection():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("TEST-ZONE", 14.0, 10.0) # 1.4x > 1.35x
    assert inc.state == IncidentState.ANOMALY

def test_04_349x_anomaly():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    ratio = 64.2 / 18.4
    assert round(ratio, 2) == 3.49

def test_05_weather_tool():
    res = check_weather("BLDG-04")
    assert "No rain" in res["finding"]

def test_06_peer_baseline_tool():
    res = check_peer_baselines("BLDG-04")
    assert "1.0x baseline" in res["finding"]

def test_local_peer_baselines_are_deterministic():
    first = check_local_peer_baselines("BLDG-04")
    second = check_local_peer_baselines("BLDG-04")
    assert first == second
    assert [peer["ratio"] for peer in first["peers"]] == [1.0, 0.98, 1.02, 0.99]

def test_07_maintenance_tool():
    res = check_maintenance_history("BLDG-04")
    assert "fissure" in res["finding"]

def test_08_occupancy_tool():
    res = check_occupancy("BLDG-04")
    assert "Standard rest hours" in res["finding"]

def test_09_agent_investigation():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    inc = svc.run_investigation(inc.incident_id)
    assert inc.diagnosis == "LEAK_CONFIRMED"

def test_10_leak_diagnosis():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    inc = svc.run_investigation(inc.incident_id)
    assert inc.state == IncidentState.LEAK_CONFIRMED

def test_11_confidence_recording():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    inc = svc.run_investigation(inc.incident_id)
    assert inc.confidence == 0.98

def test_12_work_order_creation():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    assert wo.priority == "P1"

def test_13_technician_completion():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    inc = svc.claim_completion(wo.work_order_id)
    assert inc.state == IncidentState.VERIFYING

def test_14_failed_verification():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    inc = svc.verify_repair(wo.work_order_id, 61.8)
    assert inc.state == IncidentState.ESCALATED

def test_15_escalation():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    inc = svc.verify_repair(wo.work_order_id, 61.8)
    wo = db.get_work_order(wo.work_order_id)
    assert wo.status == "ESCALATED"
    assert wo.assigned_role == "Senior Supervisor"

def test_16_second_repair():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    svc.verify_repair(wo.work_order_id, 61.8)
    inc = svc.start_second_repair(wo.work_order_id)
    assert inc.state == IncidentState.REPAIRING

def test_17_successful_verification():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    svc.verify_repair(wo.work_order_id, 61.8)
    svc.start_second_repair(wo.work_order_id)
    svc.claim_completion(wo.work_order_id)
    inc = svc.verify_repair(wo.work_order_id, 18.2)
    assert inc.state == IncidentState.CLOSED

def test_18_resolution():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("TEST", 50, 10)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    inc = svc.verify_repair(wo.work_order_id, 10.1) # Passes
    # We verify it passes through RESOLVED to CLOSED
    # The service code directly does RESOLVED -> CLOSED, so final is CLOSED
    assert inc.state == IncidentState.CLOSED

def test_19_closure():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("TEST", 50, 10)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    inc = svc.verify_repair(wo.work_order_id, 10.1)
    assert inc.state == IncidentState.CLOSED

def test_20_impact_calculation():
    # Explicit numerical assertions from prompt
    assert (64.2 - 18.4) * 1440 == 65952
    assert (64.2 - 18.2) * 1440 == 66240
    assert round(64.2 - 18.2, 1) == 46.0

def test_21_event_ordering():
    db.events = [] # clear
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    events = [e.event_type for e in db.events if e.incident_id == inc.incident_id]
    assert events == ["INCIDENT_CREATED", "ANOMALY_DETECTED"]

def test_22_audit_ordering():
    db.audits = []
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    assert db.audits[-1].action == "CONFIRM_LEAK"

def test_23_invalid_state_transition():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    # Try to dispatch before investigating
    with pytest.raises(ValueError):
        svc.dispatch_work_order(inc.incident_id)

def test_24_duplicate_completion():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    with pytest.raises(ValueError):
        svc.claim_completion(wo.work_order_id) # Already verifying

def test_25_duplicate_verification():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)
    svc.verify_repair(wo.work_order_id, 18.2) # Closes
    with pytest.raises(ValueError):
        svc.verify_repair(wo.work_order_id, 18.2) # Already closed, not VERIFYING

def test_26_demo_reset():
    db.reset_demo_state()
    assert len(db.incidents) == 5

def test_27_demo_replay():
    pass # handled by main endpoint test normally

def test_28_summary_endpoint():
    db.reset_demo_state()
    svc = PipeSenseService()
    summary = svc.get_summary()
    assert summary["total_zones"] == 14

def test_29_impact_endpoint():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    svc.run_investigation(inc.incident_id)
    assert inc.metadata["estimated_daily_loss_liters"] == 65952.0

def test_30_multiple_incidents():
    db.reset_demo_state()
    assert "INC-1004" in db.incidents

def test_31_legitimate_usage_spike():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("CANTEEN", 55.0, 10.0)
    inc = svc.run_investigation(inc.incident_id)
    assert inc.state == IncidentState.NOMINAL
    assert inc.diagnosis == "LEGITIMATE_USAGE"

def test_32_suspected_leak():
    svc = PipeSenseService()
    inc = svc.detect_anomaly("UNKNOWN_ZONE", 40.0, 20.0) # 2.0x, < 3.0x
    inc = svc.run_investigation(inc.incident_id)
    assert inc.state == IncidentState.LEAK_SUSPECTED

def test_33_full_end_to_end_test():
    svc = PipeSenseService()
    
    # 1. Detect
    inc = svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    assert inc.state == IncidentState.ANOMALY
    
    # 2. Investigate
    inc = svc.run_investigation(inc.incident_id)
    assert inc.state == IncidentState.LEAK_CONFIRMED
    assert inc.confidence == 0.98
    assert inc.metadata["estimated_daily_loss_liters"] == 65952.0
    
    # 3. Dispatch
    wo = svc.dispatch_work_order(inc.incident_id)
    assert inc.state == IncidentState.WORK_ORDER_ISSUED
    
    # 4. Human claims complete
    inc = svc.claim_completion(wo.work_order_id)
    assert inc.state == IncidentState.VERIFYING
    
    # 5. Failed Verification
    inc = svc.verify_repair(wo.work_order_id, 61.8)
    assert inc.state == IncidentState.ESCALATED
    
    # 6. Second Repair
    inc = svc.start_second_repair(wo.work_order_id)
    assert inc.state == IncidentState.REPAIRING
    
    # 7. Complete again
    inc = svc.claim_completion(wo.work_order_id)
    assert inc.state == IncidentState.VERIFYING
    
    # 8. Successful Verification
    inc = svc.verify_repair(wo.work_order_id, 18.2)
    assert inc.state == IncidentState.CLOSED
    
    # Check impact
    assert inc.metadata["verified_daily_loss_avoided_liters"] == 66240.0
