# src/incident_workflow/activities.py
from temporalio import activity


class IncidentActivities:
    @activity.defn
    async def detect_incident(self, context: dict) -> dict:
        activity.logger.info(f"Detecting incident based on prompt: {context.get('initial_prompt')}")
        # In a real scenario, this would involve checking monitoring systems, etc.
        return {"incident_id": "INC-123", "severity": "critical"}

    @activity.defn
    async def analyze_logs(self, context: dict) -> dict:
        incident_id = context.get('incident_id')
        activity.logger.info(f"Analyzing logs for incident {incident_id}...")
        # Simulate log analysis
        return {"analysis_summary": "Found error stack trace related to service 'payment-processor'."}

    @activity.defn
    async def send_notification(self, context: dict) -> dict:
        summary = context.get('analysis_summary', 'An incident has occurred.')
        activity.logger.info(f"Sending notification to on-call: {summary}")
        # This would integrate with PagerDuty, Slack, etc.
        return {"notification_status": "sent"}

    @activity.defn
    async def mark_complete(self, context: dict) -> dict:
        incident_id = context.get('incident_id')
        activity.logger.info(f"Marking incident {incident_id} as resolved.")
        # This would update a ticketing system like Jira.
        return {"resolution_status": "complete"}

# Export an instance for the worker to discover
incident_activities_instance = IncidentActivities()
