"""Chat Session Worker - Runs the chat session workflow and activities."""

import asyncio
from temporalio.worker import Worker
from src.chat_session.workflows import ChatSessionWorkflow
from src.chat_session.activities import activities_instance
from src.utils import connect_to_temporal_with_retry


async def main():
    """Main function to start the chat session worker."""
    client = await connect_to_temporal_with_retry("temporal:7233")
    worker = Worker(
        client,
        task_queue="chat-session-queue",
        workflows=[ChatSessionWorkflow],
        activities=[
            activities_instance.generate_ai_response,
            activities_instance.analyze_message_for_workflows,
            activities_instance.validate_user_permissions,
            activities_instance.log_chat_event,
            activities_instance.save_conversation_state,
        ],
    )
    print("Starting Chat Session worker on task queue: chat-session-queue")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
