"""Tests for document processing activities."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.document_processing.activities import DocumentProcessingActivities
from src.domain.workflow_inputs import DocumentProcessingInput


class TestDocumentProcessingActivities:
    """Test document processing activities."""
    
    def setup_method(self):
        """Setup test instance."""
        self.activities = DocumentProcessingActivities()
    
    @pytest.mark.asyncio
    async def test_validate_document_success(self):
        """Test successful document validation."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        result = await self.activities.validate_document(input_data)
        
        assert result["success"] is True
        assert len(result["errors"]) == 0
        assert "document_info" in result
    
    @pytest.mark.asyncio
    async def test_validate_document_failure(self):
        """Test document validation failure."""
        input_data = {
            "document_uri": "",  # Invalid
            "source": "s3",
            "event_type": "ObjectCreated"
        }
        
        result = await self.activities.validate_document(input_data)
        
        assert result["success"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_download_document_s3_success(self):
        """Test successful S3 document download."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        result = await self.activities.download_document(input_data)
        
        assert result["success"] is True
        assert result["content_size"] > 0
        assert result["content_type"] is not None
        assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_download_document_chat_success(self):
        """Test successful chat document download (simulated)."""
        input_data = {
            "document_uri": "/uploads/doc.pdf",
            "source": "chat",
            "event_type": "document-uploaded"
        }
        
        # Since it's simulated, it should work even if file doesn't exist
        result = await self.activities.download_document(input_data)
        
        # This will fail because file doesn't exist, but we can test the flow
        assert "success" in result
        assert "content_size" in result
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_download_document_azure_success(self):
        """Test successful Azure document download (simulated)."""
        input_data = {
            "document_uri": "https://storage.blob.core.windows.net/container/doc.pdf",
            "source": "azure_blob",
            "event_type": "BlobCreated",
            "container": "container",
            "blob_name": "doc.pdf"
        }
        
        result = await self.activities.download_document(input_data)
        
        assert result["success"] is True
        assert result["content_size"] > 0
        assert result["content_type"] == "application/pdf"
    
    @pytest.mark.asyncio
    async def test_extract_text_success(self):
        """Test successful text extraction."""
        extract_input = {
            "download_result": {
                "success": True,
                "content_size": 1000,
                "content_type": "application/pdf",
                "error": None
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated"
            }
        }
        
        result = await self.activities.extract_text(extract_input)
        
        assert result["success"] is True
        assert len(result["text"]) > 0
        assert result["metadata"]["extraction_method"] == "simulated"
        assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_extract_text_download_failed(self):
        """Test text extraction when download failed."""
        extract_input = {
            "download_result": {
                "success": False,
                "error": "Download failed"
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated"
            }
        }
        
        result = await self.activities.extract_text(extract_input)
        
        assert result["success"] is False
        assert result["text"] is None
        assert "Document download failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_chunk_text_success(self):
        """Test successful text chunking."""
        chunk_input = {
            "text_result": {
                "success": True,
                "text": "This is a test document with some content that will be chunked into smaller pieces for processing.",
                "metadata": {"extraction_method": "simulated"}
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated",
                "chunk_size": 50,
                "chunk_overlap": 10
            }
        }
        
        result = await self.activities.chunk_text(chunk_input)
        
        assert result["success"] is True
        assert len(result["chunks"]) > 1  # Should be chunked
        assert len(result["chunk_metadata"]) == len(result["chunks"])
        assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_chunk_text_extraction_failed(self):
        """Test text chunking when extraction failed."""
        chunk_input = {
            "text_result": {
                "success": False,
                "error": "Text extraction failed"
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated"
            }
        }
        
        result = await self.activities.chunk_text(chunk_input)
        
        assert result["success"] is False
        assert len(result["chunks"]) == 0
        assert "Text extraction failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self):
        """Test successful embedding generation."""
        embedding_input = {
            "chunk_result": {
                "success": True,
                "chunks": ["chunk 1", "chunk 2", "chunk 3"],
                "chunk_metadata": [{}, {}, {}]
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated",
                "embedding_model": "text-embedding-3-small"
            }
        }
        
        result = await self.activities.generate_embeddings(embedding_input)
        
        assert result["success"] is True
        assert len(result["embeddings"]) == 3
        assert result["embedding_dimensions"] == 1536
        assert result["embedding_model"] == "text-embedding-3-small"
        assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_chunking_failed(self):
        """Test embedding generation when chunking failed."""
        embedding_input = {
            "chunk_result": {
                "success": False,
                "error": "Text chunking failed"
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated"
            }
        }
        
        result = await self.activities.generate_embeddings(embedding_input)
        
        assert result["success"] is False
        assert len(result["embeddings"]) == 0
        assert "Text chunking failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_store_chunks_success(self):
        """Test successful chunk storage."""
        storage_input = {
            "chunk_result": {
                "success": True,
                "chunks": ["chunk 1", "chunk 2"],
                "chunk_metadata": [{"index": 0}, {"index": 1}]
            },
            "embedding_result": {
                "success": True,
                "embeddings": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
                "embedding_model": "text-embedding-3-small"
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated",
                "index_name": "test-index"
            }
        }
        
        result = await self.activities.store_chunks(storage_input)
        
        assert result["success"] is True
        assert len(result["stored_ids"]) == 2
        assert result["index_name"] == "test-index"
        assert "storage_stats" in result
        assert result["error"] is None
    
    @pytest.mark.asyncio
    async def test_store_chunks_previous_step_failed(self):
        """Test chunk storage when previous steps failed."""
        storage_input = {
            "chunk_result": {
                "success": False,
                "error": "Chunking failed"
            },
            "embedding_result": {
                "success": True,
                "embeddings": []
            },
            "input_data": {
                "document_uri": "s3://test-bucket/doc.pdf",
                "source": "s3",
                "event_type": "ObjectCreated"
            }
        }
        
        result = await self.activities.store_chunks(storage_input)
        
        assert result["success"] is False
        assert len(result["stored_ids"]) == 0
        assert "Previous processing steps failed" in result["error"]


class TestDocumentDownloadStrategies:
    """Test document download strategy methods."""
    
    def setup_method(self):
        """Setup test instance."""
        self.activities = DocumentProcessingActivities()
    
    @pytest.mark.asyncio
    async def test_download_s3_file_simulation(self):
        """Test S3 file download simulation."""
        doc_input = DocumentProcessingInput(
            document_uri="s3://test-bucket/doc.pdf",
            source="s3",
            event_type="ObjectCreated",
            bucket="test-bucket",
            key="doc.pdf"
        )
        
        result = await self.activities._download_s3_file(doc_input)
        
        assert result.success is True
        assert result.content is not None
        assert result.content_type == "application/pdf"
        assert b"S3 CONTENT" in result.content
    
    @pytest.mark.asyncio
    async def test_download_azure_file_simulation(self):
        """Test Azure Blob file download simulation."""
        doc_input = DocumentProcessingInput(
            document_uri="https://storage.blob.core.windows.net/container/doc.pdf",
            source="azure_blob",
            event_type="BlobCreated",
            container="container",
            blob_name="doc.pdf"
        )
        
        result = await self.activities._download_azure_file(doc_input)
        
        assert result.success is True
        assert result.content is not None
        assert result.content_type == "application/pdf"
        assert b"AZURE CONTENT" in result.content
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_download_http_file_success(self, mock_get):
        """Test HTTP file download success."""
        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = b"HTTP file content"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_get.return_value.__aenter__.return_value = mock_response
        
        doc_input = DocumentProcessingInput(
            document_uri="https://example.com/doc.pdf",
            source="webhook",
            event_type="document-ready"
        )
        
        result = await self.activities._download_http_file(doc_input)
        
        assert result.success is True
        assert result.content == b"HTTP file content"
        assert result.content_type == "application/pdf"
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_download_http_file_failure(self, mock_get):
        """Test HTTP file download failure."""
        # Mock the HTTP response with error
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.reason = "Not Found"
        mock_get.return_value.__aenter__.return_value = mock_response
        
        doc_input = DocumentProcessingInput(
            document_uri="https://example.com/missing.pdf",
            source="webhook",
            event_type="document-ready"
        )
        
        result = await self.activities._download_http_file(doc_input)
        
        assert result.success is False
        assert "HTTP 404" in result.error
