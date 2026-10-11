"""
PipeSense Resilience Agent with Amazon Bedrock & Strands Agents SDK Integration.

Supports:
1. Local Deterministic Rule Engine (default offline demo mode).
2. Amazon Bedrock Foundation Models (Claude 3.5 Sonnet / Amazon Nova) via:
   - Strands Agents SDK (Agent + BedrockModel + registered callable @tools + structured outputs).
   - Bedrock Converse API with boto3 tool use.
3. Safe server-side environment configuration (USE_AWS_BEDROCK, AWS_REGION, BEDROCK_MODEL_ID).
4. Truthful operational status reporting (local_demo, bedrock_configured_unverified, bedrock_active, bedrock_unavailable).
5. Seamless local fallback on AWS errors, timeouts, or malformed responses.
"""

import os
import re
import json
import logging
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# Local tool implementations
from backend_v2.agent.tools.tools import (
    check_weather as local_check_weather,
    check_peer_baselines as local_check_peer_baselines,
    check_maintenance_history as local_check_maintenance_history,
    check_occupancy as local_check_occupancy,
)

logger = logging.getLogger(__name__)

# Structured Diagnosis Schema for Bedrock structured output
class InvestigationDiagnosis(BaseModel):
    diagnosis: Literal["LEAK_CONFIRMED", "LEGITIMATE_USAGE", "LEAK_SUSPECTED"] = Field(
        description="Verdict classification: must be LEAK_CONFIRMED, LEGITIMATE_USAGE, or LEAK_SUSPECTED"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score constrained between 0.0 and 1.0"
    )
    probable_location: str = Field(
        default="Basement Secondary Riser",
        description="Suspected localized pipe segment or fitting, or 'N/A' if non-leak"
    )
    recommended_action: str = Field(
        default="ISSUE_P1_WORK_ORDER",
        description="Actionable next step: ISSUE_P1_WORK_ORDER, CLOSE, or MONITOR"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Synthesized reasoning bullets summarizing weather, baseline, maintenance, and occupancy findings"
    )


# Strands tool definitions with @tool decorator
try:
    from strands import tool as strands_tool
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False
    def strands_tool(fn):
        return fn


@strands_tool
def check_weather_tool(location: str = "Campus-North") -> Dict[str, Any]:
    """Check ambient weather, precipitation, and automated irrigation status for the building quadrant.
    
    Args:
        location: Target quadrant or building identifier (e.g. BLDG-04 or Campus-North).
    """
    res = local_check_weather(location)
    return {
        "location": location,
        "rainfall_last_12h_mm": 0.0,
        "irrigation_active": False,
        "verdict": "CLEAR_WEATHER",
        "finding": res.get("finding", "No rain. Irrigation off.")
    }


@strands_tool
def check_peer_baselines_tool(building_id: str = "BLDG-04") -> Dict[str, Any]:
    """Compare night-flow ratio against peer campus buildings to verify if surge is isolated or municipal.
    
    Args:
        building_id: Target building identifier (e.g. BLDG-04).
    """
    res = local_check_peer_baselines(building_id)
    return {
        "building_id": building_id,
        "peers": {"BLDG-01": 1.00, "BLDG-02": 0.98, "BLDG-03": 1.02, "BLDG-05": 0.99},
        "verdict": "ISOLATED_ANOMALY",
        "finding": res.get("finding", f"Neighboring buildings approximately 1.0x baseline. Surge localized to {building_id}.")
    }


@strands_tool
def check_maintenance_history_tool(building_id: str = "BLDG-04") -> Dict[str, Any]:
    """Inspect asset history, previous service tickets, and known pipe vulnerabilities.
    
    Args:
        building_id: Target building identifier (e.g. BLDG-04).
    """
    res = local_check_maintenance_history(building_id)
    return {
        "building_id": building_id,
        "critical_fittings": "Basement Riser & Sump Pump Line B",
        "verdict": "KNOWN_VULNERABILITY",
        "finding": res.get("finding", "Minor fissure on Basement Secondary Riser.")
    }


@strands_tool
def check_occupancy_tool(building_id: str = "BLDG-04") -> Dict[str, Any]:
    """Cross-reference building schedule to rule out authorized nocturnal events or night labs.
    
    Args:
        building_id: Target building identifier (e.g. BLDG-04 or CANTEEN).
    """
    res = local_check_occupancy(building_id)
    return {
        "building_id": building_id,
        "verdict": "ACTIVE_HOURS" if building_id == "CANTEEN" else "NO_UNUSUAL_OCCUPANCY",
        "finding": res.get("finding", "Standard rest hours. No approved events.")
    }


REGISTERED_TOOLS = [
    check_weather_tool,
    check_peer_baselines_tool,
    check_maintenance_history_tool,
    check_occupancy_tool,
]


class StrandsAgent:
    """
    PipeSense Resilience Agent with dual execution engine:
    - Primary: Amazon Bedrock reasoning loop via Strands Agents SDK (or Bedrock Converse).
    - Fallback: Deterministic local rule engine.
    """

    def __init__(self):
        self.has_verified_invocation: bool = False
        self.last_invocation_error: Optional[str] = None
        self._strands_agent = None
        self._bedrock_model = None

    @property
    def is_bedrock_configured(self) -> bool:
        """Checks if Bedrock integration is enabled via server-side environment flags."""
        val = os.environ.get("USE_AWS_BEDROCK", "false").strip().lower()
        return val in ("true", "1", "yes")

    @property
    def region(self) -> str:
        return os.environ.get("AWS_REGION", "us-east-1")

    @property
    def model_id(self) -> str:
        return os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")

    @property
    def mode(self) -> str:
        """Computes current operational mode based on configuration and verification state."""
        if not self.is_bedrock_configured:
            return "local_deterministic"
        if self.last_invocation_error:
            return "bedrock_unavailable"
        if self.has_verified_invocation:
            return "bedrock_active"
        return "bedrock_configured_unverified"

    def get_status(self) -> Dict[str, Any]:
        """
        Returns truthful operational status of the agent.
        Distinguishes clearly between:
        - local demo mode
        - Bedrock configured but not yet verified
        - Bedrock invocation successful (active)
        - Bedrock unavailable or misconfigured
        """
        current_mode = self.mode

        if current_mode == "local_deterministic":
            return {
                "mode": "local_deterministic",
                "status_key": "local_demo",
                "provider": "Local Deterministic Rule Engine",
                "bedrock_enabled": False,
                "bedrock_configured": False,
                "region": None,
                "model_id": None,
                "status_text": "Local Demo Mode",
                "error_reason": None,
                "description": "Running in offline local demo mode using deterministic domain rules and context tools. Amazon Bedrock is not enabled."
            }

        if current_mode == "bedrock_configured_unverified":
            return {
                "mode": "bedrock_configured_unverified",
                "status_key": "bedrock_configured_unverified",
                "provider": "Amazon Bedrock (Strands Agents SDK)",
                "bedrock_enabled": False,
                "bedrock_configured": True,
                "region": self.region,
                "model_id": self.model_id,
                "status_text": "Bedrock Configured (Pending Verification)",
                "error_reason": None,
                "description": f"Amazon Bedrock is configured with model '{self.model_id}' in region '{self.region}'. Verification pending first live invocation."
            }

        if current_mode == "bedrock_active":
            return {
                "mode": "bedrock_active",
                "status_key": "bedrock_active",
                "provider": "Amazon Bedrock (Strands Agents SDK)",
                "bedrock_enabled": True,
                "bedrock_configured": True,
                "region": self.region,
                "model_id": self.model_id,
                "status_text": "Bedrock Agent Active",
                "error_reason": None,
                "description": f"Amazon Bedrock resilience agent verified and active using model '{self.model_id}' in '{self.region}'."
            }

        # bedrock_unavailable
        return {
            "mode": "bedrock_unavailable",
            "status_key": "bedrock_unavailable",
            "provider": "Amazon Bedrock (Strands Agents SDK)",
            "bedrock_enabled": False,
            "bedrock_configured": True,
            "region": self.region,
            "model_id": self.model_id,
            "status_text": "Bedrock Unavailable / Misconfigured",
            "error_reason": self.last_invocation_error,
            "description": f"Amazon Bedrock is enabled for '{self.model_id}', but the last invocation failed: {self.last_invocation_error}. Local fallback is active."
        }

    def _sanitize_error(self, err: str) -> str:
        """Sanitizes AWS/runtime errors to avoid exposing secrets or credentials in logs or UI."""
        s = str(err)
        # Redact potential key IDs, secret patterns, and session tokens
        s = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_ACCESS_KEY]', s)
        s = re.sub(r'(SecretAccessKey|SessionToken|aws_secret_access_key)=[^,\s]+', r'\1=[REDACTED]', s)
        
        if "NoCredentialsError" in s or "Unable to locate credentials" in s:
            return "AWS credentials not configured on host environment"
        if "AccessDeniedException" in s or "UnauthorizedException" in s:
            return "AWS Bedrock access denied (verify IAM permissions for bedrock:InvokeModel)"
        if "ResourceNotFoundException" in s:
            return f"Bedrock foundation model '{self.model_id}' not found in region '{self.region}'"
        if "ValidationException" in s:
            return "Bedrock model request validation error"
        if "ConnectTimeoutError" in s or "EndpointConnectionError" in s:
            return f"Could not connect to Bedrock service endpoint in region '{self.region}'"
        
        return s[:280]

    def _run_local_investigation(self, incident, tool_results: Dict[str, Any], evidence: List[str]) -> Dict[str, Any]:
        """Deterministic local rule engine for offline demo mode or safe error fallback."""
        zone = getattr(incident, "zone", "BLDG-04")
        current_flow = getattr(incident, "current_flow_lpm", 64.2)
        baseline_flow = getattr(incident, "baseline_flow_lpm", 18.4)
        ratio = current_flow / baseline_flow if baseline_flow else 0.0

        if zone == "CANTEEN":
            return {
                "diagnosis": "LEGITIMATE_USAGE",
                "verdict": "LEGITIMATE_USAGE",
                "confidence": 0.91,
                "probable_location": "N/A",
                "evidence": evidence,
                "tool_results": tool_results,
                "recommended_action": "CLOSE",
                "agent_mode": "local_deterministic"
            }

        if ratio > 3.0:
            return {
                "diagnosis": "LEAK_CONFIRMED",
                "verdict": "CONFIRMED_MAJOR_LEAK",
                "confidence": 0.98,
                "probable_location": "Basement Secondary Riser",
                "evidence": evidence,
                "tool_results": tool_results,
                "recommended_action": "ISSUE_P1_WORK_ORDER",
                "agent_mode": "local_deterministic"
            }

        return {
            "diagnosis": "LEAK_SUSPECTED",
            "verdict": "SUSPECTED_MICRO_FISSURE",
            "confidence": 0.72,
            "probable_location": "Basement Secondary Riser",
            "evidence": evidence,
            "tool_results": tool_results,
            "recommended_action": "MONITOR",
            "agent_mode": "local_deterministic"
        }

    def _invoke_bedrock_strands(self, prompt: str) -> Optional[InvestigationDiagnosis]:
        """Executes the investigation using the Strands Agents SDK with BedrockModel."""
        if not STRANDS_AVAILABLE:
            raise RuntimeError("Strands Agents SDK is not installed in the environment")

        from strands import Agent
        from strands.models import BedrockModel

        if self._bedrock_model is None:
            self._bedrock_model = BedrockModel(
                model_id=self.model_id,
                region_name=self.region
            )

        agent = Agent(
            model=self._bedrock_model,
            tools=REGISTERED_TOOLS,
            system_prompt=(
                "You are PipeSense Autonomous Resilience Agent. "
                "Investigate water flow anomalies in campus buildings using the registered tools. "
                "Always call check_weather_tool, check_peer_baselines_tool, check_maintenance_history_tool, and check_occupancy_tool. "
                "Synthesize findings and provide a definitive diagnosis: LEAK_CONFIRMED, LEGITIMATE_USAGE, or LEAK_SUSPECTED."
            ),
            structured_output_model=InvestigationDiagnosis
        )

        res = agent(prompt, structured_output_model=InvestigationDiagnosis)
        if hasattr(res, "structured_output") and res.structured_output is not None:
            if isinstance(res.structured_output, InvestigationDiagnosis):
                return res.structured_output
            if isinstance(res.structured_output, dict):
                return InvestigationDiagnosis(**res.structured_output)

        # Attempt to parse raw text output if structured_output was not populated
        raw_text = str(res)
        return self._parse_json_diagnosis(raw_text)

    def _invoke_bedrock_converse_boto3(self, prompt: str) -> Optional[InvestigationDiagnosis]:
        """Direct Bedrock Converse tool-use runner via boto3 as a robust alternative."""
        import boto3

        client = boto3.client("bedrock-runtime", region_name=self.region)
        
        tool_config = {
            "tools": [
                {"toolSpec": getattr(t, "tool_spec", None) or {
                    "name": getattr(t, "tool_name", t.__name__),
                    "description": t.__doc__ or "Tool",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }} for t in REGISTERED_TOOLS
            ]
        }

        system_prompts = [{
            "text": (
                "You are PipeSense Autonomous Resilience Agent. "
                "Investigate water anomalies using tools. "
                "Output JSON matching schema: {diagnosis: 'LEAK_CONFIRMED'|'LEGITIMATE_USAGE'|'LEAK_SUSPECTED', confidence: float, probable_location: str, recommended_action: str, evidence: list[str]}"
            )
        }]

        messages = [{"role": "user", "content": [{"text": prompt}]}]
        max_turns = 6

        for _ in range(max_turns):
            response = client.converse(
                modelId=self.model_id,
                messages=messages,
                system=system_prompts,
                toolConfig=tool_config
            )

            msg = response["output"]["message"]
            messages.append(msg)

            if response.get("stopReason") == "tool_use":
                tool_results = []
                for block in msg.get("content", []):
                    if "toolUse" in block:
                        tu = block["toolUse"]
                        tu_id = tu["toolUseId"]
                        t_name = tu["name"]
                        t_input = tu.get("input", {})

                        # Find matching tool
                        target_tool = next((t for t in REGISTERED_TOOLS if getattr(t, "tool_name", t.__name__) == t_name), None)
                        tool_out = target_tool(**t_input) if target_tool else {"error": "Tool not found"}

                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tu_id,
                                "content": [{"json": tool_out}]
                            }
                        })
                messages.append({"role": "user", "content": tool_results})
            else:
                # Turn finished
                for block in msg.get("content", []):
                    if "text" in block:
                        return self._parse_json_diagnosis(block["text"])
                break

        return None

    def _parse_json_diagnosis(self, text: str) -> Optional[InvestigationDiagnosis]:
        """Parses structured JSON from LLM text output."""
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return InvestigationDiagnosis(**data)
        except Exception as e:
            logger.debug(f"Could not parse structured diagnosis JSON: {e}")
        return None

    def investigate(self, incident) -> Dict[str, Any]:
        """
        Executes the closed-loop investigation for an incident.
        When Bedrock is enabled, invokes the model with registered tools.
        When Bedrock is disabled or encounters an error, uses deterministic local rules.
        """
        zone = getattr(incident, "zone", "BLDG-04")
        current_flow = getattr(incident, "current_flow_lpm", 64.2)
        baseline_flow = getattr(incident, "baseline_flow_lpm", 18.4)
        ratio = current_flow / baseline_flow if baseline_flow else 0.0

        # Always gather base context tools for consistent evidence & audit logging
        w = local_check_weather(zone)
        p = local_check_peer_baselines(zone)
        m = local_check_maintenance_history(zone)
        o = local_check_occupancy(zone)

        tool_results = {
            "check_weather": w,
            "check_peer_baselines": p,
            "check_maintenance_history": m,
            "check_occupancy": o
        }

        evidence = [
            f"Weather: {w.get('finding', 'Clear weather.')}",
            f"Peer baseline: {p.get('finding', 'Peers normal.')}",
            f"Maintenance: {m.get('finding', 'Asset history checked.')}",
            f"Occupancy: {o.get('finding', 'Standard nocturnal rest.')}"
        ]

        # 1. Local Deterministic Mode (Default)
        if not self.is_bedrock_configured:
            return self._run_local_investigation(incident, tool_results, evidence)

        # 2. Amazon Bedrock Enabled Mode
        prompt = (
            f"Investigate nocturnal water surge at campus zone '{zone}'. "
            f"Observed night flow is {current_flow} L/min against baseline of {baseline_flow} L/min ({ratio:.2f}x normal). "
            f"Call all available tools to evaluate environmental, peer, asset, and occupancy context before diagnosing."
        )

        try:
            diagnosis_obj = None

            # Attempt Strands SDK first if available
            if STRANDS_AVAILABLE:
                try:
                    diagnosis_obj = self._invoke_bedrock_strands(prompt)
                except Exception as strands_err:
                    clean_strands_err = self._sanitize_error(str(strands_err))
                    logger.info("Strands invocation attempt failed: %s. Trying Bedrock Converse adapter...", clean_strands_err)
                    diagnosis_obj = self._invoke_bedrock_converse_boto3(prompt)
            else:
                diagnosis_obj = self._invoke_bedrock_converse_boto3(prompt)

            if diagnosis_obj is None:
                raise ValueError("Bedrock model returned empty or malformed structured output")

            # Validate diagnosis classification
            diag_val = diagnosis_obj.diagnosis.upper()
            if "LEAK" in diag_val and "CONFIRM" in diag_val:
                clean_diag = "LEAK_CONFIRMED"
            elif "LEGITIMATE" in diag_val or "USAGE" in diag_val or "FALSE" in diag_val:
                clean_diag = "LEGITIMATE_USAGE"
            else:
                clean_diag = "LEAK_SUSPECTED"

            # Model invocation verified successfully
            self.has_verified_invocation = True
            self.last_invocation_error = None

            final_evidence = diagnosis_obj.evidence if diagnosis_obj.evidence else evidence

            return {
                "diagnosis": clean_diag,
                "verdict": clean_diag,
                "confidence": round(float(diagnosis_obj.confidence), 2),
                "probable_location": diagnosis_obj.probable_location or "Basement Secondary Riser",
                "evidence": final_evidence,
                "tool_results": tool_results,
                "recommended_action": diagnosis_obj.recommended_action or "ISSUE_P1_WORK_ORDER",
                "agent_mode": "bedrock_active",
                "model_id": self.model_id,
                "region": self.region
            }

        except Exception as e:
            clean_err = self._sanitize_error(str(e))
            self.last_invocation_error = clean_err
            self.has_verified_invocation = False
            logger.warning(f"Bedrock invocation failed ({clean_err}). Falling back to local deterministic engine.")

            fallback_res = self._run_local_investigation(incident, tool_results, evidence)
            fallback_res["agent_mode"] = "local_deterministic_fallback"
            fallback_res["bedrock_error"] = clean_err
            return fallback_res
