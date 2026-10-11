from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum
import uuid

class Base(DeclarativeBase):
    pass

class NodeType(str, enum.Enum):
    SOURCE = "SOURCE"
    JUNCTION = "JUNCTION"
    BUILDING_INLET = "BUILDING_INLET"

class MeterType(str, enum.Enum):
    FLOW = "FLOW"
    PRESSURE = "PRESSURE"
    QUALITY = "QUALITY"

def generate_uuid():
    return str(uuid.uuid4())

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
    zone_id: Mapped[str] = mapped_column(String, nullable=True) # E.g., BLDG-04, maps to incident zones
    
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
    unit: Mapped[str] = mapped_column(String, nullable=False) # e.g. "L/min", "bar"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    node: Mapped["PipelineNode"] = relationship(back_populates="meters")
