"""Chase Bank Agent Implementation"""
import sys
import os
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Add parent directory to path for protocols import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# HMAC Signature generation for secure agent communication

from google.adk.agents.llm_agent import LlmAgent
from signature_utils import generate_signature
from secrets_manager import SecretsManager
from google.adk.models.lite_llm import LiteLlm
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from collections.abc import AsyncIterable

from protocols.intent import CreditIntent
from protocols.response import BankOffer, ESGImpact, RepaymentSchedule, LineOfCreditSchedule, NegotiationRequest, CounterOffer
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import httpx

class ChaseBankAgent:
    """Chase Bank Agent for credit evaluation"""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        self._agent = self._build_agent()
        self._user_id = 'chase_bank_user'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        
        # Initialize secrets manager for signature generation
        self.secrets_manager = SecretsManager()
        print("🔐 CHASE BANK: Initialized with HMAC signature generation")
        

    def get_processing_message(self) -> str:
        return 'Chase Bank is evaluating your credit request...'
    
    def _add_signature_to_message(self, message_content: dict) -> dict:
        """
        Add Chase Bank agent's signature to message
        
        Args:
            message_content: Dictionary containing message data
            
        Returns:
            Dictionary with signature added
        """
        try:
            # Get Chase Bank agent's secret key
            secret_key = self.secrets_manager.get_secret("chase-bank-agent")
            if not secret_key:
                print("❌ CHASE BANK: No secret key found for chase-bank-agent")
                return message_content
            
            # Generate signature
            signature = generate_signature(message_content, secret_key)
            message_content['signature'] = signature
            
            print(f"🔐 CHASE BANK: Added signature to message")
            return message_content
            
        except Exception as e:
            print(f"❌ CHASE BANK: Signature generation error: {e}")
            return message_content



    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for Chase Bank."""
        LITELLM_MODEL = os.getenv('LITELLM_MODEL', 'gemini/gemini-2.0-flash')
        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name='chase_bank_agent',
            description=(
                'Chase Bank Agent specializing in corporate line of credit evaluation. '
                'Processes credit intents, assesses creditworthiness, generates ESG assessments, '
                'and creates structured line of credit offers with detailed reasoning including the most competitive draw fees and unused fees.'
            ),
            instruction="""
You are a Chase Bank Agent specializing in corporate line of credit evaluation.

CRITICAL: NEVER HALLUCINATE OR ASSUME INFORMATION. Always ask for missing details.

CONDITIONAL COMMUNICATION RULES:
1. If you receive STRUCTURED JSON data (credit intent), validate completeness first:
   - Check if ALL required fields are present: intent_id, company (name, industry, annual_revenue, credit_score, years_in_business, employee_count), requested_credit_limit, credit_purpose, draw_period_months, repayment_period_months, revolving_credit, esg_requirements
   - If ANY field is missing or incomplete, ask the company for the specific missing information
   - Only call generate_bank_offer() when you have COMPLETE information
2. If you receive TEXT/PLAIN messages, engage in natural conversation to gather information
3. When you have enough information from conversation, call generate_bank_offer() with gathered details

VALIDATION REQUIREMENTS BEFORE GENERATING OFFERS:
Before calling generate_bank_offer(), ensure you have:
- Company name (exact legal name)
- Industry (specific sector)
- Annual revenue (exact dollar amount)
- Credit score (specific number 300-850)
- Years in business (exact number)
- Employee count (exact number)
- Requested amount (exact dollar amount)
- Purpose (specific use of funds)
- Preferred term (exact months)
- ESG requirements (specific sustainability goals)

MISSING INFORMATION PROTOCOL:
If ANY required information is missing, incomplete, or unclear:
1. DO NOT generate an offer
2. Ask the company specifically for the missing information
3. Be precise about what you need (e.g., "Please provide the exact annual revenue amount")
4. Wait for complete information before proceeding

CRITICAL RESPONSE REQUIREMENT:
- When you call generate_bank_offer(), you MUST return the complete structured offer data
- Include the full offer object with all fields: offer_id, bank_name, approved_credit_limit, interest_rate, draw_fee_percentage, unused_credit_fee, line_of_credit_schedule, esg_impact, additional_conditions, reasoning, origination_fee, prepayment_penalty, collateral_required, personal_guarantee_required, created_at
- Do NOT just describe the offer - return the actual structured data

DO NOT: Just describe the offer or say you generated it
DO: Actually call the generate_bank_offer() function with the JSON data AND return the complete structured offer

CREDIT POLICIES:
- Minimum credit score: 680
- Maximum debt-to-income ratio: 0.35
- Preferred industries: Technology, Healthcare, Finance, Real Estate
- ESG bonus: +0.30% rate reduction for ESG score > 8.5
- Aggressive approach with competitive rates for qualified borrowers

ESG ASSESSMENT:
- Use LLM to generate human-readable ESG summary
- Calculate carbon footprint reduction potential
- Assess overall ESG score (0-10 scale)
- Consider company's sustainability initiatives

CONSERVATIVE APPROACH:
- Always err on the side of asking for more information
- Never assume or estimate missing data
- Be thorough in validation before making offers
- Maintain Chase Bank's reputation for competitive evaluation

Always be helpful and professional in conversations, but ensure you eventually call generate_bank_offer() when you have sufficient information.
            """,
            tools=[
                self.generate_bank_offer,
                self.assess_creditworthiness,
                self.generate_esg_assessment,
            ],
        )

    def generate_bank_offer(
        self,
        credit_intent_data: str,
        tool_context: ToolContext = None
    ) -> Dict[str, Any]:
        """Generate structured line of credit offer."""
        try:
            # Parse credit intent data
            if isinstance(credit_intent_data, str):
                intent_dict = json.loads(credit_intent_data)
            else:
                intent_dict = credit_intent_data
            
            # Extract company information
            company_info = intent_dict.get("company", {})
            requested_credit_limit = intent_dict.get("requested_credit_limit", 0)
            credit_purpose = intent_dict.get("credit_purpose", "")
            draw_period_months = intent_dict.get("draw_period_months", 12)
            repayment_period_months = intent_dict.get("repayment_period_months", 24)
            revolving_credit = intent_dict.get("revolving_credit", True)
            
            # Assess creditworthiness
            credit_assessment = self.assess_creditworthiness(company_info)
            
            # Generate ESG assessment
            esg_assessment = self.generate_esg_assessment(company_info, intent_dict)
            
            # Determine offer terms based on Chase Bank policies
            credit_score = company_info.get("credit_score", 0)
            annual_revenue = company_info.get("annual_revenue", 0)
            industry = company_info.get("industry", "")
            
            # Base interest rate calculation (Chase Bank competitive rates)
            base_rate = 6.0  # Base rate for Chase Bank
            
            # Credit score adjustments
            if credit_score >= 750:
                rate_adjustment = -1.2
            elif credit_score >= 700:
                rate_adjustment = -0.7
            elif credit_score >= 680:
                rate_adjustment = -0.2
            else:
                rate_adjustment = 1.2
            
            # Industry adjustments (Chase Bank preferred industries)
            if industry.lower() in ["technology", "healthcare", "finance", "real estate"]:
                industry_adjustment = -0.35
            else:
                industry_adjustment = 0.0
            
            # ESG bonus (Chase Bank aggressive ESG incentives)
            esg_score = esg_assessment.get("overall_esg_score", 0)
            if esg_score > 8.5:
                esg_adjustment = -0.30
            elif esg_score > 7.0:
                esg_adjustment = -0.15
            else:
                esg_adjustment = 0.0
            
            # Calculate final interest rate
            final_rate = base_rate + rate_adjustment + industry_adjustment + esg_adjustment
            final_rate = max(final_rate, 2.5)  # Minimum rate (Chase Bank competitive)
            
            # Determine approved credit limit (Chase Bank aggressive approach)
            if credit_score >= 750 and annual_revenue >= requested_credit_limit * 1.8:
                approved_credit_limit = requested_credit_limit * 1.0  # 100% of requested
            elif credit_score >= 700 and annual_revenue >= requested_credit_limit * 1.5:
                approved_credit_limit = requested_credit_limit * 0.95  # 95% of requested
            elif credit_score >= 680 and annual_revenue >= requested_credit_limit * 1.2:
                approved_credit_limit = requested_credit_limit * 0.90  # 90% of requested
            else:
                approved_credit_limit = requested_credit_limit * 0.80  # 80% of requested
            
            # Create line of credit schedule
            line_of_credit_schedule = LineOfCreditSchedule(
                draw_period_months=draw_period_months,
                repayment_period_months=repayment_period_months,
                minimum_interest_payment=approved_credit_limit * 0.009,  # 0.9% of credit limit minimum
                draw_availability_schedule="anytime",
                credit_review_frequency="semi_annually"
            )
            
            # Create ESG impact
            esg_impact = ESGImpact(
                overall_esg_score=esg_score,
                esg_summary=esg_assessment.get("esg_summary", "Standard ESG assessment"),
                carbon_footprint_reduction=esg_assessment.get("carbon_footprint_reduction", 0)
            )
            
            # Create bank offer
            bank_offer = BankOffer(
                intent_id=intent_dict.get("intent_id", "unknown"),
                bank_name="Chase Bank",
                bank_id="CHASE001",
                approved_credit_limit=approved_credit_limit,
                interest_rate=round(final_rate, 2),
                draw_fee_percentage=0.35,  # 0.35% fee on each draw (lowest among banks)
                unused_credit_fee=0.15,  # 0.15% annual fee on unused portion (lowest among banks)
                line_of_credit_schedule=line_of_credit_schedule,
                esg_impact=esg_impact,
                additional_conditions="Standard Chase Bank terms apply. Flexible repayment options available for qualified borrowers.",
                reasoning=f"Approved line of credit based on credit score {credit_score}, annual revenue ${annual_revenue:,.0f}, and ESG score {esg_score}/10. Chase Bank's competitive approach offers attractive terms for qualified borrowers with flexible working capital access.",
                origination_fee=approved_credit_limit * 0.004,  # 0.4% origination fee
                prepayment_penalty=False,
                collateral_required=approved_credit_limit > 1500000,
                personal_guarantee_required=approved_credit_limit > 750000
            )
            
            # Return offer with HMAC signature
            offer_dict = bank_offer.model_dump(mode='json')
            
            # Add signature to the offer
            offer_dict = self._add_signature_to_message(offer_dict)
            
            return {
                "status": "success",
                "offer": offer_dict,
                "message": f"Chase Bank offer generated: ${approved_credit_limit:,.0f} at {final_rate}% APR for {draw_period_months} months draw period"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to generate Chase Bank offer: {str(e)}"
            }

    def assess_creditworthiness(
        self,
        company_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess company creditworthiness using Chase Bank policies."""
        try:
            credit_score = company_info.get("credit_score", 0)
            annual_revenue = company_info.get("annual_revenue", 0)
            years_in_business = company_info.get("years_in_business", 0)
            industry = company_info.get("industry", "")
            
            # Chase Bank credit assessment criteria
            assessment = {
                "credit_score": credit_score,
                "annual_revenue": annual_revenue,
                "years_in_business": years_in_business,
                "industry": industry,
                "assessment_timestamp": datetime.utcnow().isoformat()
            }
            
            # Credit score evaluation
            if credit_score >= 750:
                assessment["credit_score_rating"] = "Excellent"
                assessment["credit_score_risk"] = "Very Low"
            elif credit_score >= 700:
                assessment["credit_score_rating"] = "Good"
                assessment["credit_score_risk"] = "Low"
            elif credit_score >= 680:
                assessment["credit_score_rating"] = "Fair"
                assessment["credit_score_risk"] = "Low-Medium"
            else:
                assessment["credit_score_rating"] = "Poor"
                assessment["credit_score_risk"] = "High"
            
            # Revenue evaluation
            if annual_revenue >= 15000000:
                assessment["revenue_rating"] = "Excellent"
            elif annual_revenue >= 8000000:
                assessment["revenue_rating"] = "Good"
            elif annual_revenue >= 2000000:
                assessment["revenue_rating"] = "Fair"
            else:
                assessment["revenue_rating"] = "Poor"
            
            # Business maturity evaluation
            if years_in_business >= 8:
                assessment["maturity_rating"] = "Excellent"
            elif years_in_business >= 4:
                assessment["maturity_rating"] = "Good"
            elif years_in_business >= 2:
                assessment["maturity_rating"] = "Fair"
            else:
                assessment["maturity_rating"] = "Poor"
            
            # Industry evaluation (Chase Bank preferred industries)
            preferred_industries = ["technology", "healthcare", "finance", "real estate", "manufacturing"]
            if industry.lower() in preferred_industries:
                assessment["industry_rating"] = "Preferred"
            else:
                assessment["industry_rating"] = "Standard"
            
            # Overall assessment (Chase Bank aggressive approach)
            if (assessment["credit_score_rating"] in ["Excellent", "Good"] and 
                assessment["revenue_rating"] in ["Excellent", "Good"] and
                assessment["maturity_rating"] in ["Excellent", "Good"]):
                assessment["overall_rating"] = "Approved"
                assessment["overall_risk"] = "Very Low"
            elif (assessment["credit_score_rating"] in ["Excellent", "Good", "Fair"] and
                  assessment["revenue_rating"] in ["Excellent", "Good", "Fair"]):
                assessment["overall_rating"] = "Approved with Conditions"
                assessment["overall_risk"] = "Low-Medium"
            else:
                assessment["overall_rating"] = "Declined"
                assessment["overall_risk"] = "High"
            
            return assessment
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to assess creditworthiness: {str(e)}"
            }

    def generate_esg_assessment(
        self,
        company_info: Dict[str, Any],
        credit_intent: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate ESG impact assessment using LLM."""
        try:
            company_name = company_info.get("name", "Unknown Company")
            industry = company_info.get("industry", "Unknown Industry")
            esg_requirements = credit_intent.get("esg_requirements", "")
            
            # Generate ESG assessment based on company information
            # In a real implementation, this would use the LLM to generate the assessment
            
            # Base ESG score calculation (Chase Bank higher baseline)
            base_score = 6.5
            
            # Industry ESG adjustments (Chase Bank ESG focus)
            if industry.lower() in ["technology", "renewable energy", "healthcare", "finance"]:
                industry_esg_bonus = 2.0
            elif industry.lower() in ["manufacturing", "education", "real estate"]:
                industry_esg_bonus = 1.0
            else:
                industry_esg_bonus = 0.0
            
            # ESG requirements bonus (Chase Bank aggressive ESG incentives)
            if "sustainability" in esg_requirements.lower():
                requirements_bonus = 1.5
            elif "environment" in esg_requirements.lower():
                requirements_bonus = 1.0
            elif "carbon" in esg_requirements.lower():
                requirements_bonus = 0.8
            else:
                requirements_bonus = 0.0
            
            # Calculate final ESG score
            final_esg_score = min(base_score + industry_esg_bonus + requirements_bonus, 10.0)
            
            # Generate ESG summary (Chase Bank style)
            if final_esg_score >= 8.5:
                esg_summary = f"{company_name} demonstrates exceptional ESG leadership with innovative sustainable practices in the {industry} sector. Chase Bank recognizes this company as a sustainability champion with significant positive impact potential."
            elif final_esg_score >= 7.0:
                esg_summary = f"{company_name} shows strong ESG commitment in the {industry} sector with excellent sustainability initiatives and environmental responsibility practices."
            elif final_esg_score >= 6.0:
                esg_summary = f"{company_name} demonstrates good ESG practices in the {industry} sector with solid foundation for enhanced sustainability programs."
            else:
                esg_summary = f"{company_name} has developing ESG practices in the {industry} sector with opportunities for significant sustainability improvements."
            
            # Calculate carbon footprint reduction (Chase Bank higher potential)
            carbon_reduction = min(final_esg_score * 3.0, 30.0)  # Up to 30% reduction
            
            return {
                "overall_esg_score": round(final_esg_score, 1),
                "esg_summary": esg_summary,
                "carbon_footprint_reduction": round(carbon_reduction, 1),
                "industry_esg_bonus": industry_esg_bonus,
                "requirements_bonus": requirements_bonus,
                "assessment_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "overall_esg_score": 5.5,
                "esg_summary": f"Standard ESG assessment for {company_info.get('name', 'Unknown Company')}",
                "carbon_footprint_reduction": 12.0,
                "error": f"ESG assessment error: {str(e)}"
            }

    def process_negotiation_request(self, negotiation_data: str) -> Dict[str, Any]:
        """Process negotiation request and generate counter-offer"""
        try:
            # Parse negotiation request
            if isinstance(negotiation_data, str):
                negotiation_request = json.loads(negotiation_data)
            else:
                negotiation_request = negotiation_data
            
            original_offer_id = negotiation_request.get("original_offer_id")
            bank_name = negotiation_request.get("bank_name", "Chase Bank")
            company_name = negotiation_request.get("company_name", "Unknown Company")
            negotiation_terms = negotiation_request.get("negotiation_terms", {})
            original_offer = negotiation_request.get("original_offer")
            
            # Chase Bank negotiation policy: Competitive but structured for line of credit
            # - Max 0.6% interest rate reduction
            # - Moderate credit limit flexibility (±12%)
            # - Competitive origination fee reduction (max 35%)
            # - Draw fee reduction (max 0.12%)
            # - Unused fee reduction (max 0.06%)
            
            requested_rate = negotiation_terms.get("requested_interest_rate", 0)
            requested_credit_limit = negotiation_terms.get("requested_credit_limit", 0)
            requested_draw_period = negotiation_terms.get("requested_draw_period_months", 0)
            requested_repayment_period = negotiation_terms.get("requested_repayment_period_months", 0)
            requested_draw_fee = negotiation_terms.get("requested_draw_fee_percentage", 0)
            requested_unused_fee = negotiation_terms.get("requested_unused_credit_fee", 0)
            requested_origination_fee = negotiation_terms.get("requested_origination_fee", 0)
            
            # Generate counter-offer based on Chase policy
            counter_offer_data = self.generate_counter_offer(
                original_offer_id=original_offer_id,
                bank_name=bank_name,
                company_name=company_name,
                requested_rate=requested_rate,
                requested_draw_period=requested_draw_period,
                requested_repayment_period=requested_repayment_period,
                requested_credit_limit=requested_credit_limit,
                requested_origination_fee=requested_origination_fee,
                original_offer=original_offer
            )
            
            return {
                "status": "success",
                "negotiation_response": counter_offer_data
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to process negotiation request: {str(e)}"
            }

    def generate_counter_offer(
        self,
        original_offer_id: str,
        bank_name: str,
        company_name: str,
        requested_rate: float,
        requested_draw_period: int,
        requested_repayment_period: int,
        requested_credit_limit: float,
        requested_origination_fee: float,
        original_offer: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate Chase Bank counter-offer based on negotiation policy"""
        
        # Chase Bank negotiation policy implementation
        # Competitive approach with structured flexibility
        
        # Use actual original offer details if provided, otherwise use defaults
        if original_offer:
            original_rate = original_offer.get("interest_rate", 6.0)
            original_draw_period = original_offer.get("draw_period_months", 12)
            original_repayment_period = original_offer.get("repayment_period_months", 24)
            original_amount = original_offer.get("approved_credit_limit", 1000000)
            original_fee = original_offer.get("origination_fee", 4000)
        else:
            # Fallback to defaults if original offer not provided
            original_rate = 6.0
            original_draw_period = 12
            original_repayment_period = 24
            original_amount = 1000000
            original_fee = 4000
        
        # Interest rate: Max 0.6% reduction from original
        max_rate_reduction = 0.6
        counter_rate = max(requested_rate, original_rate - max_rate_reduction)
        
        # Draw Period: Moderate flexibility ±9 months from original
        if requested_draw_period > 0:
            counter_draw_period = max(6, min(21, requested_draw_period))  # Between 6-21 months
        else:
            counter_draw_period = original_draw_period
        
        # Repayment Period: Structured adjustment
        if requested_repayment_period > 0:
            counter_repayment_period = max(12, min(36, requested_repayment_period))  # Between 12-36 months
        else:
            counter_repayment_period = original_repayment_period
        
        # Amount: Business potential-based adjustment
        if requested_credit_limit > 0:
            # Chase allows up to 25% increase for high-potential businesses
            max_amount_increase = original_amount * 0.25
            counter_amount = min(requested_credit_limit, original_amount + max_amount_increase)
        else:
            counter_amount = original_amount
        
        # Origination fee: Competitive reduction
        max_fee_reduction = original_fee * 0.35
        counter_fee = max(requested_origination_fee, original_fee - max_fee_reduction)
        
        # Create counter-offer
        counter_offer = BankOffer(
            offer_id=f"CHASE_COUNTER_{uuid.uuid4().hex[:8]}",
            intent_id=original_offer_id,
            bank_name=bank_name,
            bank_id="chase-bank-001",
            approved_credit_limit=counter_amount,
            interest_rate=counter_rate,
            draw_fee_percentage=0.30,  # Reduced from original
            unused_credit_fee=0.12,  # Reduced from original
            line_of_credit_schedule=LineOfCreditSchedule(
                draw_period_months=counter_draw_period,
                repayment_period_months=counter_repayment_period,
                minimum_interest_payment=counter_amount * 0.009,  # 0.9% of credit limit
                draw_availability_schedule="anytime",
                credit_review_frequency="semi_annually"
            ),
            esg_impact=ESGImpact(
                overall_esg_score=8.2,
                esg_summary="Chase Bank focuses on sustainable growth with strong environmental and social impact initiatives",
                carbon_footprint_reduction=18.0
            ),
            additional_conditions="Standard Chase Bank line of credit terms with competitive benefits",
            reasoning=f"Counter-offer based on Chase Bank's competitive negotiation policy. Interest rate reduced by {original_rate - counter_rate:.2f}%, credit limit adjusted to ${counter_amount:,.0f}, origination fee reduced by ${original_fee - counter_fee:.0f}",
            origination_fee=counter_fee,
            prepayment_penalty=False,
            collateral_required=False,
            personal_guarantee_required=True
        )
        
        # Create counter-offer response
        counter_offer_response = CounterOffer(
            original_offer_id=original_offer_id,
            bank_name=bank_name,
            company_name=company_name,
            counter_offer=counter_offer,
            negotiation_reasoning=f"Chase Bank's counter-offer reflects our competitive approach to business lending. We've reduced the interest rate by {original_rate - counter_rate:.2f}%, adjusted the credit limit to ${counter_amount:,.0f}, and reduced the origination fee by ${original_fee - counter_fee:.0f}. This offer balances competitive terms with prudent risk management."
        )
        
        return counter_offer_response.model_dump(mode='json')

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        """Stream agent responses"""
        
        # Check if this is a negotiation message and handle it directly
        try:
            import json
            message_data = json.loads(query)
            
            if message_data.get("action") == "negotiate_offer":
                print(f"🔄 CHASE BANK: Received negotiation request")
                print(f"   📋 Original Offer ID: {message_data.get('original_offer_id')}")
                print(f"   🏢 Company: {message_data.get('company_name')}")
                print(f"   📄 Negotiation Terms: {message_data.get('negotiation_terms')}")
                
                # Handle negotiation request directly
                result = self.process_negotiation_request(query)
                
                if result["status"] == "success":
                    negotiation_response = result["negotiation_response"]
                    print(f"   ✅ CHASE BANK: Generated counter-offer successfully")
                    print(f"      💰 Credit Limit: ${negotiation_response['counter_offer']['approved_credit_limit']:,.0f}")
                    print(f"      📈 Interest Rate: {negotiation_response['counter_offer']['interest_rate']}%")
                    print(f"      📅 Draw Period: {negotiation_response['counter_offer']['line_of_credit_schedule']['draw_period_months']} months")
                    print(f"      🏦 Counter-Offer ID: {negotiation_response['counter_offer']['offer_id']}")
                    
                    # Add signature to the negotiation response
                    negotiation_response = self._add_signature_to_message(negotiation_response)
                    
                    yield {
                        'content': json.dumps(negotiation_response, indent=2),
                        'is_task_complete': True,
                        'require_user_input': False,
                    }
                    return
                else:
                    yield {
                        'content': f"Negotiation processing failed: {result['error']}",
                        'is_task_complete': True,
                        'require_user_input': False,
                    }
                    return
        except (json.JSONDecodeError, AttributeError):
            # Not a negotiation message, continue with normal processing
            pass
        
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
