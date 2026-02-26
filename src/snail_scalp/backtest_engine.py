"""Backtest Engine for Multi-Token Strategy

Simulates trading on historical data to evaluate strategy performance.
"""

import json
import asyncio
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import random

from snail_scalp.token_screener import TokenScreener, TokenMetrics, RiskLevel
from snail_scalp.portfolio_manager import PortfolioManager, CloseReason
from snail_scalp.indicators import TechnicalIndicators
from snail_scalp.config import strategy_config


@dataclass
class BacktestResult:
    """Results from a backtest run"""
    # Configuration
    start_date: datetime
    end_date: datetime
    initial_capital: float
    
    # Performance
    final_value: float = 0.0
    total_return_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Metrics
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    avg_trade_return: float = 0.0
    
    # By token
    token_performance: Dict[str, Dict] = field(default_factory=dict)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    trades: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "config": {
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
                "initial_capital": self.initial_capital,
            },
            "performance": {
                "final_value": round(self.final_value, 2),
                "total_return_pct": round(self.total_return_pct, 2),
                "total_trades": self.total_trades,
                "win_rate": round(self.win_rate, 2),
                "max_drawdown_pct": round(self.max_drawdown_pct, 2),
                "sharpe_ratio": round(self.sharpe_ratio, 2),
                "avg_trade_return": round(self.avg_trade_return, 2),
            },
            "token_performance": self.token_performance,
            "equity_curve": [(t.isoformat(), v) for t, v in self.equity_curve],
        }


class BacktestEngine:
    """Backtest strategy on historical data"""
    
    def __init__(
        self,
        initial_capital: float = 20.0,
        days: int = 30,
        max_positions: int = 3,
        min_hype_score: float = 60.0,
        data_file: str = "data/top10_solana_coins.json",
    ):
        self.initial_capital = initial_capital
        self.days = days
        self.max_positions = max_positions
        self.min_hype_score = min_hype_score
        self.data_file = data_file
        
        # Load tokens
        self.screener = TokenScreener()
        self.screener.load_from_json(data_file)
        self.screener.score_tokens()
        
        # Results
        self.result = BacktestResult(
            start_date=datetime.now() - timedelta(days=days),
            end_date=datetime.now(),
            initial_capital=initial_capital,
        )
    
    def generate_historical_data(
        self,
        token: TokenMetrics,
        intervals: int = 1440  # 1 day in minutes
    ) -> List[Tuple[datetime, float, float]]:
        """Generate realistic historical price data"""
        data = []
        
        # Start price
        price = token.price_usd / (1 + token.change_24h / 100)  # Back-calculate
        
        # Volatility based on token characteristics
        base_volatility = 0.005  # 0.5% base
        if token.change_24h > 50:
            base_volatility = 0.02  # 2% for high volatility tokens
        elif token.change_24h > 20:
            base_volatility = 0.01  # 1% for medium volatility
        
        # Trend component
        trend = (token.change_24h / 100) / intervals
        
        start_time = datetime.now() - timedelta(days=1)
        
        for i in range(intervals):
            timestamp = start_time + timedelta(minutes=i)
            
            # Random walk with trend
            change = random.gauss(trend, base_volatility)
            price = price * (1 + change)
            
            # Ensure price stays positive
            price = max(price, 0.000001)
            
            # Volume varies throughout the day
            hour = timestamp.hour
            volume_multiplier = 1.5 if 9 <= hour <= 11 else 0.7  # Higher during trading hours
            volume = token.volume_24h / intervals * volume_multiplier * random.uniform(0.8, 1.2)
            
            data.append((timestamp, price, volume))
        
        return data
    
    def run_backtest(self) -> BacktestResult:
        """Run backtest simulation"""
        print("\n" + "="*70)
        print("BACKTEST ENGINE")
        print("="*70)
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Simulation Days: {self.days}")
        print(f"Max Positions: {self.max_positions}")
        print(f"Min Hype Score: {self.min_hype_score}")
        print("="*70)
        
        # Get qualified tokens
        qualified_tokens = [
            s for s in self.screener.hype_scores
            if s.total_hype_score >= self.min_hype_score
            and s.risk_level.value <= RiskLevel.HIGH.value
        ]
        
        print(f"\nTesting {len(qualified_tokens)} tokens...")
        
        # Portfolio for tracking
        portfolio = PortfolioManager(
            initial_capital=self.initial_capital,
            max_positions=self.max_positions,
            simulate=True
        )
        
        # Track equity curve
        equity_curve = []
        all_trades = []
        
        # Simulate each day
        current_date = self.result.start_date
        peak_value = self.initial_capital
        max_drawdown = 0.0
        
        for day in range(self.days):
            day_pnl = 0.0
            day_trades = 0
            
            # Process each token
            for score in qualified_tokens[:5]:  # Top 5 tokens
                token = score.token
                
                # Generate historical data for this token
                hist_data = self.generate_historical_data(token)
                
                # Simulate trading on this data
                pnl, trades = self._simulate_token_day(
                    token, score, hist_data, portfolio
                )
                
                day_pnl += pnl
                day_trades += trades
            
            # Update portfolio value
            summary = portfolio.get_portfolio_summary()
            current_value = summary['total_value']
            
            # Track drawdown
            if current_value > peak_value:
                peak_value = current_value
            drawdown = (peak_value - current_value) / peak_value * 100
            max_drawdown = max(max_drawdown, drawdown)
            
            # Record equity
            equity_curve.append((current_date, current_value))
            
            # Progress
            if day % 5 == 0:
                print(f"Day {day:3d}: Value=${current_value:.2f} | "
                      f"Return={(current_value/self.initial_capital-1)*100:+.2f}% | "
                      f"DD={max_drawdown:.1f}%")
            
            current_date += timedelta(days=1)
        
        # Compile results
        summary = portfolio.get_portfolio_summary()
        
        self.result.final_value = summary['total_value']
        self.result.total_return_pct = summary['total_return_pct']
        self.result.total_trades = summary['total_trades']
        self.result.win_rate = summary['win_rate']
        self.result.max_drawdown_pct = max_drawdown
        self.result.equity_curve = equity_curve
        
        # Calculate additional metrics
        if self.result.total_trades > 0:
            returns = [(self.result.equity_curve[i][1] - self.result.equity_curve[i-1][1]) / self.result.equity_curve[i-1][1] 
                      for i in range(1, len(self.result.equity_curve))]
            if returns:
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5
                if std_dev > 0:
                    self.result.sharpe_ratio = (avg_return * 365) / (std_dev * (365 ** 0.5))
        
        return self.result
    
    def _simulate_token_day(
        self,
        token: TokenMetrics,
        score,
        hist_data: List[Tuple[datetime, float, float]],
        portfolio: PortfolioManager
    ) -> Tuple[float, int]:
        """Simulate trading for one token on one day"""
        symbol = token.symbol
        indicators = TechnicalIndicators()
        
        position_opened = False
        trades = 0
        total_pnl = 0.0
        
        for timestamp, price, volume in hist_data:
            indicators.add_price(price, volume)
            
            # Skip if not in trading window (9-11 UTC)
            if not (9 <= timestamp.hour < 11):
                continue
            
            position = portfolio.get_position(symbol)
            
            if position and position.status.value in ['open', 'partial']:
                # Update price
                portfolio.update_position_price(symbol, price)
                
                # Check exits
                entry = position.entry_price
                pnl_pct = (price - entry) / entry * 100
                
                # Stop loss
                if pnl_pct <= -strategy_config.stop_loss_percent:
                    success, pnl = portfolio.close_position(symbol, price, CloseReason.STOP_LOSS)
                    if success:
                        total_pnl += pnl
                        trades += 1
                
                # TP1
                elif pnl_pct >= strategy_config.tp1_percent and not position.tp1_hit:
                    success, pnl = portfolio.partial_close(symbol, price, 0.5)
                    if success:
                        total_pnl += pnl
                
                # TP2
                elif pnl_pct >= strategy_config.tp2_percent and position.tp1_hit:
                    success, pnl = portfolio.close_position(symbol, price, CloseReason.TP2)
                    if success:
                        total_pnl += pnl
                        trades += 1
                
                # DCA
                elif pnl_pct <= -strategy_config.dca_trigger_percent and not position.dca_done:
                    dca_size = position.size_usd * 0.5
                    portfolio.execute_dca(symbol, price, dca_size)
            
            else:
                # Look for entry
                if len(indicators.prices) >= strategy_config.bb_period:
                    if indicators.is_entry_signal(price):
                        size = min(3.0, portfolio.state.available_capital)
                        if size >= 1.0:  # Minimum position size
                            if portfolio.open_position(
                                symbol=symbol,
                                address=token.address,
                                entry_price=price,
                                size_usd=size,
                                hype_score=score.total_hype_score,
                                risk_level=score.risk_level
                            ):
                                position_opened = True
        
        return total_pnl, trades
    
    def print_report(self):
        """Print backtest report"""
        print("\n" + "="*70)
        print("BACKTEST RESULTS")
        print("="*70)
        
        perf = self.result.to_dict()['performance']
        
        print(f"\nInitial Capital: ${self.initial_capital:.2f}")
        print(f"Final Value: ${perf['final_value']:.2f}")
        print(f"Total Return: {perf['total_return_pct']:+.2f}%")
        print(f"Total Trades: {perf['total_trades']}")
        print(f"Win Rate: {perf['win_rate']:.1f}%")
        print(f"Max Drawdown: {perf['max_drawdown_pct']:.2f}%")
        print(f"Sharpe Ratio: {perf['sharpe_ratio']:.2f}")
        
        # Interpretation
        print("\n" + "="*70)
        print("INTERPRETATION")
        print("="*70)
        
        if perf['total_return_pct'] > 50:
            print("[EXCELLENT] Strategy shows strong returns")
        elif perf['total_return_pct'] > 20:
            print("[GOOD] Strategy shows solid returns")
        elif perf['total_return_pct'] > 0:
            print("[ACCEPTABLE] Strategy is profitable but modest")
        else:
            print("[POOR] Strategy is not profitable")
        
        if perf['max_drawdown_pct'] > 20:
            print("[WARNING] High drawdown - consider tighter stops")
        elif perf['max_drawdown_pct'] > 10:
            print("[CAUTION] Moderate drawdown - monitor risk")
        else:
            print("[GOOD] Low drawdown - good risk control")
        
        if perf['win_rate'] > 60:
            print("[GOOD] High win rate")
        elif perf['win_rate'] > 40:
            print("[ACCEPTABLE] Moderate win rate")
        else:
            print("[WARNING] Low win rate - review entry criteria")
        
        print("="*70)
    
    def save_report(self, filepath: str = "data/backtest_report.json"):
        """Save backtest report to file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.result.to_dict(), f, indent=2)
        
        print(f"\nReport saved to: {filepath}")


def run_backtest(
    capital: float = 20.0,
    days: int = 30,
    save: bool = True
) -> BacktestResult:
    """Run backtest and return results"""
    engine = BacktestEngine(
        initial_capital=capital,
        days=days,
        max_positions=3,
        min_hype_score=60.0,
    )
    
    result = engine.run_backtest()
    engine.print_report()
    
    if save:
        engine.save_report()
    
    return result


if __name__ == "__main__":
    # Run backtest
    run_backtest(capital=20.0, days=30)
