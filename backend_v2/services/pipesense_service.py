from datetime import datetime
import uuid
from backend_v2.domain.models import Incident, WorkOrder, IncidentState, Event, AuditLog
from backend_v2.repository.db import db
from backend_v2.agent.pipesense_agent import StrandsAgent

class PipeSenseService:
    def detect_anomaly(self, zone: str, current_flow: float, baseline_flow: float):
        # Deterministic check: only transition to anomaly if flow > 1.35x
        ratio = current_flow / baseline_flow if baseline_flow > 0 else 0
        if ratio <= 1.35:
            # Not an anomaly
            return None
            
        inc_id = f"INC-{int(datetime.now().timestamp())}"
        incident = Incident(
            incident_id=inc_id,
            zone=zone,
            baseline_flow_lpm=baseline_flow,
            current_flow_lpm=current_flow,
            state=IncidentState.ANOMALY,
            description=f"Abnormal flow detected: {current_flow} L/min ({ratio:.2f}x baseline)"
        )
        db.save_incident(incident)
        
        db.add_event(Event(event_type="INCIDENT_CREATED", incident_id=inc_id))
        db.add_event(Event(event_type="ANOMALY_DETECTED", incident_id=inc_id))
        return incident

    def run_investigation(self, incident_id: str):
        inc = db.get_incident(incident_id)
        if not inc or inc.state != IncidentState.ANOMALY:
            raise ValueError("Invalid state transition")
            
        inc.state = IncidentState.INVESTIGATING
        db.add_event(Event(event_type="INVESTIGATION_STARTED", incident_id=incident_id))
        
        agent = StrandsAgent()
        
        # Tools called
        db.add_event(Event(event_type="TOOL_CALLED", incident_id=incident_id, details={"tool_name": "check_weather"}))
        db.add_event(Event(event_type="TOOL_CALLED", incident_id=incident_id, details={"tool_name": "check_peer_baselines"}))
        db.add_event(Event(event_type="TOOL_CALLED", incident_id=incident_id, details={"tool_name": "check_maintenance_history"}))
        db.add_event(Event(event_type="TOOL_CALLED", incident_id=incident_id, details={"tool_name": "check_occupancy"}))
        
        result = agent.investigate(inc)
        
        inc.confidence = result["confidence"]
        inc.diagnosis = result["diagnosis"]
        inc.metadata["agent_evidence"] = result["evidence"]
        
        if result["diagnosis"] == "LEAK_CONFIRMED":
            inc.state = IncidentState.LEAK_CONFIRMED
            # IMPACT PRE-REPAIR
            estimated_daily_loss = (inc.current_flow_lpm - inc.baseline_flow_lpm) * 1440
            inc.metadata["estimated_daily_loss_liters"] = estimated_daily_loss
            db.add_event(Event(event_type="LEAK_CONFIRMED", incident_id=incident_id))
            db.add_audit(AuditLog(actor="AGENT", action="CONFIRM_LEAK", incident_id=incident_id, old_state="INVESTIGATING", new_state="LEAK_CONFIRMED", reason="Evidence strongly points to leak"))
        else:
            inc.state = IncidentState.NOMINAL if result["diagnosis"] == "LEGITIMATE_USAGE" else IncidentState.LEAK_SUSPECTED
            
        db.save_incident(inc)
        return inc

    def dispatch_work_order(self, incident_id: str):
        inc = db.get_incident(incident_id)
        if not inc or inc.state != IncidentState.LEAK_CONFIRMED:
            raise ValueError("Invalid state transition")
            
        wo_id = f"WO-{uuid.uuid4().hex[:6].upper()}"
        wo = WorkOrder(
            work_order_id=wo_id,
            incident_id=incident_id,
            priority="P1",
            assigned_role="Senior Plumber",
            assigned_person="On-call Senior Plumber",
            zone=inc.zone,
            description="Basement Secondary Riser",
            status="ASSIGNED"
        )
        db.save_work_order(wo)
        
        inc.state = IncidentState.WORK_ORDER_ISSUED
        inc.priority = "P1"
        inc.severity = "HIGH"
        db.save_incident(inc)
        
        db.add_event(Event(event_type="WORK_ORDER_CREATED", incident_id=incident_id, work_order_id=wo_id))
        db.add_event(Event(event_type="NOTIFICATION_CREATED", incident_id=incident_id, details={"message": "URGENT P1 WATER LEAK"}))
        return wo

    def claim_completion(self, wo_id: str):
        wo = db.get_work_order(wo_id)
        if not wo:
            raise ValueError("Work order not found")
            
        inc = db.get_incident(wo.incident_id)
        if inc.state not in [IncidentState.WORK_ORDER_ISSUED, IncidentState.REPAIRING]:
            raise ValueError("Invalid state transition")
            
        wo.status = "COMPLETION_CLAIMED"
        wo.completion_claimed_at = datetime.now().isoformat()
        db.save_work_order(wo)
        
        inc.state = IncidentState.VERIFYING
        db.save_incident(inc)
        
        actor = "TECHNICIAN" if wo.assigned_role == "Senior Plumber" else "SUPERVISOR"
        db.add_event(Event(event_type="REPAIR_COMPLETION_CLAIMED", incident_id=inc.incident_id, work_order_id=wo_id))
        db.add_audit(AuditLog(actor=actor, action="CLAIM_COMPLETION", incident_id=inc.incident_id, work_order_id=wo_id, new_state="VERIFYING"))
        db.add_event(Event(event_type="VERIFICATION_STARTED", incident_id=inc.incident_id))
        return inc

    def verify_repair(self, wo_id: str, telemetry_reading: float):
        wo = db.get_work_order(wo_id)
        inc = db.get_incident(wo.incident_id)
        
        if inc.state != IncidentState.VERIFYING:
            raise ValueError("Incident not in VERIFYING state")
            
        passed = telemetry_reading <= (inc.baseline_flow_lpm * 1.35)
        
        if not passed:
            inc.state = IncidentState.FAILED_VERIFICATION
            wo.verification_status = "FAILED"
            wo.status = "FAILED_VERIFICATION"
            reason = "Flow remains significantly above baseline."
            db.add_event(Event(event_type="VERIFICATION_FAILED", incident_id=inc.incident_id, details={"reading": telemetry_reading, "reason": reason}))
            
            # Escalate
            inc.state = IncidentState.ESCALATED
            wo.assigned_role = "Senior Supervisor"
            wo.status = "ESCALATED"
            db.add_event(Event(event_type="INCIDENT_ESCALATED", incident_id=inc.incident_id))
        else:
            inc.state = IncidentState.RESOLVED
            wo.verification_status = "PASSED"
            wo.status = "VERIFIED"
            reason = "Flow returned to baseline range."
            db.add_event(Event(event_type="VERIFICATION_PASSED", incident_id=inc.incident_id, details={"reading": telemetry_reading, "reason": reason}))
            db.add_event(Event(event_type="INCIDENT_RESOLVED", incident_id=inc.incident_id))
            
            # Close
            inc.state = IncidentState.CLOSED
            wo.status = "CLOSED"
            db.add_event(Event(event_type="INCIDENT_CLOSED", incident_id=inc.incident_id))
            
            # Impact POST-REPAIR
            avoided = (inc.current_flow_lpm - telemetry_reading) * 1440
            inc.metadata["verified_daily_loss_avoided_liters"] = avoided
            inc.metadata["verified_post_repair_flow_lpm"] = telemetry_reading
            db.add_event(Event(event_type="IMPACT_RECORDED", incident_id=inc.incident_id, details={"avoided_lpd": avoided}))
            
        db.save_incident(inc)
        db.save_work_order(wo)
        db.add_audit(AuditLog(actor="SYSTEM", action="VERIFY_TELEMETRY", incident_id=inc.incident_id, work_order_id=wo_id, reason=reason))
        return inc

    def start_second_repair(self, wo_id: str):
        wo = db.get_work_order(wo_id)
        inc = db.get_incident(wo.incident_id)
        if inc.state != IncidentState.ESCALATED:
            raise ValueError("Incident must be ESCALATED to start second repair")
            
        inc.state = IncidentState.REPAIRING
        wo.status = "IN_PROGRESS"
        db.save_incident(inc)
        db.save_work_order(wo)
        db.add_event(Event(event_type="REPAIR_STARTED", incident_id=inc.incident_id))
        return inc

    def get_summary(self):
        incidents = list(db.incidents.values())
        return {
            "total_zones": 14,
            "active_incidents": len([i for i in incidents if i.state not in [IncidentState.CLOSED, IncidentState.NOMINAL]]),
            "critical_incidents": len([i for i in incidents if i.severity == "HIGH" and i.state != IncidentState.CLOSED]),
            "resolved_today": len([i for i in incidents if i.state == IncidentState.CLOSED]),
            "estimated_daily_loss_liters": sum([i.metadata.get("estimated_daily_loss_liters", 0) for i in incidents]),
            "verified_daily_loss_avoided_liters": sum([i.metadata.get("verified_daily_loss_avoided_liters", 0) for i in incidents])
        }
