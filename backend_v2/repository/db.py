from typing import Dict, List
from backend_v2.domain.models import Incident, WorkOrder, Event, AuditLog, IncidentState
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.reset_demo_state()

    def reset_demo_state(self):
        self.incidents: Dict[str, Incident] = {}
        self.work_orders: Dict[str, WorkOrder] = {}
        self.events: List[Event] = []
        self.audits: List[AuditLog] = []
        
        # Seed realistic zones and states
        self.seed_incident(Incident(
            incident_id="INC-1002", zone="HOSTEL-B", baseline_flow_lpm=15.0, current_flow_lpm=25.0,
            state=IncidentState.INVESTIGATING, severity="MEDIUM", priority="P3"
        ))
        self.seed_incident(Incident(
            incident_id="INC-1003", zone="UTILITY-BLOCK", baseline_flow_lpm=40.0, current_flow_lpm=41.2,
            state=IncidentState.CLOSED, severity="HIGH", priority="P1", diagnosis="LEAK_CONFIRMED"
        ))
        self.seed_incident(Incident(
            incident_id="INC-1004", zone="CANTEEN", baseline_flow_lpm=10.0, current_flow_lpm=55.0,
            state=IncidentState.CLOSED, severity="LOW", priority="P4", diagnosis="LEGITIMATE_USAGE"
        ))
        self.seed_incident(Incident(
            incident_id="INC-1005", zone="LIBRARY", baseline_flow_lpm=5.0, current_flow_lpm=7.5,
            state=IncidentState.INVESTIGATING, severity="LOW", priority="P4"
        ))
        self.seed_incident(Incident(
            incident_id="INC-1006", zone="HOSTEL-C", baseline_flow_lpm=18.0, current_flow_lpm=38.0,
            state=IncidentState.WORK_ORDER_ISSUED, severity="HIGH", priority="P2"
        ))

    def seed_incident(self, incident: Incident):
        self.incidents[incident.incident_id] = incident

    def save_incident(self, incident: Incident):
        incident.updated_at = datetime.now().isoformat()
        self.incidents[incident.incident_id] = incident
        
    def get_incident(self, incident_id: str) -> Incident:
        return self.incidents.get(incident_id)
        
    def save_work_order(self, wo: WorkOrder):
        wo.updated_at = datetime.now().isoformat()
        self.work_orders[wo.work_order_id] = wo
        
    def get_work_order(self, wo_id: str) -> WorkOrder:
        return self.work_orders.get(wo_id)
        
    def add_event(self, event: Event):
        self.events.append(event)
        
    def add_audit(self, audit: AuditLog):
        self.audits.append(audit)

db = Database()
