"""Tests for document processing workflows."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.document_processing.workflows import DocumentProcessingWorkflow
from src.document_processing.activities import DocumentProcessingActivities


class TestDocumentProcessingWorkflow:
    """Test document processing workflow."""
    
    def setup_method(self):
        """Setup test instance."""
        self.workflow = DocumentProcessingWorkflow()
        self.workflow.activities = MagicMock(spec=DocumentProcessingActivities)
    
    @pytest.mark.asyncio
    async def test_workflow_success_s3_source(self):
        """Test successful workflow execution with S3 source."""
        # Mock activity responses
        self.workflow.activities.validate_document = AsyncMock(return_value={
            "success": True,
            "errors": [],
            "document_info": {"bucket": "test-bucket", "key": "doc.pdf"}
        })
        
        self.workflow.activities.download_document = AsyncMock(return_value={
            "success": True,
            "content_size": 1024,
            "content_type": "application/pdf",
            "error": None
        })
        
        self.workflow.activities.extract_text = AsyncMock(return_value={
            "success": True,
            "text": "Sample document text content",
            "metadata": {"extraction_method": "simulated"},
            "error": None
        })
        
        self.workflow.activities.chunk_text = AsyncMock(return_value={
            "success": True,
            "chunks": ["chunk1", "chunk2"],
            "chunk_metadata": [{"index": 0}, {"index": 1}],
            "error": None
        })
        
        self.workflow.activities.generate_embeddings = AsyncMock(return_value={
            "success": True,
            "embeddings": [[1.0, 2.0], [3.0, 4.0]],
            "embedding_model": "text-embedding-3-small",
            "embedding_dimensions": 2,
            "error": None
        })
        
        self.workflow.activities.store_chunks = AsyncMock(return_value={
            "success": True,
            "stored_ids": ["id1", "id2"],
            "storage_stats": {"total_chunks": 2},
            "index_name": "test-index",
            "error": None
        })
        
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        # Mock workflow.execute_activity to return our mocked responses
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {}},
                {"success": True, "content_size": 1024, "content_type": "application/pdf"},
                {"success": True, "text": "Sample text", "metadata": {}},
                {"success": True, "chunks": ["chunk1"], "chunk_metadata": [{}]},
                {"success": True, "embeddings": [[1.0, 2.0]], "embedding_dimensions": 2},
                {"success": True, "stored_ids": ["id1"], "storage_stats": {}, "index_name": "test"}
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is True
        assert result["document_uri"] == "s3://test-bucket/doc.pdf"
        assert result["source"] == "s3"
        assert "processing_summary" in result
    
    @pytest.mark.asyncio
    async def test_workflow_validation_failure(self):
        """Test workflow failure at validation step."""
        input_data = {
            "document_uri": "",  # Invalid
            "source": "s3",
            "event_type": "ObjectCreated"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.return_value = {
                "success": False,
                "errors": ["document_uri is required"],
                "document_info": {}
            }
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "validation"
        assert "document_uri is required" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_download_failure(self):
        """Test workflow failure at download step."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {}},  # validation success
                {"success": False, "error": "File not found", "content_size": 0}  # download failure
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "download"
        assert "File not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_text_extraction_failure(self):
        """Test workflow failure at text extraction step."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {}},  # validation success
                {"success": True, "content_size": 1024, "content_type": "application/pdf"},  # download success
                {"success": False, "error": "Unsupported file format", "text": None}  # extraction failure
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "text_extraction"
        assert "Unsupported file format" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_chunking_failure(self):
        """Test workflow failure at chunking step."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {}},  # validation success
                {"success": True, "content_size": 1024, "content_type": "application/pdf"},  # download success
                {"success": True, "text": "Sample text", "metadata": {}},  # extraction success
                {"success": False, "error": "Text too short to chunk", "chunks": []}  # chunking failure
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "chunking"
        assert "Text too short to chunk" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_embedding_failure(self):
        """Test workflow failure at embedding step."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {}},  # validation success
                {"success": True, "content_size": 1024, "content_type": "application/pdf"},  # download success
                {"success": True, "text": "Sample text", "metadata": {}},  # extraction success
                {"success": True, "chunks": ["chunk1"], "chunk_metadata": [{}]},  # chunking success
                {"success": False, "error": "Embedding API error", "embeddings": []}  # embedding failure
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "embedding"
        assert "Embedding API error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_storage_failure(self):
        """Test workflow failure at storage step."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {}},  # validation success
                {"success": True, "content_size": 1024, "content_type": "application/pdf"},  # download success
                {"success": True, "text": "Sample text", "metadata": {}},  # extraction success
                {"success": True, "chunks": ["chunk1"], "chunk_metadata": [{}]},  # chunking success
                {"success": True, "embeddings": [[1.0, 2.0]], "embedding_dimensions": 2},  # embedding success
                {"success": False, "error": "Vector database unavailable", "stored_ids": []}  # storage failure
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "storage"
        assert "Vector database unavailable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_exception_handling(self):
        """Test workflow exception handling."""
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = Exception("Unexpected error")
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is False
        assert result["step"] == "workflow_execution"
        assert "Unexpected error" in result["error"]
    
    @pytest.mark.asyncio
    async def test_workflow_chat_source(self):
        """Test workflow with chat source."""
        input_data = {
            "document_uri": "/uploads/user-doc.pdf",
            "source": "chat",
            "event_type": "document-uploaded",
            "user_id": "user-123",
            "file_size": 2048
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {"filename": "user-doc.pdf"}},
                {"success": True, "content_size": 2048, "content_type": "application/pdf"},
                {"success": True, "text": "Chat uploaded content", "metadata": {}},
                {"success": True, "chunks": ["chat chunk"], "chunk_metadata": [{}]},
                {"success": True, "embeddings": [[1.0, 2.0]], "embedding_dimensions": 2},
                {"success": True, "stored_ids": ["chat-id"], "storage_stats": {}, "index_name": "chat-docs"}
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is True
        assert result["source"] == "chat"
        assert result["event_type"] == "document-uploaded"
    
    @pytest.mark.asyncio
    async def test_workflow_azure_source(self):
        """Test workflow with Azure Blob source."""
        input_data = {
            "document_uri": "https://storage.blob.core.windows.net/docs/file.pdf",
            "source": "azure_blob",
            "event_type": "BlobCreated",
            "container": "docs",
            "blob_name": "file.pdf"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {"container": "docs"}},
                {"success": True, "content_size": 4096, "content_type": "application/pdf"},
                {"success": True, "text": "Azure blob content", "metadata": {}},
                {"success": True, "chunks": ["azure chunk"], "chunk_metadata": [{}]},
                {"success": True, "embeddings": [[3.0, 4.0]], "embedding_dimensions": 2},
                {"success": True, "stored_ids": ["azure-id"], "storage_stats": {}, "index_name": "azure-docs"}
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is True
        assert result["source"] == "azure_blob"
        assert result["event_type"] == "BlobCreated"
    
    @pytest.mark.asyncio
    async def test_workflow_webhook_source(self):
        """Test workflow with webhook source."""
        input_data = {
            "document_uri": "https://api.example.com/documents/123/download",
            "source": "webhook",
            "event_type": "document-ready",
            "webhook_id": "webhook-456"
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {"webhook_id": "webhook-456"}},
                {"success": True, "content_size": 8192, "content_type": "application/pdf"},
                {"success": True, "text": "Webhook document content", "metadata": {}},
                {"success": True, "chunks": ["webhook chunk"], "chunk_metadata": [{}]},
                {"success": True, "embeddings": [[5.0, 6.0]], "embedding_dimensions": 2},
                {"success": True, "stored_ids": ["webhook-id"], "storage_stats": {}, "index_name": "webhook-docs"}
            ]
            
            result = await self.workflow.run(input_data)
        
        assert result["success"] is True
        assert result["source"] == "webhook"
        assert result["event_type"] == "document-ready"


class TestWorkflowDataFlow:
    """Test data flow between workflow steps."""
    
    @pytest.mark.asyncio
    async def test_data_flow_between_activities(self):
        """Test that data flows correctly between activities."""
        workflow = DocumentProcessingWorkflow()
        
        input_data = {
            "document_uri": "s3://test-bucket/doc.pdf",
            "source": "s3",
            "event_type": "ObjectCreated",
            "bucket": "test-bucket",
            "key": "doc.pdf",
            "chunk_size": 100,
            "chunk_overlap": 20
        }
        
        with patch('temporalio.workflow.execute_activity') as mock_execute:
            # Mock responses that include data passed between steps
            download_result = {"success": True, "content_size": 1024, "content_type": "application/pdf"}
            text_result = {"success": True, "text": "Sample text content", "metadata": {"length": 18}}
            chunk_result = {"success": True, "chunks": ["chunk1", "chunk2"], "chunk_metadata": [{}, {}]}
            embedding_result = {"success": True, "embeddings": [[1.0, 2.0], [3.0, 4.0]], "embedding_dimensions": 2}
            storage_result = {"success": True, "stored_ids": ["id1", "id2"], "storage_stats": {"total": 2}, "index_name": "test"}
            
            mock_execute.side_effect = [
                {"success": True, "errors": [], "document_info": {}},  # validation
                download_result,  # download
                text_result,      # extract_text
                chunk_result,     # chunk_text
                embedding_result, # generate_embeddings
                storage_result    # store_chunks
            ]
            
            result = await workflow.run(input_data)
            
            # Verify the calls were made with correct data flow
            assert mock_execute.call_count == 6
            
            # Check that extract_text received download_result
            extract_call = mock_execute.call_args_list[2]
            extract_input = extract_call[0][1]  # Second argument is the input data
            assert extract_input["download_result"] == download_result
            assert extract_input["input_data"] == input_data
            
            # Check that chunk_text received text_result
            chunk_call = mock_execute.call_args_list[3]
            chunk_input = chunk_call[0][1]
            assert chunk_input["text_result"] == text_result
            assert chunk_input["input_data"] == input_data
            
            # Check that generate_embeddings received chunk_result
            embedding_call = mock_execute.call_args_list[4]
            embedding_input = embedding_call[0][1]
            assert embedding_input["chunk_result"] == chunk_result
            assert embedding_input["input_data"] == input_data
            
            # Check that store_chunks received both chunk_result and embedding_result
            storage_call = mock_execute.call_args_list[5]
            storage_input = storage_call[0][1]
            assert storage_input["chunk_result"] == chunk_result
            assert storage_input["embedding_result"] == embedding_result
            assert storage_input["input_data"] == input_data
