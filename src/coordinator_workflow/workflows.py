
from datetime import timedelta
from temporalio import workflow
from temporalio.exceptions import ApplicationError


@workflow.defn
class CoordinatorWorkflow:
    def __init__(self):
        self._event_payload = None

    @workflow.signal
    async def trigger(self, event_payload: dict):
        self._event_payload = event_payload

    @workflow.run
    async def run(self, input: dict = None) -> str:
        workflow.logger.info("CoordinatorWorkflow started. Waiting for trigger signal...")
        # Wait for the trigger signal
        while self._event_payload is None:
            await workflow.wait_condition(lambda: self._event_payload is not None)
        event_payload = self._event_payload
        workflow.logger.info(f"Received event payload: {event_payload}")
        try:
            # 1. Get list of available state machine definitions.
            available_workflows = await workflow.execute_activity(
                "get_available_workflows",
                start_to_close_timeout=timedelta(seconds=10),
            )
            if not available_workflows:
                raise ApplicationError("No available workflows found.", non_retryable=True)

            # 2. Choose the correct workflow based on event_type
            choice_result = await workflow.execute_activity(
                "choose_workflow",
                {"event_type": event_payload.get("event_type", ""), "available_workflows": available_workflows},
                start_to_close_timeout=timedelta(seconds=30),
            )
            chosen_workflow_name = choice_result["workflow_name"]

            # 3. Load the JSON definition for the chosen workflow.
            definition_result = await workflow.execute_activity(
                "load_workflow_definition",
                {"workflow_name": chosen_workflow_name, "workflows_base_dir": "/app/src"},
                start_to_close_timeout=timedelta(seconds=10),
            )
            workflow_definition = definition_result["workflow_def"]

            # 4. If the chosen workflow is 'incident_workflow', run it as a child workflow
            if chosen_workflow_name == "incident_workflow":
                child_id = f"incident-{workflow.uuid4()}"
                task_queue_name = "incident_workflow-queue"
                workflow.logger.info(f"Starting child workflow '{child_id}' on task queue '{task_queue_name}'")
                final_result = await workflow.execute_child_workflow(
                    "IncidentWorkflow",
                    args=[{"initial_prompt": event_payload.get("initial_prompt")}],
                    id=child_id,
                    task_queue=task_queue_name,
                )
                workflow.logger.info("Child workflow completed successfully.")
                return f"Coordinator finished. Child result: {final_result}"
            else:
                workflow.logger.info(f"No child workflow started for '{chosen_workflow_name}'. Returning definition only.")
                return f"Coordinator finished. Loaded workflow definition: {workflow_definition}"

        except ApplicationError as e:
            workflow.logger.error(f"Coordinator workflow failed: {e}")
            return f"Coordinator failed: {e}"

