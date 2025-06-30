# Temporal Worker Autoscaling Explained

## How Automatic Worker Upscaling Works

1. **Deploy Workers as Containers**
   - Workers are typically deployed as containers (e.g., in Kubernetes).

2. **Configure Autoscaling**
   - Use tools like:
     - **Kubernetes HPA (Horizontal Pod Autoscaler):** Scales based on CPU, memory, or custom metrics.
     - **KEDA:** Scales based on external event sources, such as Temporal task queue depth.

3. **Set Scaling Thresholds**
   - Example rules:
     - "If task queue depth > 100, add more replicas."
     - "If CPU usage > 70% for 5 minutes, scale up."

4. **Autoscaler Monitors Metrics**
   - The autoscaler watches metrics (from Prometheus, KEDA, etc.).
   - When a threshold is reached, it instructs Kubernetes to start more worker pods.

5. **New Workers Join the Pool**
   - New worker pods start and connect to the Temporal server.
   - Each worker polls a specific task queue for available tasks.
   - Tasks are distributed dynamically: any worker in the pool can pick up any available task from the queue.

6. **Task Specialization (Optional)**
   - If you want certain workers to handle only specific tasks, set up separate task queues and run dedicated worker pools for each queue.

## How to Add Worker Replicas

### In Kubernetes
- Edit your worker Deployment and set `spec.replicas` to the desired number:
  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: incident-worker
  spec:
    replicas: 3  # Number of worker pods
    ...
  ```
- Or, let the autoscaler (HPA/KEDA) adjust this automatically based on metrics.

### In Docker Compose (for local/dev)
- In your `docker-compose.yml`, set the `replicas` field (if using Compose v3+ with Swarm):
  ```yaml
  incident-worker:
    ...
    deploy:
      replicas: 3
  ```
- Or, run multiple containers manually:
  ```sh
  docker-compose up --scale incident-worker=3
  ```

Increasing the number of replicas means more worker processes will poll the task queue and process tasks in parallel, improving throughput and resilience.

---
## Key Points
- **Autoscaling is not automatic by default:** You must configure the autoscaler and define scaling rules.
- **Workers compete for tasks:** After scaling, all workers in a pool pull from the same queue and process tasks independently.
- **Design for clarity:** For large systems, it's best to give each worker pool a clear responsibility by using separate task queues.

This approach ensures your Temporal system can handle increased load automatically, as long as you set up the right autoscaling logic and monitoring.
