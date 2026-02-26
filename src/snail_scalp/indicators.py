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

        # Condition 1: Price at or below lower band (with 0.5% tolerance - US-1.3)
        at_bb = current_price <= bb.lower * 1.005

        # Condition 2: RSI in oversold range
        rsi_ok = rsi_min <= rsi <= rsi_max

        # Condition 3: Band width > minimum (avoid flat markets)
        volatility_ok = bb.width_percent > min_band_width

        # Condition 4: Price is above recent low (avoid falling knives)
        recent_low = min(list(self.prices)[-5:]) if len(self.prices) >= 5 else current_price
        not_falling = current_price > recent_low * 0.99

        # Condition 5: Volume confirmation (>1.3x average - US-1.2)
        volume_ok = self._check_volume_confirmation()

        return at_bb and rsi_ok and volatility_ok and not_falling and volume_ok

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

    def _check_volume_confirmation(self, threshold: float = 1.3) -> bool:
        """Check if current volume is above threshold x average (US-1.2)"""
        if len(self.volumes) < self.period:
            return True  # Allow if not enough data
        
        volumes = list(self.volumes)[-self.period:]
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        current_volume = volumes[-1]
        
        if avg_volume == 0:
            return True
        
        return current_volume >= avg_volume * threshold

    def calculate_atr(self, period: int = 14) -> float:
        """Calculate Average True Range (ATR) for dynamic stops (US-2.1)"""
        if len(self.prices) < period + 1:
            return 0.0
        
        prices = list(self.prices)
        tr_values = []
        
        for i in range(1, min(period + 1, len(prices))):
            high = max(prices[-(i+1):-i+1]) if i > 1 else prices[-i]
            low = min(prices[-(i+1):-i+1]) if i > 1 else prices[-(i+1)]
            close_prev = prices[-(i+1)]
            
            tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
            tr_values.append(tr)
        
        return np.mean(tr_values) if tr_values else 0.0

    def get_exit_levels(self, entry_price: float, use_atr: bool = True, 
                        atr_multiplier: float = 1.5, max_stop_pct: float = 3.0) -> ExitLevels:
        """Calculate take-profit and stop-loss levels with ATR support (US-2.1)"""
        bb = self.calculate_bb()
        
        if use_atr:
            atr = self.calculate_atr()
            if atr > 0:
                # ATR-based stop: Entry - (ATR * multiplier), capped at max_stop_pct
                atr_stop = entry_price - (atr * atr_multiplier)
                max_stop = entry_price * (1 - max_stop_pct / 100)
                stop = max(atr_stop, max_stop)  # Don't exceed max_stop_pct
            else:
                stop = entry_price * 0.985  # Fallback to 1.5% hard stop
        else:
            stop = entry_price * 0.985  # 1.5% hard stop

        if bb is None:
            # Use percentage targets if bands not ready
            return ExitLevels(
                tp1=entry_price * 1.025, tp2=entry_price * 1.04, stop=stop
            )

        return ExitLevels(
            tp1=bb.middle,  # Middle band
            tp2=bb.upper,  # Upper band
            stop=stop,
        )

    def get_stats(self) -> dict:
        """Get current indicator statistics"""
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()
        atr = self.calculate_atr()

        return {
            "bb_lower": bb.lower if bb else None,
            "bb_middle": bb.middle if bb else None,
            "bb_upper": bb.upper if bb else None,
            "bb_width": bb.width_percent if bb else None,
            "rsi": rsi,
            "atr": atr,
            "data_points": len(self.prices),
        }
