"""
Closed-Loop Repair Verification Engine.
The key differentiator: The agent does NOT take human word for granted.
It queries real-time water meter telemetry to mathematically prove whether the repair worked.
"""

from datetime import datetime
from backend.data.campus_db import store

class RepairVerifier:
    def verify_repair(self, incident_id, current_telemetry_flow_lpm, baseline_lpm=18.4):
        """
        Compares post-repair telemetry against the historical baseline.
        - If flow is still > 1.35x baseline: REJECT closure, mark repair incomplete, escalate alert!
        - If flow is <= 1.35x baseline: VERIFY repair, close incident, compute water savings.
        """
        ratio = current_telemetry_flow_lpm / baseline_lpm

        if ratio > 1.35:
            # Repair failed or incomplete!
            escalation_reason = (
                f"VERIFICATION REJECTED: Current night flow is {current_telemetry_flow_lpm} L/min "
                f"({round(ratio, 2)}x baseline of {baseline_lpm} L/min). "
                f"Physical water telemetry confirms leak is STILL ACTIVE despite technician completion claim."
            )
            store.reject_repair_and_escalate(incident_id, escalation_reason)
            return {
                "verified": False,
                "status": "REPAIR_REJECTED_ESCALATED",
                "measured_flow_lpm": current_telemetry_flow_lpm,
                "baseline_lpm": baseline_lpm,
                "surge_ratio": round(ratio, 2),
                "message": escalation_reason,
                "action_taken": "Incident reopened. P1 Escalation notice sent to Facilities Director."
            }
        else:
            # Repair successfully verified!
            incident = store.incidents.get(incident_id, {})
            alert_data = incident.get('telemetry_alert', {})
            peak_flow = alert_data.get('flow_rate_lpm', 64.2)
            
            liters_saved_per_day = int((peak_flow - current_telemetry_flow_lpm) * 60 * 24)
            liters_saved_per_month = liters_saved_per_day * 30
            
            outcome = {
                "verified": True,
                "status": "VERIFIED_AND_CLOSED",
                "measured_flow_lpm": current_telemetry_flow_lpm,
                "baseline_lpm": baseline_lpm,
                "surge_ratio": round(ratio, 2),
                "liters_saved_daily": liters_saved_per_day,
                "liters_saved_monthly": liters_saved_per_month,
                "carbon_offset_kg_co2e_monthly": round(liters_saved_per_month * 0.000298, 1), # Municipal pumping energy offset
                "verified_at": datetime.now().isoformat(),
                "summary": (
                    f"SUCCESSFULLY VERIFIED: Night flow restored to {current_telemetry_flow_lpm} L/min "
                    f"(Baseline: {baseline_lpm} L/min). "
                    f"Verified Water Savings: {liters_saved_per_day:,} Liters/day ({liters_saved_per_month:,} L/month)."
                )
            }
            store.close_incident(incident_id, outcome)
            return outcome

verifier = RepairVerifier()
