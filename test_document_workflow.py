#!/usr/bin/env python3
"""Test script for DocumentProcessingWorkflow."""

import asyncio
import sys
from temporalio.client import Client


async def test_document_processing_workflow():
    """Test the DocumentProcessingWorkflow with various scenarios."""
    
    # Connect to Temporal
    client = await Client.connect("temporal:7233")
    
    print("🧪 Testing DocumentProcessingWorkflow...")
    
    # Test scenarios
    test_cases = [
        {
            "name": "S3 Document Processing",
            "input": {
                "document_uri": "s3://my-bucket/documents/test-report.pdf",
                "source": "s3",
                "event_type": "ObjectCreated",
                "bucket": "my-bucket",
                "key": "documents/test-report.pdf",
                "size": 1024000,
                "content_type": "application/pdf",
                "timestamp": "2025-01-08T10:00:00Z"
            }
        },
        {
            "name": "Azure Blob Document Processing", 
            "input": {
                "document_uri": "https://storage.blob.core.windows.net/documents/presentation.docx",
                "source": "azure-blob",
                "event_type": "BlobCreated",
                "container": "documents",
                "blob_name": "presentation.docx",
                "size": 512000,
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "timestamp": "2025-01-08T10:05:00Z"
            }
        },
        {
            "name": "Chat Upload Document Processing",
            "input": {
                "document_uri": "/tmp/uploads/user-manual.pdf",
                "source": "chat",
                "event_type": "document-uploaded",
                "timestamp": "2025-01-08T10:10:00Z",
                "additional_context": {
                    "userId": "user123",
                    "chatId": "chat-session-456",
                    "filename": "user-manual.pdf"
                }
            }
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"   Input: {test_case['input']['source']} -> {test_case['input']['document_uri']}")
        
        try:
            # Create workflow ID
            workflow_id = f"test-doc-processing-{i}-{test_case['input']['source']}"
            
            # Start workflow
            handle = await client.start_workflow(
                "DocumentProcessingWorkflow",
                test_case["input"],
                id=workflow_id,
                task_queue="document_processing-queue"
            )
            
            print(f"   ✅ Workflow started: {workflow_id}")
            
            # Wait for result (with timeout)
            try:
                result = await asyncio.wait_for(handle.result(), timeout=60)
                
                if result.get("success"):
                    summary = result.get("processing_summary", {})
                    print(f"   ✅ SUCCESS: Processed {summary.get('chunks_created', 0)} chunks, "
                          f"{summary.get('embeddings_generated', 0)} embeddings")
                    print(f"   📊 Stats: {summary.get('content_size', 0)} bytes -> "
                          f"{summary.get('text_length', 0)} chars -> "
                          f"{summary.get('chunks_stored', 0)} stored")
                else:
                    print(f"   ❌ FAILED at step '{result.get('step')}': {result.get('error')}")
                
                results.append({
                    "test": test_case["name"],
                    "success": result.get("success", False),
                    "result": result
                })
                
            except asyncio.TimeoutError:
                print(f"   ⏰ TIMEOUT: Workflow took longer than 60 seconds")
                results.append({
                    "test": test_case["name"],
                    "success": False,
                    "result": {"error": "timeout"}
                })
                
        except Exception as e:
            print(f"   ❌ ERROR: Failed to start workflow: {e}")
            results.append({
                "test": test_case["name"],
                "success": False,
                "result": {"error": str(e)}
            })
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Total tests: {len(test_cases)}")
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"   ✅ Successful: {len(successful)}")
    print(f"   ❌ Failed: {len(failed)}")
    
    if failed:
        print(f"\n❌ Failed tests:")
        for fail in failed:
            print(f"   - {fail['test']}: {fail['result'].get('error', 'unknown error')}")
    
    print(f"\n🎯 Overall result: {'SUCCESS' if len(failed) == 0 else 'PARTIAL SUCCESS' if len(successful) > 0 else 'FAILURE'}")
    
    return len(failed) == 0


if __name__ == "__main__":
    success = asyncio.run(test_document_processing_workflow())
    sys.exit(0 if success else 1)
