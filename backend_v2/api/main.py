import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from backend_v2.services.pipesense_service_sql import PipeSenseServiceSQL
from backend_v2.repository.topology_db import SessionLocal
from backend_v2.domain.sql_models import Incident, WorkOrder, AuditLog, IncidentState
from backend_v2.api.drain_routes import drain_blueprint
from backend_v2.api.topology_routes import topology_bp

app = Flask(__name__)

# Configure CORS: allow restricting to deployed frontend in production while allowing local dev by default
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS") or os.environ.get("FRONTEND_URL")
if allowed_origins_env and allowed_origins_env.strip() != "*":
    origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]
    CORS(app, origins=origins)
else:
    CORS(app)

app.register_blueprint(drain_blueprint)
app.register_blueprint(topology_bp)
service = PipeSenseServiceSQL()

@app.route("/incidents/detect", methods=["POST"])
@app.route("/pipesense/detect", methods=["POST"])
def detect():
    data = request.json or {}
    zone = data.get("zone") or data.get("asset_id") or "BLDG-04"
    inc = service.detect_anomaly(zone, float(data.get("current_flow", 64.2)), float(data.get("baseline_flow", 18.4)))
    if inc: return jsonify(inc)
    return jsonify({"message": "Nominal flow"})

@app.route("/incidents", methods=["GET"])
@app.route("/pipesense/incidents", methods=["GET"])
def list_incidents():
    with SessionLocal() as db:
        incs = db.query(Incident).order_by(Incident.created_at.desc()).all()
        return jsonify([service._to_dict(i) for i in incs])

@app.route("/incidents/<incident_id>", methods=["GET"])
@app.route("/pipesense/incidents/<incident_id>", methods=["GET"])
def get_incident(incident_id: str):
    with SessionLocal() as db:
        inc = db.query(Incident).filter_by(id=incident_id).first()
        if not inc: return jsonify({"error": "not found"}), 404
        return jsonify(service._to_dict(inc))

@app.route("/work-orders", methods=["GET"])
@app.route("/pipesense/work-orders", methods=["GET"])
def list_work_orders():
    with SessionLocal() as db:
        wos = db.query(WorkOrder).order_by(WorkOrder.created_at.desc()).all()
        return jsonify([service._to_dict(w) for w in wos])

@app.route("/work-orders/<work_order_id>", methods=["GET"])
@app.route("/pipesense/work-orders/<work_order_id>", methods=["GET"])
def get_work_order(work_order_id: str):
    with SessionLocal() as db:
        wo = db.query(WorkOrder).filter_by(id=work_order_id).first()
        if not wo: return jsonify({"error": "not found"}), 404
        return jsonify(service._to_dict(wo))

@app.route("/summary", methods=["GET"])
@app.route("/pipesense/summary", methods=["GET"])
def get_summary():
    return jsonify(service.get_summary())

@app.route("/pipesense/impact", methods=["GET"])
def get_impact():
    with SessionLocal() as db:
        # Find latest BLDG-04 incident
        inc = db.query(Incident).filter_by(asset_id="BLDG-04").order_by(Incident.created_at.desc()).first()
        if inc:
            base_flow = inc.baseline_flow if inc.baseline_flow is not None else 18.4
            peak_flow = inc.current_flow if inc.current_flow is not None else 64.2
            
            # Pre-repair estimated daily loss based on abnormal flow above baseline
            loss_rate = peak_flow - base_flow if peak_flow > base_flow else 0.0
            estimated_daily_loss = loss_rate * 1440.0

            is_resolved = inc.state in ("RESOLVED", "CLOSED", IncidentState.RESOLVED, IncidentState.CLOSED)
            
            # Actual measured post-repair reading from verified telemetry
            measured_post_flow = inc.post_repair_flow
            if measured_post_flow is None and is_resolved:
                from backend_v2.domain.sql_models import VerificationRecord
                v_rec = db.query(VerificationRecord).filter_by(incident_id=inc.id, passed=True).order_by(VerificationRecord.timestamp.desc()).first()
                if v_rec and v_rec.post_repair_flow is not None:
                    measured_post_flow = v_rec.post_repair_flow

            if is_resolved and measured_post_flow is not None:
                # Water savings: abnormal pre-repair flow minus actual measured post-repair flow
                flow_reduction = peak_flow - measured_post_flow if peak_flow > measured_post_flow else 0.0
                avoided_daily_loss = flow_reduction * 1440.0
                return jsonify({
                    "estimated_daily_loss_liters": estimated_daily_loss,
                    "verified_daily_loss_avoided_liters": avoided_daily_loss,
                    "baseline_flow_lpm": base_flow,
                    "peak_abnormal_flow_lpm": peak_flow,
                    "verified_post_repair_flow_lpm": measured_post_flow,
                    "water_loss_reduction_lpm": flow_reduction
                })
            else:
                return jsonify({
                    "estimated_daily_loss_liters": estimated_daily_loss,
                    "verified_daily_loss_avoided_liters": 0.0,
                    "baseline_flow_lpm": base_flow,
                    "peak_abnormal_flow_lpm": peak_flow,
                    "verified_post_repair_flow_lpm": None,
                    "water_loss_reduction_lpm": 0.0
                })
    return jsonify({})

@app.route("/events/<incident_id>", methods=["GET"])
def get_events(incident_id: str):
    with SessionLocal() as db:
        events = db.query(AuditLog).filter_by(target_id=incident_id).order_by(AuditLog.timestamp.desc()).all()
        return jsonify([service._to_dict(e) for e in events])

@app.route("/audit-logs", methods=["GET"])
def list_audit_logs():
    with SessionLocal() as db:
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()
        return jsonify([service._to_dict(l) for l in logs])

@app.route("/agent-status", methods=["GET"])
@app.route("/pipesense/agent-status", methods=["GET"])
def get_agent_status():
    return jsonify(service.get_agent_status())

@app.route("/thresholds", methods=["GET"])
@app.route("/pipesense/thresholds", methods=["GET"])
def get_thresholds():
    st = service.get_agent_status()
    return jsonify({
        "anomaly_multiplier_threshold": 1.35,
        "night_flow_window": "01:00 - 05:00 IST",
        "verification_tolerance_multiplier": 1.35,
        "critical_leak_multiplier": 3.0,
        "agent_mode": st.get("mode", "local_deterministic"),
        "status_key": st.get("status_key", "local_demo"),
        "bedrock_enabled": st.get("bedrock_enabled", False),
        "bedrock_configured": st.get("bedrock_configured", False),
        "is_simulated": not st.get("bedrock_enabled", False),
        "mode_description": st.get("description", "")
    })

@app.route("/incidents/<incident_id>/investigate", methods=["POST"])
@app.route("/pipesense/incidents/<incident_id>/investigate", methods=["POST"])
def investigate(incident_id: str):
    inc = service.run_investigation(incident_id)
    return jsonify(inc)

@app.route("/incidents/<incident_id>/dispatch", methods=["POST"])
@app.route("/pipesense/incidents/<incident_id>/dispatch", methods=["POST"])
def dispatch(incident_id: str):
    wo = service.dispatch_work_order(incident_id)
    return jsonify(wo)

@app.route("/work-orders/<work_order_id>/complete", methods=["POST"])
def complete_wo(work_order_id: str):
    inc = service.claim_completion(work_order_id)
    return jsonify(inc)

@app.route("/work-orders/<work_order_id>/verify", methods=["POST"])
def verify_wo(work_order_id: str):
    data = request.json or {}
    telemetry = float(data.get("telemetry", 18.2))
    inc = service.verify_repair(work_order_id, telemetry)
    return jsonify(inc)

@app.route("/work-orders/<work_order_id>/repair", methods=["POST"])
def repair_wo(work_order_id: str):
    inc = service.start_second_repair(work_order_id)
    return jsonify(inc)

@app.route("/demo/pipesense/reset", methods=["POST"])
def reset_demo():
    res = service.reset_demo()
    return jsonify(res)

@app.route("/demo/pipesense/run", methods=["POST"])
def run_demo():
    inc = service.detect_anomaly("BLDG-04", 64.2, 18.4)
    service.run_investigation(inc["incident_id"])
    wo = service.dispatch_work_order(inc["incident_id"])
    service.claim_completion(wo["work_order_id"])
    service.verify_repair(wo["work_order_id"], 61.8) # Fails
    service.start_second_repair(wo["work_order_id"])
    service.claim_completion(wo["work_order_id"])
    inc = service.verify_repair(wo["work_order_id"], 18.2) # Passes
    
    with SessionLocal() as db:
        events = db.query(AuditLog).filter_by(target_id=inc["incident_id"]).order_by(AuditLog.timestamp.desc()).all()
        ev_dicts = [service._to_dict(e) for e in events]
    return jsonify({"incident": inc, "events": ev_dicts})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port)

