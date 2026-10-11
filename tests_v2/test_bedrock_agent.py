"""
Unit and integration tests for PipeSense Amazon Bedrock & Strands agent integration.
Tests all operational modes using mocked responses with ZERO live AWS calls:
1. Local deterministic default mode
2. Bedrock configured but pending verification
3. Successful Bedrock/Strands structured diagnosis with tool evidence
4. Malformed/invalid output fallback
5. AWS client/credentials errors and secret sanitization
6. Dynamic agent-status and thresholds API endpoints
"""

import os
import logging
import pytest
from unittest.mock import MagicMock, patch
import botocore.exceptions
import pydantic

from backend_v2.agent.pipesense_agent import (
    StrandsAgent,
    InvestigationDiagnosis,
    check_weather_tool,
    check_peer_baselines_tool,
    check_maintenance_history_tool,
    check_occupancy_tool
)
from backend_v2.api.main import app


class DummyIncident:
    def __init__(self, zone="BLDG-04", current_flow=64.2, baseline_flow=18.4):
        self.zone = zone
        self.current_flow_lpm = current_flow
        self.baseline_flow_lpm = baseline_flow


def test_default_mode_is_local_deterministic(monkeypatch):
    """Default mode must be local deterministic with zero AWS access."""
    monkeypatch.delenv("USE_AWS_BEDROCK", raising=False)
    agent = StrandsAgent()

    assert agent.is_bedrock_configured is False
    assert agent.mode == "local_deterministic"
    assert agent.has_verified_invocation is False

    status = agent.get_status()
    assert status["status_key"] == "local_demo"
    assert status["bedrock_enabled"] is False
    assert status["bedrock_configured"] is False
    assert status["provider"] == "Local Deterministic Rule Engine"
    assert "Local Demo Mode" in status["status_text"]

    # In local mode, investigation runs offline heuristics
    inc = DummyIncident()
    res = agent.investigate(inc)
    assert res["diagnosis"] == "LEAK_CONFIRMED"
    assert res["agent_mode"] == "local_deterministic"
    assert "check_weather" in res["tool_results"]
    assert "check_peer_baselines" in res["tool_results"]
    assert "check_maintenance_history" in res["tool_results"]
    assert "check_occupancy" in res["tool_results"]


def test_bedrock_configured_unverified_state(monkeypatch):
    """When Bedrock is configured, status is unverified until first real call succeeds."""
    monkeypatch.setenv("USE_AWS_BEDROCK", "true")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")

    agent = StrandsAgent()
    assert agent.is_bedrock_configured is True
    assert agent.has_verified_invocation is False
    assert agent.mode == "bedrock_configured_unverified"

    status = agent.get_status()
    assert status["status_key"] == "bedrock_configured_unverified"
    assert status["bedrock_enabled"] is False  # Safety: MUST NOT claim enabled until verified
    assert status["bedrock_configured"] is True
    assert status["region"] == "us-east-1"
    assert "us.anthropic.claude-3-5-sonnet" in status["model_id"]
    assert "Pending Verification" in status["status_text"]


def test_successful_bedrock_strands_invocation_and_tool_evidence(monkeypatch):
    """Successful mocked Strands agent invocation marks status active and returns structured diagnosis."""
    monkeypatch.setenv("USE_AWS_BEDROCK", "true")
    agent = StrandsAgent()

    mock_diagnosis = InvestigationDiagnosis(
        diagnosis="LEAK_CONFIRMED",
        confidence=0.97,
        probable_location="Basement Secondary Riser Segment B",
        recommended_action="ISSUE_P1_WORK_ORDER",
        reasoning="Night flow is 3.49x baseline. Peer baselines normal, dry weather, known riser fissure.",
        evidence=[
            "Weather: Dry and clear",
            "Peer: Normal baseline across campus",
            "Maintenance: Known micro-fissure on basement riser",
            "Occupancy: Zero authorized nocturnal activities"
        ]
    )

    with patch.object(agent, "_invoke_bedrock_strands", return_value=mock_diagnosis):
        inc = DummyIncident("BLDG-04", 64.2, 18.4)
        result = agent.investigate(inc)

        assert result["diagnosis"] == "LEAK_CONFIRMED"
        assert result["confidence"] == 0.97
        assert result["probable_location"] == "Basement Secondary Riser Segment B"
        assert result["agent_mode"] == "bedrock_active"
        assert len(result["evidence"]) == 4

        # Verify state transition to active
        assert agent.has_verified_invocation is True
        assert agent.mode == "bedrock_active"
        st = agent.get_status()
        assert st["status_key"] == "bedrock_active"
        assert st["bedrock_enabled"] is True
        assert st["bedrock_configured"] is True


def test_bedrock_converse_boto3_fallback_path(monkeypatch):
    """When Strands fails or is unavailable, Bedrock Converse path succeeds."""
    monkeypatch.setenv("USE_AWS_BEDROCK", "true")
    agent = StrandsAgent()

    mock_diagnosis = InvestigationDiagnosis(
        diagnosis="LEAK_CONFIRMED",
        confidence=0.94,
        probable_location="Basement Secondary Riser",
        recommended_action="ISSUE_P1_WORK_ORDER",
        reasoning="Converse tool use confirmed localized pipe fissure.",
        evidence=["Converse verified leak evidence"]
    )

    with patch.object(agent, "_invoke_bedrock_strands", side_effect=Exception("Strands test error")), \
         patch.object(agent, "_invoke_bedrock_converse_boto3", return_value=mock_diagnosis):
        
        inc = DummyIncident("BLDG-04", 64.2, 18.4)
        result = agent.investigate(inc)

        assert result["diagnosis"] == "LEAK_CONFIRMED"
        assert result["confidence"] == 0.94
        assert result["agent_mode"] == "bedrock_active"
        assert agent.has_verified_invocation is True
        assert agent.mode == "bedrock_active"


def test_bedrock_malformed_output_safe_fallback(monkeypatch):
    """Malformed output safely falls back to local deterministic mode without crashing."""
    monkeypatch.setenv("USE_AWS_BEDROCK", "true")
    agent = StrandsAgent()

    with patch.object(agent, "_invoke_bedrock_strands", return_value=None), \
         patch.object(agent, "_invoke_bedrock_converse_boto3", return_value=None):
        
        inc = DummyIncident("BLDG-04", 64.2, 18.4)
        result = agent.investigate(inc)

        # Result is valid local fallback
        assert result["diagnosis"] == "LEAK_CONFIRMED"
        assert result["agent_mode"] == "local_deterministic_fallback"
        assert "bedrock_error" in result

        # Agent state transitioned to bedrock_unavailable
        assert agent.has_verified_invocation is False
        assert agent.mode == "bedrock_unavailable"
        st = agent.get_status()
        assert st["status_key"] == "bedrock_unavailable"
        assert st["bedrock_enabled"] is False
        assert st["error_reason"] is not None


def test_aws_credentials_error_sanitization_and_fallback(monkeypatch):
    """AWS credential and client errors are safely sanitized and do not leak keys."""
    monkeypatch.setenv("USE_AWS_BEDROCK", "true")
    agent = StrandsAgent()

    # Simulate an AWS error containing simulated sensitive tokens
    raw_leak_error = (
        "ClientError: An error occurred (UnrecognizedClientException) when calling InvokeModel: "
        "The security token included in the request is invalid. "
        "AKIAIOSFODNN7EXAMPLE SecretAccessKey=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    )

    # Verify sanitization method directly
    direct_sanitized = agent._sanitize_error(raw_leak_error)
    assert "AKIAIOSFODNN7EXAMPLE" not in direct_sanitized
    assert "wJalrXUtnFEMI" not in direct_sanitized
    assert "[REDACTED_ACCESS_KEY]" in direct_sanitized

    with patch.object(agent, "_invoke_bedrock_strands", side_effect=Exception(raw_leak_error)), \
         patch.object(agent, "_invoke_bedrock_converse_boto3", side_effect=Exception(raw_leak_error)):
        inc = DummyIncident("BLDG-04", 64.2, 18.4)
        result = agent.investigate(inc)

        assert result["agent_mode"] == "local_deterministic_fallback"
        assert agent.mode == "bedrock_unavailable"
        
        st = agent.get_status()
        assert st["status_key"] == "bedrock_unavailable"
        
        # Verify secret sanitization: Raw AKIA and secret MUST NOT be in error reason or status
        err_msg = st["error_reason"]
        assert "AKIAIOSFODNN7EXAMPLE" not in err_msg
        assert "wJalrXUtnFEMI" not in err_msg
        assert "[REDACTED" in err_msg


def test_registered_tools_execute_locally():
    """All 4 registered investigation tools execute cleanly and return typed outputs."""
    w = check_weather_tool("BLDG-04")
    assert "rainfall_last_12h_mm" in w
    assert "finding" in w

    p = check_peer_baselines_tool("BLDG-04")
    assert "verdict" in p
    assert "finding" in p
    assert p["verdict"] == "ISOLATED_ANOMALY"

    m = check_maintenance_history_tool("BLDG-04")
    assert "critical_fittings" in m
    assert "finding" in m
    assert "Basement Riser" in m["critical_fittings"]

    o = check_occupancy_tool("BLDG-04")
    assert "verdict" in o
    assert "finding" in o
    assert "verdict" in o
    assert o["verdict"] == "NO_UNUSUAL_OCCUPANCY"

    # Canteen should reflect active nocturnal hours
    o_canteen = check_occupancy_tool("CANTEEN")
    assert o_canteen["verdict"] == "ACTIVE_HOURS"


def test_api_agent_status_and_thresholds_endpoints():
    """API endpoints return truthful agent status across modes."""
    with app.test_client() as client:
        # 1. Agent status endpoint
        r_status = client.get("/pipesense/agent-status")
        assert r_status.status_code == 200
        st = r_status.json
        assert "status_key" in st
        assert "provider" in st
        assert "bedrock_enabled" in st
        assert "mode" in st

        # 2. Thresholds endpoint
        r_thresh = client.get("/pipesense/thresholds")
        assert r_thresh.status_code == 200
        th = r_thresh.json
        assert th["anomaly_multiplier_threshold"] == 1.35
        assert "night_flow_window" in th
        assert "agent_mode" in th
        assert "status_key" in th


def test_diagnosis_schema_validation_constraints():
    """Verify that diagnosis only accepts the 3 valid verdicts and confidence is constrained to 0.0-1.0."""
    # Valid verdicts and confidence ranges
    d1 = InvestigationDiagnosis(diagnosis="LEAK_CONFIRMED", confidence=0.98)
    assert d1.diagnosis == "LEAK_CONFIRMED"
    assert d1.confidence == 0.98

    d2 = InvestigationDiagnosis(diagnosis="LEGITIMATE_USAGE", confidence=0.0)
    assert d2.diagnosis == "LEGITIMATE_USAGE"
    assert d2.confidence == 0.0

    d3 = InvestigationDiagnosis(diagnosis="LEAK_SUSPECTED", confidence=1.0)
    assert d3.diagnosis == "LEAK_SUSPECTED"
    assert d3.confidence == 1.0

    # Invalid diagnosis classifications must raise ValidationError
    with pytest.raises(pydantic.ValidationError):
        InvestigationDiagnosis(diagnosis="UNKNOWN_VERDICT", confidence=0.5)

    with pytest.raises(pydantic.ValidationError):
        InvestigationDiagnosis(diagnosis="MAYBE_LEAK", confidence=0.8)

    with pytest.raises(pydantic.ValidationError):
        InvestigationDiagnosis(diagnosis="TRUE_LEAK", confidence=0.9)

    # Confidence strictly constrained between 0.0 and 1.0
    with pytest.raises(pydantic.ValidationError):
        InvestigationDiagnosis(diagnosis="LEAK_CONFIRMED", confidence=1.01)

    with pytest.raises(pydantic.ValidationError):
        InvestigationDiagnosis(diagnosis="LEAK_CONFIRMED", confidence=-0.05)

    with pytest.raises(pydantic.ValidationError):
        InvestigationDiagnosis(diagnosis="LEAK_CONFIRMED", confidence=99.0)


def test_schema_validation_error_triggers_local_fallback(monkeypatch):
    """When model structured output violates schema (e.g. invalid verdict or confidence > 1.0), agent falls back safely."""
    monkeypatch.setenv("USE_AWS_BEDROCK", "true")
    agent = StrandsAgent()

    # Simulate raw text output with invalid verdict that fails schema validation
    invalid_schema_text = '{"diagnosis": "INVALID_ANOMALY_TYPE", "confidence": 1.5}'

    with patch.object(agent, "_invoke_bedrock_strands", side_effect=Exception("Pydantic validation failure: invalid diagnosis")), \
         patch.object(agent, "_invoke_bedrock_converse_boto3", side_effect=Exception("Pydantic validation failure: confidence > 1.0")):
        
        inc = DummyIncident("BLDG-04", 64.2, 18.4)
        result = agent.investigate(inc)

        # Fallback executes and returns valid local diagnosis
        assert result["diagnosis"] == "LEAK_CONFIRMED"
        assert result["agent_mode"] == "local_deterministic_fallback"
        assert agent.mode == "bedrock_unavailable"
        assert agent.get_status()["status_key"] == "bedrock_unavailable"


def test_raw_strands_exception_never_logged(monkeypatch, caplog):
    """Ensure raw Strands exception text with tokens or secret keys is never logged."""
    monkeypatch.setenv("USE_AWS_BEDROCK", "true")
    agent = StrandsAgent()

    raw_sensitive_error = (
        "StrandsRuntimeError: Failed with AKIAIOSFODNN7EXAMPLE and "
        "SecretAccessKey=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY on endpoint"
    )

    mock_converse_diagnosis = InvestigationDiagnosis(
        diagnosis="LEAK_CONFIRMED",
        confidence=0.95,
        probable_location="Basement Secondary Riser",
        recommended_action="ISSUE_P1_WORK_ORDER",
        evidence=["Converse verified evidence"]
    )

    with caplog.at_level(logging.INFO):
        with patch.object(agent, "_invoke_bedrock_strands", side_effect=Exception(raw_sensitive_error)), \
             patch.object(agent, "_invoke_bedrock_converse_boto3", return_value=mock_converse_diagnosis):
            
            inc = DummyIncident("BLDG-04", 64.2, 18.4)
            result = agent.investigate(inc)

            # Invocations proceeded via converse adapter
            assert result["diagnosis"] == "LEAK_CONFIRMED"

            # Check all captured log output
            captured = caplog.text
            assert "AKIAIOSFODNN7EXAMPLE" not in captured
            assert "wJalrXUtnFEMI" not in captured
            assert "[REDACTED" in captured
            assert "Strands invocation attempt failed:" in captured
