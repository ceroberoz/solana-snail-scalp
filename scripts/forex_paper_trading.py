#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dual Paper Trading Mode (M5.2)

Paper trading simulator for both USD/SGD and USD/MYR simultaneously.
Virtual portfolio tracking with realistic execution simulation.

Usage:
    python scripts/forex_paper_trading.py --capital 2000 --duration 7
    python scripts/forex_paper_trading.py --pairs USD_SGD USD_MYR --real-time
"""

import sys
import argparse
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_bot.config.pairs import get_pair_config, get_phase_2_pairs
from forex_bot.data.yahoo_provider import YahooFinanceProvider
from forex_bot.portfolio_manager import create_portfolio_manager
from forex_bot.portfolio_sizer import create_portfolio_sizer
from forex_bot.strategy.indicators import ForexIndicators


class PaperTradingEngine:
    """
    M5.2: Dual Paper Trading Engine

    Simulates live trading with:
    - Virtual capital tracking
    - Realistic execution delays
    - Performance metrics
    - Trade logging
    - Portfolio rebalancing
    """

    def __init__(
        self,
        pairs: List[str],
        initial_capital: float = 2000.0,
        data_provider=None,
    ):
        """
        Initialize paper trading engine

        Args:
            pairs: List of pairs to trade
            initial_capital: Starting virtual capital
            data_provider: Data provider instance
        """
        self.pairs = pairs
        self.initial_capital = initial_capital

        # Initialize data provider
        self.provider = data_provider or YahooFinanceProvider()

        # Load pair configurations
        self.pair_configs = {}
        for pair in pairs:
            config = get_pair_config(pair)
            self.pair_configs[pair] = {
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
            }

        # Initialize portfolio manager
        self.portfolio = create_portfolio_manager(
            initial_capital=initial_capital,
            pair_configs=self.pair_configs,
            max_positions=len(pairs),
        )

        # Initialize portfolio sizer (M5.1)
        self.sizer = create_portfolio_sizer(
            use_kelly=True,
            kelly_fraction=0.5,
            use_volatility=True,
        )

        # Trading state
        self.is_running = False
        self.trade_count = 0
        self.start_time: Optional[datetime] = None

        # Performance tracking
        self.daily_pnl: Dict[str, List[float]] = {pair: [] for pair in pairs}
        self.equity_curve: List[dict] = []

        logger.info(f"PaperTradingEngine initialized")
        logger.info(f"  Pairs: {pairs}")
        logger.info(f"  Capital: ${initial_capital:,.2f}")

    def fetch_latest_data(self, pair: str) -> Optional[pd.DataFrame]:
        """
        Fetch latest price data for a pair

        Args:
            pair: Pair code

        Returns:
            DataFrame with recent data or None
        """
        try:
            df = self.provider.download(pair, period="5d", interval="15m")
            if df.empty:
                return None
            return df
        except Exception as e:
            logger.error(f"Failed to fetch data for {pair}: {e}")
            return None

    def run_simulation(
        self, duration_days: int = 7, real_time: bool = False, speed_multiplier: float = 1.0
    ):
        """
        Run paper trading simulation

        Args:
            duration_days: Number of days to simulate
            real_time: Run in real-time mode
            speed_multiplier: Speed multiplier for simulation (1.0 = real-time)
        """
        print("\n" + "=" * 60)
        print("DUAL PAPER TRADING (M5.2)")
        print("=" * 60)
        print(f"Pairs: {', '.join(self.pairs)}")
        print(f"Capital: ${self.initial_capital:,.2f}")
        print(f"Duration: {duration_days} days")
        print(f"Mode: {'Real-time' if real_time else 'Historical simulation'}")
        print("=" * 60 + "\n")

        if real_time:
            self._run_real_time(duration_days)
        else:
            self._run_historical(duration_days, speed_multiplier)

    def _run_historical(self, duration_days: int, speed_multiplier: float):
        """Run historical simulation"""
        # Load historical data
        pair_data = {}
        for pair in self.pairs:
            df = self.fetch_latest_data(pair)
            if df is not None:
                # Limit to duration
                end_time = df.index[-1]
                start_time = end_time - timedelta(days=duration_days)
                pair_data[pair] = df[df.index >= start_time].copy()

        if len(pair_data) < len(self.pairs):
            print("[ERROR] Could not load data for all pairs")
            return

        # Get all timestamps
        all_times = sorted(set(t for df in pair_data.values() for t in df.index))

        print(f"Simulating {len(all_times)} bars...\n")

        # Simulation loop
        lookback = 50
        for i, current_time in enumerate(all_times[lookback:], start=lookback):
            # Update each pair
            for pair, df in pair_data.items():
                if current_time not in df.index:
                    continue

                idx = df.index.get_loc(current_time)
                if idx < lookback:
                    continue

                bar = df.iloc[idx]
                price = bar["Close"]

                # Update correlation
                self.portfolio.update_correlation(pair, current_time, price)

                # Record return for volatility
                if idx > 0:
                    prev_price = df.iloc[idx - 1]["Close"]
                    ret = (price - prev_price) / prev_price
                    self.sizer.record_return(pair, ret)

                # Process position
                self._process_pair(pair, current_time, price, bar, df, idx)

            # Record equity
            self._record_equity(current_time)

            # Progress
            if i % 100 == 0:
                progress = (i / len(all_times)) * 100
                print(
                    f"Progress: {progress:.1f}% | Capital: ${self.portfolio.state.capital:,.2f} | Trades: {len(self.portfolio.trade_history)}\r",
                    end="",
                )

        print(f"\n{'=' * 60}")
        self._print_results()

    def _run_real_time(self, duration_days: int):
        """Run real-time paper trading"""
        print("Real-time paper trading mode")
        print("Press Ctrl+C to stop\n")

        self.start_time = datetime.now()
        end_time = self.start_time + timedelta(days=duration_days)

        self.is_running = True

        try:
            while self.is_running and datetime.now() < end_time:
                current_time = datetime.now()

                for pair in self.pairs:
                    df = self.fetch_latest_data(pair)
                    if df is None or df.empty:
                        continue

                    latest = df.iloc[-1]
                    price = latest["Close"]

                    # Update
                    self.portfolio.update_correlation(pair, current_time, price)

                    # Check position
                    position = self.portfolio.get_position(pair)
                    if position is not None:
                        self._check_exit(pair, current_time, price, latest)
                    else:
                        self._check_entry(pair, current_time, price, df)

                self._record_equity(current_time)

                # Sleep
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            print("\n\nStopping...")

        self._print_results()

    def _process_pair(self, pair: str, current_time: datetime, price: float, bar, df, idx):
        """Process a single pair"""
        position = self.portfolio.get_position(pair)
        config = self.pair_configs[pair]

        if position is not None:
            # Check exits
            self._check_exit(pair, current_time, price, bar)
        else:
            # Check entry
            self._check_entry(pair, current_time, price, df.iloc[idx - 50 : idx + 1])

    def _check_entry(self, pair: str, current_time: datetime, price: float, df_window):
        """Check for entry signals"""
        # Check if we can trade
        can_trade, reason = self.portfolio.can_open_position(pair, current_time)
        if not can_trade:
            return

        # Get indicators
        indicators = ForexIndicators(df_window)

        # Check ranging market
        if not indicators.is_ranging_market(adx_threshold=25.0):
            return

        # Check entry signal
        config = self.pair_configs[pair]
        signal = indicators.check_entry_signal(
            price=price,
            rsi_min=config["rsi_oversold_min"],
            rsi_max=config["rsi_oversold_max"],
            bb_tolerance_pips=3.0,
            min_bb_width_pips=10.0,
        )

        if not signal.is_valid:
            return

        # Get exit levels
        levels = indicators.get_exit_levels(
            entry_price=price,
            target_pips=config["target_pips"],
            stop_pips=config["stop_pips"],
            use_atr=True,
        )

        # Calculate position size with M5.1 optimization
        sizing = self.sizer.calculate_position_size(
            pair_code=pair,
            base_risk_pct=config["risk_per_trade_pct"],
            capital=self.portfolio.get_available_capital(pair),
            stop_pips=config["stop_pips"],
            pip_value=config["pip_value_usd"],
        )

        # Open position
        success = self.portfolio.open_position(
            pair_code=pair,
            entry_time=current_time,
            entry_price=price,
            size_lots=sizing["lots"],
            stop_price=levels["stop"],
            targets=levels["targets"],
        )

        if success:
            print(
                f"📈 ENTRY {pair}: {sizing['lots']:.2f} lots @ {price:.5f} (mult: {sizing['total_multiplier']:.1f}x)"
            )

    def _check_exit(self, pair: str, current_time: datetime, price: float, bar):
        """Check for exit conditions"""
        position = self.portfolio.get_position(pair)
        if position is None:
            return

        config = self.pair_configs[pair]

        # Time exit
        hours_held = (current_time - position.entry_time).total_seconds() / 3600
        if hours_held >= config["max_hold_hours"]:
            pnl = self.portfolio.close_position(pair, current_time, price, "Time exit")
            self.sizer.record_trade(pair, pnl or 0, current_time)
            print(f"📉 EXIT {pair}: Time exit | PnL: ${pnl:+.2f}")
            return

        # Stop loss
        if price <= position.stop_price:
            pnl = self.portfolio.close_position(pair, current_time, price, "Stop loss")
            self.sizer.record_trade(pair, pnl or 0, current_time)
            print(f"📉 EXIT {pair}: Stop loss | PnL: ${pnl:+.2f}")
            return

        # Targets
        for i, target in enumerate(position.targets):
            if not position.scale_levels_hit[i] and price >= target:
                position.scale_levels_hit[i] = True

                if i == 0:
                    position.tp1_hit = True
                    position.stop_price = max(position.stop_price, position.entry_price)
                elif i == 1:
                    position.tp2_hit = True
                elif i == 2:
                    position.tp3_hit = True
                    pnl = self.portfolio.close_position(pair, current_time, price, "TP3")
                    self.sizer.record_trade(pair, pnl or 0, current_time)
                    print(f"📉 EXIT {pair}: TP3 | PnL: ${pnl:+.2f}")
                    return

    def _record_equity(self, timestamp: datetime):
        """Record equity snapshot"""
        unrealized = 0.0
        # Simplified - would need actual position values

        self.equity_curve.append(
            {
                "timestamp": timestamp,
                "capital": self.portfolio.state.capital,
                "total_equity": self.portfolio.state.capital + unrealized,
            }
        )

    def _print_results(self):
        """Print final results"""
        print("\n" + "=" * 60)
        print("PAPER TRADING RESULTS")
        print("=" * 60)

        self.portfolio.print_summary()
        self.sizer.print_sizing_info()

        # Save results
        self._save_results()

    def _save_results(self):
        """Save trading results"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "pairs": self.pairs,
            "initial_capital": self.initial_capital,
            "final_capital": self.portfolio.state.capital,
            "trades": self.portfolio.trade_history,
            "equity_curve": self.equity_curve,
            "sizing_summary": self.sizer.get_sizing_summary(),
        }

        output_file = Path("data/paper_trading_results.json")
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n💾 Results saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Dual Paper Trading (M5.2)")

    parser.add_argument(
        "--pairs",
        nargs="+",
        default=["USD_SGD", "USD_MYR"],
        help="Pairs to trade",
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=2000.0,
        help="Initial capital",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=7,
        help="Duration in days",
    )

    parser.add_argument(
        "--real-time",
        action="store_true",
        help="Real-time mode",
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Simulation speed multiplier",
    )

    args = parser.parse_args()

    # Create and run engine
    engine = PaperTradingEngine(
        pairs=args.pairs,
        initial_capital=args.capital,
    )

    engine.run_simulation(
        duration_days=args.duration,
        real_time=args.real_time,
        speed_multiplier=args.speed,
    )

    return 0


if __name__ == "__main__":
    # Setup logging
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger(__name__)

    sys.exit(main())
