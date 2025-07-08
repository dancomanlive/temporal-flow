"""Document processing domain services - pure business logic."""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from urllib.parse import urlparse

from ..domain.workflow_inputs import DocumentProcessingInput


@dataclass
class DocumentValidationResult:
    """Result of document validation."""
    is_valid: bool
    errors: List[str]
    document_info: Optional[Dict[str, Any]] = None


@dataclass
class DocumentDownloadResult:
    """Result of document download operation."""
    success: bool
    content: Optional[bytes] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    error: Optional[str] = None


@dataclass
class TextExtractionResult:
    """Result of text extraction from document."""
    success: bool
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class ChunkingResult:
    """Result of text chunking operation."""
    success: bool
    chunks: List[str] = None
    chunk_metadata: List[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class EmbeddingResult:
    """Result of text embedding generation."""
    success: bool
    embeddings: List[List[float]] = None
    error: Optional[str] = None


@dataclass
class StorageResult:
    """Result of document storage operation."""
    success: bool
    stored_ids: List[str] = None
    error: Optional[str] = None


class DocumentValidationService:
    """Validates document processing inputs and URIs."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_input(self, input_data: DocumentProcessingInput) -> DocumentValidationResult:
        """Validate document processing input."""
        errors = []
        
        # Validate required fields
        if not input_data.document_uri:
            errors.append("document_uri is required")
        
        if not input_data.source:
            errors.append("source is required")
            
        if not input_data.event_type:
            errors.append("event_type is required")
        
        # Validate URI based on source
        uri_validation = self._validate_uri(input_data.document_uri, input_data.source)
        if not uri_validation.is_valid:
            errors.extend(uri_validation.errors)
        
        # Validate source-specific fields
        source_validation = self._validate_source_fields(input_data)
        if not source_validation.is_valid:
            errors.extend(source_validation.errors)
        
        return DocumentValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            document_info=uri_validation.document_info
        )
    
    def _validate_uri(self, uri: str, source: str) -> DocumentValidationResult:
        """Validate URI format based on source."""
        errors = []
        document_info = {}
        
        try:
            parsed = urlparse(uri)
            
            if source == "chat":
                # Chat uploads should be local file paths
                if not os.path.isabs(uri):
                    errors.append("Chat upload URI must be absolute path")
                document_info["filename"] = os.path.basename(uri)
                
            elif source == "s3":
                # S3 URIs should use s3:// scheme
                if parsed.scheme != "s3":
                    errors.append("S3 URI must use s3:// scheme")
                if not parsed.netloc:  # bucket
                    errors.append("S3 URI must specify bucket")
                if not parsed.path or parsed.path == "/":
                    errors.append("S3 URI must specify key")
                document_info["bucket"] = parsed.netloc
                document_info["key"] = parsed.path.lstrip("/")
                
            elif source == "azure-blob":
                # Azure Blob URIs should use https://
                if parsed.scheme != "https":
                    errors.append("Azure Blob URI must use https:// scheme")
                if "blob.core.windows.net" not in parsed.netloc:
                    errors.append("Azure Blob URI must use blob.core.windows.net domain")
                document_info["blob_url"] = uri
                
            elif source == "webhook":
                # Webhook URIs should be HTTP/HTTPS
                if parsed.scheme not in ["http", "https"]:
                    errors.append("Webhook URI must use http:// or https:// scheme")
                    
        except Exception as e:
            errors.append(f"Invalid URI format: {e}")
        
        return DocumentValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            document_info=document_info
        )
    
    def _validate_source_fields(self, input_data: DocumentProcessingInput) -> DocumentValidationResult:
        """Validate source-specific required fields."""
        errors = []
        
        if input_data.source == "s3":
            if not input_data.bucket:
                errors.append("bucket is required for S3 source")
            if not input_data.key:
                errors.append("key is required for S3 source")
                
        elif input_data.source == "azure-blob":
            if not input_data.container:
                errors.append("container is required for Azure Blob source")
            if not input_data.blob_name:
                errors.append("blob_name is required for Azure Blob source")
        
        return DocumentValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )


class DocumentProcessingService:
    """Core document processing business logic."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.validation_service = DocumentValidationService()
    
    def prepare_processing(self, input_data: DocumentProcessingInput) -> DocumentValidationResult:
        """Prepare and validate document for processing."""
        self.logger.info(f"Preparing document processing for: {input_data.document_uri}")
        
        # Validate input
        validation = self.validation_service.validate_input(input_data)
        if not validation.is_valid:
            self.logger.error(f"Validation failed: {validation.errors}")
            return validation
        
        self.logger.info(f"Document validation passed for source: {input_data.source}")
        return validation
    
    def determine_download_strategy(self, source: str) -> str:
        """Determine download strategy based on source."""
        strategies = {
            "chat": "local_file",
            "s3": "s3_download", 
            "azure_blob": "azure_download",  # Fixed: use underscore to match test data
            "azure-blob": "azure_download",  # Also support hyphen version for compatibility
            "webhook": "http_download",
            "sharepoint": "http_download"
        }
        return strategies.get(source, "http_download")
    
    def create_chunk_metadata(self, 
                            chunk_text: str, 
                            chunk_index: int, 
                            input_data: DocumentProcessingInput,
                            document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create metadata for a text chunk."""
        return {
            "chunk_index": chunk_index,
            "chunk_size": len(chunk_text),
            "source": input_data.source,
            "document_uri": input_data.document_uri,
            "event_type": input_data.event_type,
            "timestamp": input_data.timestamp,
            "document_metadata": document_metadata,
            "processing_config": {
                "chunk_size": input_data.chunk_size,
                "chunk_overlap": input_data.chunk_overlap,
                "embedding_model": input_data.embedding_model
            },
            "user_context": input_data.additional_context if input_data.source == "chat" else None
        }
    
    def calculate_processing_stats(self, 
                                 chunks: List[str], 
                                 embeddings: List[List[float]]) -> Dict[str, Any]:
        """Calculate processing statistics."""
        return {
            "total_chunks": len(chunks),
            "total_characters": sum(len(chunk) for chunk in chunks),
            "embedding_dimensions": len(embeddings[0]) if embeddings else 0,
            "average_chunk_size": sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0
        }
