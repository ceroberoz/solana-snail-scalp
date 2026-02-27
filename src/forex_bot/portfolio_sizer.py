"""Portfolio sizing optimization (M5.1)

M5.1: Portfolio Sizing
- Dynamic position sizing based on portfolio performance
- Kelly Criterion for optimal position sizing
- Volatility-based position adjustment
- Risk-adjusted allocation between pairs
- Portfolio heat monitoring
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SizingConfig:
    """Configuration for portfolio sizing"""

    # Kelly Criterion settings
    use_kelly: bool = True
    kelly_fraction: float = 0.5  # Half-Kelly for safety

    # Volatility adjustment
    use_volatility_adjustment: bool = True
    volatility_lookback: int = 20
    max_volatility_multiplier: float = 2.0
    min_volatility_multiplier: float = 0.5

    # Portfolio heat (total risk)
    max_portfolio_heat: float = 0.10  # Max 10% of capital at risk

    # Performance-based sizing
    use_performance_adjustment: bool = True
    winning_streak_boost: float = 1.2  # 20% boost after 3 wins
    losing_streak_reduction: float = 0.8  # 20% reduction after 3 losses

    # Pair allocation
    base_allocation: Dict[str, float] = None

    def __post_init__(self):
        if self.base_allocation is None:
            self.base_allocation = {"USD_SGD": 0.6, "USD_MYR": 0.4}


class PortfolioSizer:
    """
    M5.1: Advanced Portfolio Sizing

    Implements:
    1. Kelly Criterion for optimal position sizing
    2. Volatility-based adjustments
    3. Portfolio heat monitoring
    4. Performance-based sizing adjustments
    5. Dynamic pair allocation
    """

    def __init__(self, config: Optional[SizingConfig] = None):
        """
        Initialize portfolio sizer

        Args:
            config: Sizing configuration
        """
        self.config = config or SizingConfig()

        # Performance tracking
        self.trade_history: List[dict] = []
        self.current_streak: int = 0  # Positive for wins, negative for losses
        self.win_rate_20: float = 0.5  # 20-trade rolling win rate

        # Volatility tracking
        self.returns_history: Dict[str, List[float]] = {}

        logger.info("PortfolioSizer initialized")

    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly Criterion fraction

        Kelly % = W - [(1 - W) / R]
        Where:
        W = Win rate
        R = Win/Loss ratio

        Args:
            win_rate: Probability of winning (0-1)
            avg_win: Average win amount
            avg_loss: Average loss amount (positive number)

        Returns:
            Kelly fraction (0-1, or 0 if negative)
        """
        if avg_loss == 0:
            return 0

        win_loss_ratio = avg_win / avg_loss

        if win_loss_ratio <= 0:
            return 0

        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)

        # Apply fractional Kelly for safety
        kelly = kelly * self.config.kelly_fraction

        # Clamp to reasonable range
        return max(0, min(0.5, kelly))  # Max 50% of capital per trade

    def get_performance_multiplier(self) -> float:
        """
        Get position size multiplier based on recent performance

        Returns:
            Multiplier for position size
        """
        if not self.config.use_performance_adjustment:
            return 1.0

        # Streak-based adjustment
        if self.current_streak >= 3:
            # Winning streak - slightly increase size
            return self.config.winning_streak_boost
        elif self.current_streak <= -3:
            # Losing streak - reduce size
            return self.config.losing_streak_reduction

        return 1.0

    def get_volatility_multiplier(self, pair_code: str) -> float:
        """
        Get position size multiplier based on recent volatility

        Higher volatility = smaller positions
        Lower volatility = larger positions

        Args:
            pair_code: Pair to check

        Returns:
            Volatility multiplier
        """
        if not self.config.use_volatility_adjustment:
            return 1.0

        if pair_code not in self.returns_history:
            return 1.0

        returns = self.returns_history[pair_code]

        if len(returns) < self.config.volatility_lookback:
            return 1.0

        # Calculate current volatility (std of returns)
        current_vol = np.std(returns[-self.config.volatility_lookback :])

        # Calculate historical average volatility
        if len(returns) < self.config.volatility_lookback * 2:
            historical_vol = current_vol
        else:
            historical_vol = np.std(returns[: -self.config.volatility_lookback])

        if historical_vol == 0:
            return 1.0

        # Volatility ratio
        vol_ratio = current_vol / historical_vol

        # Inverse relationship: high vol = small size, low vol = large size
        if vol_ratio > 1.5:
            return self.config.min_volatility_multiplier  # High vol, reduce size
        elif vol_ratio < 0.5:
            return self.config.max_volatility_multiplier  # Low vol, increase size
        else:
            # Linear interpolation
            multiplier = 2 - vol_ratio
            return max(
                self.config.min_volatility_multiplier,
                min(self.config.max_volatility_multiplier, multiplier),
            )

    def calculate_position_size(
        self,
        pair_code: str,
        base_risk_pct: float,
        capital: float,
        stop_pips: float,
        pip_value: float,
    ) -> dict:
        """
        Calculate optimal position size

        Args:
            pair_code: Pair to trade
            base_risk_pct: Base risk percentage
            capital: Available capital
            stop_pips: Stop loss distance in pips
            pip_value: Value of 1 pip per micro lot

        Returns:
            Dictionary with sizing details
        """
        # Base calculation
        risk_amount = capital * (base_risk_pct / 100)
        base_micro_lots = risk_amount / (stop_pips * pip_value)

        # Get multipliers
        performance_mult = self.get_performance_multiplier()
        volatility_mult = self.get_volatility_multiplier(pair_code)

        # Calculate Kelly fraction if enabled
        kelly_mult = 1.0
        if self.config.use_kelly and len(self.trade_history) >= 10:
            recent_trades = self.trade_history[-20:]
            wins = [t for t in recent_trades if t["pnl"] > 0]
            losses = [t for t in recent_trades if t["pnl"] <= 0]

            if wins and losses:
                win_rate = len(wins) / len(recent_trades)
                avg_win = sum(t["pnl"] for t in wins) / len(wins)
                avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses))

                kelly = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
                # Convert Kelly to multiplier (Kelly of 0.25 = 1.0x, 0.125 = 0.5x)
                kelly_mult = min(2.0, max(0.5, kelly * 4))

        # Apply all multipliers
        adjusted_micro_lots = base_micro_lots * performance_mult * volatility_mult * kelly_mult

        # Check portfolio heat
        total_risk = self.calculate_total_risk(pair_code, adjusted_micro_lots, stop_pips, pip_value)
        if total_risk > capital * self.config.max_portfolio_heat:
            # Reduce size to stay within heat limit
            max_risk = capital * self.config.max_portfolio_heat
            adjusted_micro_lots = max_risk / (stop_pips * pip_value)

        # Convert to standard lots
        lots = adjusted_micro_lots / 100

        return {
            "lots": round(lots, 2),
            "micro_lots": round(adjusted_micro_lots, 2),
            "risk_amount": risk_amount,
            "base_lots": round(base_micro_lots / 100, 2),
            "performance_mult": performance_mult,
            "volatility_mult": volatility_mult,
            "kelly_mult": kelly_mult,
            "total_multiplier": round(performance_mult * volatility_mult * kelly_mult, 2),
        }

    def calculate_total_risk(
        self, new_pair: str, new_micro_lots: float, new_stop_pips: float, pip_value: float
    ) -> float:
        """
        Calculate total portfolio risk with new position

        Args:
            new_pair: New pair to trade
            new_micro_lots: Position size in micro lots
            new_stop_pips: Stop distance
            pip_value: Pip value

        Returns:
            Total risk amount
        """
        # This is a simplified calculation
        new_risk = new_micro_lots * new_stop_pips * pip_value
        return new_risk

    def record_trade(self, pair_code: str, pnl: float, timestamp: datetime):
        """
        Record a trade for performance tracking

        Args:
            pair_code: Pair traded
            pnl: Profit/loss amount
            timestamp: Trade timestamp
        """
        self.trade_history.append(
            {
                "pair": pair_code,
                "pnl": pnl,
                "timestamp": timestamp,
            }
        )

        # Update streak
        if pnl > 0:
            if self.current_streak > 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
        else:
            if self.current_streak < 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1

        # Update win rate
        if len(self.trade_history) >= 20:
            recent = self.trade_history[-20:]
            wins = len([t for t in recent if t["pnl"] > 0])
            self.win_rate_20 = wins / 20

    def record_return(self, pair_code: str, ret: float):
        """
        Record return for volatility calculation

        Args:
            pair_code: Pair code
            ret: Return value (e.g., 0.001 for 0.1%)
        """
        if pair_code not in self.returns_history:
            self.returns_history[pair_code] = []

        self.returns_history[pair_code].append(ret)

        # Keep only last 100 returns
        if len(self.returns_history[pair_code]) > 100:
            self.returns_history[pair_code] = self.returns_history[pair_code][-100:]

    def get_sizing_summary(self) -> dict:
        """
        Get summary of current sizing parameters

        Returns:
            Dictionary with sizing info
        """
        return {
            "current_streak": self.current_streak,
            "win_rate_20": round(self.win_rate_20, 2),
            "total_trades": len(self.trade_history),
            "performance_multiplier": self.get_performance_multiplier(),
        }

    def print_sizing_info(self):
        """Print current sizing information"""
        summary = self.get_sizing_summary()

        print("\n📊 Portfolio Sizing (M5.1)")
        print("-" * 40)
        print(f"Win Rate (20): {summary['win_rate_20']:.1%}")
        print(f"Current Streak: {summary['current_streak']:+d}")
        print(f"Performance Mult: {summary['performance_multiplier']:.1f}x")
        print(f"Total Trades: {summary['total_trades']}")

        if self.config.use_kelly:
            print(f"Kelly Fraction: {self.config.kelly_fraction:.0%}")

        print("-" * 40)


def create_portfolio_sizer(
    use_kelly: bool = True,
    kelly_fraction: float = 0.5,
    use_volatility: bool = True,
) -> PortfolioSizer:
    """
    Factory function to create a PortfolioSizer

    Args:
        use_kelly: Enable Kelly Criterion
        kelly_fraction: Kelly fraction (0.5 = Half-Kelly)
        use_volatility: Enable volatility adjustment

    Returns:
        Configured PortfolioSizer
    """
    config = SizingConfig(
        use_kelly=use_kelly,
        kelly_fraction=kelly_fraction,
        use_volatility_adjustment=use_volatility,
    )

    return PortfolioSizer(config)
