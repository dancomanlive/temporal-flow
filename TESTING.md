# Testing Guide for Temporal Flow Engine

This document describes the testing strategy and setup for the Temporal Flow Engine project.

## Overview

The testing strategy follows a **non-rigid unit testing** approach that focuses on testing business logic in isolation while maintaining flexibility for refactoring. Tests are designed to validate contracts and behavior rather than implementation details.

## Testing Philosophy

### 1. **Test Activities, Not Workflows (for unit tests)**
- Complex business logic lives in activities
- Workflows are orchestrators and are tested separately with integration tests
- Activities can be tested in isolation without running Temporal workers

### 2. **Mock External Dependencies**
- File system operations are mocked for fast, reliable tests
- Network calls and external services are mocked
- Tests run independently of environment

### 3. **Focus on Contracts, Not Implementation**
- Tests verify input/output contracts
- Implementation details can change without breaking tests
- Supports confident refactoring

## Test Structure

```
tests/
├── __init__.py
├── coordinator_workflow/
│   ├── __init__.py
│   └── test_activities.py
└── incident_workflow/
    ├── __init__.py
    └── test_activities.py
```

## Running Tests

### Quick Start
```bash
# Run all tests
./run_tests.sh

# Or manually with pytest
PYTHONPATH=. python -m pytest tests/ -v
```

### Requirements
```bash
pip install pytest pytest-asyncio
```

## Test Coverage

### Coordinator Workflow Tests (`tests/coordinator_workflow/test_activities.py`)

#### `choose_workflow` Activity
- ✅ Happy path: valid event_type matches available workflow
- ✅ Case insensitive matching
- ✅ Event type not in available workflows
- ✅ Unknown event types

#### `get_available_workflows` Activity
- ✅ Mocked filesystem with valid workflows
- ✅ Empty directory handling
- ✅ Coordinator workflow exclusion
- ✅ Missing JSON definition files

#### `load_workflow_definition` Activity
- ✅ Successful JSON loading
- ✅ File not found scenarios
- ✅ Invalid JSON handling
- ✅ IO error handling

### Incident Workflow Tests (`tests/incident_workflow/test_activities.py`)

#### All Activities Tested
- ✅ `detect_incident`: with and without context
- ✅ `analyze_logs`: with and without incident_id
- ✅ `send_notification`: various summary scenarios
- ✅ `mark_complete`: completion handling
- ✅ Full workflow simulation: end-to-end activity chain

## Key Testing Patterns

### 1. Mocking File System Operations
```python
@patch("os.path.exists")
@patch("os.path.isdir")
@patch("os.listdir")
async def test_get_available_workflows_with_mocked_fs(
    self, mock_listdir: MagicMock, mock_isdir: MagicMock, mock_exists: MagicMock
):
    # Setup mocks to simulate filesystem
    mock_listdir.return_value = ["incident_workflow", "coordinator_workflow"]
    # ... test logic
```

### 2. Testing Error Conditions
```python
async def test_choose_workflow_not_available(self):
    with pytest.raises(ApplicationError) as excinfo:
        await activities.choose_workflow(params)
    
    assert "No available workflow for this event type" in str(excinfo.value)
    assert excinfo.value.non_retryable is True
```

### 3. Contract-Based Testing
```python
async def test_detect_incident(self):
    result = await activities.detect_incident(context)
    
    # Test the contract: these keys must exist
    assert "incident_id" in result
    assert "severity" in result
    # Don't test specific values unless they're part of the contract
```

## Benefits for Refactoring

### ✅ **Filesystem to Configuration Migration**
When moving from filesystem scanning to configuration-based workflow discovery:
- Delete `test_get_available_workflows_*` tests
- Keep `test_choose_workflow_*` tests (logic remains the same)
- Add new tests for configuration loading

### ✅ **Hexagonal Architecture Support**
Current filesystem tests demonstrate adapter testing patterns:
```python
# Current: Testing filesystem adapter
@patch("os.listdir")
async def test_filesystem_adapter(self, mock_listdir):

# Future: Testing S3 adapter  
@patch("boto3.client")
async def test_s3_adapter(self, mock_s3):
```

### ✅ **Activity Logic Changes**
Tests focus on behavior contracts, so internal logic can change freely:
- Algorithm improvements don't break tests
- Data format changes only affect contract tests
- Performance optimizations are transparent

## Continuous Integration

Tests are designed to run in CI environments:
- No external dependencies (everything mocked)
- Fast execution (< 1 second typical)
- Clear failure messages
- Deterministic results

## Future Testing Considerations

### Integration Tests
For workflow orchestration testing:
```python
# Use Temporal's testing framework
from temporalio.testing import WorkflowEnvironment

async def test_coordinator_workflow_orchestration():
    async with WorkflowEnvironment() as env:
        # Test workflow orchestration logic
```

### Performance Tests
For load testing activities:
```python
# Test activity performance under load
async def test_activity_performance():
    # Measure execution time, memory usage
```

### End-to-End Tests
For full system validation:
```python
# Test with real Temporal server (docker-compose)
# Validate complete workflows with real dependencies
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure PYTHONPATH is set
   PYTHONPATH=. python -m pytest
   ```

2. **Async Test Issues**
   ```bash
   # Ensure pytest-asyncio is installed
   pip install pytest-asyncio
   ```

3. **Mock Not Working**
   ```python
   # Ensure patch targets are correct
   @patch("src.coordinator_workflow.activities.os.listdir")  # Full path
   ```

## Contributing Test Guidelines

1. **Test the contract, not the implementation**
2. **Mock all external dependencies**
3. **Use descriptive test names that explain the scenario**
4. **Include both happy path and error conditions**
5. **Keep tests fast and independent**
6. **Update tests when contracts change, not when implementation changes**

---

This testing foundation provides confidence for refactoring while maintaining a fast development feedback loop.
