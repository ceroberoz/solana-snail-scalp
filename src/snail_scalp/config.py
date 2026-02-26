"""Configuration - ADJUST THESE BEFORE TRADING"""

import os
from dataclasses import dataclass
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

# Global config instances
trading_config = TradingConfig()
strategy_config = StrategyConfig()
api_config = APIConfig()
