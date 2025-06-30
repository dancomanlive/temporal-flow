# Coordinator Workflow Usage

## How to Start and Trigger the Coordinator Workflow

1. **Start the Coordinator Workflow**

This starts the workflow and waits for an event signal:

```
temporal workflow start --task-queue coordinator_workflow-queue --type CoordinatorWorkflow --workflow-id test-coordinator-1 --input '{}'
```

2. **Send an Event Signal**

Send a signal (e.g., with an event payload) to drive workflow selection and execution:

```
temporal workflow signal --workflow-id test-coordinator-1 --name trigger --input '{"event_type": "incident"}'
```

- The workflow will wait for the `trigger` signal.
- The event payload (such as `event_type`) determines which child workflow is started.
- For example, if `event_type` is `incident`, the incident workflow will be run as a child.

**Summary:**
- Start the workflow with empty input.
- Signal it with an event payload to trigger orchestration.
