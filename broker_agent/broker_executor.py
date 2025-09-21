"""Broker Agent Executor - Pure message routing (no authentication)"""
import sys
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path for protocols import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# HMAC Signature validation for secure agent communication

from a2a.server.agent_execution import AgentExecutor, RequestContext
from signature_utils import generate_signature, validate_signature, extract_signature_from_message
from secrets_manager import SecretsManager
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
    """Broker Agent Executor with HMAC signature validation for secure message routing"""

    def __init__(self):
        # Bank endpoints
        self.bank_endpoints = {
            "wells-fargo": "http://localhost:8001",
            "bank-of-america": "http://localhost:8002",
            "chase-bank": "http://localhost:8003"
        }
        
        # Simple audit log for routing events
        self.audit_log = []
        
        # Initialize secrets manager for signature validation
        self.secrets_manager = SecretsManager()
        print("🔐 BROKER: Initialized with HMAC signature validation")

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
    
    async def _validate_message_signature(self, message_content: str, agent_id: str) -> bool:
        """
        Validate HMAC signature for incoming message
        
        Args:
            message_content: JSON string containing message data
            agent_id: Identifier of the sending agent
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            print(f"🔐 BROKER: Validating signature for message from {agent_id}")
            
            # Parse message content
            message_data = json.loads(message_content)
            
            # Extract signature from message
            message_without_signature, signature = extract_signature_from_message(message_data)
            
            if not signature:
                print(f"❌ BROKER SIGNATURE VALIDATION FAILED:")
                print(f"   🔐 Agent: {agent_id}")
                print(f"   📝 Message Type: {message_data.get('message_type', 'unknown')}")
                print(f"   ⚠️  Reason: No signature found in message")
                print(f"   ⏰ Timestamp: {datetime.utcnow().isoformat()}")
                await self._log_audit("signature_missing", {
                    "agent_id": agent_id,
                    "message_type": message_data.get("message_type", "unknown"),
                    "validation_status": "FAILED",
                    "failure_reason": "No signature found in message",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return False
            
            # Get agent's secret key
            secret_key = self.secrets_manager.get_secret(agent_id)
            if not secret_key:
                print(f"❌ BROKER SIGNATURE VALIDATION FAILED:")
                print(f"   🔐 Agent: {agent_id}")
                print(f"   📝 Message Type: {message_data.get('message_type', 'unknown')}")
                print(f"   ⚠️  Reason: No secret key found for agent")
                print(f"   ⏰ Timestamp: {datetime.utcnow().isoformat()}")
                await self._log_audit("secret_key_missing", {
                    "agent_id": agent_id,
                    "message_type": message_data.get("message_type", "unknown"),
                    "validation_status": "FAILED",
                    "failure_reason": f"No secret key found for agent {agent_id}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return False
            
            # Validate signature
            is_valid = validate_signature(message_without_signature, signature, secret_key)
            
            if is_valid:
                print(f"✅ BROKER SIGNATURE VALIDATION SUCCESS:")
                print(f"   🔐 Agent: {agent_id}")
                print(f"   📝 Message Type: {message_data.get('message_type', 'unknown')}")
                print(f"   🔑 Signature: {signature[:16]}...{signature[-8:]}")
                print(f"   ⏰ Timestamp: {datetime.utcnow().isoformat()}")
                await self._log_audit("signature_validated", {
                    "agent_id": agent_id,
                    "message_type": message_data.get("message_type", "unknown"),
                    "signature_preview": f"{signature[:16]}...{signature[-8:]}",
                    "validation_status": "SUCCESS",
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                print(f"❌ BROKER SIGNATURE VALIDATION FAILED:")
                print(f"   🔐 Agent: {agent_id}")
                print(f"   📝 Message Type: {message_data.get('message_type', 'unknown')}")
                print(f"   🔑 Signature: {signature[:16]}...{signature[-8:]}")
                print(f"   ⏰ Timestamp: {datetime.utcnow().isoformat()}")
                print(f"   ⚠️  Reason: HMAC signature validation failed")
                await self._log_audit("signature_invalid", {
                    "agent_id": agent_id,
                    "message_type": message_data.get("message_type", "unknown"),
                    "signature_preview": f"{signature[:16]}...{signature[-8:]}",
                    "validation_status": "FAILED",
                    "failure_reason": "HMAC signature validation failed",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            return is_valid
            
        except json.JSONDecodeError as e:
            print(f"❌ BROKER: Invalid JSON in message from {agent_id}: {e}")
            return False
        except Exception as e:
            print(f"❌ BROKER: Signature validation error for {agent_id}: {e}")
            return False
    
    def _add_signature_to_message(self, message_content: str) -> str:
        """
        Add broker's signature to outgoing message
        
        Args:
            message_content: JSON string containing message data
            
        Returns:
            JSON string with broker's signature added
        """
        try:
            message_data = json.loads(message_content)
            
            # Get broker's secret key
            secret_key = self.secrets_manager.get_secret("broker-agent")
            if not secret_key:
                print(f"❌ BROKER: No secret key found for broker-agent")
                return message_content
            
            # Generate signature
            signature = generate_signature(message_data, secret_key)
            message_data['signature'] = signature
            
            print(f"🔐 BROKER: SIGNATURE GENERATION SUCCESS")
            print(f"   📤 Direction: Outgoing message")
            print(f"   📝 Message Type: {message_data.get('message_type', 'unknown')}")
            print(f"   🔑 Signature: {signature[:16]}...{signature[-8:]}")
            print(f"   ⏰ Timestamp: {datetime.utcnow().isoformat()}")
            return json.dumps(message_data)
            
        except Exception as e:
            print(f"❌ BROKER: Signature generation error: {e}")
            return message_content

    async def _route_to_banks(self, message_content: str) -> List[Dict[str, Any]]:
        """Route message content to all bank agents with HMAC signature"""
        responses = []
        
        async with httpx.AsyncClient() as client:
            for bank_name, endpoint in self.bank_endpoints.items():
                try:
                    # Create message for bank
                    bank_message = {
                        "message_type": "credit_intent",
                        "agent_id": "broker-agent",
                        "data": json.loads(message_content) if message_content else {},
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "broker",
                        "target_bank": bank_name
                    }
                    
                    # Add broker's signature to the message
                    bank_message_json = json.dumps(bank_message)
                    bank_message_with_signature = self._add_signature_to_message(bank_message_json)
                    
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
                                            "text": bank_message_with_signature
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
                # Create negotiation message for bank
                negotiation_message_content = {
                    "message_type": "negotiation_request",
                    "agent_id": "broker-agent",
                    "data": json.loads(negotiation_message) if negotiation_message else {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "broker",
                    "target_bank": bank_name
                }
                
                # Add broker's signature to the negotiation message
                negotiation_message_json = json.dumps(negotiation_message_content)
                negotiation_message_with_signature = self._add_signature_to_message(negotiation_message_json)
                
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
                                "parts": [{"text": negotiation_message_with_signature}],
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
        """Execute broker agent logic with HMAC signature validation"""
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
            
            # Parse message to get agent_id for signature validation
            try:
                message_data = json.loads(user_input)
                agent_id = message_data.get('agent_id', 'unknown')
                message_type = message_data.get('message_type', 'unknown')
                
                print(f"🔐 BROKER: Processing message from {agent_id} (type: {message_type})")
                
                # Validate signature for intents and offers
                if message_type in ['credit_intent', 'negotiation_request']:
                    print(f"🔐 BROKER: Starting signature validation for {agent_id}")
                    print(f"   📝 Message Type: {message_type}")
                    print(f"   📏 Message Length: {len(user_input)} characters")
                    
                    if not await self._validate_message_signature(user_input, agent_id):
                        print(f"🚫 BROKER: MESSAGE REJECTED - SIGNATURE VALIDATION FAILED")
                        print(f"   🔐 Agent: {agent_id}")
                        print(f"   📝 Message Type: {message_type}")
                        print(f"   ⚠️  Action: Marking task as failed")
                        await event_queue.enqueue_event(
                            TaskStatusUpdateEvent(
                                status=TaskStatus(state=TaskState.failed),
                                final=True,
                                context_id=task.context_id,
                                task_id=task.id,
                            )
                        )
                        return
                    
                    print(f"🎉 BROKER: MESSAGE ACCEPTED - SIGNATURE VALIDATION PASSED")
                    print(f"   🔐 Agent: {agent_id}")
                    print(f"   📝 Message Type: {message_type}")
                    print(f"   ✅ Action: Proceeding with message routing")
                else:
                    print(f"ℹ️ BROKER: SIGNATURE VALIDATION SKIPPED")
                    print(f"   📝 Message Type: {message_type}")
                    print(f"   📋 Reason: Message type does not require signature validation")
                    
            except json.JSONDecodeError:
                print("❌ BROKER: Invalid JSON format in message")
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        status=TaskStatus(state=TaskState.failed),
                        final=True,
                        context_id=task.context_id,
                        task_id=task.id,
                    )
                )
                return

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