"""
DrainPilot Service for Drainage Monitoring & Incident Response.

Implements deterministic anomaly detection, multi-threshold evaluation,
input validation, and autonomous investigation for campus drainage networks.
Reuses existing Incident, Event, AuditLog, and Database domain infrastructure.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid

from backend_v2.domain.models import Incident, IncidentState, Event, AuditLog, WorkOrder
from backend_v2.repository.db import db
from backend_v2.agent.drainpilot_agent import DrainPilotAgent

class DrainPilotService:
    """
    Manages drainage telemetry validation, anomaly detection, threshold monitoring,
    work-order dispatch, and resolution verification.
    """

    def __init__(
        self,
        warning_fill_ratio: float = 0.65,
        critical_fill_ratio: float = 0.85,
        rapid_rise_threshold_cm_hr: float = 15.0,
        overflow_margin_cm: float = 15.0,
        safe_fill_ratio: float = 0.45,
        safe_freeboard_cm: float = 30.0,
        safe_rate_of_rise_cm_hr: float = 5.0
    ):
        # Explainable, configurable operational thresholds
        self.warning_fill_ratio = warning_fill_ratio
        self.critical_fill_ratio = critical_fill_ratio
        self.rapid_rise_threshold_cm_hr = rapid_rise_threshold_cm_hr
        self.overflow_margin_cm = overflow_margin_cm
        self.safe_fill_ratio = safe_fill_ratio
        self.safe_freeboard_cm = safe_freeboard_cm
        self.safe_rate_of_rise_cm_hr = safe_rate_of_rise_cm_hr
        self.abnormal_pump_states = ("TRIPPED", "ALERT_OVERHEAT", "FAILED", "FAULT")

    def validate_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates drainage chamber telemetry.
        Handles missing optional readings and prevents invalid arithmetic.
        """
        if not isinstance(telemetry, dict):
            raise ValueError("Telemetry payload must be a dictionary")

        zone = telemetry.get("zone")
        if not zone or not isinstance(zone, str) or not zone.strip():
            raise ValueError("Telemetry requires a non-empty 'zone' string")

        if "chamber_depth_cm" not in telemetry or telemetry["chamber_depth_cm"] is None:
            raise ValueError("Telemetry requires 'chamber_depth_cm'")
        
        try:
            chamber_depth_cm = float(telemetry["chamber_depth_cm"])
        except (ValueError, TypeError):
            raise ValueError("'chamber_depth_cm' must be a valid number")

        if chamber_depth_cm <= 0:
            raise ValueError("'chamber_depth_cm' must be greater than zero")

        if "water_level_cm" not in telemetry or telemetry["water_level_cm"] is None:
            raise ValueError("Telemetry requires 'water_level_cm'")

        try:
            water_level_cm = float(telemetry["water_level_cm"])
        except (ValueError, TypeError):
            raise ValueError("'water_level_cm' must be a valid number")

        if water_level_cm < 0:
            raise ValueError("'water_level_cm' cannot be negative")

        # Optional fields with safe defaults
        baseline_level_cm = 0.0
        if telemetry.get("baseline_water_level_cm") is not None:
            try:
                baseline_level_cm = max(0.0, float(telemetry["baseline_water_level_cm"]))
            except (ValueError, TypeError):
                pass

        rate_of_rise_cm_per_hr = 0.0
        if telemetry.get("rate_of_rise_cm_per_hr") is not None:
            try:
                rate_of_rise_cm_per_hr = float(telemetry["rate_of_rise_cm_per_hr"])
            except (ValueError, TypeError):
                pass

        pump_status = str(telemetry.get("pump_status", "OFF")).upper().strip()

        return {
            "zone": zone.strip(),
            "chamber_depth_cm": chamber_depth_cm,
            "water_level_cm": water_level_cm,
            "baseline_water_level_cm": baseline_level_cm,
            "rate_of_rise_cm_per_hr": rate_of_rise_cm_per_hr,
            "pump_status": pump_status,
            "timestamp": telemetry.get("timestamp", datetime.now().isoformat())
        }

    def detect_anomaly(self, raw_telemetry: Dict[str, Any]) -> Optional[Incident]:
        """
        Evaluates drainage telemetry against operational thresholds:
        - Abnormally high chamber water levels (warning / critical fill ratio)
        - Rapid water-level rises (rate of rise >= threshold)
        - Overflow risk (freeboard <= overflow margin)
        - Abnormal pump activity (tripped / failed / running during rising level)

        Returns an Incident with system="DRAIN" if an anomaly is detected,
        or None if all metrics remain nominal.
        """
        telemetry = self.validate_telemetry(raw_telemetry)

        chamber_depth = telemetry["chamber_depth_cm"]
        water_level = telemetry["water_level_cm"]
        rate_of_rise = telemetry["rate_of_rise_cm_per_hr"]
        pump_status = telemetry["pump_status"]

        fill_ratio = round(water_level / chamber_depth, 3)
        freeboard_cm = max(0.0, round(chamber_depth - water_level, 2))

        # 1. Evaluate triggers
        is_overflow_risk = (freeboard_cm <= self.overflow_margin_cm) or (fill_ratio >= self.critical_fill_ratio)
        is_high_water_level = fill_ratio >= self.warning_fill_ratio
        is_rapid_rise = rate_of_rise >= self.rapid_rise_threshold_cm_hr
        is_pump_abnormal = (
            pump_status in self.abnormal_pump_states or
            (pump_status == "RUNNING" and is_rapid_rise and is_high_water_level)
        )

        # 2. Check if all conditions are nominal
        if not (is_overflow_risk or is_high_water_level or is_rapid_rise or is_pump_abnormal):
            return None

        # 3. Determine incident severity and priority
        reasons = []
        if is_overflow_risk:
            reasons.append(f"Critical overflow risk: freeboard {freeboard_cm} cm (fill ratio {fill_ratio * 100:.1f}%)")
        if is_high_water_level:
            reasons.append(f"High chamber level: {water_level} cm / {chamber_depth} cm ({fill_ratio * 100:.1f}%)")
        if is_rapid_rise:
            reasons.append(f"Rapid water-level surge: +{rate_of_rise:.1f} cm/hr")
        if is_pump_abnormal:
            reasons.append(f"Abnormal drainage pump condition: {pump_status}")

        if is_overflow_risk:
            severity = "CRITICAL"
            priority = "P1"
        elif is_rapid_rise or is_pump_abnormal or fill_ratio >= 0.75:
            severity = "HIGH"
            priority = "P2"
        else:
            severity = "MEDIUM"
            priority = "P3"

        # 4. Construct Incident
        # Flow fields are preserved as 0.0 because flow rates (L/min) are physically
        # incompatible with chamber level depths (cm). Drainage telemetry is kept in metadata.
        inc_id = f"INC-DRN-{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:4].upper()}"
        
        metadata = {
            "water_level_cm": water_level,
            "chamber_depth_cm": chamber_depth,
            "baseline_water_level_cm": telemetry["baseline_water_level_cm"],
            "fill_ratio": fill_ratio,
            "freeboard_cm": freeboard_cm,
            "rate_of_rise_cm_per_hr": rate_of_rise,
            "pump_status": pump_status,
            "overflow_risk_flag": is_overflow_risk,
            "rapid_rise_flag": is_rapid_rise,
            "high_level_flag": is_high_water_level,
            "pump_abnormal_flag": is_pump_abnormal,
            "detection_reasons": reasons,
            "data_origin": "SIMULATED_BENCHMARK_TELEMETRY",
            "sensor_disclaimer": "Simulated operational data for evaluation. Physical hardware sensors are not connected."
        }

        incident = Incident(
            incident_id=inc_id,
            zone=telemetry["zone"],
            baseline_flow_lpm=0.0,
            current_flow_lpm=0.0,
            system="DRAIN",
            state=IncidentState.ANOMALY,
            severity=severity,
            priority=priority,
            description="; ".join(reasons),
            metadata=metadata
        )

        db.save_incident(incident)
        db.add_event(Event(
            event_type="INCIDENT_CREATED",
            incident_id=inc_id,
            details={"system": "DRAIN", "zone": telemetry["zone"]}
        ))
        db.add_event(Event(
            event_type="DRAIN_ANOMALY_DETECTED",
            incident_id=inc_id,
            details={"severity": severity, "reasons": reasons, "fill_ratio": fill_ratio}
        ))

        return incident

    def run_investigation(self, incident_id: str) -> Incident:
        """
        Executes autonomous agent investigation on an existing drainage anomaly:
        1. Validates that the incident exists and is in ANOMALY state.
        2. Transitions state to INVESTIGATING.
        3. Queries the 4 drainage context tools via DrainPilotAgent.
        4. Synthesizes findings and updates incident diagnosis and evidence.
        """
        inc = db.get_incident(incident_id)
        if not inc:
            raise ValueError(f"Incident {incident_id} not found")

        if inc.system != "DRAIN":
            raise ValueError(f"Incident {incident_id} belongs to system '{inc.system}', not 'DRAIN'")

        if inc.state != IncidentState.ANOMALY:
            raise ValueError(f"Invalid state transition: incident must be in ANOMALY state (current: {inc.state})")

        inc.state = IncidentState.INVESTIGATING
        db.add_event(Event(event_type="INVESTIGATION_STARTED", incident_id=incident_id))

        # Record tool invocation audit events
        for tool_name in [
            "check_catchment_rainfall",
            "check_downstream_capacity",
            "check_siltation_history",
            "check_surface_debris"
        ]:
            db.add_event(Event(
                event_type="TOOL_CALLED",
                incident_id=incident_id,
                details={"tool_name": tool_name}
            ))

        agent = DrainPilotAgent()
        result = agent.investigate(inc)

        inc.confidence = result["confidence"]
        inc.diagnosis = result["suspected_problem"]
        inc.metadata["agent_evidence"] = result["evidence"]
        inc.metadata["agent_finding"] = result["finding"]
        inc.metadata["recommended_action"] = result["recommended_action"]
        inc.metadata["confidence_type"] = result["confidence_type"]
        inc.metadata["confidence_disclaimer"] = result["confidence_disclaimer"]

        if result["suspected_problem"] == "NOMINAL_OR_MINOR_SURCHARGE":
            inc.state = IncidentState.NOMINAL
            db.add_event(Event(
                event_type="DRAIN_ANOMALY_CLEARED",
                incident_id=incident_id,
                details={"reason": "Investigation ruled out physical blockage or surcharge."}
            ))
        else:
            db.add_event(Event(
                event_type="BLOCKAGE_DIAGNOSED",
                incident_id=incident_id,
                details={"diagnosis": inc.diagnosis, "confidence": inc.confidence}
            ))
            db.add_audit(AuditLog(
                actor="AGENT",
                action="DIAGNOSE_DRAINAGE_ISSUE",
                incident_id=incident_id,
                old_state="ANOMALY",
                new_state="INVESTIGATING",
                reason=result["finding"]
            ))

        db.save_incident(inc)
        return inc

    def dispatch_work_order(self, incident_id: str) -> WorkOrder:
        """
        Dispatches maintenance crew for a DrainPilot incident.
        Validates incident existence, system == 'DRAIN', and eligible state (INVESTIGATING or ANOMALY).
        Transitions incident state to WORK_ORDER_ISSUED.
        """
        inc = db.get_incident(incident_id)
        if not inc:
            raise ValueError(f"Incident '{incident_id}' not found")
        if getattr(inc, "system", None) != "DRAIN":
            raise ValueError(f"Incident '{incident_id}' belongs to system '{inc.system}', not 'DRAIN'")
        if inc.state not in [IncidentState.INVESTIGATING, IncidentState.ANOMALY]:
            raise ValueError(
                f"Invalid state transition: incident must be in INVESTIGATING or ANOMALY state to dispatch (current: {inc.state})"
            )

        wo_id = f"WO-DRN-{uuid.uuid4().hex[:6].upper()}"
        description = inc.diagnosis or "Drainage chamber obstruction clearance and desilting"
        priority = inc.priority if inc.priority != "UNASSIGNED" else "P1"

        wo = WorkOrder(
            work_order_id=wo_id,
            incident_id=incident_id,
            priority=priority,
            assigned_role="Drainage & Civils",
            assigned_person="Manoj Sharma (On-call Drainage Crew)",
            zone=inc.zone,
            description=f"Action: {inc.metadata.get('recommended_action', 'CLEAR_BLOCKAGE')}; Diagnosis: {description}",
            status="ASSIGNED"
        )
        db.save_work_order(wo)

        old_state = inc.state.value if hasattr(inc.state, "value") else str(inc.state)
        inc.state = IncidentState.WORK_ORDER_ISSUED
        db.save_incident(inc)

        db.add_event(Event(
            event_type="WORK_ORDER_CREATED",
            incident_id=incident_id,
            work_order_id=wo_id,
            details={"system": "DRAIN", "assigned_role": wo.assigned_role, "priority": wo.priority}
        ))
        db.add_event(Event(
            event_type="NOTIFICATION_CREATED",
            incident_id=incident_id,
            details={"message": f"URGENT {wo.priority} DRAINAGE DISPATCH for {inc.zone}: {wo.description}"}
        ))
        db.add_audit(AuditLog(
            actor="AGENT",
            action="DISPATCH_WORK_ORDER",
            incident_id=incident_id,
            work_order_id=wo_id,
            old_state=old_state,
            new_state="WORK_ORDER_ISSUED",
            reason=f"Dispatched {wo.assigned_role} to address {description}"
        ))
        return wo

    def claim_completion(self, work_order_id: str) -> Incident:
        """
        Records technician-reported maintenance completion.
        Completion does NOT automatically resolve or close the incident;
        it moves the incident state to VERIFYING awaiting telemetry verification.
        """
        wo = db.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order '{work_order_id}' not found")
        inc = db.get_incident(wo.incident_id)
        if not inc:
            raise ValueError(f"Incident '{wo.incident_id}' linked to work order '{work_order_id}' not found")
        if getattr(inc, "system", None) != "DRAIN":
            raise ValueError(f"Work order '{work_order_id}' belongs to system '{inc.system}', not 'DRAIN'")
        if inc.state not in [IncidentState.WORK_ORDER_ISSUED, IncidentState.REPAIRING]:
            raise ValueError(
                f"Invalid state transition: incident must be in WORK_ORDER_ISSUED or REPAIRING state to claim completion (current: {inc.state})"
            )

        wo.status = "COMPLETION_CLAIMED"
        wo.completion_claimed_at = datetime.now().isoformat()
        db.save_work_order(wo)

        old_state = inc.state.value if hasattr(inc.state, "value") else str(inc.state)
        inc.state = IncidentState.VERIFYING
        db.save_incident(inc)

        actor = "TECHNICIAN" if wo.assigned_role == "Drainage & Civils" else "SUPERVISOR"
        db.add_event(Event(
            event_type="MAINTENANCE_COMPLETION_CLAIMED",
            incident_id=inc.incident_id,
            work_order_id=work_order_id,
            details={"actor": actor, "note": "Technician reported desilting/grate clearing complete"}
        ))
        db.add_event(Event(
            event_type="VERIFICATION_STARTED",
            incident_id=inc.incident_id,
            work_order_id=work_order_id
        ))
        db.add_audit(AuditLog(
            actor=actor,
            action="CLAIM_COMPLETION",
            incident_id=inc.incident_id,
            work_order_id=work_order_id,
            old_state=old_state,
            new_state="VERIFYING",
            reason="Technician submitted maintenance completion claim. Pending physical telemetry verification."
        ))
        return inc

    def verify_resolution(self, work_order_id: str, telemetry: Dict[str, Any]) -> Incident:
        """
        Evaluates post-maintenance telemetry against drainage resolution acceptance criteria:
        - Fill ratio <= safe_fill_ratio (0.45)
        - Freeboard >= safe_freeboard_cm (30 cm)
        - Rate of rise <= safe_rate_of_rise_cm_hr (5.0 cm/hr)
        - Pump status is not faulted

        On failure:
        - Incident remains open and transitions to ESCALATED.
        - Work order re-assigned to Senior Civil Supervisor.
        - Failure reason and telemetry recorded in audit trail.

        On success:
        - Incident transitions to CLOSED.
        - Work order marked VERIFIED / CLOSED.
        - Avoided flood risk & restored headroom recorded.
        """
        wo = db.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order '{work_order_id}' not found")
        inc = db.get_incident(wo.incident_id)
        if not inc:
            raise ValueError(f"Incident '{wo.incident_id}' linked to work order '{work_order_id}' not found")
        if getattr(inc, "system", None) != "DRAIN":
            raise ValueError(f"Work order '{work_order_id}' belongs to system '{inc.system}', not 'DRAIN'")
        if inc.state != IncidentState.VERIFYING:
            raise ValueError(
                f"Invalid state transition: incident must be in VERIFYING state to run verification (current: {inc.state})"
            )

        if not isinstance(telemetry, dict):
            raise ValueError("Telemetry payload must be a dictionary")
        if "water_level_cm" not in telemetry or telemetry["water_level_cm"] is None:
            raise ValueError("Verification telemetry requires 'water_level_cm'")
        try:
            water_level_cm = float(telemetry["water_level_cm"])
        except (ValueError, TypeError):
            raise ValueError("'water_level_cm' must be a valid number")
        if water_level_cm < 0:
            raise ValueError("'water_level_cm' cannot be negative")

        chamber_depth_cm = float(telemetry.get("chamber_depth_cm") or inc.metadata.get("chamber_depth_cm", 100.0))
        rate_of_rise_cm_hr = float(telemetry.get("rate_of_rise_cm_per_hr", 0.0))
        pump_status = str(telemetry.get("pump_status", "OFF")).upper().strip()

        fill_ratio = round(water_level_cm / chamber_depth_cm, 3)
        freeboard_cm = max(0.0, round(chamber_depth_cm - water_level_cm, 2))

        # Drainage verification acceptance criteria
        passed = (
            fill_ratio <= self.safe_fill_ratio and
            freeboard_cm >= self.safe_freeboard_cm and
            rate_of_rise_cm_hr <= self.safe_rate_of_rise_cm_hr and
            pump_status not in self.abnormal_pump_states
        )

        verification_record = {
            "water_level_cm": water_level_cm,
            "chamber_depth_cm": chamber_depth_cm,
            "fill_ratio": fill_ratio,
            "freeboard_cm": freeboard_cm,
            "rate_of_rise_cm_per_hr": rate_of_rise_cm_hr,
            "pump_status": pump_status,
            "timestamp": datetime.now().isoformat(),
            "data_origin": "SIMULATED_POST_MAINTENANCE_TELEMETRY",
            "is_simulated": True
        }

        if not passed:
            failure_reasons = []
            if fill_ratio > self.safe_fill_ratio:
                failure_reasons.append(
                    f"Water level remains high at {water_level_cm} cm ({fill_ratio*100:.1f}% capacity, safe threshold {self.safe_fill_ratio*100:.0f}%)"
                )
            if freeboard_cm < self.safe_freeboard_cm:
                failure_reasons.append(
                    f"Insufficient freeboard ({freeboard_cm} cm < {self.safe_freeboard_cm} cm safety margin)"
                )
            if rate_of_rise_cm_hr > self.safe_rate_of_rise_cm_hr:
                failure_reasons.append(
                    f"Rate of rise remains elevated (+{rate_of_rise_cm_hr} cm/hr > {self.safe_rate_of_rise_cm_hr} cm/hr)"
                )
            if pump_status in self.abnormal_pump_states:
                failure_reasons.append(f"Pump remains in abnormal state: {pump_status}")

            reason = "; ".join(failure_reasons)
            inc.state = IncidentState.ESCALATED
            wo.verification_status = "FAILED"
            wo.status = "ESCALATED"
            wo.assigned_role = "Senior Civil Supervisor"
            wo.assigned_person = "Senior Civil Engineering Supervisor"

            inc.metadata["failed_verification_telemetry"] = verification_record
            inc.metadata["verification_failure_reason"] = reason

            db.add_event(Event(
                event_type="VERIFICATION_FAILED",
                incident_id=inc.incident_id,
                work_order_id=wo.work_order_id,
                details={"telemetry": verification_record, "reason": reason}
            ))
            db.add_event(Event(
                event_type="INCIDENT_ESCALATED",
                incident_id=inc.incident_id,
                work_order_id=wo.work_order_id,
                details={"escalated_to": wo.assigned_role, "reason": reason}
            ))
            db.add_audit(AuditLog(
                actor="SYSTEM",
                action="VERIFY_DRAINAGE_TELEMETRY",
                incident_id=inc.incident_id,
                work_order_id=wo.work_order_id,
                old_state="VERIFYING",
                new_state="ESCALATED",
                reason=f"Verification rejected: {reason}. Escalated to {wo.assigned_role}."
            ))
        else:
            reason = (
                f"Chamber water level safely normalized to {water_level_cm} cm ({fill_ratio*100:.1f}% capacity). "
                f"Freeboard restored to {freeboard_cm} cm with stable rate of rise (+{rate_of_rise_cm_hr} cm/hr)."
            )
            inc.state = IncidentState.CLOSED
            wo.verification_status = "PASSED"
            wo.status = "CLOSED"

            inc.metadata["verified_post_maintenance_telemetry"] = verification_record
            inc.metadata["verified_at"] = datetime.now().isoformat()
            chamber_cross_section_sq_m = 1.5
            restored_depth_m = max(0.0, (inc.metadata.get("water_level_cm", 80.0) - water_level_cm)) / 100.0
            restored_liters = round(chamber_cross_section_sq_m * restored_depth_m * 1000.0, 1)
            inc.metadata["verified_stormwater_capacity_restored_liters"] = restored_liters

            db.add_event(Event(
                event_type="VERIFICATION_PASSED",
                incident_id=inc.incident_id,
                work_order_id=wo.work_order_id,
                details={"telemetry": verification_record, "reason": reason}
            ))
            db.add_event(Event(
                event_type="INCIDENT_RESOLVED",
                incident_id=inc.incident_id,
                work_order_id=wo.work_order_id
            ))
            db.add_event(Event(
                event_type="INCIDENT_CLOSED",
                incident_id=inc.incident_id,
                work_order_id=wo.work_order_id,
                details={"restored_capacity_liters": restored_liters}
            ))
            db.add_audit(AuditLog(
                actor="SYSTEM",
                action="VERIFY_DRAINAGE_TELEMETRY",
                incident_id=inc.incident_id,
                work_order_id=wo.work_order_id,
                old_state="VERIFYING",
                new_state="CLOSED",
                reason=reason
            ))

        db.save_incident(inc)
        db.save_work_order(wo)
        return inc

    def start_second_repair(self, work_order_id: str) -> Incident:
        """
        Allows Senior Supervisor to initiate a second maintenance attempt
        after verification failure. Incident must be in ESCALATED state.
        Transitions state to REPAIRING.
        """
        wo = db.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order '{work_order_id}' not found")
        inc = db.get_incident(wo.incident_id)
        if not inc:
            raise ValueError(f"Incident '{wo.incident_id}' linked to work order '{work_order_id}' not found")
        if getattr(inc, "system", None) != "DRAIN":
            raise ValueError(f"Work order '{work_order_id}' belongs to system '{inc.system}', not 'DRAIN'")
        if inc.state != IncidentState.ESCALATED:
            raise ValueError(
                f"Invalid state transition: incident must be in ESCALATED state to start second repair (current: {inc.state})"
            )

        inc.state = IncidentState.REPAIRING
        wo.status = "IN_PROGRESS"
        db.save_incident(inc)
        db.save_work_order(wo)

        db.add_event(Event(
            event_type="REPAIR_STARTED",
            incident_id=inc.incident_id,
            work_order_id=wo.work_order_id,
            details={"assigned_role": wo.assigned_role, "actor": "Senior Civil Supervisor"}
        ))
        db.add_audit(AuditLog(
            actor="SUPERVISOR",
            action="START_SECOND_MAINTENANCE",
            incident_id=inc.incident_id,
            work_order_id=wo.work_order_id,
            old_state="ESCALATED",
            new_state="REPAIRING",
            reason="Senior Civil Supervisor initiated second maintenance intervention."
        ))
        return inc

    def get_summary(self) -> Dict[str, Any]:
        """
        Returns drainage-only operational summary metrics based on incidents
        and work orders in the shared database.
        """
        drain_incidents = [i for i in db.incidents.values() if i.system == "DRAIN"]
        active = [i for i in drain_incidents if i.state not in [IncidentState.CLOSED, IncidentState.NOMINAL]]
        critical = [i for i in active if i.severity == "CRITICAL" or i.metadata.get("overflow_risk_flag", False)]
        high = [i for i in active if i.severity == "HIGH"]
        investigating = [i for i in active if i.state == IncidentState.INVESTIGATING]
        resolved = [i for i in drain_incidents if i.state == IncidentState.CLOSED]

        drain_wo = [
            w for w in db.work_orders.values()
            if db.get_incident(w.incident_id) and db.get_incident(w.incident_id).system == "DRAIN"
        ]
        active_wo = [w for w in drain_wo if w.status != "CLOSED"]
        escalated_wo = [w for w in drain_wo if w.status == "ESCALATED"]

        monitored_zones = sorted(list(set(i.zone for i in drain_incidents)))

        return {
            "total_zones_monitored": len(monitored_zones),
            "monitored_zones": monitored_zones,
            "total_drain_incidents": len(drain_incidents),
            "active_incidents": len(active),
            "critical_overflow_risks": len(critical),
            "high_severity_incidents": len(high),
            "investigating_count": len(investigating),
            "resolved_count": len(resolved),
            "total_work_orders": len(drain_wo),
            "active_work_orders": len(active_wo),
            "escalated_work_orders": len(escalated_wo),
            "is_simulated": True,
            "data_origin": "SIMULATED_OPERATIONAL_DATA",
            "disclaimer": "Metrics derived from simulated drainage benchmark models. Physical sensor networks are not connected."
        }
