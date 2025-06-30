import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from src.coordinator_workflow.workflows import CoordinatorWorkflow

from src.coordinator_workflow.activities import activities_instance

async def main():
    client = await Client.connect("temporal:7233")
    worker = Worker(
        client,
        task_queue="coordinator_workflow-queue",
        workflows=[CoordinatorWorkflow],
        activities=[
            activities_instance.get_available_workflows,
            activities_instance.choose_workflow,
        ],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
