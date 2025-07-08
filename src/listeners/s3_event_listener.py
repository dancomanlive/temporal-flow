"""S3 Event Listener - Listens for S3 events via SQS and triggers Temporal workflows."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from temporalio.client import Client
from src.utils import connect_to_temporal_with_retry


class S3EventListener:
    """Listens for S3 events from SQS and triggers Temporal workflows."""
    
    def __init__(
        self,
        sqs_queue_url: str,
        temporal_address: str = "temporal:7233",
        workflow_id_prefix: str = "s3-event",
        poll_interval: int = 10,
        max_messages: int = 10
    ):
        """Initialize the S3 event listener.
        
        Args:
            sqs_queue_url: URL of the SQS queue to poll
            temporal_address: Address of the Temporal server
            workflow_id_prefix: Prefix for generated workflow IDs
            poll_interval: How often to poll SQS (seconds)
            max_messages: Maximum messages to retrieve per poll
        """
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 is required for S3EventListener. Install with: pip install boto3")
        
        self.sqs_queue_url = sqs_queue_url
        self.temporal_address = temporal_address
        self.workflow_id_prefix = workflow_id_prefix
        self.poll_interval = poll_interval
        self.max_messages = max_messages
        
        # Initialize AWS clients
        self.sqs_client = boto3.client('sqs')
        
        # Temporal client will be initialized in async context
        self.temporal_client: Optional[Client] = None
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the event listener service."""
        self.logger.info("Starting S3 Event Listener")
        self.logger.info(f"SQS Queue: {self.sqs_queue_url}")
        self.logger.info(f"Temporal Address: {self.temporal_address}")
        self.logger.info("Triggering document processing workflows directly")
        
        # Initialize Temporal client
        self.temporal_client = await connect_to_temporal_with_retry(self.temporal_address)
        
        # Start polling loop
        while True:
            try:
                await self._poll_and_process()
                await asyncio.sleep(self.poll_interval)
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal, shutting down...")
                break
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(self.poll_interval)
    
    async def _poll_and_process(self):
        """Poll SQS for messages and process S3 events."""
        try:
            # Poll SQS for messages
            response = self.sqs_client.receive_message(
                QueueUrl=self.sqs_queue_url,
                MaxNumberOfMessages=self.max_messages,
                WaitTimeSeconds=5,  # Long polling
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            if not messages:
                return
            
            self.logger.info(f"Received {len(messages)} messages from SQS")
            
            # Process each message
            for message in messages:
                try:
                    await self._process_message(message)
                    
                    # Delete message after successful processing
                    self.sqs_client.delete_message(
                        QueueUrl=self.sqs_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    
                except Exception as e:
                    self.logger.error(f"Error processing message {message.get('MessageId', 'unknown')}: {e}")
                    # Message will remain in queue for retry
        
        except ClientError as e:
            self.logger.error(f"Error polling SQS: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in polling: {e}")
    
    async def _process_message(self, message: Dict[str, Any]):
        """Process a single SQS message containing S3 event data.
        
        Args:
            message: SQS message containing S3 event notification
        """
        message_id = message.get('MessageId', 'unknown')
        self.logger.info(f"Processing message {message_id}")
        
        try:
            # Parse the message body
            body = json.loads(message['Body'])
            
            # Handle S3 notification format
            if 'Records' in body:
                # Direct S3 notification
                for record in body['Records']:
                    if record.get('eventSource') == 'aws:s3':
                        await self._handle_s3_event(record)
            elif 'Message' in body:
                # SNS wrapped S3 notification
                sns_message = json.loads(body['Message'])
                if 'Records' in sns_message:
                    for record in sns_message['Records']:
                        if record.get('eventSource') == 'aws:s3':
                            await self._handle_s3_event(record)
            else:
                self.logger.warning(f"Unknown message format for message {message_id}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in message {message_id}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message {message_id}: {e}")
    
    async def _handle_s3_event(self, s3_record: Dict[str, Any]):
        """Handle a single S3 event record.
        
        Args:
            s3_record: S3 event record from the notification
        """
        try:
            # Extract S3 event information
            event_name = s3_record.get('eventName', '')
            s3_info = s3_record.get('s3', {})
            bucket_info = s3_info.get('bucket', {})
            object_info = s3_info.get('object', {})
            
            bucket_name = bucket_info.get('name', '')
            object_key = object_info.get('key', '')
            object_size = object_info.get('size', 0)
            
            self.logger.info(f"S3 Event: {event_name} for s3://{bucket_name}/{object_key}")
            
            # Determine event type based on S3 event name
            event_type = self._map_s3_event_to_type(event_name)
            
            # Create event payload for Temporal workflow
            event_payload = {
                "eventType": event_type,
                "source": "s3",
                "bucket": bucket_name,
                "key": object_key,
                "documentUri": f"s3://{bucket_name}/{object_key}",
                "size": object_size,
                "s3EventName": event_name,
                "timestamp": datetime.utcnow().isoformat(),
                "rawEvent": s3_record
            }
            
            # Generate unique workflow ID
            workflow_id = f"{self.workflow_id_prefix}-{bucket_name}-{object_key.replace('/', '-')}-{int(datetime.utcnow().timestamp())}"
            
            # Trigger Temporal workflow
            await self._trigger_temporal_workflow(workflow_id, event_payload)
            
        except Exception as e:
            self.logger.error(f"Error handling S3 event: {e}")
    
    def _map_s3_event_to_type(self, s3_event_name: str) -> str:
        """Map S3 event name to our internal event type.
        
        Args:
            s3_event_name: S3 event name (e.g., 's3:ObjectCreated:Put')
            
        Returns:
            Internal event type string
        """
        if 'ObjectCreated' in s3_event_name:
            return "document-added"
        elif 'ObjectRemoved' in s3_event_name:
            return "document-removed"
        else:
            return "document-changed"
    
    async def _trigger_temporal_workflow(self, workflow_id: str, event_payload: Dict[str, Any]):
        """Trigger a Temporal workflow with the event payload.
        
        Args:
            workflow_id: Unique workflow ID
            event_payload: Event data to send to workflow
        """
        try:
            self.logger.info(f"Triggering placeholder workflow {workflow_id}")
            
            # All S3 events trigger document processing workflow (placeholder until ready)
            self.logger.info("Using DocumentProcessingWorkflowPlaceholder - DocumentProcessingWorkflow not implemented yet")
            await self.temporal_client.start_workflow(
                "DocumentProcessingWorkflowPlaceholder",
                args=[{
                    "document_uri": event_payload.get('documentUri'),
                    "source": "s3",
                    "event_type": event_payload.get('eventType'),
                    "bucket": event_payload.get('bucket'),
                    "key": event_payload.get('key'),
                    "size": event_payload.get('size'),
                    "timestamp": event_payload.get('timestamp'),
                    "additional_context": {
                        "s3EventName": event_payload.get('s3EventName'),
                        "rawEvent": event_payload.get('rawEvent')
                    }
                }],
                id=workflow_id,
                task_queue="document_processing-queue",
            )
            
            self.logger.info(f"Successfully triggered placeholder workflow {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Error triggering Temporal workflow {workflow_id}: {e}")
            raise


async def main():
    """Main function to run the S3 event listener."""
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Get configuration from environment
    sqs_queue_url = os.getenv('SQS_QUEUE_URL')
    if not sqs_queue_url:
        logger.warning("SQS_QUEUE_URL environment variable is not set")
        logger.info("S3 Event Listener will not start without SQS configuration")
        logger.info("To enable S3 event listening, set SQS_QUEUE_URL environment variable")
        logger.info("S3 Event Listener shutting down gracefully...")
        return
    
    temporal_address = os.getenv('TEMPORAL_ADDRESS', 'temporal:7233')
    
    # Create and start listener
    listener = S3EventListener(
        sqs_queue_url=sqs_queue_url,
        temporal_address=temporal_address
    )
    
    await listener.start()


if __name__ == "__main__":
    asyncio.run(main())
