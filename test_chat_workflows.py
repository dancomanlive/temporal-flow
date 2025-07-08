#!/usr/bin/env python3
"""Test script for Chat Session Workflow functionality."""

import asyncio
import json
from datetime import datetime
from src.utils import connect_to_temporal_with_retry


async def test_chat_session_workflow():
    """Test the ChatSessionWorkflow functionality."""
    print("🧪 Testing Chat Session Workflow...")
    
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
        
        # Wait a moment for workflow to initialize
        await asyncio.sleep(2)
        
        # Test sending a message
        print("💬 Sending test message...")
        await handle.signal("receive_message", {
            "messageId": "msg-001",
            "content": "Hello! Can you help me process a document?",
            "role": "user",
            "timestamp": datetime.now().isoformat(),
            "userId": "test-user-123"
        })
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Query session state
        print("📊 Querying session state...")
        state = await handle.query("get_session_state")
        print(f"   Session state: {json.dumps(state, indent=2)}")
        
        # Query message history
        print("📚 Querying message history...")
        history = await handle.query("get_message_history", {"limit": 10})
        print(f"   Message count: {len(history)}")
        for msg in history:
            print(f"   - [{msg['role']}] {msg['content'][:50]}...")
        
        # Test workflow triggering
        print("🚀 Testing workflow trigger...")
        await handle.signal("trigger_workflow", {
            "eventType": "document-added",
            "message": "Critical system failure detected",
            "priority": "high",
            "metadata": {
                "source": "chat-test",
                "sessionId": session_id
            }
        })
        
        # Wait for trigger processing
        await asyncio.sleep(3)
        
        # Query triggered workflows
        print("📋 Querying triggered workflows...")
        triggered = await handle.query("get_triggered_workflows")
        print(f"   Triggered workflows: {len(triggered)}")
        for wf_id in triggered:
            print(f"   - {wf_id}")
        
        # Test rate limiting check
        print("🚦 Testing rate limit check...")
        rate_limit = await handle.query("check_rate_limit")
        print(f"   Rate limit status: {json.dumps(rate_limit, indent=2)}")
        
        # Send another message to test count increment
        print("💬 Sending second message...")
        await handle.signal("receive_message", {
            "messageId": "msg-002", 
            "content": "Thank you for the help!",
            "role": "user",
            "timestamp": datetime.now().isoformat(),
            "userId": "test-user-123"
        })
        
        await asyncio.sleep(2)
        
        # Check updated state
        print("📊 Checking updated state...")
        updated_state = await handle.query("get_session_state")
        print(f"   Updated message count: {updated_state['messageCount']}")
        
        # Test ending session
        print("🔚 Ending chat session...")
        await handle.signal("end_session", "Test completed")
        
        # Wait for completion
        await asyncio.sleep(2)
        
        # Final state check
        final_state = await handle.query("get_session_state")
        print(f"   Final state - Active: {final_state['isActive']}")
        
        print("✅ Chat session workflow test completed successfully!")
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
        await test_guest_rate_limiting()
        
        print("\n🎉 All tests passed! Chat Session Workflows are working correctly.")
        print("\n📋 Next steps:")
        print("   1. Visit http://localhost:8080 to view workflows in Temporal UI")
        print("   2. Test the chat integration at http://localhost:3001")
        print("   3. Monitor workflow logs in Docker Compose")
        
    except Exception as e:
        print(f"\n💥 Tests failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Ensure Temporal server is running: docker compose up temporal")
        print("   2. Ensure chat session worker is running: docker compose up chat-session-worker")
        print("   3. Check worker logs: docker compose logs chat-session-worker")


if __name__ == "__main__":
    asyncio.run(main())
