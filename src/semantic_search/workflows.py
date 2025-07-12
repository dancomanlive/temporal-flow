"""Workflow orchestration for semantic search."""

from typing import Dict, Any
from temporalio import workflow
from datetime import timedelta
from ..domain.workflow_inputs import SemanticSearchInput
from .activities import SemanticSearchActivities

@workflow.defn
class SemanticSearchWorkflow:
    """Main workflow for semantic search functionality."""
    
    def __init__(self):
        self.activities = SemanticSearchActivities()
    
    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main workflow execution."""
        try:
            # Convert to domain input
            workflow_input = SemanticSearchInput(**input_data)
            
            # Step 1: Embed query
            embedding_result = await workflow.execute_activity(
                self.activities.embed_query,
                {"query": workflow_input.query},
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            # Step 2: Retrieve relevant chunks
            retrieval_result = await workflow.execute_activity(
                self.activities.retrieve_chunks,
                {"embedding": embedding_result["embedding"]},
                start_to_close_timeout=timedelta(seconds=60)
            )
            
            # Step 3: Generate response
            response_result = await workflow.execute_activity(
                self.activities.generate_response,
                {"query": workflow_input.query, "chunks": retrieval_result["chunks"]},
                start_to_close_timeout=timedelta(minutes=2)
            )
            
            return {
                "success": True,
                "response": response_result["response"],
                "chunks": retrieval_result["chunks"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": "workflow_execution"
            }