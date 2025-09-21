"""Credit Intent Protocol Definition"""
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime

class CompanyInfo(BaseModel):
    name: str = Field(..., description="Name of the company")
    industry: str = Field(..., description="Industry of the company")
    annual_revenue: float = Field(..., description="Annual revenue of the company in USD")
    credit_score: int = Field(..., description="Company's credit score (e.g., 300-850)")
    years_in_business: int = Field(..., description="Number of years the company has been in business")
    employee_count: int = Field(..., description="Number of employees in the company")

class CreditIntent(BaseModel):
    intent_id: str = Field(default_factory=lambda: f"INTENT_{uuid.uuid4().hex}", description="Unique identifier for the credit intent")
    company: CompanyInfo = Field(..., description="Information about the company requesting credit")
    requested_credit_limit: float = Field(..., description="Desired credit limit in USD")
    credit_purpose: str = Field(..., description="Purpose of the line of credit (e.g., working capital, seasonal needs)")
    draw_period_months: int = Field(..., description="Period during which funds can be drawn (e.g., 12 months)")
    repayment_period_months: int = Field(..., description="Period to repay after draw period ends (e.g., 24 months)")
    minimum_draw_amount: float = Field(default=10000.0, description="Minimum amount per draw request in USD")
    credit_utilization_target: float = Field(default=0.7, description="Expected percentage of credit line to be used (0.0-1.0)")
    revolving_credit: bool = Field(default=True, description="Whether this is a revolving line of credit")
    esg_requirements: str = Field(..., description="Specific ESG (Environmental, Social, Governance) requirements or preferences")
    preferred_interest_rate: float = Field(default=0.0, description="Preferred interest rate (0.0 if no preference)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when intent was created")
