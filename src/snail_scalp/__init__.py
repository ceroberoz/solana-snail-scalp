"""Solana Snail Scalp Bot - A conservative scalping strategy for Solana."""

__version__ = "1.0.0"
__author__ = "Solana Snail Scalp Bot"

from snail_scalp.config import (
    TradingConfig,
    StrategyConfig,
    APIConfig,
    trading_config,
    strategy_config,
    api_config,
    PAIR_ADDRESS,
    TOKEN_IN,
    TOKEN_OUT,
    SIMULATION_CONFIG,
)
from snail_scalp.data_feed import PriceData, DataFeed, SimulationDataFeed, HybridDataFeed
from snail_scalp.indicators import TechnicalIndicators, BollingerBands, ExitLevels
from snail_scalp.risk_manager import RiskManager, DailyStats
from snail_scalp.trader import Trader, Trade, TradeStatus, CloseReason

__all__ = [
    "TradingConfig",
    "StrategyConfig",
    "APIConfig",
    "trading_config",
    "strategy_config",
    "api_config",
    "PAIR_ADDRESS",
    "TOKEN_IN",
    "TOKEN_OUT",
    "SIMULATION_CONFIG",
    "PriceData",
    "DataFeed",
    "SimulationDataFeed",
    "HybridDataFeed",
    "TechnicalIndicators",
    "BollingerBands",
    "ExitLevels",
    "RiskManager",
    "DailyStats",
    "Trader",
    "Trade",
    "TradeStatus",
    "CloseReason",
]
