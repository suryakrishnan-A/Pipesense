"""
End-to-End Closed-Loop Verification Test.
Asserts the full closed-loop transitions and calculated metrics:
DETECT -> INVESTIGATE (4 TOOLS) -> DISPATCH -> VERIFY (REJECT BAD FIX) -> VERIFY (CONFIRM GOOD FIX) -> MEASURE IMPACT
Note: This build executes the local deterministic resilience agent by default; zero AWS calls made.
"""

import sys
import os
import time
import io

# Force UTF-8 on Windows stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.data.campus_db import store
from backend.agent.bedrock_agent import BedrockResilienceAgent
from backend.engine.dispatcher import dispatcher
from backend.engine.verifier import verifier

def print_banner(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

def run_hackathon_demo():
    print_banner("PIPESENSE: CLOSED-LOOP RESILIENCE ENGINE VERIFICATION")
    print("Mode: Local Deterministic Agent (Zero AWS calls made)")

    # 1. Anomaly Trigger
    print_banner("STEP 1: ANOMALY DETECTED (METER TELEMETRY)")
    telemetry_alert = {
        "building_id": "BLDG-04",
        "building_name": "Satish Dhawan Hostel & Lab Block",
        "flow_rate_lpm": 64.2,
        "baseline_lpm": 18.4,
        "timestamp": "02:45:00 IST",
        "spike_multiplier": 3.49
    }
    print(f"⏰ Timestamp: {telemetry_alert['timestamp']}")
    print(f"🏢 Building:  {telemetry_alert['building_name']} ({telemetry_alert['building_id']})")
    print(f"🚨 Observed Flow: {telemetry_alert['flow_rate_lpm']} L/min (Baseline: {telemetry_alert['baseline_lpm']} L/min)")
    print(f"⚡ Alert: Night flow exceeds 2x threshold (Current: 3.49x baseline). Triggering AI Agent!")

    incident = store.create_incident(
        incident_type="WATER_LEAK_SURGE",
        building_id="BLDG-04",
        title="Critical Night Flow Surge in Satish Dhawan Block",
        details=f"Flow sustained at {telemetry_alert['flow_rate_lpm']} L/min during 01:00-05:00 sleep window."
    )
    store.incidents[incident['incident_id']]['telemetry_alert'] = telemetry_alert
    print(f"📋 Incident Record Created: {incident['incident_id']}")

    # State Assertions - Incident Creation
    assert incident['incident_id'].startswith("INC-"), "Incident ID must start with INC-"
    assert incident['status'] == "INVESTIGATING", "Initial status must be INVESTIGATING"
    assert incident['building_id'] == "BLDG-04"

    # 2. Agent Investigation
    print_banner("STEP 2: LOCAL RESILIENCE AGENT INVESTIGATION (TOOL REASONING)")
    print("🤖 Agent initiating autonomous multi-tool context gathering...")
    agent = BedrockResilienceAgent()
    diagnosis = agent.run_investigation(incident['incident_id'], telemetry_alert)

    inv_log = store.incidents[incident['incident_id']]['investigation_log']
    for i, step in enumerate(inv_log):
        print(f"\n  [Tool Call {i+1}] {step['tool']}()")
        print(f"   Reasoning: {step['reasoning']}")
        print(f"   Output:    {step['result']['analysis']}")

    # State & Metric Assertions - Investigation
    assert len(inv_log) == 4, f"Expected 4 tool calls, got {len(inv_log)}"
    executed_tools = [step['tool'] for step in inv_log]
    assert executed_tools == ['check_weather', 'check_peer_baselines', 'check_maintenance_history', 'check_occupancy']
    assert diagnosis['verdict'] == "CONFIRMED_MAJOR_LEAK"
    assert diagnosis['recommended_priority'] == "P1_URGENT"
    assert diagnosis['confidence_score'] == 0.98
    assert diagnosis['probable_location'] == "Basement Riser & Sump Pump Line B"
    assert diagnosis['estimated_water_loss_rate_lpm'] == 45.8  # 64.2 - 18.4
    assert diagnosis['estimated_daily_waste_liters'] == 65952  # 45.8 * 1440

    print("\n💡 AGENT SYNTHESIS & DIAGNOSIS:")
    print(f"   Verdict:           {diagnosis['verdict']}")
    print(f"   Confidence:        {diagnosis['confidence_score'] * 100}%")
    print(f"   Probable Location: {diagnosis['probable_location']}")
    print(f"   Wasted Volume:     {diagnosis['estimated_daily_waste_liters']:,} Liters/day")

    # 3. Dispatch
    print_banner("STEP 3: WORK ORDER DISPATCH & CREW NOTIFICATION")
    dispatch_res = dispatcher.dispatch_leak_repair(incident['incident_id'], diagnosis)
    wo = dispatch_res["work_order"]
    notif = dispatch_res["notification"]
    print(f"🛠️ Work Order ID: {wo['work_order_id']} ({wo['priority']})")
    print(f"👤 Assigned To:   {wo['assigned_to']['name']} ({wo['assigned_to']['role']})")
    print(f"📱 Dispatch SMS:  \"{notif['message']}\"")

    # State Assertions - Work Order Dispatch
    assert wo['work_order_id'].startswith("WO-"), "Work Order ID must start with WO-"
    assert wo['status'] == "DISPATCHED", "Initial work order status must be DISPATCHED"
    assert wo['status'] != "COMPLETED", "Work order must not be COMPLETED upon dispatch"
    assert store.incidents[incident['incident_id']]['status'] == "DISPATCHED"
    assert store.incidents[incident['incident_id']]['work_order_id'] == wo['work_order_id']

    # 4. Bad Repair Simulation (Agent catches it and rejects completion!)
    print_banner("STEP 4: VERIFICATION - TECHNICIAN REPORTS REPAIR COMPLETE")
    print("👷 Plumber marks work order COMPLETE: 'Replaced rubber washer on secondary outlet.'")
    store.update_work_order_status(wo['work_order_id'], "COMPLETION_REPORTED", "Replaced rubber washer on secondary outlet.")

    # State Assertion - Premature claim must NOT complete the work order
    assert store.work_orders[wo['work_order_id']]['status'] == "COMPLETION_REPORTED"
    assert store.work_orders[wo['work_order_id']]['status'] != "COMPLETED", "Work order must remain pending verification!"
    
    print("\n🔍 Agent autonomously queries post-repair telemetry...")
    bad_repair_flow = 61.8  # Still leaking!
    print(f"📊 Telemetry Readout: {bad_repair_flow} L/min (Expected: ~18.4 L/min)")
    verif_1 = verifier.verify_repair(incident['incident_id'], bad_repair_flow)
    print(f"❌ RESULT: {verif_1['status']}")
    print(f"⚠️ Agent Verdict: {verif_1['message']}")
    print(f"📢 Escalation Triggered: Reopening case, summoning senior supervisor.")

    # State & Calculation Assertions - Rejection
    assert verif_1['verified'] is False, "Verification must fail for 61.8 L/min"
    assert verif_1['status'] == "REPAIR_REJECTED_ESCALATED"
    assert verif_1['measured_flow_lpm'] == 61.8
    assert verif_1['baseline_lpm'] == 18.4
    assert verif_1['surge_ratio'] == round(61.8 / 18.4, 2)
    assert store.incidents[incident['incident_id']]['status'] == "VERIFICATION_FAILED_ESCALATED"
    assert store.work_orders[wo['work_order_id']]['status'] == "IN_PROGRESS", "Work order must revert to IN_PROGRESS upon rejection"
    assert store.work_orders[wo['work_order_id']]['status'] != "COMPLETED", "Work order must not be COMPLETED on failed verification"

    # 5. Good Repair Simulation
    print_banner("STEP 5: RE-INSPECTION & SUCCESSFUL VERIFIED OUTCOME")
    print("👷 Senior supervisor replaces cracked 2-inch GI pipe section & pressure tests.")
    good_repair_flow = 18.2  # Restored to normal!
    print(f"📊 Telemetry Readout: {good_repair_flow} L/min (Baseline: 18.4 L/min)")
    verif_2 = verifier.verify_repair(incident['incident_id'], good_repair_flow)
    print(f"✅ RESULT: {verif_2['status']}")
    print(f"🎉 Agent Verdict: {verif_2['summary']}")
    print(f"🌍 MEASURED IMPACT: {verif_2['liters_saved_daily']:,} Liters/day saved! ({verif_2['liters_saved_monthly']:,} L/month)")
    print(f"🌱 Carbon Offset:   {verif_2['carbon_offset_kg_co2e_monthly']} kg CO2e / month")

    # State & Metric Assertions - Successful Verification & Impact
    assert verif_2['verified'] is True, "Verification must pass for 18.2 L/min"
    assert verif_2['status'] == "VERIFIED_AND_CLOSED"
    assert verif_2['measured_flow_lpm'] == 18.2
    assert verif_2['surge_ratio'] == round(18.2 / 18.4, 2)
    expected_daily_savings = int((64.2 - 18.2) * 60 * 24)  # 46.0 * 1440 = 66,240
    assert verif_2['liters_saved_daily'] == 66240, f"Expected 66240 L/day, got {verif_2['liters_saved_daily']}"
    assert verif_2['liters_saved_monthly'] == 66240 * 30, f"Expected 1987200 L/month, got {verif_2['liters_saved_monthly']}"
    assert verif_2['carbon_offset_kg_co2e_monthly'] == round(1987200 * 0.000298, 1)

    # Database Final State Assertions
    assert store.incidents[incident['incident_id']]['status'] == "RESOLVED_VERIFIED"
    assert store.work_orders[wo['work_order_id']]['status'] == "COMPLETED", "Work order must ONLY be COMPLETED after verification passes"
    assert store.work_orders[wo['work_order_id']]['verification_status'] == "PASSED"

    print_banner("DEMO COMPLETE: 100% CLOSED-LOOP VERIFIED RESILIENCE (ALL ASSERTIONS PASSED)")
    return True

if __name__ == "__main__":
    success = run_hackathon_demo()
    print("\nClosed-loop test completed successfully with all assertions verified.")
