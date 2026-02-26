"""Backtest engine for forex strategies"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

import pandas as pd
import numpy as np

from .indicators import ForexIndicators
from .position_sizing import calculate_position_size, PositionSize


logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"


class CloseReason(Enum):
    TP1 = "tp1"
    TP2 = "tp2"
    TP3 = "tp3"
    STOP_LOSS = "stop_loss"
    BREAKEVEN = "breakeven"
    TIME_EXIT = "time_exit"


@dataclass
class Trade:
    """Record of a single trade"""
    entry_time: datetime
    entry_price: float
    size_lots: float
    stop_price: float
    targets: List[float]
    
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    close_reason: Optional[CloseReason] = None
    
    # Partial exits
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    
    # PnL tracking
    pips: float = 0.0
    pnl_usd: float = 0.0
    
    # Scale tracking
    scale_levels_hit: List[bool] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.scale_levels_hit:
            self.scale_levels_hit = [False] * len(self.targets)
    
    @property
    def is_open(self) -> bool:
        return self.exit_time is None
    
    @property
    def duration_hours(self) -> float:
        if self.exit_time is None:
            return 0
        return (self.exit_time - self.entry_time).total_seconds() / 3600


@dataclass
class BacktestResult:
    """Results of backtest run"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    total_pips: float
    avg_pips_per_trade: float
    avg_win_pips: float
    avg_loss_pips: float
    
    total_pnl_usd: float
    max_drawdown_pips: float
    max_drawdown_pct: float
    
    avg_trade_duration: float
    
    trades: List[Trade]
    equity_curve: pd.DataFrame
    
    def print_summary(self):
        """Print formatted summary"""
        print("\n" + "="*60)
        print("BACKTEST RESULTS - USD/SGD")
        print("="*60)
        
        print(f"\n📊 Trade Statistics:")
        print(f"   Total Trades: {self.total_trades}")
        print(f"   Winning: {self.winning_trades} ({self.win_rate:.1f}%)")
        print(f"   Losing: {self.losing_trades}")
        
        print(f"\n📈 Performance (Pips):")
        print(f"   Total: {self.total_pips:+.1f} pips")
        print(f"   Average per trade: {self.avg_pips_per_trade:+.1f}")
        print(f"   Average win: {self.avg_win_pips:+.1f}")
        print(f"   Average loss: {self.avg_loss_pips:+.1f}")
        
        print(f"\n💰 P&L (USD):")
        print(f"   Total P&L: ${self.total_pnl_usd:+.2f}")
        
        print(f"\n⚠️ Risk Metrics:")
        print(f"   Max Drawdown: {self.max_drawdown_pips:.1f} pips ({self.max_drawdown_pct:.1f}%)")
        print(f"   Average Duration: {self.avg_trade_duration:.1f} hours")
        
        print("\n" + "="*60)


class ForexBacktest:
    """
    Event-driven backtest engine for forex strategies
    
    Features:
    - Walk-forward simulation
    - Partial profit taking
    - Breakeven stops
    - Time-based exits
    """
    
    def __init__(
        self,
        df: pd.DataFrame,
        pair_config: dict,
        initial_capital: float = 1000.0,
        risk_per_trade_pct: float = 2.0,
        verbose: bool = False,
    ):
        """
        Initialize backtest
        
        Args:
            df: OHLCV DataFrame with DatetimeIndex
            pair_config: Pair configuration dict
            initial_capital: Starting capital in USD
            risk_per_trade_pct: Risk per trade as % of capital
            verbose: Print detailed trade info
        """
        self.df = df.copy()
        self.config = pair_config
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.verbose = verbose
        
        # Pip value for USD/SGD
        self.pip_size = 0.0001
        self.pip_value_per_micro_lot = pair_config.get('pip_value_usd', 0.074)
        
        # State
        self.capital = initial_capital
        self.trades: List[Trade] = []
        self.active_trade: Optional[Trade] = None
        self.equity_curve: List[Dict] = []
        
        # Statistics
        self.total_pips = 0.0
        self.max_capital = initial_capital
        self.max_drawdown = 0.0
        
    def calculate_position_size(self, entry: float, stop: float) -> PositionSize:
        """Calculate position size using position sizing module"""
        from .position_sizing import calculate_position_size
        
        return calculate_position_size(
            account_balance=self.capital,
            entry_price=entry,
            stop_price=stop,
            pair_code="USD_SGD",  # Phase 1 only
            risk_pct=self.risk_per_trade_pct,
        )
    
    def run(self) -> BacktestResult:
        """Run the backtest simulation"""
        logger.info(f"Starting backtest with {len(self.df)} bars")
        
        # Lookback period for indicators
        lookback = 50
        
        for i in range(lookback, len(self.df)):
            # Get current bar
            current_bar = self.df.iloc[i]
            current_time = self.df.index[i]
            current_price = current_bar['Close']
            
            # Get indicator data (lookback window)
            window = self.df.iloc[i-lookback:i+1]
            indicators = ForexIndicators(window)
            
            # Manage active trade
            if self.active_trade is not None:
                self._manage_position(
                    current_time, current_price, current_bar
                )
            else:
                # Look for entry
                self._check_entry(
                    current_time, current_price, indicators
                )
            
            # Record equity
            self._update_equity(current_time)
        
        # Close any open trade at end
        if self.active_trade is not None:
            final_price = self.df['Close'].iloc[-1]
            final_time = self.df.index[-1]
            self._close_trade(
                final_time, final_price, 
                CloseReason.TIME_EXIT,
                "End of backtest"
            )
        
        return self._generate_results()
    
    def _check_entry(
        self, 
        current_time: datetime, 
        current_price: float,
        indicators: ForexIndicators
    ):
        """Check for entry signal"""
        # Check ADX - only trade in ranging markets (mean reversion)
        if not indicators.is_ranging_market(adx_threshold=25.0):
            return  # Skip trending markets
        
        # Get signal
        signal = indicators.check_entry_signal(
            price=current_price,
            rsi_min=self.config['rsi_oversold_min'],
            rsi_max=self.config['rsi_oversold_max'],
            bb_tolerance_pips=self.config.get('bb_tolerance_pips', 3.0),
            min_bb_width_pips=self.config.get('min_bb_width_pips', 10.0),
        )
        
        if not signal.is_valid:
            return
        
        # Calculate exit levels first to get actual stop price
        levels = indicators.get_exit_levels(
            entry_price=current_price,
            target_pips=self.config['target_pips'],
            stop_pips=self.config['stop_pips'],
            use_atr=True,
        )
        
        # Calculate position size
        position = self.calculate_position_size(current_price, levels['stop'])
        size_lots = position.lots
        
        if size_lots <= 0:
            return
        
        # Open trade
        self.active_trade = Trade(
            entry_time=current_time,
            entry_price=current_price,
            size_lots=size_lots,
            stop_price=levels['stop'],
            targets=levels['targets'],
        )
        
        if self.verbose:
            print(f"\n📈 ENTRY at {current_time}")
            print(f"   Price: {current_price:.5f}")
            print(f"   Size: {size_lots:.2f} lots")
            print(f"   Stop: {levels['stop']:.5f} ({levels['stop_pips']:.1f} pips)")
            print(f"   Targets: {[f'{t:.5f}' for t in levels['targets']]}")
            print(f"   RSI: {signal.rsi:.1f}, Confidence: {signal.confidence}%")
    
    def _manage_position(
        self,
        current_time: datetime,
        current_price: float,
        current_bar: pd.Series
    ):
        """Manage open position"""
        if self.active_trade is None:
            return
        
        trade = self.active_trade
        entry = trade.entry_price
        
        # Check time exit
        hours_held = (current_time - trade.entry_time).total_seconds() / 3600
        if hours_held >= self.config['max_hold_hours']:
            self._close_trade(
                current_time, current_price,
                CloseReason.TIME_EXIT,
                f"Max hold time ({hours_held:.1f}h)"
            )
            return
        
        # Check stop loss
        if current_price <= trade.stop_price:
            self._close_trade(
                current_time, current_price,
                CloseReason.STOP_LOSS,
                f"Stop loss hit"
            )
            return
        
        # Check partial targets
        for i, target in enumerate(trade.targets):
            if not trade.scale_levels_hit[i] and current_price >= target:
                trade.scale_levels_hit[i] = True
                
                if i == 0:
                    trade.tp1_hit = True
                    # Move stop to breakeven after TP1
                    trade.stop_price = max(trade.stop_price, trade.entry_price)
                    if self.verbose:
                        print(f"   TP1 hit! Stop moved to breakeven")
                elif i == 1:
                    trade.tp2_hit = True
                elif i == 2:
                    trade.tp3_hit = True
                    # Close remaining position
                    self._close_trade(
                        current_time, current_price,
                        CloseReason.TP3,
                        f"TP3 hit (final target)"
                    )
                    return
    
    def _close_trade(
        self,
        exit_time: datetime,
        exit_price: float,
        reason: CloseReason,
        note: str
    ):
        """Close the active trade"""
        if self.active_trade is None:
            return
        
        trade = self.active_trade
        trade.exit_time = exit_time
        trade.exit_price = exit_price
        trade.close_reason = reason
        
        # Calculate PnL in pips
        trade.pips = (exit_price - trade.entry_price) / self.pip_size
        
        # Calculate PnL in USD
        # Simple calculation: pips * pip_value * position_size
        trade.pnl_usd = trade.pips * self.pip_value_per_micro_lot * (trade.size_lots * 100)
        
        # Update capital
        self.capital += trade.pnl_usd
        
        # Track max capital and drawdown
        if self.capital > self.max_capital:
            self.max_capital = self.capital
        
        dd = self.max_capital - self.capital
        if dd > self.max_drawdown:
            self.max_drawdown = dd
        
        # Store trade
        self.trades.append(trade)
        self.total_pips += trade.pips
        
        if self.verbose:
            print(f"📉 EXIT at {exit_time}")
            print(f"   Price: {exit_price:.5f}")
            print(f"   Reason: {reason.value} ({note})")
            print(f"   P&L: {trade.pips:+.1f} pips (${trade.pnl_usd:+.2f})")
            print(f"   Duration: {trade.duration_hours:.1f} hours")
        
        # Clear active trade
        self.active_trade = None
    
    def _update_equity(self, current_time: datetime):
        """Update equity curve"""
        # Calculate unrealized PnL if there's an open trade
        unrealized = 0.0
        if self.active_trade is not None:
            current_price = self.df.loc[current_time, 'Close']
            unrealized = (current_price - self.active_trade.entry_price) / self.pip_size
            unrealized *= self.pip_value_per_micro_lot * (self.active_trade.size_lots * 100)
        
        self.equity_curve.append({
            'timestamp': current_time,
            'capital': self.capital,
            'unrealized': unrealized,
            'total_equity': self.capital + unrealized,
        })
    
    def _generate_results(self) -> BacktestResult:
        """Generate backtest results"""
        closed_trades = [t for t in self.trades if t.exit_time is not None]
        
        if not closed_trades:
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pips=0.0,
                avg_pips_per_trade=0.0,
                avg_win_pips=0.0,
                avg_loss_pips=0.0,
                total_pnl_usd=0.0,
                max_drawdown_pips=0.0,
                max_drawdown_pct=0.0,
                avg_trade_duration=0.0,
                trades=[],
                equity_curve=pd.DataFrame(),
            )
        
        winning = [t for t in closed_trades if t.pips > 0]
        losing = [t for t in closed_trades if t.pips <= 0]
        
        total_pips = sum(t.pips for t in closed_trades)
        total_pnl = sum(t.pnl_usd for t in closed_trades)
        
        # Calculate drawdown in pips
        cumulative_pips = 0
        max_dd_pips = 0
        peak_pips = 0
        
        for t in closed_trades:
            cumulative_pips += t.pips
            if cumulative_pips > peak_pips:
                peak_pips = cumulative_pips
            dd = peak_pips - cumulative_pips
            if dd > max_dd_pips:
                max_dd_pips = dd
        
        equity_df = pd.DataFrame(self.equity_curve)
        
        return BacktestResult(
            total_trades=len(closed_trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=(len(winning) / len(closed_trades) * 100) if closed_trades else 0,
            total_pips=total_pips,
            avg_pips_per_trade=total_pips / len(closed_trades) if closed_trades else 0,
            avg_win_pips=sum(t.pips for t in winning) / len(winning) if winning else 0,
            avg_loss_pips=sum(t.pips for t in losing) / len(losing) if losing else 0,
            total_pnl_usd=total_pnl,
            max_drawdown_pips=max_dd_pips,
            max_drawdown_pct=(self.max_drawdown / self.initial_capital * 100) if self.initial_capital else 0,
            avg_trade_duration=sum(t.duration_hours for t in closed_trades) / len(closed_trades) if closed_trades else 0,
            trades=closed_trades,
            equity_curve=equity_df,
        )
