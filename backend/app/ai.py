from __future__ import annotations

from typing import Any, Dict, Optional, Union

from backend.Models.schemas import MarketIntelQuery


def generate_insight(
    data: Optional[Union[str, dict, MarketIntelQuery]] = None,
    *,
    region: Optional[str] = None,
    line_of_business: Optional[str] = None,
) -> Dict[str, Any]:
    if isinstance(data, MarketIntelQuery):
        region = data.region
        line_of_business = data.line_of_business
        keywords = data.keywords or []
    elif isinstance(data, dict):
        region = data.get("region", region)
        line_of_business = data.get("line_of_business", line_of_business)
        keywords = data.get("keywords", [])
    else:
        keywords = []

    if not region:
        region = "global"
    if not line_of_business:
        line_of_business = "general"

    return {
        "summary": f"AI review for {line_of_business} in {region} suggests monitoring pricing and retention risk.",
        "keywords": keywords,
        "recommendations": [
            "Review attachment points against recent loss trend.",
            "Cross-check pricing assumptions with current market conditions.",
        ],
    }
