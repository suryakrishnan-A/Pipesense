"""
DrainPilot Autonomous Investigation Agent.

Deterministic, explainable reasoning component for drainage resilience.
Uses deterministic heuristics over simulated drainage context tools.
Does NOT rely on LLM inference for numerical comparisons or state decisions.
"""

from typing import Dict, Any, List
from backend_v2.domain.models import Incident
from backend_v2.agent.tools.drain_tools import (
    check_catchment_rainfall,
    check_downstream_capacity,
    check_siltation_history,
    check_surface_debris
)

class DrainPilotAgent:
    """
    Evaluates drainage anomalies deterministically by querying four domain-specific
    context tools: catchment rainfall, downstream capacity, siltation history,
    and surface grate obstruction.
    """

    def investigate(self, incident: Incident) -> Dict[str, Any]:
        zone = incident.zone
        
        # 1. Execute the 4 deterministic context checks
        rainfall = check_catchment_rainfall(zone)
        downstream = check_downstream_capacity(zone)
        siltation = check_siltation_history(zone)
        surface = check_surface_debris(zone)
        
        evidence: List[str] = [
            f"Rainfall: {rainfall['finding']}",
            f"Downstream: {downstream['finding']}",
            f"Siltation: {siltation['finding']}",
            f"Surface Grates: {surface['finding']}"
        ]
        
        # 2. Deterministic Rule Hierarchy (explainable decision tree)
        
        # Check A: Downstream backwater saturation
        if downstream.get("backwater_detected", False) or downstream.get("capacity_utilization_pct", 0) >= 85.0:
            suspected_problem = "DOWNSTREAM_BACKWATER_SURCHARGE"
            finding = (
                f"Downstream trunk channel is heavily surcharged ({downstream.get('capacity_utilization_pct', 0)}% capacity). "
                "Water elevation in the local chamber is caused by hydraulic backwater rather than an internal conduit blockage."
            )
            recommended_action = "MONITOR_TRUNK_DISCHARGE"
            confidence = 0.92
            
        # Check B: Surface intake grate obstruction
        elif surface.get("grate_obstruction_pct", 0) >= 60.0:
            suspected_problem = "SURFACE_GRATE_OBSTRUCTION"
            finding = (
                f"Intake grates are severely clogged ({surface.get('grate_obstruction_pct', 0)}% obstruction) "
                f"by {surface.get('debris_type', 'debris')}, preventing storm runoff from entering conveyance channels."
            )
            recommended_action = "DISPATCH_SURFACE_CLEARANCE"
            confidence = 0.94
            
        # Check C: Severe silt sediment buildup in sump
        elif siltation.get("sump_capacity_reduction_pct", 0) >= 40.0 or siltation.get("estimated_silt_depth_cm", 0) >= 30.0:
            suspected_problem = "INTERNAL_SILT_BLOCKAGE"
            finding = (
                f"Chamber sump contains critical sediment accumulation ({siltation.get('estimated_silt_depth_cm', 0)} cm deep, "
                f"{siltation.get('sump_capacity_reduction_pct', 0)}% sump loss), choking chamber discharge flow."
            )
            recommended_action = "DISPATCH_DESILTING_CREW"
            confidence = 0.96
            
        # Check D: Heavy rainfall runoff with clear conduits
        elif rainfall.get("rainfall_rate_mm_per_hr", 0) >= 35.0:
            suspected_problem = "EXTREME_WEATHER_INFLUX"
            finding = (
                f"Intense precipitation ({rainfall.get('rainfall_rate_mm_per_hr', 0)} mm/hr) is generating peak catchment runoff. "
                "Conduits and sumps are operating without physical obstructions."
            )
            recommended_action = "ACTIVATE_ATTENUATION_PUMPS"
            confidence = 0.89
            
        # Check E: Nominal or unconfirmed impedance
        else:
            suspected_problem = "NOMINAL_OR_MINOR_SURCHARGE"
            finding = (
                "Telemetry and contextual indicators show minor fluctuations within baseline storm resilience allowances. "
                "No critical physical blockage identified."
            )
            recommended_action = "CONTINUE_MONITORING"
            confidence = 0.70

        return {
            "finding": finding,
            "evidence": evidence,
            "suspected_problem": suspected_problem,
            "recommended_action": recommended_action,
            "confidence": confidence,
            "confidence_type": "DEMO_ESTIMATE",
            "confidence_disclaimer": "Heuristic benchmark estimate for demonstration; not a validated statistical ML probability.",
            "tools_called": [
                "check_catchment_rainfall",
                "check_downstream_capacity",
                "check_siltation_history",
                "check_surface_debris"
            ]
        }
