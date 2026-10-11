from enum import Enum
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

class IncidentState(str, Enum):
    NOMINAL = "NOMINAL"
    ANOMALY = "ANOMALY"
    INVESTIGATING = "INVESTIGATING"
    LEAK_CONFIRMED = "LEAK_CONFIRMED"
    LEAK_SUSPECTED = "LEAK_SUSPECTED"
    LEGITIMATE_USAGE = "LEGITIMATE_USAGE"
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
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
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
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

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
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
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
    status: str = "OPEN"
    verification_status: str = "PENDING"
    completion_claimed_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
