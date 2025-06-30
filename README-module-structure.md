# Temporal Workflow Module Structure

This project organizes each workflow module with the following files:

1. **`__init__.py`**
   - Marks the directory as a Python package.
   - Optionally, can be used to expose or import key symbols for easier imports elsewhere.
   - Usually contains little or no logic.

2. **`activities.py`**
   - Defines the activity functions for the workflow.
   - Each function is decorated (e.g., with `@activity.defn`) so it can be registered and run by the Temporal worker.
   - Activities contain the business logic for steps that run outside the workflow (e.g., database updates, API calls).

3. **`workflows.py`**
   - Defines the workflow class and its logic.
   - The class is decorated (e.g., with `@workflow.defn`) so Temporal can discover and execute it.
   - The workflow orchestrates the order and conditions for calling activities, handling signals, and managing state.

4. **`run_worker.py`**
   - The entrypoint script for running a Temporal worker process.
   - Connects to the Temporal server, registers the workflow(s) and activity(ies), and starts the worker loop.
   - This is the file you run (or set as the Docker entrypoint) to start processing workflow and activity tasks for this module.

**Summary:**
This structure keeps each concern separate and makes it easy to add, test, and maintain workflows and activities.
