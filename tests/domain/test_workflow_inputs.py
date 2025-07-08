"""Test the new dataclass-based workflow inputs."""

from src.domain.workflow_inputs import DocumentProcessingInput


def test_document_processing_input_creation():
    """Test creating DocumentProcessingInput with various parameters."""
    # Test with full parameters
    input_full = DocumentProcessingInput(
        document_uri="s3://my-bucket/documents/test.pdf",
        source="s3",
        event_type="s3:ObjectCreated:Put",
        bucket="my-bucket",
        key="documents/test.pdf",
        size=1024000,
        content_type="application/pdf",
        timestamp="2024-01-15T10:30:00Z",
        chunk_size=1500,
        chunk_overlap=150,
        embedding_model="text-embedding-3-large",
        index_name="documents",
        additional_context={
            "user_id": "user123",
            "upload_source": "web_ui"
        }
    )
    
    assert input_full.document_uri == "s3://my-bucket/documents/test.pdf"
    assert input_full.source == "s3"
    assert input_full.event_type == "s3:ObjectCreated:Put"
    assert input_full.bucket == "my-bucket"
    assert input_full.key == "documents/test.pdf"
    assert input_full.size == 1024000
    assert input_full.content_type == "application/pdf"
    assert input_full.chunk_size == 1500
    assert input_full.chunk_overlap == 150
    assert input_full.embedding_model == "text-embedding-3-large"
    assert input_full.index_name == "documents"
    assert input_full.additional_context["user_id"] == "user123"
    
    # Test with minimal required fields
    input_minimal = DocumentProcessingInput(
        document_uri="https://example.com/doc.txt",
        source="azure-blob",
        event_type="Microsoft.Storage.BlobCreated"
    )
    assert input_minimal.document_uri == "https://example.com/doc.txt"
    assert input_minimal.source == "azure-blob"
    assert input_minimal.event_type == "Microsoft.Storage.BlobCreated"
    assert input_minimal.bucket is None
    assert input_minimal.chunk_size == 1000  # default value
    assert input_minimal.chunk_overlap == 200  # default value
    assert input_minimal.embedding_model == "text-embedding-3-small"  # default value


def test_backwards_compatibility():
    """Test that the dataclasses support backwards compatibility."""
    # Test that we can create instances with partial data
    input_partial = DocumentProcessingInput(
        document_uri="https://example.com/legacy.pdf",
        source="legacy_system",
        event_type="document-uploaded",
        additional_context={"legacy_data": True}
    )
    
    assert input_partial.document_uri == "https://example.com/legacy.pdf"
    assert input_partial.source == "legacy_system"
    assert input_partial.additional_context["legacy_data"] is True


if __name__ == "__main__":
    test_document_processing_input_creation()
    test_backwards_compatibility()
    print("✅ All workflow input tests passed!")
