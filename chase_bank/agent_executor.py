"""Chase Bank Agent Executor for A2A Protocol"""
import sys
import os
import json
from datetime import datetime
from typing import override

# Add parent directory to path for protocols import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from a2a.utils import new_agent_text_message, new_task, new_text_artifact
from agent import ChaseBankAgent

class ChaseBankAgentExecutor(AgentExecutor):
    """Chase Bank Agent Executor for A2A Protocol"""

    def __init__(self):
        self.chase_bank_agent = ChaseBankAgent()

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute Chase Bank agent logic"""
        query = context.get_user_input()
        task = context.current_task

        # Enhanced logging for Chase Bank
        print(f"🏦 CHASE BANK RECEIVED REQUEST:")
        print(f"   📏 Length: {len(query)} characters")
        print(f"   📄 Content: {query}")
        print(f"   🕐 Time: {datetime.utcnow().isoformat()}")
        print(f"   🆔 Task ID: {task.id if task else 'unknown'}")

        if not context.message:
            raise Exception('No message provided')

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        async for event in self.chase_bank_agent.stream(query, task.id):
            if event['is_task_complete']:
                # Handle tool results properly - convert to JSON if it's a dict
                content = event['content']
                if isinstance(content, dict):
                    content = json.dumps(content, indent=2)
                
                print(f"✅ CHASE BANK RESPONSE GENERATED:")
                print(f"   📊 Content Type: {type(event['content'])}")
                print(f"   📄 Response: {content}")
                print(f"   🕐 Time: {datetime.utcnow().isoformat()}")
                
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=False,
                        context_id=task.context_id,
                        task_id=task.id,
                        last_chunk=True,
                        artifact=new_text_artifact(
                            name='chase_bank_response',
                            description='Chase Bank bank offer',
                            text=content,
                        ),
                    )
                )
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(state=TaskState.completed),
                        final=True,
                        context_id=task.context_id,
                        task_id=task.id,
                    )
                )
            elif event['require_user_input']:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(
                            state=TaskState.input_required,
                            message=new_agent_text_message(
                                event['content'],
                                task.context_id,
                                task.id,
                            ),
                        ),
                        final=True,
                        context_id=task.context_id,
                        task_id=task.id,
                    )
                )
            else:
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        append=True,
                        status=TaskStatus(
                            state=TaskState.working,
                            message=new_agent_text_message(
                                event['content'],
                                task.context_id,
                                task.id,
                            ),
                        ),
                        final=False,
                        context_id=task.context_id,
                        task_id=task.id,
                    )
                )

    @override
    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel Chase Bank agent processing"""
        raise Exception('Chase Bank agent task cancellation not supported')
