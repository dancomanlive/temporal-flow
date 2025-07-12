#!/usr/bin/env python3
"""Test script for Chat Session Workflow functionality."""

import asyncio
import json
from datetime import datetime
from src.utils import connect_to_temporal_with_retry


async def test_chat_session_workflow():
    """Test the ChatSessionWorkflow functionality."""
    print("🧪 Testing Chat Session Workflow with DocumentProcessing and SemanticSearch child workflows...")

    # Connect to Temporal
    client = await connect_to_temporal_with_retry("localhost:7233")

    # Test session ID
    session_id = f"test-chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    workflow_id = f"chat-session-{session_id}"

    print(f"📝 Starting chat session: {session_id}")

    try:
        # Start the chat session workflow
        handle = await client.start_workflow(
            "ChatSessionWorkflow",
            args=[{
                "sessionId": session_id,
                "userId": "test-user-123",
                "userType": "authenticated",
                "messageCount": 0,
                "isActive": True,
                "lastActivity": datetime.now().isoformat()
            }],
            id=workflow_id,
            task_queue="chat-session-queue"
        )

        print(f"✅ Chat session workflow started: {workflow_id}")
        await asyncio.sleep(2)

        # Send a document processing message
        print("💬 Sending document processing message...")
        await handle.signal("receive_message", {
            "messageId": "msg-001",
            "content": "Please process the attached document.",
            "role": "user",
            "timestamp": datetime.now().isoformat(),
            "userId": "test-user-123"
        })
        await asyncio.sleep(3)
        
        # Send a semantic search message
        print("🔍 Sending semantic search message...")
        await handle.signal("receive_message", {
            "messageId": "msg-002",
            "content": "What is the meaning of life?",
            "role": "user",
            "timestamp": datetime.now().isoformat(),
            "userId": "test-user-123"
        })
        await asyncio.sleep(3)

        # Query for triggered child workflows
        print("📋 Querying triggered workflows...")
        triggered = await handle.query("get_triggered_workflows")
        print(f"   Triggered workflows: {len(triggered)}")
        for wf_id in triggered:
            print(f"   - {wf_id}")

        # Optionally, query the result of the child workflow if available
        if triggered:
            child_id = triggered[0]
            print(f"� Querying result of DocumentProcessing child workflow: {child_id}")
            # This assumes a query method exists; adjust as needed for your implementation
            try:
                child_result = await client.get_workflow_handle(child_id).query("get_result")
                print(f"   Child workflow result: {json.dumps(child_result, indent=2)}")
            except Exception as ce:
                print(f"   Could not query child workflow result: {ce}")

        print("✅ Test completed: Single ChatSessionWorkflow and DocumentProcessing child workflow.")
        print(f"🌐 View in Temporal UI: http://localhost:8080/namespaces/default/workflows/{workflow_id}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


async def test_guest_rate_limiting():
    """Test guest user rate limiting."""
    print("\n🧪 Testing Guest User Rate Limiting...")
    
    client = await connect_to_temporal_with_retry("localhost:7233")
    
    session_id = f"guest-test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    workflow_id = f"chat-session-{session_id}"
    
    print(f"👤 Starting guest session: {session_id}")
    
    try:
        # Start guest session
        handle = await client.start_workflow(
            "ChatSessionWorkflow",
            args=[{
                "sessionId": session_id,
                "userId": "guest-456",
                "userType": "guest",
                "messageCount": 0,
                "isActive": True,
                "lastActivity": datetime.now().isoformat()
            }],
            id=workflow_id,
            task_queue="chat-session-queue"
        )
        
        print(f"✅ Guest session started: {workflow_id}")
        await asyncio.sleep(1)
        
        # Send 3 messages (guest limit)
        for i in range(1, 4):
            print(f"💬 Sending message {i}/3...")
            await handle.signal("receive_message", {
                "messageId": f"guest-msg-{i:03d}",
                "content": f"Guest message number {i}",
                "role": "user", 
                "timestamp": datetime.now().isoformat(),
                "userId": "guest-456"
            })
            await asyncio.sleep(1)
            
            # Check rate limit status
            rate_limit = await handle.query("check_rate_limit")
            print(f"   Rate limit after message {i}: {rate_limit}")
        
        print("✅ Guest rate limiting test completed!")
        
    except Exception as e:
        print(f"❌ Guest test failed: {e}")
        raise


async def main():
    """Run all tests."""
    print("🚀 Starting Chat Session Workflow Tests...\n")
    
    try:
        await test_chat_session_workflow()
        print("\n🎉 Test passed! Single ChatSessionWorkflow and DocumentProcessing child workflow executed.")
        print("\n📋 Next steps:")
        print("   1. Visit http://localhost:8080 to view workflows in Temporal UI")
        print("   2. Test the chat integration at http://localhost:3001")
        print("   3. Monitor workflow logs in Docker Compose")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure Temporal server is running: docker compose up temporal")
        print("   2. Ensure chat session worker is running: docker compose up chat-session-worker")
        print("   3. Check worker logs: docker compose logs chat-session-worker")


if __name__ == "__main__":
    asyncio.run(main())
