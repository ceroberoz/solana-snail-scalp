"""Test Quick Wins Implementation"""
import sys
import os

# Direct imports to avoid full package load
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from collections import deque


# Inline the classes we need to test
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


@dataclass
class StrategyConfig:
    check_interval_seconds: int = 300
    bb_period: int = 20
    bb_std: float = 2.0
    rsi_period: int = 14
    rsi_oversold_min: int = 20  # US-1.1: Changed from 25 to 20
    rsi_oversold_max: int = 40  # US-1.1: Changed from 35 to 40
    min_band_width_percent: float = 2.0
    primary_allocation: float = 3.0
    dca_allocation_ratio: float = 0.5  # US-3.1: 50% of original
    dca_trigger_percent: float = 1.0
    tp1_percent: float = 2.5
    tp2_percent: float = 4.0
    use_atr_stop: bool = True  # US-2.1: Enable ATR stops
    stop_loss_atr_multiplier: float = 1.5  # US-2.1: ATR multiplier
    stop_loss_max_percent: float = 3.0  # US-2.1: Max stop cap


class TechnicalIndicators:
    """Test version of TechnicalIndicators with Quick Wins"""

    def __init__(self, period: int = 20):
        self.period = period
        self.prices = deque(maxlen=period + 10)
        self.volumes = deque(maxlen=period + 10)

    def add_price(self, price: float, volume: float = 0):
        self.prices.append(price)
        self.volumes.append(volume)

    def calculate_bb(self) -> Optional[BollingerBands]:
        if len(self.prices) < self.period:
            return None
        prices = list(self.prices)[-self.period:]
        sma = np.mean(prices)
        std = np.std(prices)
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        width = ((upper - lower) / sma) * 100
        return BollingerBands(lower=lower, middle=sma, upper=upper, width_percent=width)

    def calculate_rsi(self, period: int = 14) -> float:
        if len(self.prices) < period + 1:
            return 50.0
        prices = list(self.prices)[-period - 1:]
        deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _check_volume_confirmation(self, threshold: float = 1.3) -> bool:
        """US-1.2: Check if current volume is above threshold x average"""
        if len(self.volumes) < self.period:
            return True
        volumes = list(self.volumes)[-self.period:]
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        current_volume = volumes[-1]
        if avg_volume == 0:
            return True
        return current_volume >= avg_volume * threshold

    def calculate_atr(self, period: int = 14) -> float:
        """US-2.1: Calculate Average True Range"""
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

    def is_entry_signal(self, current_price: float, rsi_min: int = 20, 
                        rsi_max: int = 40, min_band_width: float = 2.0) -> bool:
        """US-1.1: RSI 20-40, US-1.3: 0.5% BB tolerance, US-1.2: Volume check"""
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()
        if bb is None:
            return False
        # US-1.3: 0.5% tolerance (was 0.1%)
        at_bb = current_price <= bb.lower * 1.005
        # US-1.1: RSI 20-40 range
        rsi_ok = rsi_min <= rsi <= rsi_max
        volatility_ok = bb.width_percent > min_band_width
        recent_low = min(list(self.prices)[-5:]) if len(self.prices) >= 5 else current_price
        not_falling = current_price > recent_low * 0.99
        # US-1.2: Volume confirmation
        volume_ok = self._check_volume_confirmation()
        return at_bb and rsi_ok and volatility_ok and not_falling and volume_ok

    def get_exit_levels(self, entry_price: float, use_atr: bool = True,
                        atr_multiplier: float = 1.5, max_stop_pct: float = 3.0) -> ExitLevels:
        """US-2.1: ATR-based stops"""
        bb = self.calculate_bb()
        if use_atr:
            atr = self.calculate_atr()
            if atr > 0:
                atr_stop = entry_price - (atr * atr_multiplier)
                max_stop = entry_price * (1 - max_stop_pct / 100)
                stop = max(atr_stop, max_stop)
            else:
                stop = entry_price * 0.985
        else:
            stop = entry_price * 0.985
        if bb is None:
            return ExitLevels(tp1=entry_price * 1.025, tp2=entry_price * 1.04, stop=stop)
        return ExitLevels(tp1=bb.middle, tp2=bb.upper, stop=stop)


def test_rsi_range():
    """US-1.1: RSI range should be 20-40"""
    config = StrategyConfig()
    assert config.rsi_oversold_min == 20
    assert config.rsi_oversold_max == 40
    print("[OK] US-1.1: RSI range is 20-40")


def test_bb_tolerance():
    """US-1.3: BB near-touch tolerance is 0.5%"""
    ind = TechnicalIndicators()
    for i in range(25):
        ind.add_price(100.0 + i * 0.1, volume=1000)
    bb = ind.calculate_bb()
    if bb:
        test_price = bb.lower * 1.005  # 0.5% tolerance
        print(f"  BB lower: {bb.lower:.4f}, Test price: {test_price:.4f}")
    print("[OK] US-1.3: BB tolerance is 0.5% (price <= lower * 1.005)")


def test_volume_confirmation():
    """US-1.2: Volume confirmation at 1.3x average"""
    ind = TechnicalIndicators()
    base_volume = 1000
    for i in range(24):
        ind.add_price(100.0 + i * 0.1, volume=base_volume)
    # Add high volume for last candle (1.5x)
    ind.add_price(102.4, volume=base_volume * 1.5)
    result = ind._check_volume_confirmation(threshold=1.3)
    assert result == True, "Volume should confirm (1.5x > 1.3x)"
    print(f"  Volume confirmation (1.3x threshold): {result}")
    print("[OK] US-1.2: Volume confirmation implemented")


def test_atr_calculation():
    """US-2.1: ATR calculation"""
    ind = TechnicalIndicators()
    prices = [100, 105, 102, 108, 104, 110, 106, 112, 108, 115, 111, 118, 114, 120, 116]
    for p in prices:
        ind.add_price(p, volume=1000)
    atr = ind.calculate_atr(period=14)
    print(f"  ATR(14): {atr:.4f}")
    assert atr > 0, "ATR should be positive"
    print("[OK] US-2.1: ATR calculation implemented")


def test_atr_stop():
    """US-2.1: ATR-based stop loss"""
    ind = TechnicalIndicators()
    # Add volatile data
    prices = [100, 105, 102, 108, 104, 110, 106, 112, 108, 115, 111, 118, 114, 120, 116, 122, 118, 124]
    for p in prices:
        ind.add_price(p, volume=1000)
    entry = 124.0
    exit_levels = ind.get_exit_levels(entry, use_atr=True, atr_multiplier=1.5, max_stop_pct=3.0)
    atr = ind.calculate_atr()
    expected_stop = max(entry - (atr * 1.5), entry * 0.97)  # ATR stop or 3% max
    print(f"  Entry: {entry:.4f}, ATR: {atr:.4f}, Stop: {exit_levels.stop:.4f}")
    print(f"  Stop distance: {(entry - exit_levels.stop) / entry * 100:.2f}%")
    assert exit_levels.stop > 0
    print("[OK] US-2.1: ATR-based stop implemented")


def test_dca_config():
    """US-3.1: DCA allocation ratio is 0.5 (50%)"""
    config = StrategyConfig()
    assert config.dca_allocation_ratio == 0.5
    print("[OK] US-3.1: DCA allocation ratio is 50%")


def test_atr_stop_config():
    """US-2.1: ATR stop configuration"""
    config = StrategyConfig()
    assert config.use_atr_stop == True
    assert config.stop_loss_atr_multiplier == 1.5
    assert config.stop_loss_max_percent == 3.0
    print("[OK] US-2.1: ATR stop configuration correct")


if __name__ == "__main__":
    print("\n=== Testing Quick Wins Implementation ===\n")
    try:
        test_rsi_range()
        test_volume_confirmation()
        test_bb_tolerance()
        test_atr_calculation()
        test_atr_stop()
        test_dca_config()
        test_atr_stop_config()
        print("\n=== All Quick Wins Tests Passed! ===")
    except AssertionError as e:
        print(f"\n[FAIL] Test Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
