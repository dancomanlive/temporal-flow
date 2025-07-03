"""Tests for Root Orchestrator Activities."""

import pytest
from src.root_orchestrator.activities import RootOrchestratorActivities
from src.domain.workflow_routing import EventRoutingConfig, WorkflowConfig

pytestmark = pytest.mark.asyncio


class TestRootOrchestratorActivities:
    """Tests for RootOrchestratorActivities."""

    async def test_validate_event_success(self):
        """
        GIVEN a valid event with required fields
        WHEN validate_event is called
        THEN it should return valid=True with no errors.
        """
        activities = RootOrchestratorActivities()
        
        event = {
            "eventType": "document-added",
            "source": "s3",
            "documentUri": "s3://bucket/file.txt"
        }
        
        result = await activities.validate_event({"event": event})
        
        assert result.valid is True
        assert len(result.errors) == 0

    async def test_validate_event_missing_event_type(self):
        """
        GIVEN an event missing the eventType field
        WHEN validate_event is called
        THEN it should return valid=False with appropriate error.
        """
        activities = RootOrchestratorActivities()
        
        event = {
            "source": "s3",
            "documentUri": "s3://bucket/file.txt"
        }
        
        result = await activities.validate_event({"event": event})
        
        assert result.valid is False
        assert "Event must contain 'eventType' field" in result.errors

    async def test_validate_event_empty_event_type(self):
        """
        GIVEN an event with empty eventType
        WHEN validate_event is called
        THEN it should return valid=False with appropriate error.
        """
        activities = RootOrchestratorActivities()
        
        event = {
            "eventType": "",
            "source": "s3"
        }
        
        result = await activities.validate_event({"event": event})
        
        assert result.valid is False
        assert "'eventType' must be a non-empty string" in result.errors

    async def test_validate_event_invalid_source_type(self):
        """
        GIVEN an event with non-string source field
        WHEN validate_event is called
        THEN it should return valid=False with appropriate error.
        """
        activities = RootOrchestratorActivities()
        
        event = {
            "eventType": "document-added",
            "source": 123  # Invalid type
        }
        
        result = await activities.validate_event({"event": event})
        
        assert result.valid is False
        assert "'source' field must be a string if present" in result.errors

    async def test_validate_event_non_dict(self):
        """
        GIVEN a non-dictionary event
        WHEN validate_event is called
        THEN it should return valid=False with appropriate error.
        """
        activities = RootOrchestratorActivities()
        
        result = await activities.validate_event({"event": "not a dict"})
        
        assert result.valid is False
        assert "Invalid parameters" in result.errors[0]

    async def test_route_event_by_event_type(self):
        """
        GIVEN an event with a known eventType
        WHEN route_event is called
        THEN it should route to the correct workflow.
        """
        activities = RootOrchestratorActivities()
        
        event = {
            "eventType": "incident",
            "source": "monitoring",
            "message": "System down"
        }
        
        result = await activities.route_event({"event": event})
        
        assert result.routed is True
        assert result.workflow_name == "incident_workflow"
        assert result.task_queue == "incident_workflow-queue"
        assert result.workflow_config is not None

    async def test_route_event_by_source(self):
        """
        GIVEN an event with unknown eventType but known source
        WHEN route_event is called
        THEN it should route based on source mapping.
        """
        activities = RootOrchestratorActivities()
        
        event = {
            "eventType": "unknown-event",
            "source": "s3",
            "documentUri": "s3://bucket/file.txt"
        }
        
        result = await activities.route_event({"event": event})
        
        assert result.routed is True
        assert result.workflow_name == "document_processing_workflow"
        assert result.task_queue == "document_processing-queue"

    async def test_route_event_default_workflow(self):
        """
        GIVEN an event that doesn't match eventType or source mappings
        WHEN route_event is called
        THEN it should route to default workflow.
        """
        activities = RootOrchestratorActivities()
        
        event = {
            "eventType": "unknown-event",
            "source": "unknown-source"
        }
        
        result = await activities.route_event({"event": event})
        
        assert result.routed is True
        assert result.workflow_name == "incident_workflow"  # Default workflow

    async def test_route_event_custom_config(self):
        """
        GIVEN a custom routing configuration
        WHEN route_event is called with custom config
        THEN it should use the custom configuration.
        """
        activities = RootOrchestratorActivities()
        
        custom_config = {
            "event_type_mappings": {
                "custom-event": "custom_workflow"
            },
            "source_mappings": {},
            "default_workflow": None,
            "workflows": {
                "custom_workflow": {
                    "workflow_name": "custom_workflow",
                    "workflow_class": "CustomWorkflow",
                    "task_queue": "custom-queue",
                    "description": "Custom workflow",
                    "enabled": True
                }
            }
        }
        
        event = {
            "eventType": "custom-event"
        }
        
        result = await activities.route_event({
            "event": event,
            "routing_config": custom_config
        })
        
        assert result.routed is True
        assert result.workflow_name == "custom_workflow"
        assert result.task_queue == "custom-queue"

    async def test_route_event_no_matching_workflow(self):
        """
        GIVEN an event that cannot be routed to any workflow
        WHEN route_event is called
        THEN it should raise an ApplicationError.
        """
        from temporalio.exceptions import ApplicationError
        
        # Create custom config with no default workflow
        custom_config = EventRoutingConfig(
            event_type_mappings={},
            source_mappings={},
            default_workflow=None,
            workflows={}
        )
        
        activities = RootOrchestratorActivities(custom_config)
        
        event = {
            "eventType": "unknown-event",
            "source": "unknown-source"
        }
        
        with pytest.raises(ApplicationError) as exc_info:
            await activities.route_event({"event": event})
        
        assert "No workflow configured to handle" in str(exc_info.value)
        assert exc_info.value.non_retryable is True

    async def test_route_event_disabled_workflow(self):
        """
        GIVEN a routing configuration with a disabled workflow
        WHEN route_event is called for that workflow
        THEN it should not route to the disabled workflow.
        """
        from temporalio.exceptions import ApplicationError
        
        # Create config with disabled workflow
        custom_config = EventRoutingConfig(
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
        
        activities = RootOrchestratorActivities(custom_config)
        
        event = {
            "eventType": "test-event"
        }
        
        with pytest.raises(ApplicationError) as exc_info:
            await activities.route_event({"event": event})
        
        assert "No workflow configured to handle" in str(exc_info.value)

    async def test_route_event_invalid_custom_config(self):
        """
        GIVEN an invalid custom routing configuration
        WHEN route_event is called
        THEN it should raise an ApplicationError.
        """
        from temporalio.exceptions import ApplicationError
        
        activities = RootOrchestratorActivities()
        
        invalid_config = {
            "event_type_mappings": "not a dict",  # Invalid type
            "workflows": {}
        }
        
        event = {
            "eventType": "test-event"
        }
        
        with pytest.raises(ApplicationError) as exc_info:
            await activities.route_event({
                "event": event,
                "routing_config": invalid_config
            })
        
        assert "Invalid routing configuration" in str(exc_info.value)
        assert exc_info.value.non_retryable is True
