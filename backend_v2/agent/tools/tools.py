def check_weather(zone="BLDG-04"):
    if zone == "BLDG-04":
        return {"finding": "No rain. Irrigation off."}
    return {"finding": "Light rain. Irrigation off."}

def check_peer_baselines(zone="BLDG-04"):
    if zone == "BLDG-04":
        return {"finding": "Neighboring buildings approximately 1.0x baseline."}
    return {"finding": "Peers elevated."}

def check_maintenance_history(zone="BLDG-04"):
    if zone == "BLDG-04":
        return {"finding": "Minor fissure on Basement Secondary Riser."}
    return {"finding": "No known vulnerabilities."}

def check_occupancy(zone="BLDG-04"):
    if zone == "CANTEEN":
        return {"finding": "Kitchen operation. Approved high usage."}
    return {"finding": "Standard rest hours. No approved events."}
