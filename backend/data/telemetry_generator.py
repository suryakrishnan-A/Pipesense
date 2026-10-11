import json
import math
import random
from datetime import datetime, timedelta

def generate_water_telemetry(days=7, sample_rate_minutes=15, inject_leak=True):
    """
    Generates 7 days of realistic water meter telemetry for Campus Building 4 (Hostel/Lab).
    - Normal daytime flow: 35-70 L/min (activity peaks morning & evening)
    - Normal nighttime flow (1 AM - 5 AM): 14-22 L/min (baseline: ~18 L/min)
    - Injected Leak: At Day 5 (hour 108), an underground pipe joint ruptures.
      Night flow spikes from 18 L/min to 64 L/min.
    """
    start_time = datetime.now() - timedelta(days=days)
    readings = []
    
    total_samples = int((days * 24 * 60) / sample_rate_minutes)
    leak_start_index = int((4.5 * 24 * 60) / sample_rate_minutes) # Leak begins midway through day 5
    
    for i in range(total_samples):
        timestamp = start_time + timedelta(minutes=i * sample_rate_minutes)
        hour = timestamp.hour
        
        # Base diurnal cycle
        if 1 <= hour <= 5:
            # Deep night: very low background flow (toilets, small leaks)
            base_flow = 16.0 + random.uniform(-2.5, 3.5)
        elif 6 <= hour <= 9:
            # Morning rush
            base_flow = 55.0 + 15.0 * math.sin((hour - 6) * math.pi / 3) + random.uniform(-4, 6)
        elif 10 <= hour <= 17:
            # Regular day activity
            base_flow = 38.0 + random.uniform(-5, 7)
        elif 18 <= hour <= 22:
            # Evening peak
            base_flow = 58.0 + 12.0 * math.sin((hour - 18) * math.pi / 4) + random.uniform(-5, 5)
        else:
            # Late night transition
            base_flow = 25.0 + random.uniform(-3, 3)
            
        # Inject leak
        is_leak_active = inject_leak and (i >= leak_start_index)
        if is_leak_active:
            # Steady continuous baseline loss of ~45 L/min added to all hours
            leak_volume = 44.0 + random.uniform(-2.0, 3.0)
            base_flow += leak_volume
            
        flow_rate = max(2.0, round(base_flow, 2))
        
        readings.append({
            "timestamp": timestamp.isoformat(),
            "building_id": "BLDG-04",
            "building_name": "Satish Dhawan Hostel & Lab Block",
            "flow_rate_lpm": flow_rate,
            "pressure_psi": round(42.0 - (10.0 if is_leak_active else 0.0) + random.uniform(-1.5, 1.5), 1),
            "is_night_window": 1 <= hour <= 5,
            "leak_injected": is_leak_active
        })
        
    return readings

if __name__ == "__main__":
    data = generate_water_telemetry()
    print(f"Generated {len(data)} telemetry records. Sample:")
    print(json.dumps(data[-1], indent=2))
