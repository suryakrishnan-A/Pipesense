import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

# 1. DOMAIN MODELS & STATE MACHINE
domain_models = """
from enum import Enum
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

class IncidentState(str, Enum):
    NOMINAL = "NOMINAL"
    ANOMALY = "ANOMALY"
    INVESTIGATING = "INVESTIGATING"
    LEAK_CONFIRMED = "LEAK_CONFIRMED"
    WORK_ORDER_ISSUED = "WORK_ORDER_ISSUED"
    VERIFYING = "VERIFYING"
    FAILED_VERIFICATION = "FAILED_VERIFICATION"
    ESCALATED = "ESCALATED"
    REPAIRING = "REPAIRING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

@dataclass
class Event:
    event_type: str
    incident_id: Optional[str] = None
    work_order_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AuditLog:
    actor: str
    action: str
    incident_id: Optional[str] = None
    work_order_id: Optional[str] = None
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Incident:
    incident_id: str
    zone: str
    baseline_flow_lpm: float
    current_flow_lpm: float
    system: str = "PIPE"
    state: IncidentState = IncidentState.NOMINAL
    severity: str = "UNKNOWN"
    priority: str = "UNASSIGNED"
    confidence: float = 0.0
    description: str = ""
    diagnosis: str = ""
    detected_at: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkOrder:
    work_order_id: str
    incident_id: str
    priority: str
    assigned_role: str
    assigned_person: str
    zone: str
    description: str
    status: str = "DISPATCHED"
    verification_status: str = "PENDING"
    completion_claimed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
"""
write_file('backend_v2/domain/models.py', domain_models)

# 2. REPOSITORY
repo_db = """
from typing import Dict, List
from backend_v2.domain.models import Incident, WorkOrder, Event, AuditLog

class Database:
    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.work_orders: Dict[str, WorkOrder] = {}
        self.events: List[Event] = []
        self.audits: List[AuditLog] = []
        self.telemetry_history: List[Dict] = []
        
    def save_incident(self, incident: Incident):
        self.incidents[incident.incident_id] = incident
        
    def get_incident(self, incident_id: str) -> Incident:
        return self.incidents.get(incident_id)
        
    def save_work_order(self, wo: WorkOrder):
        self.work_orders[wo.work_order_id] = wo
        
    def get_work_order(self, wo_id: str) -> WorkOrder:
        return self.work_orders.get(wo_id)
        
    def add_event(self, event: Event):
        self.events.append(event)
        
    def add_audit(self, audit: AuditLog):
        self.audits.append(audit)
        
db = Database()
"""
write_file('backend_v2/repository/db.py', repo_db)

# 3. AGENT TOOLS
agent_tools = """
def check_weather():
    return {"rainfall_last_12h_mm": 0.0, "irrigation_active": False, "analysis": "No rain. Irrigation off."}

def check_peer_baselines():
    return {"analysis": "Neighboring buildings approximately 1.0x baseline."}

def check_maintenance_history():
    return {"analysis": "Minor fissure on Basement Secondary Riser."}

def check_occupancy():
    return {"analysis": "Standard rest hours. No approved events."}
"""
write_file('backend_v2/agent/tools/tools.py', agent_tools)

# 4. AGENT FRAMEWORK
agent_fw = """
from backend_v2.agent.tools.tools import check_weather, check_peer_baselines, check_maintenance_history, check_occupancy

class StrandsAgent:
    def investigate(self, incident):
        # Record tool calls (simulated for demo)
        w = check_weather()
        p = check_peer_baselines()
        m = check_maintenance_history()
        o = check_occupancy()
        
        # Hardcoded 98% logic as required by prompt for this specific anomaly
        return {
            "diagnosis": "LEAK_CONFIRMED",
            "confidence": 0.98,
            "evidence": [w['analysis'], p['analysis'], m['analysis'], o['analysis']],
            "recommended_action": "ISSUE_P1_WORK_ORDER"
        }
"""
write_file('backend_v2/agent/pipesense_agent.py', agent_fw)

# 5. SERVICES (STATE MACHINE & LOGIC)
services = """
from datetime import datetime
import uuid
from backend_v2.domain.models import Incident, WorkOrder, IncidentState, Event, AuditLog
from backend_v2.repository.db import db
from backend_v2.agent.pipesense_agent import StrandsAgent

class PipeSenseService:
    def detect_anomaly(self, zone: str, current_flow: float, baseline_flow: float):
        ratio = current_flow / baseline_flow if baseline_flow > 0 else 0
        
        # Create Incident
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
        result = agent.investigate(inc)
        
        if result["diagnosis"] == "LEAK_CONFIRMED" and result["confidence"] >= 0.95:
            inc.state = IncidentState.LEAK_CONFIRMED
            inc.confidence = result["confidence"]
            inc.diagnosis = result["diagnosis"]
            
            # Impact calculation
            daily_loss = (inc.current_flow_lpm - inc.baseline_flow_lpm) * 1440
            inc.metadata["estimated_daily_loss_liters"] = daily_loss
            
            db.add_event(Event(event_type="LEAK_CONFIRMED", incident_id=incident_id, details={"daily_loss": daily_loss}))
            db.add_audit(AuditLog(actor="AGENT", action="CONFIRM_LEAK", incident_id=incident_id, old_state="INVESTIGATING", new_state="LEAK_CONFIRMED"))
        
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
            description="Basement Secondary Riser"
        )
        db.save_work_order(wo)
        
        inc.state = IncidentState.WORK_ORDER_ISSUED
        inc.priority = "P1"
        db.save_incident(inc)
        
        db.add_event(Event(event_type="WORK_ORDER_CREATED", incident_id=incident_id, work_order_id=wo_id))
        db.add_event(Event(event_type="NOTIFICATION_CREATED", incident_id=incident_id, details={"message": "URGENT P1 WATER LEAK..."}))
        return wo

    def claim_completion(self, wo_id: str):
        wo = db.get_work_order(wo_id)
        if not wo:
            raise ValueError("Work order not found")
            
        inc = db.get_incident(wo.incident_id)
        if inc.state not in [IncidentState.WORK_ORDER_ISSUED, IncidentState.REPAIRING]:
            raise ValueError("Invalid state transition")
            
        wo.status = "COMPLETION_CLAIMED"
        wo.completion_claimed_at = datetime.now()
        db.save_work_order(wo)
        
        inc.state = IncidentState.VERIFYING
        db.save_incident(inc)
        
        db.add_event(Event(event_type="REPAIR_COMPLETION_CLAIMED", incident_id=inc.incident_id, work_order_id=wo_id))
        db.add_event(Event(event_type="VERIFICATION_STARTED", incident_id=inc.incident_id))
        return inc

    def verify_repair(self, wo_id: str, telemetry_reading: float):
        wo = db.get_work_order(wo_id)
        inc = db.get_incident(wo.incident_id)
        
        if inc.state != IncidentState.VERIFYING:
            raise ValueError("Incident not in VERIFYING state")
            
        if telemetry_reading > (inc.baseline_flow_lpm * 1.35):
            # Failed
            inc.state = IncidentState.FAILED_VERIFICATION
            wo.verification_status = "FAILED"
            db.add_event(Event(event_type="VERIFICATION_FAILED", incident_id=inc.incident_id, details={"reading": telemetry_reading}))
            
            # Escalate
            inc.state = IncidentState.ESCALATED
            wo.assigned_role = "Senior Supervisor"
            db.add_event(Event(event_type="INCIDENT_ESCALATED", incident_id=inc.incident_id))
        else:
            # Passed
            inc.state = IncidentState.RESOLVED
            wo.verification_status = "PASSED"
            db.add_event(Event(event_type="VERIFICATION_PASSED", incident_id=inc.incident_id))
            db.add_event(Event(event_type="INCIDENT_RESOLVED", incident_id=inc.incident_id))
            
            # Close
            inc.state = IncidentState.CLOSED
            db.add_event(Event(event_type="INCIDENT_CLOSED", incident_id=inc.incident_id))
            
            # Impact
            saved = (inc.current_flow_lpm - telemetry_reading) * 1440
            inc.metadata["verified_loss_avoidance_lpd"] = saved
            db.add_event(Event(event_type="IMPACT_RECORDED", incident_id=inc.incident_id, details={"saved_lpd": saved}))
            
        db.save_incident(inc)
        db.save_work_order(wo)
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
"""
write_file('backend_v2/services/pipesense_service.py', services)

# 6. API ROUTES
api = """
from flask import Flask, jsonify, request
from backend_v2.services.pipesense_service import PipeSenseService
from backend_v2.repository.db import db
from dataclasses import asdict

app = Flask(__name__)
service = PipeSenseService()

@app.route("/pipesense/detect", methods=["POST"])
def detect():
    data = request.json
    inc = service.detect_anomaly(data["zone"], data["current_flow"], data["baseline_flow"])
    return jsonify(asdict(inc))

@app.route("/pipesense/incidents/<incident_id>/investigate", methods=["POST"])
def investigate(incident_id: str):
    inc = service.run_investigation(incident_id)
    return jsonify(asdict(inc))

@app.route("/pipesense/incidents/<incident_id>/dispatch", methods=["POST"])
def dispatch(incident_id: str):
    wo = service.dispatch_work_order(incident_id)
    return jsonify(asdict(wo))

@app.route("/work-orders/<work_order_id>/complete", methods=["POST"])
def complete_wo(work_order_id: str):
    inc = service.claim_completion(work_order_id)
    return jsonify(asdict(inc))

@app.route("/work-orders/<work_order_id>/verify", methods=["POST"])
def verify_wo(work_order_id: str):
    data = request.json
    inc = service.verify_repair(work_order_id, data["telemetry"])
    return jsonify(asdict(inc))

@app.route("/work-orders/<work_order_id>/repair", methods=["POST"])
def repair_wo(work_order_id: str):
    inc = service.start_second_repair(work_order_id)
    return jsonify(asdict(inc))

@app.route("/demo/pipesense/run", methods=["POST"])
def run_demo():
    inc = service.detect_anomaly("BLDG-04", 64.2, 18.4)
    service.run_investigation(inc.incident_id)
    wo = service.dispatch_work_order(inc.incident_id)
    service.claim_completion(wo.work_order_id)
    service.verify_repair(wo.work_order_id, 61.8) # Fails -> Escalates
    service.start_second_repair(wo.work_order_id)
    service.claim_completion(wo.work_order_id)
    inc = service.verify_repair(wo.work_order_id, 18.2) # Passes -> Resolves -> Closes
    
    events = [asdict(e) for e in db.events if e.incident_id == inc.incident_id]
    return jsonify({"incident": asdict(inc), "events": events})

if __name__ == '__main__':
    app.run(port=5001)
"""
write_file('backend_v2/api/main.py', api)

# 7. TESTS
tests = """
import pytest
from backend_v2.services.pipesense_service import PipeSenseService
from backend_v2.domain.models import IncidentState

def test_end_to_end_flow():
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
    assert inc.metadata["verified_loss_avoidance_lpd"] == 66240.0 # (64.2 - 18.2) * 1440
"""
write_file('tests_v2/test_pipesense.py', tests)
