"""Worker process for semantic search."""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import SemanticSearchWorkflow
from .activities import SemanticSearchActivities

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """Run the workflow worker."""
    logger.info("Initializing Semantic Search worker...")
    
    # Connect to Temporal server
    logger.info("Connecting to Temporal server...")
    client = await Client.connect("temporal:7233")
    logger.info("Connected to Temporal server successfully!")
    
    # Create activities instance
    logger.info("Creating activities instance...")
    activities = SemanticSearchActivities()
    logger.info("Activities instance created!")
    
    # Create worker
    logger.info("Creating worker...")
    worker = Worker(
        client,
        task_queue="semantic-search-queue",
        workflows=[SemanticSearchWorkflow],
        activities=[
            activities.embed_query,
            activities.retrieve_chunks,
            activities.generate_response
        ]
    )
    logger.info("Worker created successfully!")
    
    logger.info("Starting Semantic Search worker on task queue: semantic-search-queue")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())