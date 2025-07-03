"""Domain services - Pure business logic without framework dependencies."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .workflow_routing import WorkflowRouter, WorkflowConfig, EventRoutingConfig


@dataclass
class EventValidationResult:
    """Result of event validation - pure domain model."""
    is_valid: bool
    errors: List[str]
    normalized_event: Optional[Dict[str, Any]] = None


@dataclass 
class RoutingResult:
    """Result of event routing - pure domain model."""
    workflow_config: Optional[WorkflowConfig]
    routing_decision: str  # Why this routing was chosen
    confidence: float = 1.0


class EventValidationService:
    """Pure domain service for event validation - no Temporal dependencies."""
    
    def validate_event(self, event: Any) -> EventValidationResult:
        """Validate an incoming event according to business rules.
        
        Args:
            event: Raw event data
            
        Returns:
            EventValidationResult with validation outcome
        """
        errors = []
        
        # Business rule: Event must be a dictionary
        if not isinstance(event, dict):
            errors.append("Event must be a dictionary")
            return EventValidationResult(is_valid=False, errors=errors)
        
        # Business rule: Event must have eventType (can be empty for defaults)
        if "eventType" not in event:
            errors.append("Event must contain 'eventType' field")
        
        # Business rule: eventType must be string and non-empty
        event_type = event.get("eventType", "")
        if not isinstance(event_type, str):
            errors.append("eventType must be a string")
        elif not event_type.strip():
            errors.append("'eventType' must be a non-empty string")
        
        # Business rule: Source must be string if provided
        source = event.get("source")
        if source is not None and not isinstance(source, str):
            errors.append("'source' field must be a string if present")
        
        # Only normalize if basic types are correct
        if len(errors) == 0:
            normalized_event = {
                "eventType": event_type.strip(),
                "source": source.strip() if source else "",
                **{k: v for k, v in event.items() if k not in ["eventType", "source"]}
            }
        else:
            normalized_event = None
        
        is_valid = len(errors) == 0
        return EventValidationResult(
            is_valid=is_valid,
            errors=errors,
            normalized_event=normalized_event if is_valid else None
        )


class EventRoutingService:
    """Pure domain service for event routing - no Temporal dependencies."""
    
    def __init__(self, default_config: Optional[EventRoutingConfig] = None):
        """Initialize with default routing configuration."""
        self.default_config = default_config
    
    def route_event(
        self, 
        event: Dict[str, Any], 
        custom_config: Optional[EventRoutingConfig] = None
    ) -> RoutingResult:
        """Route an event to appropriate workflow using business logic.
        
        Args:
            event: Validated and normalized event
            custom_config: Optional custom routing configuration
            
        Returns:
            RoutingResult with routing decision
        """
        # Use custom config if provided, otherwise default
        config = custom_config or self.default_config
        if not config:
            return RoutingResult(
                workflow_config=None,
                routing_decision="No routing configuration available"
            )
        
        router = WorkflowRouter(config)
        workflow_config = router.route_event(event)
        
        # Determine routing decision for auditability
        event_type = event.get("eventType", "").lower()
        source = event.get("source", "").lower()
        
        if workflow_config:
            if event_type and event_type in config.event_type_mappings:
                decision = f"Routed by eventType '{event_type}' to {workflow_config.workflow_name}"
                confidence = 1.0
            elif source and source in config.source_mappings:
                decision = f"Routed by source '{source}' to {workflow_config.workflow_name}"
                confidence = 0.8
            elif config.default_workflow:
                decision = f"Routed to default workflow {workflow_config.workflow_name}"
                confidence = 0.5
            else:
                decision = f"Routed to {workflow_config.workflow_name}"
                confidence = 0.7
        else:
            decision = f"No workflow found for eventType '{event_type}' and source '{source}'"
            confidence = 0.0
        
        return RoutingResult(
            workflow_config=workflow_config,
            routing_decision=decision,
            confidence=confidence
        )


class OrchestratorDomainService:
    """Facade service that coordinates all domain operations."""
    
    def __init__(self, routing_config: Optional[EventRoutingConfig] = None):
        """Initialize domain service with configuration."""
        self.validation_service = EventValidationService()
        self.routing_service = EventRoutingService(routing_config)
    
    def process_event_for_routing(
        self, 
        raw_event: Any, 
        custom_config: Optional[EventRoutingConfig] = None
    ) -> tuple[EventValidationResult, Optional[RoutingResult]]:
        """Complete domain operation: validate and route an event.
        
        Args:
            raw_event: Raw incoming event
            custom_config: Optional custom routing configuration
            
        Returns:
            Tuple of (validation_result, routing_result)
        """
        # Step 1: Validate
        validation_result = self.validation_service.validate_event(raw_event)
        
        # Step 2: Route if valid
        routing_result = None
        if validation_result.is_valid:
            routing_result = self.routing_service.route_event(
                validation_result.normalized_event,
                custom_config
            )
        
        return validation_result, routing_result
