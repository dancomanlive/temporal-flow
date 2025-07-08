"""Tests for workflow routing domain logic."""

from src.domain.workflow_routing import (
    WorkflowConfig, 
    EventRoutingConfig, 
    WorkflowRouter,
    DEFAULT_ROUTING_CONFIG
)


class TestWorkflowRouter:
    """Tests for WorkflowRouter."""

    def test_route_by_event_type(self):
        """
        GIVEN a router with event type mappings
        WHEN an event with a known eventType is routed
        THEN it should return the correct workflow config.
        """
        router = WorkflowRouter(DEFAULT_ROUTING_CONFIG)
        
        event = {
            "eventType": "document-added",
            "source": "monitoring"
        }
        
        result = router.route_event(event)
        
        assert result is not None
        assert result.workflow_name == "document_processing_workflow"
        assert result.task_queue == "document_processing-queue"
        assert result.enabled is True

    def test_route_by_source(self):
        """
        GIVEN a router with source mappings
        WHEN an event with unknown eventType but known source is routed
        THEN it should return the workflow config based on source.
        """
        router = WorkflowRouter(DEFAULT_ROUTING_CONFIG)
        
        event = {
            "eventType": "unknown-event",
            "source": "s3"
        }
        
        result = router.route_event(event)
        
        assert result is not None
        assert result.workflow_name == "document_processing_workflow"
        assert result.task_queue == "document_processing-queue"

    def test_route_to_default_workflow(self):
        """
        GIVEN a router with a default workflow configured
        WHEN an event that doesn't match any mapping is routed
        THEN it should return the default workflow config.
        """
        router = WorkflowRouter(DEFAULT_ROUTING_CONFIG)
        
        event = {
            "eventType": "unknown-event",
            "source": "unknown-source"
        }
        
        result = router.route_event(event)
        
        assert result is not None
        assert result.workflow_name == "document_processing_workflow"  # Default workflow

    def test_route_case_insensitive(self):
        """
        GIVEN a router with lowercase event type mappings
        WHEN an event with uppercase eventType is routed
        THEN it should match case-insensitively.
        """
        router = WorkflowRouter(DEFAULT_ROUTING_CONFIG)
        
        event = {
            "eventType": "DOCUMENT-ADDED",
            "source": "MONITORING"
        }
        
        result = router.route_event(event)
        
        assert result is not None
        assert result.workflow_name == "document_processing_workflow"

    def test_route_no_match_no_default(self):
        """
        GIVEN a router with no default workflow
        WHEN an event that doesn't match any mapping is routed
        THEN it should return None.
        """
        config = EventRoutingConfig(
            event_type_mappings={},
            source_mappings={},
            default_workflow=None,
            workflows={}
        )
        
        router = WorkflowRouter(config)
        
        event = {
            "eventType": "unknown-event",
            "source": "unknown-source"
        }
        
        result = router.route_event(event)
        
        assert result is None

    def test_route_disabled_workflow(self):
        """
        GIVEN a router with a disabled workflow
        WHEN an event is routed to that workflow
        THEN it should return None.
        """
        config = EventRoutingConfig(
            event_type_mappings={
                "test-event": "disabled_workflow"
            },
            source_mappings={},
            default_workflow=None,
            workflows={
                "disabled_workflow": WorkflowConfig(
                    workflow_name="disabled_workflow",
                    workflow_class="DisabledWorkflow",
                    task_queue="disabled-queue",
                    enabled=False
                )
            }
        )
        
        router = WorkflowRouter(config)
        
        event = {
            "eventType": "test-event"
        }
        
        result = router.route_event(event)
        
        assert result is None

    def test_route_nonexistent_workflow(self):
        """
        GIVEN a router with a mapping to a nonexistent workflow
        WHEN an event is routed to that workflow
        THEN it should return None.
        """
        config = EventRoutingConfig(
            event_type_mappings={
                "test-event": "nonexistent_workflow"
            },
            source_mappings={},
            default_workflow=None,
            workflows={}
        )
        
        router = WorkflowRouter(config)
        
        event = {
            "eventType": "test-event"
        }
        
        result = router.route_event(event)
        
        assert result is None

    def test_route_priority_event_type_over_source(self):
        """
        GIVEN a router with both event type and source mappings
        WHEN an event matches both mappings to different workflows
        THEN it should prioritize event type mapping.
        """
        config = EventRoutingConfig(
            event_type_mappings={
                "special-event": "special_workflow"
            },
            source_mappings={
                "s3": "document_processing_workflow"
            },
            default_workflow=None,
            workflows={
                "special_workflow": WorkflowConfig(
                    workflow_name="special_workflow",
                    workflow_class="SpecialWorkflow",
                    task_queue="special-queue",
                    enabled=True
                ),
                "document_processing_workflow": WorkflowConfig(
                    workflow_name="document_processing_workflow",
                    workflow_class="DocumentProcessingWorkflow",
                    task_queue="document_processing-queue",
                    enabled=True
                )
            }
        )
        
        router = WorkflowRouter(config)
        
        event = {
            "eventType": "special-event",
            "source": "s3"
        }
        
        result = router.route_event(event)
        
        assert result is not None
        assert result.workflow_name == "special_workflow"

    def test_route_missing_event_fields(self):
        """
        GIVEN a router with valid configuration
        WHEN an event with missing eventType and source is routed
        THEN it should return the default workflow if configured.
        """
        router = WorkflowRouter(DEFAULT_ROUTING_CONFIG)
        
        event = {}
        
        result = router.route_event(event)
        
        assert result is not None
        assert result.workflow_name == "document_processing_workflow"  # Default workflow


class TestWorkflowConfig:
    """Tests for WorkflowConfig model."""

    def test_workflow_config_creation(self):
        """
        GIVEN valid workflow configuration parameters
        WHEN a WorkflowConfig is created
        THEN it should have all the correct attributes.
        """
        config = WorkflowConfig(
            workflow_name="test_workflow",
            workflow_class="TestWorkflow",
            task_queue="test-queue",
            description="Test workflow",
            enabled=True
        )
        
        assert config.workflow_name == "test_workflow"
        assert config.workflow_class == "TestWorkflow"
        assert config.task_queue == "test-queue"
        assert config.description == "Test workflow"
        assert config.enabled is True

    def test_workflow_config_defaults(self):
        """
        GIVEN minimal workflow configuration parameters
        WHEN a WorkflowConfig is created
        THEN it should use default values for optional fields.
        """
        config = WorkflowConfig(
            workflow_name="test_workflow",
            workflow_class="TestWorkflow",
            task_queue="test-queue"
        )
        
        assert config.workflow_name == "test_workflow"
        assert config.workflow_class == "TestWorkflow"
        assert config.task_queue == "test-queue"
        assert config.description is None
        assert config.enabled is True


class TestEventRoutingConfig:
    """Tests for EventRoutingConfig model."""

    def test_event_routing_config_creation(self):
        """
        GIVEN valid routing configuration parameters
        WHEN an EventRoutingConfig is created
        THEN it should have all the correct attributes.
        """
        workflows = {
            "test_workflow": WorkflowConfig(
                workflow_name="test_workflow",
                workflow_class="TestWorkflow",
                task_queue="test-queue"
            )
        }
        
        config = EventRoutingConfig(
            event_type_mappings={"test": "test_workflow"},
            source_mappings={"source": "test_workflow"},
            default_workflow="test_workflow",
            workflows=workflows
        )
        
        assert config.event_type_mappings == {"test": "test_workflow"}
        assert config.source_mappings == {"source": "test_workflow"}
        assert config.default_workflow == "test_workflow"
        assert config.workflows == workflows


class TestDefaultConfig:
    """Tests for the default routing configuration."""

    def test_default_config_structure(self):
        """
        GIVEN the default routing configuration
        WHEN accessed
        THEN it should have the expected structure and values.
        """
        config = DEFAULT_ROUTING_CONFIG
        
        # Check event type mappings
        assert "document-added" in config.event_type_mappings
        assert config.event_type_mappings["document-added"] == "document_processing_workflow"
        
        # Check source mappings
        assert "s3" in config.source_mappings
        assert "azure-blob" in config.source_mappings
        assert config.source_mappings["s3"] == "document_processing_workflow"
        
        # Check default workflow
        assert config.default_workflow == "document_processing_workflow"
        
        # Check workflows
        assert "document_processing_workflow" in config.workflows
        assert config.workflows["document_processing_workflow"].enabled is True

    def test_default_config_router_integration(self):
        """
        GIVEN the default routing configuration
        WHEN used with WorkflowRouter
        THEN it should route events correctly.
        """
        router = WorkflowRouter(DEFAULT_ROUTING_CONFIG)
        
        # Test document routing
        doc_event = {"eventType": "document-added"}
        result = router.route_event(doc_event)
        assert result.workflow_name == "document_processing_workflow"
        
        # Test source routing
        s3_event = {"eventType": "unknown", "source": "s3"}
        result = router.route_event(s3_event)
        assert result.workflow_name == "document_processing_workflow"
