"""Chat Session Activities - Activities for chat session workflow operations."""

from typing import Dict, Any, List, Optional
from temporalio import activity
from dataclasses import dataclass
import asyncio
import aiohttp
import os


@dataclass
class AIResponse:
    """AI response data structure."""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    tools_used: Optional[List[str]] = None
    workflow_triggered: bool = False


class ChatSessionActivities:
    """Activities for chat session workflow operations."""
    
    @activity.defn
    async def generate_ai_response(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]],
        user_context: Dict[str, Any]
    ) -> AIResponse:
        """Generate AI response for a chat message.
        
        Note: This activity is called from within the ChatSessionWorkflow.
        Since the chat API already handles AI response generation via the UI,
        this activity should focus on workflow-specific processing rather than
        generating duplicate responses.
        
        Args:
            message: User message content
            conversation_history: Previous messages in conversation
            user_context: User information and context
            
        Returns:
            AI response with content and metadata
        """
        activity.logger.info(f"Processing workflow message for analysis: {len(message)} chars")
        
        try:
            # For workflow integration, we don't need to generate AI responses
            # since the chat API already handles that. Instead, we focus on
            # workflow-specific processing and return a simple acknowledgment.
            
            # Log the message processing for debugging
            activity.logger.info(f"Workflow processed message from user {user_context.get('userId', 'unknown')}")
            
            return AIResponse(
                content="Message processed by workflow",
                metadata={
                    "processed_by": "ChatSessionWorkflow",
                    "message_length": len(message),
                    "user_context": user_context,
                    "workflow_processing": True
                },
                tools_used=["workflow_analysis"],
                workflow_triggered=True
            )
                        
        except Exception as e:
            activity.logger.error(f"Error processing workflow message: {e}")
            return AIResponse(
                content="Workflow message processing completed with errors",
                metadata={"error": str(e), "workflow_processing": True}
            )
    
    @activity.defn
    async def analyze_message_for_workflows(
        self, 
        message: str, 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze message to determine if it should trigger workflows.
        
        Args:
            message: User message content
            user_context: User information and context
            
        Returns:
            Analysis result with workflow triggers
        """
        activity.logger.info(f"Analyzing message for workflow triggers: {len(message)} chars")
        
        # Simple keyword-based analysis (could be enhanced with ML/AI)
        workflow_keywords = {
            'document': ['document', 'file', 'upload', 'process', 'analyze', 'pdf', 'doc'],
            'data': ['data', 'pipeline', 'etl', 'process', 'batch', 'job', 'analytics'],
            'automation': ['automate', 'workflow', 'trigger', 'run', 'execute', 'schedule'],
            'search': ['search', 'find', 'lookup', 'query', 'retrieve']
        }
        
        message_lower = message.lower()
        detected_workflows = []
        
        # Check for question marks which typically indicate search intent
        if '?' in message:
            detected_workflows.append({
                'type': 'search',
                'keyword': '?',
                'confidence': 0.9
            })
        
        for workflow_type, keywords in workflow_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    detected_workflows.append({
                        'type': workflow_type,
                        'keyword': keyword,
                        'confidence': 0.8  # Simple confidence score
                    })
                    break
        
        # Additional analysis could include:
        # - Sentiment analysis
        # - Entity extraction
        # - Intent classification
        # - Context understanding
        
        return {
            'shouldTriggerWorkflow': len(detected_workflows) > 0,
            'detectedWorkflows': detected_workflows,
            'primaryWorkflow': detected_workflows[0] if detected_workflows else None,
            'confidence': max([w['confidence'] for w in detected_workflows]) if detected_workflows else 0.0
        }
    
    @activity.defn
    async def validate_user_permissions(
        self, 
        user_id: Optional[str], 
        user_type: str, 
        requested_action: str
    ) -> Dict[str, Any]:
        """Validate user permissions for requested actions.
        
        Args:
            user_id: User identifier
            user_type: Type of user (guest/authenticated)
            requested_action: Action being requested
            
        Returns:
            Permission validation result
        """
        activity.logger.info(f"Validating permissions for {user_type} user: {requested_action}")
        
        # Define permission rules
        permissions = {
            'guest': {
                'chat': True,
                'trigger_workflow': False,
                'view_history': True,
                'message_limit': 3
            },
            'authenticated': {
                'chat': True,
                'trigger_workflow': True,
                'view_history': True,
                'message_limit': -1  # unlimited
            }
        }
        
        user_permissions = permissions.get(user_type, permissions['guest'])
        
        # Check specific action permissions
        action_allowed = user_permissions.get(requested_action, False)
        
        return {
            'allowed': action_allowed,
            'userType': user_type,
            'action': requested_action,
            'permissions': user_permissions,
            'reason': f"Action '{requested_action}' {'allowed' if action_allowed else 'not allowed'} for {user_type} users"
        }
    
    @activity.defn
    async def log_chat_event(
        self, 
        session_id: str, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> bool:
        """Log chat session events for analytics and debugging.
        
        Args:
            session_id: Chat session identifier
            event_type: Type of event (message, workflow_trigger, etc.)
            event_data: Event details
            
        Returns:
            True if logged successfully
        """
        activity.logger.info(f"Logging chat event: {event_type} for session {session_id}")
        
        try:
            # In a real implementation, this would write to a database or logging service
            # For now, we'll just log to the activity logger
            log_entry = {
                'sessionId': session_id,
                'eventType': event_type,
                'eventData': event_data,
                'timestamp': activity.info().heartbeat_timeout.total_seconds()  # Simplified timestamp
            }
            
            activity.logger.info(f"Chat event logged: {log_entry}")
            return True
            
        except Exception as e:
            activity.logger.error(f"Failed to log chat event: {e}")
            return False
    
    @activity.defn
    async def save_conversation_state(
        self, 
        session_id: str, 
        state: Dict[str, Any]
    ) -> bool:
        """Save conversation state for persistence.
        
        Args:
            session_id: Chat session identifier
            state: Current conversation state
            
        Returns:
            True if saved successfully
        """
        activity.logger.info(f"Saving conversation state for session: {session_id}")
        
        try:
            # In a real implementation, this would save to a database
            # For now, we'll just log the state
            activity.logger.info(f"Conversation state: {state}")
            return True
            
        except Exception as e:
            activity.logger.error(f"Failed to save conversation state: {e}")
            return False


# Global instance for easy import
activities_instance = ChatSessionActivities()
