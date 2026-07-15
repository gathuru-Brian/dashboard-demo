from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from .database import Base


class PricingRun(Base):
    __tablename__ = "pricing_runs"

    id = Column(Integer, primary_key=True, index=True)
    treaty_id = Column(String, index=True, nullable=False)
    client_name = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    technical_premium = Column(Float, default=0.0)
    commercial_premium = Column(Float, default=0.0)


class MarketInsight(Base):
    __tablename__ = "market_insights"

    id = Column(Integer, primary_key=True, index=True)
    region = Column(String, index=True)
    line_of_business = Column(String, index=True)
    summary = Column(Text, nullable=True)
    sentiment_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
