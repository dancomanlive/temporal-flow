import asyncio
import logging
from temporalio.worker import Worker
from src.incident_workflow.workflows import IncidentWorkflow
from src.utils import connect_to_temporal_with_retry

from src.incident_workflow.activities import incident_activities_instance

async def main():
    """Main function to start the incident workflow worker."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Incident Workflow Worker")
    client = await connect_to_temporal_with_retry("temporal:7233")
    worker = Worker(
        client,
        task_queue="incident_workflow-queue",
        workflows=[IncidentWorkflow],
        activities=[
            # Incident workflow activities
            incident_activities_instance.detect_incident,
            incident_activities_instance.analyze_logs,
            incident_activities_instance.send_notification,
            incident_activities_instance.mark_complete,
        ],
    )
    logger.info("Starting Incident Workflow worker on task queue: incident_workflow-queue")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
