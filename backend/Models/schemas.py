from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import date

class LossRecord(BaseModel):
    year: int
    reported_loss: float
    paid_loss: float
    premium: float

class TreatyInput(BaseModel):
    treaty_id: str
    client_name: str
    effective_date: date
    historical_losses: List[LossRecord]
    layer_attachment: float = Field(..., description="Attachment point for excess of loss")
    layer_limit: float = Field(..., description="Limit for excess of loss")
    target_loss_ratio: float = Field(0.65, description="Target loss ratio for pricing")
    expenses_ratio: float = Field(0.20, description="Brokerage and internal expenses")
    profit_margin: float = Field(0.15, description="Target profit margin")

class PricingResult(BaseModel):
    treaty_id: str
    burning_cost_rate: float
    pure_premium: float
    technical_premium: float
    commercial_premium: float
    expected_loss_ratio: float
    combined_ratio: float
    risk_metrics: Dict[str, float]

class MarketIntelQuery(BaseModel):
    region: str
    line_of_business: str
    keywords: List[str]

class MarketIntelResult(BaseModel):
    summary: str
    competitor_rates: Dict[str, float]
    market_trends: List[str]
    sentiment_score: float
