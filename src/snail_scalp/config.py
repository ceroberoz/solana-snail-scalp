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
    rsi_oversold_min: int = 25
    rsi_oversold_max: int = 35
    min_band_width_percent: float = 2.0  # Avoid flat markets

    # Entry settings
    primary_allocation: float = 3.0  # $3 first entry
    dca_allocation: float = 3.0  # $3 DCA if drops 1%
    dca_trigger_percent: float = 1.0

    # Exit settings
    tp1_percent: float = 2.5  # Sell 50%
    tp2_percent: float = 4.0  # Sell remaining 50%
    stop_loss_percent: float = 1.5


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
