
"""
import asyncio
from temporalio import workflow

@workflow.defn
class DeclarativeWorkflow:
    def __init__(self):
        self.state = ""
        self.machine = {}
        self.context = {}
        self.signal_queue = asyncio.Queue()

    @workflow.run
    async def run(self, machine_spec, initial_context=None):
        self.machine = machine_spec
        self.state = self.machine["initial"]
        self.context = initial_context or {}
        for state_def in self.machine.get("states", {}).values():
            for signal in state_def.get("on", {}):
                workflow.set_signal_handler(signal, lambda payload=None, s=signal: self.signal_queue.put_nowait((s, payload or {})))
        while True:
            state_def = self.machine["states"][self.state]
            if state_def.get("type") == "final":
                break
            event, payload = await self.signal_queue.get()
            self.context.update(payload)
            transition = state_def.get("on", {}).get(event)
            if not transition:
                continue
            action = transition.get("action")
            target = transition.get("target", self.state)
            if action:
                await self._run_activity(action, self.context)
            self.state = target
        return self.context

    async def _run_activity(self, action, context):
        return await workflow.execute_activity(
            action["name"], context, schedule_to_close_timeout=60
        )
"""