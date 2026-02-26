"""Solana Snail Scalp Bot - A conservative scalping strategy for Solana."""

__version__ = "1.2.0"
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

# Token Screening (v1.1)
from snail_scalp.token_screener import (
    TokenScreener,
    TokenMetrics,
    HypeScore,
    HypeCategory,
    RiskLevel,
    TOP_SOLANA_COINS,
    create_demo_data,
)
from snail_scalp.sentiment_analysis import (
    SentimentAnalyzer,
    SocialMetrics,
    CommunityMetrics,
    OnChainSentiment,
    SentimentScore,
    SentimentType,
    SignalStrength,
    HypeCycleDetector,
)
from snail_scalp.multi_token_feed import (
    MultiTokenFeed,
    TokenData,
)

# Portfolio Management (v1.2)
from snail_scalp.portfolio_manager import (
    PortfolioManager,
    PortfolioState,
    TokenPosition,
    PositionStatus,
)
from snail_scalp.screening_bot import (
    ScreeningTradingBot,
    TokenTrader,
)
from snail_scalp.backtest_engine import (
    BacktestEngine,
    BacktestResult,
    run_backtest,
)

__all__ = [
    # Config
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
    # Data Feed
    "PriceData",
    "DataFeed",
    "SimulationDataFeed",
    "HybridDataFeed",
    # Indicators
    "TechnicalIndicators",
    "BollingerBands",
    "ExitLevels",
    # Risk
    "RiskManager",
    "DailyStats",
    # Trading
    "Trader",
    "Trade",
    "TradeStatus",
    "CloseReason",
    # Token Screening
    "TokenScreener",
    "TokenMetrics",
    "HypeScore",
    "HypeCategory",
    "RiskLevel",
    "TOP_SOLANA_COINS",
    "create_demo_data",
    # Sentiment Analysis
    "SentimentAnalyzer",
    "SocialMetrics",
    "CommunityMetrics",
    "OnChainSentiment",
    "SentimentScore",
    "SentimentType",
    "SignalStrength",
    "HypeCycleDetector",
    # Multi-Token Feed
    "MultiTokenFeed",
    "TokenData",
    # Portfolio Management (New in v1.2)
    "PortfolioManager",
    "PortfolioState",
    "TokenPosition",
    "PositionStatus",
    # Screening Bot (New in v1.2)
    "ScreeningTradingBot",
    "TokenTrader",
    # Backtest Engine (New in v1.2)
    "BacktestEngine",
    "BacktestResult",
    "run_backtest",
]
