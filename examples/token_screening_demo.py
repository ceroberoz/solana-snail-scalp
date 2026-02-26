"""Token Screening Demo - How to use the hype-based filtering system

This example shows how to:
1. Load and screen top Solana tokens
2. Apply technical and sentiment analysis
3. Generate a trading watchlist
4. Integrate with the scalping strategy
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from snail_scalp import (
    TokenScreener, TokenMetrics, HypeScore, HypeCategory, RiskLevel,
    SentimentAnalyzer, SocialMetrics, CommunityMetrics, HypeCycleDetector,
    MultiTokenFeed, TokenData,
    TechnicalIndicators,
)


def demo_basic_screening():
    """Demo: Basic token screening"""
    print("\n" + "="*80)
    print("DEMO 1: Basic Token Screening")
    print("="*80)
    
    # Create screener and load data
    screener = TokenScreener()
    screener.load_from_json("data/top10_solana_coins.json")
    
    # Run screening
    scores = screener.score_tokens()
    
    # Print top 5
    print("\n[STATS] TOP 5 BY HYPE SCORE:\n")
    for i, score in enumerate(screener.get_top_picks(5), 1):
        t = score.token
        print(f"{i}. {t.symbol} - Hype Score: {score.total_hype_score:.1f}")
        print(f"   Price: ${t.price_usd:.6f} | 24h: {t.change_24h:+.1f}% | 7d: {t.change_7d:+.1f}%")
        print(f"   Risk: {score.risk_level.name} | Category: {score.category.value}")
        print()
    
    return screener


def demo_sentiment_analysis():
    """Demo: Sentiment analysis"""
    print("\n" + "="*80)
    print("DEMO 2: Sentiment Analysis")
    print("="*80)
    
    analyzer = SentimentAnalyzer()
    
    # Example social metrics
    social = SocialMetrics(
        mentions_24h=5000,
        mentions_change=250,
        engagement_rate=0.06,
        bullish_vs_bearish=3.0,
        influencer_mentions=15,
        influencer_change=200
    )
    
    community = CommunityMetrics(
        holders=5000,
        holder_change_24h=800,
        holder_change_7d=2000,
        new_wallets_24h=750,
        active_wallets_24h=2000,
        social_growth_rate=35
    )
    
    score = analyzer.analyze_social_metrics("EXAMPLE", social, community)
    
    print(f"\n[CHART] Sentiment Analysis for EXAMPLE:\n")
    print(f"   Social Score: {score.social_score:.1f}/100")
    print(f"   Community Score: {score.community_score:.1f}/100")
    print(f"   Composite: {score.composite_score:.1f}/100")
    print(f"   Sentiment: {score.overall_sentiment.value} ({score.sentiment_strength.name})")
    
    if score.key_drivers:
        print(f"\n   [DRIVERS] Key Drivers:")
        for driver in score.key_drivers:
            print(f"      • {driver}")
    
    if score.warnings:
        print(f"\n   [WARN]  Warnings:")
        for warning in score.warnings:
            print(f"      • {warning}")


def demo_hype_cycle_detection():
    """Demo: Hype cycle detection"""
    print("\n" + "="*80)
    print("DEMO 3: Hype Cycle Detection")
    print("="*80)
    
    detector = HypeCycleDetector()
    
    # Example tokens with different phases
    examples = [
        ("BOOB", 98.8, 140.0, 8.5, 5.0, 800),
        ("GBOY", 41.0, 20.1, 2.5, 2.0, 400),
        ("FARTCOIN", 3.3, 28.9, 1.2, 1.1, 1200),
        ("67COIN", 22.9, 3934.4, 15.0, 12.0, 500),
    ]
    
    print("\n[CYCLE] Hype Cycle Analysis:\n")
    print(f"{'Token':<12}{'24h%':<10}{'7d%':<12}{'Phase':<15}{'Advice'}")
    print("-"*80)
    
    for symbol, chg24, chg7d, vol_spike, soc_spike, holders in examples:
        phase = detector.detect_phase(chg24, chg7d, vol_spike, soc_spike, holders)
        advice = detector.get_phase_advice(phase)
        print(f"{symbol:<12}{chg24:>+7.1f}%  {chg7d:>+7.1f}%    {phase.value:<15}{advice[:40]}...")


def demo_multi_token_feed():
    """Demo: Multi-token feed integration"""
    print("\n" + "="*80)
    print("DEMO 4: Multi-Token Feed & Trading Dashboard")
    print("="*80)
    
    feed = MultiTokenFeed()
    
    # Get ranked tokens
    ranked = feed.get_ranked_tokens(min_hype_score=70)
    
    print(f"\n[DATA] Tokens with Hype Score >= 70: {len(ranked)}\n")
    print(f"{'Rank':<6}{'Symbol':<10}{'Hype':<10}{'Risk':<12}{'Phase':<12}{'Composite'}")
    print("-"*70)
    
    for i, token in enumerate(ranked[:10], 1):
        h = token.hype
        print(f"{i:<6}{token.metrics.symbol:<10}{h.total_hype_score:.1f}      "
              f"{h.risk_level.name:<12}{token.phase:<12}{token.composite_rank():.1f}")
    
    # Best scalping candidates
    print("\n" + "-"*70)
    print("\n[TARGET] BEST SCALPING CANDIDATES:\n")
    
    scalping = feed.get_best_scalping_candidates(5)
    for i, token in enumerate(scalping, 1):
        m = token.metrics
        vmc = m.volume_to_mcap_ratio()
        print(f"{i}. {m.symbol} - Vol/MCap: {vmc:.2f}x, Liquidity: ${m.liquidity_usd/1e6:.1f}M")
    
    return feed


def demo_integration_with_strategy():
    """Demo: How to integrate with existing scalping strategy"""
    print("\n" + "="*80)
    print("DEMO 5: Integration with Scalping Strategy")
    print("="*80)
    
    feed = MultiTokenFeed()
    
    # Get top candidate
    candidates = feed.get_best_scalping_candidates(1)
    
    if not candidates:
        print("No suitable candidates found")
        return
    
    token = candidates[0]
    
    print(f"\n[TARGET] SELECTED TRADING PAIR: {token.metrics.symbol}")
    print("-"*50)
    
    # Show technical context
    print(f"\n[CHART] Technical Context:")
    print(f"   Current Price: ${token.metrics.price_usd:.6f}")
    print(f"   24h Change: {token.metrics.change_24h:+.1f}%")
    print(f"   Volume: ${token.metrics.volume_24h:,.0f}")
    print(f"   Liquidity: ${token.metrics.liquidity_usd:,.0f}")
    
    # Show recommended strategy adjustments
    print(f"\n[CONFIG]  Strategy Adjustments:")
    
    if token.hype.risk_level == RiskLevel.EXTREME:
        print("   • Position Size: Reduce to $1.50 (50% of normal)")
        print("   • Stop Loss: 1.0% (tighter than usual 1.5%)")
        print("   • Take Profit: 2% / 3% (faster exits)")
        print("   • Max Hold Time: 15 minutes")
    elif token.hype.risk_level == RiskLevel.HIGH:
        print("   • Position Size: $2.25 (75% of normal)")
        print("   • Stop Loss: 1.5% (standard)")
        print("   • Take Profit: 2.5% / 4% (standard)")
        print("   • Max Hold Time: 30 minutes")
    else:
        print("   • Position Size: $3.00 (standard)")
        print("   • Stop Loss: 1.5% (standard)")
        print("   • Take Profit: 2.5% / 4% (standard)")
        print("   • Max Hold Time: 60 minutes")
    
    # Entry strategy
    print(f"\n[PLAN] Recommended Entry Strategy:")
    
    if token.phase == "early":
        print("   1. Wait for price to touch lower Bollinger Band")
        print("   2. Confirm RSI between 25-35")
        print("   3. Enter with full position size")
        print("   4. Target: Middle band (TP1), Upper band (TP2)")
    elif token.phase == "accel":
        print("   1. Use 15m timeframe for faster signals")
        print("   2. Enter on any pullback to lower BB")
        print("   3. Be ready to exit quickly on momentum loss")
    elif token.phase == "parabolic":
        print("   ⚠️  PARABOLIC PHASE - EXTREME CAUTION")
        print("   1. Only enter if you're watching the chart")
        print("   2. Use 5m timeframe")
        print("   3. Set stop loss immediately after entry")
        print("   4. Take profit at 2% no matter what")
    
    print(f"\n[TIP] Pair Address: {token.metrics.address}")


def demo_export_watchlist():
    """Demo: Export watchlist for bot"""
    print("\n" + "="*80)
    print("DEMO 6: Export Watchlist")
    print("="*80)
    
    feed = MultiTokenFeed()
    filepath = feed.export_watchlist("data/my_watchlist.json")
    
    print(f"\n[OK] Watchlist exported to: {filepath}")
    print("\nYou can now use this watchlist with your trading bot:")
    print("""
    # In your trading script:
    import json
    
    with open('data/my_watchlist.json') as f:
        watchlist = json.load(f)
    
    for token in watchlist['watchlist']:
        if token['recommended']:
            print(f"Trading {token['symbol']} - Hype: {token['hype_score']}")
            # Setup trading pair...
    """)


def main():
    """Run all demos"""
    print("\n" + "="*40)
    print("  SOLANA SNAIL SCALP - TOKEN SCREENING SYSTEM")
    print("  Technical + Sentiment Analysis for Hype Trading")
    print("="*40)
    
    # Run demos
    screener = demo_basic_screening()
    demo_sentiment_analysis()
    demo_hype_cycle_detection()
    feed = demo_multi_token_feed()
    demo_integration_with_strategy()
    demo_export_watchlist()
    
    print("\n" + "="*80)
    print("[DONE] All demos complete!")
    print("="*80)
    print("""
Next steps:
1. Review the top picks in data/top10_solana_coins.json
2. Check data/hype_screening_report.json for full analysis
3. Use MultiTokenFeed in your trading script
4. Customize risk levels and filters in your config

Happy scalping!
    """)


if __name__ == "__main__":
    main()
