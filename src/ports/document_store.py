"""Document store port - Abstract interface for document storage operations."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel


class Document(BaseModel):
    """Represents a document with metadata and content."""
    
    source_uri: str
    content: bytes
    metadata: Dict[str, Any]
    content_type: str
    size: int
    last_modified: Optional[str] = None


class DocumentStore(ABC):
    """Abstract base class for document storage operations.
    
    This port defines the interface for all document storage operations,
    decoupling the core business logic from specific storage implementations.
    """

    @abstractmethod
    async def get_document(self, source_uri: str) -> Document:
        """Retrieve a document from the storage system.
        
        Args:
            source_uri: The URI identifying the document location
            
        Returns:
            Document: The retrieved document with content and metadata
            
        Raises:
            DocumentNotFoundError: If the document doesn't exist
            DocumentAccessError: If access is denied or other retrieval error
        """
        pass

    @abstractmethod
    async def list_documents(self, prefix: str = "", max_results: int = 100) -> list[str]:
        """List documents in the storage system.
        
        Args:
            prefix: Optional prefix to filter documents
            max_results: Maximum number of document URIs to return
            
        Returns:
            List of document URIs
        """
        pass

    @abstractmethod
    async def document_exists(self, source_uri: str) -> bool:
        """Check if a document exists in the storage system.
        
        Args:
            source_uri: The URI identifying the document location
            
        Returns:
            True if document exists, False otherwise
        """
        pass


class DocumentNotFoundError(Exception):
    """Raised when a requested document is not found."""
    pass


class DocumentAccessError(Exception):
    """Raised when document access fails due to permissions or other errors."""
    pass
