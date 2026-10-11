"""
Investigation Tools for Local Deterministic Resilience Agent.
These correspond to the multi-tool context investigation definitions.
Amazon Bedrock and Strands Agent integrations are unimplemented in this build; execution is local and deterministic.
"""

from datetime import datetime

def check_weather(location="Campus-North"):
    """
    Tool: check_weather
    Inspects ambient weather and environmental triggers.
    """
    # Deterministic local evaluation for nocturnal baseline
    is_raining = False
    is_irrigating = False
    
    if is_raining or is_irrigating:
        return {
            "location": location,
            "rainfall_last_12h_mm": 12.5 if is_raining else 0.0,
            "rain_forecast_next_24h_mm": 5.0,
            "temperature_celsius": 22.0,
            "irrigation_active": is_irrigating,
            "verdict": "ENVIRONMENTAL_TRIGGER",
            "analysis": f"Rainfall detected: {is_raining}. Irrigation active: {is_irrigating}. Flow surge is likely environmental."
        }
    
    return {
        "location": location,
        "rainfall_last_12h_mm": 0.0,
        "rain_forecast_next_24h_mm": 2.0,
        "temperature_celsius": 28.5,
        "irrigation_active": False,
        "verdict": "CLEAR_WEATHER",
        "analysis": "No rainfall detected in the past 12 hours. Scheduled irrigation valves are OFF. Flow surge cannot be attributed to weather or landscaping systems."
    }

def check_peer_baselines(target_building_id="BLDG-04"):
    """
    Tool: check_peer_baselines
    Compares the target building's night flow against peer campus blocks.
    Deterministic nominal readings around 1.0x baseline.
    """
    peer_data = [
        {"building_id": "BLDG-01", "ratio": 1.00, "status": "NORMAL"},
        {"building_id": "BLDG-02", "ratio": 0.98, "status": "NORMAL"},
        {"building_id": "BLDG-03", "ratio": 1.02, "status": "NORMAL"},
        {"building_id": "BLDG-05", "ratio": 0.99, "status": "NORMAL"}
    ]
        
    return {
        "target_building_id": target_building_id,
        "target_surge_ratio": 3.49,
        "peers": peer_data,
        "verdict": "ISOLATED_ANOMALY",
        "analysis": f"All peer buildings show normal night flow ratios (0.95x - 1.05x). Only {target_building_id} shows a severe surge. This confirms a localized physical pipe breach rather than campus-wide supply fluctuation."
    }

def check_maintenance_history(building_id="BLDG-04"):
    """
    Tool: check_maintenance_history
    Inspects historical maintenance logs, asset age, and recent service tickets.
    """
    logs = [
        {"date": "2026-08-15", "component": "Ground Floor Restroom Valve", "status": "Replaced gasket", "priority": "P3"},
        {"date": "2026-09-02", "component": "Basement Secondary Riser Joint", "status": "Identified micro-fissure; flagged for overhaul", "priority": "P2"},
    ]
    return {
        "building_id": building_id,
        "pipe_material": "GI Schedule 40 (Installed 2017)",
        "critical_fittings": "Basement Riser & Sump Pump Line B",
        "previous_tickets": logs,
        "recurrence_risk": "HIGH",
        "verdict": "KNOWN_VULNERABILITY",
        "analysis": f"{building_id} Basement Secondary Riser was flagged with minor fissure on Sept 2 without full replacement. High probability of joint rupture at high nocturnal pump pressure."
    }

def check_occupancy(building_id="BLDG-04"):
    """
    Tool: check_occupancy
    Verifies campus events, hostel occupancy, night laboratory sessions.
    Evaluates nocturnal sleep window (01:00 - 05:00 IST) for night leak anomalies.
    """
    if building_id == "CANTEEN":
        return {
            "building_id": building_id,
            "verdict": "ACTIVE_HOURS",
            "analysis": "Canteen kitchen prep in operation. High water usage expected."
        }

    return {
        "building_id": building_id,
        "current_time_slot": "Night/Sleep Window (02:45 IST)",
        "is_exam_period": False,
        "scheduled_night_labs": 0,
        "estimated_active_occupants": 8,
        "verdict": "NO_UNUSUAL_OCCUPANCY",
        "analysis": "Normal sleeping hours in hostel wing. No all-night robotics lab sessions registered. Expected human consumption should not exceed 20 L/min."
    }

# Tool mapping registry
TOOL_REGISTRY = {
    "check_weather": check_weather,
    "check_peer_baselines": check_peer_baselines,
    "check_maintenance_history": check_maintenance_history,
    "check_occupancy": check_occupancy
}
