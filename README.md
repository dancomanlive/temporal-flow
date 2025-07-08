# Temporal Flow Engine - Event-Driven Workflow Orchestration

## Overview

The Temporal Flow Engine is a configurable, event-driven workflow orchestration platform built with Temporal.io. It implements a Hexagonal Architecture pattern that provides clean separation between core business logic and external adapters, making it easy to integrate with various data sources and event systems.

## 🚀 Quick Navigation

- **[Start Temporal Workflows](#quick-start)** - Get the core platform running in minutes
- **[🤖 AI Chat Assistant](#-ai-chat-assistant---quick-access)** - Interactive AI chatbot for workflow management (requires `temporal-flow-customizations` branch)
- **[Architecture Overview](#architecture)** - System design and components
- **[Event Listeners](#event-listeners)** - External integrations (S3, Azure, webhooks)
- **[Configuration](#configuration)** - Environment setup and customization

## Architecture

```
External Sources → Event Listeners → Domain Workflows (Direct)
     ↓                 ↓                   ↓                    ↓
S3, Azure Blob,    SQS, Service Bus,  Direct Domain       Document Processing,
SharePoint, etc.   HTTP Webhooks       Workflows          Chat Sessions, etc.
```

### Key Components

- **Chat Session Workflows**: Long-running workflows that manage chat conversations and trigger domain workflows
- **Event Listeners**: External services that listen for events from various sources and directly trigger appropriate domain workflows
- **Ports & Adapters**: Abstract interfaces and concrete implementations following hexagonal architecture
- **Domain Workflows**: Business-specific workflows (e.g., document processing, chat sessions)

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
- Chat session worker
- Document processing worker

**Event Listeners (Optional):**
- S3 event listener (requires AWS SQS configuration)
- Azure blob listener (requires Azure Service Bus configuration)  
- Webhook listener (works without configuration, but WEBHOOK_SECRET recommended)

### 2. Test Chat Session Workflows

Test the revolutionary chat workflow system:

```bash
# Run automated tests
python test_chat_workflows.py

# Or test in browser with chat UI
open http://localhost:3001

# Monitor workflows in Temporal UI
open http://localhost:8080
```

### 3. Test Direct Domain Workflow Triggering

Start a document processing workflow directly:
```bash
temporal workflow start \
  --task-queue document_processing-queue \
  --type DocumentProcessingWorkflow \
  --workflow-id test-document-1 \
  --input '{
    "document_uri": "s3://test-bucket/sample.pdf",
    "source": "s3",
    "event_type": "ObjectCreated",
    "bucket": "test-bucket",
    "key": "sample.pdf"
  }'
```
  }'
```

### 3. Monitor Workflows

Open the Temporal Web UI: [http://localhost:8080/namespaces/default/workflows](http://localhost:8080/namespaces/default/workflows)

## 🤖 AI Chat Assistant - Quick Access

**Want to interact with workflows using AI? We have a custom AI chatbot with workflow integration!**

```bash
# Navigate to the AI chatbot
cd vercel_ai_chatbot

# ⚠️ IMPORTANT: Switch to the customizations branch
git checkout temporal-flow-customizations

# Install dependencies and start
pnpm install
pnpm dev
```

**Visit:** [http://localhost:3001](http://localhost:3001)

**Features:**
- 🎯 **Guest users get 3 free messages** before registration
- 🤖 **GPT-4o integration** for Temporal workflow expertise  
- 🔄 **Real-time streaming** responses
- 🛠 **Temporal-specific knowledge** and tools
- 🚀 **NEW: Chat Session Workflows** - Each chat is now a long-running Temporal workflow!

### 🚀 Chat Session Workflows (NEW!)

Each chat conversation is now powered by a **long-running Temporal workflow** that:

- **Persists conversation state** across all messages
- **Receives messages as signals** for reliable, asynchronous processing  
- **Triggers workflows naturally** from conversation content
- **Manages user rate limiting** at the workflow level
- **Integrates seamlessly** with the broader orchestration platform

**Key Benefits:**
- 💾 **Stateful conversations** - Remember full context and history
- ⚡ **Event-driven messaging** - Messages become Temporal signals
- 🔗 **Workflow integration** - "Process this document" → automatically triggers DocumentProcessingWorkflow  
- 🛡 **Enterprise reliability** - Timeouts, retries, and failure handling
- 📊 **Full observability** - Monitor chat sessions in Temporal Web UI

See [Chat Session Workflows Documentation](README-chat-session-workflows.md) for complete architecture details.

> **Note:** The AI chatbot is in the `vercel_ai_chatbot/` subdirectory and requires the `temporal-flow-customizations` branch for our enhanced features (guest user support, registration fixes, workflow integration, etc.).

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
- `document-added` → `document_processing_workflow`
- `document-uploaded` → `document_processing_workflow`
- `data-processing` → `data_processing_workflow`

#### Source Mappings
- `s3` → `document_processing_workflow`
- `azure-blob` → `document_processing_workflow`
- `sharepoint` → `document_processing_workflow`

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
docker compose --profile test run --rm test-runner python -m pytest tests/domain/ -v
docker compose --profile test run --rm test-runner python -m pytest tests/document_processing/ -v

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
pytest tests/domain/
pytest tests/document_processing/
pytest tests/document_processing/
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

The platform includes an AI-powered chat interface (`vercel_ai_chatbot/`) that helps users interact with Temporal workflows using natural language. Built with AI SDK 5 Beta and specialized for Temporal workflow orchestration.

**Features:**
- 🤖 **AI SDK 5 Beta** integration with OpenAI GPT-4o
- 🔄 **Real-time streaming** responses  
- 🛠 **Temporal expertise** - specialized knowledge of workflows, activities, and best practices
- 🎨 **Modern UI** with Next.js and Tailwind CSS
- 🔒 **Secure configuration** with environment variables
- 👤 **Guest user support** - 3 free messages before registration
- 📊 **Database persistence** with PostgreSQL

**Quick Start:**
```bash
# Navigate to the chatbot and start development
cd vercel_ai_chatbot
git checkout temporal-flow-customizations
pnpm dev
```

### AI Chatbot Setup & Customizations

The `vercel_ai_chatbot/` folder contains the official [Vercel AI Chatbot](https://github.com/vercel/ai-chatbot) as a git submodule with two branches:

- **`main`** - Clean upstream Vercel AI Chatbot reference
- **`temporal-flow-customizations`** - Our customized version for Temporal workflows

**Our Customizations:**
- 🎯 **Enhanced guest experience** - 3 messages before registration requirement
- � **OpenAI integration** - Switched from Grok to GPT-4o for better performance
- 🎨 **Improved UX** - Better error handling and registration flow
- � **Database separation** - Uses dedicated `chatbot` database
- 🔧 **API enhancements** - Better streaming and error handling

**Staying Synced with Upstream:**
```bash
# Sync with latest Vercel AI Chatbot updates
cd vercel_ai_chatbot
git checkout main
git pull origin main
git checkout temporal-flow-customizations
git rebase main  # Apply our changes on top of latest upstream
```

**Key Benefits:**
- ✅ **Conflict-free updates** from upstream Vercel repository
- ✅ **Clear customization tracking** with dedicated branch
- ✅ **Easy comparison** between vanilla and customized versions
- ✅ **Maintainable workflow** for ongoing development

See [`CUSTOMIZATIONS.md`](CUSTOMIZATIONS.md) for detailed documentation of all modifications and sync strategies.

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
