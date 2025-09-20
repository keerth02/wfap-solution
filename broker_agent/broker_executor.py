"""Broker Agent Executor - Pure message routing"""
import sys
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path for protocols import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    Message,
    TextPart,
    Artifact,
)
from a2a.utils import new_agent_text_message, new_task, new_text_artifact
import httpx

class BrokerAgentExecutor(AgentExecutor):
    """Broker Agent Executor for pure message routing"""

    def __init__(self):
        # Bank endpoints
        self.bank_endpoints = {
            "wells-fargo": "http://localhost:8001",
            "bank-of-america": "http://localhost:8002"
        }
        
        # Simple audit log for routing events
        self.audit_log = []

    async def _log_audit(self, action: str, details: Dict[str, Any] = None):
        """Log audit trail"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details or {}
        }
        self.audit_log.append(audit_entry)
        print(f"🔍 AUDIT: {action} - {audit_entry['timestamp']}")

    async def _route_to_banks(self, message_content: str) -> List[Dict[str, Any]]:
        """Route message content to all bank agents"""
        responses = []
        
        async with httpx.AsyncClient() as client:
            for bank_name, endpoint in self.bank_endpoints.items():
                try:
                    # Send message to bank agent
                    response = await client.post(
                        f"{endpoint}",
                        json={
                            "jsonrpc": "2.0",
                            "id": f"broker-{bank_name}",
                            "method": "message/send",
                            "params": {
                                "id": f"task-{bank_name}",
                                "message": {
                                    "messageId": f"msg-{bank_name}",
                                    "role": "user",
                                    "parts": [
                                        {
                                            "type": "text",
                                            "text": message_content
                                        }
                                    ]
                                }
                            }
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        bank_response = response.json()
                        responses.append({
                            "bank": bank_name,
                            "response": bank_response,
                            "status": "success"
                        })
                        await self._log_audit("bank_routing", {
                            "bank": bank_name,
                            "endpoint": endpoint,
                            "status": "success"
                        })
                    else:
                        responses.append({
                            "bank": bank_name,
                            "response": None,
                            "status": "error",
                            "error": f"HTTP {response.status_code}"
                        })
                        await self._log_audit("bank_routing_error", {
                            "bank": bank_name,
                            "endpoint": endpoint,
                            "status": "error",
                            "error": f"HTTP {response.status_code}"
                        })
                        
                except Exception as e:
                    responses.append({
                        "bank": bank_name,
                        "response": None,
                        "status": "error",
                        "error": str(e)
                    })
                    await self._log_audit("bank_routing_exception", {
                        "bank": bank_name,
                        "endpoint": endpoint,
                        "error": str(e)
                    })
        
        return responses

    async def _aggregate_responses(self, bank_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate and validate bank responses"""
        valid_offers = []
        errors = []
        
        for response in bank_responses:
            if response["status"] == "success":
                try:
                    # Extract offer from bank response
                    bank_data = response["response"]
                    if "result" in bank_data and "artifacts" in bank_data["result"]:
                        artifacts = bank_data["result"]["artifacts"]
                        for artifact in artifacts:
                            if artifact and "parts" in artifact:
                                for part in artifact["parts"]:
                                    if part.get("kind") == "text" and "text" in part:
                                        try:
                                            offer_data = json.loads(part["text"])
                                            valid_offers.append(offer_data)
                                            await self._log_audit("offer_received", {
                                                "bank": response["bank"],
                                                "offer_id": offer_data.get("offer_id", "unknown")
                                            })
                                        except json.JSONDecodeError:
                                            # If it's not JSON, treat as text response
                                            await self._log_audit("text_response_received", {
                                                "bank": response["bank"],
                                                "response": part["text"][:100] + "..."
                                            })
                except Exception as e:
                    errors.append({
                        "bank": response["bank"],
                        "error": f"Failed to parse offer: {str(e)}"
                    })
            else:
                errors.append({
                    "bank": response["bank"],
                    "error": response.get("error", "Unknown error")
                })
        
        return {
            "offers": valid_offers,
            "errors": errors,
            "total_banks": len(bank_responses),
            "successful_responses": len(valid_offers),
            "failed_responses": len(errors)
        }

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute broker agent logic - pure message routing"""
        user_input = context.get_user_input()
        task = context.current_task

        if not context.message:
            raise Exception('No message provided')

        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        try:
            # Update task status to working
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(state=TaskState.working),
                    final=False,
                    context_id=task.context_id,
                    task_id=task.id,
                )
            )

            # Log incoming message
            await self._log_audit("message_received", {
                "message_length": len(user_input),
                "message_preview": user_input[:100] + "..." if len(user_input) > 100 else user_input
            })

            # Route to banks (no JWT validation - banks will handle it)
            bank_responses = await self._route_to_banks(user_input)
            
            # Aggregate responses
            aggregated_result = await self._aggregate_responses(bank_responses)
            
            # Create response message
            response_data = {
                "status": "success",
                "message_routed": True,
                "banks_contacted": list(self.bank_endpoints.keys()),
                "aggregated_result": aggregated_result,
                "audit_summary": {
                    "total_audit_entries": len(self.audit_log),
                    "last_audit_entry": self.audit_log[-1] if self.audit_log else None
                }
            }
            
            response_text = json.dumps(response_data, indent=2)
            
            # Send final result
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    context_id=task.context_id,
                    task_id=task.id,
                    last_chunk=True,
                    artifact=new_text_artifact(
                        name='broker_result',
                        description='Broker routing result with bank responses',
                        text=response_text,
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
            
        except Exception as e:
            error_msg = f"❌ Broker routing failed: {str(e)}"
            await event_queue.enqueue_event(
                TaskArtifactUpdateEvent(
                    append=False,
                    context_id=task.context_id,
                    task_id=task.id,
                    last_chunk=True,
                    artifact=new_text_artifact(
                        name='broker_error',
                        description='Broker routing error',
                        text=error_msg,
                    ),
                )
            )
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    status=TaskStatus(state=TaskState.failed),
                    final=True,
                    context_id=task.context_id,
                    task_id=task.id,
                )
            )

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> None:
        """Cancel broker operation"""
        pass