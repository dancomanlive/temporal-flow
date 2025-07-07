
from temporalio import workflow
from ..domain.workflow_inputs import IncidentWorkflowInput
from .activities import IncidentContext


@workflow.defn
class IncidentWorkflow:
    @workflow.run
    async def run(self, input: IncidentWorkflowInput = None):
        from datetime import timedelta
        
        # Handle None input for backwards compatibility
        if input is None:
            input = IncidentWorkflowInput()
            
        # Create typed context for activities
        context = IncidentContext(
            initial_prompt=input.message,
            incident_id=input.incident_id,
            severity=input.severity,
        )

        # Step 1: Detect incident
        detection_result = await workflow.execute_activity(
            "detect_incident", context, schedule_to_close_timeout=timedelta(seconds=60)
        )
        # Update context with detection results
        context.incident_id = detection_result.incident_id
        context.severity = detection_result.severity

        # Step 2: Analyze logs
        analysis_result = await workflow.execute_activity(
            "analyze_logs", context, schedule_to_close_timeout=timedelta(seconds=120)
        )
        # Update context with analysis results
        context.analysis_summary = analysis_result.analysis_summary

        # Step 3: Send notification
        notification_result = await workflow.execute_activity(
            "send_notification", context, schedule_to_close_timeout=timedelta(seconds=60)
        )
        # Update context with notification results
        context.notification_status = notification_result.notification_status

        # Step 4: Mark complete
        resolution_result = await workflow.execute_activity(
            "mark_complete", context, schedule_to_close_timeout=timedelta(seconds=60)
        )
        # Update context with resolution results
        context.resolution_status = resolution_result.resolution_status

        # Return the final context as a dict for backwards compatibility
        return context.model_dump()
