"""Document processing activities - thin adapters around domain services."""

import os
import logging
from typing import Dict, Any
from temporalio import activity
import aiohttp

from .services import (
    DocumentProcessingService,
    DocumentDownloadResult
)
from ..domain.workflow_inputs import DocumentProcessingInput


class DocumentProcessingActivities:
    """Activity adapters for document processing workflow."""
    
    def __init__(self):
        self.domain_service = DocumentProcessingService()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @activity.defn
    async def validate_document(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document processing input."""
        activity.logger.info(f"Validating document: {input_data.get('document_uri')}")
        
        # Convert dict to dataclass
        doc_input = DocumentProcessingInput(**input_data)
        
        # Delegate to domain service
        result = self.domain_service.prepare_processing(doc_input)
        
        return {
            "success": result.is_valid,
            "errors": result.errors,
            "document_info": result.document_info or {}
        }
    
    @activity.defn
    async def download_document(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Download document from various sources."""
        doc_input = DocumentProcessingInput(**input_data)
        activity.logger.info(f"Downloading document from {doc_input.source}: {doc_input.document_uri}")
        
        try:
            strategy = self.domain_service.determine_download_strategy(doc_input.source)
            
            if strategy == "local_file":
                result = await self._download_local_file(doc_input)
            elif strategy == "s3_download":
                result = await self._download_s3_file(doc_input)
            elif strategy == "azure_download":
                result = await self._download_azure_file(doc_input)
            elif strategy == "http_download":
                result = await self._download_http_file(doc_input)
            else:
                result = DocumentDownloadResult(
                    success=False,
                    error=f"Unsupported download strategy: {strategy}"
                )
            
            return {
                "success": result.success,
                "content_size": len(result.content) if result.content else 0,
                "content_type": result.content_type,
                "error": result.error
            }
            
        except Exception as e:
            activity.logger.error(f"Download failed: {e}")
            return {
                "success": False,
                "content_size": 0,
                "content_type": None,
                "error": str(e)
            }
    
    @activity.defn
    async def extract_text(self, extract_input: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from downloaded document.
        
        Args:
            extract_input: Dictionary containing 'download_result' and 'input_data'
        """
        activity.logger.info("Extracting text from document")
        
        download_result = extract_input.get("download_result", {})
        input_data = extract_input.get("input_data", {})
        
        try:
            # For now, simulate text extraction
            # In production, this would use libraries like:
            # - PyPDF2/pdfplumber for PDFs
            # - python-docx for Word docs
            # - openpyxl for Excel
            # - BeautifulSoup for HTML
            
            if not download_result.get("success"):
                return {
                    "success": False,
                    "text": None,
                    "metadata": {},
                    "error": "Document download failed"
                }
            
            # Simulate text extraction based on content type
            content_type = download_result.get("content_type", "").lower()
            
            if "pdf" in content_type:
                extracted_text = f"[PDF TEXT] Simulated text extraction from PDF document. Size: {download_result.get('content_size')} bytes"
            elif "word" in content_type or "docx" in content_type:
                extracted_text = f"[DOCX TEXT] Simulated text extraction from Word document. Size: {download_result.get('content_size')} bytes"
            elif "plain" in content_type or "text" in content_type:
                extracted_text = f"[TEXT] Simulated text extraction from text document. Size: {download_result.get('content_size')} bytes"
            else:
                extracted_text = f"[UNKNOWN] Simulated text extraction from unknown document type. Size: {download_result.get('content_size')} bytes"
            
            # Add sample content for demonstration
            extracted_text += "\n\nThis is simulated document content that would normally be extracted from the actual file. " * 10
            
            metadata = {
                "extraction_method": "simulated",
                "content_type": content_type,
                "original_size": download_result.get("content_size"),
                "extracted_length": len(extracted_text)
            }
            
            return {
                "success": True,
                "text": extracted_text,
                "metadata": metadata,
                "error": None
            }
            
        except Exception as e:
            activity.logger.error(f"Text extraction failed: {e}")
            return {
                "success": False,
                "text": None,
                "metadata": {},
                "error": str(e)
            }
    
    @activity.defn
    async def chunk_text(self, chunk_input: Dict[str, Any]) -> Dict[str, Any]:
        """Chunk text into smaller segments for embedding.
        
        Args:
            chunk_input: Dictionary containing 'text_result' and 'input_data'
        """
        activity.logger.info("Chunking text for embedding")
        
        text_result = chunk_input.get("text_result", {})
        input_data = chunk_input.get("input_data", {})
        
        try:
            if not text_result.get("success"):
                return {
                    "success": False,
                    "chunks": [],
                    "chunk_metadata": [],
                    "error": "Text extraction failed"
                }
            
            text = text_result.get("text", "")
            doc_input = DocumentProcessingInput(**input_data)
            
            # Simple chunking implementation
            # In production, use more sophisticated methods like:
            # - Semantic chunking
            # - Sentence-aware chunking
            # - langchain.text_splitter
            
            chunk_size = doc_input.chunk_size
            chunk_overlap = doc_input.chunk_overlap
            
            chunks = []
            chunk_metadata = []
            
            start = 0
            chunk_index = 0
            
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                
                chunks.append(chunk_text)
                
                # Create metadata for this chunk
                metadata = self.domain_service.create_chunk_metadata(
                    chunk_text, chunk_index, doc_input, text_result.get("metadata", {})
                )
                chunk_metadata.append(metadata)
                
                # Move to next chunk with overlap
                start = end - chunk_overlap
                chunk_index += 1
                
                # Prevent infinite loop
                if start >= len(text) - chunk_overlap:
                    break
            
            activity.logger.info(f"Created {len(chunks)} chunks from {len(text)} characters")
            
            return {
                "success": True,
                "chunks": chunks,
                "chunk_metadata": chunk_metadata,
                "error": None
            }
            
        except Exception as e:
            activity.logger.error(f"Text chunking failed: {e}")
            return {
                "success": False,
                "chunks": [],
                "chunk_metadata": [],
                "error": str(e)
            }
    
    @activity.defn
    async def generate_embeddings(self, embedding_input: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings for text chunks.
        
        Args:
            embedding_input: Dictionary containing 'chunk_result' and 'input_data'
        """
        activity.logger.info("Generating embeddings for chunks")
        
        chunk_result = embedding_input.get("chunk_result", {})
        input_data = embedding_input.get("input_data", {})
        
        try:
            if not chunk_result.get("success"):
                return {
                    "success": False,
                    "embeddings": [],
                    "error": "Text chunking failed"
                }
            
            chunks = chunk_result.get("chunks", [])
            doc_input = DocumentProcessingInput(**input_data)
            
            # Simulate embedding generation
            # In production, this would use:
            # - OpenAI embeddings API
            # - Sentence transformers
            # - Other embedding models
            
            embeddings = []
            embedding_dim = 1536  # OpenAI text-embedding-3-small dimension
            
            for i, chunk in enumerate(chunks):
                # Simulate embedding vector (normally from AI model)
                # Create deterministic "embedding" based on chunk content
                import hashlib
                chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
                
                # Convert hash to numbers between -1 and 1
                embedding = []
                for j in range(embedding_dim):
                    hash_val = int(chunk_hash[j % len(chunk_hash)], 16)
                    embedding.append((hash_val / 15.0) * 2 - 1)  # Normalize to [-1, 1]
                
                embeddings.append(embedding)
            
            activity.logger.info(f"Generated {len(embeddings)} embeddings with {embedding_dim} dimensions")
            
            return {
                "success": True,
                "embeddings": embeddings,
                "embedding_model": doc_input.embedding_model,
                "embedding_dimensions": embedding_dim,
                "error": None
            }
            
        except Exception as e:
            activity.logger.error(f"Embedding generation failed: {e}")
            return {
                "success": False,
                "embeddings": [],
                "error": str(e)
            }
    
    @activity.defn
    async def store_chunks(self, storage_input: Dict[str, Any]) -> Dict[str, Any]:
        """Store processed chunks and embeddings.
        
        Args:
            storage_input: Dictionary containing 'chunk_result', 'embedding_result', and 'input_data'
        """
        activity.logger.info("Storing chunks and embeddings")
        
        chunk_result = storage_input.get("chunk_result", {})
        embedding_result = storage_input.get("embedding_result", {})
        input_data = storage_input.get("input_data", {})
        activity.logger.info("Storing processed document chunks")
        
        try:
            if not chunk_result.get("success") or not embedding_result.get("success"):
                return {
                    "success": False,
                    "stored_ids": [],
                    "error": "Previous processing steps failed"
                }
            
            chunks = chunk_result.get("chunks", [])
            embeddings = embedding_result.get("embeddings", [])
            chunk_metadata = chunk_result.get("chunk_metadata", [])
            doc_input = DocumentProcessingInput(**input_data)
            
            # Simulate storage to vector database
            # In production, this would use:
            # - Pinecone
            # - Weaviate  
            # - Chroma
            # - PostgreSQL with pgvector
            # - Elasticsearch
            
            stored_ids = []
            
            for i, (chunk, embedding, metadata) in enumerate(zip(chunks, embeddings, chunk_metadata)):
                # Generate storage ID
                import uuid
                chunk_id = f"{doc_input.source}_{doc_input.event_type}_{uuid.uuid4().hex[:8]}_{i}"
                
                # Log storage (in production, actually store to vector DB)
                activity.logger.debug(f"Storing chunk {chunk_id}: {len(chunk)} chars, {len(embedding)} dimensions")
                stored_ids.append(chunk_id)
            
            # Calculate final stats
            stats = self.domain_service.calculate_processing_stats(chunks, embeddings)
            
            activity.logger.info(f"Successfully stored {len(stored_ids)} chunks")
            
            return {
                "success": True,
                "stored_ids": stored_ids,
                "storage_stats": stats,
                "index_name": doc_input.index_name or "default-documents",
                "error": None
            }
            
        except Exception as e:
            activity.logger.error(f"Chunk storage failed: {e}")
            return {
                "success": False,
                "stored_ids": [],
                "error": str(e)
            }
    
    # Private helper methods for download strategies
    
    async def _download_local_file(self, doc_input: DocumentProcessingInput) -> DocumentDownloadResult:
        """Download from local filesystem (chat uploads)."""
        try:
            if not os.path.exists(doc_input.document_uri):
                return DocumentDownloadResult(
                    success=False,
                    error=f"File not found: {doc_input.document_uri}"
                )
            
            # Use synchronous file I/O for simplicity in this demo
            with open(doc_input.document_uri, 'rb') as f:
                content = f.read()
            
            # Determine content type from file extension
            _, ext = os.path.splitext(doc_input.document_uri)
            content_type_map = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.txt': 'text/plain',
                '.html': 'text/html',
                '.md': 'text/markdown'
            }
            content_type = content_type_map.get(ext.lower(), 'application/octet-stream')
            
            return DocumentDownloadResult(
                success=True,
                content=content,
                content_type=content_type,
                size=len(content)
            )
            
        except Exception as e:
            return DocumentDownloadResult(
                success=False,
                error=f"Local file download failed: {e}"
            )
    
    async def _download_s3_file(self, doc_input: DocumentProcessingInput) -> DocumentDownloadResult:
        """Download from S3 storage."""
        try:
            # Simulate S3 download
            # In production, use boto3:
            # import boto3
            # s3 = boto3.client('s3')
            # response = s3.get_object(Bucket=doc_input.bucket, Key=doc_input.key)
            # content = response['Body'].read()
            
            simulated_content = f"[S3 CONTENT] Simulated content from s3://{doc_input.bucket}/{doc_input.key}".encode()
            
            return DocumentDownloadResult(
                success=True,
                content=simulated_content,
                content_type=doc_input.content_type or 'application/pdf',
                size=len(simulated_content)
            )
            
        except Exception as e:
            return DocumentDownloadResult(
                success=False,
                error=f"S3 download failed: {e}"
            )
    
    async def _download_azure_file(self, doc_input: DocumentProcessingInput) -> DocumentDownloadResult:
        """Download from Azure Blob Storage."""
        try:
            # Simulate Azure Blob download
            # In production, use azure-storage-blob:
            # from azure.storage.blob import BlobServiceClient
            # blob_client = BlobServiceClient.from_connection_string(conn_str)
            # content = blob_client.download_blob().readall()
            
            simulated_content = f"[AZURE CONTENT] Simulated content from {doc_input.container}/{doc_input.blob_name}".encode()
            
            return DocumentDownloadResult(
                success=True,
                content=simulated_content,
                content_type=doc_input.content_type or 'application/pdf',
                size=len(simulated_content)
            )
            
        except Exception as e:
            return DocumentDownloadResult(
                success=False,
                error=f"Azure Blob download failed: {e}"
            )
    
    async def _download_http_file(self, doc_input: DocumentProcessingInput) -> DocumentDownloadResult:
        """Download from HTTP/HTTPS URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(doc_input.document_uri) as response:
                    if response.status == 200:
                        content = await response.read()
                        content_type = response.headers.get('content-type', 'application/octet-stream')
                        
                        return DocumentDownloadResult(
                            success=True,
                            content=content,
                            content_type=content_type,
                            size=len(content)
                        )
                    else:
                        return DocumentDownloadResult(
                            success=False,
                            error=f"HTTP {response.status}: {response.reason}"
                        )
                        
        except Exception as e:
            return DocumentDownloadResult(
                success=False,
                error=f"HTTP download failed: {e}"
            )
