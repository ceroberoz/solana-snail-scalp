"""Multi-Token Data Feed with Hype Screening Integration

Extends the basic data feed to support multiple tokens
with automatic hype-based filtering and ranking.
"""

import aiohttp
import asyncio
import json
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from snail_scalp.token_screener import (
    TokenScreener, TokenMetrics, HypeScore, 
    HypeCategory, RiskLevel
)
from snail_scalp.sentiment_analysis import (
    SentimentAnalyzer, SocialMetrics, CommunityMetrics,
    SentimentScore, HypeCycleDetector
)


@dataclass
class TokenData:
    """Combined token data with all metrics"""
    metrics: TokenMetrics
    hype: Optional[HypeScore] = None
    sentiment: Optional[SentimentScore] = None
    phase: Optional[str] = None
    
    # Trading specific
    pair_address: str = ""
    is_tradable: bool = False
    last_update: datetime = field(default_factory=datetime.now)
    
    def composite_rank(self) -> float:
        """Calculate composite ranking score"""
        scores = []
        if self.hype:
            scores.append(self.hype.total_hype_score * 0.5)
        if self.sentiment:
            scores.append(self.sentiment.composite_score * 0.3)
        if self.phase:
            # Bonus for early phases
            phase_bonus = {
                "early": 20, "accel": 15, "parabolic": 5,
                "dist": -10, "decline": -20, "accum": 5
            }
            scores.append(phase_bonus.get(self.phase, 0))
        
        return sum(scores) / max(len(scores), 1) if scores else 0


class MultiTokenFeed:
    """Feed that manages multiple tokens with hype screening"""
    
    def __init__(
        self,
        data_file: str = "data/top10_solana_coins.json",
        auto_screen: bool = True,
        min_risk_level: Optional[RiskLevel] = None
    ):
        self.data_file = Path(data_file)
        self.tokens: Dict[str, TokenData] = {}
        self.screener = TokenScreener()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.hype_detector = HypeCycleDetector()
        
        self.auto_screen = auto_screen
        self.min_risk_level = min_risk_level
        
        # Load and process
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from JSON and process"""
        if not self.data_file.exists():
            raise FileNotFoundError(f"Token data file not found: {self.data_file}")
        
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        # Convert to TokenMetrics
        metrics_list = []
        for item in data.get('tokens', []):
            m = item['metrics']
            metrics_list.append(TokenMetrics(
                symbol=item['symbol'],
                name=item['name'],
                address=item.get('contract_address', ''),
                price_usd=m['price_usd'],
                market_cap=m['market_cap'],
                volume_24h=m['volume_24h'],
                liquidity_usd=m['liquidity_usd'],
                change_1h=m.get('change_1h', 0),
                change_24h=m.get('change_24h', 0),
                change_7d=m.get('change_7d', 0),
                change_30d=m.get('change_30d', 0),
                holders=m.get('holders', 0),
                fdv=m.get('fdv', 0)
            ))
        
        # Run screening if enabled
        if self.auto_screen:
            self.screener.tokens = metrics_list
            hype_scores = self.screener.score_tokens()
            
            # Create TokenData objects
            for score in hype_scores:
                symbol = score.token.symbol
                
                # Detect phase
                volume_avg = score.token.volume_24h / max(score.token.market_cap, 1)
                phase = self.hype_detector.detect_phase(
                    price_change_24h=score.token.change_24h,
                    price_change_7d=score.token.change_7d,
                    volume_spike=volume_avg * 10,  # Approximate
                    social_spike=1.5,  # Default
                    holder_velocity=score.token.holders / 30  # Approx daily
                )
                
                self.tokens[symbol] = TokenData(
                    metrics=score.token,
                    hype=score,
                    phase=phase.value,
                    is_tradable=score.risk_level.value <= (self.min_risk_level.value if self.min_risk_level else 5)
                )
        else:
            # Just load without screening
            for m in metrics_list:
                self.tokens[m.symbol] = TokenData(metrics=m, is_tradable=True)
    
    def get_ranked_tokens(
        self,
        min_hype_score: float = 0,
        max_risk: Optional[RiskLevel] = None,
        category: Optional[HypeCategory] = None
    ) -> List[TokenData]:
        """Get tokens ranked by composite score"""
        results = list(self.tokens.values())
        
        # Apply filters
        if min_hype_score > 0:
            results = [t for t in results 
                      if t.hype and t.hype.total_hype_score >= min_hype_score]
        
        if max_risk:
            results = [t for t in results 
                      if t.hype and t.hype.risk_level.value <= max_risk.value]
        
        if category:
            results = [t for t in results 
                      if t.hype and t.hype.category == category]
        
        # Sort by composite rank
        results.sort(key=lambda x: x.composite_rank(), reverse=True)
        return results
    
    def get_best_scalping_candidates(
        self,
        n: int = 5,
        require_liquidity_usd: float = 1_000_000
    ) -> List[TokenData]:
        """Get tokens best suited for scalping strategy"""
        candidates = []
        
        for token in self.tokens.values():
            # Must have hype data
            if not token.hype:
                continue
            
            # Must have adequate liquidity
            if token.metrics.liquidity_usd < require_liquidity_usd:
                continue
            
            # Skip extreme risk for scalping (too unpredictable)
            if token.hype.risk_level == RiskLevel.EXTREME:
                continue
            
            # Prefer high volume for easy exits
            vmc = token.metrics.volume_to_mcap_ratio()
            if vmc < 0.1:
                continue
            
            # Calculate scalping score
            score = 0
            
            # Volume is king for scalping
            score += min(vmc * 30, 40)
            
            # Momentum provides opportunity
            score += token.hype.momentum_score * 0.3
            
            # Liquidity reduces slippage
            lmc = token.metrics.liquidity_to_mcap_ratio()
            score += min(lmc * 20, 20)
            
            # Avoid parabolic phases (too risky)
            if token.phase == "parabolic":
                score -= 20
            elif token.phase == "accel":
                score += 10
            
            candidates.append((token, score))
        
        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in candidates[:n]]
    
    def get_watchlist_for_trading_window(
        self,
        window_hours: int = 2
    ) -> List[TokenData]:
        """Get tokens to watch during trading session"""
        # Get top candidates
        candidates = self.get_ranked_tokens(min_hype_score=60)
        
        # Prioritize by:
        # 1. Good liquidity (can enter/exit)
        # 2. Active phase (momentum)
        # 3. Recent 1h activity (immediate interest)
        
        prioritized = []
        for token in candidates:
            priority = 0
            
            # Liquidity priority
            if token.metrics.liquidity_usd > 5_000_000:
                priority += 3
            elif token.metrics.liquidity_usd > 1_000_000:
                priority += 2
            
            # Phase priority
            if token.phase in ["early", "accel"]:
                priority += 2
            elif token.phase == "parabolic":
                priority += 1  # Still interesting but risky
            
            # Recent activity
            if token.metrics.change_1h > 5:
                priority += 2
            elif token.metrics.change_1h > 0:
                priority += 1
            
            prioritized.append((token, priority))
        
        prioritized.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in prioritized[:10]]
    
    def print_trading_dashboard(self):
        """Print formatted trading dashboard"""
        print("\n" + "="*90)
        print("[ROCKET] SOLANA SCALPING DASHBOARD - TOP HYPE COINS")
        print("="*90)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
        print("-"*90)
        
        # Best scalping candidates
        print("\n[TARGET] TOP SCALPING CANDIDATES (Liquidity + Momentum):\n")
        scalping = self.get_best_scalping_candidates(5)
        
        print(f"{'#':<4}{'Symbol':<10}{'Price':<12}{'24h%':<10}{'Vol/MCap':<12}{'Phase':<12}{'Risk':<10}{'Score'}")
        print("-"*90)
        
        for i, token in enumerate(scalping, 1):
            m = token.metrics
            h = token.hype
            vmc = m.volume_to_mcap_ratio()
            
            print(f"{i:<4}{m.symbol:<10}${m.price_usd:<10.6f}{m.change_24h:>+7.1f}%  "
                  f"{vmc:>8.2f}x  {token.phase:<12}{h.risk_level.name:<10}"
                  f"{token.composite_rank():.1f}")
        
        # Risk breakdown
        print("\n" + "-"*90)
        print("[DATA] BY RISK CATEGORY:\n")
        
        for risk in [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.EXTREME]:
            tokens = [t for t in self.tokens.values() 
                     if t.hype and t.hype.risk_level == risk]
            if tokens:
                print(f"  {risk.name}: {len(tokens)} tokens")
                for t in sorted(tokens, key=lambda x: x.hype.total_hype_score, reverse=True)[:3]:
                    print(f"    • {t.metrics.symbol} (Hype: {t.hype.total_hype_score:.1f})")
        
        # Trading recommendations
        print("\n" + "="*90)
        print("[TIP] TRADING RECOMMENDATIONS:")
        print("="*90)
        
        watchlist = self.get_watchlist_for_trading_window()
        print("\n[LIST] 2-HOUR TRADING WATCHLIST:\n")
        
        for i, token in enumerate(watchlist[:5], 1):
            m = token.metrics
            h = token.hype
            
            print(f"{i}. {m.symbol} (${m.price_usd:.6f})")
            print(f"   24h: {m.change_24h:+.1f}% | 7d: {m.change_7d:+.1f}% | "
                  f"Liquidity: ${m.liquidity_usd/1e6:.1f}M")
            print(f"   Phase: {token.phase} | Risk: {h.risk_level.name}")
            
            # Entry suggestion
            if token.phase in ["early", "accel"]:
                print(f"   [TIP] Strategy: Wait for pullback to lower BB, RSI 25-35")
            elif token.phase == "parabolic":
                print(f"   [WARN]  Strategy: QUICK SCALPS ONLY - Tight 1% stops")
            else:
                print(f"   [PAUSE]  Strategy: Wait for better setup")
            print()
        
        print("="*90)
    
    def export_watchlist(self, filepath: str = "data/trading_watchlist.json"):
        """Export current watchlist for bot consumption"""
        watchlist = self.get_watchlist_for_trading_window()
        
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "watchlist": []
        }
        
        for token in watchlist:
            export_data["watchlist"].append({
                "symbol": token.metrics.symbol,
                "address": token.metrics.address,
                "price": token.metrics.price_usd,
                "liquidity_usd": token.metrics.liquidity_usd,
                "hype_score": token.hype.total_hype_score if token.hype else 0,
                "risk_level": token.hype.risk_level.name if token.hype else "UNKNOWN",
                "phase": token.phase,
                "recommended": token.phase in ["early", "accel", "parabolic"],
                "change_24h": token.metrics.change_24h,
                "volume_24h": token.metrics.volume_24h
            })
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filepath


def integrate_with_config():
    """Show how to integrate with existing config"""
    from snail_scalp.config import StrategyConfig, trading_config
    
    # Create multi-token feed
    feed = MultiTokenFeed()
    
    # Get best scalping candidate for the day
    best = feed.get_best_scalping_candidates(1)
    
    if best:
        token = best[0]
        print(f"\n🎯 RECOMMENDED PAIR FOR TODAY: {token.metrics.symbol}")
        print(f"   Price: ${token.metrics.price_usd}")
        print(f"   Liquidity: ${token.metrics.liquidity_usd:,.0f}")
        print(f"   24h Change: {token.metrics.change_24h:+.1f}%")
        print(f"   Risk Level: {token.hype.risk_level.name}")
        
        # Adjust strategy based on risk
        if token.hype.risk_level == RiskLevel.EXTREME:
            print("\n⚠️  EXTREME RISK - Adjusting strategy:")
            print("   • Reduce position size by 50%")
            print("   • Tighter stops (1% instead of 1.5%)")
            print("   • Quick exits - don't hold through consolidation")
    
    return feed


if __name__ == "__main__":
    # Run full demo
    feed = MultiTokenFeed()
    feed.print_trading_dashboard()
    
    # Export watchlist
    filepath = feed.export_watchlist()
    print(f"\n✅ Watchlist exported to: {filepath}")
    
    # Show integration example
    print("\n" + "="*90)
    integrate_with_config()
