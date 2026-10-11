"""
Test Suite for DrainPilot Phase 1: Drainage Monitoring & Investigation.

Validates:
- Normal readings (no false anomalies)
- High water-level threshold violations (warning & critical)
- Rapid water-level rises
- Imminent overflow risk calculation
- Abnormal drainage pump activity
- Input validation and missing telemetry handling
- Context tool simulated labeling and outputs
- Autonomous agent diagnosis (silt, surface debris, backwater, extreme rain)
- Demo confidence estimation
- Domain model integrity (system='DRAIN', flow fields untouched, metadata isolation)
- Event sequencing and audit trail integrity
"""

import pytest
from backend_v2.services.drainpilot_service import DrainPilotService
from backend_v2.domain.models import IncidentState
from backend_v2.repository.db import db
from backend_v2.agent.tools.drain_tools import (
    check_catchment_rainfall,
    check_downstream_capacity,
    check_siltation_history,
    check_surface_debris
)

@pytest.fixture(autouse=True)
def reset_database():
    """Ensure a clean in-memory database state before each test."""
    db.reset_demo_state()

# ---------------------------------------------------------
# 1. Telemetry Validation & Input Handling
# ---------------------------------------------------------

def test_01_validation_valid_input():
    svc = DrainPilotService()
    valid_payload = {
        "zone": "DRAIN-01",
        "chamber_depth_cm": 120.0,
        "water_level_cm": 30.0,
        "rate_of_rise_cm_per_hr": 2.5,
        "pump_status": "OFF"
    }
    validated = svc.validate_telemetry(valid_payload)
    assert validated["zone"] == "DRAIN-01"
    assert validated["chamber_depth_cm"] == 120.0
    assert validated["water_level_cm"] == 30.0
    assert validated["pump_status"] == "OFF"

def test_02_validation_missing_optional_fields():
    svc = DrainPilotService()
    minimal_payload = {
        "zone": "DRAIN-02",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 20.0
    }
    validated = svc.validate_telemetry(minimal_payload)
    assert validated["baseline_water_level_cm"] == 0.0
    assert validated["rate_of_rise_cm_per_hr"] == 0.0
    assert validated["pump_status"] == "OFF"

def test_03_validation_negative_water_level():
    svc = DrainPilotService()
    with pytest.raises(ValueError, match="cannot be negative"):
        svc.validate_telemetry({
            "zone": "DRAIN-03",
            "chamber_depth_cm": 100.0,
            "water_level_cm": -5.0
        })

def test_04_validation_invalid_chamber_depth():
    svc = DrainPilotService()
    with pytest.raises(ValueError, match="greater than zero"):
        svc.validate_telemetry({
            "zone": "DRAIN-04",
            "chamber_depth_cm": 0.0,
            "water_level_cm": 10.0
        })

def test_05_validation_missing_zone():
    svc = DrainPilotService()
    with pytest.raises(ValueError, match="non-empty 'zone' string"):
        svc.validate_telemetry({
            "zone": "   ",
            "chamber_depth_cm": 100.0,
            "water_level_cm": 10.0
        })

# ---------------------------------------------------------
# 2. Anomaly Detection & Operational Thresholds
# ---------------------------------------------------------

def test_06_normal_reading_returns_none():
    svc = DrainPilotService()
    # 25 cm in 100 cm chamber = 25% fill ratio (below 65% warning)
    # Rate of rise 2.0 cm/hr (below 15.0 cm/hr threshold)
    # Freeboard 75 cm (well above 15 cm overflow margin)
    result = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 25.0,
        "rate_of_rise_cm_per_hr": 2.0,
        "pump_status": "OFF"
    })
    assert result is None

def test_07_warning_high_water_level():
    svc = DrainPilotService()
    # 70 cm in 100 cm chamber = 70% fill ratio (>= 65% warning threshold)
    inc = svc.detect_anomaly({
        "zone": "DRAIN-CULVERT-02",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 70.0,
        "rate_of_rise_cm_per_hr": 3.0,
        "pump_status": "OFF"
    })
    assert inc is not None
    assert inc.system == "DRAIN"
    assert inc.state == IncidentState.ANOMALY
    assert inc.metadata["high_level_flag"] is True
    assert inc.metadata["fill_ratio"] == 0.70

def test_08_critical_high_water_level():
    svc = DrainPilotService()
    # 88 cm in 100 cm chamber = 88% fill ratio (>= 85% critical threshold)
    inc = svc.detect_anomaly({
        "zone": "DRAIN-CULVERT-03",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 88.0,
        "rate_of_rise_cm_per_hr": 5.0,
        "pump_status": "OFF"
    })
    assert inc is not None
    assert inc.severity == "CRITICAL"
    assert inc.priority == "P1"
    assert inc.metadata["overflow_risk_flag"] is True

def test_09_rapid_water_level_rise_at_low_level():
    svc = DrainPilotService()
    # Low absolute level (35 cm in 100 cm = 35%), but rising rapidly (+22.0 cm/hr >= 15.0)
    inc = svc.detect_anomaly({
        "zone": "DRAIN-SURGE-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 35.0,
        "rate_of_rise_cm_per_hr": 22.0,
        "pump_status": "OFF"
    })
    assert inc is not None
    assert inc.metadata["rapid_rise_flag"] is True
    assert inc.severity == "HIGH"
    assert "Rapid water-level surge" in inc.description

def test_10_imminent_overflow_risk():
    svc = DrainPilotService()
    # 92 cm in 100 cm chamber = freeboard 8 cm (<= 15 cm margin)
    inc = svc.detect_anomaly({
        "zone": "DRAIN-OVERFLOW-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 92.0,
        "rate_of_rise_cm_per_hr": 6.0,
        "pump_status": "RUNNING"
    })
    assert inc is not None
    assert inc.severity == "CRITICAL"
    assert inc.priority == "P1"
    assert inc.metadata["freeboard_cm"] == 8.0
    assert inc.metadata["overflow_risk_flag"] is True

def test_11_abnormal_pump_tripped():
    svc = DrainPilotService()
    # Normal water level (40%), but pump tripped
    inc = svc.detect_anomaly({
        "zone": "DRAIN-PUMP-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 40.0,
        "rate_of_rise_cm_per_hr": 1.0,
        "pump_status": "TRIPPED"
    })
    assert inc is not None
    assert inc.metadata["pump_abnormal_flag"] is True
    assert "TRIPPED" in inc.description

def test_12_domain_model_invariants():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 75.0
    })
    assert inc is not None
    # Crucial architectural rules:
    assert inc.system == "DRAIN"
    assert inc.baseline_flow_lpm == 0.0
    assert inc.current_flow_lpm == 0.0
    assert inc.metadata["water_level_cm"] == 75.0
    assert inc.metadata["chamber_depth_cm"] == 100.0
    assert inc.metadata["data_origin"] == "SIMULATED_BENCHMARK_TELEMETRY"

# ---------------------------------------------------------
# 3. Context Tools & Simulated Labeling
# ---------------------------------------------------------

def test_13_rainfall_tool_simulated_contract():
    res = check_catchment_rainfall("DRAIN-NORTH-01")
    assert res["is_simulated"] is True
    assert "SIMULATED" in res["data_origin"]
    assert "Physical" in res["disclaimer"]
    assert res["weather_condition"] == "DRY"

def test_14_downstream_tool_simulated_contract():
    res = check_downstream_capacity("DRAIN-NORTH-01")
    assert res["is_simulated"] is True
    assert "SIMULATED" in res["data_origin"]
    assert res["backwater_detected"] is False

def test_15_siltation_tool_simulated_contract():
    res = check_siltation_history("DRAIN-NORTH-01")
    assert res["is_simulated"] is True
    assert "SIMULATED" in res["data_origin"]
    assert res["estimated_silt_depth_cm"] == 42.0

def test_16_surface_debris_tool_simulated_contract():
    res = check_surface_debris("DRAIN-CANTEEN-GRATE")
    assert res["is_simulated"] is True
    assert "SIMULATED" in res["data_origin"]
    assert res["grate_obstruction_pct"] == 80.0

# ---------------------------------------------------------
# 4. Agent Autonomous Investigation
# ---------------------------------------------------------

def test_17_investigation_internal_silt_blockage():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    investigated = svc.run_investigation(inc.incident_id)
    assert investigated.state == IncidentState.INVESTIGATING
    assert investigated.diagnosis == "INTERNAL_SILT_BLOCKAGE"
    assert investigated.metadata["recommended_action"] == "DISPATCH_DESILTING_CREW"
    assert investigated.confidence == 0.96
    assert investigated.metadata["confidence_type"] == "DEMO_ESTIMATE"
    assert len(investigated.metadata["agent_evidence"]) == 4

def test_18_investigation_surface_grate_debris():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-CANTEEN-GRATE",
        "chamber_depth_cm": 80.0,
        "water_level_cm": 65.0
    })
    investigated = svc.run_investigation(inc.incident_id)
    assert investigated.state == IncidentState.INVESTIGATING
    assert investigated.diagnosis == "SURFACE_GRATE_OBSTRUCTION"
    assert investigated.metadata["recommended_action"] == "DISPATCH_SURFACE_CLEARANCE"
    assert investigated.confidence == 0.94

def test_19_investigation_downstream_backwater():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-OUTFALL-RIVER",
        "chamber_depth_cm": 150.0,
        "water_level_cm": 130.0
    })
    investigated = svc.run_investigation(inc.incident_id)
    assert investigated.state == IncidentState.INVESTIGATING
    assert investigated.diagnosis == "DOWNSTREAM_BACKWATER_SURCHARGE"
    assert investigated.metadata["recommended_action"] == "MONITOR_TRUNK_DISCHARGE"
    assert investigated.confidence == 0.92

def test_20_investigation_extreme_weather_influx():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-STORM-EAST",
        "chamber_depth_cm": 120.0,
        "water_level_cm": 95.0
    })
    investigated = svc.run_investigation(inc.incident_id)
    assert investigated.state == IncidentState.INVESTIGATING
    assert investigated.diagnosis == "EXTREME_WEATHER_INFLUX"
    assert investigated.metadata["recommended_action"] == "ACTIVATE_ATTENUATION_PUMPS"
    assert investigated.confidence == 0.89

# ---------------------------------------------------------
# 5. Events, Auditing & State Transitions
# ---------------------------------------------------------

def test_21_event_and_audit_emission():
    db.events = []
    db.audits = []
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 75.0
    })
    svc.run_investigation(inc.incident_id)

    event_types = [e.event_type for e in db.events if e.incident_id == inc.incident_id]
    assert "INCIDENT_CREATED" in event_types
    assert "DRAIN_ANOMALY_DETECTED" in event_types
    assert "INVESTIGATION_STARTED" in event_types
    assert "TOOL_CALLED" in event_types
    assert "BLOCKAGE_DIAGNOSED" in event_types

    # Verify audit log
    audit_actions = [a.action for a in db.audits if a.incident_id == inc.incident_id]
    assert "DIAGNOSE_DRAINAGE_ISSUE" in audit_actions
    assert db.audits[-1].actor == "AGENT"
    assert db.audits[-1].old_state == "ANOMALY"
    assert db.audits[-1].new_state == "INVESTIGATING"

def test_22_invalid_state_transition():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 75.0
    })
    # Run investigation once -> state is now INVESTIGATING
    svc.run_investigation(inc.incident_id)
    # Attempting to run investigation again must raise ValueError because it's no longer ANOMALY
    with pytest.raises(ValueError, match="Invalid state transition"):
        svc.run_investigation(inc.incident_id)

def test_23_cross_system_protection():
    # Attempting to run DrainPilot investigation on a PipeSense incident must fail
    from backend_v2.services.pipesense_service import PipeSenseService
    pipe_svc = PipeSenseService()
    pipe_inc = pipe_svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    drain_svc = DrainPilotService()
    with pytest.raises(ValueError, match="belongs to system 'PIPE'"):
        drain_svc.run_investigation(pipe_inc.incident_id)

# ---------------------------------------------------------
# 6. Work Orders, Dispatch, Completion & Resolution
# ---------------------------------------------------------

def test_24_dispatch_work_order_success():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)

    assert wo is not None
    assert wo.assigned_role == "Drainage & Civils"
    assert "Manoj Sharma" in wo.assigned_person
    assert wo.status == "ASSIGNED"
    assert wo.zone == "DRAIN-NORTH-01"

    updated_inc = db.get_incident(inc.incident_id)
    assert updated_inc.state == IncidentState.WORK_ORDER_ISSUED

def test_25_claim_completion_moves_to_verifying():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)

    updated_inc = svc.claim_completion(wo.work_order_id)
    assert updated_inc.state == IncidentState.VERIFYING

    updated_wo = db.get_work_order(wo.work_order_id)
    assert updated_wo.status == "COMPLETION_CLAIMED"
    assert updated_wo.completion_claimed_at is not None

def test_26_verification_failure_escalates():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)

    # Post-maintenance telemetry still high (water level 70 cm / 100 cm = 70% > 45% safe threshold)
    failed_inc = svc.verify_resolution(wo.work_order_id, {
        "water_level_cm": 70.0,
        "rate_of_rise_cm_per_hr": 8.0,
        "pump_status": "OFF"
    })

    assert failed_inc.state == IncidentState.ESCALATED
    updated_wo = db.get_work_order(wo.work_order_id)
    assert updated_wo.verification_status == "FAILED"
    assert updated_wo.status == "ESCALATED"
    assert updated_wo.assigned_role == "Senior Civil Supervisor"
    assert "failed_verification_telemetry" in failed_inc.metadata

def test_27_second_repair_and_successful_closure():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)

    # 1. First verification fails
    svc.verify_resolution(wo.work_order_id, {"water_level_cm": 72.0})
    escalated_inc = db.get_incident(inc.incident_id)
    assert escalated_inc.state == IncidentState.ESCALATED

    # 2. Supervisor starts second repair
    repairing_inc = svc.start_second_repair(wo.work_order_id)
    assert repairing_inc.state == IncidentState.REPAIRING

    # 3. Supervisor claims completion
    svc.claim_completion(wo.work_order_id)
    verifying_inc = db.get_incident(inc.incident_id)
    assert verifying_inc.state == IncidentState.VERIFYING

    # 4. Telemetry passes: water level 20 cm / 100 cm (20% <= 45%, freeboard 80 cm >= 30 cm)
    closed_inc = svc.verify_resolution(wo.work_order_id, {
        "water_level_cm": 20.0,
        "rate_of_rise_cm_per_hr": 1.0,
        "pump_status": "OFF"
    })
    assert closed_inc.state == IncidentState.CLOSED

    final_wo = db.get_work_order(wo.work_order_id)
    assert final_wo.verification_status == "PASSED"
    assert final_wo.status == "CLOSED"
    assert "verified_post_maintenance_telemetry" in closed_inc.metadata
    assert closed_inc.metadata["verified_stormwater_capacity_restored_liters"] > 0

def test_28_duplicate_completion_claim_rejected():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    svc.claim_completion(wo.work_order_id)

    with pytest.raises(ValueError, match="Invalid state transition"):
        svc.claim_completion(wo.work_order_id)

def test_29_verification_wrong_state_rejected():
    svc = DrainPilotService()
    inc = svc.detect_anomaly({
        "zone": "DRAIN-NORTH-01",
        "chamber_depth_cm": 100.0,
        "water_level_cm": 80.0
    })
    svc.run_investigation(inc.incident_id)
    wo = svc.dispatch_work_order(inc.incident_id)
    # Attempt verification while still in WORK_ORDER_ISSUED state (before completion claim)
    with pytest.raises(ValueError, match="must be in VERIFYING state"):
        svc.verify_resolution(wo.work_order_id, {"water_level_cm": 20.0})

def test_30_work_order_cross_system_protection():
    from backend_v2.services.pipesense_service import PipeSenseService
    pipe_svc = PipeSenseService()
    pipe_inc = pipe_svc.detect_anomaly("BLDG-04", 64.2, 18.4)
    pipe_svc.run_investigation(pipe_inc.incident_id)
    pipe_wo = pipe_svc.dispatch_work_order(pipe_inc.incident_id)

    drain_svc = DrainPilotService()
    with pytest.raises(ValueError, match="belongs to system 'PIPE'"):
        drain_svc.claim_completion(pipe_wo.work_order_id)
