"""Tests for domain services - Pure business logic testing."""

from src.domain.services import (
    EventValidationService,
    EventRoutingService, 
    OrchestratorDomainService
)
from src.domain.workflow_routing import (
    EventRoutingConfig,
    WorkflowConfig,
    DEFAULT_ROUTING_CONFIG
)


class TestEventValidationService:
    """Test pure domain validation logic without Temporal dependencies."""
    
    def test_validate_valid_event(self):
        """
        GIVEN a valid event
        WHEN validation service validates it
        THEN it should return valid result with normalized event.
        """
        service = EventValidationService()
        
        event = {
            "eventType": "document-added",
            "source": "monitoring",
            "message": "Test document"
        }
        
        result = service.validate_event(event)
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.normalized_event["eventType"] == "document-added"
        assert result.normalized_event["source"] == "monitoring"
        assert result.normalized_event["message"] == "Test document"
    
    def test_validate_missing_event_type(self):
        """
        GIVEN an event missing eventType
        WHEN validation service validates it
        THEN it should return invalid result.
        """
        service = EventValidationService()
        
        event = {"source": "s3"}
        
        result = service.validate_event(event)
        
        assert result.is_valid is False
        assert "Event must contain 'eventType' field" in result.errors
        assert result.normalized_event is None
    
    def test_validate_non_dict_event(self):
        """
        GIVEN a non-dictionary event
        WHEN validation service validates it
        THEN it should return invalid result.
        """
        service = EventValidationService()
        
        result = service.validate_event("not a dict")
        
        assert result.is_valid is False
        assert "Event must be a dictionary" in result.errors
        assert result.normalized_event is None


class TestEventRoutingService:
    """Test pure domain routing logic without Temporal dependencies."""
    
    def test_route_by_event_type(self):
        """
        GIVEN a routing service with default config
        WHEN routing a document event
        THEN it should route to document processing workflow.
        """
        service = EventRoutingService(DEFAULT_ROUTING_CONFIG)
        
        event = {
            "eventType": "document-added",
            "source": "monitoring"
        }
        
        result = service.route_event(event)
        
        assert result.workflow_config is not None
        assert result.workflow_config.workflow_name == "document_processing_workflow"
        assert "Routed by eventType 'document-added'" in result.routing_decision
        assert result.confidence == 1.0
    
    def test_route_by_source_fallback(self):
        """
        GIVEN a routing service with default config
        WHEN routing an unknown event from s3
        THEN it should route to document workflow via source mapping.
        """
        service = EventRoutingService(DEFAULT_ROUTING_CONFIG)
        
        event = {
            "eventType": "unknown-event",
            "source": "s3"
        }
        
        result = service.route_event(event)
        
        assert result.workflow_config is not None
        assert result.workflow_config.workflow_name == "document_processing_workflow"
        assert "Routed by source 's3'" in result.routing_decision
        assert result.confidence == 0.8
    
    def test_route_no_match(self):
        """
        GIVEN a routing service with no default workflow
        WHEN routing an unmatchable event
        THEN it should return no workflow.
        """
        config = EventRoutingConfig(
            event_type_mappings={},
            source_mappings={},
            default_workflow=None,
            workflows={}
        )
        service = EventRoutingService(config)
        
        event = {
            "eventType": "unknown",
            "source": "unknown"
        }
        
        result = service.route_event(event)
        
        assert result.workflow_config is None
        assert "No workflow found" in result.routing_decision
        assert result.confidence == 0.0


class TestOrchestratorDomainService:
    """Test the coordinating domain service."""
    
    def test_process_event_full_flow(self):
        """
        GIVEN an orchestrator domain service
        WHEN processing a valid event
        THEN it should validate and route successfully.
        """
        service = OrchestratorDomainService(DEFAULT_ROUTING_CONFIG)
        
        event = {
            "eventType": "document-added",
            "source": "monitoring",
            "message": "Document uploaded"
        }
        
        validation_result, routing_result = service.process_event_for_routing(event)
        
        # Validation should succeed
        assert validation_result.is_valid is True
        assert validation_result.errors == []
        
        # Routing should succeed
        assert routing_result is not None
        assert routing_result.workflow_config is not None
        assert routing_result.workflow_config.workflow_name == "document_processing_workflow"
    
    def test_process_invalid_event(self):
        """
        GIVEN an orchestrator domain service
        WHEN processing an invalid event
        THEN it should validate but not route.
        """
        service = OrchestratorDomainService(DEFAULT_ROUTING_CONFIG)
        
        validation_result, routing_result = service.process_event_for_routing("invalid")
        
        # Validation should fail
        assert validation_result.is_valid is False
        assert "Event must be a dictionary" in validation_result.errors
        
        # Routing should not occur
        assert routing_result is None
    
    def test_process_with_custom_config(self):
        """
        GIVEN an orchestrator domain service
        WHEN processing with custom routing config
        THEN it should use the custom config.
        """
        service = OrchestratorDomainService()
        
        custom_config = EventRoutingConfig(
            event_type_mappings={"custom": "custom_workflow"},
            source_mappings={},
            default_workflow=None,
            workflows={
                "custom_workflow": WorkflowConfig(
                    workflow_name="custom_workflow",
                    workflow_class="CustomWorkflow",
                    task_queue="custom-queue"
                )
            }
        )
        
        event = {"eventType": "custom"}
        
        validation_result, routing_result = service.process_event_for_routing(
            event, 
            custom_config
        )
        
        # Should route with custom config
        assert validation_result.is_valid is True
        assert routing_result is not None
        assert routing_result.workflow_config.workflow_name == "custom_workflow"
