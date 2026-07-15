import sys
from pathlib import Path
import random


def _ensure_repo_root_on_path() -> None:
    current = Path(__file__).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "backend").exists() and (candidate / "backend" / "Models").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


_ensure_repo_root_on_path()

from backend.Models.schemas import MarketIntelQuery, MarketIntelResult

class MarketIntelligenceService:
    def __init__(self):
        # Mock database for market intel
        self.mock_trends = [
            "Hardening market in property catastrophe",
            "Increased demand for cyber reinsurance",
            "Inflation driving up attachment points",
            "Capacity constraints in lower layers"
        ]
        
    async def gather_intelligence(self, query: MarketIntelQuery) -> MarketIntelResult:
        """
        Simulate gathering market intelligence based on region and line of business.
        In a real system, this would call external APIs, scrape reports, or query an LLM.
        """
        # Generate mock competitor rates
        base_rate = random.uniform(0.05, 0.15)
        competitors = ["Swiss Re", "Munich Re", "Hannover Re", "SCOR"]
        rates = {comp: round(base_rate * random.uniform(0.9, 1.1), 4) for comp in competitors}
        
        # Select random trends
        trends = random.sample(self.mock_trends, 2)
        
        return MarketIntelResult(
            summary=f"Market analysis for {query.line_of_business} in {query.region} indicates firming rates.",
            competitor_rates=rates,
            market_trends=trends,
            sentiment_score=round(random.uniform(0.4, 0.9), 2)
        )
