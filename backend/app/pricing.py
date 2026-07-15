from __future__ import annotations

from typing import Optional, Union

from backend.Models.schemas import PricingResult, TreatyInput
from backend.core.Pricing_engine import ActuarialPricingEngine


def calculate_price(
    base_price: Optional[float] = None,
    margin: float = 0.1,
    treaty: Optional[TreatyInput] = None,
) -> Union[float, PricingResult]:
    if treaty is not None:
        engine = ActuarialPricingEngine()
        return engine.calculate_burning_cost(treaty)

    if base_price is None:
        raise ValueError("base_price is required when treaty is not provided")

    return round(base_price * (1 + margin), 2)
