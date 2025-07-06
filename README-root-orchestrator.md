# Root Orchestrator Workflow Usage

## Overview

The Root Orchestrator Workflow is a generic, configuration-driven workflow that routes incoming events to appropriate domain-specific workflows. It replaces the hardcoded Coordinator Workflow with a flexible, extensible architecture.

## Key Features

- **Configuration-driven routing**: Routes events based on eventType and source
- **Hexagonal architecture**: Clean separation between core logic and external adapters
- **Event validation**: Validates incoming events before processing
- **Dynamic configuration**: Can update routing configuration at runtime
- **Multiple event sources**: Supports S3, Azure Blob, SharePoint, and generic webhooks

## Architecture

```
External Event Sources → Event Listeners → Root Orchestrator → Child Workflows
                    ↓                     ↓                    ↓
                SQS/Service Bus      Temporal Signals     Domain Workflows
```

## Configuration

The Root Orchestrator uses configuration-based routing defined in `src/domain/workflow_routing.py`:

### Default Event Type Mappings
- `incident` → `incident_workflow`
- `document-added` → `document_processing_workflow`
- `document-uploaded` → `document_processing_workflow`
- `data-processing` → `data_processing_workflow`

### Default Source Mappings  
- `s3` → `document_processing_workflow`
- `azure-blob` → `document_processing_workflow`
- `sharepoint` → `document_processing_workflow`
- `monitoring` → `incident_workflow`

## Usage

### 1. Start the Root Orchestrator

```bash
temporal workflow start \
  --task-queue root_orchestrator-queue \
  --type RootOrchestratorWorkflow \
  --workflow-id test-orchestrator-1 \
  --input '{}'
```

### 2. Send Event Signals

#### Incident Event
```bash
temporal workflow signal \
  --workflow-id test-orchestrator-1 \
  --name trigger \
  --input '{
    "eventType": "incident",
    "source": "monitoring",
    "message": "Critical system failure detected"
  }'
```

#### Document Processing Event
```bash
temporal workflow signal \
  --workflow-id test-orchestrator-1 \
  --name trigger \
  --input '{
    "eventType": "document-added",
    "source": "s3",
    "bucket": "my-documents",
    "key": "uploads/document.pdf",
    "documentUri": "s3://my-documents/uploads/document.pdf"
  }'
```

#### Custom Configuration
```bash
temporal workflow signal \
  --workflow-id test-orchestrator-1 \
  --name update_configuration \
  --input '{
    "event_type_mappings": {
      "custom-event": "custom_workflow"
    },
    "workflows": {
      "custom_workflow": {
        "workflow_name": "custom_workflow",
        "workflow_class": "CustomWorkflow",
        "task_queue": "custom-queue",
        "enabled": true
      }
    }
  }'
```

## Event Listeners

### S3 Event Listener

Polls SQS queue for S3 notifications:

```bash
export SQS_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789/s3-events"
export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_HERE"
export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_KEY_HERE"
python -m src.listeners.s3_event_listener
```

### Azure Blob Listener

Listens to Service Bus for blob events:

```bash
export AZURE_SERVICEBUS_CONNECTION_STRING="Endpoint=sb://..."
export AZURE_SERVICEBUS_TOPIC="blob-events"
export AZURE_SERVICEBUS_SUBSCRIPTION="temporal-subscription"
python -m src.listeners.azure_blob_listener
```

### Webhook Listener

HTTP server for webhooks:

```bash
export WEBHOOK_PORT="8000"
export WEBHOOK_SECRET="your-secret"
python -m src.listeners.webhook_listener
```

#### Webhook Endpoints

- `POST /webhook` - Generic webhook endpoint
- `POST /webhook/sharepoint` - SharePoint-specific webhook
- `POST /webhook/azure-eventgrid` - Azure Event Grid webhook
- `GET /health` - Health check

## Document Store Adapters

### S3 Document Store

```python
from src.adapters.s3_document_store import S3DocumentStore

store = S3DocumentStore(
    aws_access_key_id="YOUR_AWS_ACCESS_KEY_HERE",
    aws_secret_access_key="YOUR_AWS_SECRET_KEY_HERE",
    region_name="us-east-1"
)

document = await store.get_document("s3://bucket/path/to/file.txt")
```

## Event Structure

### Standard Event Format

All events processed by the Root Orchestrator follow this structure:

```json
{
  "eventType": "document-added",
  "source": "s3",
  "timestamp": "2025-07-01T12:00:00Z",
  "documentUri": "s3://bucket/file.txt",
  "rawEvent": { ... }
}
```

### Required Fields
- `eventType`: String identifying the type of event
- `source`: String identifying the event source (optional but recommended)

### Common Optional Fields
- `documentUri`: URI to the document (for document events)
- `message`: Human-readable message (for incident events)
- `timestamp`: ISO timestamp of the event
- `rawEvent`: Original event data from the source system

## Migration from Coordinator Workflow

The Root Orchestrator replaces the Coordinator Workflow with these improvements:

1. **Removed filesystem scanning**: No more `get_available_workflows` activity
2. **Configuration-driven routing**: Replaced hardcoded `choose_workflow` logic
3. **Event validation**: Added proper event structure validation
4. **Flexible child workflow execution**: Can route to any configured workflow
5. **External event integration**: Built-in support for multiple event sources

## Monitoring

Monitor workflows in the Temporal Web UI:
- [http://localhost:8080/namespaces/default/workflows](http://localhost:8080/namespaces/default/workflows)

Check logs for event processing and routing decisions.
