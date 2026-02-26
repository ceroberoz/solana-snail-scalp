#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run backtest simulation with USD/SGD data

Usage:
    python scripts/run_backtest.py --data data/historical/usd_sgd_1h_2y.parquet
    python scripts/run_backtest.py --period 2y --capital 5000
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd

from forex_bot.config.pairs import USD_SGD, get_pair_config
from forex_bot.strategy.backtest import ForexBacktest


def load_data(data_path: str, resample: str = None) -> pd.DataFrame:
    """Load and optionally resample data"""
    print(f"Loading data from {data_path}...")
    df = pd.read_parquet(data_path)
    
    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    # Resample if needed
    if resample and resample != "1h":
        from forex_bot.strategy.indicators import resample_ohlc
        df = resample_ohlc(df, resample)
        print(f"Resampled to {resample}: {len(df)} rows")
    
    print(f"Loaded {len(df)} rows")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")
    print(f"Price range: {df['Close'].min():.5f} - {df['Close'].max():.5f}")
    
    return df


def run_backtest(df: pd.DataFrame, config: dict, capital: float = 1000.0):
    """Run backtest and display results"""
    print("\n" + "="*60)
    print("INITIALIZING BACKTEST")
    print("="*60)
    
    print(f"\nConfiguration:")
    print(f"   Pair: {config['name']}")
    print(f"   Initial Capital: ${capital:,.2f}")
    print(f"   Risk per Trade: {config['risk_per_trade_pct']}%")
    print(f"   Timeframe: {config['timeframe']}")
    print(f"   BB Period: {config['bb_period']}, Std: {config['bb_std']}")
    print(f"   RSI Range: {config['rsi_oversold_min']}-{config['rsi_oversold_max']}")
    print(f"   Targets: {config['target_pips']} pips")
    print(f"   Stop: {config['stop_pips']} pips")
    print(f"   Max Hold: {config['max_hold_hours']} hours")
    
    # Run backtest
    backtest = ForexBacktest(
        df=df,
        pair_config=config,
        initial_capital=capital,
        risk_per_trade_pct=config['risk_per_trade_pct'],
        verbose=False,  # Set to True for trade-by-trade output
    )
    
    print("\nRunning simulation...")
    results = backtest.run()
    
    # Display results
    results.print_summary()
    
    # Show some trades
    if results.trades:
        print("\n📋 Sample Trades (first 5):")
        print("-" * 80)
        print(f"{'Entry Time':<20} {'Exit Time':<20} {'Pips':>8} {'P&L':>10} {'Reason':<15}")
        print("-" * 80)
        
        for t in results.trades[:5]:
            entry = t.entry_time.strftime("%Y-%m-%d %H:%M")
            exit_t = t.exit_time.strftime("%Y-%m-%d %H:%M") if t.exit_time else "Open"
            pips = f"{t.pips:+.1f}"
            pnl = f"${t.pnl_usd:+.2f}"
            reason = t.close_reason.value if t.close_reason else "Open"
            
            print(f"{entry:<20} {exit_t:<20} {pips:>8} {pnl:>10} {reason:<15}")
        
        if len(results.trades) > 5:
            print(f"\n... and {len(results.trades) - 5} more trades")
    
    # Plot if matplotlib available
    try:
        import matplotlib.pyplot as plt
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        
        # Price and trades
        ax1 = axes[0]
        ax1.plot(df.index, df['Close'], label='USD/SGD', alpha=0.7)
        
        # Mark entries and exits
        for t in results.trades:
            color = 'green' if t.pips > 0 else 'red'
            ax1.scatter(t.entry_time, t.entry_price, color='blue', marker='^', s=50, zorder=5)
            ax1.scatter(t.exit_time, t.exit_price, color=color, marker='v', s=50, zorder=5)
        
        ax1.set_title('USD/SGD Price with Trade Signals')
        ax1.set_ylabel('Price')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Equity curve
        ax2 = axes[1]
        if not results.equity_curve.empty:
            ax2.plot(results.equity_curve['timestamp'], results.equity_curve['total_equity'], label='Equity', color='green')
            ax2.axhline(y=capital, color='gray', linestyle='--', label='Initial Capital')
            ax2.set_title('Equity Curve')
            ax2.set_ylabel('Capital (USD)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # Cumulative pips
        ax3 = axes[2]
        if results.trades:
            cumulative_pips = []
            running_total = 0
            times = []
            for t in results.trades:
                running_total += t.pips
                cumulative_pips.append(running_total)
                times.append(t.exit_time)
            
            ax3.plot(times, cumulative_pips, label='Cumulative Pips', color='blue')
            ax3.axhline(y=0, color='gray', linestyle='--')
            ax3.set_title('Cumulative Pips')
            ax3.set_ylabel('Pips')
            ax3.set_xlabel('Date')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = Path("data/backtest_results.png")
        plot_path.parent.mkdir(exist_ok=True)
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        print(f"\n📊 Plot saved to: {plot_path}")
        
        plt.show()
        
    except ImportError:
        print("\nNote: Install matplotlib to see plots: pip install matplotlib")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Run USD/SGD backtest simulation")
    parser.add_argument(
        "--data",
        type=str,
        default="data/historical/usd_sgd_1h_2y.parquet",
        help="Path to historical data file",
    )
    parser.add_argument(
        "--pair",
        type=str,
        default="USD_SGD",
        help="Pair code (USD_SGD or USD_MYR)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1000.0,
        help="Initial capital in USD",
    )
    parser.add_argument(
        "--resample",
        type=str,
        default=None,
        help="Resample data (15m, 30m, 1h, 4h, 1d)",
    )
    
    args = parser.parse_args()
    
    # Load data
    df = load_data(args.data, args.resample)
    
    # Get config
    config = get_pair_config(args.pair)
    config_dict = {
        'name': config.name,
        'timeframe': args.resample or config.timeframe,
        'bb_period': config.bb_period,
        'bb_std': config.bb_std,
        'rsi_period': config.rsi_period,
        'rsi_oversold_min': config.rsi_oversold_min,
        'rsi_oversold_max': config.rsi_oversold_max,
        'target_pips': config.target_pips,
        'stop_pips': config.stop_pips,
        'max_hold_hours': config.max_hold_hours,
        'risk_per_trade_pct': config.risk_per_trade_pct,
        'pip_value_usd': config.pip_value_usd,
        'bb_tolerance_pips': 3.0,
        'min_bb_width_pips': 10.0,
    }
    
    # Run backtest
    results = run_backtest(df, config_dict, args.capital)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
