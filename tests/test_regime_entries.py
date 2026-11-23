"""Tests for regime-aware entry modes (bull momentum, range mean reversion, bear short)."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from snail_scalp.config import StrategyConfig
from snail_scalp.indicators import TechnicalIndicators
from snail_scalp.trader import Trader


class _Risk:
    def can_trade_today(self):
        return True

    def is_trading_window(self):
        return True

    def check_position_size(self, available_capital, kind, size):
        return size


class _FakeIndicators:
    """Stub that records which entry predicate the trader called."""

    def __init__(self, regime, momentum=False, meanrev=False, short=False):
        self.regime = regime
        self.momentum = momentum
        self.meanrev = meanrev
        self.short = short
        self.momentum_called = False
        self.meanrev_called = False
        self.short_called = False

    def detect_market_regime(self, adx_threshold=25.0):
        return self.regime

    def is_momentum_entry_signal(self, *args, **kwargs):
        self.momentum_called = True
        return self.momentum

    def is_entry_signal(self, *args, **kwargs):
        self.meanrev_called = True
        return self.meanrev

    def is_short_entry_signal(self, *args, **kwargs):
        self.short_called = True
        return self.short

    def calculate_confidence_score(self):
        return 80.0


def _config(**overrides):
    cfg = {
        "use_regime_detection": True,
        "regime_aware_entries": True,
        "skip_choppy_markets": True,
        "skip_trending_down_entries": True,
        "enable_short_entries": False,
        "use_confidence_gate": True,
        "min_confidence_score": 50.0,
        "primary_allocation": 3.0,
        "short_allocation": 3.0,
        "use_dynamic_sizing": False,
        "position_size_by_regime": False,
        "use_partial_scaling": True,
        "partial_scale_levels": ((0.25, 1.5), (0.25, 2.5), (0.25, 4.0)),
        "regime_scale_levels": {
            "TRENDING_UP": ((0.25, 2.0), (0.25, 3.5), (0.25, 6.0)),
            "RANGING": ((0.25, 1.5), (0.25, 2.5), (0.25, 4.0)),
        },
        "max_slippage_percent": 0.8,
    }
    cfg.update(overrides)
    return cfg


def _run_check(trader, indicators):
    return asyncio.get_event_loop().run_until_complete(
        trader.check_entry(100.0, indicators, available_capital=20.0, symbol="TEST")
    )


def test_bull_regime_uses_momentum_entry():
    ind = _FakeIndicators("TRENDING_UP", momentum=True)
    trader = Trader(_config(), _Risk(), simulate=True)

    assert _run_check(trader, ind) is True
    assert ind.momentum_called is True
    assert ind.meanrev_called is False
    assert trader.active_position.entry_regime == "TRENDING_UP"
    # Bull regime uses wider scale-out targets (3 levels).
    assert len(trader.active_position.scale_levels_hit) == 3


def test_bull_regime_can_be_configured_as_pullback():
    ind = _FakeIndicators("TRENDING_UP", meanrev=True)
    trader = Trader(_config(bull_entry_mode="pullback"), _Risk(), simulate=True)

    assert _run_check(trader, ind) is True
    assert ind.meanrev_called is True
    assert ind.momentum_called is False


def test_ranging_regime_uses_mean_reversion():
    ind = _FakeIndicators("RANGING", meanrev=True)
    trader = Trader(_config(), _Risk(), simulate=True)

    assert _run_check(trader, ind) is True
    assert ind.meanrev_called is True
    assert ind.momentum_called is False


def test_bear_regime_shorts_when_enabled():
    ind = _FakeIndicators("TRENDING_DOWN", short=True)
    trader = Trader(_config(enable_short_entries=True), _Risk(), simulate=True)

    assert _run_check(trader, ind) is True
    assert ind.short_called is True
    assert trader.active_position.side == "short"


def test_bear_regime_skips_long_when_shorts_disabled():
    ind = _FakeIndicators("TRENDING_DOWN", meanrev=True)
    trader = Trader(_config(enable_short_entries=False), _Risk(), simulate=True)

    assert _run_check(trader, ind) is False
    assert ind.short_called is False
    assert ind.meanrev_called is False
    assert trader.active_position is None


def test_choppy_regime_skips_everything():
    ind = _FakeIndicators("CHOPPY", momentum=True, meanrev=True, short=True)
    trader = Trader(_config(enable_short_entries=True), _Risk(), simulate=True)

    assert _run_check(trader, ind) is False
    assert not (ind.momentum_called or ind.meanrev_called or ind.short_called)


def _build(seq, last_volume=None):
    ind = TechnicalIndicators(enable_multi_timeframe=False)
    for i, price in enumerate(seq):
        volume = 1000.0
        if last_volume is not None and i == len(seq) - 1:
            volume = last_volume
        ind.add_price(price, volume)
    return ind


def test_momentum_signal_fires_in_uptrend_pullback_reclaim():
    seq = [100 + i * 0.6 for i in range(30)]
    start = seq[-1]
    seq += [start - 0.5 * (i + 1) for i in range(7)]
    seq += [seq[-1] + 0.9, seq[-1] + 1.8]
    ind = _build(seq, last_volume=1200.0)

    assert ind.detect_market_regime() == "TRENDING_UP"
    assert ind.is_momentum_entry_signal(seq[-1]) is True
    # Mean reversion should not fire in an uptrend reclaim.
    assert ind.is_entry_signal(seq[-1], rsi_min=25, rsi_max=35) is False


def test_mean_reversion_signal_fires_in_ranging_dip():
    seq = [100 + (0.3 if i % 2 == 0 else -0.3) for i in range(30)]
    seq += [100, 99.5, 99, 98.5, 98.2]
    ind = _build(seq, last_volume=1400.0)

    assert ind.detect_market_regime() == "RANGING"
    assert ind.is_entry_signal(seq[-1], rsi_min=25, rsi_max=40) is True
    assert ind.is_momentum_entry_signal(seq[-1]) is False


def test_exit_target_multiplier_widens_targets():
    seq = [100 + i * 0.6 for i in range(30)]
    ind = _build(seq)
    entry = 100.0

    base = ind.get_exit_levels(entry, target_multiplier=1.0)
    wide = ind.get_exit_levels(entry, target_multiplier=1.25)

    assert wide.tp1 > base.tp1
    assert wide.tp2 > base.tp2


def test_config_regime_defaults():
    cfg = StrategyConfig()
    assert cfg.regime_aware_entries is True
    assert cfg.bull_entry_mode == "momentum"
    assert cfg.range_entry_mode == "mean_reversion"
    assert cfg.regime_scale_levels["TRENDING_UP"][-1][1] > cfg.regime_scale_levels["RANGING"][-1][1]
