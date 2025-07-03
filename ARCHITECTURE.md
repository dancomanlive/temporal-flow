# Domain Services + Activity Adapters Pattern

## The Problem
Mixing business logic with Temporal infrastructure creates:
- Duplicated logic across layers
- Hard-to-test code (requires Temporal)
- Tight coupling to framework

## ✅ Solution: Clean Separation

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

class OrchestratorDomainService:
    """Coordinates domain operations."""
    
    def process_event_for_routing(self, raw_event: Any) -> tuple[ValidationResult, RoutingResult]:
        validation = self.validation_service.validate_event(raw_event)
        routing = self.routing_service.route_event(validation.normalized_event) if validation.is_valid else None
        return validation, routing
```

## Activity Adapters (Thin Delegation)

```python
class RootOrchestratorActivities:
    """Thin adapters - delegate everything to domain services."""
    
    def __init__(self):
        self.domain_service = OrchestratorDomainService()
    
    @activity.defn
    async def validate_event(self, params: ValidateEventParams) -> ValidateEventResult:
        # Log (infrastructure concern)
        activity.logger.info(f"Validating event: {params.event}")
        
        # DELEGATE - no business logic here
        result = self.domain_service.validation_service.validate_event(params.event)
        
        # Convert to Temporal result
        return ValidateEventResult(valid=result.is_valid, errors=result.errors)
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
    result = service.validate_event({"eventType": "incident"})
    assert result.is_valid is True

# Minimal activity tests
async def test_activity_delegation():
    activities = RootOrchestratorActivities()
    result = await activities.validate_event({"event": {"eventType": "test"}})
    assert result.valid is True
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
