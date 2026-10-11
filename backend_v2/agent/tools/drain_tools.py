"""
Drainage Context Tools for DrainPilot Autonomous Resilience Agent.

All data returned by these tools is strictly simulated benchmark data for
hackathon demonstration and scenario modeling.
Physical sensors, external CCTV cameras, and live meteorological APIs
are NOT connected.
"""

from typing import Dict, Any

def check_catchment_rainfall(zone: str = "DRAIN-NORTH-01") -> Dict[str, Any]:
    """
    Evaluates simulated precipitation and catchment runoff conditions.
    Distinguishes dry conditions, moderate rain, and severe downpours.
    """
    if zone in ["DRAIN-NORTH-01", "CULVERT-BLDG-04", "DRAIN-CRITICAL-01"]:
        # Dry catchment scenario: local buildup is NOT weather-driven
        return {
            "zone": zone,
            "rainfall_rate_mm_per_hr": 0.0,
            "accumulated_past_3h_mm": 1.2,
            "weather_condition": "DRY",
            "finding": "Simulated catchment rain gauge indicates dry conditions (0.0 mm/hr). Influx is not caused by recent rainfall.",
            "is_simulated": True,
            "data_origin": "SIMULATED_WEATHER_MODEL",
            "disclaimer": "Simulated operational data. Physical meteorological sensors are not connected."
        }
    elif zone == "DRAIN-STORM-EAST":
        # Heavy storm runoff scenario
        return {
            "zone": zone,
            "rainfall_rate_mm_per_hr": 48.0,
            "accumulated_past_3h_mm": 72.5,
            "weather_condition": "HEAVY_STORM",
            "finding": "Simulated precipitation indicates severe storm conditions (48.0 mm/hr, 72.5 mm in past 3h). Heavy catchment runoff expected.",
            "is_simulated": True,
            "data_origin": "SIMULATED_WEATHER_MODEL",
            "disclaimer": "Simulated operational data. Physical meteorological sensors are not connected."
        }
    else:
        # Moderate baseline rain
        return {
            "zone": zone,
            "rainfall_rate_mm_per_hr": 8.0,
            "accumulated_past_3h_mm": 12.0,
            "weather_condition": "LIGHT_RAIN",
            "finding": "Simulated precipitation indicates light rain (8.0 mm/hr). Influx is within standard wet-weather conveyance allowances.",
            "is_simulated": True,
            "data_origin": "SIMULATED_WEATHER_MODEL",
            "disclaimer": "Simulated operational data. Physical meteorological sensors are not connected."
        }


def check_downstream_capacity(zone: str = "DRAIN-NORTH-01") -> Dict[str, Any]:
    """
    Evaluates simulated downstream conveyance capacity to rule out or identify
    hydraulic backwater effects and municipal trunk saturation.
    """
    if zone in ["DRAIN-NORTH-01", "CULVERT-BLDG-04", "DRAIN-CRITICAL-01"]:
        # Free-flowing downstream trunk
        return {
            "zone": zone,
            "downstream_trunk_id": "TRUNK-MAIN-NORTH",
            "capacity_utilization_pct": 24.0,
            "flow_velocity_mps": 1.45,
            "backwater_detected": False,
            "finding": "Simulated downstream trunk channel is at 24% capacity with free gravity flow (1.45 m/s). Downstream backwater ruled out.",
            "is_simulated": True,
            "data_origin": "SIMULATED_HYDRODYNAMIC_MODEL",
            "disclaimer": "Simulated operational data. Physical flow sensors are not connected."
        }
    elif zone == "DRAIN-OUTFALL-RIVER":
        # Surcharged trunk creating backwater
        return {
            "zone": zone,
            "downstream_trunk_id": "MUNICIPAL-OUTFALL-01",
            "capacity_utilization_pct": 94.0,
            "flow_velocity_mps": 0.20,
            "backwater_detected": True,
            "finding": "Simulated downstream outfall is surcharged at 94% capacity with stagnant velocity (0.20 m/s), creating severe hydraulic backwater into feeder sumps.",
            "is_simulated": True,
            "data_origin": "SIMULATED_HYDRODYNAMIC_MODEL",
            "disclaimer": "Simulated operational data. Physical flow sensors are not connected."
        }
    else:
        # Standard capacity
        return {
            "zone": zone,
            "downstream_trunk_id": "TRUNK-FEEDER-DEFAULT",
            "capacity_utilization_pct": 45.0,
            "flow_velocity_mps": 1.10,
            "backwater_detected": False,
            "finding": "Simulated downstream trunk is operating within nominal capacity (45% utilization).",
            "is_simulated": True,
            "data_origin": "SIMULATED_HYDRODYNAMIC_MODEL",
            "disclaimer": "Simulated operational data. Physical flow sensors are not connected."
        }


def check_siltation_history(zone: str = "DRAIN-NORTH-01") -> Dict[str, Any]:
    """
    Evaluates simulated historical desilting maintenance records and sump
    sediment accumulation estimates.
    """
    if zone in ["DRAIN-NORTH-01", "CULVERT-BLDG-04", "DRAIN-CRITICAL-01"]:
        # Heavy silt buildup scenario
        return {
            "zone": zone,
            "days_since_last_desilting": 210,
            "estimated_silt_depth_cm": 42.0,
            "sump_capacity_reduction_pct": 52.5,
            "maintenance_flag": "OVERDUE_DESILTING",
            "finding": "Simulated maintenance registry indicates sump was last desilted 210 days ago. Estimated sediment depth is 42.0 cm (52.5% reduction in chamber capacity).",
            "is_simulated": True,
            "data_origin": "SIMULATED_MAINTENANCE_REGISTRY",
            "disclaimer": "Simulated operational data. Silt depth sensors are not connected."
        }
    elif zone == "DRAIN-CENTRAL-NEW":
        # Recently desilted
        return {
            "zone": zone,
            "days_since_last_desilting": 14,
            "estimated_silt_depth_cm": 3.0,
            "sump_capacity_reduction_pct": 3.5,
            "maintenance_flag": "RECENTLY_CLEARED",
            "finding": "Simulated maintenance records confirm full desilting completed 14 days ago. Minimal sediment accumulation (3.0 cm).",
            "is_simulated": True,
            "data_origin": "SIMULATED_MAINTENANCE_REGISTRY",
            "disclaimer": "Simulated operational data. Silt depth sensors are not connected."
        }
    else:
        # Moderate silt
        return {
            "zone": zone,
            "days_since_last_desilting": 90,
            "estimated_silt_depth_cm": 15.0,
            "sump_capacity_reduction_pct": 18.0,
            "maintenance_flag": "SCHEDULED_MAINTENANCE_CURRENT",
            "finding": "Simulated maintenance records show routine desilting 90 days ago with moderate silt accumulation (15.0 cm).",
            "is_simulated": True,
            "data_origin": "SIMULATED_MAINTENANCE_REGISTRY",
            "disclaimer": "Simulated operational data. Silt depth sensors are not connected."
        }


def check_surface_debris(zone: str = "DRAIN-NORTH-01") -> Dict[str, Any]:
    """
    Evaluates simulated intake surface condition and grate blockage by debris.
    """
    if zone == "DRAIN-CANTEEN-GRATE":
        # Heavy surface trash / food waste / foliage
        return {
            "zone": zone,
            "grate_obstruction_pct": 80.0,
            "debris_type": "URBAN_LITTER_AND_LEAVES",
            "grate_condition": "SEVERE_OBSTRUCTION",
            "finding": "Simulated surface visual survey indicates 80% surface grate obstruction from accumulated foliage and litter over intake grates.",
            "is_simulated": True,
            "data_origin": "SIMULATED_SURFACE_SURVEY",
            "disclaimer": "Simulated operational data. CCTV/optical camera systems are not connected."
        }
    elif zone in ["DRAIN-NORTH-01", "CULVERT-BLDG-04", "DRAIN-CRITICAL-01"]:
        # Moderate or minor grate debris
        return {
            "zone": zone,
            "grate_obstruction_pct": 15.0,
            "debris_type": "MINIMAL_LEAF_LITTER",
            "grate_condition": "CLEAR",
            "finding": "Simulated surface intake is mostly clear (15% minor leaf litter). Surface intake restriction is ruled out.",
            "is_simulated": True,
            "data_origin": "SIMULATED_SURFACE_SURVEY",
            "disclaimer": "Simulated operational data. CCTV/optical camera systems are not connected."
        }
    else:
        return {
            "zone": zone,
            "grate_obstruction_pct": 10.0,
            "debris_type": "NONE",
            "grate_condition": "CLEAR",
            "finding": "Simulated surface grates are clear and unobstructed.",
            "is_simulated": True,
            "data_origin": "SIMULATED_SURFACE_SURVEY",
            "disclaimer": "Simulated operational data. CCTV/optical camera systems are not connected."
        }
