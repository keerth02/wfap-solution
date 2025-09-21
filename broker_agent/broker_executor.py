"""Broker Agent Executor - Pure message routing with OAuth authentication"""
import sys
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path for protocols import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import authentication manager
from auth_config import auth_manager, AUTH_CONFIG

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
    """Broker Agent Executor for pure message routing with OAuth authentication"""

    def __init__(self):
        # Bank endpoints
        self.bank_endpoints = {
            "wells-fargo": "http://localhost:8001",
            "bank-of-america": "http://localhost:8002",
            "chase-bank": "http://localhost:8003"
        }
        
        # Simple audit log for routing events
        self.audit_log = []
        
        # Authentication endpoints
        self.auth_endpoints = {
            "token": "/auth/token",
            "verify": "/auth/verify"
        }

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
    
    async def _handle_auth_token_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle OAuth token request"""
        print(f"🔐 BROKER: Token request received")
        
        client_id = request_data.get("client_id")
        client_secret = request_data.get("client_secret")
        grant_type = request_data.get("grant_type", "client_credentials")
        
        if grant_type != "client_credentials":
            auth_manager.log_auth_event("invalid_grant_type", client_id or "unknown", {
                "grant_type": grant_type
            })
            return {
                "error": "unsupported_grant_type",
                "error_description": "Only client_credentials grant type is supported"
            }
        
        if not client_id or not client_secret:
            auth_manager.log_auth_event("missing_credentials", client_id or "unknown")
            return {
                "error": "invalid_request",
                "error_description": "client_id and client_secret are required"
            }
        
        # Generate token
        token_data = auth_manager.generate_access_token(client_id, client_secret)
        
        if not token_data:
            auth_manager.log_auth_event("invalid_credentials", client_id)
            return {
                "error": "invalid_client",
                "error_description": "Invalid client credentials"
            }
        
        auth_manager.log_auth_event("token_issued", client_id, {
            "expires_at": token_data["expires_at"]
        })
        
        return token_data
    
    async def _handle_auth_verify(self, token: str) -> Dict[str, Any]:
        """Handle token verification request"""
        print(f"🔍 BROKER: Token verification request")
        
        payload = auth_manager.validate_token(token)
        
        if not payload:
            auth_manager.log_auth_event("token_verification_failed", "unknown")
            return {
                "valid": False,
                "error": "invalid_token"
            }
        
        client_info = auth_manager.get_client_info(payload["client_id"])
        
        auth_manager.log_auth_event("token_verified", payload["client_id"])
        
        return {
            "valid": True,
            "client_id": payload["client_id"],
            "scope": payload.get("scope"),
            "expires_at": datetime.fromtimestamp(payload["exp"]).isoformat(),
            "client_name": client_info.get("name") if client_info else None
        }
    
    async def _validate_bearer_token(self, headers: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Validate Bearer token from request headers"""
        auth_header = headers.get("Authorization") or headers.get("authorization")
        
        if not auth_header:
            print(f"❌ BROKER: No Authorization header provided")
            return None
        
        if not auth_header.startswith("Bearer "):
            print(f"❌ BROKER: Invalid Authorization header format")
            return None
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        payload = auth_manager.validate_token(token)
        
        if not payload:
            print(f"❌ BROKER: Invalid or expired token")
            return None
        
        print(f"✅ BROKER: Token validated for client_id: {payload['client_id']}")
        return payload
    
    async def _extract_auth_from_message(self, message_content: str) -> Optional[Dict[str, Any]]:
        """Extract and validate authentication from message content"""
        try:
            # Parse the message content
            message_data = json.loads(message_content)
            
            # Check if it's an authenticated message format
            if not isinstance(message_data, dict):
                print(f"❌ BROKER: Message is not a valid JSON object")
                return None
            
            # Extract authentication information
            auth_token = message_data.get("auth_token")
            client_id = message_data.get("client_id")
            message_type = message_data.get("message_type")
            timestamp = message_data.get("timestamp")
            
            if not auth_token:
                print(f"❌ BROKER: No auth_token found in message")
                return None
            
            if not auth_token.startswith("Bearer "):
                print(f"❌ BROKER: Invalid auth_token format - must start with 'Bearer '")
                return None
            
            # Extract token and validate
            token = auth_token[7:]  # Remove "Bearer " prefix
            payload = auth_manager.validate_token(token)
            
            if not payload:
                print(f"❌ BROKER: Invalid or expired token in message")
                return None
            
            # Verify client_id matches token
            if client_id and payload.get("client_id") != client_id:
                print(f"❌ BROKER: Client ID mismatch - token: {payload.get('client_id')}, message: {client_id}")
                return None
            
            # Log successful authentication
            print(f"✅ BROKER: Message authentication successful")
            print(f"   🔐 Token: {token[:20]}...")
            print(f"   👤 Client ID: {payload['client_id']}")
            print(f"   📋 Message Type: {message_type}")
            print(f"   🕐 Timestamp: {timestamp}")
            
            # Log authentication event
            auth_manager.log_auth_event("message_authenticated", payload["client_id"], {
                "message_type": message_type,
                "timestamp": timestamp,
                "token_preview": token[:20] + "..."
            })
            
            return payload
            
        except json.JSONDecodeError as e:
            print(f"❌ BROKER: Failed to parse message content as JSON: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ BROKER: Error extracting authentication from message: {str(e)}")
            return None

    async def _route_to_banks(self, message_content: str, auth_payload: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Route message content to all bank agents with embedded authentication"""
        responses = []
        
        # Get broker token for outbound requests
        broker_token = None
        if auth_payload:
            broker_token = auth_manager.generate_access_token(
                AUTH_CONFIG["broker"]["client_id"],
                AUTH_CONFIG["broker"]["client_secret"]
            )
            if broker_token:
                broker_token = broker_token["access_token"]
        
        async with httpx.AsyncClient() as client:
            for bank_name, endpoint in self.bank_endpoints.items():
                try:
                    # Create authenticated message for bank
                    authenticated_bank_message = {
                        "auth_token": f"Bearer {broker_token}" if broker_token else None,
                        "client_id": AUTH_CONFIG["broker"]["client_id"],
                        "message_type": "credit_intent",
                        "data": json.loads(message_content) if message_content else {},
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "broker",
                        "target_bank": bank_name
                    }
                    
                    print(f"📤 BROKER → {bank_name.upper()}: Sending authenticated message")
                    print(f"   🔐 Broker Token: {broker_token[:20] + '...' if broker_token else 'None'}")
                    print(f"   👤 Broker Client ID: {AUTH_CONFIG['broker']['client_id']}")
                    
                    # Send authenticated message to bank agent
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
                                            "text": json.dumps(authenticated_bank_message)
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

    async def _route_message(self, user_input: str, auth_payload: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Route message based on content - negotiation or regular credit intent with authentication"""
        try:
            # Parse the authenticated message format
            message_data = json.loads(user_input)
            
            # Extract the actual message data
            actual_message_data = message_data.get("data", message_data)
            message_type = message_data.get("message_type", "unknown")
            
            print(f"📋 BROKER: Processing {message_type} message")
            
            # Check if this is a negotiation message
            if message_type == "negotiation_request" or actual_message_data.get("action") == "negotiate_offer":
                bank_name = actual_message_data.get("bank_name", "").lower()
                print(f"🔄 NEGOTIATION DETECTED - Routing to {bank_name}")
                return await self._route_negotiation_to_bank(json.dumps(actual_message_data), bank_name, auth_payload)
            else:
                # Regular credit intent - route to all banks
                print(f"📤 REGULAR MESSAGE - Routing to all banks")
                return await self._route_to_banks(json.dumps(actual_message_data), auth_payload)
                
        except (json.JSONDecodeError, AttributeError) as e:
            # Not JSON or not a structured message - route to all banks
            print(f"❌ JSON parse failed: {str(e)}")
            print(f"📤 FALLBACK - Routing to all banks")
            return await self._route_to_banks(user_input, auth_payload)

    async def _route_negotiation_to_bank(self, negotiation_message: str, bank_name: str, auth_payload: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Route negotiation message to specific bank only with authentication"""
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
        
        # Get broker token for outbound requests
        broker_token = None
        if auth_payload:
            broker_token = auth_manager.generate_access_token(
                AUTH_CONFIG["broker"]["client_id"],
                AUTH_CONFIG["broker"]["client_secret"]
            )
            if broker_token:
                broker_token = broker_token["access_token"]
        
        print(f"🎯 BROKER → {bank_name.upper()} NEGOTIATION:")
        print(f"   🌐 Endpoint: {endpoint}")
        print(f"   📄 Message: {negotiation_message}")
        if broker_token:
            print(f"   🔐 Using Bearer token for authentication")
        
        await self._log_audit("negotiation_routing", {
            "bank_name": bank_name,
            "endpoint": endpoint,
            "message_type": "negotiation",
            "authenticated": bool(broker_token)
        })
        
        try:
            async with httpx.AsyncClient() as client:
                # Create authenticated negotiation message for bank
                authenticated_negotiation_message = {
                    "auth_token": f"Bearer {broker_token}" if broker_token else None,
                    "client_id": AUTH_CONFIG["broker"]["client_id"],
                    "message_type": "negotiation_request",
                    "data": json.loads(negotiation_message) if negotiation_message else {},
                    "timestamp": datetime.utcnow().isoformat(),
                    "source": "broker",
                    "target_bank": bank_name
                }
                
                print(f"📤 BROKER → {bank_name.upper()}: Sending authenticated negotiation")
                print(f"   🔐 Broker Token: {broker_token[:20] + '...' if broker_token else 'None'}")
                print(f"   👤 Broker Client ID: {AUTH_CONFIG['broker']['client_id']}")
                
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
                                "parts": [{"text": json.dumps(authenticated_negotiation_message)}],
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

    async def _handle_auth_endpoints(self, user_input: str, context: RequestContext, event_queue: EventQueue, task) -> None:
        """Handle OAuth authentication endpoints"""
        try:
            if user_input.startswith("/auth/token"):
                # Handle token request
                request_data = json.loads(user_input.split("/auth/token", 1)[1].strip() or "{}")
                token_response = await self._handle_auth_token_request(request_data)
                
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=False,
                        context_id=task.context_id,
                        task_id=task.id,
                        last_chunk=True,
                        artifact=new_text_artifact(
                            name='auth_token_response',
                            description='OAuth token response',
                            text=json.dumps(token_response, indent=2),
                        ),
                    )
                )
                
            elif user_input.startswith("/auth/verify"):
                # Handle token verification
                token = user_input.split("/auth/verify", 1)[1].strip()
                verify_response = await self._handle_auth_verify(token)
                
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        append=False,
                        context_id=task.context_id,
                        task_id=task.id,
                        last_chunk=True,
                        artifact=new_text_artifact(
                            name='auth_verify_response',
                            description='Token verification response',
                            text=json.dumps(verify_response, indent=2),
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
            await self._send_auth_error(event_queue, task, f"Auth endpoint error: {str(e)}")
    
    async def _send_auth_error(self, event_queue: EventQueue, task, error_msg: str) -> None:
        """Send authentication error response"""
        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                append=False,
                context_id=task.context_id,
                task_id=task.id,
                last_chunk=True,
                artifact=new_text_artifact(
                    name='auth_error',
                    description='Authentication error',
                    text=json.dumps({
                        "error": "authentication_failed",
                        "error_description": error_msg
                    }, indent=2),
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

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute broker agent logic - pure message routing with OAuth authentication"""
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

            # Check for authentication endpoints first
            if user_input.startswith("/auth/"):
                await self._handle_auth_endpoints(user_input, context, event_queue, task)
                return

            # Extract and validate authentication from message content
            auth_payload = await self._extract_auth_from_message(user_input)
            if not auth_payload:
                print(f"❌ BROKER: No valid authentication found in message")
                await self._send_auth_error(event_queue, task, "Missing or invalid authentication token")
                return
            
            print(f"✅ BROKER: Authentication validated for client_id: {auth_payload['client_id']}")

            # Log incoming message with full content
            print(f"📨 BROKER RECEIVED MESSAGE:")
            print(f"   📏 Length: {len(user_input)} characters")
            print(f"   📄 Content: {user_input}")
            print(f"   🕐 Time: {datetime.utcnow().isoformat()}")
            if auth_payload:
                print(f"   🔐 Authenticated as: {auth_payload['client_id']}")
            
            await self._log_audit("message_received", {
                "message_length": len(user_input),
                "message_content": user_input,
                "task_id": task.id if task else "unknown",
                "authenticated": bool(auth_payload),
                "client_id": auth_payload.get("client_id") if auth_payload else None
            })

            # Check if this is a negotiation message and route accordingly
            bank_responses = await self._route_message(user_input, auth_payload)
            
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