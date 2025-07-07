"""Test the new dataclass-based workflow inputs."""

from src.domain.workflow_inputs import IncidentWorkflowInput, RootOrchestratorInput


def test_incident_workflow_input_creation():
    """Test creating IncidentWorkflowInput with various parameters."""
    # Test with full parameters
    input_full = IncidentWorkflowInput(
        incident_id="inc-123",
        source="monitoring",
        severity="high",
        message="Critical system failure",
        event_type="incident",
        timestamp="2025-07-07T10:00:00Z",
        additional_context={"region": "us-east-1"}
    )
    
    assert input_full.incident_id == "inc-123"
    assert input_full.source == "monitoring"
    assert input_full.severity == "high"
    assert input_full.message == "Critical system failure"
    assert input_full.event_type == "incident"
    assert input_full.additional_context["region"] == "us-east-1"
    
    # Test with minimal parameters (all optional)
    input_minimal = IncidentWorkflowInput()
    assert input_minimal.incident_id is None
    assert input_minimal.source is None
    assert input_minimal.additional_context is None


def test_root_orchestrator_input_creation():
    """Test creating RootOrchestratorInput with various parameters."""
    event_payload = {
        "eventType": "incident",
        "source": "monitoring",
        "message": "System alert"
    }
    
    # Test with full parameters
    input_full = RootOrchestratorInput(
        event_payload=event_payload,
        configuration={"timeout": 300},
        target_workflow="incident_workflow",
        force_route=True,
        metadata={"priority": "high"}
    )
    
    assert input_full.event_payload == event_payload
    assert input_full.configuration["timeout"] == 300
    assert input_full.target_workflow == "incident_workflow"
    assert input_full.force_route is True
    assert input_full.metadata["priority"] == "high"
    
    # Test with minimal parameters
    input_minimal = RootOrchestratorInput()
    assert input_minimal.event_payload is None
    assert input_minimal.configuration is None
    assert input_minimal.force_route is False  # Default value


def test_backwards_compatibility():
    """Test that the dataclasses support backwards compatibility."""
    # Test that we can create instances with partial data
    input_partial = IncidentWorkflowInput(
        message="Alert detected",
        additional_context={"legacy_data": True}
    )
    
    assert input_partial.message == "Alert detected"
    assert input_partial.incident_id is None
    assert input_partial.additional_context["legacy_data"] is True


if __name__ == "__main__":
    test_incident_workflow_input_creation()
    test_root_orchestrator_input_creation()
    test_backwards_compatibility()
    print("✅ All workflow input tests passed!")
