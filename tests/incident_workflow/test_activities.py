import pytest

from src.incident_workflow.activities import IncidentActivities

pytestmark = pytest.mark.asyncio


class TestIncidentActivities:
    """Tests for IncidentActivities."""

    async def test_detect_incident(self):
        """
        GIVEN an initial context
        WHEN detect_incident is called
        THEN it should return a dictionary with incident details.
        """
        activities = IncidentActivities()
        context = {"initial_prompt": "Server is down!"}

        result = await activities.detect_incident(context)

        assert "incident_id" in result
        assert "severity" in result
        assert result["incident_id"] == "INC-123"  # Ok to be specific for now
        assert result["severity"] == "critical"

    async def test_detect_incident_with_empty_context(self):
        """
        GIVEN an empty context
        WHEN detect_incident is called
        THEN it should still return incident details.
        """
        activities = IncidentActivities()
        context = {}

        result = await activities.detect_incident(context)

        assert "incident_id" in result
        assert "severity" in result
        assert isinstance(result["incident_id"], str)
        assert isinstance(result["severity"], str)

    async def test_analyze_logs(self):
        """
        GIVEN a context with an incident_id
        WHEN analyze_logs is called
        THEN it should return a dictionary with an analysis summary.
        """
        activities = IncidentActivities()
        context = {"incident_id": "INC-123"}

        result = await activities.analyze_logs(context)

        assert "analysis_summary" in result
        # This test is flexible - it doesn't care about the *content* of the summary
        assert isinstance(result["analysis_summary"], str)
        assert len(result["analysis_summary"]) > 0

    async def test_analyze_logs_without_incident_id(self):
        """
        GIVEN a context without an incident_id
        WHEN analyze_logs is called
        THEN it should still return an analysis summary.
        """
        activities = IncidentActivities()
        context = {}

        result = await activities.analyze_logs(context)

        assert "analysis_summary" in result
        assert isinstance(result["analysis_summary"], str)

    async def test_send_notification(self):
        """
        GIVEN a context with an analysis summary
        WHEN send_notification is called
        THEN it should return a dictionary with a notification status.
        """
        activities = IncidentActivities()
        context = {"analysis_summary": "Error found in payment-processor"}

        result = await activities.send_notification(context)

        assert "notification_status" in result
        assert result["notification_status"] == "sent"

    async def test_send_notification_without_summary(self):
        """
        GIVEN a context without an analysis summary
        WHEN send_notification is called
        THEN it should still send a notification with default message.
        """
        activities = IncidentActivities()
        context = {}

        result = await activities.send_notification(context)

        assert "notification_status" in result
        assert result["notification_status"] == "sent"

    async def test_send_notification_with_custom_summary(self):
        """
        GIVEN a context with a custom analysis summary
        WHEN send_notification is called
        THEN it should return successful notification status.
        """
        activities = IncidentActivities()
        context = {"analysis_summary": "Database connection timeout detected"}

        result = await activities.send_notification(context)

        assert "notification_status" in result
        assert result["notification_status"] == "sent"
        
    async def test_mark_complete(self):
        """
        GIVEN a context with an incident_id
        WHEN mark_complete is called
        THEN it should return a dictionary with a resolution status.
        """
        activities = IncidentActivities()
        context = {"incident_id": "INC-123"}

        result = await activities.mark_complete(context)

        assert "resolution_status" in result
        assert result["resolution_status"] == "complete"

    async def test_mark_complete_without_incident_id(self):
        """
        GIVEN a context without an incident_id
        WHEN mark_complete is called
        THEN it should still return a completion status.
        """
        activities = IncidentActivities()
        context = {}

        result = await activities.mark_complete(context)

        assert "resolution_status" in result
        assert result["resolution_status"] == "complete"

    async def test_full_incident_workflow_simulation(self):
        """
        GIVEN a complete incident workflow simulation
        WHEN all activities are called in sequence
        THEN they should work together cohesively.
        """
        activities = IncidentActivities()
        
        # Step 1: Detect incident
        initial_context = {"initial_prompt": "Critical system failure"}
        detection_result = await activities.detect_incident(initial_context)
        
        # Step 2: Analyze logs
        analysis_context = {"incident_id": detection_result["incident_id"]}
        analysis_result = await activities.analyze_logs(analysis_context)
        
        # Step 3: Send notification
        notification_context = {"analysis_summary": analysis_result["analysis_summary"]}
        notification_result = await activities.send_notification(notification_context)
        
        # Step 4: Mark complete
        completion_context = {"incident_id": detection_result["incident_id"]}
        completion_result = await activities.mark_complete(completion_context)
        
        # Verify the full workflow
        assert detection_result["incident_id"] == "INC-123"
        assert analysis_result["analysis_summary"]
        assert notification_result["notification_status"] == "sent"
        assert completion_result["resolution_status"] == "complete"
