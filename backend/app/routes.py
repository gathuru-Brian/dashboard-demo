from fastapi import APIRouter, HTTPException

from backend.Models.schemas import MarketIntelQuery, TreatyInput

from .ai import generate_insight
from .market import get_market_signal
from .pricing import calculate_price

router = APIRouter(prefix="/api", tags=["core"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "RMIP-DSS"}


@router.post("/pricing/calculate")
def pricing_endpoint(treaty: TreatyInput):
    try:
        return calculate_price(treaty=treaty)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/market/signal")
def market_signal_endpoint(query: MarketIntelQuery):
    return get_market_signal(query)


@router.post("/ai/insight")
def ai_insight_endpoint(query: MarketIntelQuery):
    return generate_insight(query)
