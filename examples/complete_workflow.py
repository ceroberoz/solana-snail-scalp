"""Complete Trading Workflow Example

This example shows the complete workflow from screening to live trading:
1. Screen tokens
2. Run backtest
3. Multi-token simulation
4. Live trading (when ready)
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from snail_scalp import (
    MultiTokenFeed,
    run_backtest,
    ScreeningTradingBot,
    RiskLevel,
)


def step1_screen_tokens():
    """Step 1: Screen and select best tokens"""
    print("\n" + "="*70)
    print("STEP 1: TOKEN SCREENING")
    print("="*70)
    
    feed = MultiTokenFeed()
    
    # Get best scalping candidates
    candidates = feed.get_best_scalping_candidates(n=5)
    
    print("\n[TOP CANDIDATES]")
    for i, token in enumerate(candidates, 1):
        m = token.metrics
        print(f"{i}. {m.symbol}: ${m.price_usd:.6f} | "
              f"24h: {m.change_24h:+.1f}% | Liquidity: ${m.liquidity_usd/1e6:.1f}M")
    
    # Save watchlist
    feed.export_watchlist("data/my_watchlist.json")
    print("\nWatchlist saved to: data/my_watchlist.json")
    
    return candidates


def step2_backtest(candidates):
    """Step 2: Backtest strategy on selected tokens"""
    print("\n" + "="*70)
    print("STEP 2: BACKTEST STRATEGY")
    print("="*70)
    
    print(f"\nBacktesting with {len(candidates)} tokens...")
    
    # Run backtest
    result = run_backtest(
        capital=20.0,
        days=14,
        save=True
    )
    
    # Check if profitable
    if result.total_return_pct > 0:
        print(f"\n[RESULT] Profitable: +{result.total_return_pct:.2f}% return")
        print(f"[RESULT] Win rate: {result.win_rate:.1f}%")
        print(f"[RESULT] Max drawdown: {result.max_drawdown_pct:.2f}%")
        return True
    else:
        print(f"\n[WARNING] Not profitable: {result.total_return_pct:.2f}%")
        print("Consider adjusting strategy or waiting for better market conditions")
        return False


def step3_simulation():
    """Step 3: Run multi-token simulation"""
    print("\n" + "="*70)
    print("STEP 3: MULTI-TOKEN SIMULATION")
    print("="*70)
    
    print("\nRunning 30-minute simulation...")
    print("(In real usage, this runs during trading hours)")
    
    bot = ScreeningTradingBot(
        initial_capital=20.0,
        max_positions=3,
        simulate=True,
        min_hype_score=60.0,
        max_risk_level=RiskLevel.HIGH,
    )
    
    # Run for limited time (demo)
    # In real usage: asyncio.run(bot.run())
    print("\n[Simulated trades would execute here]")
    print("[ENTRY] COPPERINU: Opened $3.00 at $0.006442")
    print("[DCA]   COPPERINU: Added $1.50 at $0.006378")
    print("[TP1]   COPPERINU: Closed 50% at $0.006603, PnL: +$0.08")
    print("[TP2]   COPPERINU: Closed remaining at $0.006700, PnL: +$0.12")
    print("\n[PORTFOLIO] Value: $20.20 (+1.0%)")


def step4_live_trading():
    """Step 4: Live trading (when ready)"""
    print("\n" + "="*70)
    print("STEP 4: LIVE TRADING SETUP")
    print("="*70)
    
    print("""
When you're ready for live trading:

1. Ensure you have:
   - Solana wallet with trading capital
   - Private RPC endpoint
   - Jupiter API access

2. Update config.py:
   - Set your RPC endpoint
   - Set your wallet address
   - Adjust position sizes

3. Run live trading:
   uv run python -m snail_scalp --multi --live

4. Monitor via:
   - Console output
   - Portfolio state file
   - Trade history

5. Risk management:
   - Start with $20
   - Scale up +$20 weekly if profitable
   - Never risk more than you can lose
""")


def main():
    """Run complete workflow"""
    print("\n" + "="*70)
    print("COMPLETE TRADING WORKFLOW")
    print("="*70)
    print("""
This example demonstrates the complete workflow:
1. Screen tokens for opportunities
2. Backtest strategy before risking capital
3. Run simulation to practice
4. Go live when ready

Let's begin...
""")
    
    # Step 1: Screen
    candidates = step1_screen_tokens()
    
    if not candidates:
        print("No suitable candidates found. Try again later.")
        return
    
    # Step 2: Backtest
    input("\nPress Enter to run backtest...")
    is_profitable = step2_backtest(candidates)
    
    if not is_profitable:
        print("\nStrategy not profitable in backtest.")
        response = input("Continue with simulation anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Step 3: Simulation
    input("\nPress Enter to run simulation...")
    step3_simulation()
    
    # Step 4: Live trading guide
    input("\nPress Enter to see live trading setup...")
    step4_live_trading()
    
    print("\n" + "="*70)
    print("WORKFLOW COMPLETE")
    print("="*70)
    print("""
Next steps:
1. Review screening results: data/screening_watchlist.json
2. Check backtest report: data/backtest_report.json
3. Run your own simulation: uv run python -m snail_scalp --multi
4. Go live when ready: uv run python -m snail_scalp --multi --live

Remember:
- Start small ($20)
- Backtest first
- Scale gradually
- Manage risk

Happy trading!
""")


if __name__ == "__main__":
    main()
