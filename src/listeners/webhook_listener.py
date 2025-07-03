"""Generic HTTP Webhook Listener - Receives webhooks and triggers Temporal workflows."""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from aiohttp import web
    from aiohttp.web import Request, Response
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from temporalio.client import Client


class WebhookEventListener:
    """Generic HTTP webhook listener that triggers Temporal workflows."""
    
    def __init__(
        self,
        port: int = 8000,
        temporal_address: str = "temporal:7233",
        workflow_id_prefix: str = "webhook-event",
        task_queue: str = "root_orchestrator-queue",
        webhook_secret: Optional[str] = None
    ):
        """Initialize the webhook event listener.
        
        Args:
            port: Port to listen on for webhooks
            temporal_address: Address of the Temporal server
            workflow_id_prefix: Prefix for generated workflow IDs
            task_queue: Task queue for triggering workflows
            webhook_secret: Optional secret for webhook verification
        """
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp is required for WebhookEventListener. Install with: pip install aiohttp")
            
        self.port = port
        self.temporal_address = temporal_address
        self.workflow_id_prefix = workflow_id_prefix
        self.task_queue = task_queue
        self.webhook_secret = webhook_secret
        
        # Temporal client will be initialized in async context
        self.temporal_client: Optional[Client] = None
        
        # Configure logging
        self.logger = logging.getLogger(__name__)
        
        # Create web application
        self.app = web.Application()
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes for webhook endpoints."""
        # Generic webhook endpoint
        self.app.router.add_post('/webhook', self._handle_webhook)
        
        # SharePoint-specific endpoint
        self.app.router.add_post('/webhook/sharepoint', self._handle_sharepoint_webhook)
        
        # Azure Event Grid endpoint (for blob storage notifications)
        self.app.router.add_post('/webhook/azure-eventgrid', self._handle_azure_eventgrid_webhook)
        
        # Health check endpoint
        self.app.router.add_get('/health', self._health_check)
    
    async def start(self):
        """Start the webhook listener service."""
        self.logger.info("Starting Webhook Event Listener")
        self.logger.info(f"Port: {self.port}")
        self.logger.info(f"Temporal Address: {self.temporal_address}")
        self.logger.info(f"Task Queue: {self.task_queue}")
        
        # Initialize Temporal client
        self.temporal_client = await Client.connect(self.temporal_address)
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        self.logger.info(f"Webhook listener started on port {self.port}")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, shutting down...")
        finally:
            await runner.cleanup()
    
    async def _health_check(self, request: Request) -> Response:
        """Health check endpoint."""
        return web.json_response({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})
    
    async def _handle_webhook(self, request: Request) -> Response:
        """Handle generic webhook requests.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response
        """
        try:
            # Parse request body
            body = await request.json()
            
            self.logger.info(f"Received generic webhook: {body}")
            
            # Extract or generate event information
            event_payload = {
                "eventType": body.get("eventType", "webhook-event"),
                "source": body.get("source", "webhook"),
                "timestamp": datetime.utcnow().isoformat(),
                "rawEvent": body
            }
            
            # Add any additional fields from the webhook body
            for key, value in body.items():
                if key not in event_payload:
                    event_payload[key] = value
            
            # Generate workflow ID
            workflow_id = f"{self.workflow_id_prefix}-generic-{int(datetime.utcnow().timestamp())}"
            
            # Trigger Temporal workflow
            await self._trigger_temporal_workflow(workflow_id, event_payload)
            
            return web.json_response({"status": "accepted", "workflow_id": workflow_id})
            
        except Exception as e:
            self.logger.error(f"Error handling generic webhook: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_sharepoint_webhook(self, request: Request) -> Response:
        """Handle SharePoint webhook requests.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response
        """
        try:
            # Parse request body
            body = await request.json()
            
            self.logger.info(f"Received SharePoint webhook: {body}")
            
            # Handle SharePoint notification format
            if "value" in body and isinstance(body["value"], list):
                # SharePoint sends arrays of notifications
                workflow_ids = []
                
                for notification in body["value"]:
                    event_payload = self._parse_sharepoint_notification(notification)
                    
                    # Generate workflow ID
                    resource = notification.get("resource", "unknown")
                    workflow_id = f"{self.workflow_id_prefix}-sharepoint-{resource.replace('/', '-')}-{int(datetime.utcnow().timestamp())}"
                    
                    # Trigger Temporal workflow
                    await self._trigger_temporal_workflow(workflow_id, event_payload)
                    workflow_ids.append(workflow_id)
                
                return web.json_response({"status": "accepted", "workflow_ids": workflow_ids})
            else:
                # Single notification
                event_payload = self._parse_sharepoint_notification(body)
                
                # Generate workflow ID
                resource = body.get("resource", "unknown")
                workflow_id = f"{self.workflow_id_prefix}-sharepoint-{resource.replace('/', '-')}-{int(datetime.utcnow().timestamp())}"
                
                # Trigger Temporal workflow
                await self._trigger_temporal_workflow(workflow_id, event_payload)
                
                return web.json_response({"status": "accepted", "workflow_id": workflow_id})
            
        except Exception as e:
            self.logger.error(f"Error handling SharePoint webhook: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_azure_eventgrid_webhook(self, request: Request) -> Response:
        """Handle Azure Event Grid webhook requests.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response
        """
        try:
            # Parse request body
            body = await request.json()
            
            self.logger.info(f"Received Azure Event Grid webhook: {body}")
            
            # Handle Event Grid validation
            if isinstance(body, list) and len(body) > 0:
                first_event = body[0]
                if first_event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
                    # Return validation response
                    validation_code = first_event.get("data", {}).get("validationCode")
                    return web.json_response({"validationResponse": validation_code})
            
            # Process events
            workflow_ids = []
            if isinstance(body, list):
                for event in body:
                    if self._is_blob_storage_event(event):
                        event_payload = self._parse_azure_blob_event(event)
                        
                        # Generate workflow ID
                        subject = event.get("subject", "unknown")
                        workflow_id = f"{self.workflow_id_prefix}-azure-{subject.replace('/', '-')}-{int(datetime.utcnow().timestamp())}"
                        
                        # Trigger Temporal workflow
                        await self._trigger_temporal_workflow(workflow_id, event_payload)
                        workflow_ids.append(workflow_id)
            
            return web.json_response({"status": "accepted", "workflow_ids": workflow_ids})
            
        except Exception as e:
            self.logger.error(f"Error handling Azure Event Grid webhook: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    def _parse_sharepoint_notification(self, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Parse SharePoint notification into our event format.
        
        Args:
            notification: SharePoint notification data
            
        Returns:
            Standardized event payload
        """
        return {
            "eventType": "document-changed",
            "source": "sharepoint",
            "resource": notification.get("resource", ""),
            "tenantId": notification.get("tenantId", ""),
            "siteUrl": notification.get("siteUrl", ""),
            "webId": notification.get("webId", ""),
            "timestamp": datetime.utcnow().isoformat(),
            "rawEvent": notification
        }
    
    def _is_blob_storage_event(self, event: Dict[str, Any]) -> bool:
        """Check if an event is a blob storage event.
        
        Args:
            event: Event data
            
        Returns:
            True if this is a blob storage event
        """
        event_type = event.get('eventType', '')
        return 'Microsoft.Storage.Blob' in event_type
    
    def _parse_azure_blob_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Azure Blob Storage event into our event format.
        
        Args:
            event: Azure Blob Storage event data
            
        Returns:
            Standardized event payload
        """
        data = event.get('data', {})
        
        # Determine our internal event type
        event_type = event.get('eventType', '')
        if 'BlobCreated' in event_type:
            internal_event_type = "document-added"
        elif 'BlobDeleted' in event_type:
            internal_event_type = "document-removed"
        else:
            internal_event_type = "document-changed"
        
        return {
            "eventType": internal_event_type,
            "source": "azure-blob",
            "blobUrl": data.get('url', ''),
            "documentUri": data.get('url', ''),
            "contentType": data.get('contentType', ''),
            "size": data.get('contentLength', 0),
            "azureEventType": event_type,
            "subject": event.get('subject', ''),
            "timestamp": datetime.utcnow().isoformat(),
            "rawEvent": event
        }
    
    async def _trigger_temporal_workflow(self, workflow_id: str, event_payload: Dict[str, Any]):
        """Trigger a Temporal workflow with the event payload.
        
        Args:
            workflow_id: Unique workflow ID
            event_payload: Event data to send to workflow
        """
        try:
            self.logger.info(f"Triggering Temporal workflow {workflow_id}")
            
            # Start the root orchestrator workflow
            handle = await self.temporal_client.start_workflow(
                "RootOrchestratorWorkflow",
                id=workflow_id,
                task_queue=self.task_queue,
            )
            
            # Send the event signal
            await handle.signal("trigger", event_payload)
            
            self.logger.info(f"Successfully triggered workflow {workflow_id}")
            
        except Exception as e:
            self.logger.error(f"Error triggering Temporal workflow {workflow_id}: {e}")
            raise


async def main():
    """Main function to run the webhook event listener."""
    import os
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration from environment
    port = int(os.getenv('WEBHOOK_PORT', '8000'))
    temporal_address = os.getenv('TEMPORAL_ADDRESS', 'temporal:7233')
    webhook_secret = os.getenv('WEBHOOK_SECRET')
    
    # Create and start listener
    listener = WebhookEventListener(
        port=port,
        temporal_address=temporal_address,
        webhook_secret=webhook_secret
    )
    
    await listener.start()


if __name__ == "__main__":
    asyncio.run(main())
