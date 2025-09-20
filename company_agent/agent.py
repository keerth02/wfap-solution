"""Company Agent Implementation with A2A communication"""
import sys
import os
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

# Add parent directory to path for protocols import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from collections.abc import AsyncIterable

from protocols.intent import CreditIntent, CompanyInfo
from protocols.response import BankOffer, ESGImpact
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpx

class CompanyAgent:
    """Company Agent for credit requests with A2A communication"""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        self._agent = self._build_agent()
        self._user_id = 'company_user'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        
        
        # Broker endpoint
        self.broker_endpoint = "http://localhost:8000"
        
        # Store received offers and evaluated offers
        self.received_offers = []
        self.evaluated_offers = []

    def get_processing_message(self) -> str:
        return 'Processing your credit request and communicating with banks...'

    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the company agent."""
        LITELLM_MODEL = os.getenv('LITELLM_MODEL', 'gemini/gemini-2.0-flash')
        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name='company_agent',
            description=(
                'This agent handles corporate credit requests using A2A protocol communication. '
                'It creates structured credit intents, sends them to banks via broker, evaluates offers, '
                'and selects the best offer based on ESG and financial criteria.'
            ),
            instruction="""
You are a Company Agent responsible for managing corporate credit requests using A2A protocol communication.

WORKFLOW:
1. Create structured credit intent using create_credit_intent()
2. IMMEDIATELY call send_credit_request_to_broker() with the intent data
3. Receive responses from broker (may be offers or bank questions)
4. If bank questions received, use handle_bank_questions() to process them
5. If offers received, evaluate using evaluate_offers()
6. Select best offer using select_best_offer()
7. Optionally negotiate using negotiate_offer()

CRITICAL: After creating a credit intent, you MUST call send_credit_request_to_broker() with the intent data. Do not just describe what you would do - actually call the function.

CONDITIONAL RESPONSES:
- If banks ask for more information (text responses), use handle_bank_questions() to process them
- If banks provide structured offers, use evaluate_offers() and select_best_offer()
- You may need to gather additional information from the user and resend to banks

COMPREHENSIVE OFFER EVALUATION (BASED ONLY ON STRUCTURED BANK OFFERS):
- Primary Criterion: Composite Score (ESG-adjusted effective rate + risk penalties)
- Secondary Criterion: ESG Impact Score (ESG score + carbon footprint reduction bonus)
- Financial Analysis: Effective rate (including fees), total cost of borrowing, monthly payments
- Risk Assessment: Collateral requirements, personal guarantee, prepayment penalties
- ESG Analysis: ESG score, carbon footprint reduction, human-readable ESG summaries

EVALUATION METHODOLOGY:
- Composite Score = ESG-adjusted effective rate + risk penalties
- ESG Impact Score = ESG score + (carbon footprint reduction / 10)
- Risk Penalties: Collateral (+0.5), Personal Guarantee (+0.3), Prepayment Penalty (+0.2)
- Effective Rate includes origination fees and total cost of borrowing
- Sort by composite score (ascending) then ESG impact score (descending)

RESPONSE HANDLING:
- JSON responses = Structured offers ready for evaluation (call evaluate_offers and select_best_offer)
- Text responses = Bank needs more information or has questions (call handle_bank_questions)
- Always inform the user about the type of response received
- When banks ask questions, ask the user for the requested information

RESPONSE HANDLING WORKFLOW:
1. After sending intent to broker, check the response
2. If you receive bank_questions, call handle_bank_questions tool
3. If you receive offers, call evaluate_offers and select_best_offer
4. Always communicate clearly with the user about what happened

Always provide clear communication about offer evaluation reasoning.
            """,
            tools=[
                self.create_credit_intent,
                self.send_credit_request_to_broker,
                self.evaluate_offers,
                self.select_best_offer,
                self.handle_bank_questions,
                self.negotiate_offer,
            ],
        )

    def create_credit_intent(
        self,
        company_name: str,
        industry: str,
        annual_revenue: float,
        credit_score: int,
        years_in_business: int,
        employee_count: int,
        requested_amount: float,
        purpose: str,
        preferred_term_months: int,
        esg_requirements: str,
        preferred_interest_rate: float,
    ) -> Dict[str, Any]:
        """Create structured credit intent with company information."""
        try:
            company_info = CompanyInfo(
                name=company_name,
                industry=industry,
                annual_revenue=annual_revenue,
                credit_score=credit_score,
                years_in_business=years_in_business,
                employee_count=employee_count
            )
            
            credit_intent = CreditIntent(
                company=company_info,
                requested_amount=requested_amount,
                purpose=purpose,
                preferred_term_months=preferred_term_months,
                esg_requirements=esg_requirements,
                preferred_interest_rate=preferred_interest_rate
            )
            
            return {
                "status": "success",
                "intent": credit_intent.model_dump(mode='json'),
                "message": f"Created credit intent {credit_intent.intent_id} for {company_name}"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to create credit intent: {str(e)}"
            }

    def send_credit_request_to_broker(
        self,
        intent_data: str,
        tool_context: ToolContext = None
    ) -> Dict[str, Any]:
        """Send credit intent to broker agent."""
        # Parse intent data - handle both string and dict inputs
        if isinstance(intent_data, str):
            try:
                parsed_data = json.loads(intent_data)
                # If it's a response from create_credit_intent, extract the intent
                if isinstance(parsed_data, dict) and "intent" in parsed_data:
                    intent_dict = parsed_data["intent"]
                else:
                    intent_dict = parsed_data
            except json.JSONDecodeError:
                # If it's not valid JSON, treat as plain text
                intent_dict = {"raw_text": intent_data}
        elif isinstance(intent_data, dict):
            # If it's a response from create_credit_intent, extract the intent
            if "intent" in intent_data:
                intent_dict = intent_data["intent"]
            else:
                intent_dict = intent_data
        else:
            # Convert other types to string and wrap
            intent_dict = {"raw_text": str(intent_data)}
        
        # Send to broker via A2A - Send structured intent data
        async def _send_to_broker():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.broker_endpoint}",
                    json={
                        "jsonrpc": "2.0",
                        "id": f"company-{uuid.uuid4().hex[:8]}",
                        "method": "message/send",
                        "params": {
                            "id": f"task-{uuid.uuid4().hex[:8]}",
                            "message": {
                                "messageId": f"msg-{uuid.uuid4().hex[:8]}",
                                "role": "user",
                                "parts": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(intent_dict)
                                    }
                                ]
                            }
                        }
                    },
                    timeout=60.0
                )
                return response
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # Use ThreadPoolExecutor to run async code
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _send_to_broker())
                response = future.result()
        except RuntimeError:
            # No event loop running, create new one
            response = asyncio.run(_send_to_broker())
        
        if response.status_code == 200:
            broker_response = response.json()
            
            # Extract offers and text responses from broker response - use correct A2A format
            if "result" in broker_response and "artifacts" in broker_response["result"]:
                artifacts = broker_response["result"]["artifacts"]
                for artifact in artifacts:
                    if artifact and "parts" in artifact:
                        for part in artifact["parts"]:
                            if part.get("kind") == "text" and "text" in part:
                                response_text = part["text"]
                                
                                # Check if it contains structured data
                                if "--- STRUCTURED DATA ---" in response_text:
                                    # Extract human-readable part and structured data
                                    parts = response_text.split("--- STRUCTURED DATA ---")
                                    human_response = parts[0].strip()
                                    structured_data = parts[1].strip() if len(parts) > 1 else ""
                                    
                                    try:
                                        broker_data = json.loads(structured_data)
                                        if "aggregated_result" in broker_data:
                                            offers = broker_data["aggregated_result"].get("offers", [])
                                            text_responses = broker_data["aggregated_result"].get("text_responses", [])
                                            self.received_offers = offers
                                            
                                            # Handle text responses from banks
                                            bank_questions = []
                                            for text_resp in text_responses:
                                                bank_questions.append({
                                                    "bank": text_resp["bank"],
                                                    "question": text_resp["response"]
                                                })
                                            
                                            return {
                                                "status": "success",
                                                "sent": True,
                                                "broker_response": broker_data,
                                                "offers_received": len(offers),
                                                "text_responses_received": len(text_responses),
                                                "offers": offers,
                                                "bank_questions": bank_questions,
                                                "human_response": human_response,
                                                "message": f"Successfully sent intent to broker. Received {len(offers)} offers and {len(text_responses)} text responses from banks."
                                            }
                                    except json.JSONDecodeError:
                                        # If structured data parsing fails, return human response
                                        return {
                                            "status": "success",
                                            "sent": True,
                                            "broker_response": {"text_response": response_text},
                                            "human_response": response_text,
                                            "message": f"Broker response: {response_text}"
                                        }
                                else:
                                    # Plain text response without structured data
                                    return {
                                        "status": "success",
                                        "sent": True,
                                        "broker_response": {"text_response": response_text},
                                        "human_response": response_text,
                                        "message": f"Broker response: {response_text}"
                                    }
            
            return {
                "status": "success",
                "sent": True,
                "broker_response": broker_response,
                "message": "Successfully sent intent to broker"
            }
        else:
            return {
                "status": "error",
                "error": f"Broker communication failed: HTTP {response.status_code}",
                "response": response.text
            }

    def evaluate_offers(
        self,
        offers_data: str,
        tool_context: ToolContext = None
    ) -> Dict[str, Any]:
        """Evaluate received offers based ONLY on structured loan offer data from banks."""
        try:
            # Parse offers data - handle both string and list inputs
            if isinstance(offers_data, str):
                try:
                    offers = json.loads(offers_data)
                except json.JSONDecodeError:
                    # If it's not JSON, try to extract offers from the text
                    offers = self.received_offers
            else:
                offers = offers_data
            
            # If still no offers, use stored offers
            if not offers or not isinstance(offers, list):
                offers = self.received_offers
            
            if not offers:
                return {
                    "status": "error",
                    "error": "No offers available for evaluation"
                }
            
            evaluated_offers = []
            
            for offer in offers:
                try:
                    # Extract comprehensive offer data from structured bank offers
                    base_rate = offer.get("interest_rate", 0)
                    esg_impact = offer.get("esg_impact", {})
                    esg_score = esg_impact.get("overall_esg_score", 0)
                    approved_amount = offer.get("approved_amount", 0)
                    term_months = offer.get("term_months", 84)
                    repayment_schedule = offer.get("repayment_schedule", {})
                    origination_fee = offer.get("origination_fee", 0)
                    prepayment_penalty = offer.get("prepayment_penalty", False)
                    collateral_required = offer.get("collateral_required", False)
                    personal_guarantee_required = offer.get("personal_guarantee_required", False)
                    bank_name = offer.get("bank_name", "Unknown Bank")
                    
                    # Calculate comprehensive financial metrics
                    # 1. Carbon-adjusted interest rate (ESG bonus)
                    carbon_adjusted_rate = base_rate - (esg_score * 0.15)  # Enhanced ESG bonus
                    
                    # 2. Total cost of borrowing (including fees)
                    monthly_rate = base_rate / 100 / 12
                    monthly_payment = approved_amount * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
                    total_interest = (monthly_payment * term_months) - approved_amount
                    total_cost_of_borrowing = total_interest + origination_fee
                    
                    # 3. Effective interest rate (including fees)
                    effective_rate = ((total_cost_of_borrowing / approved_amount) * 100) * (12 / term_months)
                    
                    # 4. ESG-adjusted effective rate
                    esg_adjusted_effective_rate = effective_rate - (esg_score * 0.1)
                    
                    # 5. Risk-adjusted score (penalize for collateral/personal guarantee requirements)
                    risk_penalty = 0
                    if collateral_required:
                        risk_penalty += 0.5
                    if personal_guarantee_required:
                        risk_penalty += 0.3
                    if prepayment_penalty:
                        risk_penalty += 0.2
                    
                    # 6. Final composite score (lower is better)
                    composite_score = esg_adjusted_effective_rate + risk_penalty
                    
                    # 7. ESG impact score (higher is better)
                    esg_impact_score = esg_score + (esg_impact.get("carbon_footprint_reduction", 0) / 10)
                    
                    evaluated_offer = {
                        **offer,
                        "carbon_adjusted_rate": round(carbon_adjusted_rate, 2),
                        "total_cost_of_borrowing": round(total_cost_of_borrowing, 2),
                        "effective_rate": round(effective_rate, 2),
                        "esg_adjusted_effective_rate": round(esg_adjusted_effective_rate, 2),
                        "composite_score": round(composite_score, 2),
                        "esg_impact_score": round(esg_impact_score, 2),
                        "risk_penalty": round(risk_penalty, 2),
                        "monthly_payment": round(monthly_payment, 2),
                        "total_interest": round(total_interest, 2),
                        "evaluation_timestamp": datetime.utcnow().isoformat()
                    }
                    
                    evaluated_offers.append(evaluated_offer)
                    
                except Exception as e:
                    print(f"Error evaluating offer {offer.get('offer_id', 'unknown')}: {str(e)}")
                    continue
            
            # Sort by composite score (lower is better) - primary criterion
            # Secondary sort by ESG impact score (higher is better)
            evaluated_offers.sort(key=lambda x: (x.get("composite_score", 999), -x.get("esg_impact_score", 0)))
            
            # Store evaluated offers for selection
            self.evaluated_offers = evaluated_offers
            
            return {
                "status": "success",
                "evaluated_offers": evaluated_offers,
                "evaluation_criteria": {
                    "primary_sorting": "composite_score (ascending) - includes ESG-adjusted effective rate + risk penalties",
                    "secondary_sorting": "esg_impact_score (descending)",
                    "carbon_adjusted_rate": "base_rate - (esg_score * 0.15)",
                    "effective_rate": "includes origination fees",
                    "risk_penalties": "collateral (+0.5), personal guarantee (+0.3), prepayment penalty (+0.2)",
                    "esg_impact_score": "esg_score + (carbon_footprint_reduction / 10)"
                },
                "message": f"✅ Successfully evaluated {len(evaluated_offers)} offers based on comprehensive financial and ESG criteria from structured bank offers. Offers are now ready for selection."
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to evaluate offers: {str(e)}"
            }

    def select_best_offer(
        self,
        evaluated_offers_data: str = "",
        tool_context: ToolContext = None
    ) -> Dict[str, Any]:
        """Select the best offer based on evaluation criteria."""
        try:
            # Use stored evaluated offers if available, otherwise parse input
            if hasattr(self, 'evaluated_offers') and self.evaluated_offers:
                evaluated_offers = self.evaluated_offers
            else:
                # Parse evaluated offers data
                if isinstance(evaluated_offers_data, str) and evaluated_offers_data.strip():
                    try:
                        evaluated_offers = json.loads(evaluated_offers_data)
                    except json.JSONDecodeError:
                        evaluated_offers = self.received_offers
                else:
                    evaluated_offers = evaluated_offers_data or self.received_offers
            
            if not evaluated_offers or not isinstance(evaluated_offers, list):
                return {
                    "status": "error",
                    "error": "No offers available for selection. Please evaluate offers first."
                }
            
            # Select the best offer (first in sorted list by carbon-adjusted rate)
            best_offer = evaluated_offers[0]
            
            # Generate comprehensive selection reasoning based on structured offer data
            bank_name = best_offer.get('bank_name', 'Unknown Bank')
            composite_score = best_offer.get('composite_score', 'N/A')
            esg_impact_score = best_offer.get('esg_impact_score', 'N/A')
            approved_amount = best_offer.get('approved_amount', 0)
            interest_rate = best_offer.get('interest_rate', 'N/A')
            effective_rate = best_offer.get('effective_rate', 'N/A')
            monthly_payment = best_offer.get('monthly_payment', 0)
            total_cost_of_borrowing = best_offer.get('total_cost_of_borrowing', 0)
            origination_fee = best_offer.get('origination_fee', 0)
            collateral_required = best_offer.get('collateral_required', False)
            personal_guarantee_required = best_offer.get('personal_guarantee_required', False)
            prepayment_penalty = best_offer.get('prepayment_penalty', False)
            
            reasoning_parts = []
            reasoning_parts.append(f"🏆 **SELECTED OFFER: {bank_name.upper()}**")
            reasoning_parts.append(f"💰 Approved Amount: ${approved_amount:,.0f}")
            reasoning_parts.append(f"📈 Base Interest Rate: {interest_rate}%")
            reasoning_parts.append(f"💳 Effective Rate (with fees): {effective_rate}%")
            reasoning_parts.append(f"📅 Monthly Payment: ${monthly_payment:,.2f}")
            reasoning_parts.append(f"💸 Total Cost of Borrowing: ${total_cost_of_borrowing:,.2f}")
            reasoning_parts.append(f"🏦 Origination Fee: ${origination_fee:,.0f}")
            reasoning_parts.append(f"⚡ Composite Score: {composite_score} (lower is better)")
            reasoning_parts.append(f"🌱 ESG Impact Score: {esg_impact_score}/10")
            
            # Add risk factors
            risk_factors = []
            if collateral_required:
                risk_factors.append("Collateral Required")
            if personal_guarantee_required:
                risk_factors.append("Personal Guarantee Required")
            if prepayment_penalty:
                risk_factors.append("Prepayment Penalty")
            if not risk_factors:
                risk_factors.append("No additional risk factors")
            reasoning_parts.append(f"⚠️ Risk Factors: {', '.join(risk_factors)}")
            
            # Add comparison with other offers
            if len(evaluated_offers) > 1:
                other_offers = evaluated_offers[1:]
                reasoning_parts.append(f"\n📊 **COMPARISON WITH OTHER OFFERS:**")
                for i, offer in enumerate(other_offers[:2], 1):  # Show top 2 alternatives
                    other_bank = offer.get('bank_name', f'Bank {i}')
                    other_composite = offer.get('composite_score', 'N/A')
                    other_effective = offer.get('effective_rate', 'N/A')
                    other_amount = offer.get('approved_amount', 0)
                    reasoning_parts.append(f"   • {other_bank}: ${other_amount:,.0f} at {other_effective}% effective rate (composite score: {other_composite})")
            
            # Add ESG summary if available
            if best_offer.get("esg_impact", {}).get("esg_summary"):
                reasoning_parts.append(f"\n🌍 **ESG SUMMARY:** {best_offer['esg_impact']['esg_summary']}")
            
            # Add repayment schedule if available
            repayment_schedule = best_offer.get("repayment_schedule", {})
            if repayment_schedule:
                schedule_type = repayment_schedule.get("type", "monthly")
                amount_per_period = repayment_schedule.get("amount_per_period", monthly_payment)
                number_of_periods = repayment_schedule.get("number_of_periods", best_offer.get("term_months", 0))
                reasoning_parts.append(f"\n📋 **REPAYMENT SCHEDULE:** {schedule_type.title()} payments of ${amount_per_period:,.2f} for {number_of_periods} periods")
            
            # Add final recommendation
            reasoning_parts.append(f"\n✅ **RECOMMENDATION:** Accept the {bank_name} offer for the best combination of financial terms, ESG impact, and risk profile based on comprehensive evaluation of structured offer data.")
            
            return {
                "status": "success",
                "best_offer": best_offer,
                "reasoning": reasoning_parts,
                "selection_summary": {
                    "selected_bank": bank_name,
                    "approved_amount": approved_amount,
                    "base_interest_rate": interest_rate,
                    "effective_rate": effective_rate,
                    "composite_score": composite_score,
                    "esg_impact_score": esg_impact_score,
                    "monthly_payment": monthly_payment,
                    "total_cost_of_borrowing": total_cost_of_borrowing,
                    "risk_factors": risk_factors,
                    "total_offers_considered": len(evaluated_offers)
                },
                "message": f"🎯 **BEST OFFER SELECTED: {bank_name.upper()}** - ${approved_amount:,.0f} at {effective_rate}% effective rate with composite score {composite_score} and ESG impact score {esg_impact_score}/10"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to select best offer: {str(e)}"
            }

    def handle_bank_questions(
        self,
        bank_questions_data: str,
        tool_context: ToolContext = None
    ) -> Dict[str, Any]:
        """Handle questions from banks and ask user for more information."""
        try:
            # Parse bank questions data
            if isinstance(bank_questions_data, str):
                bank_questions = json.loads(bank_questions_data)
            else:
                bank_questions = bank_questions_data
            
            if not isinstance(bank_questions, list):
                return {
                    "status": "error",
                    "error": "Invalid bank questions format"
                }
            
            # Compile all questions from banks
            questions_summary = []
            for question in bank_questions:
                bank_name = question.get("bank", "Unknown Bank")
                question_text = question.get("question", "")
                questions_summary.append(f"🏦 {bank_name.upper()}: {question_text}")
            
            # Create comprehensive response for user
            user_message = "The banks have requested additional information to process your loan application:\n\n"
            user_message += "\n".join(questions_summary)
            user_message += "\n\nPlease provide the requested information so I can send it to the banks and get you proper loan offers."
            
            return {
                "status": "success",
                "bank_questions_count": len(bank_questions),
                "questions_summary": questions_summary,
                "user_message": user_message,
                "message": f"Received {len(bank_questions)} questions from banks. Please provide the requested information."
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to handle bank questions: {str(e)}"
            }

    def negotiate_offer(
        self,
        offer_id: str,
        negotiation_terms: str,
        tool_context: ToolContext = None
    ) -> Dict[str, Any]:
        """Send counter-offer for negotiation."""
        try:
            # Find the offer to negotiate
            target_offer = None
            for offer in self.received_offers:
                if offer.get("offer_id") == offer_id:
                    target_offer = offer
                    break
            
            if not target_offer:
                return {
                    "status": "error",
                    "error": f"Offer {offer_id} not found"
                }
            
            # Create negotiation request
            negotiation_request = {
                "offer_id": offer_id,
                "bank_name": target_offer.get("bank_name"),
                "negotiation_terms": negotiation_terms,
                "original_offer": target_offer,
                "negotiation_timestamp": datetime.utcnow().isoformat()
            }
            
            # Send negotiation request to broker for routing to specific bank
            async def _send_negotiation():
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.broker_endpoint}",
                        json={
                            "jsonrpc": "2.0",
                            "id": f"negotiation-{uuid.uuid4().hex[:8]}",
                            "method": "message/send",
                            "params": {
                                "message": {
                                    "id": f"negotiation-{uuid.uuid4().hex[:8]}",
                                    "parts": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(negotiation_request)
                                        }
                                    ]
                                }
                            }
                        },
                        timeout=60.0
                    )
                    return response
            
            # Run async function in sync context
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _send_negotiation())
                    response = future.result()
            except RuntimeError:
                response = asyncio.run(_send_negotiation())
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "negotiation_sent": True,
                    "offer_id": offer_id,
                    "bank_name": target_offer.get("bank_name"),
                    "negotiation_terms": negotiation_terms,
                    "message": f"Sent negotiation request to {target_offer.get('bank_name')} via broker"
                }
            else:
                return {
                    "status": "error",
                    "error": f"Negotiation request failed: HTTP {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to send negotiation request: {str(e)}"
            }

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        """Stream agent responses"""
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(
            role='user', parts=[types.Part.from_text(text=query)]
        )
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ''
                if (
                    event.content
                    and event.content.parts
                    and event.content.parts[0].text
                ):
                    response = event.content.parts[0].text
                yield {
                    'content': response,
                    'is_task_complete': True,
                    'require_user_input': False,
                }
            elif event.content and event.content.parts:
                response = ''
                if event.content.parts[0].text:
                    response = event.content.parts[0].text
                yield {
                    'content': response,
                    'is_task_complete': False,
                    'require_user_input': False,
                }
root_agent = CompanyAgent()._agent