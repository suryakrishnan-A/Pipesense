from datetime import datetime
import uuid
import enum
from backend_v2.domain.sql_models import (
    Incident,
    WorkOrder,
    IncidentState,
    AuditLog,
    Severity,
    WorkOrderStatus,
    Site,
    VerificationRecord
)
from backend_v2.repository.topology_db import SessionLocal
from backend_v2.repository.db import db as in_memory_db
from backend_v2.agent.pipesense_agent import StrandsAgent

class PipeSenseServiceSQL:
    def __init__(self):
        self.agent = StrandsAgent()

    def get_agent_status(self):
        return self.agent.get_status()

    def detect_anomaly(self, zone: str, current_flow: float, baseline_flow: float):
        ratio = current_flow / baseline_flow if baseline_flow > 0 else 0
        if ratio <= 1.35:
            return None
            
        with SessionLocal() as db:
            site = db.query(Site).first()
            site_id = site.id if site else "campus-1"
            inc_id = f"INC-{int(datetime.now().timestamp())}"
            incident = Incident(
                id=inc_id,
                site_id=site_id,
                asset_id=zone,
                baseline_flow=baseline_flow,
                current_flow=current_flow,
                state=IncidentState.INVESTIGATING,
                severity=Severity.HIGH if ratio > 2.0 else Severity.MEDIUM,
                description=f"Abnormal flow detected: {current_flow} L/min ({ratio:.2f}x baseline)"
            )
            db.add(incident)
            
            audit = AuditLog(
                actor_id="SYSTEM",
                action="ANOMALY_DETECTED",
                target_type="INCIDENT",
                target_id=inc_id,
                details={
                    "zone": zone,
                    "current_flow": current_flow,
                    "baseline_flow": baseline_flow,
                    "ratio": round(ratio, 2),
                    "window": "01:00-05:00 IST sleep window"
                }
            )
            db.add(audit)
            db.commit()
            return self._to_dict(incident)

    def run_investigation(self, incident_id: str):
        with SessionLocal() as db:
            inc = db.query(Incident).filter_by(id=incident_id).first()
            if not inc:
                raise ValueError("Incident not found")
                
            inc.state = IncidentState.INVESTIGATING
            
            db.add(AuditLog(
                actor_id="LOCAL_AGENT",
                action="INVESTIGATION_STARTED",
                target_type="INCIDENT",
                target_id=incident_id,
                details={"zone": inc.asset_id, "mode": self.agent.mode}
            ))

            class FakeInc:
                zone = inc.asset_id
                current_flow_lpm = inc.current_flow
                baseline_flow_lpm = inc.baseline_flow
                
            result = self.agent.investigate(FakeInc())
            
            # Log tool calls to audit trail
            for tool_name, tool_output in result.get("tool_results", {}).items():
                db.add(AuditLog(
                    actor_id="LOCAL_AGENT",
                    action="TOOL_CALLED",
                    target_type="INCIDENT",
                    target_id=incident_id,
                    details={"tool_name": tool_name, "finding": tool_output.get("finding", ""), "result": tool_output}
                ))

            inc.hypothesis = result["diagnosis"]
            evidence_text = "\n".join(result["evidence"])
            
            if result["diagnosis"] == "LEAK_CONFIRMED":
                inc.state = IncidentState.WORK_ORDER_ISSUED
                inc.severity = Severity.HIGH
                inc.description += f"\n\nAgent Evidence:\n{evidence_text}\nConfidence: {result['confidence']}"
                db.add(AuditLog(
                    actor_id="LOCAL_AGENT",
                    action="LEAK_CONFIRMED",
                    target_type="INCIDENT",
                    target_id=incident_id,
                    details={
                        "verdict": "CONFIRMED_MAJOR_LEAK",
                        "confidence": result["confidence"],
                        "evidence": result["evidence"],
                        "probable_location": "Basement Secondary Riser"
                    }
                ))
            elif result["diagnosis"] == "LEGITIMATE_USAGE":
                inc.state = IncidentState.FALSE_ALARM
                inc.severity = Severity.LOW
                db.add(AuditLog(
                    actor_id="LOCAL_AGENT",
                    action="FALSE_ALARM_RESOLVED",
                    target_type="INCIDENT",
                    target_id=incident_id,
                    details={"confidence": result["confidence"], "verdict": "LEGITIMATE_USAGE"}
                ))
            else:
                inc.severity = Severity.MEDIUM
                db.add(AuditLog(
                    actor_id="LOCAL_AGENT",
                    action="LEAK_SUSPECTED",
                    target_type="INCIDENT",
                    target_id=incident_id,
                    details={"confidence": result["confidence"], "evidence": result["evidence"]}
                ))
                
            db.commit()
            return self._to_dict(inc)

    def dispatch_work_order(self, incident_id: str):
        with SessionLocal() as db:
            inc = db.query(Incident).filter_by(id=incident_id).first()
            if not inc:
                raise ValueError("Incident not found")
                
            wo_id = f"WO-{uuid.uuid4().hex[:6].upper()}"
            wo = WorkOrder(
                id=wo_id,
                incident_id=incident_id,
                status=WorkOrderStatus.PENDING,
                notes="Basement Secondary Riser - P1 Priority Dispatched to Senior Plumber"
            )
            db.add(wo)
            
            inc.state = IncidentState.WORK_ORDER_ISSUED
            inc.severity = Severity.CRITICAL
            
            db.add(AuditLog(
                actor_id="SYSTEM",
                action="WORK_ORDER_ISSUED",
                target_type="INCIDENT",
                target_id=incident_id,
                details={
                    "work_order_id": wo_id,
                    "assigned_role": "Senior Plumber",
                    "priority": "P1",
                    "location": "Basement Secondary Riser"
                }
            ))
            
            db.commit()
            return self._to_dict(wo)

    def claim_completion(self, wo_id: str):
        with SessionLocal() as db:
            wo = db.query(WorkOrder).filter_by(id=wo_id).first()
            if not wo:
                raise ValueError("Work order not found")
                
            inc = db.query(Incident).filter_by(id=wo.incident_id).first()
            # Work order completion remains PENDING until telemetry verification passes
            wo.status = WorkOrderStatus.PENDING
            wo.completed_at = None
            
            inc.state = IncidentState.REPAIR_VERIFICATION
            
            db.add(AuditLog(
                actor_id="TECHNICIAN",
                action="COMPLETION_CLAIMED",
                target_type="INCIDENT",
                target_id=wo.incident_id,
                details={
                    "work_order_id": wo_id,
                    "notes": "Field plumber reported repair complete (washer replacement claimed)",
                    "status": "AWAITING_TELEMETRY_VERIFICATION"
                }
            ))
            
            db.commit()
            return self._to_dict(inc)

    def verify_repair(self, wo_id: str, telemetry_reading: float):
        with SessionLocal() as db:
            wo = db.query(WorkOrder).filter_by(id=wo_id).first()
            if not wo:
                raise ValueError("Work order not found")
            inc = db.query(Incident).filter_by(id=wo.incident_id).first()
            if not inc:
                raise ValueError("Incident not found")
            
            passed = telemetry_reading <= (inc.baseline_flow * 1.35)
            
            v_rec = VerificationRecord(
                incident_id=inc.id,
                work_order_id=wo.id,
                passed=passed,
                post_repair_flow=telemetry_reading,
                notes="Verification Passed" if passed else "Verification Failed: leak flow still active"
            )
            db.add(v_rec)
            
            if not passed:
                inc.state = IncidentState.OPEN # Escalated
                inc.post_repair_flow = None
                wo.status = WorkOrderStatus.IN_PROGRESS
                wo.completed_at = None
                db.add(AuditLog(
                    actor_id="LOCAL_AGENT",
                    action="FAILED_VERIFICATION",
                    target_type="INCIDENT",
                    target_id=inc.id,
                    details={
                        "work_order_id": wo_id,
                        "observed_flow": telemetry_reading,
                        "baseline_flow": inc.baseline_flow,
                        "verdict": "VERIFICATION_REJECTED",
                        "status": "ESCALATED",
                        "message": f"Telemetry reads {telemetry_reading} L/min (baseline: {inc.baseline_flow} L/min). Physical flow confirms leak is still active."
                    }
                ))
            else:
                inc.state = IncidentState.RESOLVED
                inc.post_repair_flow = telemetry_reading
                wo.status = WorkOrderStatus.COMPLETED
                wo.completed_at = datetime.utcnow()
                db.add(AuditLog(
                    actor_id="LOCAL_AGENT",
                    action="VERIFIED_RESOLVED",
                    target_type="INCIDENT",
                    target_id=inc.id,
                    details={
                        "work_order_id": wo_id,
                        "observed_flow": telemetry_reading,
                        "baseline_flow": inc.baseline_flow,
                        "verdict": "VERIFIED_AND_CLOSED",
                        "status": "RESOLVED",
                        "message": f"Telemetry verified restored at {telemetry_reading} L/min. Incident officially closed."
                    }
                ))
                
            db.commit()
            return self._to_dict(inc)

    def start_second_repair(self, wo_id: str):
        with SessionLocal() as db:
            wo = db.query(WorkOrder).filter_by(id=wo_id).first()
            if not wo:
                raise ValueError("Work order not found")
            inc = db.query(Incident).filter_by(id=wo.incident_id).first()
            if not inc:
                raise ValueError("Incident not found")
            
            inc.state = IncidentState.WORK_ORDER_ISSUED
            wo.status = WorkOrderStatus.IN_PROGRESS
            wo.completed_at = None
            wo.notes = "Escalated to Senior Supervisor - Full 2-inch pipe replacement in progress"
            
            db.add(AuditLog(
                actor_id="SYSTEM",
                action="REPAIR_STARTED",
                target_type="INCIDENT",
                target_id=inc.id,
                details={
                    "work_order_id": wo_id,
                    "assigned_role": "Senior Supervisor",
                    "action": "Secondary physical repair initiated"
                }
            ))
            
            db.commit()
            return self._to_dict(inc)

    def reset_demo(self):
        """Resets the demo state in both SQL database and in-memory repository."""
        # 1. Reset in-memory DB
        in_memory_db.reset_demo_state()
        
        # 2. Reset SQL DB
        with SessionLocal() as db:
            # Delete dynamically created demo incidents (keep seeded mock ones)
            seeded_ids = {"INC-1002", "INC-1003", "INC-1004", "INC-1005", "INC-1006"}
            dynamic_incs = db.query(Incident).filter(~Incident.id.in_(seeded_ids)).all()
            for d_inc in dynamic_incs:
                # Remove related work orders, records, and logs
                db.query(VerificationRecord).filter_by(incident_id=d_inc.id).delete()
                db.query(WorkOrder).filter_by(incident_id=d_inc.id).delete()
                db.query(AuditLog).filter_by(target_id=d_inc.id).delete()
                db.delete(d_inc)
            
            # Reset seeded mock incidents to their exact initial state
            inc_states = {
                "INC-1002": (IncidentState.INVESTIGATING, 35.0, 15.0, Severity.MEDIUM),
                "INC-1003": (IncidentState.WORK_ORDER_ISSUED, 64.2, 18.4, Severity.HIGH),
                "INC-1004": (IncidentState.CLOSED, 6.2, 5.0, Severity.LOW),
                "INC-1005": (IncidentState.INVESTIGATING, 13.0, 12.0, Severity.LOW),
                "INC-1006": (IncidentState.WORK_ORDER_ISSUED, 38.0, 18.0, Severity.HIGH),
            }
            for i_id, (st, cur, base, sev) in inc_states.items():
                m_inc = db.query(Incident).filter_by(id=i_id).first()
                if m_inc:
                    m_inc.state = st
                    m_inc.current_flow = cur
                    m_inc.baseline_flow = base
                    m_inc.post_repair_flow = None
                    m_inc.severity = sev
                    db.query(WorkOrder).filter_by(incident_id=i_id).delete()
                    db.query(AuditLog).filter_by(target_id=i_id).delete()
                    db.query(VerificationRecord).filter_by(incident_id=i_id).delete()

            # Clean up any test nodes added by topology tests
            from backend_v2.domain.sql_models import PipelineNode
            db.query(PipelineNode).filter(PipelineNode.name == "TEST-NODE").delete()
            
            db.commit()
        return {"message": "Demo reset complete."}

    def get_summary(self):
        with SessionLocal() as db:
            incidents = db.query(Incident).all()
            active_count = len([i for i in incidents if i.state not in [IncidentState.CLOSED, IncidentState.RESOLVED]])
            total_count = len(incidents)
            resolved_count = len([i for i in incidents if i.state in [IncidentState.CLOSED, IncidentState.RESOLVED]])
            
            daily_loss = sum([
                (i.current_flow - i.baseline_flow) * 1440
                for i in incidents
                if i.current_flow and i.baseline_flow and (i.current_flow > i.baseline_flow)
            ])
            
            avoided_loss = 0.0
            for i in incidents:
                if i.state in [IncidentState.CLOSED, IncidentState.RESOLVED] and i.current_flow:
                    post_flow = i.post_repair_flow
                    if post_flow is None:
                        v_rec = db.query(VerificationRecord).filter_by(incident_id=i.id, passed=True).order_by(VerificationRecord.timestamp.desc()).first()
                        if v_rec and v_rec.post_repair_flow is not None:
                            post_flow = v_rec.post_repair_flow
                    if post_flow is not None and i.current_flow > post_flow:
                        avoided_loss += (i.current_flow - post_flow) * 1440.0
                    elif i.baseline_flow and i.current_flow > i.baseline_flow:
                        avoided_loss += (i.current_flow - i.baseline_flow) * 1440.0
            
            return {
                "total_zones": 14,
                "total_incidents": total_count,
                "active_incidents": active_count,
                "critical_incidents": len([i for i in incidents if i.severity == Severity.CRITICAL]),
                "resolved_today": resolved_count,
                "estimated_daily_loss_liters": daily_loss,
                "verified_daily_loss_avoided_liters": avoided_loss,
                "average_confidence": 0.94
            }
            
    def _to_dict(self, obj):
        # Helper to safely serialize SQLAlchemy objects for jsonify
        d = {}
        for c in obj.__table__.columns:
            val = getattr(obj, c.name)
            if isinstance(val, enum.Enum):
                val = val.value
            elif isinstance(val, datetime):
                val = val.isoformat()
            d[c.name] = val
        # To maintain compatibility with existing PipeSense frontend which expects certain fields:
        if isinstance(obj, Incident):
            d["incident_id"] = d.pop("id")
            d["zone"] = d.pop("asset_id")
            d["baseline_flow_lpm"] = d.pop("baseline_flow")
            d["current_flow_lpm"] = d.pop("current_flow")
            d["post_repair_flow_lpm"] = d.get("post_repair_flow")
        elif isinstance(obj, WorkOrder):
            d["work_order_id"] = d.pop("id")
        elif isinstance(obj, AuditLog):
            d["event_type"] = d.get("action", "")
            d["incident_id"] = d.get("target_id")
            if isinstance(d.get("details"), dict) and "work_order_id" in d["details"]:
                d["work_order_id"] = d["details"]["work_order_id"]
        return d

