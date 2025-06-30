
from temporalio import workflow


@workflow.defn
class IncidentWorkflow:
    @workflow.run
    async def run(self, initial_context=None):
        from datetime import timedelta
        context = initial_context or {}

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
