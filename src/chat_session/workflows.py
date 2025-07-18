"""Chat Session Workflow - Long-running workflow for chat conversations."""

from datetime import timedelta
from typing import Dict, Any, List, Optional
from temporalio import workflow
from temporalio.exceptions import ApplicationError
from dataclasses import dataclass
from ..semantic_search.workflows import SemanticSearchWorkflow
from .activities import activities_instance


@dataclass
class ChatMessage:
    """Chat message data structure."""
    message_id: str
    content: str
    role: str  # 'user', 'assistant', 'system'
    timestamp: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatSessionState:
    """Chat session state data structure."""
    session_id: str
    user_id: Optional[str] = None
    user_type: str = 'guest'  # 'guest' or 'authenticated'
    message_count: int = 0
    is_active: bool = True
    last_activity: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowTriggerEvent:
    """Event for triggering other workflows from chat."""
    event_type: str
    source: str = 'chat'
    message: str = ""
    priority: str = 'normal'
    metadata: Optional[Dict[str, Any]] = None


@workflow.defn
class ChatSessionWorkflow:
    """Long-running workflow that manages a chat session.
    
    This workflow:
    - Receives chat messages as signals
    - Maintains conversation state and history
    - Handles rate limiting for guest users
    - Triggers other workflows based on chat content
    - Integrates with the AI chat system
    """
    
    def __init__(self):
        """Initialize the chat session workflow."""
        self._state: Optional[ChatSessionState] = None
        self._message_history: List[ChatMessage] = []
        self._triggered_workflows: List[str] = []
        self._ai_processing_queue: List[ChatMessage] = []
        
    @workflow.signal
    async def receive_message(self, message_data: Dict[str, Any]):
        """Receive a chat message signal.
        
        Args:
            message_data: Message data containing content, role, etc.
        """
        # Use provided messageId, or fallback to deterministic ID
        message_id = message_data.get('messageId')
        if not message_id:
            # Fallback: deterministic ID based on session and message count
            session_id = self._state.session_id if self._state else "unknown"
            message_id = f"{session_id}-msg-{len(self._message_history) + 1}"
        workflow.logger.info(f"Received message: {message_id}")
        
        # Create ChatMessage object
        message = ChatMessage(
            message_id=message_id,
            content=message_data.get('content', ''),
            role=message_data.get('role', 'user'),
            timestamp=message_data.get('timestamp', ''),
            user_id=message_data.get('userId'),
            metadata=message_data.get('metadata', {})
        )
        
        # Add to history
        self._message_history.append(message)
        
        # Update state
        if self._state:
            self._state.message_count += 1
            self._state.last_activity = message.timestamp
        
        # Queue for AI processing
        self._ai_processing_queue.append(message)
        
        workflow.logger.info(f"Message queued for processing. Total messages: {len(self._message_history)}")
    
    @workflow.signal
    async def trigger_workflow(self, workflow_event: Dict[str, Any]):
        """Trigger a domain workflow based on chat content analysis.
        
        Args:
            workflow_event: Event data containing workflow type and parameters
        """
        # Support both 'eventType' and 'event_type' for compatibility
        event_type = workflow_event.get('eventType') or workflow_event.get('event_type')
        if not event_type:
            workflow.logger.warning("No eventType/event_type in workflow_event, skipping trigger")
            return
        workflow.logger.info(f"Triggering workflow for event type: {event_type}")
        # Generate deterministic workflow ID for the triggered workflow
        # Use session_id and event_type and message count for uniqueness
        session_id = self._state.session_id if self._state else "unknown"
        message_count = self._state.message_count if self._state else 0
        workflow_id = f"chat-triggered-{event_type}-{session_id}-{message_count}"
        
        try:
            # Directly trigger domain workflows based on event type
            if event_type in ["document-added", "document-uploaded"]:
                # Start document processing workflow directly
                await workflow.execute_child_workflow(
                    "DocumentProcessingWorkflow",
                    args=[{
                        "document_uri": workflow_event.get("documentUri"),
                        "source": "chat",
                        "event_type": event_type,
                        "bucket": workflow_event.get("bucket"),
                        "key": workflow_event.get("key"),
                        "additional_context": {
                            "chatId": self._state.session_id if self._state else None,
                            "userId": self._state.user_id if self._state else None,
                            "metadata": workflow_event.get('metadata', {})
                        }
                    }],
                    id=workflow_id,
                    task_queue="document_processing-queue"
                )
                
            else:
                # Generic workflow handling - could be extended
                workflow.logger.warning(f"Unknown event type: {event_type}, creating generic workflow")
                await workflow.execute_child_workflow(
                    "GenericWorkflow",
                    args=[workflow_event],
                    id=workflow_id,
                    task_queue="generic-queue"
                )
            
            self._triggered_workflows.append(workflow_id)
            workflow.logger.info(f"Successfully triggered {event_type} workflow: {workflow_id}")
            
        except Exception as e:
            workflow.logger.error(f"Failed to trigger workflow: {e}")
            raise ApplicationError(f"Failed to trigger workflow: {e}")
    
    @workflow.signal
    async def update_user(self, user_data: Dict[str, Any]):
        """Update user information for the chat session.
        
        Args:
            user_data: User data containing userId and userType
        """
        if self._state:
            self._state.user_id = user_data.get('userId')
            self._state.user_type = user_data.get('userType', 'guest')
            workflow.logger.info(f"Updated user: {self._state.user_id} ({self._state.user_type})")
    
    @workflow.signal
    async def end_session(self, reason: str = "Session ended"):
        """End the chat session.
        
        Args:
            reason: Reason for ending the session
        """
        if self._state:
            self._state.is_active = False
            workflow.logger.info(f"Chat session ended: {reason}")
    
    @workflow.query
    def get_session_state(self) -> Optional[Dict[str, Any]]:
        """Get current session state.
        
        Returns:
            Current session state as dictionary
        """
        if not self._state:
            return None
            
        return {
            "sessionId": self._state.session_id,
            "userId": self._state.user_id,
            "userType": self._state.user_type,
            "messageCount": self._state.message_count,
            "isActive": self._state.is_active,
            "lastActivity": self._state.last_activity,
            "metadata": self._state.metadata
        }
    
    @workflow.query
    def get_message_history(self, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get chat message history.
        
        Args:
            params: Query parameters (e.g., limit)
            
        Returns:
            List of chat messages as dictionaries
        """
        limit = params.get('limit', 50) if params else 50
        recent_messages = self._message_history[-limit:] if limit > 0 else self._message_history
        
        return [
            {
                "messageId": msg.message_id,
                "content": msg.content,
                "role": msg.role,
                "timestamp": msg.timestamp,
                "userId": msg.user_id,
                "metadata": msg.metadata
            }
            for msg in recent_messages
        ]
    
    @workflow.query
    def get_triggered_workflows(self) -> List[str]:
        """Get list of workflows triggered by this chat session.
        
        Returns:
            List of workflow IDs
        """
        return self._triggered_workflows.copy()
    
    @workflow.query
    def check_rate_limit(self) -> Dict[str, Any]:
        """Check if user has hit rate limits.
        
        Returns:
            Rate limit status
        """
        if not self._state:
            return {"limited": False, "reason": "No session state"}
        
        # Guest users limited to 3 messages
        if self._state.user_type == 'guest' and self._state.message_count >= 3:
            return {
                "limited": True,
                "reason": "Guest user message limit reached",
                "messageCount": self._state.message_count,
                "limit": 3
            }
        
        return {
            "limited": False,
            "messageCount": self._state.message_count,
            "limit": 3 if self._state.user_type == 'guest' else -1
        }
    
    @workflow.run
    async def run(self, initial_state: Dict[str, Any]) -> str:
        """Run the chat session workflow.
        
        Args:
            initial_state: Initial session state
            
        Returns:
            Final session status
        """
        workflow.logger.info(f"Starting chat session: {initial_state.get('sessionId')}")
        
        # Initialize state
        self._state = ChatSessionState(
            session_id=initial_state.get('sessionId'),
            user_id=initial_state.get('userId'),
            user_type=initial_state.get('userType', 'guest'),
            message_count=initial_state.get('messageCount', 0),
            is_active=initial_state.get('isActive', True),
            last_activity=initial_state.get('lastActivity', ''),
            metadata=initial_state.get('metadata', {})
        )
        
        workflow.logger.info(f"Chat session initialized for user: {self._state.user_id} ({self._state.user_type})")
        
        try:
            # Main chat session loop
            while self._state.is_active:
                # Process ALL queued AI messages
                while self._ai_processing_queue and self._state.is_active:
                    message = self._ai_processing_queue.pop(0)
                    await self._process_ai_message(message)
                
                # Only wait if no messages are queued and session is still active
                if self._state.is_active and not self._ai_processing_queue:
                    # Wait for new messages or session to end (24 hours timeout)
                    await workflow.wait_condition(
                        lambda: not self._state.is_active or self._ai_processing_queue,
                        timeout=timedelta(hours=24)
                    )
            
            workflow.logger.info("Chat session ended normally")
            return f"Chat session {self._state.session_id} completed. Messages: {self._state.message_count}, Triggered workflows: {len(self._triggered_workflows)}"
            
        except Exception as e:
            workflow.logger.error(f"Chat session failed: {e}")
            return f"Chat session {self._state.session_id} failed: {e}"
    
    async def _process_ai_message(self, message: ChatMessage) -> Dict[str, Any]:
        """Process a message for AI response and workflow triggers.
        
        Args:
            message: The chat message to process
        
        Returns:
            Processing result with metadata
        """
        workflow.logger.info(f"Processing AI message: {message.message_id}")
        result = {"processed": False}
        
        try:
            # First analyze message for potential workflows
            user_context = {
                'userId': message.user_id,
                'sessionId': self._state.session_id if self._state else "unknown",
                'userType': self._state.user_type if self._state else 'guest'
            }
            
            analysis_result = await workflow.execute_activity(
                activities_instance.analyze_message_for_workflows,
                args=[message.content, user_context],
                start_to_close_timeout=timedelta(seconds=10)
            )
                
            if analysis_result.get('shouldTriggerWorkflow', False):
                    detected_workflows = analysis_result.get('detectedWorkflows', [])
                    primary_workflow = analysis_result.get('primaryWorkflow')
                    
                    if primary_workflow:
                        workflow_type = primary_workflow.get('type')
                        workflow.logger.info(f"Detected workflow type '{workflow_type}' in message")
                        
                        # Map workflow types to event types
                        if workflow_type == 'search':
                            search_result = await workflow.execute_child_workflow(
                                "SemanticSearchWorkflow",
                                args=[{
                                    "query": message.content,
                                    "session_id": self._state.session_id if self._state else "unknown",
                                    "user_id": message.user_id,
                                    "metadata": {
                                        "messageId": message.message_id
                                    }
                                }],
                                id=f"semantic-search-{message.message_id}",
                                task_queue="semantic-search-queue"
                            )
                            
                            if search_result.get("success"):
                                workflow.logger.info(f"Semantic search completed for message: {message.message_id}")
                                result["search_triggered"] = True
                                result["search_result"] = search_result
                                # Continue processing instead of returning early
                            else:
                                workflow.logger.error(f"Semantic search failed for message: {message.message_id}")
                        elif workflow_type == 'document':
                            await self.trigger_workflow({
                                'eventType': 'document-added',
                                'message': message.content,
                                'priority': 'normal',
                                'metadata': {
                                    'messageId': message.message_id,
                                    'detectedWorkflows': detected_workflows,
                                    'confidence': analysis_result.get('confidence', 0.0)
                                }
                            })
                        elif workflow_type in ['data', 'automation']:
                            await self.trigger_workflow({
                                'eventType': 'user-request',
                                'message': message.content,
                                'priority': 'normal',
                                'metadata': {
                                    'messageId': message.message_id,
                                    'workflowType': workflow_type,
                                    'detectedWorkflows': detected_workflows,
                                    'confidence': analysis_result.get('confidence', 0.0)
                                }
                            })
            
            # Search handling is done above in the workflow detection section
            
            # Process workflow acknowledgment (no AI response needed since chat API handles that)
            workflow_response = await workflow.execute_activity(
                activities_instance.generate_ai_response,
                args=[message.content, [], user_context],  # Empty history to avoid circular processing
                start_to_close_timeout=timedelta(seconds=10)  # Shorter timeout since it's just acknowledgment
            )
            
            result.update({"processed": True, "workflow_response": workflow_response})
            
        except Exception as e:
            workflow.logger.error(f"Error processing AI message: {e}")
            result["error"] = str(e)
            
        return result
