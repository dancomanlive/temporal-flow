"""Root Orchestrator Activities - Thin adapters that delegate to domain services."""

from typing import Dict, Any, Optional
from pydantic import BaseModel
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.domain.workflow_routing import (
    EventRoutingConfig, 
    DEFAULT_ROUTING_CONFIG
)
from src.domain.services import (
    OrchestratorDomainService
)


class RouteEventParams(BaseModel):
    """Parameters for routing an event to a workflow."""
    
    event: Dict[str, Any]
    routing_config: Optional[Dict[str, Any]] = None


class RouteEventResult(BaseModel):
    """Result of event routing."""
    
    workflow_config: Optional[Dict[str, Any]]
    workflow_name: Optional[str]
    task_queue: Optional[str]
    routed: bool


class ValidateEventParams(BaseModel):
    """Parameters for event validation."""
    
    event: Dict[str, Any]


class ValidateEventResult(BaseModel):
    """Result of event validation."""
    
    valid: bool
    errors: list[str]


class RootOrchestratorActivities:
    """Activities for the Root Orchestrator workflow - Thin adapters to domain services."""
    
    def __init__(self, routing_config: Optional[EventRoutingConfig] = None):
        """Initialize with routing configuration.
        
        Args:
            routing_config: Custom routing configuration, defaults to DEFAULT_ROUTING_CONFIG
        """
        self.routing_config = routing_config or DEFAULT_ROUTING_CONFIG
        # Domain service encapsulates all business logic
        self.domain_service = OrchestratorDomainService(self.routing_config)
    
    @activity.defn
    async def validate_event(self, params: ValidateEventParams) -> ValidateEventResult:
        """Validate an event using domain service - thin adapter pattern.
        
        Args:
            params: Parameters containing the event to validate
            
        Returns:
            ValidateEventResult with validation outcome
        """
        # Handle both Pydantic model and dict input (Temporal serialization)
        if isinstance(params, dict):
            try:
                params = ValidateEventParams(**params)
            except Exception as e:
                # Return domain validation error, not Temporal error
                return ValidateEventResult(valid=False, errors=[f"Invalid parameters: {e}"])
            
        activity.logger.info(f"Validating event: {params.event}")
        
        # DELEGATE TO DOMAIN SERVICE - no business logic in activity
        validation_result = self.domain_service.validation_service.validate_event(params.event)
        
        # Log result (infrastructure concern)
        if validation_result.is_valid:
            activity.logger.info("Event validation passed")
        else:
            activity.logger.warning(f"Event validation failed: {validation_result.errors}")
        
        # Convert domain result to Temporal result (adapter responsibility)
        return ValidateEventResult(
            valid=validation_result.is_valid,
            errors=validation_result.errors
        )
    
    @activity.defn
    async def route_event(self, params: RouteEventParams) -> RouteEventResult:
        """Route an event using domain service - thin adapter pattern.
        
        Args:
            params: Parameters containing the event and optional routing config
            
        Returns:
            RouteEventResult with the target workflow information
            
        Raises:
            ApplicationError: If routing fails or no workflow can handle the event
        """
        # Handle both Pydantic model and dict input (Temporal serialization)
        if isinstance(params, dict):
            try:
                params = RouteEventParams(**params)
            except Exception as e:
                activity.logger.error(f"Invalid routing parameters: {e}")
                raise ApplicationError(f"Invalid routing parameters: {e}", non_retryable=True)
            
        activity.logger.info(f"Routing event: {params.event}")
        
        # Parse custom config if provided
        custom_config = None
        if params.routing_config:
            try:
                custom_config = EventRoutingConfig(**params.routing_config)
            except Exception as e:
                activity.logger.error(f"Invalid routing configuration: {e}")
                raise ApplicationError(f"Invalid routing configuration: {e}", non_retryable=True)
        
        # DELEGATE TO DOMAIN SERVICE - no business logic in activity
        routing_result = self.domain_service.routing_service.route_event(
            params.event, 
            custom_config
        )
        
        # Handle domain result and convert to Temporal concerns
        if routing_result.workflow_config is None:
            event_type = params.event.get("eventType", "unknown")
            source = params.event.get("source", "unknown")
            activity.logger.error(f"Routing failed: {routing_result.routing_decision}")
            raise ApplicationError(
                f"No workflow configured to handle event type '{event_type}' from source '{source}'", 
                non_retryable=True
            )
        
        # Log routing decision (infrastructure concern)
        activity.logger.info(f"Routed to workflow: {routing_result.workflow_config.workflow_name}")
        activity.logger.debug(f"Routing decision: {routing_result.routing_decision} (confidence: {routing_result.confidence})")
        
        # Convert domain result to Temporal result (adapter responsibility)
        return RouteEventResult(
            workflow_config=routing_result.workflow_config.model_dump(),
            workflow_name=routing_result.workflow_config.workflow_name,
            task_queue=routing_result.workflow_config.task_queue,
            routed=True
        )


# Export an instance for the worker to discover
activities_instance = RootOrchestratorActivities()
