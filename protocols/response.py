"""Bank Offer Response Protocol Definition"""
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime

class ESGImpact(BaseModel):
    overall_esg_score: float = Field(..., description="Overall ESG score (e.g., 0-10)")
    esg_summary: str = Field(..., description="Human-readable summary of the ESG impact")
    carbon_footprint_reduction: Optional[float] = Field(None, description="Estimated carbon footprint reduction percentage")

class RepaymentSchedule(BaseModel):
    type: str = Field(..., description="Type of repayment (e.g., 'monthly', 'quarterly')")
    amount_per_period: float = Field(..., description="Amount to be repaid per period")
    number_of_periods: int = Field(..., description="Total number of repayment periods")

class BankOffer(BaseModel):
    offer_id: str = Field(default_factory=lambda: f"OFFER_{uuid.uuid4().hex}", description="Unique identifier for the bank offer")
    intent_id: str = Field(..., description="ID of the original credit intent this offer responds to")
    bank_name: str = Field(..., description="Name of the offering bank")
    bank_id: str = Field(..., description="Unique identifier for the bank")
    approved_amount: float = Field(..., description="Approved credit amount in USD")
    interest_rate: float = Field(..., description="Annual interest rate offered (percentage)")
    term_months: int = Field(..., description="Approved repayment term in months")
    repayment_schedule: Optional[RepaymentSchedule] = Field(None, description="Detailed repayment schedule")
    esg_impact: ESGImpact = Field(..., description="ESG impact assessment of the offer")
    additional_conditions: Optional[str] = Field(None, description="Any additional terms or conditions")
    reasoning: str = Field(..., description="Detailed reasoning behind the bank's offer")
    origination_fee: Optional[float] = Field(None, description="Origination fee in USD")
    prepayment_penalty: bool = Field(default=False, description="Whether prepayment penalty applies")
    collateral_required: bool = Field(default=False, description="Whether collateral is required")
    personal_guarantee_required: bool = Field(default=False, description="Whether personal guarantee is required")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when offer was created")
