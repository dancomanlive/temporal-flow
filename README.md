# Temporal Orchestrator Quickstart

## How to Run the Demo

1. **Build the Docker images:**
   ```sh
   docker compose build --no-cache
   ```

2. **Start all services:**
   ```sh
   docker-compose up -d
   ```

3. **Start the coordinator workflow:**
   ```sh
   temporal workflow start --task-queue coordinator_workflow-queue --type CoordinatorWorkflow --workflow-id test-coordinator-1 --input '{}'
   ```

   3a. **Open the Temporal Web UI:**
   - Go to [http://localhost:8080/namespaces/default/workflows](http://localhost:8080/namespaces/default/workflows)
   - Refresh the page if the workflow is not immediately visible.

4. **Send a trigger signal to the workflow:**
   ```sh
   temporal workflow signal --workflow-id test-coordinator-1 --name trigger --input '{"event_type": "incident"}'
   ```

   4a. **See the child workflow running** in the Temporal Web UI.

5. **Click on the workflow** in the UI to see the activities that were performed.

---

This will demonstrate the full orchestration flow: coordinator workflow, event-driven signal, child workflow, and activities.
