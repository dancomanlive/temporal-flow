# Temporal Flow Engine - Event-Driven Workflow Orchestration

## Overview

The Temporal Flow Engine is a configurable, event-driven workflow orchestration platform built with Temporal.io. It implements a Hexagonal Architecture pattern that provides clean separation between core business logic and external adapters, making it easy to integrate with various data sources and event systems.

## Architecture

```
External Sources → Event Listeners → Root Orchestrator → Domain Workflows
     ↓                 ↓                   ↓                    ↓
S3, Azure Blob,    SQS, Service Bus,  Temporal Signals    Incident, Document
SharePoint, etc.   HTTP Webhooks       & Activities        Processing, etc.
```

### Key Components

- **Root Orchestrator**: Configuration-driven workflow router that validates events and routes them to appropriate domain workflows
- **Event Listeners**: External services that listen for events from various sources and trigger Temporal workflows
- **Ports & Adapters**: Abstract interfaces and concrete implementations following hexagonal architecture
- **Domain Workflows**: Business-specific workflows (e.g., incident management, document processing)

## Quick Start

### 1. Build and Start Services

```bash
# Build Docker images
docker compose build --no-cache

# Start core services (Temporal + workers)
docker compose up -d

# Start with event listeners (optional)
docker compose --profile listeners up -d
```

### 2. Test the Root Orchestrator

Start a workflow:
```bash
temporal workflow start \
  --task-queue root_orchestrator-queue \
  --type RootOrchestratorWorkflow \
  --workflow-id test-orchestrator-1 \
  --input '{}'
```

Send an incident event:
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

Send a document processing event:
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

### 3. Monitor Workflows

Open the Temporal Web UI: [http://localhost:8080/namespaces/default/workflows](http://localhost:8080/namespaces/default/workflows)

## Configuration

### Event Routing

The Root Orchestrator routes events based on configuration in `src/domain/workflow_routing.py`:

#### Event Type Mappings
- `incident` → `incident_workflow`
- `document-added` → `document_processing_workflow`
- `document-uploaded` → `document_processing_workflow`
- `data-processing` → `data_processing_workflow`

#### Source Mappings
- `s3` → `document_processing_workflow`
- `azure-blob` → `document_processing_workflow`
- `sharepoint` → `document_processing_workflow`
- `monitoring` → `incident_workflow`

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your configurations
```

## Event Listeners

### S3 Event Listener

Monitors SQS queue for S3 notifications:

```bash
# Configure environment
export SQS_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/123456789/s3-events"
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"

# Run listener
python -m src.listeners.s3_event_listener
```

### Azure Blob Listener

Monitors Service Bus for blob events:

```bash
# Configure environment
export AZURE_SERVICEBUS_CONNECTION_STRING="Endpoint=sb://..."
export AZURE_SERVICEBUS_TOPIC="blob-events"
export AZURE_SERVICEBUS_SUBSCRIPTION="temporal-subscription"

# Run listener
python -m src.listeners.azure_blob_listener
```

### HTTP Webhook Listener

HTTP server for webhook notifications:

```bash
# Configure environment
export WEBHOOK_PORT="8000"
export WEBHOOK_SECRET="your-secret"

# Run listener
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
    aws_access_key_id="your-key",
    aws_secret_access_key="your-secret",
    region_name="us-east-1"
)

# Get document
document = await store.get_document("s3://bucket/path/to/file.txt")
print(f"Content: {document.content}")
print(f"Size: {document.size}")
print(f"Type: {document.content_type}")

# List documents
documents = await store.list_documents("s3://bucket/prefix")
for doc_uri in documents:
    print(f"Found: {doc_uri}")
```

## Testing

Run all tests:
```bash
pytest
```

Run specific test suites:
```bash
# Domain logic tests
pytest tests/domain/

# Root orchestrator tests
pytest tests/root_orchestrator/

# Incident workflow tests
pytest tests/incident_workflow/
```

## Event-Driven Architecture

The Root Orchestrator provides a modern, configuration-driven approach to workflow orchestration with these features:

1. **Configuration-driven routing** instead of hardcoded logic
2. **Event validation** before processing
3. **Multiple event sources** support
4. **Hexagonal architecture** for clean separation of concerns
5. **External event listeners** instead of internal polling

## Documentation

- [Root Orchestrator Guide](README-root-orchestrator.md)
- [Module Structure](README-module-structure.md)
- [Autoscaling Guide](README-autoscaling.md)

## Development

### Adding New Event Sources

1. Create a new listener in `src/listeners/`
2. Implement event parsing to standard format
3. Trigger Root Orchestrator workflow with event signal
4. Add service to `docker-compose.yml`

### Adding New Workflows

1. Create workflow directory in `src/`
2. Implement workflow and activities
3. Add workflow configuration to `src/domain/workflow_routing.py`
4. Update event type or source mappings as needed

### Adding New Document Stores

1. Create adapter in `src/adapters/`
2. Implement `DocumentStore` interface from `src/ports/document_store.py`
3. Add configuration and dependency injection

## Production Deployment

For production deployment:

1. Use external Temporal Cloud or self-hosted Temporal cluster
2. Configure proper secrets management for AWS/Azure credentials
3. Set up monitoring and alerting for event listeners
4. Configure autoscaling for workflow workers
5. Implement proper logging and observability

---

This demonstrates a complete event-driven workflow orchestration platform with clean architecture, configuration-driven routing, and support for multiple event sources.
