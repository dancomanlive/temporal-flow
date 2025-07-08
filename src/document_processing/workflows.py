"""Document processing workflow implementation."""

from typing import Dict, Any
from temporalio import workflow
from datetime import timedelta

from .activities import DocumentProcessingActivities
from ..domain.workflow_inputs import DocumentProcessingInput


@workflow.defn
class DocumentProcessingWorkflow:
    """Workflow for processing documents from various sources.
    
    Handles documents from:
    - Chat uploads (local files)
    - S3 storage events
    - Azure Blob storage events  
    - Webhook notifications
    """
    
    def __init__(self):
        self.activities = DocumentProcessingActivities()
    
    def _safe_log(self, message: str, level: str = "info"):
        """Safe logging that doesn't fail during testing."""
        try:
            if level == "error":
                workflow.logger.error(message)
            else:
                workflow.logger.info(message)
        except Exception:
            # Ignore logging failures during testing
            pass
    
    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main workflow execution."""
        self._safe_log(f"Starting document processing workflow for: {input_data}")
        
        try:
            # Convert input to dataclass for validation
            doc_input = DocumentProcessingInput(**input_data)
            self._safe_log(f"Processing document from {doc_input.source}: {doc_input.document_uri}")
            
            # Step 1: Validate document input
            validation_result = await workflow.execute_activity(
                self.activities.validate_document,
                input_data,
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            if not validation_result["success"]:
                self._safe_log(f"Document validation failed: {validation_result['errors']}", "error")
                return {
                    "success": False,
                    "step": "validation",
                    "error": validation_result["errors"],
                    "document_uri": doc_input.document_uri,
                    "source": doc_input.source
                }
            
            self._safe_log("Document validation passed")
            
            # Step 2: Download document
            download_result = await workflow.execute_activity(
                self.activities.download_document,
                input_data,
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            if not download_result["success"]:
                self._safe_log(f"Document download failed: {download_result['error']}", "error")
                return {
                    "success": False,
                    "step": "download",
                    "error": download_result["error"],
                    "document_uri": doc_input.document_uri,
                    "source": doc_input.source
                }
            
            self._safe_log(f"Document downloaded: {download_result['content_size']} bytes")
            
            # Step 3: Extract text from document
            extract_input = {
                "download_result": download_result,
                "input_data": input_data
            }
            text_result = await workflow.execute_activity(
                self.activities.extract_text,
                extract_input,
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            if not text_result["success"]:
                self._safe_log(f"Text extraction failed: {text_result['error']}", "error")
                return {
                    "success": False,
                    "step": "text_extraction",
                    "error": text_result["error"],
                    "document_uri": doc_input.document_uri,
                    "source": doc_input.source
                }
            
            self._safe_log(f"Text extracted: {len(text_result['text'])} characters")
            
            # Step 4: Chunk text for embedding
            chunk_input = {
                "text_result": text_result,
                "input_data": input_data
            }
            chunk_result = await workflow.execute_activity(
                self.activities.chunk_text,
                chunk_input,
                start_to_close_timeout=timedelta(minutes=5)
            )
            
            if not chunk_result["success"]:
                self._safe_log(f"Text chunking failed: {chunk_result['error']}", "error")
                return {
                    "success": False,
                    "step": "chunking",
                    "error": chunk_result["error"],
                    "document_uri": doc_input.document_uri,
                    "source": doc_input.source
                }
            
            self._safe_log(f"Text chunked: {len(chunk_result['chunks'])} chunks")
            
            # Step 5: Generate embeddings
            embedding_input = {
                "chunk_result": chunk_result,
                "input_data": input_data
            }
            embedding_result = await workflow.execute_activity(
                self.activities.generate_embeddings,
                embedding_input,
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            if not embedding_result["success"]:
                self._safe_log(f"Embedding generation failed: {embedding_result['error']}", "error")
                return {
                    "success": False,
                    "step": "embedding",
                    "error": embedding_result["error"],
                    "document_uri": doc_input.document_uri,
                    "source": doc_input.source
                }
            
            self._safe_log(f"Embeddings generated: {len(embedding_result['embeddings'])} vectors")
            
            # Step 6: Store chunks and embeddings
            storage_input = {
                "chunk_result": chunk_result,
                "embedding_result": embedding_result,
                "input_data": input_data
            }
            storage_result = await workflow.execute_activity(
                self.activities.store_chunks,
                storage_input,
                start_to_close_timeout=timedelta(minutes=10)
            )
            
            if not storage_result["success"]:
                self._safe_log(f"Chunk storage failed: {storage_result['error']}", "error")
                return {
                    "success": False,
                    "step": "storage",
                    "error": storage_result["error"],
                    "document_uri": doc_input.document_uri,
                    "source": doc_input.source
                }
            
            self._safe_log(f"Chunks stored: {len(storage_result['stored_ids'])} documents indexed")
            
            # Success! Return processing summary
            return {
                "success": True,
                "document_uri": doc_input.document_uri,
                "source": doc_input.source,
                "event_type": doc_input.event_type,
                "processing_summary": {
                    "content_size": download_result["content_size"],
                    "content_type": download_result["content_type"],
                    "text_length": len(text_result["text"]),
                    "chunks_created": len(chunk_result["chunks"]),
                    "embeddings_generated": len(embedding_result["embeddings"]),
                    "chunks_stored": len(storage_result["stored_ids"]),
                    "storage_stats": storage_result["storage_stats"],
                    "index_name": storage_result["index_name"]
                },
                "stored_ids": storage_result["stored_ids"],
                "user_context": doc_input.additional_context if doc_input.source == "chat" else None
            }
            
        except Exception as e:
            self._safe_log(f"Workflow execution failed: {e}", "error")
            return {
                "success": False,
                "step": "workflow_execution",
                "error": str(e),
                "document_uri": input_data.get("document_uri", "unknown"),
                "source": input_data.get("source", "unknown")
            }
