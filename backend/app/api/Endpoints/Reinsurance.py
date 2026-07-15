from fastapi import APIRouter, Depends, HTTPException
import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
    current = Path(__file__).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "backend").exists() and (candidate / "backend" / "Models").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


_ensure_repo_root_on_path()

from backend.Models.schemas import TreatyInput, PricingResult, MarketIntelQuery, MarketIntelResult
from backend.core.Pricing_engine import ActuarialPricingEngine
from backend.Services.market_intel import MarketIntelligenceService

router = APIRouter()

def get_pricing_engine():
    return ActuarialPricingEngine()

def get_intel_service():
    return MarketIntelligenceService()

@router.post("/pricing/calculate", response_model=PricingResult)
async def calculate_pricing(
    treaty: TreatyInput,
    engine: ActuarialPricingEngine = Depends(get_pricing_engine)
):
    try:
        result = engine.calculate_burning_cost(treaty)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/intelligence/analyze", response_model=MarketIntelResult)
async def analyze_market(
    query: MarketIntelQuery,
    service: MarketIntelligenceService = Depends(get_intel_service)
):
    try:
        result = await service.gather_intelligence(query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))