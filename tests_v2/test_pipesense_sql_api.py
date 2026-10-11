import pytest
from backend_v2.api.main import app
from backend_v2.repository.topology_db import init_db

@pytest.fixture
def client():
    init_db()
    c = app.test_client()
    c.post('/demo/pipesense/reset')
    yield c
    c.post('/demo/pipesense/reset')

def test_agent_status_truthful(client):
    res = client.get('/pipesense/agent-status')
    assert res.status_code == 200
    data = res.json
    assert data['mode'] in ('local_demo', 'local_deterministic')
    assert data['bedrock_enabled'] is False
    assert 'Local Demo Mode' in data['status_text']

def test_thresholds_endpoint(client):
    res = client.get('/pipesense/thresholds')
    assert res.status_code == 200
    data = res.json
    assert data['anomaly_multiplier_threshold'] == 1.35
    assert data['agent_mode'] in ('local_demo', 'local_deterministic')

def test_get_meters_endpoint(client):
    res = client.get('/topology/meters')
    assert res.status_code == 200
    meters = res.json
    assert len(meters) >= 4
    assert any('Main Inlet Flow' in m['name'] for m in meters)

def test_full_pipesense_closed_loop_flow(client):
    # 1. Reset
    r_reset = client.post('/demo/pipesense/reset')
    assert r_reset.status_code == 200

    # 2. Anomaly Detection
    r_det = client.post('/pipesense/detect', json={
        "zone": "BLDG-04",
        "current_flow": 64.2,
        "baseline_flow": 18.4
    })
    assert r_det.status_code == 200
    inc = r_det.json
    assert inc['zone'] == 'BLDG-04'
    inc_id = inc['incident_id']

    # 3. Investigation
    r_inv = client.post(f'/pipesense/incidents/{inc_id}/investigate')
    assert r_inv.status_code == 200
    inv_data = r_inv.json
    assert inv_data['hypothesis'] == 'LEAK_CONFIRMED'

    # 4. Dispatch Work Order
    r_disp = client.post(f'/pipesense/incidents/{inc_id}/dispatch')
    assert r_disp.status_code == 200
    wo = r_disp.json
    wo_id = wo['work_order_id']
    assert wo['status'] == 'PENDING'

    # Check work order initially is NOT completed
    r_wo_check = client.get(f'/work-orders/{wo_id}')
    assert r_wo_check.status_code == 200
    assert r_wo_check.json['status'] == 'PENDING'
    assert r_wo_check.json.get('completed_at') is None

    # 5. Field Completion Claim: Work order must remain PENDING verification
    r_comp = client.post(f'/work-orders/{wo_id}/complete')
    assert r_comp.status_code == 200
    assert r_comp.json['state'] == 'REPAIR_VERIFICATION'

    r_wo_after_claim = client.get(f'/work-orders/{wo_id}')
    assert r_wo_after_claim.status_code == 200
    assert r_wo_after_claim.json['status'] == 'PENDING', "Work order must not be marked COMPLETED upon claim"
    assert r_wo_after_claim.json.get('completed_at') is None

    # 6. Verify Repair - Fails with high telemetry (61.8 L/min)
    r_ver_fail = client.post(f'/work-orders/{wo_id}/verify', json={"telemetry": 61.8})
    assert r_ver_fail.status_code == 200
    assert r_ver_fail.json['state'] == 'OPEN'  # Escalated
    assert r_ver_fail.json.get('post_repair_flow_lpm') is None

    # Work order reverts to IN_PROGRESS upon failed verification, NOT completed
    r_wo_after_fail = client.get(f'/work-orders/{wo_id}')
    assert r_wo_after_fail.status_code == 200
    assert r_wo_after_fail.json['status'] == 'IN_PROGRESS'
    assert r_wo_after_fail.json.get('completed_at') is None

    # Check impact endpoint reports zero avoided loss during failure
    r_imp_fail = client.get('/pipesense/impact')
    assert r_imp_fail.status_code == 200
    assert r_imp_fail.json['verified_daily_loss_avoided_liters'] == 0.0
    assert r_imp_fail.json['verified_post_repair_flow_lpm'] is None

    # 7. Secondary Repair Dispatch
    r_rep = client.post(f'/work-orders/{wo_id}/repair')
    assert r_rep.status_code == 200
    assert r_rep.json['state'] == 'WORK_ORDER_ISSUED'

    # 8. Second Field Completion Claim
    r_comp2 = client.post(f'/work-orders/{wo_id}/complete')
    assert r_comp2.status_code == 200
    r_wo_after_claim2 = client.get(f'/work-orders/{wo_id}')
    assert r_wo_after_claim2.json['status'] == 'PENDING'
    assert r_wo_after_claim2.json.get('completed_at') is None

    # 9. Verify Repair - Passes with restored telemetry (18.2 L/min)
    r_ver_pass = client.post(f'/work-orders/{wo_id}/verify', json={"telemetry": 18.2})
    assert r_ver_pass.status_code == 200
    pass_inc = r_ver_pass.json
    assert pass_inc['state'] == 'RESOLVED'
    # Verify pre-repair peak flow (64.2) and post-repair flow (18.2) remain distinct
    assert pass_inc['current_flow_lpm'] == 64.2
    assert pass_inc['baseline_flow_lpm'] == 18.4
    assert pass_inc['post_repair_flow_lpm'] == 18.2

    # Work order is ONLY NOW marked COMPLETED with completed_at set
    r_wo_final = client.get(f'/work-orders/{wo_id}')
    assert r_wo_final.status_code == 200
    assert r_wo_final.json['status'] == 'COMPLETED'
    assert r_wo_final.json.get('completed_at') is not None

    # 10. Audit logs & events verification
    r_evts = client.get(f'/events/{inc_id}')
    assert r_evts.status_code == 200
    events = r_evts.json
    assert len(events) >= 5
    # Verify event types are populated properly
    event_types = [e['event_type'] for e in events]
    assert 'ANOMALY_DETECTED' in event_types
    assert 'LEAK_CONFIRMED' in event_types
    assert 'FAILED_VERIFICATION' in event_types
    assert 'VERIFIED_RESOLVED' in event_types

    # 11. All audit logs endpoint
    r_all_audit = client.get('/audit-logs')
    assert r_all_audit.status_code == 200
    assert len(r_all_audit.json) >= 5

    # 12. Summary & Impact metrics with exact calculations
    r_sum = client.get('/pipesense/summary')
    assert r_sum.status_code == 200
    assert r_sum.json['total_incidents'] >= 1
    assert r_sum.json['active_incidents'] >= 0
    # Avoided loss campus-wide includes resolved BLDG-04 incident (66,240 L/day)
    assert r_sum.json['verified_daily_loss_avoided_liters'] >= 66240.0

    r_imp = client.get('/pipesense/impact')
    assert r_imp.status_code == 200
    imp = r_imp.json
    assert imp['verified_daily_loss_avoided_liters'] == 66240.0
    assert imp['verified_post_repair_flow_lpm'] == 18.2
    assert imp['peak_abnormal_flow_lpm'] == 64.2
    assert imp['baseline_flow_lpm'] == 18.4
    assert imp['water_loss_reduction_lpm'] == 46.0

def test_work_order_completion_lifecycle_pending_until_verification(client):
    """
    Asserts that work-order completion stays PENDING and is NOT marked COMPLETED
    until physical telemetry verification passes.
    """
    client.post('/demo/pipesense/reset')
    r_det = client.post('/pipesense/detect', json={"zone": "BLDG-04", "current_flow": 64.2, "baseline_flow": 18.4})
    inc_id = r_det.json['incident_id']
    client.post(f'/pipesense/incidents/{inc_id}/investigate')
    wo = client.post(f'/pipesense/incidents/{inc_id}/dispatch').json
    wo_id = wo['work_order_id']

    # 1. State right after dispatch
    wo_data = client.get(f'/work-orders/{wo_id}').json
    assert wo_data['status'] == 'PENDING'
    assert wo_data.get('completed_at') is None

    # 2. State after technician completion claim: MUST NOT be COMPLETED
    client.post(f'/work-orders/{wo_id}/complete')
    wo_data = client.get(f'/work-orders/{wo_id}').json
    assert wo_data['status'] == 'PENDING', "Completion claim must not set status to COMPLETED"
    assert wo_data.get('completed_at') is None

    # 3. State after failed verification (61.8 L/min): MUST NOT be COMPLETED
    client.post(f'/work-orders/{wo_id}/verify', json={"telemetry": 61.8})
    wo_data = client.get(f'/work-orders/{wo_id}').json
    assert wo_data['status'] == 'IN_PROGRESS', "Failed verification must set status to IN_PROGRESS"
    assert wo_data.get('completed_at') is None

    # 4. State after re-dispatch & second completion claim: MUST NOT be COMPLETED
    client.post(f'/work-orders/{wo_id}/repair')
    client.post(f'/work-orders/{wo_id}/complete')
    wo_data = client.get(f'/work-orders/{wo_id}').json
    assert wo_data['status'] == 'PENDING'
    assert wo_data.get('completed_at') is None

    # 5. State after passing verification (18.2 L/min): MUST BE COMPLETED with timestamp
    client.post(f'/work-orders/{wo_id}/verify', json={"telemetry": 18.2})
    wo_data = client.get(f'/work-orders/{wo_id}').json
    assert wo_data['status'] == 'COMPLETED', "Work order must ONLY be COMPLETED after verification passes"
    assert wo_data.get('completed_at') is not None

def test_water_savings_calculations_with_distinct_pre_and_post_flows(client):
    """
    Asserts calculation of water savings keeping pre-repair flow (64.2 L/min)
    and post-repair flow (18.2 L/min) distinct, verifying avoided daily loss = 66,240 L/day.
    """
    client.post('/demo/pipesense/reset')
    r_det = client.post('/pipesense/detect', json={"zone": "BLDG-04", "current_flow": 64.2, "baseline_flow": 18.4})
    inc_id = r_det.json['incident_id']
    client.post(f'/pipesense/incidents/{inc_id}/investigate')
    wo = client.post(f'/pipesense/incidents/{inc_id}/dispatch').json
    wo_id = wo['work_order_id']
    client.post(f'/work-orders/{wo_id}/complete')

    # Step A: Failed verification at 61.8 L/min
    res_fail = client.post(f'/work-orders/{wo_id}/verify', json={"telemetry": 61.8}).json
    assert res_fail['state'] == 'OPEN'
    assert res_fail.get('post_repair_flow_lpm') is None

    imp_fail = client.get('/pipesense/impact').json
    assert imp_fail['verified_daily_loss_avoided_liters'] == 0.0
    assert imp_fail['verified_post_repair_flow_lpm'] is None
    assert imp_fail['water_loss_reduction_lpm'] == 0.0

    # Step B: Passing verification at 18.2 L/min
    client.post(f'/work-orders/{wo_id}/repair')
    client.post(f'/work-orders/{wo_id}/complete')
    res_pass = client.post(f'/work-orders/{wo_id}/verify', json={"telemetry": 18.2}).json

    assert res_pass['state'] == 'RESOLVED'
    assert res_pass['current_flow_lpm'] == 64.2  # Preserves abnormal peak flow
    assert res_pass['baseline_flow_lpm'] == 18.4
    assert res_pass['post_repair_flow_lpm'] == 18.2  # Real measured post-repair flow

    imp_pass = client.get('/pipesense/impact').json
    expected_avoided_daily = (64.2 - 18.2) * 1440.0  # 46.0 * 1440 = 66240.0
    assert imp_pass['verified_daily_loss_avoided_liters'] == expected_avoided_daily
    assert imp_pass['verified_post_repair_flow_lpm'] == 18.2
    assert imp_pass['peak_abnormal_flow_lpm'] == 64.2
    assert imp_pass['baseline_flow_lpm'] == 18.4
    assert imp_pass['water_loss_reduction_lpm'] == 46.0

    sum_pass = client.get('/pipesense/summary').json
    assert sum_pass['verified_daily_loss_avoided_liters'] >= expected_avoided_daily

