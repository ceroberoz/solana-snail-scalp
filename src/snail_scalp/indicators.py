"""Technical Analysis Indicators"""

import numpy as np
from collections import deque
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class BollingerBands:
    lower: float
    middle: float
    upper: float
    width_percent: float


@dataclass
class ExitLevels:
    tp1: float
    tp2: float
    stop: float


class TechnicalIndicators:
    """Bollinger Bands and RSI calculation"""

    def __init__(self, period: int = 20):
        self.period = period
        self.prices = deque(maxlen=period + 10)
        self.volumes = deque(maxlen=period + 10)

    def add_price(self, price: float, volume: float = 0):
        """Add new price point"""
        self.prices.append(price)
        self.volumes.append(volume)

    def calculate_bb(self) -> Optional[BollingerBands]:
        """Calculate Bollinger Bands"""
        if len(self.prices) < self.period:
            return None

        prices = list(self.prices)[-self.period :]
        sma = np.mean(prices)
        std = np.std(prices)

        upper = sma + (std * 2)
        lower = sma - (std * 2)
        width = ((upper - lower) / sma) * 100

        return BollingerBands(lower=lower, middle=sma, upper=upper, width_percent=width)

    def calculate_rsi(self, period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(self.prices) < period + 1:
            return 50.0  # Neutral when not enough data

        prices = list(self.prices)[-period - 1 :]
        deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]

        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def is_entry_signal(
        self,
        current_price: float,
        rsi_min: int = 25,
        rsi_max: int = 35,
        min_band_width: float = 2.0,
    ) -> bool:
        """Check all entry conditions"""
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()

        if bb is None:
            return False

        # Condition 1: Price at or below lower band (with 0.1% tolerance)
        at_bb = current_price <= bb.lower * 1.001

        # Condition 2: RSI in oversold range
        rsi_ok = rsi_min <= rsi <= rsi_max

        # Condition 3: Band width > minimum (avoid flat markets)
        volatility_ok = bb.width_percent > min_band_width

        # Condition 4: Price is above recent low (avoid falling knives)
        recent_low = min(list(self.prices)[-5:]) if len(self.prices) >= 5 else current_price
        not_falling = current_price > recent_low * 0.99

        return at_bb and rsi_ok and volatility_ok and not_falling

    def get_exit_levels(self, entry_price: float) -> ExitLevels:
        """Calculate take-profit and stop-loss levels"""
        bb = self.calculate_bb()

        if bb is None:
            # Use percentage targets if bands not ready
            return ExitLevels(
                tp1=entry_price * 1.025, tp2=entry_price * 1.04, stop=entry_price * 0.985
            )

        return ExitLevels(
            tp1=bb.middle,  # Middle band
            tp2=bb.upper,  # Upper band
            stop=entry_price * 0.985,  # 1.5% hard stop
        )

    def get_stats(self) -> dict:
        """Get current indicator statistics"""
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()

        return {
            "bb_lower": bb.lower if bb else None,
            "bb_middle": bb.middle if bb else None,
            "bb_upper": bb.upper if bb else None,
            "bb_width": bb.width_percent if bb else None,
            "rsi": rsi,
            "data_points": len(self.prices),
        }
