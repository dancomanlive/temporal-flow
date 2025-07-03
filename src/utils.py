"""Shared utilities for Temporal Flow Engine."""

import asyncio
import logging
from temporalio.client import Client


async def connect_to_temporal_with_retry(
    temporal_address: str,
    max_retries: int = 10,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
) -> Client:
    """
    Connect to Temporal server with exponential backoff retry logic.
    
    Args:
        temporal_address: Address of the Temporal server
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Exponential backoff multiplier
        
    Returns:
        Connected Temporal client
        
    Raises:
        RuntimeError: If connection fails after all retries
    """
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect to Temporal at {temporal_address} (attempt {attempt + 1}/{max_retries})")
            client = await Client.connect(temporal_address)
            logger.info("Successfully connected to Temporal")
            return client
            
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Temporal after {max_retries} attempts: {e}")
                raise RuntimeError(f"Failed to connect to Temporal at {temporal_address} after {max_retries} attempts: {e}")
            
            delay = min(initial_delay * (backoff_factor ** attempt), max_delay)
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f} seconds...")
            await asyncio.sleep(delay)
    
    # This should never be reached due to the raise in the loop
    raise RuntimeError(f"Unexpected error connecting to Temporal at {temporal_address}")
