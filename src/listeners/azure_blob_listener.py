"""Azure Blob Storage Event Listener - Listens for Azure events and triggers Temporal workflows."""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from azure.servicebus import ServiceBusClient
    from azure.core.exceptions import ServiceBusError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

from temporalio.client import Client
from src.utils import connect_to_temporal_with_retry


class AzureBlobEventListener:
    """Listens for Azure Blob Storage events via Service Bus and triggers Temporal workflows."""
    
    def __init__(
        self,
        connection_string: str,
        topic_name: str,
        subscription_name: str,
        temporal_address: str = "temporal:7233",
        workflow_id_prefix: str = "azure-event",
        poll_interval: int = 10,
        max_messages: int = 10
    ):
        """Initialize the Azure Blob event listener.
        
        Args:
            connection_string: Azure Service Bus connection string
            topic_name: Service Bus topic name
            subscription_name: Service Bus subscription name  
            temporal_address: Address of the Temporal server
            workflow_id_prefix: Prefix for generated workflow IDs
            poll_interval: How often to poll for messages (seconds)
            max_messages: Maximum messages to retrieve per poll
        """
        if not AZURE_AVAILABLE:
            raise RuntimeError("azure-servicebus is required for AzureBlobEventListener. Install with: pip install azure-servicebus")
        
        self.connection_string = connection_string
        self.topic_name = topic_name
        self.subscription_name = subscription_name
        self.temporal_address = temporal_address
        self.workflow_id_prefix = workflow_id_prefix
        self.poll_interval = poll_interval
        self.max_messages = max_messages
        
        # Initialize Azure Service Bus client
        self.servicebus_client = ServiceBusClient.from_connection_string(connection_string)
        
        # Temporal client will be initialized in async context
        self.temporal_client: Optional[Client] = None
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the event listener service."""
        self.logger.info("Starting Azure Blob Event Listener")
        self.logger.info(f"Topic: {self.topic_name}")
        self.logger.info(f"Subscription: {self.subscription_name}")
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
        
        # Cleanup
        self.servicebus_client.close()
    
    async def _poll_and_process(self):
        """Poll Service Bus for messages and process Azure Blob events."""
        try:
            # Get receiver for the subscription
            with self.servicebus_client.get_subscription_receiver(
                topic_name=self.topic_name,
                subscription_name=self.subscription_name,
                max_wait_time=5
            ) as receiver:
                
                # Receive messages
                messages = receiver.receive_messages(max_message_count=self.max_messages, max_wait_time=5)
                
                if not messages:
                    return
                
                self.logger.info(f"Received {len(messages)} messages from Service Bus")
                
                # Process each message
                for message in messages:
                    try:
                        await self._process_message(message)
                        
                        # Complete message after successful processing
                        receiver.complete_message(message)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing message {message.message_id}: {e}")
                        # Message will remain in subscription for retry
        
        except ServiceBusError as e:
            self.logger.error(f"Error polling Service Bus: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in polling: {e}")
    
    async def _process_message(self, message):
        """Process a single Service Bus message containing Azure Blob event data.
        
        Args:
            message: Service Bus message containing Azure event notification
        """
        message_id = message.message_id or 'unknown'
        self.logger.info(f"Processing message {message_id}")
        
        try:
            # Parse the message body
            if hasattr(message, 'body') and message.body:
                if isinstance(message.body, bytes):
                    body_str = message.body.decode('utf-8')
                else:
                    body_str = str(message.body)
                
                body = json.loads(body_str)
            else:
                self.logger.warning(f"Empty message body for message {message_id}")
                return
            
            # Handle Azure Event Grid format
            if isinstance(body, list):
                # Event Grid sends arrays of events
                for event in body:
                    if self._is_blob_storage_event(event):
                        await self._handle_blob_event(event)
            elif isinstance(body, dict) and self._is_blob_storage_event(body):
                # Single event
                await self._handle_blob_event(body)
            else:
                self.logger.warning(f"Unknown message format for message {message_id}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in message {message_id}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message {message_id}: {e}")
    
    def _is_blob_storage_event(self, event: Dict[str, Any]) -> bool:
        """Check if an event is a blob storage event.
        
        Args:
            event: Event data
            
        Returns:
            True if this is a blob storage event
        """
        event_type = event.get('eventType', '')
        return 'Microsoft.Storage.Blob' in event_type
    
    async def _handle_blob_event(self, blob_event: Dict[str, Any]):
        """Handle a single Azure Blob Storage event.
        
        Args:
            blob_event: Azure Blob Storage event data
        """
        try:
            # Extract blob event information
            event_type = blob_event.get('eventType', '')
            subject = blob_event.get('subject', '')
            data = blob_event.get('data', {})
            
            # Parse blob information from subject or data
            blob_url = data.get('url', '')
            content_type = data.get('contentType', '')
            content_length = data.get('contentLength', 0)
            
            self.logger.info(f"Azure Blob Event: {event_type} for {blob_url}")
            
            # Determine our internal event type
            internal_event_type = self._map_azure_event_to_type(event_type)
            
            # Create event payload for Temporal workflow
            event_payload = {
                "eventType": internal_event_type,
                "source": "azure-blob",
                "blobUrl": blob_url,
                "documentUri": blob_url,
                "contentType": content_type,
                "size": content_length,
                "azureEventType": event_type,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat(),
                "rawEvent": blob_event
            }
            
            # Generate unique workflow ID
            blob_name = blob_url.split('/')[-1] if blob_url else 'unknown'
            workflow_id = f"{self.workflow_id_prefix}-{blob_name}-{int(datetime.utcnow().timestamp())}"
            
            # Trigger Temporal workflow
            await self._trigger_temporal_workflow(workflow_id, event_payload)
            
        except Exception as e:
            self.logger.error(f"Error handling Azure Blob event: {e}")
    
    def _map_azure_event_to_type(self, azure_event_type: str) -> str:
        """Map Azure event type to our internal event type.
        
        Args:
            azure_event_type: Azure event type (e.g., 'Microsoft.Storage.BlobCreated')
            
        Returns:
            Internal event type string
        """
        if 'BlobCreated' in azure_event_type:
            return "document-added"
        elif 'BlobDeleted' in azure_event_type:
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
            
            # All Azure Blob events trigger document processing workflow (placeholder until ready)
            self.logger.info("Using DocumentProcessingWorkflowPlaceholder - DocumentProcessingWorkflow not implemented yet")
            await self.temporal_client.start_workflow(
                "DocumentProcessingWorkflowPlaceholder",
                args=[{
                    "document_uri": event_payload.get('documentUri'),
                    "source": "azure-blob",
                    "event_type": event_payload.get('eventType'),
                    "container": event_payload.get('container'),
                    "blob_name": event_payload.get('blobName'),
                    "size": event_payload.get('size'),
                    "timestamp": event_payload.get('timestamp'),
                    "additional_context": {
                        "azureBlobEvent": event_payload.get('azureBlobEvent'),
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
    """Main function to run the Azure Blob event listener."""
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Get configuration from environment
    connection_string = os.getenv('AZURE_SERVICEBUS_CONNECTION_STRING')
    if not connection_string:
        logger.warning("AZURE_SERVICEBUS_CONNECTION_STRING environment variable is not set")
        logger.info("Azure Blob Event Listener will not start without Service Bus configuration")
        logger.info("To enable Azure blob event listening, set AZURE_SERVICEBUS_CONNECTION_STRING environment variable")
        logger.info("Azure Blob Event Listener shutting down gracefully...")
        return
    
    topic_name = os.getenv('AZURE_SERVICEBUS_TOPIC', 'blob-events')
    subscription_name = os.getenv('AZURE_SERVICEBUS_SUBSCRIPTION', 'temporal-subscription')
    temporal_address = os.getenv('TEMPORAL_ADDRESS', 'temporal:7233')
    
    # Create and start listener
    listener = AzureBlobEventListener(
        connection_string=connection_string,
        topic_name=topic_name,
        subscription_name=subscription_name,
        temporal_address=temporal_address
    )
    
    await listener.start()


if __name__ == "__main__":
    asyncio.run(main())
