# src/coordinator_workflow/activities.py

import json
import os
from typing import Any, Dict, List
from pydantic import BaseModel
from temporalio import activity
from temporalio.exceptions import ApplicationError

# --- Data Models ---
class ChooseWorkflowParams(BaseModel):
    event_type: str
    available_workflows: List[str]

class ChooseWorkflowResult(BaseModel):
    workflow_name: str

class LoadDefinitionParams(BaseModel):
    workflow_name: str
    workflows_base_dir: str

class LoadDefinitionResult(BaseModel):
    workflow_def: Dict[str, Any]

class GenerateUUIDResult(BaseModel):
    uuid: str

# --- Activity Class ---
class CoordinatorActivities:
    def __init__(self):
        # openai.api_key = os.getenv("OPENAI_API_KEY")
        # if not openai.api_key:
        #     raise ValueError("OPENAI_API_KEY environment variable not set.")
        # Assumes the script is run with /app as the working directory inside the container
        self.workflows_base_dir = os.path.abspath("./src")

    @activity.defn
    async def choose_workflow(self, params: ChooseWorkflowParams) -> ChooseWorkflowResult:
        """Simple logic: if event_type is 'incident', select 'incident_workflow', else error."""
        activity.logger.info(f"Choosing workflow for event_type: '{params.event_type}'")
        event_type = params.event_type.lower()
        if event_type == "incident" and "incident_workflow" in params.available_workflows:
            activity.logger.info("Chose 'incident_workflow' based on event_type.")
            return ChooseWorkflowResult(workflow_name="incident_workflow")
        else:
            activity.logger.warning("No available workflow for this event type.")
            raise ApplicationError("No available workflow for this event type.", non_retryable=True)


    @activity.defn
    async def get_available_workflows(self) -> List[str]:
        """Scans the filesystem to find all available workflow directories."""
        activity.logger.info(f"Scanning for workflows in '{self.workflows_base_dir}'")
        available = []
        for d in os.listdir(self.workflows_base_dir):
            # A valid workflow module must have a .json definition file.
            # We exclude 'coordinator_workflow' from the list of choices.
            if d == "coordinator_workflow":
                continue
            dir_path = os.path.join(self.workflows_base_dir, d)
            json_path = os.path.join(dir_path, f"{d}.json")
            if os.path.isdir(dir_path) and os.path.exists(json_path):
                available.append(d)
        activity.logger.info(f"Found available workflows: {available}")
        return available

    @activity.defn
    async def load_workflow_definition(self, params: LoadDefinitionParams) -> LoadDefinitionResult:
        """Load the JSON definition file for a specific workflow."""
        workflow_name = params.workflow_name
        workflows_base_dir = params.workflows_base_dir
        
        activity.logger.info(f"Loading definition for workflow: '{workflow_name}'")
        
        # Construct the path to the JSON definition file
        json_path = os.path.join(workflows_base_dir, workflow_name, f"{workflow_name}.json")
        
        if not os.path.exists(json_path):
            activity.logger.error(f"Definition file not found: {json_path}")
            raise ApplicationError(f"Workflow definition file not found for '{workflow_name}'", non_retryable=True)
        
        try:
            with open(json_path, 'r') as f:
                workflow_def = json.load(f)
            activity.logger.info(f"Successfully loaded definition for '{workflow_name}'")
            return LoadDefinitionResult(workflow_def=workflow_def)
        except (json.JSONDecodeError, IOError) as e:
            activity.logger.error(f"Failed to load workflow definition: {e}")
            raise ApplicationError(f"Failed to load workflow definition for '{workflow_name}': {e}", non_retryable=True)

# Export an instance for the worker to discover
activities_instance = CoordinatorActivities()