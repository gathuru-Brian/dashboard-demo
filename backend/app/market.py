from __future__ import annotations

from typing import Any, Dict, Optional, Union

from backend.Models.schemas import MarketIntelQuery


def get_market_signal(
    query: Optional[Union[dict, MarketIntelQuery]] = None,
) -> Dict[str, Any]:
    if isinstance(query, MarketIntelQuery):
        region = query.region
        line_of_business = query.line_of_business
    elif isinstance(query, dict):
        region = query.get("region", "global")
        line_of_business = query.get("line_of_business", "general")
    else:
        region = "global"
        line_of_business = "general"

    return {
        "signal": "stable",
        "region": region,
        "line_of_business": line_of_business,
        "message": "Capacity remains broadly stable, but monitoring is advised for retention-sensitive segments.",
    }
