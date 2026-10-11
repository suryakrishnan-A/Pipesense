"""
DrainPilot API Routes.

Flask Blueprint providing drainage-specific operational endpoints:
- POST /drainpilot/detect: Ingest telemetry and detect drainage anomalies.
- GET  /drainpilot/incidents: List only DrainPilot incidents.
- GET  /drainpilot/incidents/<incident_id>: Get a single DrainPilot incident.
- POST /drainpilot/incidents/<incident_id>/investigate: Trigger autonomous investigation.
- POST /drainpilot/incidents/<incident_id>/dispatch: Dispatch maintenance crew for an incident.
- GET  /drainpilot/work-orders: List only DrainPilot work orders.
- GET  /drainpilot/work-orders/<work_order_id>: Retrieve a single DrainPilot work order.
- POST /drainpilot/work-orders/<work_order_id>/complete: Record technician maintenance completion.
- POST /drainpilot/work-orders/<work_order_id>/verify: Submit post-maintenance telemetry for resolution verification.
- POST /drainpilot/work-orders/<work_order_id>/repair: Initiate second repair attempt after escalation.
- GET  /drainpilot/summary: Query operational metrics for drainage.

All endpoints strictly identify simulated benchmark data.
System isolation is enforced across all operations.
"""

from flask import Blueprint, jsonify, request
from dataclasses import asdict

from backend_v2.services.drainpilot_service import DrainPilotService
from backend_v2.repository.db import db
from backend_v2.domain.models import IncidentState

drain_blueprint = Blueprint("drainpilot", __name__)
drain_service = DrainPilotService()

# ----------------------------------------------------------------------
# 1. Anomaly Detection & Incident Querying
# ----------------------------------------------------------------------

@drain_blueprint.route("/drainpilot/detect", methods=["POST"])
def detect_drain_anomaly():
    """
    Accepts and validates drainage telemetry.
    Returns:
    - 201 with created incident details if an anomaly/overflow risk is detected.
    - 200 with nominal status if all metrics are within safe thresholds.
    - 400 with an error description if telemetry is malformed or invalid.
    """
    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "error": "Malformed or missing JSON body",
            "is_simulated": True
        }), 400

    try:
        inc = drain_service.detect_anomaly(data)
    except ValueError as err:
        return jsonify({
            "error": str(err),
            "is_simulated": True
        }), 400

    if inc:
        response_data = asdict(inc)
        response_data["status"] = "ANOMALY_DETECTED"
        response_data["is_simulated"] = True
        return jsonify(response_data), 201

    return jsonify({
        "status": "NOMINAL",
        "message": "Drainage telemetry within safe operating parameters. No anomaly detected.",
        "is_simulated": True,
        "data_origin": "SIMULATED_BENCHMARK_TELEMETRY"
    }), 200


@drain_blueprint.route("/drainpilot/incidents", methods=["GET"])
def list_drain_incidents():
    """
    Lists only incidents belonging to the DrainPilot system (system == 'DRAIN').
    Maintains system isolation from PipeSense water-loss incidents.
    """
    drain_incidents = [
        asdict(i) for i in db.incidents.values()
        if getattr(i, "system", None) == "DRAIN"
    ]
    return jsonify(drain_incidents), 200


@drain_blueprint.route("/drainpilot/incidents/<incident_id>", methods=["GET"])
def get_drain_incident(incident_id: str):
    """
    Retrieves a single incident only if it belongs to the DrainPilot system.
    Returns 404 if the incident does not exist or belongs to another system.
    """
    inc = db.get_incident(incident_id)
    if not inc or getattr(inc, "system", None) != "DRAIN":
        return jsonify({
            "error": f"Drainage incident '{incident_id}' not found",
            "is_simulated": True
        }), 404

    return jsonify(asdict(inc)), 200


@drain_blueprint.route("/drainpilot/incidents/<incident_id>/investigate", methods=["POST"])
def investigate_drain_incident(incident_id: str):
    """
    Executes autonomous investigation on an existing DrainPilot anomaly.
    Validates state transitions (incident must be in ANOMALY state) and
    prevents cross-system execution on PipeSense incidents.
    """
    inc = db.get_incident(incident_id)
    if not inc:
        return jsonify({
            "error": f"Incident '{incident_id}' not found",
            "is_simulated": True
        }), 404

    if getattr(inc, "system", None) != "DRAIN":
        return jsonify({
            "error": f"Incident '{incident_id}' belongs to system '{inc.system}', not 'DRAIN'",
            "is_simulated": True
        }), 400

    if inc.state != IncidentState.ANOMALY:
        return jsonify({
            "error": f"Invalid state transition: incident must be in ANOMALY state (current: {inc.state})",
            "is_simulated": True
        }), 409

    try:
        updated_inc = drain_service.run_investigation(incident_id)
        return jsonify(asdict(updated_inc)), 200
    except ValueError as err:
        return jsonify({
            "error": str(err),
            "is_simulated": True
        }), 400


# ----------------------------------------------------------------------
# 2. Work Order Dispatch & Maintenance Operations
# ----------------------------------------------------------------------

@drain_blueprint.route("/drainpilot/incidents/<incident_id>/dispatch", methods=["POST"])
def dispatch_drain_work_order(incident_id: str):
    """
    Dispatches a Priority 1/2 maintenance work order for a DrainPilot incident.
    Assigns crew to Drainage & Civils specialist and transitions incident to WORK_ORDER_ISSUED.
    """
    inc = db.get_incident(incident_id)
    if not inc:
        return jsonify({
            "error": f"Incident '{incident_id}' not found",
            "is_simulated": True
        }), 404

    if getattr(inc, "system", None) != "DRAIN":
        return jsonify({
            "error": f"Incident '{incident_id}' belongs to system '{inc.system}', not 'DRAIN'",
            "is_simulated": True
        }), 400

    if inc.state not in [IncidentState.INVESTIGATING, IncidentState.ANOMALY]:
        return jsonify({
            "error": f"Invalid state transition: incident must be in INVESTIGATING or ANOMALY state (current: {inc.state})",
            "is_simulated": True
        }), 409

    try:
        wo = drain_service.dispatch_work_order(incident_id)
        response_data = asdict(wo)
        response_data["is_simulated"] = True
        return jsonify(response_data), 201
    except ValueError as err:
        return jsonify({
            "error": str(err),
            "is_simulated": True
        }), 400


@drain_blueprint.route("/drainpilot/work-orders", methods=["GET"])
def list_drain_work_orders():
    """
    Lists only work orders created for DrainPilot incidents.
    Maintains system isolation from PipeSense plumbing work orders.
    """
    drain_work_orders = []
    for wo in db.work_orders.values():
        inc = db.get_incident(wo.incident_id)
        if inc and getattr(inc, "system", None) == "DRAIN":
            drain_work_orders.append(asdict(wo))
    return jsonify(drain_work_orders), 200


@drain_blueprint.route("/drainpilot/work-orders/<work_order_id>", methods=["GET"])
def get_drain_work_order(work_order_id: str):
    """
    Retrieves a single DrainPilot work order by ID.
    Returns 404 if the work order does not exist or belongs to another system.
    """
    wo = db.get_work_order(work_order_id)
    if not wo:
        return jsonify({
            "error": f"Drainage work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    inc = db.get_incident(wo.incident_id)
    if not inc or getattr(inc, "system", None) != "DRAIN":
        return jsonify({
            "error": f"Drainage work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    return jsonify(asdict(wo)), 200


@drain_blueprint.route("/drainpilot/work-orders/<work_order_id>/complete", methods=["POST"])
def complete_drain_work_order(work_order_id: str):
    """
    Records technician-reported maintenance completion claim.
    Transitions incident state to VERIFYING. Does NOT automatically close the incident.
    """
    wo = db.get_work_order(work_order_id)
    if not wo:
        return jsonify({
            "error": f"Work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    inc = db.get_incident(wo.incident_id)
    if not inc:
        return jsonify({
            "error": f"Incident linked to work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    if getattr(inc, "system", None) != "DRAIN":
        return jsonify({
            "error": f"Work order '{work_order_id}' belongs to system '{inc.system}', not 'DRAIN'",
            "is_simulated": True
        }), 400

    if inc.state not in [IncidentState.WORK_ORDER_ISSUED, IncidentState.REPAIRING]:
        return jsonify({
            "error": f"Invalid state transition: incident must be in WORK_ORDER_ISSUED or REPAIRING state (current: {inc.state})",
            "is_simulated": True
        }), 409

    try:
        updated_inc = drain_service.claim_completion(work_order_id)
        response_data = asdict(updated_inc)
        response_data["is_simulated"] = True
        return jsonify(response_data), 200
    except ValueError as err:
        return jsonify({
            "error": str(err),
            "is_simulated": True
        }), 400


@drain_blueprint.route("/drainpilot/work-orders/<work_order_id>/verify", methods=["POST"])
def verify_drain_work_order(work_order_id: str):
    """
    Submits post-maintenance drainage telemetry for resolution verification.
    Compares telemetry against drainage acceptance criteria:
    - If criteria fail: incident transitions to ESCALATED, work order assigned to Senior Supervisor.
    - If criteria pass: incident transitions to CLOSED, verified headroom/capacity recorded.
    """
    wo = db.get_work_order(work_order_id)
    if not wo:
        return jsonify({
            "error": f"Work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    inc = db.get_incident(wo.incident_id)
    if not inc:
        return jsonify({
            "error": f"Incident linked to work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    if getattr(inc, "system", None) != "DRAIN":
        return jsonify({
            "error": f"Work order '{work_order_id}' belongs to system '{inc.system}', not 'DRAIN'",
            "is_simulated": True
        }), 400

    if inc.state != IncidentState.VERIFYING:
        return jsonify({
            "error": f"Invalid state transition: incident must be in VERIFYING state to verify (current: {inc.state})",
            "is_simulated": True
        }), 409

    data = request.get_json(silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            "error": "Missing or malformed JSON verification telemetry payload",
            "is_simulated": True
        }), 400

    try:
        updated_inc = drain_service.verify_resolution(work_order_id, data)
        response_data = asdict(updated_inc)
        response_data["is_simulated"] = True
        return jsonify(response_data), 200
    except ValueError as err:
        return jsonify({
            "error": str(err),
            "is_simulated": True
        }), 400


@drain_blueprint.route("/drainpilot/work-orders/<work_order_id>/repair", methods=["POST"])
def repair_drain_work_order(work_order_id: str):
    """
    Initiates a second maintenance attempt after a failed verification.
    Requires incident to be in ESCALATED state. Transitions state to REPAIRING.
    """
    wo = db.get_work_order(work_order_id)
    if not wo:
        return jsonify({
            "error": f"Work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    inc = db.get_incident(wo.incident_id)
    if not inc:
        return jsonify({
            "error": f"Incident linked to work order '{work_order_id}' not found",
            "is_simulated": True
        }), 404

    if getattr(inc, "system", None) != "DRAIN":
        return jsonify({
            "error": f"Work order '{work_order_id}' belongs to system '{inc.system}', not 'DRAIN'",
            "is_simulated": True
        }), 400

    if inc.state != IncidentState.ESCALATED:
        return jsonify({
            "error": f"Invalid state transition: incident must be in ESCALATED state to start second repair (current: {inc.state})",
            "is_simulated": True
        }), 409

    try:
        updated_inc = drain_service.start_second_repair(work_order_id)
        response_data = asdict(updated_inc)
        response_data["is_simulated"] = True
        return jsonify(response_data), 200
    except ValueError as err:
        return jsonify({
            "error": str(err),
            "is_simulated": True
        }), 400


# ----------------------------------------------------------------------
# 3. Operational Summary
# ----------------------------------------------------------------------

@drain_blueprint.route("/drainpilot/summary", methods=["GET"])
def get_drain_summary():
    """
    Returns drainage-only operational metrics from the shared database.
    """
    return jsonify(drain_service.get_summary()), 200
