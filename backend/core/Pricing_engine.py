import sys
from pathlib import Path
import pandas as pd
import numpy as np


def _ensure_repo_root_on_path() -> None:
    current = Path(__file__).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "backend").exists() and (candidate / "backend" / "Models").exists():
            if str(candidate) not in sys.path:
                sys.path.insert(0, str(candidate))
            return


_ensure_repo_root_on_path()

from backend.Models.schemas import TreatyInput, PricingResult

class ActuarialPricingEngine:
    def __init__(self):
        # Default Loss Development Factors (LDFs) - mock data for demonstration
        self.ldfs = {
            1: 1.50,
            2: 1.25,
            3: 1.10,
            4: 1.05,
            5: 1.02,
            6: 1.00
        }
        
        # Trend factors for inflation
        self.trend_factor = 1.05  # 5% annual inflation

    def calculate_burning_cost(self, treaty: TreatyInput) -> PricingResult:
        """
        Calculate technical price using the Burning Cost method for Excess of Loss treaties.
        """
        df = pd.DataFrame([loss.dict() for loss in treaty.historical_losses])
        current_year = pd.Timestamp.now().year
        
        # Calculate developed and trended losses
        developed_losses = []
        for _, row in df.iterrows():
            age = current_year - row['year']
            ldf = self.ldfs.get(age, 1.0)
            trend = self.trend_factor ** age
            
            ultimate_loss = row['reported_loss'] * ldf
            trended_loss = ultimate_loss * trend
            
            # Apply layer structure (Excess of Loss)
            layer_loss = max(0, min(trended_loss - treaty.layer_attachment, treaty.layer_limit))
            developed_losses.append(layer_loss)
            
        df['layer_loss'] = developed_losses
        
        # Calculate Burning Cost Rate (Total Layer Losses / Total Subject Premium)
        total_layer_losses = df['layer_loss'].sum()
        total_premium = df['premium'].sum()
        
        burning_cost_rate = total_layer_losses / total_premium if total_premium > 0 else 0
        
        # Pure Premium
        pure_premium = total_layer_losses / len(df) if len(df) > 0 else 0
        
        # Technical Premium (Pure Premium + Expenses)
        technical_premium = pure_premium / (1 - treaty.expenses_ratio)
        
        # Commercial Premium (Technical + Profit Margin)
        commercial_premium = technical_premium / (1 - treaty.profit_margin)
        
        # Metrics
        expected_loss_ratio = pure_premium / commercial_premium if commercial_premium > 0 else 0
        combined_ratio = expected_loss_ratio + treaty.expenses_ratio
        
        return PricingResult(
            treaty_id=treaty.treaty_id,
            burning_cost_rate=round(burning_cost_rate, 4),
            pure_premium=round(pure_premium, 2),
            technical_premium=round(technical_premium, 2),
            commercial_premium=round(commercial_premium, 2),
            expected_loss_ratio=round(expected_loss_ratio, 4),
            combined_ratio=round(combined_ratio, 4),
            risk_metrics={
                "var_95": round(commercial_premium * 1.5, 2), # Mock VaR
                "tail_var_99": round(commercial_premium * 2.0, 2)
            }
        )
