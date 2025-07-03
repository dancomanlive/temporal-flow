#!/usr/bin/env python3
"""Script to wait for Temporal server to be ready before starting worker."""

import asyncio
import sys
import os
from src.utils import connect_to_temporal_with_retry

async def wait_for_temporal():
    """Wait for Temporal server to be ready."""
    temporal_address = os.environ.get("TEMPORAL_ADDRESS", "temporal:7233")
    
    try:
        # For health checks, use shorter timeout
        if len(sys.argv) > 1 and sys.argv[1] == "--health-check":
            await connect_to_temporal_with_retry(temporal_address, max_retries=1, initial_delay=1.0)
        else:
            print(f"Waiting for Temporal server at {temporal_address} to be ready...")
            await connect_to_temporal_with_retry(temporal_address, max_retries=30, initial_delay=2.0)
            print("Temporal server is ready!")
        return True
    except Exception as e:
        if not (len(sys.argv) > 1 and sys.argv[1] == "--health-check"):
            print(f"Failed to connect to Temporal: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(wait_for_temporal())
    sys.exit(0 if success else 1)
