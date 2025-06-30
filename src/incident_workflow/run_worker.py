import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from src.incident_workflow.workflows import IncidentWorkflow

from src.incident_workflow.activities import incident_activities_instance

async def main():
    client = await Client.connect("temporal:7233")
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
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
