#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-pair backtest runner (M1.2, M1.4)

Runs backtest on multiple currency pairs simultaneously with:
- Portfolio capital allocation
- Correlation-based position filtering (M1.4)
- Combined performance reporting

Usage:
    python scripts/forex_run_multi_pair_backtest.py --pairs USD_SGD USD_MYR --capital 2000
    python scripts/forex_run_multi_pair_backtest.py --phase2 --capital 2000
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_bot.config.pairs import get_pair_config, get_phase_2_pairs
from forex_bot.portfolio_manager import create_portfolio_manager
from forex_bot.strategy.backtest import ForexBacktest
from forex_bot.strategy.indicators import ForexIndicators


def load_pair_data(pair_code: str, period: str = "2y") -> pd.DataFrame:
    """Load historical data for a pair"""
    config = get_pair_config(pair_code)
    interval = "1h"  # Use 1h for longer periods

    data_path = Path(f"data/historical/{pair_code.lower()}_{interval}_{period}.parquet")

    if not data_path.exists():
        print(f"[ERROR] Data file not found: {data_path}")
        print(
            f"        Run: python scripts/forex_download_history.py --pair {pair_code} --period {period}"
        )
        return None

    df = pd.read_parquet(data_path)

    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    print(f"✅ Loaded {pair_code}: {len(df)} rows ({df.index[0]} to {df.index[-1]})")

    return df


def run_multi_pair_backtest(pairs: List[str], capital: float = 2000.0, verbose: bool = False):
    """
    Run multi-pair backtest simulation

    Args:
        pairs: List of pair codes to trade
        capital: Initial capital
        verbose: Print detailed trade info
    """
    print("\n" + "=" * 60)
    print("MULTI-PAIR BACKTEST")
    print("=" * 60)
    print(f"Pairs: {', '.join(pairs)}")
    print(f"Initial Capital: ${capital:,.2f}")
    print(f"Max Positions: {len(pairs)}")
    print("=" * 60)

    # Load data for all pairs
    pair_data: Dict[str, pd.DataFrame] = {}
    pair_configs = {}

    print("\n📥 Loading data...")
    for pair_code in pairs:
        df = load_pair_data(pair_code)
        if df is not None:
            pair_data[pair_code] = df
            config = get_pair_config(pair_code)
            pair_configs[pair_code] = {
                "name": config.name,
                "timeframe": config.timeframe,
                "bb_period": config.bb_period,
                "bb_std": config.bb_std,
                "rsi_period": config.rsi_period,
                "rsi_oversold_min": config.rsi_oversold_min,
                "rsi_oversold_max": config.rsi_oversold_max,
                "target_pips": config.target_pips,
                "stop_pips": config.stop_pips,
                "max_hold_hours": config.max_hold_hours,
                "risk_per_trade_pct": config.risk_per_trade_pct,
                "pip_value_usd": config.pip_value_usd,
                "portfolio_allocation": 0.5 if len(pairs) == 2 else 1.0 / len(pairs),
            }

    if len(pair_data) < 2:
        print("[ERROR] Need at least 2 pairs for multi-pair backtest")
        return 1

    # Create portfolio manager (M1.2, M1.4)
    portfolio = create_portfolio_manager(
        initial_capital=capital,
        pair_configs=pair_configs,
        max_positions=len(pairs),
    )

    # Find common date range
    start_times = [df.index[0] for df in pair_data.values()]
    end_times = [df.index[-1] for df in pair_data.values()]
    common_start = max(start_times)
    common_end = min(end_times)

    print(f"\n📅 Common date range: {common_start} to {common_end}")

    # Filter data to common range
    for pair_code in pair_data:
        df = pair_data[pair_code]
        pair_data[pair_code] = df[(df.index >= common_start) & (df.index <= common_end)].copy()

    # Run simulation
    print(f"\n🚀 Running simulation...")
    print(f"   Processing {len(pairs)} pairs simultaneously")
    print(f"   Correlation monitoring: ENABLED (M1.4)")
    print()

    # Create individual backtest engines for each pair
    backtests = {}
    for pair_code, df in pair_data.items():
        backtests[pair_code] = ForexBacktest(
            df=df,
            pair_config=pair_configs[pair_code],
            initial_capital=capital / len(pairs),  # Split capital initially
            risk_per_trade_pct=pair_configs[pair_code]["risk_per_trade_pct"],
            verbose=False,
        )

    # Get all unique timestamps across all pairs
    all_timestamps = sorted(set(ts for df in pair_data.values() for ts in df.index))

    # Simulation loop
    lookback = 50
    trade_count = 0

    for i, current_time in enumerate(all_timestamps[lookback:], start=lookback):
        # Process each pair
        for pair_code, df in pair_data.items():
            if current_time not in df.index:
                continue

            # Get current data
            current_idx = df.index.get_loc(current_time)
            if current_idx < lookback:
                continue

            current_bar = df.iloc[current_idx]
            current_price = current_bar["Close"]

            # Update correlation monitor (M1.4)
            portfolio.update_correlation(pair_code, current_time, current_price)

            # Get indicators
            window = df.iloc[current_idx - lookback : current_idx + 1]
            indicators = ForexIndicators(window)

            # Check if we have a position in this pair
            position = portfolio.get_position(pair_code)

            if position is not None:
                # Manage existing position
                _manage_position(
                    portfolio,
                    pair_code,
                    current_time,
                    current_price,
                    current_bar,
                    position,
                    pair_configs[pair_code],
                )
            else:
                # Check for entry
                _check_entry(
                    portfolio,
                    pair_code,
                    current_time,
                    current_price,
                    indicators,
                    pair_configs[pair_code],
                    backtests[pair_code],
                )

        # Progress indicator
        if i % 1000 == 0:
            progress = (i / len(all_timestamps)) * 100
            print(
                f"   Progress: {progress:.1f}% | Trades: {len(portfolio.trade_history)} | Capital: ${portfolio.state.capital:,.2f}",
                end="\r",
            )

    print(
        f"\n   Progress: 100.0% | Trades: {len(portfolio.trade_history)} | Capital: ${portfolio.state.capital:,.2f}"
    )

    # Print results
    portfolio.print_summary()

    # Per-pair statistics
    print("\n" + "=" * 60)
    print("PER-PAIR PERFORMANCE")
    print("=" * 60)

    for pair_code in pairs:
        pair_trades = [t for t in portfolio.trade_history if t["pair"] == pair_code]
        if pair_trades:
            winning = [t for t in pair_trades if t["pnl"] > 0]
            total_pnl = sum(t["pnl"] for t in pair_trades)
            print(f"\n{pair_code}:")
            print(f"   Trades: {len(pair_trades)} (Win: {len(winning)})")
            print(f"   Total P&L: ${total_pnl:+.2f}")
            print(f"   Avg per trade: ${total_pnl / len(pair_trades):+.2f}")

    # Save results
    _save_results(portfolio, pairs)

    return 0


def _manage_position(
    portfolio,
    pair_code: str,
    current_time: datetime,
    current_price: float,
    current_bar,
    position,
    config: dict,
):
    """Manage an open position"""
    # Check time exit
    hours_held = (current_time - position.entry_time).total_seconds() / 3600
    if hours_held >= config["max_hold_hours"]:
        portfolio.close_position(pair_code, current_time, current_price, "Time exit")
        return

    # Check stop loss
    if current_price <= position.stop_price:
        portfolio.close_position(pair_code, current_time, current_price, "Stop loss")
        return

    # Check targets
    for i, target in enumerate(position.targets):
        if not position.scale_levels_hit[i] and current_price >= target:
            position.scale_levels_hit[i] = True

            if i == 0:
                position.tp1_hit = True
                position.stop_price = max(position.stop_price, position.entry_price)
            elif i == 1:
                position.tp2_hit = True
            elif i == 2:
                position.tp3_hit = True
                portfolio.close_position(pair_code, current_time, current_price, "TP3")
                return


def _check_entry(
    portfolio,
    pair_code: str,
    current_time: datetime,
    current_price: float,
    indicators,
    config: dict,
    backtest_engine,
):
    """Check for entry signal"""
    # Check if we can open position (includes correlation check M1.4)
    can_trade, reason = portfolio.can_open_position(pair_code, current_time)
    if not can_trade:
        return

    # Check ADX - only trade in ranging markets
    if not indicators.is_ranging_market(adx_threshold=25.0):
        return

    # Get entry signal
    signal = indicators.check_entry_signal(
        price=current_price,
        rsi_min=config["rsi_oversold_min"],
        rsi_max=config["rsi_oversold_max"],
        bb_tolerance_pips=3.0,
        min_bb_width_pips=10.0,
    )

    if not signal.is_valid:
        return

    # Get exit levels
    levels = indicators.get_exit_levels(
        entry_price=current_price,
        target_pips=config["target_pips"],
        stop_pips=config["stop_pips"],
        use_atr=True,
    )

    # Calculate position size with session adjustment (M3.1)
    position_size = backtest_engine.calculate_position_size(
        current_price, levels["stop"], current_time
    )

    # Apply portfolio allocation
    available_capital = portfolio.get_available_capital(pair_code)
    max_risk = available_capital * (config["risk_per_trade_pct"] / 100)

    # Adjust size based on available capital
    if position_size.risk_amount > max_risk:
        scale_factor = max_risk / position_size.risk_amount
        adjusted_lots = position_size.lots * scale_factor
    else:
        adjusted_lots = position_size.lots

    if adjusted_lots <= 0:
        return

    # Open position
    success = portfolio.open_position(
        pair_code=pair_code,
        entry_time=current_time,
        entry_price=current_price,
        size_lots=adjusted_lots,
        stop_price=levels["stop"],
        targets=levels["targets"],
    )


def _save_results(portfolio, pairs: List[str]):
    """Save backtest results to file"""
    import json

    stats = portfolio.get_statistics()

    results = {
        "timestamp": datetime.now().isoformat(),
        "pairs": pairs,
        "initial_capital": portfolio.initial_capital,
        "final_capital": stats["current_capital"],
        "total_return_pct": stats["return_pct"],
        "total_trades": stats["total_trades"],
        "winning_trades": stats["winning_trades"],
        "losing_trades": stats["losing_trades"],
        "win_rate": stats["win_rate"],
        "total_pnl": stats["total_pnl"],
        "trades": portfolio.trade_history,
    }

    output_file = Path("data/multi_pair_backtest_results.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n💾 Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Run multi-pair backtest (M1.2, M1.4)")

    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["USD_SGD", "USD_MYR"],
        help="Pairs to trade (default: USD_SGD USD_MYR)",
    )

    parser.add_argument(
        "--phase2",
        action="store_true",
        help="Use all Phase 2 pairs",
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=2000.0,
        help="Initial capital (default: 2000)",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Determine pairs
    if args.phase2:
        pairs = list(get_phase_2_pairs().keys())
        print(f"Using Phase 2 pairs: {pairs}")
    else:
        pairs = args.pairs

    # Run backtest
    return run_multi_pair_backtest(pairs, args.capital, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
