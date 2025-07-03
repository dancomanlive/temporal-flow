#!/usr/bin/env python3
"""Test script to verify the connection retry logic works."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.utils import connect_to_temporal_with_retry

async def test_connection():
    """Test connection to Temporal with retry logic."""
    print("Testing connection to Temporal server...")
    
    try:
        await connect_to_temporal_with_retry("temporal:7233", max_retries=5, initial_delay=1.0)
        print("✅ Connection successful!")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
