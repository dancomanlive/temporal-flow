# Workflow Creation Guide

This guide outlines the patterns, conventions, and best practices for creating new workflows in the temporal-flow-engine project. Follow these guidelines to ensure consistency, testability, and maintainability.

## Architecture Overview

The project follows a **Domain-Driven Design (DDD)** pattern with clear separation of concerns:

```
src/
├── domain/                    # Pure business logic, no Temporal dependencies
│   ├── workflow_inputs.py     # Input dataclasses for type safety
│   └── document_store.py      # Domain models
├── {workflow_name}/           # Workflow-specific module
│   ├── __init__.py
│   ├── services.py           # Domain services (pure business logic)
│   ├── activities.py         # Temporal activity adapters
│   ├── workflows.py          # Temporal workflow orchestration
│   └── run_worker.py         # Worker process for this workflow
├── ports/                    # Abstract interfaces
└── adapters/                 # External service implementations
```

## 1. Input Dataclass Definition

### Location: `src/domain/workflow_inputs.py`

Create a dataclass for your workflow input to ensure type safety and evolution:

```python
@dataclass
class YourWorkflowInput:
    """Input for your workflow.
    
    Using a dataclass allows for backwards-compatible evolution by adding
    optional fields without changing the function signature.
    """
    # Required fields first
    primary_field: str
    source: str
    event_type: str
    
    # Optional metadata - allows for different sources
    optional_field: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Configuration with sensible defaults
    config_option: str = "default_value"
    
    # Additional context for backwards compatibility
    additional_context: Optional[Dict[str, Any]] = None
```

**Key Principles:**
- Required fields first, optional fields with defaults
- Use descriptive field names and types
- Include docstring explaining the workflow purpose
- Always include `additional_context` for future extensibility

## 2. Domain Services

### Location: `src/{workflow_name}/services.py`

Domain services contain **pure business logic** with no Temporal dependencies:

```python
"""Domain services for {workflow_name} - pure business logic."""

from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class YourValidationResult:
    """Result of workflow input validation."""
    success: bool
    errors: List[str]
    processed_data: Dict[str, Any]

class YourWorkflowService:
    """Pure business logic for your workflow."""
    
    def validate_input(self, input_data: YourWorkflowInput) -> YourValidationResult:
        """Validate workflow input according to business rules."""
        errors = []
        
        # Implement validation logic
        if not input_data.primary_field:
            errors.append("primary_field is required")
            
        return YourValidationResult(
            success=len(errors) == 0,
            errors=errors,
            processed_data={"validated": True}
        )
    
    def determine_strategy(self, source: str) -> str:
        """Determine processing strategy based on source."""
        strategies = {
            "source1": "strategy1",
            "source2": "strategy2"
        }
        return strategies.get(source, "default_strategy")
```

**Key Principles:**
- No Temporal imports or decorators
- Pure functions that can be unit tested easily
- Return structured results using dataclasses
- Separate validation, business logic, and configuration

## 3. Activity Layer

### Location: `src/{workflow_name}/activities.py`

Activities are **adapters** that wrap domain services for Temporal:

```python
"""Temporal activities for {workflow_name}."""

from typing import Dict, Any
from temporalio import activity
from .services import YourWorkflowService
from ..domain.workflow_inputs import YourWorkflowInput

class YourWorkflowActivities:
    """Temporal activity adapters."""
    
    def __init__(self):
        self.domain_service = YourWorkflowService()
    
    @activity.defn
    async def validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate workflow input."""
        try:
            # Convert to domain input
            workflow_input = YourWorkflowInput(**input_data)
            
            # Call domain service
            result = self.domain_service.validate_input(workflow_input)
            
            # Return structured response
            return {
                "success": result.success,
                "errors": result.errors,
                "processed_data": result.processed_data
            }
            
        except Exception as e:
            activity.logger.error(f"Validation failed: {e}")
            return {
                "success": False,
                "errors": [str(e)],
                "processed_data": {}
            }
    
    @activity.defn
    async def process_step(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a workflow step."""
        try:
            # Extract previous step results if needed
            previous_result = input_data.get("previous_result", {})
            original_input = input_data.get("input_data", {})
            
            # Call domain logic
            result = self.domain_service.process_step(previous_result, original_input)
            
            return {
                "success": True,
                "result": result,
                "error": None
            }
            
        except Exception as e:
            activity.logger.error(f"Processing failed: {e}")
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }
```

**Key Principles:**
- **Single Parameter Pattern**: Activities take one dictionary parameter (Temporal SDK requirement)
- **Structured Error Handling**: Always return success/error structure
- **Domain Service Delegation**: Activities are thin adapters, logic lives in domain services
- **Data Flow Pattern**: Pass previous step results and original input to next steps

## 4. Workflow Orchestration

### Location: `src/{workflow_name}/workflows.py`

Workflows orchestrate the execution of activities:

```python
"""Workflow orchestration for {workflow_name}."""

from typing import Dict, Any
from temporalio import workflow
from datetime import timedelta
from .activities import YourWorkflowActivities
from ..domain.workflow_inputs import YourWorkflowInput

@workflow.defn
class YourWorkflow:
    """Main workflow for {workflow_name}."""
    
    def __init__(self):
        self.activities = YourWorkflowActivities()
    
    def _safe_log(self, message: str, level: str = "info"):
        """Safe logging that doesn't fail during testing."""
        try:
            if level == "error":
                workflow.logger.error(message)
            else:
                workflow.logger.info(message)
        except Exception:
            # Ignore logging failures during testing
            pass
    
    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main workflow execution."""
        self._safe_log(f"Starting {self.__class__.__name__} for: {input_data}")
        
        try:
            # Convert to domain input for validation
            workflow_input = YourWorkflowInput(**input_data)
            
            # Step 1: Validate input
            validation_result = await workflow.execute_activity(
                self.activities.validate_input,
                input_data,
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            if not validation_result["success"]:
                self._safe_log(f"Validation failed: {validation_result['errors']}", "error")
                return {
                    "success": False,
                    "step": "validation",
                    "error": validation_result["errors"],
                    "input": input_data
                }
            
            self._safe_log("Validation passed")
            
            # Step 2: Process workflow step
            process_input = {
                "input_data": input_data,
                "validation_result": validation_result
            }
            
            process_result = await workflow.execute_activity(
                self.activities.process_step,
                process_input,
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            if not process_result["success"]:
                self._safe_log(f"Processing failed: {process_result['error']}", "error")
                return {
                    "success": False,
                    "step": "processing",
                    "error": process_result["error"],
                    "input": input_data
                }
            
            self._safe_log("Processing completed")
            
            # Success response
            return {
                "success": True,
                "workflow_input": workflow_input,
                "results": {
                    "validation": validation_result,
                    "processing": process_result
                }
            }
            
        except Exception as e:
            self._safe_log(f"Workflow execution failed: {e}", "error")
            return {
                "success": False,
                "step": "workflow_execution",
                "error": str(e),
                "input": input_data
            }
```

**Key Principles:**
- **Safe Logging**: Use `_safe_log()` method to prevent test failures
- **Early Returns**: Return immediately on step failures with error context
- **Step Identification**: Include which step failed in error responses
- **Data Flow**: Pass results from previous steps to subsequent activities
- **Timeout Configuration**: Set appropriate timeouts for each activity
- **Structured Responses**: Consistent success/error response format

## 5. Worker Process

### Location: `src/{workflow_name}/run_worker.py`

Worker processes register workflows and activities:

```python
"""Worker process for {workflow_name}."""

import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import YourWorkflow
from .activities import YourWorkflowActivities

async def main():
    """Run the workflow worker."""
    logging.basicConfig(level=logging.INFO)
    
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Create activities instance
    activities = YourWorkflowActivities()
    
    # Create worker
    worker = Worker(
        client,
        task_queue="your-workflow-task-queue",
        workflows=[YourWorkflow],
        activities=[
            activities.validate_input,
            activities.process_step,
        ]
    )
    
    print("Starting Your Workflow worker...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## 6. Testing Strategy

### Create comprehensive tests in `tests/{workflow_name}/`

#### Domain Service Tests (`test_services.py`)
```python
"""Tests for domain services - no Temporal dependencies."""

import pytest
from src.{workflow_name}.services import YourWorkflowService
from src.domain.workflow_inputs import YourWorkflowInput

class TestYourWorkflowService:
    def setup_method(self):
        self.service = YourWorkflowService()
    
    def test_validate_input_success(self):
        """Test successful input validation."""
        input_data = YourWorkflowInput(
            primary_field="valid_value",
            source="test_source",
            event_type="test_event"
        )
        
        result = self.service.validate_input(input_data)
        
        assert result.success is True
        assert len(result.errors) == 0
    
    def test_validate_input_missing_required(self):
        """Test validation with missing required fields."""
        input_data = YourWorkflowInput(
            primary_field="",  # Invalid
            source="test_source",
            event_type="test_event"
        )
        
        result = self.service.validate_input(input_data)
        
        assert result.success is False
        assert "primary_field is required" in result.errors
```

#### Activity Tests (`test_activities.py`)
```python
"""Tests for Temporal activities."""

import pytest
from src.{workflow_name}.activities import YourWorkflowActivities

class TestYourWorkflowActivities:
    def setup_method(self):
        self.activities = YourWorkflowActivities()
    
    @pytest.mark.asyncio
    async def test_validate_input_success(self):
        """Test successful activity execution."""
        input_data = {
            "primary_field": "valid_value",
            "source": "test_source",
            "event_type": "test_event"
        }
        
        result = await self.activities.validate_input(input_data)
        
        assert result["success"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_process_step_with_data_flow(self):
        """Test activity with data from previous steps."""
        input_data = {
            "input_data": {"primary_field": "value"},
            "validation_result": {"success": True, "processed_data": {}}
        }
        
        result = await self.activities.process_step(input_data)
        
        assert result["success"] is True
        assert result["error"] is None
```

#### Workflow Tests (`test_workflows.py`)
```python
"""Tests for workflow orchestration."""

import pytest
from unittest.mock import patch
from src.{workflow_name}.workflows import YourWorkflow

class TestYourWorkflow:
    def setup_method(self):
        self.workflow = YourWorkflow()
    
    @pytest.mark.asyncio
    async def test_workflow_success(self):
        """Test successful workflow execution."""
        input_data = {
            "primary_field": "valid_value",
            "source": "test_source",
            "event_type": "test_event"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "processed_data": {}},  # validation
                {"success": True, "result": "processed", "error": None}  # processing
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is True
        assert "results" in result
    
    @pytest.mark.asyncio
    async def test_workflow_validation_failure(self):
        """Test workflow failure at validation step."""
        input_data = {"primary_field": ""}  # Invalid
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": ["primary_field is required"],
                "processed_data": {}
            }
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "validation"
        assert "primary_field is required" in result["error"]
```

## 7. Integration with Docker

### Update `docker-compose.yml`
```yaml
services:
  your-workflow-worker:
    build: .
    command: python -m src.your_workflow.run_worker
    depends_on:
      - temporal
    environment:
      - TEMPORAL_ADDRESS=temporal:7233
    networks:
      - temporal-network
```

## 8. Common Patterns & Anti-Patterns

### ✅ Do This

1. **Use dataclasses for inputs** - Type safety and evolution
2. **Separate domain logic from Temporal concerns** - Testability
3. **Use structured error responses** - Consistent error handling
4. **Include step identification in failures** - Better debugging
5. **Pass data between activities explicitly** - Clear data flow
6. **Use safe logging in workflows** - Prevent test failures
7. **Test all layers independently** - Domain, Activities, Workflows

### ❌ Avoid This

1. **Don't put business logic in workflows** - Hard to test
2. **Don't use multiple parameters in activities** - Temporal SDK limitation
3. **Don't use bare `except` clauses** - Catches system exceptions
4. **Don't skip input validation** - Runtime errors
5. **Don't ignore data flow between steps** - Inconsistent results
6. **Don't mix domain models with Temporal decorators** - Tight coupling

## 9. Checklist for New Workflows

- [ ] Input dataclass created in `src/domain/workflow_inputs.py`
- [ ] Domain services with pure business logic
- [ ] Activities as thin adapters with single parameter pattern
- [ ] Workflow with safe logging and structured error handling
- [ ] Worker process for registration
- [ ] Comprehensive tests for all layers
- [ ] Docker integration updated
- [ ] Documentation for workflow purpose and usage

## 10. Example File Structure

```
src/your_workflow/
├── __init__.py
├── services.py          # Domain logic (13+ tests)
├── activities.py        # Temporal adapters (17+ tests)  
├── workflows.py         # Orchestration (12+ tests)
└── run_worker.py        # Worker process

tests/your_workflow/
├── __init__.py
├── test_services.py     # Domain logic tests
├── test_activities.py   # Activity tests
└── test_workflows.py    # Workflow orchestration tests
```

This architecture has proven successful with the DocumentProcessingWorkflow, achieving 42/42 passing tests and clean separation of concerns. Follow these patterns for consistent, maintainable, and testable workflows.
