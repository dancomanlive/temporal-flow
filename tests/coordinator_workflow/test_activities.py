import pytest
from unittest.mock import patch, MagicMock, mock_open
from temporalio.exceptions import ApplicationError
import json

# Import the class containing the activities
from src.coordinator_workflow.activities import (
    CoordinatorActivities, 
    ChooseWorkflowParams, 
    LoadDefinitionParams
)

# Mark all tests in this file as asyncio
pytestmark = pytest.mark.asyncio


class TestCoordinatorActivities:
    """Tests for CoordinatorActivities."""

    async def test_choose_workflow_happy_path(self):
        """
        GIVEN a valid event_type and available workflows
        WHEN choose_workflow is called
        THEN it should return the correct workflow name.
        This test is pure logic and needs no mocking.
        """
        activities = CoordinatorActivities()
        params = ChooseWorkflowParams(
            event_type="incident",
            available_workflows=["incident_workflow", "other_workflow"],
        )
        
        # Directly call the method, no need for Temporal worker
        result = await activities.choose_workflow(params)

        assert result.workflow_name == "incident_workflow"

    async def test_choose_workflow_case_insensitive(self):
        """
        GIVEN an event_type with different casing
        WHEN choose_workflow is called
        THEN it should handle case-insensitive matching.
        """
        activities = CoordinatorActivities()
        params = ChooseWorkflowParams(
            event_type="INCIDENT",
            available_workflows=["incident_workflow", "other_workflow"],
        )
        
        result = await activities.choose_workflow(params)

        assert result.workflow_name == "incident_workflow"

    async def test_choose_workflow_not_available(self):
        """
        GIVEN an event_type for a workflow that is not in the available list
        WHEN choose_workflow is called
        THEN it should raise a non-retryable ApplicationError.
        """
        activities = CoordinatorActivities()
        params = ChooseWorkflowParams(
            event_type="incident",
            available_workflows=["other_workflow_1", "other_workflow_2"],
        )

        with pytest.raises(ApplicationError) as excinfo:
            await activities.choose_workflow(params)
        
        assert "No available workflow for this event type" in str(excinfo.value)
        assert excinfo.value.non_retryable is True

    async def test_choose_workflow_unknown_event_type(self):
        """
        GIVEN an unknown event_type
        WHEN choose_workflow is called
        THEN it should raise a non-retryable ApplicationError.
        """
        activities = CoordinatorActivities()
        params = ChooseWorkflowParams(
            event_type="unknown_event",
            available_workflows=["incident_workflow", "other_workflow"],
        )

        with pytest.raises(ApplicationError) as excinfo:
            await activities.choose_workflow(params)
        
        assert "No available workflow for this event type" in str(excinfo.value)
        assert excinfo.value.non_retryable is True

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    async def test_get_available_workflows_with_mocked_fs(
        self, mock_listdir: MagicMock, mock_isdir: MagicMock, mock_exists: MagicMock
    ):
        """
        GIVEN a mocked filesystem structure
        WHEN get_available_workflows is called
        THEN it should correctly identify valid workflow modules.
        This test is completely isolated from the actual filesystem.
        """
        activities = CoordinatorActivities()
        
        # --- Mock Setup ---
        # 1. Simulate the contents of the 'src' directory
        mock_listdir.return_value = [
            "incident_workflow",      # A valid workflow
            "coordinator_workflow",   # Should be ignored
            "data_processing_workflow", # A valid workflow
            "empty_dir",              # A directory without a .json file
            "not_a_dir.txt"           # A file that is not a directory
        ]

        # 2. Simulate which paths are directories
        def isdir_side_effect(path):
            # Check if the last part of the path is one of our simulated dirs
            dir_name = path.split('/')[-1]
            return dir_name in ["incident_workflow", "coordinator_workflow", "data_processing_workflow", "empty_dir"]
        mock_isdir.side_effect = isdir_side_effect

        # 3. Simulate which workflow directories contain the required .json file
        def exists_side_effect(path):
            return "incident_workflow.json" in path or "data_processing_workflow.json" in path
        mock_exists.side_effect = exists_side_effect
        
        # --- Execution ---
        result = await activities.get_available_workflows()

        # --- Assertions ---
        # The result should be sorted for predictable testing
        assert sorted(result) == ["data_processing_workflow", "incident_workflow"]
        # Verify it ignored the coordinator and the invalid directories
        assert "coordinator_workflow" not in result
        assert "empty_dir" not in result

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    async def test_get_available_workflows_empty_directory(
        self, mock_listdir: MagicMock, mock_isdir: MagicMock, mock_exists: MagicMock
    ):
        """
        GIVEN an empty src directory
        WHEN get_available_workflows is called
        THEN it should return an empty list.
        """
        activities = CoordinatorActivities()
        
        mock_listdir.return_value = []
        
        result = await activities.get_available_workflows()
        
        assert result == []

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    async def test_get_available_workflows_only_coordinator(
        self, mock_listdir: MagicMock, mock_isdir: MagicMock, mock_exists: MagicMock
    ):
        """
        GIVEN a directory with only the coordinator_workflow
        WHEN get_available_workflows is called
        THEN it should return an empty list (coordinator is excluded).
        """
        activities = CoordinatorActivities()
        
        mock_listdir.return_value = ["coordinator_workflow"]
        mock_isdir.return_value = True
        mock_exists.return_value = True
        
        result = await activities.get_available_workflows()
        
        assert result == []

    @patch("os.path.exists")
    @patch("os.path.isdir") 
    @patch("os.listdir")
    async def test_get_available_workflows_no_json_files(
        self, mock_listdir: MagicMock, mock_isdir: MagicMock, mock_exists: MagicMock
    ):
        """
        GIVEN directories without corresponding .json definition files
        WHEN get_available_workflows is called
        THEN it should return an empty list.
        """
        activities = CoordinatorActivities()
        
        mock_listdir.return_value = ["workflow_without_json", "another_workflow"]
        mock_isdir.return_value = True
        mock_exists.return_value = False  # No .json files exist
        
        result = await activities.get_available_workflows()
        
        assert result == []

    @patch("builtins.open", new_callable=mock_open, read_data='{"name": "test_workflow", "version": "1.0"}')
    @patch("os.path.exists")
    async def test_load_workflow_definition_success(self, mock_exists: MagicMock, mock_file: MagicMock):
        """
        GIVEN a valid workflow definition file
        WHEN load_workflow_definition is called
        THEN it should return the parsed JSON content.
        """
        activities = CoordinatorActivities()
        mock_exists.return_value = True
        
        params = LoadDefinitionParams(
            workflow_name="test_workflow",
            workflows_base_dir="/app/src"
        )
        
        result = await activities.load_workflow_definition(params)
        
        assert result.workflow_def == {"name": "test_workflow", "version": "1.0"}
        mock_exists.assert_called_once_with("/app/src/test_workflow/test_workflow.json")
        mock_file.assert_called_once_with("/app/src/test_workflow/test_workflow.json", 'r')

    @patch("os.path.exists")
    async def test_load_workflow_definition_file_not_found(self, mock_exists: MagicMock):
        """
        GIVEN a workflow definition file that doesn't exist
        WHEN load_workflow_definition is called
        THEN it should raise a non-retryable ApplicationError.
        """
        activities = CoordinatorActivities()
        mock_exists.return_value = False
        
        params = LoadDefinitionParams(
            workflow_name="nonexistent_workflow",
            workflows_base_dir="/app/src"
        )
        
        with pytest.raises(ApplicationError) as excinfo:
            await activities.load_workflow_definition(params)
        
        assert "Workflow definition file not found" in str(excinfo.value)
        assert excinfo.value.non_retryable is True

    @patch("builtins.open", new_callable=mock_open, read_data='{"invalid": json}')
    @patch("os.path.exists")
    async def test_load_workflow_definition_invalid_json(self, mock_exists: MagicMock, mock_file: MagicMock):
        """
        GIVEN a workflow definition file with invalid JSON
        WHEN load_workflow_definition is called
        THEN it should raise a non-retryable ApplicationError.
        """
        activities = CoordinatorActivities()
        mock_exists.return_value = True
        
        params = LoadDefinitionParams(
            workflow_name="invalid_workflow",
            workflows_base_dir="/app/src"
        )
        
        with pytest.raises(ApplicationError) as excinfo:
            await activities.load_workflow_definition(params)
        
        assert "Failed to load workflow definition" in str(excinfo.value)
        assert excinfo.value.non_retryable is True

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    @patch("os.path.exists")
    async def test_load_workflow_definition_io_error(self, mock_exists: MagicMock, mock_file: MagicMock):
        """
        GIVEN a workflow definition file that can't be read due to IO error
        WHEN load_workflow_definition is called
        THEN it should raise a non-retryable ApplicationError.
        """
        activities = CoordinatorActivities()
        mock_exists.return_value = True
        
        params = LoadDefinitionParams(
            workflow_name="inaccessible_workflow", 
            workflows_base_dir="/app/src"
        )
        
        with pytest.raises(ApplicationError) as excinfo:
            await activities.load_workflow_definition(params)
        
        assert "Failed to load workflow definition" in str(excinfo.value)
        assert "Permission denied" in str(excinfo.value)
        assert excinfo.value.non_retryable is True
