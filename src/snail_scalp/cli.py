#!/usr/bin/env python3
"""
Solana Snail Scalp Bot
Conservative scalping strategy for $20 capital on Solana

Usage:
    uv run python -m snail_scalp --simulate              # Run simulation with sample data
    uv run python -m snail_scalp --screen                # Screen tokens and show best picks
    uv run python -m snail_scalp --backtest --days 30    # Backtest strategy
    uv run python -m snail_scalp --multi                 # Multi-token trading mode
    uv run python -m snail_scalp                         # Run live trading (requires API keys)
"""

import sys
import asyncio
import aiohttp
import argparse
from datetime import datetime
from pathlib import Path

# Enable line buffering for immediate output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

from snail_scalp.config import (
    trading_config,
    strategy_config,
    SIMULATION_CONFIG,
    PAIR_ADDRESS,
)
from snail_scalp.data_feed import HybridDataFeed
from snail_scalp.indicators import TechnicalIndicators
from snail_scalp.risk_manager import RiskManager
from snail_scalp.trader import Trader


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Solana Snail Scalp Bot - Conservative scalping strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  Standard Mode:
    %(prog)s --simulate                    # Paper trading with sample data
    %(prog)s --simulate --log data/history.csv  # Use custom price history
    %(prog)s --speed 5                     # 5x simulation speed
    %(prog)s                               # Live trading mode

  Screening Mode:
    %(prog)s --screen                      # Show token screening results
    %(prog)s --screen --hype 70            # Filter by min hype score
    %(prog)s --screen --risk moderate      # Filter by max risk level

  Backtest Mode:
    %(prog)s --backtest                    # Run 30-day backtest
    %(prog)s --backtest --days 60          # Run 60-day backtest
    %(prog)s --backtest --capital 100      # Test with $100 capital

  Multi-Token Mode:
    %(prog)s --multi                       # Multi-token trading (simulation)
    %(prog)s --multi --live                # Multi-token trading (live)
        """,
    )

    # Standard mode
    parser.add_argument(
        "--simulate",
        "-s",
        action="store_true",
        help="Run in simulation/paper trading mode using log data",
    )

    parser.add_argument(
        "--log",
        "-l",
        type=str,
        default=SIMULATION_CONFIG["log_file"],
        help=f"Path to price log file for simulation (default: {SIMULATION_CONFIG['log_file']})",
    )

    parser.add_argument(
        "--speed",
        "-x",
        type=float,
        default=SIMULATION_CONFIG["speed_multiplier"],
        help=f"Simulation speed multiplier (default: {SIMULATION_CONFIG['speed_multiplier']} = real-time)",
    )

    # Screening mode
    parser.add_argument(
        "--screen",
        action="store_true",
        help="Run token screening and show best picks",
    )

    parser.add_argument(
        "--hype",
        type=float,
        default=60.0,
        help="Minimum hype score for screening (default: 60)",
    )

    parser.add_argument(
        "--risk",
        type=str,
        default="high",
        choices=["minimal", "low", "moderate", "high", "extreme"],
        help="Maximum risk level for screening (default: high)",
    )

    # Backtest mode
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run backtest simulation",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to backtest (default: 30)",
    )

    # Multi-token mode
    parser.add_argument(
        "--multi",
        action="store_true",
        help="Run multi-token trading mode",
    )

    parser.add_argument(
        "--live",
        action="store_true",
        help="Enable live trading (default is simulation)",
    )

    # Common options
    parser.add_argument(
        "--capital",
        "-c",
        type=float,
        default=trading_config.initial_capital,
        help=f"Initial capital in USD (default: ${trading_config.initial_capital})",
    )

    parser.add_argument(
        "--window-start",
        type=int,
        default=trading_config.trading_start_utc,
        help=f"Trading window start hour UTC (default: {trading_config.trading_start_utc})",
    )

    parser.add_argument(
        "--window-end",
        type=int,
        default=trading_config.trading_end_utc,
        help=f"Trading window end hour UTC (default: {trading_config.trading_end_utc})",
    )

    parser.add_argument(
        "--reset", action="store_true", help="Reset all state files before starting"
    )

    parser.add_argument(
        "--results",
        type=str,
        default=SIMULATION_CONFIG["results_file"],
        help=f"Path to save simulation results (default: {SIMULATION_CONFIG['results_file']})",
    )

    return parser.parse_args()


def run_screening(args):
    """Run token screening"""
    from snail_scalp.multi_token_feed import MultiTokenFeed
    from snail_scalp.token_screener import RiskLevel

    print("\n" + "="*70)
    print("TOKEN SCREENING MODE")
    print("="*70)

    # Map risk string to enum
    risk_map = {
        "minimal": RiskLevel.MINIMAL,
        "low": RiskLevel.LOW,
        "moderate": RiskLevel.MODERATE,
        "high": RiskLevel.HIGH,
        "extreme": RiskLevel.EXTREME,
    }
    max_risk = risk_map.get(args.risk, RiskLevel.HIGH)

    print(f"Min Hype Score: {args.hype}")
    print(f"Max Risk Level: {max_risk.name}")
    print("="*70)

    # Load and screen
    feed = MultiTokenFeed()

    # Print full dashboard
    feed.print_trading_dashboard()

    # Export watchlist
    watchlist_file = feed.export_watchlist("data/screening_watchlist.json")
    print(f"\nWatchlist exported to: {watchlist_file}")

    # Show filtered results
    filtered = feed.get_ranked_tokens(
        min_hype_score=args.hype,
        max_risk=max_risk
    )

    print(f"\n" + "="*70)
    print(f"FILTERED RESULTS (Hype >= {args.hype}, Risk <= {max_risk.name})")
    print("="*70)
    print(f"Found {len(filtered)} tokens matching criteria\n")

    for i, token in enumerate(filtered[:10], 1):
        m = token.metrics
        h = token.hype
        print(f"{i}. {m.symbol} - Hype: {h.total_hype_score:.1f}, Risk: {h.risk_level.name}")
        print(f"   Price: ${m.price_usd:.6f} | 24h: {m.change_24h:+.1f}% | Liquidity: ${m.liquidity_usd/1e6:.1f}M")

    return 0


def run_backtest(args):
    """Run backtest"""
    from snail_scalp.backtest_engine import run_backtest

    print("\n" + "="*70)
    print("BACKTEST MODE")
    print("="*70)
    print(f"Capital: ${args.capital:.2f}")
    print(f"Days: {args.days}")
    print("="*70)

    result = run_backtest(
        capital=args.capital,
        days=args.days,
        save=True
    )

    return 0 if result.total_return_pct > 0 else 1


def run_multi_token(args):
    """Run multi-token trading"""
    from snail_scalp.screening_bot import ScreeningTradingBot
    from snail_scalp.token_screener import RiskLevel

    print("\n" + "="*70)
    print("MULTI-TOKEN TRADING MODE")
    print("="*70)

    simulate = not args.live
    mode_str = "SIMULATION" if simulate else "LIVE TRADING"
    print(f"Mode: {mode_str}")
    print(f"Capital: ${args.capital:.2f}")
    print("="*70)

    if not simulate:
        print("\nWARNING: LIVE TRADING MODE")
        print("This will use real funds!")
        response = input("\nContinue? (yes/no): ").lower().strip()
        if response != "yes":
            print("Aborted.")
            return 0

    bot = ScreeningTradingBot(
        initial_capital=args.capital,
        max_positions=3,
        simulate=simulate,
        min_hype_score=60.0,
        max_risk_level=RiskLevel.HIGH,
        trading_hours=(args.window_start, args.window_end),
    )

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nStopped by user.")

    return 0


class TradingBot:
    """Main trading bot orchestrator (single token mode)"""

    def __init__(self, args):
        self.args = args
        self.simulate = args.simulate
        self.capital = args.capital

        # Initialize components
        self.data_feed = HybridDataFeed(
            simulate=self.simulate, log_file=args.log, speed_multiplier=args.speed
        )

        self.indicators = TechnicalIndicators(period=strategy_config.bb_period)

        self.risk = RiskManager(
            daily_loss_limit=trading_config.daily_loss_limit_usd,
            max_consecutive_losses=trading_config.max_consecutive_losses,
            trading_start_utc=args.window_start,
            trading_end_utc=args.window_end,
            simulate=self.simulate,
        )

        self.trader = Trader(
            strategy_config={
                "rsi_oversold_min": strategy_config.rsi_oversold_min,
                "rsi_oversold_max": strategy_config.rsi_oversold_max,
                "min_band_width_percent": strategy_config.min_band_width_percent,
                "primary_allocation": strategy_config.primary_allocation,
                "dca_allocation": strategy_config.dca_allocation,
                "dca_trigger_percent": strategy_config.dca_trigger_percent,
                "tp1_percent": strategy_config.tp1_percent,
                "tp2_percent": strategy_config.tp2_percent,
                "stop_loss_percent": strategy_config.stop_loss_percent,
            },
            risk_manager=self.risk,
            simulate=self.simulate,
            results_file=args.results,
        )

        self.running = True

    def print_banner(self):
        """Print startup banner"""
        mode = "SIMULATION" if self.simulate else "LIVE TRADING"
        print("=" * 60)
        print(f"Solana Snail Scalp Bot - {mode}")
        print("=" * 60)
        print(f"Capital: ${self.capital:.2f}")
        print(f"Max Position: ${trading_config.max_position_usd:.2f} (30%)")
        print(f"Emergency Reserve: ${trading_config.emergency_reserve:.2f} (20%)")
        print(f"Trading Window: {self.args.window_start:02d}:00-{self.args.window_end:02d}:00 UTC")
        print(f"Check Interval: {strategy_config.check_interval_seconds}s")

        if self.simulate:
            print(f"Log File: {self.args.log}")
            print(f"Speed: {self.args.speed}x")
            print(f"Results: {self.args.results}")
        else:
            print(f"Pair: {PAIR_ADDRESS}")
            print("WARNING: Keep Telegram/Discord open for alerts!")

        print("=" * 60)
        print()

    async def run(self):
        """Main trading loop"""
        self.print_banner()

        # Check log file exists for simulation
        if self.simulate and not Path(self.args.log).exists():
            print(f"Log file not found: {self.args.log}")
            print("Run 'uv run python -m snail_scalp.generate_data' to create sample data")
            return

        session = None if self.simulate else aiohttp.ClientSession()

        try:
            while self.running:
                try:
                    # Fetch data first to get timestamp for simulation window check
                    price_data = await self.data_feed.get_price_data(session, PAIR_ADDRESS)

                    if not price_data:
                        if self.simulate:
                            print("Simulation complete - no more data")
                            break
                        await asyncio.sleep(strategy_config.check_interval_seconds)
                        continue

                    # Check if we should be trading (use data timestamp in simulation)
                    sim_time = (
                        datetime.fromtimestamp(price_data.timestamp) if self.simulate else None
                    )
                    in_window = self.risk.is_trading_window(sim_time)

                    # Fast-forward when outside trading window in simulation
                    if self.simulate and self.data_feed.sim_feed:
                        self.data_feed.sim_feed.skip_sleep = not in_window

                    if not in_window:
                        # Only print every hour to reduce spam
                        if self.simulate and sim_time and sim_time.minute == 0:
                            print(
                                f"[{sim_time.strftime('%H:%M')}] Outside trading window. Fast-forwarding to {self.args.window_start:02d}:00 UTC..."
                            )
                        elif not self.simulate and datetime.now().minute == 0:
                            print(
                                f"Outside trading window. Waiting for {self.args.window_start:02d}:00 UTC..."
                            )
                        # No sleep in simulation during fast-forward
                        if not self.simulate:
                            await asyncio.sleep(60)
                        else:
                            await asyncio.sleep(0)  # Yield control
                        continue

                    # Check circuit breakers
                    if not self.risk.can_trade_today():
                        if self.simulate:
                            print("Simulation stopped due to risk limits")
                            break
                        await asyncio.sleep(300)
                        continue

                    # Disable fast-forward now that we're in trading window
                    if self.simulate and self.data_feed.sim_feed:
                        self.data_feed.sim_feed.skip_sleep = False

                    current_price = price_data.price
                    data_timestamp = datetime.fromtimestamp(price_data.timestamp)
                    timestamp_str = (
                        data_timestamp.strftime("%H:%M:%S")
                        if self.simulate
                        else datetime.now().strftime("%H:%M:%S")
                    )
                    source_tag = "[SIM]" if price_data.source == "simulated" else "[LIVE]"

                    print(
                        f"\n[{timestamp_str}] {source_tag} Price: ${current_price:.4f} | "
                        f"Vol24h: ${price_data.volume24h:,.0f}"
                    )

                    # Update indicators
                    self.indicators.add_price(current_price, price_data.volume24h)

                    # Print indicator stats every few iterations
                    if self.indicators.prices and len(self.indicators.prices) % 5 == 0:
                        stats = self.indicators.get_stats()
                        bb_width_str = (
                            f"{stats['bb_width']:.2f}%" if stats["bb_width"] is not None else "N/A"
                        )
                        print(
                            f"   RSI: {stats['rsi']:.1f} | BB Width: {bb_width_str} | "
                            f"Data Points: {stats['data_points']}"
                        )
                    # Check if in position
                    if self.trader.active_position:
                        await self.trader.manage_position(current_price, self.indicators)
                    else:
                        # Look for entry
                        await self.trader.check_entry(current_price, self.indicators, self.capital)

                    # Wait for next check
                    if self.simulate:
                        await asyncio.sleep(0.1)  # Small delay in simulation
                    else:
                        await asyncio.sleep(strategy_config.check_interval_seconds)
                except KeyboardInterrupt:
                    print("\n\nBot stopped by user")
                    break
                except Exception as e:
                    print(f"\nError: {e}")
                    import traceback

                    traceback.print_exc()
                    await asyncio.sleep(60)

        finally:
            if session:
                await session.close()

            # Print summary
            self.print_summary()

    def print_summary(self):
        """Print final trading summary"""
        print("\n" + "=" * 60)
        print("TRADING SUMMARY")
        print("=" * 60)

        risk_stats = self.risk.get_stats()
        trader_summary = self.trader.get_summary()

        print(f"Total Trades: {risk_stats['trades_today']}")
        print(f"Wins: {risk_stats['wins']} | Losses: {risk_stats['losses']}")
        print(f"Win Rate: {risk_stats['win_rate']:.1f}%")
        print(f"Total PnL: ${trader_summary['total_pnl']:.2f}")
        print(f"Return: {(trader_summary['total_pnl'] / self.capital * 100):.2f}%")

        if self.simulate:
            print(f"\nResults saved to: {self.args.results}")

        print("=" * 60)


def main():
    """Main entry point"""
    args = parse_arguments()

    # Reset if requested
    if args.reset:
        print("Resetting state files...")
        for f in ["data/trading_state.json", "data/simulation_state.json",
                  "data/trades.json", "data/simulation_trades.json",
                  "data/portfolio_state.json", "data/simulation_portfolio.json"]:
            p = Path(f)
            if p.exists():
                p.unlink()
                print(f"  Deleted: {f}")

    # Route to appropriate mode
    if args.screen:
        return run_screening(args)

    if args.backtest:
        return run_backtest(args)

    if args.multi:
        return run_multi_token(args)

    # Standard single-token mode
    # Generate sample data if needed
    if args.simulate and not Path(args.log).exists():
        print(f"Log file not found: {args.log}")
        response = input("Generate sample data? (y/n): ").lower().strip()
        if response == "y":
            from snail_scalp.generate_data import generate_sample_data

            generate_sample_data(output_file=args.log)
        else:
            print("Cannot run simulation without data")
            sys.exit(1)

    # Create and run bot
    bot = TradingBot(args)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
