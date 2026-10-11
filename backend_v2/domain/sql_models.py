from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Float, Boolean, ForeignKey, Enum as SQLEnum, DateTime, Text, Integer, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum
import uuid

class Base(DeclarativeBase):
    pass

def generate_uuid():
    return str(uuid.uuid4())

# ---------------------------------------------------------
# Enums
# ---------------------------------------------------------
class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    TECHNICIAN = "TECHNICIAN"
    VIEWER = "VIEWER"

class NodeType(str, enum.Enum):
    SOURCE = "SOURCE"
    JUNCTION = "JUNCTION"
    BUILDING_INLET = "BUILDING_INLET"
    TANK = "TANK"
    PUMP = "PUMP"
    VALVE = "VALVE"

class MeterType(str, enum.Enum):
    FLOW = "FLOW"
    PRESSURE = "PRESSURE"
    QUALITY = "QUALITY"

class IncidentState(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    WORK_ORDER_ISSUED = "WORK_ORDER_ISSUED"
    REPAIR_VERIFICATION = "REPAIR_VERIFICATION"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    FALSE_ALARM = "FALSE_ALARM"

class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class WorkOrderStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

# ---------------------------------------------------------
# Auth & RBAC
# ---------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[Role] = mapped_column(SQLEnum(Role), default=Role.VIEWER)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

# ---------------------------------------------------------
# Topology & Assets
# ---------------------------------------------------------
class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    sites: Mapped[List["Site"]] = relationship(back_populates="organization", cascade="all, delete-orphan")

class Site(Base):
    __tablename__ = "sites"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    organization: Mapped["Organization"] = relationship(back_populates="sites")
    buildings: Mapped[List["Building"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    nodes: Mapped[List["PipelineNode"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    segments: Mapped[List["PipeSegment"]] = relationship(back_populates="site", cascade="all, delete-orphan")

class Building(Base):
    __tablename__ = "buildings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    zone_id: Mapped[str] = mapped_column(String, nullable=True)
    site: Mapped["Site"] = relationship(back_populates="buildings")
    inlet_nodes: Mapped[List["PipelineNode"]] = relationship(back_populates="building")

class PipelineNode(Base):
    __tablename__ = "pipeline_nodes"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), nullable=False)
    building_id: Mapped[Optional[str]] = mapped_column(ForeignKey("buildings.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    node_type: Mapped[NodeType] = mapped_column(SQLEnum(NodeType), nullable=False)
    site: Mapped["Site"] = relationship(back_populates="nodes")
    building: Mapped[Optional["Building"]] = relationship(back_populates="inlet_nodes")
    meters: Mapped[List["Meter"]] = relationship(back_populates="node", cascade="all, delete-orphan")

class PipeSegment(Base):
    __tablename__ = "pipe_segments"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), nullable=False)
    source_node_id: Mapped[str] = mapped_column(ForeignKey("pipeline_nodes.id"), nullable=False)
    target_node_id: Mapped[str] = mapped_column(ForeignKey("pipeline_nodes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    length_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    site: Mapped["Site"] = relationship(back_populates="segments")
    source_node: Mapped["PipelineNode"] = relationship(foreign_keys=[source_node_id])
    target_node: Mapped["PipelineNode"] = relationship(foreign_keys=[target_node_id])

class Meter(Base):
    __tablename__ = "meters"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    node_id: Mapped[str] = mapped_column(ForeignKey("pipeline_nodes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    meter_type: Mapped[MeterType] = mapped_column(SQLEnum(MeterType), nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    node: Mapped["PipelineNode"] = relationship(back_populates="meters")
    readings: Mapped[List["TelemetryReading"]] = relationship(back_populates="meter", cascade="all, delete-orphan")

# ---------------------------------------------------------
# Telemetry
# ---------------------------------------------------------
class TelemetryReading(Base):
    __tablename__ = "telemetry_readings"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality_flag: Mapped[str] = mapped_column(String, default="GOOD") # GOOD, SUSPECT, BAD
    meter: Mapped["Meter"] = relationship(back_populates="readings")

# ---------------------------------------------------------
# Incidents, Work Orders, Verification
# ---------------------------------------------------------
class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), nullable=False)
    asset_id: Mapped[str] = mapped_column(String, nullable=False) # e.g. Node ID or Building Zone
    state: Mapped[IncidentState] = mapped_column(SQLEnum(IncidentState), default=IncidentState.OPEN)
    severity: Mapped[Severity] = mapped_column(SQLEnum(Severity), default=Severity.MEDIUM)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    baseline_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    post_repair_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hypothesis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    work_orders: Mapped[List["WorkOrder"]] = relationship(back_populates="incident")
    evidence: Mapped[List["Evidence"]] = relationship(back_populates="incident")

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    data_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    incident: Mapped["Incident"] = relationship(back_populates="evidence")

class WorkOrder(Base):
    __tablename__ = "work_orders"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[WorkOrderStatus] = mapped_column(SQLEnum(WorkOrderStatus), default=WorkOrderStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repair_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    incident: Mapped["Incident"] = relationship(back_populates="work_orders")

class VerificationRecord(Base):
    __tablename__ = "verification_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    work_order_id: Mapped[str] = mapped_column(ForeignKey("work_orders.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    post_repair_flow: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

# ---------------------------------------------------------
# Audit & Config
# ---------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    actor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # User ID or 'SYSTEM'
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    details: Mapped[dict] = mapped_column(JSON, nullable=True)

class ThresholdConfig(Base):
    __tablename__ = "threshold_configs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), nullable=False)
    parameter_name: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
