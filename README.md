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

# Start core services (Temporal + workers) - Always works
docker compose up -d

# Optional: Start with event listeners (only if external services configured)
docker compose --profile listeners up -d
```

**Core Services Include:**
- Temporal server & UI
- PostgreSQL database  
- Root orchestrator worker
- Incident workflow worker

**Event Listeners (Optional):**
- S3 event listener (requires AWS SQS configuration)
- Azure blob listener (requires Azure Service Bus configuration)  
- Webhook listener (works without configuration, but WEBHOOK_SECRET recommended)

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

### 4. Run Tests (Optional)

Validate everything works with the test suite:

```bash
# Run all tests in Docker (recommended)
./run_docker_tests.sh

# Or run tests locally
./run_tests.sh
```

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

Event listeners are **optional components** that connect external services to the Temporal Flow Engine. They start only when properly configured and gracefully shut down when configuration is missing.

### Core vs Event Listeners

**Core Services (Always Start):**
- ✅ Temporal server & workers
- ✅ PostgreSQL database  
- ✅ Root orchestrator
- ✅ Domain workflows

**Event Listeners (Start Only When Configured):**
- 🔧 S3 Event Listener - requires `SQS_QUEUE_URL`
- 🔧 Azure Blob Listener - requires `AZURE_SERVICEBUS_CONNECTION_STRING`
- 🔧 Webhook Listener - optional `WEBHOOK_SECRET`

### Deployment Options

```bash
# Option 1: Core services only (no external integrations)
docker compose up -d

# Option 2: Core + specific listeners
docker compose up -d  # Core first
export SQS_QUEUE_URL="https://sqs.region.amazonaws.com/account-id/queue-name"
docker compose up s3-listener -d  # Add S3 listener

# Option 3: Core + all listeners (when all external services configured)
docker compose --profile listeners up -d
```

### S3 Event Listener

Monitors SQS queue for S3 notifications:

```bash
# Configure environment
export SQS_QUEUE_URL="https://sqs.region.amazonaws.com/account-id/queue-name"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}"

# Run listener
docker compose up s3-listener -d
# OR: python -m src.listeners.s3_event_listener
```

### Azure Blob Listener

Monitors Service Bus for blob events:

```bash
# Configure environment
export AZURE_SERVICEBUS_CONNECTION_STRING="Endpoint=sb://your-namespace.servicebus.windows.net/;SharedAccessKeyName=..."
export AZURE_SERVICEBUS_TOPIC="blob-events"
export AZURE_SERVICEBUS_SUBSCRIPTION="temporal-subscription"

# Run listener
docker compose up azure-listener -d
# OR: python -m src.listeners.azure_blob_listener
```

### HTTP Webhook Listener

HTTP server for webhook notifications:

```bash
# Configure environment (optional)
export WEBHOOK_PORT="8000"
export WEBHOOK_SECRET="${WEBHOOK_SECRET}"  # Optional but recommended for production

# Run listener
docker compose up webhook-listener -d
# OR: python -m src.listeners.webhook_listener
```

### Graceful Configuration Handling

When environment variables are missing, listeners behave gracefully:

**S3 Listener without `SQS_QUEUE_URL`:**
```
WARNING - SQS_QUEUE_URL environment variable is not set
INFO - S3 Event Listener will not start without SQS configuration
INFO - To enable S3 event listening, set SQS_QUEUE_URL environment variable
INFO - S3 Event Listener shutting down gracefully...
```

**Azure Listener without `AZURE_SERVICEBUS_CONNECTION_STRING`:**
```
WARNING - AZURE_SERVICEBUS_CONNECTION_STRING environment variable is not set
INFO - Azure Blob Event Listener will not start without Service Bus configuration
INFO - To enable Azure blob event listening, set AZURE_SERVICEBUS_CONNECTION_STRING
INFO - Azure Blob Event Listener shutting down gracefully...
```

**Webhook Listener without `WEBHOOK_SECRET`:**
```
WARNING - WEBHOOK_SECRET environment variable is not set
INFO - Webhook listener will start without signature verification
INFO - For production, set WEBHOOK_SECRET environment variable
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
    aws_access_key_id="${AWS_ACCESS_KEY_ID}",
    aws_secret_access_key="${AWS_SECRET_ACCESS_KEY}",
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

### Docker Testing (Recommended)

Run tests in a containerized environment identical to production:

```bash
# Quick test run using the script
./run_docker_tests.sh

# Or run directly with docker compose
docker compose --profile test run --rm test-runner

# Run specific test suites
docker compose --profile test run --rm test-runner python -m pytest tests/domain/ -v
docker compose --profile test run --rm test-runner python -m pytest tests/root_orchestrator/ -v
docker compose --profile test run --rm test-runner python -m pytest tests/incident_workflow/ -v

# Run tests with detailed coverage report
docker compose --profile test run --rm test-runner python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
```

**Benefits of Docker Testing:**
- ✅ Consistent environment across development and CI/CD
- ✅ No local Python environment setup required
- ✅ Same Docker image used for testing and production
- ✅ Automatic dependency isolation

The HTML coverage report will be available at `htmlcov/index.html`.

### Local Testing (Development Alternative)

For rapid development iterations, you can also run tests locally:

```bash
# Using the shell script (sets up venv automatically)
./run_tests.sh

# Or directly with pytest (requires local Python setup)
pytest
pytest tests/domain/
pytest tests/root_orchestrator/
pytest tests/incident_workflow/
```

## Event-Driven Architecture

The Root Orchestrator provides a modern, configuration-driven approach to workflow orchestration with these features:

1. **Configuration-driven routing** instead of hardcoded logic
2. **Event validation** before processing
3. **Multiple event sources** support
4. **Hexagonal architecture** for clean separation of concerns
5. **External event listeners** instead of internal polling

## Chat UI and AI Integration

### Temporal Flow Chat Assistant

The platform includes an AI-powered chat interface (`chat-ui/`) that helps users interact with Temporal workflows using natural language. Built with AI SDK 5 Beta and specialized for Temporal workflow orchestration.

**Features:**
- 🤖 **AI SDK 5 Beta** integration with OpenAI
- 🔄 **Real-time streaming** responses  
- 🛠 **Temporal expertise** - specialized knowledge of workflows, activities, and best practices
- 🎨 **Modern UI** with Next.js and Tailwind CSS
- 🔒 **Secure configuration** with environment variables

**Quick Start:**
```bash
# Start the AI chatbot reference (recommended - includes all AI SDK 5 features)
./run_chat_ui.sh

# Or start the simple chat UI (basic implementation, works immediately)  
./run_simple_chat_ui.sh

# Or with Docker (simple version only)
docker compose --profile ui up -d
```

### AI SDK 5 Reference Implementation

The `ai-chatbot-reference/` folder contains the official [Vercel AI Chatbot](https://github.com/vercel/ai-chatbot) as a reference implementation for learning advanced AI SDK 5 patterns.

**Why This Reference?**
- 📚 **Learning resource** for AI SDK 5 best practices
- 🔍 **Feature comparison** with our simplified implementation  
- 🛠 **Advanced patterns** like tool calling, multi-modal support, and database integration
- 💡 **Inspiration** for future enhancements

**Key Differences:**
| Feature | Our Chat-UI | Vercel Reference |
|---------|-------------|------------------|
| **Purpose** | Temporal workflow assistance | General-purpose chatbot |
| **Complexity** | Simple, focused | Full-featured application |
| **Database** | Stateless | PostgreSQL with persistence |
| **Authentication** | None | Complete user management |
| **Tools** | None | Web search, code execution |
| **File Support** | None | Images, documents, CSV |

**Staying Synced:**
```bash
# Update reference implementation
git sync-chatbot
```

See [`ai-chatbot-reference/README-REFERENCE.md`](ai-chatbot-reference/README-REFERENCE.md) for detailed comparison and learning opportunities.

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
