"""Multi-pair portfolio manager for forex trading (M1.2, M1.4)

M1.2: Multi-Pair Architecture
- Manage multiple currency pairs simultaneously
- Capital allocation across pairs
- Max concurrent positions limit

M1.4: Correlation Monitor
- Track correlation between pairs
- Avoid correlated positions
- Reduce risk when pairs move together
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open position in a pair"""

    pair_code: str
    entry_time: datetime
    entry_price: float
    size_lots: float
    stop_price: float
    targets: List[float]

    # Tracking
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False

    def __post_init__(self):
        if not hasattr(self, "scale_levels_hit"):
            self.scale_levels_hit = [False] * len(self.targets)


@dataclass
class PortfolioState:
    """Current state of the portfolio"""

    capital: float
    positions: Dict[str, Position] = field(default_factory=dict)
    pair_allocations: Dict[str, float] = field(default_factory=dict)
    correlation_matrix: Optional[pd.DataFrame] = None

    @property
    def total_exposure(self) -> float:
        """Total position exposure in lots"""
        return sum(pos.size_lots for pos in self.positions.values())

    @property
    def open_pairs(self) -> List[str]:
        """List of pairs with open positions"""
        return list(self.positions.keys())

    @property
    def num_positions(self) -> int:
        """Number of open positions"""
        return len(self.positions)


class CorrelationMonitor:
    """
    M1.4: Monitor correlation between currency pairs

    Features:
    - Calculate rolling correlation between pairs
    - Alert when correlation exceeds threshold
    - Block new positions in correlated pairs
    """

    def __init__(self, lookback_periods: int = 20, threshold: float = 0.85):
        """
        Initialize correlation monitor

        Args:
            lookback_periods: Number of periods for correlation calculation
            threshold: Correlation threshold (0-1)
        """
        self.lookback = lookback_periods
        self.threshold = threshold
        self.price_history: Dict[str, pd.Series] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None

        logger.info(
            f"CorrelationMonitor initialized (lookback={lookback_periods}, threshold={threshold})"
        )

    def update_price(self, pair_code: str, timestamp: datetime, price: float):
        """
        Update price history for a pair

        Args:
            pair_code: Pair identifier
            timestamp: Price timestamp
            price: Close price
        """
        if pair_code not in self.price_history:
            self.price_history[pair_code] = pd.Series(dtype=float)

        self.price_history[pair_code][timestamp] = price

        # Keep only recent history
        if len(self.price_history[pair_code]) > self.lookback * 2:
            self.price_history[pair_code] = self.price_history[pair_code].iloc[-self.lookback * 2 :]

    def calculate_correlation(self) -> Optional[pd.DataFrame]:
        """
        Calculate correlation matrix between all pairs

        Returns:
            Correlation matrix DataFrame or None if insufficient data
        """
        if len(self.price_history) < 2:
            return None

        # Align all series to common timestamps
        df = pd.DataFrame(self.price_history)

        # Need at least lookback periods of overlapping data
        if len(df) < self.lookback:
            return None

        # Use returns for correlation (more meaningful)
        returns = df.pct_change().dropna()

        # Calculate rolling correlation if we have enough data
        if len(returns) >= self.lookback:
            # Use last lookback periods
            recent_returns = returns.iloc[-self.lookback :]
            self.correlation_matrix = recent_returns.corr()
            return self.correlation_matrix

        return None

    def are_correlated(self, pair1: str, pair2: str) -> bool:
        """
        Check if two pairs are currently correlated

        Args:
            pair1: First pair code
            pair2: Second pair code

        Returns:
            True if correlation exceeds threshold
        """
        corr_matrix = self.calculate_correlation()

        if corr_matrix is None:
            return False

        if pair1 not in corr_matrix.columns or pair2 not in corr_matrix.columns:
            return False

        correlation = abs(corr_matrix.loc[pair1, pair2])
        return correlation > self.threshold

    def get_correlation(self, pair1: str, pair2: str) -> Optional[float]:
        """
        Get correlation between two pairs

        Args:
            pair1: First pair code
            pair2: Second pair code

        Returns:
            Correlation coefficient or None
        """
        corr_matrix = self.calculate_correlation()

        if corr_matrix is None:
            return None

        if pair1 not in corr_matrix.columns or pair2 not in corr_matrix.columns:
            return None

        return corr_matrix.loc[pair1, pair2]

    def get_correlated_pairs(self, pair_code: str) -> List[str]:
        """
        Get list of pairs that are correlated with given pair

        Args:
            pair_code: Pair to check

        Returns:
            List of correlated pair codes
        """
        corr_matrix = self.calculate_correlation()

        if corr_matrix is None or pair_code not in corr_matrix.columns:
            return []

        correlations = corr_matrix[pair_code].abs()
        correlated = correlations[correlations > self.threshold].index.tolist()
        correlated.remove(pair_code)  # Remove self

        return correlated


class PortfolioManager:
    """
    M1.2: Multi-Pair Portfolio Manager

    Manages multiple currency pairs with:
    - Capital allocation per pair
    - Maximum concurrent positions
    - Correlation-based risk management
    - Position tracking across pairs
    """

    def __init__(
        self,
        initial_capital: float,
        pair_configs: Dict[str, dict],
        max_positions: int = 2,
        enable_correlation_check: bool = True,
        correlation_threshold: float = 0.85,
    ):
        """
        Initialize portfolio manager

        Args:
            initial_capital: Starting capital in USD
            pair_configs: Dict of pair_code -> config dict
            max_positions: Maximum number of concurrent positions
            enable_correlation_check: Enable M1.4 correlation monitoring
            correlation_threshold: Correlation threshold for blocking trades
        """
        self.initial_capital = initial_capital
        self.pair_configs = pair_configs
        self.max_positions = max_positions

        # Portfolio state
        self.state = PortfolioState(
            capital=initial_capital, pair_allocations=self._calculate_allocations()
        )

        # Correlation monitoring (M1.4)
        self.enable_correlation = enable_correlation_check
        self.correlation_monitor = (
            CorrelationMonitor(threshold=correlation_threshold)
            if enable_correlation_check
            else None
        )

        # Performance tracking
        self.total_pnl = 0.0
        self.trade_history: List[dict] = []

        logger.info(f"PortfolioManager initialized")
        logger.info(f"  Capital: ${initial_capital:,.2f}")
        logger.info(f"  Max positions: {max_positions}")
        logger.info(f"  Pairs: {list(pair_configs.keys())}")
        logger.info(f"  Correlation check: {enable_correlation_check}")

    def _calculate_allocations(self) -> Dict[str, float]:
        """Calculate capital allocation per pair"""
        allocations = {}
        total_allocation = sum(
            config.get("portfolio_allocation", 1.0 / len(self.pair_configs))
            for config in self.pair_configs.values()
        )

        for pair_code, config in self.pair_configs.items():
            allocation = config.get("portfolio_allocation", 1.0 / len(self.pair_configs))
            allocations[pair_code] = allocation / total_allocation

        return allocations

    def can_open_position(self, pair_code: str, current_time: datetime) -> tuple[bool, str]:
        """
        Check if a new position can be opened

        Args:
            pair_code: Pair to trade
            current_time: Current timestamp

        Returns:
            (can_trade, reason)
        """
        # Check if pair is valid
        if pair_code not in self.pair_configs:
            return False, f"Invalid pair: {pair_code}"

        # Check max positions
        if self.state.num_positions >= self.max_positions:
            return False, f"Max positions reached ({self.max_positions})"

        # Check if already have position in this pair
        if pair_code in self.state.positions:
            return False, f"Already have position in {pair_code}"

        # Check correlation (M1.4)
        if self.enable_correlation and self.correlation_monitor:
            for open_pair in self.state.open_pairs:
                if self.correlation_monitor.are_correlated(pair_code, open_pair):
                    corr = self.correlation_monitor.get_correlation(pair_code, open_pair)
                    return False, f"Correlated with {open_pair} (r={corr:.2f})"

        return True, "OK"

    def open_position(
        self,
        pair_code: str,
        entry_time: datetime,
        entry_price: float,
        size_lots: float,
        stop_price: float,
        targets: List[float],
    ) -> bool:
        """
        Open a new position

        Args:
            pair_code: Pair to trade
            entry_time: Entry timestamp
            entry_price: Entry price
            size_lots: Position size in lots
            stop_price: Stop loss price
            targets: List of profit targets

        Returns:
            True if position opened successfully
        """
        can_trade, reason = self.can_open_position(pair_code, entry_time)

        if not can_trade:
            logger.warning(f"Cannot open position in {pair_code}: {reason}")
            return False

        position = Position(
            pair_code=pair_code,
            entry_time=entry_time,
            entry_price=entry_price,
            size_lots=size_lots,
            stop_price=stop_price,
            targets=targets,
        )

        self.state.positions[pair_code] = position

        logger.info(f"Opened position in {pair_code}: {size_lots:.2f} lots @ {entry_price:.5f}")

        return True

    def close_position(
        self, pair_code: str, exit_time: datetime, exit_price: float, reason: str
    ) -> Optional[float]:
        """
        Close a position

        Args:
            pair_code: Pair to close
            exit_time: Exit timestamp
            exit_price: Exit price
            reason: Close reason

        Returns:
            PnL in USD or None if position not found
        """
        if pair_code not in self.state.positions:
            return None

        position = self.state.positions[pair_code]

        # Calculate PnL
        pip_size = 0.0001
        pip_value = self.pair_configs[pair_code].get("pip_value_usd", 0.1)

        pips = (exit_price - position.entry_price) / pip_size
        pnl = pips * pip_value * (position.size_lots * 100)

        # Update capital
        self.state.capital += pnl
        self.total_pnl += pnl

        # Record trade
        self.trade_history.append(
            {
                "pair": pair_code,
                "entry_time": position.entry_time,
                "exit_time": exit_time,
                "entry_price": position.entry_price,
                "exit_price": exit_price,
                "size_lots": position.size_lots,
                "pips": pips,
                "pnl": pnl,
                "reason": reason,
            }
        )

        # Remove position
        del self.state.positions[pair_code]

        logger.info(f"Closed {pair_code}: {pips:+.1f} pips (${pnl:+.2f}) - {reason}")

        return pnl

    def update_correlation(self, pair_code: str, timestamp: datetime, price: float):
        """Update correlation data (M1.4)"""
        if self.correlation_monitor:
            self.correlation_monitor.update_price(pair_code, timestamp, price)

    def get_position(self, pair_code: str) -> Optional[Position]:
        """Get position for a pair"""
        return self.state.positions.get(pair_code)

    def has_position(self, pair_code: str) -> bool:
        """Check if we have a position in a pair"""
        return pair_code in self.state.positions

    def get_available_capital(self, pair_code: str) -> float:
        """
        Get available capital for a specific pair

        Args:
            pair_code: Pair to check

        Returns:
            Available capital in USD
        """
        allocation = self.state.pair_allocations.get(pair_code, 0.5)
        pair_capital = self.state.capital * allocation

        # Subtract capital tied up in other positions
        # (simplified - assumes equal capital usage per position)
        if self.state.num_positions > 0:
            used_capital = sum(
                pos.size_lots * 100_000 * pos.entry_price / 30  # Approximate margin
                for pos in self.state.positions.values()
            )
            return max(0, self.state.capital - used_capital) * allocation

        return pair_capital

    def get_statistics(self) -> dict:
        """Get portfolio statistics"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "current_capital": self.state.capital,
                "return_pct": 0.0,
            }

        winning = [t for t in self.trade_history if t["pnl"] > 0]
        losing = [t for t in self.trade_history if t["pnl"] <= 0]

        total_pnl = sum(t["pnl"] for t in self.trade_history)

        return {
            "total_trades": len(self.trade_history),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(self.trade_history) * 100,
            "total_pnl": total_pnl,
            "current_capital": self.state.capital,
            "return_pct": (self.state.capital / self.initial_capital - 1) * 100,
            "open_positions": len(self.state.positions),
        }

    def print_summary(self):
        """Print portfolio summary"""
        stats = self.get_statistics()

        print("\n" + "=" * 60)
        print("PORTFOLIO SUMMARY")
        print("=" * 60)

        print(f"\n💰 Capital:")
        print(f"   Initial: ${self.initial_capital:,.2f}")
        print(f"   Current: ${stats['current_capital']:,.2f}")
        print(f"   Return: {stats['return_pct']:+.2f}%")

        print(f"\n📊 Trading Statistics:")
        print(f"   Total Trades: {stats['total_trades']}")
        print(f"   Winning: {stats['winning_trades']}")
        print(f"   Losing: {stats['losing_trades']}")
        print(f"   Win Rate: {stats['win_rate']:.1f}%")
        print(f"   Total P&L: ${stats['total_pnl']:+.2f}")

        print(f"\n📈 Open Positions: {stats['open_positions']}/{self.max_positions}")
        for pair_code, pos in self.state.positions.items():
            print(f"   {pair_code}: {pos.size_lots:.2f} lots @ {pos.entry_price:.5f}")

        # Correlation info (M1.4)
        if self.enable_correlation and self.correlation_monitor:
            corr_matrix = self.correlation_monitor.calculate_correlation()
            if corr_matrix is not None:
                print(f"\n🔗 Correlation Matrix:")
                print(corr_matrix.to_string())

        print("=" * 60)


def create_portfolio_manager(
    initial_capital: float,
    pair_configs: Dict[str, dict],
    max_positions: int = 2,
) -> PortfolioManager:
    """
    Factory function to create a PortfolioManager

    Args:
        initial_capital: Starting capital
        pair_configs: Configuration for each pair
        max_positions: Maximum concurrent positions

    Returns:
        Configured PortfolioManager
    """
    return PortfolioManager(
        initial_capital=initial_capital,
        pair_configs=pair_configs,
        max_positions=max_positions,
        enable_correlation_check=True,
        correlation_threshold=0.85,
    )
