"""Social Sentiment Analysis for Solana Tokens

Analyzes social signals to gauge token hype:
- Social volume and engagement metrics
- Community growth indicators
- FOMO/Fear indicators
- Whale activity signals
"""

import json
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import re


class SentimentType(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class SignalStrength(Enum):
    VERY_STRONG = 5
    STRONG = 4
    MODERATE = 3
    WEAK = 2
    VERY_WEAK = 1


@dataclass
class SocialMetrics:
    """Social engagement metrics"""
    mentions_24h: int = 0
    mentions_change: float = 0.0  # % change vs previous 24h
    
    engagement_rate: float = 0.0  # likes + comments / impressions
    engagement_change: float = 0.0
    
    bullish_vs_bearish: float = 1.0  # ratio >1 = more bullish
    
    influencer_mentions: int = 0
    influencer_change: float = 0.0


@dataclass
class CommunityMetrics:
    """Community growth metrics"""
    holders: int = 0
    holder_change_24h: int = 0
    holder_change_7d: int = 0
    
    new_wallets_24h: int = 0
    active_wallets_24h: int = 0
    
    discord_members: int = 0
    telegram_members: int = 0
    social_growth_rate: float = 0.0  # % daily


@dataclass
class OnChainSentiment:
    """On-chain sentiment indicators"""
    buy_pressure: float = 0.0  # buy vol / sell vol ratio
    whale_accumulation: float = 0.0  # net whale inflow
    
    smart_money_flow: float = 0.0  # + = inflow, - = outflow
    retail_fomo_score: float = 0.0  # 0-100, higher = more retail buying
    
    large_tx_count_24h: int = 0  # $10k+ transactions
    large_tx_change: float = 0.0


@dataclass
class SentimentScore:
    """Composite sentiment analysis"""
    symbol: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Individual components (0-100)
    social_score: float = 50.0
    community_score: float = 50.0
    onchain_score: float = 50.0
    
    # Combined
    overall_sentiment: SentimentType = SentimentType.NEUTRAL
    sentiment_strength: SignalStrength = SignalStrength.WEAK
    composite_score: float = 50.0  # 0-100, >60 bullish, <40 bearish
    
    # Analysis
    key_drivers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "scores": {
                "social": round(self.social_score, 2),
                "community": round(self.community_score, 2),
                "onchain": round(self.onchain_score, 2),
                "composite": round(self.composite_score, 2)
            },
            "sentiment": self.overall_sentiment.value,
            "strength": self.sentiment_strength.name,
            "key_drivers": self.key_drivers,
            "warnings": self.warnings
        }


class SentimentAnalyzer:
    """Analyze token sentiment from multiple sources"""
    
    # Keywords for basic sentiment detection
    BULLISH_KEYWORDS = [
        "moon", "pump", "bull", "accumulate", "gem", "alpha", "10x", "100x",
        " ATH", "breakout", "send it", "wagmi", "diamond hands", "inverse",
        "long", "buy", "support", "bouncing", "ripping", "flying"
    ]
    
    BEARISH_KEYWORDS = [
        "dump", "bear", "crash", "rug", "scam", "exit", "sell", "short",
        "rekt", "ngmi", "paper hands", "correction", "dip", "falling",
        "resistance", "rejection", "overbought", "distribution"
    ]
    
    FOMO_KEYWORDS = [
        "fomo", "missed", "next", "don't miss", "last chance", "exploding",
        "trending", "viral", "hype", "fomoing", "ape in", "send"
    ]
    
    def __init__(self):
        self.cache: Dict[str, SentimentScore] = {}
        self.cache_ttl = timedelta(minutes=15)
        self._cache_time: Dict[str, datetime] = {}
    
    def analyze_social_metrics(
        self,
        symbol: str,
        social: SocialMetrics,
        community: CommunityMetrics
    ) -> SentimentScore:
        """Calculate sentiment from social and community metrics"""
        
        score = SentimentScore(symbol=symbol)
        
        # Social score calculation
        social_score = 50.0
        
        # Mentions momentum
        if social.mentions_change > 200:
            social_score += 25
        elif social.mentions_change > 100:
            social_score += 20
        elif social.mentions_change > 50:
            social_score += 15
        elif social.mentions_change > 20:
            social_score += 10
        elif social.mentions_change < -50:
            social_score -= 20
        
        # Engagement quality
        if social.engagement_rate > 0.05:  # 5%+
            social_score += 15
        elif social.engagement_rate > 0.03:
            social_score += 10
        elif social.engagement_rate > 0.01:
            social_score += 5
        
        # Sentiment ratio
        if social.bullish_vs_bearish > 3:
            social_score += 10
        elif social.bullish_vs_bearish > 2:
            social_score += 5
        elif social.bullish_vs_bearish < 0.5:
            social_score -= 10
        
        # Influencer activity
        if social.influencer_change > 100:
            social_score += 10
        elif social.influencer_change > 50:
            social_score += 5
        
        score.social_score = max(0, min(100, social_score))
        
        # Community score calculation
        community_score = 50.0
        
        # Holder growth
        if community.holder_change_24h > 1000:
            community_score += 20
        elif community.holder_change_24h > 500:
            community_score += 15
        elif community.holder_change_24h > 100:
            community_score += 10
        elif community.holder_change_24h < -100:
            community_score -= 15
        
        # Wallet activity
        active_ratio = community.active_wallets_24h / max(community.holders, 1)
        if active_ratio > 0.3:  # 30%+ active
            community_score += 15
        elif active_ratio > 0.2:
            community_score += 10
        elif active_ratio > 0.1:
            community_score += 5
        
        # Social channel growth
        if community.social_growth_rate > 20:
            community_score += 15
        elif community.social_growth_rate > 10:
            community_score += 10
        elif community.social_growth_rate > 5:
            community_score += 5
        
        score.community_score = max(0, min(100, community_score))
        
        # Composite calculation
        score.composite_score = (
            score.social_score * 0.5 +
            score.community_score * 0.5
        )
        
        # Determine sentiment type
        score.overall_sentiment = self._classify_sentiment(score.composite_score)
        score.sentiment_strength = self._classify_strength(score.composite_score)
        
        # Generate insights
        score.key_drivers = self._identify_drivers(social, community)
        score.warnings = self._identify_warnings(social, community)
        
        # Cache result
        self.cache[symbol] = score
        self._cache_time[symbol] = datetime.now()
        
        return score
    
    def analyze_onchain(
        self,
        symbol: str,
        onchain: OnChainSentiment
    ) -> SentimentScore:
        """Calculate sentiment from on-chain metrics"""
        
        score = SentimentScore(symbol=symbol)
        
        onchain_score = 50.0
        
        # Buy pressure
        if onchain.buy_pressure > 2.0:  # 2:1 buy:sell
            onchain_score += 20
        elif onchain.buy_pressure > 1.5:
            onchain_score += 15
        elif onchain.buy_pressure > 1.2:
            onchain_score += 10
        elif onchain.buy_pressure < 0.8:
            onchain_score -= 15
        
        # Whale activity
        if onchain.whale_accumulation > 100_000:  # $100k+ net inflow
            onchain_score += 15
        elif onchain.whale_accumulation > 50_000:
            onchain_score += 10
        elif onchain.whale_accumulation < -50_000:
            onchain_score -= 10
        
        # Smart money
        if onchain.smart_money_flow > 50_000:
            onchain_score += 15
        elif onchain.smart_money_flow > 20_000:
            onchain_score += 10
        elif onchain.smart_money_flow < -20_000:
            onchain_score -= 10
        
        # Large transactions
        if onchain.large_tx_change > 100:
            onchain_score += 10
        elif onchain.large_tx_change > 50:
            onchain_score += 5
        
        score.onchain_score = max(0, min(100, onchain_score))
        score.composite_score = score.onchain_score
        score.overall_sentiment = self._classify_sentiment(score.composite_score)
        score.sentiment_strength = self._classify_strength(score.composite_score)
        
        return score
    
    def _classify_sentiment(self, score: float) -> SentimentType:
        """Classify score into sentiment type"""
        if score >= 70:
            return SentimentType.BULLISH
        elif score >= 60:
            return SentimentType.MIXED  # Leaning bullish
        elif score <= 30:
            return SentimentType.BEARISH
        elif score <= 40:
            return SentimentType.MIXED  # Leaning bearish
        else:
            return SentimentType.NEUTRAL
    
    def _classify_strength(self, score: float) -> SignalStrength:
        """Classify signal strength"""
        if score >= 85:
            return SignalStrength.VERY_STRONG
        elif score >= 70:
            return SignalStrength.STRONG
        elif score >= 60:
            return SignalStrength.MODERATE
        elif score >= 45:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK
    
    def _identify_drivers(
        self,
        social: SocialMetrics,
        community: CommunityMetrics
    ) -> List[str]:
        """Identify key sentiment drivers"""
        drivers = []
        
        if social.mentions_change > 100:
            drivers.append(f"Social mentions up {social.mentions_change:.0f}%")
        
        if community.holder_change_24h > 500:
            drivers.append(f"Strong holder growth (+{community.holder_change_24h})")
        
        if social.bullish_vs_bearish > 2:
            drivers.append("Bullish sentiment dominant")
        
        if social.influencer_change > 50:
            drivers.append("Influencer attention increasing")
        
        if community.social_growth_rate > 10:
            drivers.append(f"Community growing fast ({community.social_growth_rate:.1f}%/day)")
        
        return drivers
    
    def _identify_warnings(
        self,
        social: SocialMetrics,
        community: CommunityMetrics
    ) -> List[str]:
        """Identify potential red flags"""
        warnings = []
        
        if social.mentions_change > 500:
            warnings.append("Extreme social spike - potential top")
        
        if community.holder_change_24h > 5000:
            warnings.append("Unsustainable holder growth - watch for drop")
        
        if social.bullish_vs_bearish > 5:
            warnings.append("Euphoria levels - contrarian signal")
        
        if community.active_wallets_24h / max(community.holders, 1) < 0.05:
            warnings.append("Low wallet activity relative to holders")
        
        return warnings
    
    def analyze_text_sentiment(self, text: str) -> Tuple[SentimentType, float]:
        """Basic sentiment analysis from text"""
        text_lower = text.lower()
        
        bullish_count = sum(1 for kw in self.BULLISH_KEYWORDS if kw in text_lower)
        bearish_count = sum(1 for kw in self.BEARISH_KEYWORDS if kw in text_lower)
        fomo_count = sum(1 for kw in self.FOMO_KEYWORDS if kw in text_lower)
        
        total = bullish_count + bearish_count
        if total == 0:
            return SentimentType.NEUTRAL, 0.0
        
        sentiment_score = (bullish_count - bearish_count) / total
        
        # Adjust for FOMO indicators
        if fomo_count > 2:
            sentiment_score += 0.2
        
        if sentiment_score > 0.3:
            return SentimentType.BULLISH, sentiment_score
        elif sentiment_score < -0.3:
            return SentimentType.BEARISH, sentiment_score
        else:
            return SentimentType.NEUTRAL, sentiment_score
    
    def get_cached(self, symbol: str) -> Optional[SentimentScore]:
        """Get cached sentiment if still fresh"""
        if symbol in self.cache:
            cached_time = self._cache_time.get(symbol)
            if cached_time and datetime.now() - cached_time < self.cache_ttl:
                return self.cache[symbol]
        return None
    
    def get_sentiment_summary(
        self,
        symbols: List[str],
        social_data: Dict[str, SocialMetrics],
        community_data: Dict[str, CommunityMetrics]
    ) -> Dict[str, SentimentScore]:
        """Get sentiment for multiple tokens"""
        results = {}
        
        for symbol in symbols:
            # Check cache first
            cached = self.get_cached(symbol)
            if cached:
                results[symbol] = cached
                continue
            
            # Calculate new sentiment
            social = social_data.get(symbol, SocialMetrics())
            community = community_data.get(symbol, CommunityMetrics())
            
            score = self.analyze_social_metrics(symbol, social, community)
            results[symbol] = score
        
        return results


class HypeCycleDetector:
    """Detect which phase of hype cycle a token is in"""
    
    class Phase(Enum):
        EARLY = "early"           # Smart money accumulating
        ACCELERATION = "accel"    # Early momentum
        PARABOLIC = "parabolic"   # Mainstream FOMO
        DISTRIBUTION = "dist"     # Smart money exiting
        DECLINE = "decline"       # Hype fading
        ACCUMULATION = "accum"    # Bottoming, preparing for next cycle
    
    def detect_phase(
        self,
        price_change_24h: float,
        price_change_7d: float,
        volume_spike: float,  # current vol / avg vol
        social_spike: float,  # current mentions / avg mentions
        holder_velocity: float  # new holders per day
    ) -> Phase:
        """Determine hype cycle phase"""
        
        # Parabolic phase: extreme price + volume + social
        if price_change_24h > 50 and volume_spike > 5 and social_spike > 3:
            return self.Phase.PARABOLIC
        
        # Acceleration: strong momentum building
        if price_change_24h > 20 and price_change_7d > 50 and volume_spike > 2:
            return self.Phase.ACCELERATION
        
        # Early phase: moderate gains, low volume/social but growing
        if price_change_7d > 20 and price_change_24h < 20 and volume_spike > 1.5:
            return self.Phase.EARLY
        
        # Distribution: high volume but price stalling
        if volume_spike > 3 and price_change_24h < 10 and price_change_24h > -10:
            return self.Phase.DISTRIBUTION
        
        # Decline: negative momentum
        if price_change_24h < -10 and price_change_7d < 0:
            return self.Phase.DECLINE
        
        # Accumulation: low activity, bottoming
        if volume_spike < 0.5 and abs(price_change_24h) < 5:
            return self.Phase.ACCUMULATION
        
        return self.Phase.ACCELERATION  # Default
    
    def get_phase_advice(self, phase: Phase) -> str:
        """Get trading advice for each phase"""
        advice = {
            self.Phase.EARLY: "Good entry zone. Smart money accumulating. Low risk.",
            self.Phase.ACCELERATION: "Momentum building. Can enter with tight stops.",
            self.Phase.PARABOLIC: "EXTREME RISK. Only for quick scalps. Watch for dump.",
            self.Phase.DISTRIBUTION: "Smart money selling. Avoid or short.",
            self.Phase.DECLINE: "Wait for accumulation phase before entering.",
            self.Phase.ACCUMULATION: "Prepare for next cycle. Watch for breakout.",
        }
        return advice.get(phase, "Unknown phase - proceed with caution")


# Demo/mock data for testing
DEMO_SOCIAL_DATA = {
    "BOOB": SocialMetrics(
        mentions_24h=5000,
        mentions_change=450,
        engagement_rate=0.08,
        bullish_vs_bearish=3.5,
        influencer_mentions=12,
        influencer_change=200
    ),
    "GBOY": SocialMetrics(
        mentions_24h=3200,
        mentions_change=180,
        engagement_rate=0.06,
        bullish_vs_bearish=2.8,
        influencer_mentions=8,
        influencer_change=150
    ),
    "FARTCOIN": SocialMetrics(
        mentions_24h=15000,
        mentions_change=25,
        engagement_rate=0.04,
        bullish_vs_bearish=1.8,
        influencer_mentions=45,
        influencer_change=10
    ),
}

DEMO_COMMUNITY_DATA = {
    "BOOB": CommunityMetrics(
        holders=2500,
        holder_change_24h=800,
        holder_change_7d=1800,
        new_wallets_24h=750,
        active_wallets_24h=1200,
        social_growth_rate=45
    ),
    "GBOY": CommunityMetrics(
        holders=4500,
        holder_change_24h=600,
        holder_change_7d=1500,
        new_wallets_24h=550,
        active_wallets_24h=2000,
        social_growth_rate=25
    ),
    "FARTCOIN": CommunityMetrics(
        holders=45000,
        holder_change_24h=1200,
        holder_change_7d=8500,
        new_wallets_24h=1000,
        active_wallets_24h=15000,
        social_growth_rate=8
    ),
}


def demo():
    """Run sentiment analysis demo"""
    print("\n" + "="*70)
    print("[DATA] SENTIMENT ANALYSIS DEMO")
    print("="*70)
    
    analyzer = SentimentAnalyzer()
    
    symbols = ["BOOB", "GBOY", "FARTCOIN"]
    
    results = analyzer.get_sentiment_summary(
        symbols,
        DEMO_SOCIAL_DATA,
        DEMO_COMMUNITY_DATA
    )
    
    print("\n[RISE] SENTIMENT SCORES:\n")
    print(f"{'Token':<12}{'Social':<10}{'Community':<12}{'Composite':<12}{'Sentiment'}")
    print("-"*70)
    
    for symbol, score in results.items():
        print(f"{symbol:<12}{score.social_score:.1f}      {score.community_score:.1f}        "
              f"{score.composite_score:.1f}        {score.overall_sentiment.value} "
              f"({score.sentiment_strength.name})")
        
        if score.key_drivers:
            print(f"   🚀 Drivers: {', '.join(score.key_drivers[:2])}")
        if score.warnings:
            print(f"   ⚠️  Warnings: {', '.join(score.warnings[:2])}")
        print()
    
    # Hype cycle detection
    print("\n[CYCLE] HYPE CYCLE ANALYSIS:\n")
    detector = HypeCycleDetector()
    
    test_tokens = [
        ("BOOB", 98.8, 140.0, 8.5, 5.0, 800),
        ("FARTCOIN", 3.3, 28.9, 1.2, 1.1, 1200),
        ("67COIN", 22.9, 3934.4, 15.0, 12.0, 500),
    ]
    
    for symbol, chg24, chg7d, vol_spike, soc_spike, holders in test_tokens:
        phase = detector.detect_phase(chg24, chg7d, vol_spike, soc_spike, holders)
        print(f"{symbol:<12} Phase: {phase.value:<12} | {detector.get_phase_advice(phase)}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    demo()
