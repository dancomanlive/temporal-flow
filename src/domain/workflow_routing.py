"""Configuration-driven workflow routing."""

from typing import Dict, Any, Optional
from pydantic import BaseModel


class WorkflowConfig(BaseModel):
    """Configuration for a single workflow."""
    
    workflow_name: str
    workflow_class: str
    task_queue: str
    description: Optional[str] = None
    enabled: bool = True


class EventRoutingConfig(BaseModel):
    """Configuration for event-based workflow routing."""
    
    event_type_mappings: Dict[str, str]  # event_type -> workflow_name
    source_mappings: Dict[str, str]      # source -> workflow_name  
    default_workflow: Optional[str] = None
    workflows: Dict[str, WorkflowConfig]


class WorkflowRouter:
    """Routes events to appropriate workflows based on configuration."""
    
    def __init__(self, config: EventRoutingConfig):
        """Initialize router with configuration.
        
        Args:
            config: The routing configuration
        """
        self.config = config
    
    def route_event(self, event: Dict[str, Any]) -> Optional[WorkflowConfig]:
        """Determine which workflow should handle an event.
        
        Args:
            event: The event payload containing eventType, source, etc.
            
        Returns:
            WorkflowConfig for the target workflow, or None if no match
        """
        event_type = event.get("eventType", "").lower()
        source = event.get("source", "").lower()
        
        # First, try to route by event type
        if event_type and event_type in self.config.event_type_mappings:
            workflow_name = self.config.event_type_mappings[event_type]
            return self._get_workflow_config(workflow_name)
        
        # Then, try to route by source
        if source and source in self.config.source_mappings:
            workflow_name = self.config.source_mappings[source]
            return self._get_workflow_config(workflow_name)
        
        # Finally, use default workflow if configured
        if self.config.default_workflow:
            return self._get_workflow_config(self.config.default_workflow)
        
        return None
    
    def _get_workflow_config(self, workflow_name: str) -> Optional[WorkflowConfig]:
        """Get workflow configuration by name.
        
        Args:
            workflow_name: Name of the workflow
            
        Returns:
            WorkflowConfig if found and enabled, None otherwise
        """
        if workflow_name not in self.config.workflows:
            return None
            
        workflow_config = self.config.workflows[workflow_name]
        return workflow_config if workflow_config.enabled else None


# Default configuration for the system
DEFAULT_ROUTING_CONFIG = EventRoutingConfig(
    event_type_mappings={
        "document-added": "document_processing_workflow",
        "document-uploaded": "document_processing_workflow",
        "data-processing": "data_processing_workflow",
    },
    source_mappings={
        "s3": "document_processing_workflow", 
        "azure-blob": "document_processing_workflow",
        "sharepoint": "document_processing_workflow",
    },
    default_workflow="document_processing_workflow",
    workflows={
        "document_processing_workflow": WorkflowConfig(
            workflow_name="document_processing_workflow",
            workflow_class="DocumentProcessingWorkflow",
            task_queue="document_processing-queue", 
            description="Processes documents from various sources",
            enabled=True
        ),
        "data_processing_workflow": WorkflowConfig(
            workflow_name="data_processing_workflow",
            workflow_class="DataProcessingWorkflow",
            task_queue="data_processing-queue",
            description="Handles data transformation and analysis",
            enabled=True
        ),
    }
)
