"""Tests for document processing domain services."""

from src.domain.workflow_inputs import DocumentProcessingInput
from src.document_processing.services import (
    DocumentValidationService,
    DocumentProcessingService
)


class TestDocumentValidationService:
    """Test document validation service."""
    
    def setup_method(self):
        self.service = DocumentValidationService()
    
    def test_validate_valid_s3_input(self):
        """Test validation of valid S3 input."""
        input_data = DocumentProcessingInput(
            document_uri="s3://my-bucket/documents/test.pdf",
            source="s3",
            event_type="ObjectCreated",
            bucket="my-bucket",
            key="documents/test.pdf"
        )
        
        result = self.service.validate_input(input_data)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.document_info["bucket"] == "my-bucket"
        assert result.document_info["key"] == "documents/test.pdf"
    
    def test_validate_valid_chat_input(self):
        """Test validation of valid chat upload input."""
        input_data = DocumentProcessingInput(
            document_uri="/tmp/uploads/document.pdf",
            source="chat",
            event_type="document-uploaded",
            additional_context={"userId": "123", "chatId": "chat-456"}
        )
        
        result = self.service.validate_input(input_data)
        
        assert result.is_valid
        assert len(result.errors) == 0
        assert result.document_info["filename"] == "document.pdf"
    
    def test_validate_valid_azure_input(self):
        """Test validation of valid Azure Blob input."""
        input_data = DocumentProcessingInput(
            document_uri="https://storage.blob.core.windows.net/container/blob.pdf",
            source="azure-blob",
            event_type="BlobCreated",
            container="container",
            blob_name="blob.pdf"
        )
        
        result = self.service.validate_input(input_data)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_missing_required_fields(self):
        """Test validation with missing required fields."""
        input_data = DocumentProcessingInput(
            document_uri="",  # Missing
            source="",        # Missing
            event_type=""     # Missing
        )
        
        result = self.service.validate_input(input_data)
        
        assert not result.is_valid
        assert "document_uri is required" in result.errors
        assert "source is required" in result.errors
        assert "event_type is required" in result.errors
    
    def test_validate_invalid_s3_uri(self):
        """Test validation with invalid S3 URI."""
        input_data = DocumentProcessingInput(
            document_uri="http://invalid-s3-uri",  # Wrong scheme
            source="s3",
            event_type="ObjectCreated",
            bucket="my-bucket",
            key="test.pdf"
        )
        
        result = self.service.validate_input(input_data)
        
        assert not result.is_valid
        assert "S3 URI must use s3:// scheme" in result.errors
    
    def test_validate_missing_s3_fields(self):
        """Test validation with missing S3-specific fields."""
        input_data = DocumentProcessingInput(
            document_uri="s3://my-bucket/test.pdf",
            source="s3",
            event_type="ObjectCreated"
            # Missing bucket and key
        )
        
        result = self.service.validate_input(input_data)
        
        assert not result.is_valid
        assert "bucket is required for S3 source" in result.errors
        assert "key is required for S3 source" in result.errors
    
    def test_validate_invalid_azure_uri(self):
        """Test validation with invalid Azure Blob URI."""
        input_data = DocumentProcessingInput(
            document_uri="http://invalid-azure-uri",  # Wrong domain
            source="azure-blob",
            event_type="BlobCreated",
            container="container",
            blob_name="blob.pdf"
        )
        
        result = self.service.validate_input(input_data)
        
        assert not result.is_valid
        assert "Azure Blob URI must use blob.core.windows.net domain" in result.errors


class TestDocumentProcessingService:
    """Test document processing service."""
    
    def setup_method(self):
        self.service = DocumentProcessingService()
    
    def test_prepare_processing_valid_input(self):
        """Test preparing valid input for processing."""
        input_data = DocumentProcessingInput(
            document_uri="s3://my-bucket/test.pdf",
            source="s3",
            event_type="ObjectCreated",
            bucket="my-bucket",
            key="test.pdf"
        )
        
        result = self.service.prepare_processing(input_data)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_prepare_processing_invalid_input(self):
        """Test preparing invalid input for processing."""
        input_data = DocumentProcessingInput(
            document_uri="",  # Invalid
            source="s3",
            event_type="ObjectCreated"
        )
        
        result = self.service.prepare_processing(input_data)
        
        assert not result.is_valid
        assert len(result.errors) > 0
    
    def test_determine_download_strategy(self):
        """Test download strategy determination."""
        assert self.service.determine_download_strategy("chat") == "local_file"
        assert self.service.determine_download_strategy("s3") == "s3_download"
        assert self.service.determine_download_strategy("azure-blob") == "azure_download"
        assert self.service.determine_download_strategy("webhook") == "http_download"
        assert self.service.determine_download_strategy("unknown") == "http_download"
    
    def test_create_chunk_metadata(self):
        """Test chunk metadata creation."""
        input_data = DocumentProcessingInput(
            document_uri="s3://my-bucket/test.pdf",
            source="s3",
            event_type="ObjectCreated",
            bucket="my-bucket",
            key="test.pdf",
            chunk_size=1000,
            chunk_overlap=200,
            embedding_model="text-embedding-3-small"
        )
        
        chunk_text = "This is a test chunk."
        chunk_index = 0
        document_metadata = {"content_type": "application/pdf"}
        
        metadata = self.service.create_chunk_metadata(
            chunk_text, chunk_index, input_data, document_metadata
        )
        
        assert metadata["chunk_index"] == 0
        assert metadata["chunk_size"] == len(chunk_text)
        assert metadata["source"] == "s3"
        assert metadata["document_uri"] == "s3://my-bucket/test.pdf"
        assert metadata["processing_config"]["chunk_size"] == 1000
        assert metadata["processing_config"]["embedding_model"] == "text-embedding-3-small"
        assert metadata["user_context"] is None  # Not a chat upload
    
    def test_create_chunk_metadata_chat_source(self):
        """Test chunk metadata creation for chat uploads."""
        input_data = DocumentProcessingInput(
            document_uri="/tmp/uploads/doc.pdf",
            source="chat",
            event_type="document-uploaded",
            additional_context={"userId": "123", "chatId": "chat-456"}
        )
        
        chunk_text = "This is a test chunk."
        chunk_index = 1
        document_metadata = {"content_type": "application/pdf"}
        
        metadata = self.service.create_chunk_metadata(
            chunk_text, chunk_index, input_data, document_metadata
        )
        
        assert metadata["chunk_index"] == 1
        assert metadata["source"] == "chat"
        assert metadata["user_context"] == {"userId": "123", "chatId": "chat-456"}
    
    def test_calculate_processing_stats(self):
        """Test processing statistics calculation."""
        chunks = ["chunk1", "chunk2 is longer", "chunk3"]
        embeddings = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]]
        
        stats = self.service.calculate_processing_stats(chunks, embeddings)
        
        assert stats["total_chunks"] == 3
        assert stats["total_characters"] == len("chunk1") + len("chunk2 is longer") + len("chunk3")
        assert stats["embedding_dimensions"] == 3
        assert stats["average_chunk_size"] == stats["total_characters"] / 3
