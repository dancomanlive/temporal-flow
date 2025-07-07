# src/incident_workflow/activities.py
from temporalio import activity
from pydantic import BaseModel
from typing import Optional


class IncidentContext(BaseModel):
    """Domain model for incident context."""
    initial_prompt: Optional[str] = None
    incident_id: Optional[str] = None
    severity: Optional[str] = None
    analysis_summary: Optional[str] = None
    notification_status: Optional[str] = None
    resolution_status: Optional[str] = None


class DetectionResult(BaseModel):
    """Result of incident detection."""
    incident_id: str
    severity: str


class AnalysisResult(BaseModel):
    """Result of log analysis."""
    analysis_summary: str


class NotificationResult(BaseModel):
    """Result of notification sending."""
    notification_status: str


class ResolutionResult(BaseModel):
    """Result of incident resolution."""
    resolution_status: str


class IncidentActivities:
    @activity.defn
    async def detect_incident(self, context: IncidentContext) -> DetectionResult:
        activity.logger.info(f"Detecting incident based on prompt: {context.initial_prompt}")
        # In a real scenario, this would involve checking monitoring systems, etc.
        return DetectionResult(incident_id="INC-123", severity="critical")

    @activity.defn
    async def analyze_logs(self, context: IncidentContext) -> AnalysisResult:
        activity.logger.info(f"Analyzing logs for incident {context.incident_id}...")
        # Simulate log analysis
        return AnalysisResult(analysis_summary="Found error stack trace related to service 'payment-processor'.")

    @activity.defn
    async def send_notification(self, context: IncidentContext) -> NotificationResult:
        summary = context.analysis_summary or 'An incident has occurred.'
        activity.logger.info(f"Sending notification to on-call: {summary}")
        # This would integrate with PagerDuty, Slack, etc.
        return NotificationResult(notification_status="sent")

    @activity.defn
    async def mark_complete(self, context: IncidentContext) -> ResolutionResult:
        activity.logger.info(f"Marking incident {context.incident_id} as resolved.")
        # This would update a ticketing system like Jira.
        return ResolutionResult(resolution_status="complete")

# Export an instance for the worker to discover
incident_activities_instance = IncidentActivities()
