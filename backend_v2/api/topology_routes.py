from flask import Blueprint, jsonify, request
from backend_v2.repository.topology_db import get_db, init_db
from backend_v2.domain.topology_models import Organization, Site, Building, PipelineNode, PipeSegment, Meter
from sqlalchemy.orm import Session

# Initialize the db metadata on module load for the demo
init_db()

topology_bp = Blueprint("topology", __name__, url_prefix="/topology")

@topology_bp.route("/organizations", methods=["GET"])
def get_orgs():
    db: Session = next(get_db())
    try:
        orgs = db.query(Organization).all()
        return jsonify([{"id": o.id, "name": o.name} for o in orgs])
    finally:
        db.close()

@topology_bp.route("/sites", methods=["GET"])
def get_sites():
    db: Session = next(get_db())
    try:
        sites = db.query(Site).all()
        return jsonify([{"id": s.id, "organization_id": s.organization_id, "name": s.name} for s in sites])
    finally:
        db.close()

@topology_bp.route("/sites/<site_id>/network", methods=["GET"])
def get_network(site_id: str):
    db: Session = next(get_db())
    try:
        # Load the full topology for a site
        site = db.query(Site).filter_by(id=site_id).first()
        if not site:
            return jsonify({"error": "Site not found"}), 404
            
        buildings = db.query(Building).filter_by(site_id=site_id).all()
        nodes = db.query(PipelineNode).filter_by(site_id=site_id).all()
        segments = db.query(PipeSegment).filter_by(site_id=site_id).all()
        meters = db.query(Meter).join(PipelineNode).filter(PipelineNode.site_id == site_id).all()
        
        return jsonify({
            "site": {"id": site.id, "name": site.name},
            "buildings": [{"id": b.id, "name": b.name, "zone_id": b.zone_id} for b in buildings],
            "nodes": [{"id": n.id, "name": n.name, "type": n.node_type.value, "building_id": n.building_id} for n in nodes],
            "segments": [{"id": s.id, "source_node_id": s.source_node_id, "target_node_id": s.target_node_id, "name": s.name} for s in segments],
            "meters": [{"id": m.id, "node_id": m.node_id, "name": m.name, "type": m.meter_type.value, "unit": m.unit} for m in meters]
        })
    finally:
        db.close()

@topology_bp.route("/nodes", methods=["POST"])
def create_node():
    db: Session = next(get_db())
    data = request.json
    try:
        node = PipelineNode(
            site_id=data["site_id"],
            name=data["name"],
            node_type=data["node_type"],
            building_id=data.get("building_id")
        )
        db.add(node)
        db.commit()
        return jsonify({"id": node.id, "name": node.name, "type": node.node_type.value}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

@topology_bp.route("/segments", methods=["POST"])
def create_segment():
    db: Session = next(get_db())
    data = request.json
    try:
        # Validate graph connections - ensuring both nodes exist in the same site
        src = db.query(PipelineNode).filter_by(id=data["source_node_id"], site_id=data["site_id"]).first()
        tgt = db.query(PipelineNode).filter_by(id=data["target_node_id"], site_id=data["site_id"]).first()
        
        if not src or not tgt:
            return jsonify({"error": "Invalid source or target node reference"}), 400
            
        segment = PipeSegment(
            site_id=data["site_id"],
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            name=data["name"],
            length_m=data.get("length_m")
        )
        db.add(segment)
        db.commit()
        return jsonify({"id": segment.id, "name": segment.name}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

@topology_bp.route("/meters", methods=["GET"])
def get_all_meters():
    db: Session = next(get_db())
    try:
        meters = db.query(Meter).all()
        result = []
        for m in meters:
            node = db.query(PipelineNode).filter_by(id=m.node_id).first()
            building = db.query(Building).filter_by(id=node.building_id).first() if (node and node.building_id) else None
            result.append({
                "id": m.id,
                "name": m.name,
                "meter_type": m.meter_type.value,
                "unit": m.unit,
                "is_active": m.is_active,
                "node_id": m.node_id,
                "node_name": node.name if node else "Unknown Node",
                "building_name": building.name if building else "Trunk Segment",
                "zone_id": building.zone_id if building else None
            })
        return jsonify(result)
    finally:
        db.close()

@topology_bp.route("/meters", methods=["POST"])
def create_meter():
    db: Session = next(get_db())
    data = request.json or {}
    try:
        node = db.query(PipelineNode).filter_by(id=data["node_id"]).first()
        if not node:
            return jsonify({"error": "Invalid node reference"}), 400
            
        meter = Meter(
            node_id=data["node_id"],
            name=data["name"],
            meter_type=data["meter_type"],
            unit=data.get("unit", "L/min")
        )
        db.add(meter)
        db.commit()
        return jsonify({"id": meter.id, "name": meter.name}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

