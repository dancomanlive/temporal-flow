"""Root Orchestrator Worker - Runs the root orchestrator workflow and activities."""

import asyncio
from temporalio.worker import Worker
from src.root_orchestrator.workflows import RootOrchestratorWorkflow
from src.root_orchestrator.activities import activities_instance
from src.utils import connect_to_temporal_with_retry


async def main():
    """Main function to start the root orchestrator worker."""
    client = await connect_to_temporal_with_retry("temporal:7233")
    worker = Worker(
        client,
        task_queue="root_orchestrator-queue",
        workflows=[RootOrchestratorWorkflow],
        activities=[
            activities_instance.validate_event,
            activities_instance.route_event,
        ],
    )
    print("Starting Root Orchestrator worker on task queue: root_orchestrator-queue")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
