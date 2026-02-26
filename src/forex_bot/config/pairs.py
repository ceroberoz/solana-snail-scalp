"""Forex pair configuration for Phase 1 (USD/SGD) and Phase 2 (USD/MYR)"""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PairConfig:
    """Configuration for a forex pair"""
    
    # Identification
    name: str
    yahoo_ticker: str
    oanda_instrument: Optional[str]
    ibkr_symbol: Optional[str]
    
    # Phase & Priority
    phase: int  # 1 = Phase 1 (primary), 2 = Phase 2 (secondary)
    priority: str  # "primary", "secondary"
    
    # Trading Parameters
    timeframe: str  # "15m", "1h", etc.
    spread_max_pips: float
    target_pips: List[int]
    stop_pips: int
    max_hold_hours: int
    
    # Strategy Parameters
    bb_period: int
    bb_std: float
    rsi_period: int
    rsi_oversold_min: int
    rsi_oversold_max: int
    
    # Position Sizing
    pip_value_usd: float  # per micro lot (0.01)
    risk_per_trade_pct: float
    max_position_lots: float


# Phase 1: USD/SGD Configuration
USD_SGD = PairConfig(
    name="USD/SGD",
    yahoo_ticker="USDSGD=X",
    oanda_instrument="USD_SGD",
    ibkr_symbol=None,  # Use OANDA for SGD
    
    phase=1,
    priority="primary",
    
    # Trading - Optimized for 1h data (Yahoo limitation)
    timeframe="1h",
    spread_max_pips=5.0,
    target_pips=[25, 50, 80],  # Wider for trending markets
    stop_pips=25,
    max_hold_hours=48,  # Allow swing trades
    
    # Strategy
    bb_period=20,
    bb_std=2.0,
    rsi_period=14,
    rsi_oversold_min=20,
    rsi_oversold_max=40,
    
    # Risk - Standard
    pip_value_usd=0.074,  # ~$0.074 per pip per micro lot
    risk_per_trade_pct=2.0,
    max_position_lots=1.0,
)

# Phase 2: USD/MYR Configuration (for future)
USD_MYR = PairConfig(
    name="USD/MYR",
    yahoo_ticker="USDMYR=X",
    oanda_instrument=None,  # Not available on OANDA
    ibkr_symbol="USD.MYR",  # Interactive Brokers
    
    phase=2,
    priority="secondary",
    
    # Trading - Swing optimized (wider spreads)
    timeframe="1h",
    spread_max_pips=50.0,
    target_pips=[50, 100, 150],
    stop_pips=60,
    max_hold_hours=72,
    
    # Strategy - Wider bands for volatility
    bb_period=20,
    bb_std=2.5,
    rsi_period=14,
    rsi_oversold_min=20,
    rsi_oversold_max=40,
    
    # Risk - Lower (secondary pair)
    pip_value_usd=0.022,  # Approximate, verify with broker
    risk_per_trade_pct=1.5,
    max_position_lots=0.5,
)

# Active pairs by phase
ACTIVE_PAIRS_PHASE_1 = {
    "USD_SGD": USD_SGD,
}

ACTIVE_PAIRS_PHASE_2 = {
    "USD_SGD": USD_SGD,
    "USD_MYR": USD_MYR,
}


def get_pair_config(pair_code: str) -> PairConfig:
    """Get configuration for a specific pair"""
    pairs = ACTIVE_PAIRS_PHASE_2  # Use Phase 2 for lookup
    if pair_code not in pairs:
        raise ValueError(f"Unknown pair: {pair_code}")
    return pairs[pair_code]


def get_phase_1_pairs() -> dict:
    """Get Phase 1 pairs (USD/SGD only)"""
    return ACTIVE_PAIRS_PHASE_1


def get_phase_2_pairs() -> dict:
    """Get Phase 2 pairs (USD/SGD + USD/MYR)"""
    return ACTIVE_PAIRS_PHASE_2


# Portfolio configuration
PORTFOLIO_CONFIG = {
    "max_correlation": 0.85,
    "phase_1_allocation": {
        "USD_SGD": 1.0,  # 100%
    },
    "phase_2_allocation": {
        "USD_SGD": 0.70,  # 70%
        "USD_MYR": 0.30,  # 30%
    },
}
