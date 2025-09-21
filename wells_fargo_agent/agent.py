"""Wells Fargo Bank Agent Implementation"""
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

class WellsFargoAgent:
    """Wells Fargo Bank Agent for credit evaluation"""

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self):
        self._agent = self._build_agent()
        self._user_id = 'wells_fargo_user'
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        
        # Initialize secrets manager for signature generation
        self.secrets_manager = SecretsManager()
        print("🔐 WELLS FARGO: Initialized with HMAC signature generation")
        

    def get_processing_message(self) -> str:
        return 'Wells Fargo is evaluating your credit request...'
    
    def _add_signature_to_message(self, message_content: dict) -> dict:
        """
        Add Wells Fargo agent's signature to message
        
        Args:
            message_content: Dictionary containing message data
            
        Returns:
            Dictionary with signature added
        """
        try:
            # Get Wells Fargo agent's secret key
            secret_key = self.secrets_manager.get_secret("wells-fargo-agent")
            if not secret_key:
                print("❌ WELLS FARGO: No secret key found for wells-fargo-agent")
                return message_content
            
            # Generate signature
            signature = generate_signature(message_content, secret_key)
            message_content['signature'] = signature
            
            print(f"🔐 WELLS FARGO: Added signature to message")
            return message_content
            
        except Exception as e:
            print(f"❌ WELLS FARGO: Signature generation error: {e}")
            return message_content



    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for Wells Fargo."""
        LITELLM_MODEL = os.getenv('LITELLM_MODEL', 'gemini/gemini-2.0-flash')
        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name='wells_fargo_agent',
            description=(
                'Wells Fargo Bank Agent specializing in corporate line of credit evaluation. '
                'Processes credit intents, assesses creditworthiness, generates ESG assessments, '
                'and creates structured line of credit offers with detailed reasoning including draw fees and unused fees.'
            ),
            instruction="""
You are a Wells Fargo Bank Agent specializing in corporate line of credit evaluation.

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
- Requested credit limit (exact dollar amount)
- Credit purpose (specific use of line of credit)
- Draw period (exact months for drawing funds)
- Repayment period (exact months for repayment)
- Revolving credit (true/false)
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
- Minimum credit score: 650
- Maximum debt-to-income ratio: 0.4
- Preferred industries: Technology, Healthcare, Manufacturing
- ESG bonus: +0.25% rate reduction for ESG score > 8.0
- Conservative approach with strong emphasis on creditworthiness

ESG ASSESSMENT:
- Use LLM to generate human-readable ESG summary
- Calculate carbon footprint reduction potential
- Assess overall ESG score (0-10 scale)
- Consider company's sustainability initiatives

CONSERVATIVE APPROACH:
- Always err on the side of asking for more information
- Never assume or estimate missing data
- Be thorough in validation before making offers
- Maintain Wells Fargo's reputation for careful evaluation

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
            
            # Determine offer terms based on Wells Fargo policies
            credit_score = company_info.get("credit_score", 0)
            annual_revenue = company_info.get("annual_revenue", 0)
            industry = company_info.get("industry", "")
            
            # Base interest rate calculation
            base_rate = 6.5  # Base rate for Wells Fargo
            
            # Credit score adjustments
            if credit_score >= 750:
                rate_adjustment = -1.0
            elif credit_score >= 700:
                rate_adjustment = -0.5
            elif credit_score >= 650:
                rate_adjustment = 0.0
            else:
                rate_adjustment = 1.0
            
            # Industry adjustments
            if industry.lower() in ["technology", "healthcare", "manufacturing"]:
                industry_adjustment = -0.25
            else:
                industry_adjustment = 0.0
            
            # ESG bonus
            esg_score = esg_assessment.get("overall_esg_score", 0)
            if esg_score > 8.0:
                esg_adjustment = -0.25
            else:
                esg_adjustment = 0.0
            
            # Calculate final interest rate
            final_rate = base_rate + rate_adjustment + industry_adjustment + esg_adjustment
            final_rate = max(final_rate, 3.0)  # Minimum rate
            
            # Determine approved credit limit (conservative approach for line of credit)
            if credit_score >= 700 and annual_revenue >= requested_credit_limit * 2:
                approved_credit_limit = requested_credit_limit * 0.95  # 95% of requested
            elif credit_score >= 650 and annual_revenue >= requested_credit_limit * 1.5:
                approved_credit_limit = requested_credit_limit * 0.85  # 85% of requested
            else:
                approved_credit_limit = requested_credit_limit * 0.75  # 75% of requested
            
            # Create line of credit schedule
            line_of_credit_schedule = LineOfCreditSchedule(
                draw_period_months=draw_period_months,
                repayment_period_months=repayment_period_months,
                minimum_interest_payment=approved_credit_limit * 0.01,  # 1% of credit limit minimum
                draw_availability_schedule="business_hours",
                credit_review_frequency="annually"
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
                bank_name="Wells Fargo",
                bank_id="WF001",
                approved_credit_limit=approved_credit_limit,
                interest_rate=round(final_rate, 2),
                draw_fee_percentage=0.5,  # 0.5% fee on each draw
                unused_credit_fee=0.25,  # 0.25% annual fee on unused portion
                line_of_credit_schedule=line_of_credit_schedule,
                esg_impact=esg_impact,
                additional_conditions="Standard Wells Fargo line of credit terms apply. Personal guarantee may be required for limits over $500,000.",
                reasoning=f"Approved line of credit based on credit score {credit_score}, annual revenue ${annual_revenue:,.0f}, and ESG score {esg_score}/10. Wells Fargo's conservative approach ensures sustainable lending with flexible working capital access.",
                origination_fee=approved_credit_limit * 0.005,  # 0.5% origination fee
                prepayment_penalty=False,
                collateral_required=approved_credit_limit > 1000000,
                personal_guarantee_required=approved_credit_limit > 500000
            )
            
            # Return offer with HMAC signature
            offer_dict = bank_offer.model_dump(mode='json')
            
            # Add signature to the offer
            offer_dict = self._add_signature_to_message(offer_dict)
            
            return {
                "status": "success",
                "offer": offer_dict,
                "message": f"Wells Fargo offer generated: ${approved_credit_limit:,.0f} at {final_rate}% APR for {draw_period_months} months draw period"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to generate Wells Fargo offer: {str(e)}"
            }

    def assess_creditworthiness(
        self,
        company_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess company creditworthiness using Wells Fargo policies."""
        try:
            credit_score = company_info.get("credit_score", 0)
            annual_revenue = company_info.get("annual_revenue", 0)
            years_in_business = company_info.get("years_in_business", 0)
            industry = company_info.get("industry", "")
            
            # Wells Fargo credit assessment criteria
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
                assessment["credit_score_risk"] = "Low"
            elif credit_score >= 700:
                assessment["credit_score_rating"] = "Good"
                assessment["credit_score_risk"] = "Low-Medium"
            elif credit_score >= 650:
                assessment["credit_score_rating"] = "Fair"
                assessment["credit_score_risk"] = "Medium"
            else:
                assessment["credit_score_rating"] = "Poor"
                assessment["credit_score_risk"] = "High"
            
            # Revenue evaluation
            if annual_revenue >= 10000000:
                assessment["revenue_rating"] = "Excellent"
            elif annual_revenue >= 5000000:
                assessment["revenue_rating"] = "Good"
            elif annual_revenue >= 1000000:
                assessment["revenue_rating"] = "Fair"
            else:
                assessment["revenue_rating"] = "Poor"
            
            # Business maturity evaluation
            if years_in_business >= 10:
                assessment["maturity_rating"] = "Excellent"
            elif years_in_business >= 5:
                assessment["maturity_rating"] = "Good"
            elif years_in_business >= 2:
                assessment["maturity_rating"] = "Fair"
            else:
                assessment["maturity_rating"] = "Poor"
            
            # Industry evaluation
            preferred_industries = ["technology", "healthcare", "manufacturing", "finance"]
            if industry.lower() in preferred_industries:
                assessment["industry_rating"] = "Preferred"
            else:
                assessment["industry_rating"] = "Standard"
            
            # Overall assessment
            if (assessment["credit_score_rating"] in ["Excellent", "Good"] and 
                assessment["revenue_rating"] in ["Excellent", "Good"] and
                assessment["maturity_rating"] in ["Excellent", "Good"]):
                assessment["overall_rating"] = "Approved"
                assessment["overall_risk"] = "Low"
            elif (assessment["credit_score_rating"] in ["Excellent", "Good", "Fair"] and
                  assessment["revenue_rating"] in ["Excellent", "Good", "Fair"]):
                assessment["overall_rating"] = "Approved with Conditions"
                assessment["overall_risk"] = "Medium"
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
            
            # Base ESG score calculation
            base_score = 6.0
            
            # Industry ESG adjustments
            if industry.lower() in ["technology", "renewable energy", "healthcare"]:
                industry_esg_bonus = 1.5
            elif industry.lower() in ["manufacturing", "finance", "education"]:
                industry_esg_bonus = 0.5
            else:
                industry_esg_bonus = 0.0
            
            # ESG requirements bonus
            if "sustainability" in esg_requirements.lower():
                requirements_bonus = 1.0
            elif "environment" in esg_requirements.lower():
                requirements_bonus = 0.5
            else:
                requirements_bonus = 0.0
            
            # Calculate final ESG score
            final_esg_score = min(base_score + industry_esg_bonus + requirements_bonus, 10.0)
            
            # Generate ESG summary
            if final_esg_score >= 8.0:
                esg_summary = f"{company_name} demonstrates strong ESG alignment with sustainable business practices in the {industry} sector. The company shows commitment to environmental responsibility and social impact."
            elif final_esg_score >= 6.0:
                esg_summary = f"{company_name} shows good ESG practices in the {industry} sector with room for improvement in sustainability initiatives."
            else:
                esg_summary = f"{company_name} has basic ESG practices in the {industry} sector and would benefit from enhanced sustainability programs."
            
            # Calculate carbon footprint reduction
            carbon_reduction = min(final_esg_score * 2.5, 25.0)  # Up to 25% reduction
            
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
                "overall_esg_score": 5.0,
                "esg_summary": f"Standard ESG assessment for {company_info.get('name', 'Unknown Company')}",
                "carbon_footprint_reduction": 10.0,
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
            bank_name = negotiation_request.get("bank_name", "Wells Fargo")
            company_name = negotiation_request.get("company_name", "Unknown Company")
            negotiation_terms = negotiation_request.get("negotiation_terms", {})
            original_offer = negotiation_request.get("original_offer")
            
            # Wells Fargo negotiation policy: Conservative but flexible for line of credit
            # - Max 0.5% interest rate reduction
            # - Flexible on credit limit (±10%)
            # - Moderate origination fee reduction (max 25%)
            # - Draw fee reduction (max 0.1%)
            # - Unused fee reduction (max 0.05%)
            
            requested_rate = negotiation_terms.get("requested_interest_rate", 0)
            requested_credit_limit = negotiation_terms.get("requested_credit_limit", 0)
            requested_draw_period = negotiation_terms.get("requested_draw_period_months", 0)
            requested_repayment_period = negotiation_terms.get("requested_repayment_period_months", 0)
            requested_draw_fee = negotiation_terms.get("requested_draw_fee_percentage", 0)
            requested_unused_fee = negotiation_terms.get("requested_unused_credit_fee", 0)
            requested_origination_fee = negotiation_terms.get("requested_origination_fee", 0)
            
            # Generate counter-offer based on Wells Fargo policy
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
        """Generate Wells Fargo counter-offer based on negotiation policy"""
        
        # Wells Fargo negotiation policy implementation
        # Conservative approach with moderate flexibility
        
        # Use actual original offer details if provided, otherwise use defaults
        if original_offer:
            original_rate = original_offer.get("interest_rate", 6.5)
            original_draw_period = original_offer.get("draw_period_months", 12)
            original_repayment_period = original_offer.get("repayment_period_months", 24)
            original_amount = original_offer.get("approved_credit_limit", 1000000)
            original_fee = original_offer.get("origination_fee", 5000)
        else:
            # Fallback to defaults if original offer not provided
            original_rate = 6.5
            original_draw_period = 12
            original_repayment_period = 24
            original_amount = 1000000
            original_fee = 5000
        
        # Interest rate: Max 0.5% reduction from original
        max_rate_reduction = 0.5
        counter_rate = max(requested_rate, original_rate - max_rate_reduction)
        
        # Draw Period: Flexible ±6 months from original
        if requested_draw_period > 0:
            counter_draw_period = max(6, min(18, requested_draw_period))  # Between 6-18 months
        else:
            counter_draw_period = original_draw_period
        
        # Repayment Period: Conservative adjustment
        if requested_repayment_period > 0:
            counter_repayment_period = max(12, min(30, requested_repayment_period))  # Between 12-30 months
        else:
            counter_repayment_period = original_repayment_period
        
        # Amount: Conservative adjustment
        if requested_credit_limit > 0:
            # Wells Fargo allows up to 20% increase for strong credit
            max_amount_increase = original_amount * 0.2
            counter_amount = min(requested_credit_limit, original_amount + max_amount_increase)
        else:
            counter_amount = original_amount
        
        # Origination fee: Max 25% reduction
        max_fee_reduction = original_fee * 0.25
        counter_fee = max(requested_origination_fee, original_fee - max_fee_reduction)
        
        # Create counter-offer
        counter_offer = BankOffer(
            offer_id=f"WF_COUNTER_{uuid.uuid4().hex[:8]}",
            intent_id=original_offer_id,
            bank_name=bank_name,
            bank_id="wells-fargo-001",
            approved_credit_limit=counter_amount,
            interest_rate=counter_rate,
            draw_fee_percentage=0.45,  # Slightly reduced from original
            unused_credit_fee=0.22,  # Slightly reduced from original
            line_of_credit_schedule=LineOfCreditSchedule(
                draw_period_months=counter_draw_period,
                repayment_period_months=counter_repayment_period,
                minimum_interest_payment=counter_amount * 0.01,  # 1% of credit limit
                draw_availability_schedule="business_hours",
                credit_review_frequency="annually"
            ),
            esg_impact=ESGImpact(
                overall_esg_score=8.5,
                esg_summary="Wells Fargo maintains strong ESG practices with renewable energy investments and community development programs",
                carbon_footprint_reduction=15.0
            ),
            additional_conditions="Standard Wells Fargo line of credit terms apply",
            reasoning=f"Counter-offer based on Wells Fargo's conservative negotiation policy. Interest rate reduced by {original_rate - counter_rate:.2f}%, credit limit adjusted to ${counter_amount:,.0f}, origination fee reduced by ${original_fee - counter_fee:.0f}",
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
            negotiation_reasoning=f"Wells Fargo's counter-offer reflects our conservative lending approach while meeting your key requirements. We've reduced the interest rate by {original_rate - counter_rate:.2f}%, adjusted the credit limit to ${counter_amount:,.0f}, and reduced the origination fee by ${original_fee - counter_fee:.0f}. This offer maintains our risk standards while providing competitive terms."
        )
        
        return counter_offer_response.model_dump(mode='json')

    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        """Stream agent responses"""
        
        # Check if this is a negotiation message and handle it directly
        try:
            import json
            message_data = json.loads(query)
            
            if message_data.get("action") == "negotiate_offer":
                print(f"🔄 WELLS FARGO: Received negotiation request")
                print(f"   📋 Original Offer ID: {message_data.get('original_offer_id')}")
                print(f"   🏢 Company: {message_data.get('company_name')}")
                print(f"   📄 Negotiation Terms: {message_data.get('negotiation_terms')}")
                
                # Handle negotiation request directly
                result = self.process_negotiation_request(query)
                
                if result["status"] == "success":
                    negotiation_response = result["negotiation_response"]
                    print(f"   ✅ WELLS FARGO: Generated counter-offer successfully")
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
