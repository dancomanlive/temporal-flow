# Event-Driven Workflow Architecture

## Overview

The Temporal Flow Engine uses an event-driven architecture where external events (S3, Azure Blob, etc.) directly trigger domain-specific workflows. This eliminates the need for a central orchestrator and provides better scalability and maintainability.

## Architecture Principles

### 1. **Direct Workflow Triggering**
- Events trigger workflows directly
- No central orchestrator needed
- Each workflow handles its own domain logic

### 2. **Domain-Specific Workflows**
- `DocumentProcessingWorkflow` - Processes documents (chunking, embedding, indexing)
- `ChatSessionWorkflow` - Manages chat conversations and state

### 3. **Event Listeners**
- S3 event listener
- Azure Blob event listener  
- Webhook event listener
- Each listener routes to appropriate workflows

## Domain Services + Activity Adapters Pattern

```
Activities (Thin)     →    Domain Services (Pure Business Logic)
• Temporal concerns         • Event validation
• Serialization            • Routing decisions  
• Logging/errors           • Data transformation
• Parameter conversion     • Business rules
```

## Domain Services (Pure Business Logic)

```python
class EventValidationService:
    """Pure business logic - no framework dependencies."""
    
    def validate_event(self, event: Any) -> EventValidationResult:
        if not isinstance(event, dict):
            return EventValidationResult(is_valid=False, errors=["Event must be a dictionary"])
        
        # More business rules...
        return EventValidationResult(is_valid=True, errors=[])

class DocumentProcessingService:
    """Coordinates document processing operations."""
    
    def process_document_event(self, event: Any) -> DocumentProcessingInput:
        validation = self.validation_service.validate_event(event)
        if not validation.is_valid:
            raise ValueError(f"Invalid event: {validation.errors}")
            
        return DocumentProcessingInput(
            document_uri=event.get("documentUri"),
            source=event.get("source"),
            event_type=event.get("eventType"),
            # ... other fields
        )
```

## Activity Adapters (Thin Delegation)

```python
class DocumentProcessingActivities:
    """Thin adapters - delegate everything to domain services."""
    
    def __init__(self):
        self.domain_service = DocumentProcessingService()
    
    @activity.defn
    async def download_document(self, params: DownloadParams) -> DownloadResult:
        # Log (infrastructure concern)
        activity.logger.info(f"Downloading document: {params.document_uri}")
        
        # DELEGATE - no business logic here
        result = await self.domain_service.download_document(params.document_uri)
        
        # Convert to Temporal result
        return DownloadResult(success=result.success, content=result.content)
```
```

## Benefits

- **Testable**: Test business logic without Temporal
- **Portable**: Domain services work in any context  
- **Maintainable**: Clear boundaries, single responsibility
- **Framework Independent**: Business logic has zero dependencies

## Testing Strategy

```python
# Fast domain tests - no mocking needed
def test_event_validation():
    service = EventValidationService()
    result = service.validate_event({"eventType": "document"})
    assert result.is_valid is True

# Minimal activity tests
async def test_activity_delegation():
    activities = DocumentProcessingActivities()
    result = await activities.download_document({"document_uri": "s3://test/doc.pdf"})
    assert result.success is True
```

## Anti-Patterns ❌

```python
# DON'T: Business logic in activities
@activity.defn
async def validate_event(self, params):
    if not isinstance(params.event, dict):  # Business logic!
        return ValidateEventResult(valid=False, errors=["Event must be dict"])

# DON'T: Temporal dependencies in domain
class EventValidationService:
    def validate_event(self, event):
        activity.logger.info("Validating...")  # Framework dependency!

# DON'T: Direct external calls in activities  
@activity.defn
async def process_document(self, params):
    doc = await database.get_document(params.doc_id)  # Should be in domain service
```

**Rule**: Activities only handle Temporal concerns. Domain services only handle business logic.
