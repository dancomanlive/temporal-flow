"""Root Orchestrator Workflow - Generic event-driven workflow orchestration."""

from datetime import timedelta
from typing import Dict, Any, Optional
from temporalio import workflow
from temporalio.exceptions import ApplicationError
from ..domain.workflow_inputs import RootOrchestratorInput, IncidentWorkflowInput


@workflow.defn  
class RootOrchestratorWorkflow:
    """Generic root orchestrator that routes events to domain-specific workflows.
    
    This workflow provides configurable, event-driven workflow orchestration
    that can route to any child workflow based on configuration.
    """
    
    def __init__(self):
        """Initialize the orchestrator workflow."""
        self._event_payload: Optional[Dict[str, Any]] = None
        self._configuration: Optional[Dict[str, Any]] = None

    @workflow.signal
    async def trigger(self, event_payload: Dict[str, Any]):
        """Receive an event signal to trigger workflow orchestration.
        
        Args:
            event_payload: The event data containing eventType, source, and other metadata
        """
        workflow.logger.info(f"Received event signal: {event_payload}")
        self._event_payload = event_payload

    @workflow.signal
    async def update_configuration(self, config: Dict[str, Any]):
        """Update the routing configuration dynamically.
        
        Args:
            config: New routing configuration
        """
        workflow.logger.info("Received configuration update")
        self._configuration = config

    @workflow.run
    async def run(self, input: RootOrchestratorInput = None) -> str:
        """Main workflow execution.
        
        Args:
            input: Structured input containing event payload and configuration
            
        Returns:
            String describing the orchestration result
        """
        # Handle None input for backwards compatibility
        if input is None:
            input = RootOrchestratorInput()
            
        # Use provided configuration or default
        if input.configuration:
            self._configuration = input.configuration
            
        # Set event payload for signal handling
        if input.event_payload:
            self._event_payload = input.event_payload
            
        workflow.logger.info("RootOrchestratorWorkflow started. Waiting for event signal...")
        
        # Load configuration if provided
        if input.configuration:
            workflow.logger.info("Loaded initial configuration from input")
        
        # Wait for the trigger signal
        while self._event_payload is None:
            await workflow.wait_condition(lambda: self._event_payload is not None)
        
        event_payload = self._event_payload
        workflow.logger.info(f"Processing event: {event_payload}")
        
        try:
            # Step 1: Validate the event
            validation_result = await workflow.execute_activity(
                "validate_event",
                {"event": event_payload},
                start_to_close_timeout=timedelta(seconds=10),
            )
            
            if not validation_result["valid"]:
                errors = ", ".join(validation_result["errors"])
                raise ApplicationError(f"Event validation failed: {errors}", non_retryable=True)
            
            workflow.logger.info("Event validation passed")
            
            # Step 2: Route the event to determine target workflow
            routing_params = {"event": event_payload}
            if self._configuration:
                routing_params["routing_config"] = self._configuration
            
            routing_result = await workflow.execute_activity(
                "route_event",
                routing_params,
                start_to_close_timeout=timedelta(seconds=10),
            )
            
            if not routing_result["routed"]:
                raise ApplicationError("Event routing failed", non_retryable=True)
            
            workflow_name = routing_result["workflow_name"]
            task_queue = routing_result["task_queue"]
            workflow_config = routing_result["workflow_config"]
            
            workflow.logger.info(f"Event routed to workflow: {workflow_name}")
            
            # Step 3: Execute the target child workflow
            child_result = await self._execute_child_workflow(
                workflow_name, 
                workflow_config,
                task_queue,
                event_payload
            )
            
            workflow.logger.info("Child workflow completed successfully")
            return f"RootOrchestrator completed. Child workflow '{workflow_name}' result: {child_result}"
            
        except ApplicationError as e:
            workflow.logger.error(f"RootOrchestrator failed: {e}")
            return f"RootOrchestrator failed: {e}"
        except Exception as e:
            workflow.logger.error(f"Unexpected error in RootOrchestrator: {e}")
            return f"RootOrchestrator failed with unexpected error: {e}"

    async def _execute_child_workflow(
        self, 
        workflow_name: str,
        workflow_config: Dict[str, Any],
        task_queue: str,
        event_payload: Dict[str, Any]
    ) -> Any:
        """Execute a child workflow based on the routing result.
        
        Args:
            workflow_name: Name of the workflow to execute
            workflow_config: Configuration for the workflow
            task_queue: Task queue for the workflow
            event_payload: Original event payload to pass to child
            
        Returns:
            Result from the child workflow
        """
        child_id = f"{workflow_name}-{workflow.uuid4()}"
        workflow_class = workflow_config.get("workflow_class", "")
        
        workflow.logger.info(f"Starting child workflow '{child_id}' of type '{workflow_class}' on queue '{task_queue}'")
        
        # Prepare the input for the child workflow
        child_input = self._prepare_child_input(workflow_name, event_payload)
        
        # Execute the appropriate child workflow
        if workflow_name == "incident_workflow":
            return await workflow.execute_child_workflow(
                "IncidentWorkflow",
                args=[child_input],
                id=child_id,
                task_queue=task_queue,
            )
        elif workflow_name == "document_processing_workflow":
            # This would be implemented when DocumentProcessingWorkflow exists
            workflow.logger.info("DocumentProcessingWorkflow not yet implemented, returning mock result")
            return {"status": "completed", "workflow": workflow_name, "input": child_input}
        elif workflow_name == "data_processing_workflow":
            # This would be implemented when DataProcessingWorkflow exists  
            workflow.logger.info("DataProcessingWorkflow not yet implemented, returning mock result")
            return {"status": "completed", "workflow": workflow_name, "input": child_input}
        else:
            # Generic fallback - could be enhanced to dynamically load workflow classes
            workflow.logger.warning(f"Unknown workflow type: {workflow_name}, returning mock result")
            return {"status": "completed", "workflow": workflow_name, "input": child_input}

    def _prepare_child_input(self, workflow_name: str, event_payload: Dict[str, Any]) -> Any:
        """Prepare input for the child workflow based on workflow type and event.
        
        Args:
            workflow_name: Name of the target workflow
            event_payload: Original event payload
            
        Returns:
            Prepared dataclass input for the child workflow
        """
        # Workflow-specific input preparation using dataclasses
        if workflow_name == "incident_workflow":
            return IncidentWorkflowInput(
                incident_id=event_payload.get("incident_id"),
                source=event_payload.get("source"),
                severity=event_payload.get("severity", "medium"),
                message=event_payload.get("message", "System event detected"),
                event_type=event_payload.get("eventType"),
                timestamp=event_payload.get("timestamp"),
                additional_context=event_payload
            )
            
        elif workflow_name == "document_processing_workflow":
            # For document processing, return a dict for now (until we create its dataclass)
            return {
                "document_uri": event_payload.get("documentUri", event_payload.get("source_uri")),
                "bucket": event_payload.get("bucket"),
                "key": event_payload.get("key"),
                "event": event_payload,
                "eventType": event_payload.get("eventType"),
                "source": event_payload.get("source"),
            }
            
        elif workflow_name == "data_processing_workflow":
            # For data processing, return a dict for now (until we create its dataclass)
            return {
                "data_source": event_payload.get("dataSource", event_payload.get("source")),
                "processing_type": event_payload.get("processingType", "default"),
                "event": event_payload,
                "eventType": event_payload.get("eventType"),
                "source": event_payload.get("source"),
            }
        
        # Default fallback - return original payload
        return event_payload
