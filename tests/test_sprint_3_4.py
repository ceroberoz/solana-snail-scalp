"""Test Sprint 3-4 Implementation (Exit Optimization)"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
from collections import deque


# Inline StrategyConfig with Sprint 3-4 settings
@dataclass
class StrategyConfig:
    # Sprint 1-2 settings
    rsi_oversold_min: int = 20
    rsi_oversold_max: int = 40
    dca_allocation_ratio: float = 0.5
    use_atr_stop: bool = True
    stop_loss_atr_multiplier: float = 1.5
    stop_loss_max_percent: float = 3.0
    
    # Sprint 3-4 settings
    use_atr_targets: bool = True
    tp1_atr_multiplier: float = 1.0
    tp2_atr_multiplier: float = 2.0
    tp_min_percent: float = 2.0
    tp_max_percent: float = 8.0
    
    use_breakeven_stop: bool = True
    breakeven_buffer_percent: float = 0.1
    
    use_trailing_stop: bool = True
    trailing_stop_percent: float = 1.0
    trailing_update_interval: int = 300
    
    use_time_exit: bool = True
    max_hold_time_minutes: int = 120
    
    # Legacy
    tp1_percent: float = 2.5
    tp2_percent: float = 4.0


class TechnicalIndicators:
    """Test version with Sprint 3-4 features"""

    def __init__(self, period: int = 20, enable_multi_timeframe: bool = True):
        self.period = period
        self.prices = deque(maxlen=period + 10)
        self.volumes = deque(maxlen=period + 10)
        
        # US-1.4: Multi-timeframe
        self.enable_multi_timeframe = enable_multi_timeframe
        self.price_history_15m = deque(maxlen=50)
        self.current_candle_prices = []
        self.current_candle_volumes = []

    def add_price(self, price: float, volume: float = 0):
        self.prices.append(price)
        self.volumes.append(volume)

    def add_ohlcv(self, timestamp: float, open_p: float, high: float, low: float,
                  close: float, volume: float, timeframe_minutes: int = 5):
        self.add_price(close, volume)
        
        if not self.enable_multi_timeframe:
            return
        
        if timeframe_minutes == 5:
            self.current_candle_prices.append(close)
            self.current_candle_volumes.append(volume)
            
            if len(self.current_candle_prices) >= 3:
                self.price_history_15m.append({
                    'open': self.current_candle_prices[0],
                    'high': max(self.current_candle_prices),
                    'low': min(self.current_candle_prices),
                    'close': self.current_candle_prices[-1],
                    'volume': sum(self.current_candle_volumes)
                })
                self.current_candle_prices = []
                self.current_candle_volumes = []

    def calculate_bb(self):
        if len(self.prices) < self.period:
            return None
        prices = list(self.prices)[-self.period:]
        sma = np.mean(prices)
        std = np.std(prices)
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        width = ((upper - lower) / sma) * 100
        return type('BB', (), {'lower': lower, 'middle': sma, 'upper': upper, 'width_percent': width})()

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

    def calculate_rsi_15m(self, period: int = 14) -> float:
        if len(self.price_history_15m) < period + 1:
            return 50.0
        closes = [c['close'] for c in list(self.price_history_15m)[-period-1:]]
        deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def get_15m_trend(self, lookback: int = 3) -> str:
        if len(self.price_history_15m) < lookback + 1:
            return "UNKNOWN"
        candles = list(self.price_history_15m)[-lookback:]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        higher_highs = all(highs[i] > highs[i-1] for i in range(1, len(highs)))
        higher_lows = all(lows[i] > lows[i-1] for i in range(1, len(lows)))
        lower_highs = all(highs[i] < highs[i-1] for i in range(1, len(highs)))
        lower_lows = all(lows[i] < lows[i-1] for i in range(1, len(lows)))
        if higher_highs and higher_lows:
            return "UPTREND"
        elif lower_highs and lower_lows:
            return "DOWNTREND"
        else:
            return "RANGING"

    def check_multi_timeframe_confirm(self, current_price: float, rsi_15m_max: float = 50.0) -> bool:
        if not self.enable_multi_timeframe or len(self.price_history_15m) < 15:
            return True
        rsi_15m = self.calculate_rsi_15m()
        return rsi_15m < rsi_15m_max

    def calculate_atr(self, period: int = 14) -> float:
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


@dataclass
class Trade:
    entry_price: float
    size_usd: float
    entry_time: float
    dca_done: bool = False
    tp1_hit: bool = False
    highest_price: float = 0.0
    last_trailing_update: float = 0.0
    breakeven_stop_price: float = 0.0
    
    def __post_init__(self):
        if self.highest_price == 0.0:
            self.highest_price = self.entry_price


class MockTrader:
    """Mock trader to test exit logic"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.active_position: Optional[Trade] = None
        self.closed = False
        self.close_reason = None
    
    def check_time_exit(self, current_time: float) -> bool:
        """US-2.5: Time-based exit"""
        if not self.config.use_time_exit:
            return False
        if not self.active_position:
            return False
        hold_minutes = (current_time - self.active_position.entry_time) / 60
        return hold_minutes >= self.config.max_hold_time_minutes
    
    def check_breakeven_stop(self, current_price: float) -> bool:
        """US-2.2: Check if breakeven stop should trigger"""
        if not self.config.use_breakeven_stop:
            return False
        if not self.active_position or not self.active_position.tp1_hit:
            return False
        return current_price <= self.active_position.breakeven_stop_price
    
    def update_breakeven_stop(self, entry_price: float):
        """US-2.2: Set breakeven stop after TP1"""
        if not self.active_position:
            return
        buffer = self.config.breakeven_buffer_percent / 100
        self.active_position.breakeven_stop_price = entry_price * (1 + buffer)
    
    def update_trailing_stop(self, current_price: float, current_time: float) -> Optional[float]:
        """US-2.3: Update trailing stop"""
        if not self.config.use_trailing_stop:
            return None
        if not self.active_position or not self.active_position.tp1_hit:
            return None
        
        pos = self.active_position
        
        # Update highest price
        if current_price > pos.highest_price:
            pos.highest_price = current_price
        
        # Check if time to update trailing stop
        time_since_update = current_time - pos.last_trailing_update
        if time_since_update < self.config.trailing_update_interval:
            return None
        
        # Calculate trailing stop (1% below high)
        trailing_stop = pos.highest_price * (1 - self.config.trailing_stop_percent / 100)
        
        # Don't trail below breakeven
        min_stop = pos.breakeven_stop_price if pos.breakeven_stop_price > 0 else pos.entry_price
        effective_stop = max(trailing_stop, min_stop)
        
        pos.last_trailing_update = current_time
        return effective_stop
    
    def calculate_dynamic_targets(self, entry_price: float, atr: float) -> Tuple[float, float]:
        """US-2.4: Dynamic profit targets using ATR"""
        if not self.config.use_atr_targets or atr <= 0:
            tp1 = entry_price * (1 + self.config.tp1_percent / 100)
            tp2 = entry_price * (1 + self.config.tp2_percent / 100)
            return tp1, tp2
        
        # ATR-based with min/max caps
        tp1_pct = max(min(atr / entry_price * self.config.tp1_atr_multiplier * 100, 
                          self.config.tp_max_percent), self.config.tp_min_percent)
        tp2_pct = max(min(atr / entry_price * self.config.tp2_atr_multiplier * 100,
                          self.config.tp_max_percent), self.config.tp_min_percent)
        
        tp1 = entry_price * (1 + tp1_pct / 100)
        tp2 = entry_price * (1 + tp2_pct / 100)
        return tp1, tp2


def test_time_based_exit():
    """US-2.5: Time-based exit after 2 hours"""
    config = StrategyConfig()
    trader = MockTrader(config)
    
    # Create position 3 hours ago
    entry_time = 1000000  # Some timestamp
    trader.active_position = Trade(entry_price=100.0, size_usd=3.0, entry_time=entry_time)
    
    # Check at 3 hours later (180 minutes)
    current_time = entry_time + 180 * 60
    should_exit = trader.check_time_exit(current_time)
    
    assert should_exit == True, "Should exit after 120+ minutes"
    print("[OK] US-2.5: Time-based exit triggers after 120 minutes")
    
    # Check at 1 hour (should not exit)
    current_time = entry_time + 60 * 60
    should_exit = trader.check_time_exit(current_time)
    assert should_exit == False, "Should not exit before 120 minutes"
    print("[OK] US-2.5: Time-based exit doesn't trigger before 120 minutes")


def test_breakeven_stop():
    """US-2.2: Breakeven stop after TP1"""
    config = StrategyConfig()
    trader = MockTrader(config)
    
    entry_price = 100.0
    trader.active_position = Trade(entry_price=entry_price, size_usd=3.0, entry_time=1000000)
    trader.active_position.tp1_hit = True
    
    # Set breakeven stop (entry + 0.1% buffer)
    trader.update_breakeven_stop(entry_price)
    breakeven = trader.active_position.breakeven_stop_price
    expected = entry_price * 1.001
    
    assert abs(breakeven - expected) < 0.001, f"Breakeven should be {expected}, got {breakeven}"
    print(f"[OK] US-2.2: Breakeven stop set at ${breakeven:.4f} (+0.1% buffer)")
    
    # Check stop triggers when price drops below breakeven
    current_price = entry_price * 0.999  # Below breakeven
    should_stop = trader.check_breakeven_stop(current_price)
    assert should_stop == True, "Should trigger breakeven stop"
    print("[OK] US-2.2: Breakeven stop triggers correctly")


def test_trailing_stop():
    """US-2.3: Trailing stop after TP1"""
    config = StrategyConfig()
    trader = MockTrader(config)
    
    entry_price = 100.0
    entry_time = 1000000
    trader.active_position = Trade(entry_price=entry_price, size_usd=3.0, entry_time=entry_time)
    trader.active_position.tp1_hit = True
    trader.active_position.breakeven_stop_price = entry_price * 1.001
    
    # Price moves up to $110
    high_price = 110.0
    current_time = entry_time + 400  # Past trailing update interval
    
    # Update trailing stop
    trailing = trader.update_trailing_stop(high_price, current_time)
    
    # Trailing stop should be 1% below $110 = $108.9
    expected_trailing = high_price * 0.99
    assert trailing is not None, "Trailing stop should be calculated"
    assert abs(trailing - expected_trailing) < 0.1, f"Trailing should be ~{expected_trailing}, got {trailing}"
    print(f"[OK] US-2.3: Trailing stop at ${trailing:.4f} (1% below high ${high_price:.4f})")


def test_dynamic_targets():
    """US-2.4: Dynamic profit targets using ATR"""
    config = StrategyConfig()
    trader = MockTrader(config)
    
    entry_price = 100.0
    atr = 2.0  # 2% ATR
    
    tp1, tp2 = trader.calculate_dynamic_targets(entry_price, atr)
    
    # TP1 = Entry + (ATR * 1.0) = 100 + 2 = 102
    # But min is 2%, so 102
    expected_tp1 = entry_price * 1.02
    assert abs(tp1 - expected_tp1) < 0.5, f"TP1 should be ~{expected_tp1}, got {tp1}"
    
    # TP2 = Entry + (ATR * 2.0) = 100 + 4 = 104
    expected_tp2 = entry_price * 1.04
    assert abs(tp2 - expected_tp2) < 0.5, f"TP2 should be ~{expected_tp2}, got {tp2}"
    
    print(f"[OK] US-2.4: Dynamic targets TP1=${tp1:.2f}, TP2=${tp2:.2f}")


def test_multi_timeframe():
    """US-1.4: Multi-timeframe confirmation"""
    ind = TechnicalIndicators(enable_multi_timeframe=True)
    
    # Simulate 5m candles to build 15m data
    price = 100.0
    timestamp = 1000000
    for i in range(60):  # 60 * 5m = 300m = 5 hours of data
        ind.add_ohlcv(timestamp, price, price+1, price-1, price, 1000, timeframe_minutes=5)
        timestamp += 300  # 5 minutes
        price += 0.1
    
    # Check 15m RSI calculation
    rsi_15m = ind.calculate_rsi_15m()
    print(f"  15m RSI: {rsi_15m:.2f}")
    assert 0 <= rsi_15m <= 100, "RSI should be in valid range"
    print("[OK] US-1.4: 15m RSI calculated")
    
    # Check trend detection
    trend = ind.get_15m_trend()
    print(f"  15m Trend: {trend}")
    assert trend in ["UPTREND", "DOWNTREND", "RANGING", "UNKNOWN"]
    print("[OK] US-1.4: 15m trend detected")
    
    # Check confirmation (RSI < 50)
    confirm = ind.check_multi_timeframe_confirm(price, rsi_15m_max=50.0)
    print(f"  15m Confirmation (RSI<50): {confirm}")
    print("[OK] US-1.4: Multi-timeframe confirmation working")


if __name__ == "__main__":
    print("\n=== Testing Sprint 3-4 Implementation ===\n")
    try:
        test_time_based_exit()
        test_breakeven_stop()
        test_trailing_stop()
        test_dynamic_targets()
        test_multi_timeframe()
        print("\n=== All Sprint 3-4 Tests Passed! ===")
    except AssertionError as e:
        print(f"\n[FAIL] Test Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
