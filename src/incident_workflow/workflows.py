
from temporalio import workflow
from ..domain.workflow_inputs import IncidentWorkflowInput


@workflow.defn
class IncidentWorkflow:
    @workflow.run
    async def run(self, input: IncidentWorkflowInput = None):
        from datetime import timedelta
        
        # Handle None input for backwards compatibility
        if input is None:
            input = IncidentWorkflowInput()
            
        # Convert to context dict for activity execution
        context = {
            "incident_id": input.incident_id,
            "source": input.source,
            "severity": input.severity,
            "message": input.message,
            "event_type": input.event_type,
            "timestamp": input.timestamp,
        }
        
        # Add additional context if provided
        if input.additional_context:
            context.update(input.additional_context)

        # Step 1: Detect incident
        result = await workflow.execute_activity(
            "detect_incident", context, schedule_to_close_timeout=timedelta(seconds=60)
        )
        context.update(result)

        # Step 2: Analyze logs
        result = await workflow.execute_activity(
            "analyze_logs", context, schedule_to_close_timeout=timedelta(seconds=120)
        )
        context.update(result)

        # Step 3: Send notification
        result = await workflow.execute_activity(
            "send_notification", context, schedule_to_close_timeout=timedelta(seconds=60)
        )
        context.update(result)

        # Step 4: Mark complete
        result = await workflow.execute_activity(
            "mark_complete", context, schedule_to_close_timeout=timedelta(seconds=60)
        )
        context.update(result)

        return context
