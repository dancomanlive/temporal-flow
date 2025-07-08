# Connection Retry and Resilience

This document describes the connection retry mechanism and resilience improvements made to the Temporal Flow Engine.

## Problem

The original error indicated that Temporal workers were failing to connect to the Temporal server during startup:

```
RuntimeError: Failed client connect: Server connection error: tonic::transport::Error(Transport, ConnectError(ConnectError("tcp connect error", 172.18.0.3:7233, Os { code: 111, kind: ConnectionRefused, message: "Connection refused" })))
```

This happens because:
1. Docker Compose `depends_on` only waits for containers to start, not for services to be ready
2. Temporal server takes time to initialize after the container starts
3. Workers try to connect immediately and fail

## Solution

### 1. Connection Retry Utility (`src/utils.py`)

Created a robust connection utility with exponential backoff:

```python
async def connect_to_temporal_with_retry(
    temporal_address: str,
    max_retries: int = 10,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
) -> Client:
```

Features:
- Exponential backoff with configurable parameters
- Maximum retry attempts
- Detailed logging of connection attempts
- Graceful failure after max retries

### 2. Wait Script (`wait_for_temporal.py`)

Created a wait script that can be used both for startup and health checks:

```bash
# Wait for Temporal to be ready (startup)
python wait_for_temporal.py

# Quick health check (for Docker health checks)
python wait_for_temporal.py --health-check
```

### 3. Updated Worker Files

All worker files now use the retry utility:
- `src/document_processing/run_worker.py`
- `src/chat_session/run_worker.py`
- `src/listeners/s3_event_listener.py`
- `src/listeners/azure_blob_listener.py`
- `src/listeners/webhook_listener.py`

### 4. Docker Compose Improvements

Updated `docker-compose.yml` with:
- Wait script before starting workers
- Health checks using the retry utility
- Restart policies (`unless-stopped`)
- Proper startup timing

```yaml
document-processing-worker:
  # ... other config ...
  command: ["sh", "-c", "python wait_for_temporal.py && python -m src.document_processing.run_worker"]
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "python", "wait_for_temporal.py", "--health-check"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

## Benefits

1. **Robust Startup**: Workers wait for Temporal to be ready before starting
2. **Automatic Recovery**: Containers restart automatically if they fail
3. **Health Monitoring**: Health checks ensure containers are working properly
4. **Better Logging**: Clear messages about connection attempts and failures
5. **Consistent Behavior**: All components use the same retry logic

## Testing

Use the test script to verify connection retry works:

```bash
python test_connection.py
```

## Configuration

The retry behavior can be customized by modifying the parameters in `connect_to_temporal_with_retry()`:

- `max_retries`: Maximum number of connection attempts (default: 10)
- `initial_delay`: Initial delay between retries (default: 1.0s)
- `max_delay`: Maximum delay between retries (default: 60.0s)
- `backoff_factor`: Exponential backoff multiplier (default: 2.0)

## Environment Variables

The wait script respects the `TEMPORAL_ADDRESS` environment variable:

```bash
export TEMPORAL_ADDRESS=temporal:7233
python wait_for_temporal.py
```
