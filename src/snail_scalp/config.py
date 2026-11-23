"""Configuration - ADJUST THESE BEFORE TRADING"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class TradingConfig:
    initial_capital: float = 20.0  # USD
    max_position_usd: float = 6.0  # 30% max ($6)
    emergency_reserve: float = 4.0  # 20% ($4)
    vault_reserve: float = 10.0  # 50% untouchable

    # Trading window (UTC)
    trading_start_utc: int = 9  # 09:00 UTC
    trading_end_utc: int = 11  # 11:00 UTC

    # Risk limits
    daily_loss_limit_usd: float = 1.50  # 7.5% of capital
    max_consecutive_losses: int = 2
    max_slippage_percent: float = 0.8  # Abort if slippage >0.8%


@dataclass
class StrategyConfig:
    check_interval_seconds: int = 300  # 5 minutes
    bb_period: int = 20
    bb_std: float = 2.0
    rsi_period: int = 14
    rsi_oversold_min: int = 20
    rsi_oversold_max: int = 40
    min_band_width_percent: float = 2.0  # Avoid flat markets

    # Entry settings
    primary_allocation: float = 3.0  # $3 first entry
    dca_allocation_ratio: float = 0.5  # DCA size = 50% of original position
    dca_trigger_percent: float = 1.0

    # Exit settings
    # US-2.4: Dynamic Profit Targets using ATR
    use_atr_targets: bool = True  # Enable ATR-based profit targets
    tp1_atr_multiplier: float = 1.0  # TP1 = Entry + (ATR * 1.0)
    tp2_atr_multiplier: float = 2.0  # TP2 = Entry + (ATR * 2.0)
    tp_min_percent: float = 2.0  # Minimum 2% profit target
    tp_max_percent: float = 8.0  # Maximum 8% profit target
    
    # Legacy percent-based (fallback if ATR disabled)
    tp1_percent: float = 2.5  # Sell 50%
    tp2_percent: float = 4.0  # Sell remaining 50%
    
    # US-2.1: ATR-based stops
    stop_loss_atr_multiplier: float = 1.5  # Stop = Entry - (ATR * 1.5)
    stop_loss_max_percent: float = 3.0  # Max stop capped at 3%
    use_atr_stop: bool = True  # Enable ATR-based stops
    
    # US-2.2: Breakeven stop after TP1
    use_breakeven_stop: bool = True  # Move stop to entry+fees after TP1
    breakeven_buffer_percent: float = 0.1  # Small buffer for fees
    
    # US-2.3: Trailing stop after TP1
    use_trailing_stop: bool = True  # Enable trailing stop after TP1
    trailing_stop_percent: float = 1.0  # Trail at 1% below recent high
    trailing_update_interval: int = 300  # Update every 5 minutes (seconds)
    
    # US-2.5: Time-based exit
    max_hold_time_minutes: int = 120  # Max 2 hours hold time
    use_time_exit: bool = True  # Enable time-based exit
    
    # US-2.6: Partial Profit Scaling
    use_partial_scaling: bool = True  # Enable 25%, 50%, 75%, final trailing
    partial_scale_levels: tuple = ((0.25, 1.5), (0.25, 2.5), (0.25, 4.0))  # (portion, profit%)
    final_trailing_after_scale: bool = True  # Use trailing for final 25%
    
    # US-3.2: Dynamic Position Sizing
    use_dynamic_sizing: bool = True  # Enable confidence-based sizing
    min_position_ratio: float = 0.5  # Minimum 50% of base size
    max_position_ratio: float = 1.5  # Maximum 150% of base size
    confidence_rsi_weight: float = 0.4  # 40% weight on RSI depth
    confidence_volume_weight: float = 0.3  # 30% weight on volume
    confidence_bb_weight: float = 0.3  # 30% weight on BB width

    # US-3.2: Confidence gating
    use_confidence_gate: bool = True  # Skip entries below min confidence
    min_confidence_score: float = 50.0  # Minimum confidence to enter
    
    # US-3.3: Correlation Risk Management
    use_correlation_check: bool = True  # Enable correlation risk management
    max_correlated_positions: int = 2  # Max 2 correlated positions
    correlation_threshold: float = 0.7  # Correlation > 0.7 = correlated
    correlation_lookback: int = 20  # Lookback period for correlation
    
    # US-1.5: Market Regime Detection
    use_regime_detection: bool = True  # Enable market regime detection
    regime_adx_threshold: float = 25.0  # ADX > 25 = trending
    regime_lookback: int = 14  # Lookback for regime calc
    skip_choppy_markets: bool = True  # Skip trades when choppy
    skip_trending_down_entries: bool = True  # Skip long entries in TRENDING_DOWN regime
    position_size_by_regime: bool = True  # Adjust size by regime
    regime_size_multiplier: dict = None  # Will be set in __post_init__

    def __post_init__(self):
        if self.regime_size_multiplier is None:
            self.regime_size_multiplier = {
                "TRENDING_UP": 1.2,
                "TRENDING_DOWN": 0.7,
                "RANGING": 1.0,
                "CHOPPY": 0.6,
            }
        # Backwards-compatible aliases
        if not hasattr(self, "_dca_allocation"):
            pass

    # Backwards-compatible aliases for older code paths
    @property
    def dca_allocation(self) -> float:
        return self.dca_allocation_ratio

    @dca_allocation.setter
    def dca_allocation(self, value: float):
        self.dca_allocation_ratio = value

    @property
    def stop_loss_percent(self) -> float:
        return self.stop_loss_max_percent

    @stop_loss_percent.setter
    def stop_loss_percent(self, value: float):
        self.stop_loss_max_percent = value


@dataclass
class APIConfig:
    dexscreener: str = "https://api.dexscreener.com/latest/dex/pairs/solana/{pair}"
    jupiter_quote: str = "https://quote-api.jup.ag/v6/quote"
    jupiter_swap: str = "https://quote-api.jup.ag/v6/swap"
    rpc: str = "https://solana-mainnet.rpc.extrnode.com"  # Free public - REPLACE WITH YOURS


# SOL/USDC Raydium Pair (Update address if needed)
PAIR_ADDRESS = os.getenv("PAIR_ADDRESS", "8sLbNZoY3HWP8krpPjWBP1u3ZcD7nRRd6m8vPWH6Y5Pq")
TOKEN_IN = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
TOKEN_OUT = "So11111111111111111111111111111111111111112"  # SOL

# Simulation settings
SIMULATION_CONFIG = {
    "log_file": "data/sample_price_data.csv",  # Default log file for simulation
    "speed_multiplier": 1.0,  # 1.0 = real-time, 10.0 = 10x faster
    "save_results": True,  # Save simulation results to file
    "results_file": "data/simulation_results.json",
}

def apply_profile(profile: str = "default"):
    """Apply a named risk/strategy profile to the global config instances (in place)."""
    global trading_config, strategy_config

    if profile == "default":
        defaults_t = TradingConfig()
        defaults_s = StrategyConfig()
        trading_config.__dict__.update(defaults_t.__dict__)
        strategy_config.__dict__.update(defaults_s.__dict__)
        return

    if profile == "balanced":
        trading_config.max_position_usd = 8.0
        trading_config.emergency_reserve = 3.0
        trading_config.daily_loss_limit_usd = 2.00
        trading_config.max_consecutive_losses = 4
        trading_config.max_slippage_percent = 1.0
        trading_config.trading_start_utc = 8
        trading_config.trading_end_utc = 22
        strategy_config.rsi_oversold_min = 18
        strategy_config.rsi_oversold_max = 42
        strategy_config.min_band_width_percent = 1.5
        strategy_config.primary_allocation = 4.0
        strategy_config.dca_allocation_ratio = 0.6
        strategy_config.dca_trigger_percent = 0.75
        strategy_config.tp1_percent = 2.0
        strategy_config.tp2_percent = 3.5
        strategy_config.stop_loss_max_percent = 4.0
        strategy_config.stop_loss_atr_multiplier = 1.75
        strategy_config.use_breakeven_stop = True
        strategy_config.use_trailing_stop = True
        strategy_config.trailing_stop_percent = 1.5
        strategy_config.max_hold_time_minutes = 180
        strategy_config.use_time_exit = True
        strategy_config.use_partial_scaling = True
        strategy_config.min_position_ratio = 0.6
        strategy_config.max_position_ratio = 1.75
        strategy_config.use_correlation_check = True
        strategy_config.max_correlated_positions = 2
        strategy_config.correlation_threshold = 0.8
        strategy_config.use_regime_detection = True
        strategy_config.skip_choppy_markets = True
        strategy_config.skip_trending_down_entries = True
        strategy_config.position_size_by_regime = True
        strategy_config.min_confidence_score = 60.0
        strategy_config.regime_size_multiplier = {
            "TRENDING_UP": 1.2,
            "TRENDING_DOWN": 0.7,
            "RANGING": 1.0,
            "CHOPPY": 0.6,
        }
        return

    if profile == "aggressive":
        # Trading config
        trading_config.max_position_usd = 10.0
        trading_config.emergency_reserve = 2.0
        trading_config.daily_loss_limit_usd = 3.00
        trading_config.max_consecutive_losses = 5
        trading_config.max_slippage_percent = 1.5
        trading_config.trading_start_utc = 0
        trading_config.trading_end_utc = 23
        # Strategy config
        strategy_config.rsi_oversold_min = 15
        strategy_config.rsi_oversold_max = 45
        strategy_config.min_band_width_percent = 1.0
        strategy_config.primary_allocation = 5.0
        strategy_config.dca_allocation_ratio = 0.75
        strategy_config.dca_trigger_percent = 0.5
        strategy_config.tp1_percent = 1.5
        strategy_config.tp2_percent = 3.0
        strategy_config.stop_loss_max_percent = 5.0
        strategy_config.stop_loss_atr_multiplier = 2.0
        strategy_config.use_breakeven_stop = False
        strategy_config.use_trailing_stop = True
        strategy_config.trailing_stop_percent = 2.0
        strategy_config.max_hold_time_minutes = 240
        strategy_config.use_time_exit = False
        strategy_config.use_partial_scaling = True
        strategy_config.min_position_ratio = 0.75
        strategy_config.max_position_ratio = 2.0
        strategy_config.use_correlation_check = True
        strategy_config.max_correlated_positions = 3
        strategy_config.correlation_threshold = 0.85
        strategy_config.use_regime_detection = True
        strategy_config.skip_choppy_markets = False
        strategy_config.skip_trending_down_entries = False
        strategy_config.min_confidence_score = 50.0
        strategy_config.position_size_by_regime = True
        strategy_config.regime_size_multiplier = {
            "TRENDING_UP": 1.2,
            "TRENDING_DOWN": 0.7,
            "RANGING": 1.0,
            "CHOPPY": 0.6,
        }
        return

    raise ValueError(f"Unknown profile: {profile}")


# Global config instances
trading_config = TradingConfig()
strategy_config = StrategyConfig()
api_config = APIConfig()
