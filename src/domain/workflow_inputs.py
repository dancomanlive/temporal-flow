"""Workflow input types using dataclasses for type safety and evolution."""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class IncidentWorkflowInput:
    """Input for the incident workflow.
    
    Using a dataclass allows for backwards-compatible evolution by adding
    optional fields without changing the function signature.
    """
    # Core incident information
    incident_id: Optional[str] = None
    source: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    
    # Event metadata
    event_type: Optional[str] = None
    timestamp: Optional[str] = None
    
    # Additional context (for backwards compatibility)
    additional_context: Optional[Dict[str, Any]] = None


@dataclass
class RootOrchestratorInput:
    """Input for the root orchestrator workflow.
    
    This allows the orchestrator to receive structured input while maintaining
    backwards compatibility through optional fields.
    """
    # Event data
    event_payload: Optional[Dict[str, Any]] = None
    
    # Configuration overrides
    configuration: Optional[Dict[str, Any]] = None
    
    # Workflow routing hints
    target_workflow: Optional[str] = None
    force_route: bool = False
    
    # Additional context
    metadata: Optional[Dict[str, Any]] = None
