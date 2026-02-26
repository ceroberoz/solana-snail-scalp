"""Test Sprint 5-6 Implementation (Intelligence Layer)"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from dataclasses import dataclass
from typing import List
from collections import deque


# Mock correlation tracker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'snail_scalp'))
from correlation_tracker import CorrelationTracker, TokenPriceHistory


@dataclass
class MockIndicators:
    """Mock indicators for testing"""
    prices: List[float]
    volumes: List[float]
    
    def calculate_confidence_score(self):
        """US-3.2: Mock confidence score"""
        return 70  # Moderate confidence
    
    def detect_market_regime(self, adx_threshold=25.0):
        """US-1.5: Mock regime detection"""
        return "TRENDING_UP"


def test_partial_scaling_config():
    """US-2.6: Partial scaling configuration"""
    from snail_scalp.config import StrategyConfig
    config = StrategyConfig()
    
    assert hasattr(config, 'use_partial_scaling')
    assert hasattr(config, 'partial_scale_levels')
    assert config.use_partial_scaling == True
    
    # Check scale levels: (portion, profit%)
    levels = config.partial_scale_levels
    assert len(levels) == 3  # 3 scale levels
    assert levels[0] == (0.25, 1.5)  # 25% at +1.5%
    assert levels[1] == (0.25, 2.5)  # 25% at +2.5%
    assert levels[2] == (0.25, 4.0)  # 25% at +4.0%
    
    print("[OK] US-2.6: Partial scaling config correct (25/50/75% at +1.5/2.5/4%)")


def test_dynamic_sizing_config():
    """US-3.2: Dynamic position sizing configuration"""
    from snail_scalp.config import StrategyConfig
    config = StrategyConfig()
    
    assert hasattr(config, 'use_dynamic_sizing')
    assert hasattr(config, 'min_position_ratio')
    assert hasattr(config, 'max_position_ratio')
    
    assert config.use_dynamic_sizing == True
    assert config.min_position_ratio == 0.5  # 50% minimum
    assert config.max_position_ratio == 1.5  # 150% maximum
    
    print("[OK] US-3.2: Dynamic sizing config correct (50-150% of base)")


def test_correlation_config():
    """US-3.3: Correlation risk management configuration"""
    from snail_scalp.config import StrategyConfig
    config = StrategyConfig()
    
    assert hasattr(config, 'use_correlation_check')
    assert hasattr(config, 'max_correlated_positions')
    assert hasattr(config, 'correlation_threshold')
    
    assert config.use_correlation_check == True
    assert config.max_correlated_positions == 2
    assert config.correlation_threshold == 0.7
    
    print("[OK] US-3.3: Correlation config correct (max 2 correlated, threshold 0.7)")


def test_regime_detection_config():
    """US-1.5: Market regime detection configuration"""
    from snail_scalp.config import StrategyConfig
    config = StrategyConfig()
    
    assert hasattr(config, 'use_regime_detection')
    assert hasattr(config, 'skip_choppy_markets')
    assert hasattr(config, 'position_size_by_regime')
    
    assert config.use_regime_detection == True
    assert config.skip_choppy_markets == True
    assert config.position_size_by_regime == True
    
    print("[OK] US-1.5: Regime detection config correct")


def test_correlation_tracker():
    """US-3.3: Correlation tracker functionality"""
    tracker = CorrelationTracker(threshold=0.7, lookback=20)
    
    # Add prices for two correlated tokens
    for i in range(30):
        price = 100 + i * 0.5  # Upward trend
        tracker.add_price("TOKEN_A", price)
        tracker.add_price("TOKEN_B", price * 0.98)  # Similar trend
    
    # Calculate correlation
    corr = tracker.calculate_correlation("TOKEN_A", "TOKEN_B")
    print(f"  Correlation TOKEN_A vs TOKEN_B: {corr:.3f}")
    
    # Should be highly correlated
    assert abs(corr) > 0.5, f"Expected high correlation, got {corr}"
    
    # Check correlation risk
    allowed, correlated = tracker.check_correlation_risk(
        "TOKEN_A", ["TOKEN_B"], max_correlated=2
    )
    print(f"  Correlation check: allowed={allowed}, correlated={correlated}")
    
    print("[OK] US-3.3: Correlation tracker working")


def test_correlation_uncorrelated():
    """US-3.3: Uncorrelated tokens should pass"""
    tracker = CorrelationTracker(threshold=0.7, lookback=20)
    
    # Add prices for uncorrelated tokens
    import random
    random.seed(42)
    
    for i in range(30):
        tracker.add_price("TOKEN_A", 100 + i * 0.5)
        tracker.add_price("TOKEN_C", 100 + random.uniform(-5, 5))  # Random
    
    corr = tracker.calculate_correlation("TOKEN_A", "TOKEN_C")
    print(f"  Correlation TOKEN_A vs TOKEN_C: {corr:.3f}")
    
    # Should be uncorrelated
    assert abs(corr) < 0.7, f"Expected low correlation, got {corr}"
    
    # Should be allowed
    allowed, correlated = tracker.check_correlation_risk(
        "TOKEN_A", ["TOKEN_C"], max_correlated=2
    )
    assert allowed == True
    
    print("[OK] US-3.3: Uncorrelated tokens allowed")


def test_indicators_confidence_score():
    """US-3.2: Calculate confidence score"""
    from snail_scalp.indicators import TechnicalIndicators
    
    ind = TechnicalIndicators()
    
    # Add price data with volume
    for i in range(25):
        price = 100.0 + i * 0.1
        volume = 1000 * 1.5 if i > 20 else 1000  # Higher volume at end
        ind.add_price(price, volume)
    
    confidence = ind.calculate_confidence_score()
    print(f"  Confidence score: {confidence:.1f}/100")
    
    assert 0 <= confidence <= 100, "Confidence should be 0-100"
    assert confidence > 50, "Should have moderate confidence with this setup"
    
    print("[OK] US-3.2: Confidence score calculated")


def test_regime_detection():
    """US-1.5: Market regime detection"""
    from snail_scalp.indicators import TechnicalIndicators
    
    ind = TechnicalIndicators()
    
    # Add trending data
    for i in range(50):
        price = 100.0 + i * 0.5  # Strong uptrend
        ind.add_price(price, 1000)
    
    regime = ind.detect_market_regime(adx_threshold=25.0)
    print(f"  Detected regime: {regime}")
    
    assert regime in ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "CHOPPY"]
    
    print("[OK] US-1.5: Market regime detected")


def test_trade_partial_scaling_fields():
    """US-2.6: Trade has partial scaling fields"""
    from snail_scalp.trader import Trade
    
    trade = Trade(
        entry_price=100.0,
        size_usd=3.0,
        entry_time=1000000
    )
    
    # Check fields exist
    assert hasattr(trade, 'scale_levels_hit')
    assert hasattr(trade, 'final_position_size')
    
    # Check defaults
    assert trade.scale_levels_hit == [False, False, False] or trade.scale_levels_hit == []
    assert trade.final_position_size == 3.0
    
    print("[OK] US-2.6: Trade has partial scaling fields")


def test_trade_regime_field():
    """US-1.5: Trade has regime field"""
    from snail_scalp.trader import Trade
    
    trade = Trade(
        entry_price=100.0,
        size_usd=3.0,
        entry_time=1000000,
        entry_regime="TRENDING_UP"
    )
    
    assert hasattr(trade, 'entry_regime')
    assert trade.entry_regime == "TRENDING_UP"
    
    print("[OK] US-1.5: Trade has regime tracking")


if __name__ == "__main__":
    print("\n=== Testing Sprint 5-6 Implementation ===\n")
    try:
        test_partial_scaling_config()
        test_dynamic_sizing_config()
        test_correlation_config()
        test_regime_detection_config()
        test_correlation_tracker()
        test_correlation_uncorrelated()
        test_indicators_confidence_score()
        test_regime_detection()
        test_trade_partial_scaling_fields()
        test_trade_regime_field()
        print("\n=== All Sprint 5-6 Tests Passed! ===")
    except AssertionError as e:
        print(f"\n[FAIL] Test Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
