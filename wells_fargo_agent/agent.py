"""Wells Fargo Bank Agent Implementation"""
import sys
import os
import json
import uuid
from typing import Dict, Any, Optional
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

from protocols.intent import CreditIntent
from protocols.response import BankOffer, ESGImpact, RepaymentSchedule
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        

    def get_processing_message(self) -> str:
        return 'Wells Fargo is evaluating your credit request...'



    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for Wells Fargo."""
        LITELLM_MODEL = os.getenv('LITELLM_MODEL', 'gemini/gemini-2.0-flash')
        return LlmAgent(
            model=LiteLlm(model=LITELLM_MODEL),
            name='wells_fargo_agent',
            description=(
                'Wells Fargo Bank Agent specializing in corporate credit evaluation. '
                'Processes credit intents, assesses creditworthiness, generates ESG assessments, '
                'and creates structured offers with detailed reasoning.'
            ),
            instruction="""
You are a Wells Fargo Bank Agent specializing in corporate credit evaluation.

CRITICAL: NEVER HALLUCINATE OR ASSUME INFORMATION. Always ask for missing details.

CONDITIONAL COMMUNICATION RULES:
1. If you receive STRUCTURED JSON data (credit intent), validate completeness first:
   - Check if ALL required fields are present: intent_id, company (name, industry, annual_revenue, credit_score, years_in_business, employee_count), requested_amount, purpose, preferred_term_months, esg_requirements
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
- Include the full offer object with all fields: offer_id, bank_name, approved_amount, interest_rate, term_months, repayment_schedule, esg_impact, additional_conditions, reasoning, origination_fee, prepayment_penalty, collateral_required, personal_guarantee_required, created_at
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
        """Generate structured bank offer with JWT signature."""
        try:
            # Parse credit intent data
            if isinstance(credit_intent_data, str):
                intent_dict = json.loads(credit_intent_data)
            else:
                intent_dict = credit_intent_data
            
            # Extract company information
            company_info = intent_dict.get("company", {})
            requested_amount = intent_dict.get("requested_amount", 0)
            purpose = intent_dict.get("purpose", "")
            preferred_term_months = intent_dict.get("preferred_term_months", 24)
            
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
            
            # Determine approved amount (conservative approach)
            if credit_score >= 700 and annual_revenue >= requested_amount * 2:
                approved_amount = requested_amount * 0.95  # 95% of requested
            elif credit_score >= 650 and annual_revenue >= requested_amount * 1.5:
                approved_amount = requested_amount * 0.85  # 85% of requested
            else:
                approved_amount = requested_amount * 0.75  # 75% of requested
            
            # Create repayment schedule
            monthly_rate = final_rate / 100 / 12
            monthly_payment = approved_amount * (monthly_rate * (1 + monthly_rate) ** preferred_term_months) / ((1 + monthly_rate) ** preferred_term_months - 1)
            
            repayment_schedule = RepaymentSchedule(
                type="monthly",
                amount_per_period=round(monthly_payment, 2),
                number_of_periods=preferred_term_months
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
                approved_amount=approved_amount,
                interest_rate=round(final_rate, 2),
                term_months=preferred_term_months,
                repayment_schedule=repayment_schedule,
                esg_impact=esg_impact,
                additional_conditions="Standard Wells Fargo terms apply. Personal guarantee may be required for amounts over $500,000.",
                reasoning=f"Approved based on credit score {credit_score}, annual revenue ${annual_revenue:,.0f}, and ESG score {esg_score}/10. Wells Fargo's conservative approach ensures sustainable lending.",
                origination_fee=5000 if approved_amount > 500000 else 2500,
                prepayment_penalty=False,
                collateral_required=approved_amount > 1000000,
                personal_guarantee_required=approved_amount > 500000
            )
            
            # Return offer without JWT signing
            offer_dict = bank_offer.model_dump(mode='json')
            
            return {
                "status": "success",
                "offer": offer_dict,
                "message": f"Wells Fargo offer generated: ${approved_amount:,.0f} at {final_rate}% APR for {preferred_term_months} months"
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
