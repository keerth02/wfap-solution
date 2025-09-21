"""Broker Agent Executor - Pure message routing (no authentication)"""
import sys
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path for protocols import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Authentication removed - no longer needed

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
    """Broker Agent Executor for pure message routing (no authentication)"""

    def __init__(self):
        # Bank endpoints
        self.bank_endpoints = {
            "wells-fargo": "http://localhost:8001",
            "bank-of-america": "http://localhost:8002",
            "chase-bank": "http://localhost:8003"
        }
        
        # Simple audit log for routing events
        self.audit_log = []
        
        # Authentication endpoints removed - no longer needed

    async def _log_audit(self, action: str, details: Dict[str, Any] = None):
        """Log audit trail with detailed information"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "details": details or {}
        }
        self.audit_log.append(audit_entry)
        print(f"🔍 BROKER AUDIT: {action} - {audit_entry['timestamp']}")
        if details:
            print(f"   📋 Details: {json.dumps(details, indent=2)}")
    
    # Authentication methods removed - no longer needed
    
    # All authentication methods removed - no longer needed

    async def _route_to_banks(self, message_content: str) -> List[Dict[str, Any]]:
        """Route message content to all bank agents (no authentication)"""
        responses = []
        
        async with httpx.AsyncClient() as client:
            for bank_name, endpoint in self.bank_endpoints.items():
                try:
                    # Create message for bank (no authentication)
                    bank_message = {
                        "message_type": "credit_intent",
                        "agent_id": "broker-agent",
                        "data": json.loads(message_content) if message_content else {},
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "broker",
                        "target_bank": bank_name
                    }
                    
                    print(f"📤 BROKER → {bank_name.upper()}: Sending message")
                    print(f"   👤 Agent ID: broker-agent")
                    
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
                                            "text": json.dumps(bank_message)
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
                        
                        print(f"✅ BROKER → {bank_name.upper()} SUCCESS:")
                        print(f"   🌐 Endpoint: {endpoint}")
                        print(f"   📊 Response: {json.dumps(bank_response, indent=2)}")
                        
                        await self._log_audit("bank_routing_success", {
                            "bank": bank_name,
                            "endpoint": endpoint,
                            "status": "success",
                            "response_preview": str(bank_response)[:200] + "..." if len(str(bank_response)) > 200 else str(bank_response)
                        })
                    else:
                        responses.append({
                            "bank": bank_name,
                            "response": None,
                            "status": "error",
                            "error": f"HTTP {response.status_code}"
                        })
                        
                        print(f"❌ BROKER → {bank_name.upper()} ERROR:")
                        print(f"   🌐 Endpoint: {endpoint}")
                        print(f"   🚫 Status: HTTP {response.status_code}")
                        print(f"   📄 Response: {response.text}")
                        
                        await self._log_audit("bank_routing_error", {
                            "bank": bank_name,
                            "endpoint": endpoint,
                            "status": "error",
                            "error": f"HTTP {response.status_code}",
                            "response_text": response.text
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
        text_responses = []
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
                                            text_responses.append({
                                                "bank": response["bank"],
                                                "response": part["text"],
                                                "type": "text_response"
                                            })
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
            "text_responses": text_responses,
            "errors": errors,
            "total_banks": len(bank_responses),
            "successful_responses": len(valid_offers) + len(text_responses),
            "failed_responses": len(errors)
        }

    async def _route_message(self, user_input: str) -> List[Dict[str, Any]]:
        """Route message based on content - negotiation or regular credit intent (no authentication)"""
        try:
            # Parse the message format
            message_data = json.loads(user_input)
            
            # Extract the actual message data
            actual_message_data = message_data.get("data", message_data)
            message_type = message_data.get("message_type", "unknown")
            
            print(f"📋 BROKER: Processing {message_type} message")
            
            # Check if this is a negotiation message
            if message_type == "negotiation_request" or actual_message_data.get("action") == "negotiate_offer":
                bank_name = actual_message_data.get("bank_name", "").lower()
                print(f"🔄 NEGOTIATION DETECTED - Routing to {bank_name}")
                return await self._route_negotiation_to_bank(json.dumps(actual_message_data), bank_name)
            else:
                # Regular credit intent - route to all banks
                print(f"📤 REGULAR MESSAGE - Routing to all banks")
                return await self._route_to_banks(json.dumps(actual_message_data))
                
        except (json.JSONDecodeError, AttributeError) as e:
            # Not JSON or not a structured message - route to all banks
            print(f"❌ JSON parse failed: {str(e)}")
            print(f"📤 FALLBACK - Routing to all banks")
            return await self._route_to_banks(user_input)

    async def _route_negotiation_to_bank(self, negotiation_message: str, bank_name: str) -> List[Dict[str, Any]]:
        """Route negotiation message to specific bank only (no authentication)"""
        print(f"🔄 BROKER ROUTING NEGOTIATION TO {bank_name.upper()}")
        
        # Map bank names to endpoints
        bank_endpoint_map = {
            "wells fargo": "wells-fargo",
            "wells-fargo": "wells-fargo", 
            "bank of america": "bank-of-america",
            "bank-of-america": "bank-of-america",
            "chase bank": "chase-bank",
            "chase-bank": "chase-bank"
        }
        
        endpoint_key = bank_endpoint_map.get(bank_name.lower(), bank_name.lower())
        endpoint = self.bank_endpoints.get(endpoint_key)
        
        if not endpoint:
            print(f"❌ Unknown bank: {bank_name}")
            return [{
                "bank": bank_name,
                "response": None,
                "status": "error",
                "error": f"Unknown bank: {bank_name}"
            }]
        
        print(f"🎯 BROKER → {bank_name.upper()} NEGOTIATION:")
        print(f"   🌐 Endpoint: {endpoint}")
        print(f"   📄 Message: {negotiation_message}")
        
        await self._log_audit("negotiation_routing", {
            "bank_name": bank_name,
            "endpoint": endpoint,
            "message_type": "negotiation"
        })
        
        try:
            async with httpx.AsyncClient() as client:
                # Create negotiation message for bank (no authentication)
                negotiation_message_content = {
                    "message_type": "negotiation_request",
                    "agent_id": "broker-agent",
                    "data": json.loads(negotiation_message) if negotiation_message else {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "broker",
                    "target_bank": bank_name
                }
                
                print(f"📤 BROKER → {bank_name.upper()}: Sending negotiation")
                print(f"   👤 Agent ID: broker-agent")
                
                response = await client.post(
                    f"{endpoint}",
                    json={
                        "jsonrpc": "2.0",
                        "id": f"negotiation_{int(datetime.utcnow().timestamp())}",
                        "method": "message/send",
                        "params": {
                            "id": f"negotiation_{int(datetime.utcnow().timestamp())}",
                            "message": {
                                "role": "user",
                                "parts": [{"text": json.dumps(negotiation_message_content)}],
                                "messageId": f"negotiation_{int(datetime.utcnow().timestamp())}"
                            }
                        }
                    },
                    timeout=60.0
                )
                
                print(f"✅ BROKER ← {bank_name.upper()} NEGOTIATION RESPONSE:")
                print(f"   📊 Status: HTTP {response.status_code}")
                print(f"   📄 Response: {response.json()}")
                
                await self._log_audit("negotiation_response_received", {
                    "bank": bank_name,
                    "endpoint": endpoint,
                    "status": "success",
                    "response_data": response.json()
                })
                
                return [{
                    "bank": bank_name,
                    "response": response.json(),
                    "status": "success"
                }]
                
        except Exception as e:
            print(f"❌ BROKER ← {bank_name.upper()} NEGOTIATION ERROR:")
            print(f"   🚨 Error: {str(e)}")
            
            await self._log_audit("negotiation_error", {
                "bank": bank_name,
                "endpoint": endpoint,
                "error": str(e)
            })
            
            return [{
                "bank": bank_name,
                "response": None,
                "status": "error",
                "error": str(e)
            }]

    # Authentication endpoint methods removed - no longer needed

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute broker agent logic - pure message routing (no authentication)"""
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

            # Log incoming message with full content
            print(f"📨 BROKER RECEIVED MESSAGE:")
            print(f"   📏 Length: {len(user_input)} characters")
            print(f"   📄 Content: {user_input}")
            print(f"   🕐 Time: {datetime.utcnow().isoformat()}")
            
            await self._log_audit("message_received", {
                "message_length": len(user_input),
                "message_content": user_input,
                "task_id": task.id if task else "unknown"
            })

            # Check if this is a negotiation message and route accordingly
            bank_responses = await self._route_message(user_input)
            
            # Aggregate responses
            aggregated_result = await self._aggregate_responses(bank_responses)
            
            # Create response message with both offers and text responses
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
            
            # Create a human-readable response that includes text responses
            human_response = "Broker routing completed. "
            
            if aggregated_result["text_responses"]:
                human_response += f"Received {len(aggregated_result['text_responses'])} text responses from banks:\n\n"
                for text_resp in aggregated_result["text_responses"]:
                    human_response += f"🏦 {text_resp['bank'].upper()}:\n{text_resp['response']}\n\n"
            
            if aggregated_result["offers"]:
                human_response += f"Received {len(aggregated_result['offers'])} structured offers from banks.\n"
            
            if aggregated_result["errors"]:
                human_response += f"Encountered {len(aggregated_result['errors'])} errors from banks.\n"
            
            # Include both human-readable and structured data
            response_text = f"{human_response}\n\n--- STRUCTURED DATA ---\n{json.dumps(response_data, indent=2)}"
            
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