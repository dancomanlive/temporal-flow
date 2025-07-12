"""Workflow input types using dataclasses for type safety and evolution."""

from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class SemanticSearchInput:
    """Input for semantic search workflow."""
    query: str
    session_id: str
    user_id: str
    model: str = "text-embedding-ada-002"
    top_k: int = 5
    metadata: Optional[Dict[str, Any]] = None
    additional_context: Optional[Dict[str, Any]] = None


@dataclass
class DocumentProcessingInput:
    """Input for document processing workflow.
    
    Triggered by storage events (S3, Azure Blob, etc.) to process documents
    through chunking, embedding, and indexing pipeline.
    """
    # Document information
    document_uri: str
    source: str  # "s3", "azure_blob", "chat", "webhook", etc.
    event_type: str
    
    # Optional metadata from event
    bucket: Optional[str] = None
    key: Optional[str] = None
    container: Optional[str] = None
    blob_name: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    timestamp: Optional[str] = None
    
    # Chat-specific fields
    user_id: Optional[str] = None
    file_size: Optional[int] = None
    
    # Webhook-specific fields
    webhook_id: Optional[str] = None
    
    # Processing configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "text-embedding-3-small"
    index_name: Optional[str] = None
    
    # Additional context
    additional_context: Optional[Dict[str, Any]] = None
