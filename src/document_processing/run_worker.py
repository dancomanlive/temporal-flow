"""Document processing worker - registers workflows and activities."""

import asyncio
import logging
from temporalio.worker import Worker
from temporalio.client import Client

from .workflows import DocumentProcessingWorkflow
from .activities import DocumentProcessingActivities


async def main():
    """Run the document processing worker."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Connect to Temporal (use environment variable for Docker)
    import os
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(temporal_address)
    
    # Create activities instance
    activities = DocumentProcessingActivities()
    
    # Run worker
    logger.info("Starting document processing worker...")
    worker = Worker(
        client,
        task_queue="document_processing-queue",
        workflows=[DocumentProcessingWorkflow],
        activities=[
            activities.validate_document,
            activities.download_document,
            activities.extract_text,
            activities.chunk_text,
            activities.generate_embeddings,
            activities.store_chunks,
        ],
    )
    
    logger.info("Document processing worker ready - listening on 'document_processing-queue'")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
