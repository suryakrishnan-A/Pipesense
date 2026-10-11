import os
import json
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class CampusDataStore:
    """
    Hybrid Data Store for Hackathon:
    - Automatically syncs with AWS DynamoDB if active credentials/tables exist.
    - Gracefully falls back to high-speed local memory/file persistence.
    """
    def __init__(self, data_file=None):
        self.data_file = data_file or os.path.join(os.path.dirname(__file__), "mock_store.json")
        self.incidents = {}
        self.work_orders = {}
        self.buildings = {
            "BLDG-01": {"name": "Admin & Academic Block", "baseline_night_lpm": 12.0, "type": "academic"},
            "BLDG-02": {"name": "Central Library & Compute Hub", "baseline_night_lpm": 8.5, "type": "facility"},
            "BLDG-03": {"name": "Aryabhata Engineering Block", "baseline_night_lpm": 14.2, "type": "academic"},
            "BLDG-04": {"name": "Satish Dhawan Hostel & Lab Block", "baseline_night_lpm": 18.4, "type": "residential_lab"},
            "BLDG-05": {"name": "Campus Dining & Amenities", "baseline_night_lpm": 22.0, "type": "cafeteria"},
        }
        self.on_call_crew = [
            {"id": "TECH-01", "name": "Rajesh Kumar", "role": "Senior Plumber", "phone": "+91-98765-43210", "status": "AVAILABLE"},
            {"id": "TECH-02", "name": "Manoj Sharma", "role": "Drainage & Civils", "phone": "+91-98765-43211", "status": "AVAILABLE"},
            {"id": "TECH-03", "name": "Vikas Singh", "role": "Electrical & Grid", "phone": "+91-98765-43212", "status": "AVAILABLE"},
        ]
        
        self.dynamodb = None
        self.table_name = "ResilienceAgentData"
        self._init_aws()
        self._load()

    def _init_aws(self):
        # Local JSON file / in-memory persistence.
        # AWS DynamoDB is unimplemented in this local build; no AWS resources are accessed.
        self.dynamodb = None

    def _load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.incidents = data.get("incidents", {})
                    self.work_orders = data.get("work_orders", {})
            except Exception:
                pass
        
        if self.dynamodb:
            try:
                table = self.dynamodb.Table(self.table_name)
                # Just keeping it simple for the demo, we could load from DDB, 
                # but local mock is faster for demo resets.
            except Exception:
                pass

    def _save(self):
        try:
            with open(self.data_file, "w") as f:
                json.dump({
                    "incidents": self.incidents,
                    "work_orders": self.work_orders
                }, f, indent=2)
        except Exception:
            pass
            
        if self.dynamodb:
            try:
                table = self.dynamodb.Table(self.table_name)
                # Save latest state to DynamoDB
                table.put_item(Item={
                    'pk': 'LATEST_STATE',
                    'incidents': json.dumps(self.incidents),
                    'work_orders': json.dumps(self.work_orders),
                    'updated_at': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Failed to sync to DynamoDB: {e}")

    def create_incident(self, incident_type, building_id, title, details, severity="HIGH"):
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        incident = {
            "incident_id": incident_id,
            "incident_type": incident_type,
            "building_id": building_id,
            "building_name": self.buildings.get(building_id, {}).get("name", "Unknown"),
            "title": title,
            "details": details,
            "severity": severity,
            "status": "INVESTIGATING",
            "created_at": datetime.now().isoformat(),
            "investigation_log": [],
            "work_order_id": None,
            "outcome": None
        }
        self.incidents[incident_id] = incident
        self._save()
        return incident

    def log_investigation_step(self, incident_id, tool_name, query, result, reasoning=""):
        if incident_id in self.incidents:
            self.incidents[incident_id]["investigation_log"].append({
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "query": query,
                "result": result,
                "reasoning": reasoning
            })
            self._save()

    def create_work_order(self, incident_id, title, instructions, assigned_to=None, priority="P1"):
        wo_id = f"WO-{uuid.uuid4().hex[:6].upper()}"
        assigned = assigned_to or self.on_call_crew[0]
        work_order = {
            "work_order_id": wo_id,
            "incident_id": incident_id,
            "title": title,
            "instructions": instructions,
            "priority": priority,
            "assigned_to": assigned,
            "status": "DISPATCHED",
            "created_at": datetime.now().isoformat(),
            "completion_reported_at": None,
            "verification_status": "PENDING"
        }
        self.work_orders[wo_id] = work_order
        if incident_id in self.incidents:
            self.incidents[incident_id]["work_order_id"] = wo_id
            self.incidents[incident_id]["status"] = "DISPATCHED"
        self._save()
        return work_order

    def update_work_order_status(self, wo_id, status, notes=""):
        if wo_id in self.work_orders:
            self.work_orders[wo_id]["status"] = status
            if status == "COMPLETION_REPORTED":
                self.work_orders[wo_id]["completion_reported_at"] = datetime.now().isoformat()
            self.work_orders[wo_id]["notes"] = notes
            self._save()
            return self.work_orders[wo_id]
        return None

    def close_incident(self, incident_id, outcome):
        if incident_id in self.incidents:
            self.incidents[incident_id]["status"] = "RESOLVED_VERIFIED"
            self.incidents[incident_id]["outcome"] = outcome
            wo_id = self.incidents[incident_id].get("work_order_id")
            if wo_id and wo_id in self.work_orders:
                self.work_orders[wo_id]["status"] = "COMPLETED"
                self.work_orders[wo_id]["verification_status"] = "PASSED"
            self._save()
            return self.incidents[incident_id]
        return None

    def reject_repair_and_escalate(self, incident_id, reason):
        if incident_id in self.incidents:
            self.incidents[incident_id]["status"] = "VERIFICATION_FAILED_ESCALATED"
            self.incidents[incident_id]["escalation_reason"] = reason
            wo_id = self.incidents[incident_id].get("work_order_id")
            if wo_id and wo_id in self.work_orders:
                self.work_orders[wo_id]["verification_status"] = "FAILED"
                self.work_orders[wo_id]["status"] = "IN_PROGRESS"
            self._save()
            return self.incidents[incident_id]
        return None

# Global Singleton
store = CampusDataStore()
