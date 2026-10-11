import os
import time
from flask import Flask, jsonify, request, render_template

# Ensure project root is in path
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.data.campus_db import store
from backend.agent.bedrock_agent import BedrockResilienceAgent
from backend.engine.dispatcher import dispatcher
from backend.engine.verifier import verifier

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/trigger-anomaly', methods=['POST'])
def trigger_anomaly():
    telemetry_alert = {
        "building_id": "BLDG-04",
        "building_name": "Satish Dhawan Hostel & Lab Block",
        "flow_rate_lpm": 64.2,
        "baseline_lpm": 18.4,
        "timestamp": "02:45:00 IST",
        "spike_multiplier": 3.49
    }
    
    incident = store.create_incident(
        incident_type="WATER_LEAK_SURGE",
        building_id="BLDG-04",
        title="Critical Night Flow Surge in Satish Dhawan Block",
        details=f"Flow sustained at {telemetry_alert['flow_rate_lpm']} L/min during 01:00-05:00 sleep window."
    )
    
    # Save the alert into the store for later retrieval
    store.incidents[incident['incident_id']]['telemetry_alert'] = telemetry_alert
    
    return jsonify({
        "incident": incident,
        "telemetry": telemetry_alert
    })

@app.route('/api/investigate/<incident_id>', methods=['POST'])
def investigate(incident_id):
    incident = store.incidents.get(incident_id)
    if not incident:
        return jsonify({"error": "Incident not found"}), 404
        
    telemetry_alert = incident.get('telemetry_alert', {})
    
    agent = BedrockResilienceAgent()
    diagnosis = agent.run_investigation(incident_id, telemetry_alert)
    
    # Update incident with diagnosis
    store.incidents[incident_id]['diagnosis'] = diagnosis
    
    return jsonify({
        "diagnosis": diagnosis,
        "logs": store.incidents[incident_id].get('investigation_log', [])
    })

@app.route('/api/dispatch/<incident_id>', methods=['POST'])
def dispatch(incident_id):
    incident = store.incidents.get(incident_id)
    if not incident:
        return jsonify({"error": "Incident not found"}), 404
        
    diagnosis = incident.get('diagnosis', {})
    
    dispatch_res = dispatcher.dispatch_leak_repair(incident_id, diagnosis)
    return jsonify(dispatch_res)

@app.route('/api/verify/<incident_id>', methods=['POST'])
def verify(incident_id):
    data = request.json
    flow_rate = data.get('flow_rate', 18.2)
    
    verif = verifier.verify_repair(incident_id, flow_rate)
    return jsonify(verif)

if __name__ == '__main__':
    # Setup initial mock data if needed
    app.run(host='0.0.0.0', port=5000, debug=True)
