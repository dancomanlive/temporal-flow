"""Workflow input types using dataclasses for type safety and evolution."""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class IncidentWorkflowInput:
    """Input for the incident workflow.
    
    Using a dataclass allows for backwards-compatible evolution by adding
    optional fields without changing the function signature.
    """
    # Core incident information
    incident_id: Optional[str] = None
    source: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    
    # Event metadata
    event_type: Optional[str] = None
    timestamp: Optional[str] = None
    
    # Additional context (for backwards compatibility)
    additional_context: Optional[Dict[str, Any]] = None


@dataclass
class DocumentProcessingInput:
    """Input for document processing workflow.
    
    Triggered by storage events (S3, Azure Blob, etc.) to process documents
    through chunking, embedding, and indexing pipeline.
    """
    # Document information
    document_uri: str
    source: str  # "s3", "azure-blob", "sharepoint", etc.
    event_type: str
    
    # Optional metadata from event
    bucket: Optional[str] = None
    key: Optional[str] = None
    container: Optional[str] = None
    blob_name: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None
    timestamp: Optional[str] = None
    
    # Processing configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model: str = "text-embedding-3-small"
    index_name: Optional[str] = None
    
    # Additional context
    additional_context: Optional[Dict[str, Any]] = None
