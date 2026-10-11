from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend_v2.domain.sql_models import Base, Organization, Site, Building, PipelineNode, PipeSegment, Meter, NodeType, MeterType
import os

# Database file and connection setup
DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "topology.db")
DB_PATH = os.environ.get("PIPESENSE_DB_PATH", DEFAULT_DB_PATH)

def _get_engine(db_path=None):
    db_url = os.environ.get("DATABASE_URL")
    if db_url and not db_path:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return create_engine(db_url)
    resolved_path = db_path or os.environ.get("PIPESENSE_DB_PATH", DEFAULT_DB_PATH)
    return create_engine(f"sqlite:///{resolved_path}")

engine = _get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def configure_db(db_path=None):
    """Reconfigures the database engine and sessionmaker (used for test isolation)."""
    global DB_PATH, engine, SessionLocal
    if db_path is not None:
        DB_PATH = db_path
    else:
        DB_PATH = os.environ.get("PIPESENSE_DB_PATH", DEFAULT_DB_PATH)
    engine = _get_engine(db_path=DB_PATH)
    SessionLocal.configure(bind=engine)
    return engine

def init_db():
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            cols = [r[1] for r in conn.execute(text("PRAGMA table_info(incidents)")).fetchall()]
            if cols and "post_repair_flow" not in cols:
                conn.execute(text("ALTER TABLE incidents ADD COLUMN post_repair_flow FLOAT"))
                conn.commit()
    seed_demo_topology()

def reset_db_to_seed():
    """Drops all tables, recreates schema, and seeds standard baseline records."""
    Base.metadata.drop_all(bind=engine)
    init_db()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed_demo_topology():
    # Only seed if empty
    with SessionLocal() as db:
        if db.query(Organization).first() is not None:
            return
            
        # Seed initial demo network mapping to the existing frontend hardcoded graph
        org = Organization(name="Apex Manufacturing")
        db.add(org)
        db.flush()
        
        site = Site(organization_id=org.id, name="North Campus")
        db.add(site)
        db.flush()
        
        # Buildings
        b1 = Building(site_id=site.id, name="Admin Block", zone_id="BLDG-01")
        b4 = Building(site_id=site.id, name="Science Block 4", zone_id="BLDG-04")
        bh = Building(site_id=site.id, name="Hostel B", zone_id="HOSTEL-B")
        db.add_all([b1, b4, bh])
        db.flush()
        
        # Nodes
        n_src = PipelineNode(site_id=site.id, name="SRC-01", node_type=NodeType.SOURCE)
        n_jct = PipelineNode(site_id=site.id, name="JCT-A", node_type=NodeType.JUNCTION)
        n_b1 = PipelineNode(site_id=site.id, building_id=b1.id, name="INLET-BLDG-01", node_type=NodeType.BUILDING_INLET)
        n_b4 = PipelineNode(site_id=site.id, building_id=b4.id, name="INLET-BLDG-04", node_type=NodeType.BUILDING_INLET)
        n_bh = PipelineNode(site_id=site.id, building_id=bh.id, name="INLET-HOSTEL-B", node_type=NodeType.BUILDING_INLET)
        db.add_all([n_src, n_jct, n_b1, n_b4, n_bh])
        db.flush()
        
        # Segments
        s1 = PipeSegment(site_id=site.id, source_node_id=n_src.id, target_node_id=n_jct.id, name="Main Trunk A", length_m=120.0)
        s2 = PipeSegment(site_id=site.id, source_node_id=n_jct.id, target_node_id=n_b1.id, name="Branch 1", length_m=45.5)
        s3 = PipeSegment(site_id=site.id, source_node_id=n_jct.id, target_node_id=n_b4.id, name="Branch 2", length_m=65.0)
        s4 = PipeSegment(site_id=site.id, source_node_id=n_jct.id, target_node_id=n_bh.id, name="Branch 3", length_m=30.2)
        db.add_all([s1, s2, s3, s4])
        
        # Meters
        m_src = Meter(node_id=n_src.id, name="Main Inlet Flow", meter_type=MeterType.FLOW, unit="L/min")
        m_b1 = Meter(node_id=n_b1.id, name="Admin Inlet Flow", meter_type=MeterType.FLOW, unit="L/min")
        m_b4 = Meter(node_id=n_b4.id, name="Science Inlet Flow", meter_type=MeterType.FLOW, unit="L/min")
        m_bh = Meter(node_id=n_bh.id, name="Hostel Inlet Flow", meter_type=MeterType.FLOW, unit="L/min")
        db.add_all([m_src, m_b1, m_b4, m_bh])
        db.flush()

        # Mock Incidents for Tests
        from backend_v2.domain.sql_models import Incident, IncidentState, Severity
        db.add_all([
            Incident(id="INC-1002", site_id=site.id, asset_id="CANTEEN", baseline_flow=15.0, current_flow=35.0, state=IncidentState.INVESTIGATING, severity=Severity.MEDIUM),
            Incident(id="INC-1003", site_id=site.id, asset_id="BLDG-04", baseline_flow=18.4, current_flow=64.2, state=IncidentState.LEAK_CONFIRMED if hasattr(IncidentState, 'LEAK_CONFIRMED') else IncidentState.WORK_ORDER_ISSUED, severity=Severity.HIGH),
            Incident(id="INC-1004", site_id=site.id, asset_id="SPORTS-HALL", baseline_flow=5.0, current_flow=6.2, state=IncidentState.NOMINAL if hasattr(IncidentState, 'NOMINAL') else IncidentState.CLOSED, severity=Severity.LOW),
            Incident(id="INC-1005", site_id=site.id, asset_id="LIBRARY", baseline_flow=12.0, current_flow=13.0, state=IncidentState.INVESTIGATING, severity=Severity.LOW),
            Incident(id="INC-1006", site_id=site.id, asset_id="HOSTEL-C", baseline_flow=18.0, current_flow=38.0, state=IncidentState.WORK_ORDER_ISSUED, severity=Severity.HIGH)
        ])
        
        db.commit()
