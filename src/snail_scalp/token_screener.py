"""Token Screening & Hype Analysis for Solana Ecosystem

Filters and ranks Solana tokens based on:
- Technical indicators (momentum, volume, volatility)
- Sentiment metrics (social buzz, community growth)
- Risk factors (liquidity, holder distribution)
"""

import json
import aiohttp
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import numpy as np


class HypeCategory(Enum):
    EXTREME = "extreme"      # >50% 24h gain - very high risk/reward
    HIGH = "high"            # 20-50% 24h gain - strong momentum
    MODERATE = "moderate"    # 5-20% 24h gain - steady hype
    STABLE = "stable"        # 0-5% 24h gain - established


class RiskLevel(Enum):
    EXTREME = 5    # New coins, extreme pumps
    HIGH = 4       # High volatility, low liquidity
    MODERATE = 3   # Medium cap, decent liquidity
    LOW = 2        # Large cap, good liquidity
    MINIMAL = 1    # Top tier, established


@dataclass
class TokenMetrics:
    """Technical metrics for a token"""
    symbol: str
    name: str
    address: str
    price_usd: float
    market_cap: float
    volume_24h: float
    liquidity_usd: float
    
    # Performance metrics
    change_1h: float = 0.0
    change_24h: float = 0.0
    change_7d: float = 0.0
    change_30d: float = 0.0
    
    # Additional metrics
    holders: int = 0
    fdv: float = 0.0  # Fully Diluted Valuation
    
    def volume_to_mcap_ratio(self) -> float:
        """Higher ratio = more trading interest relative to size"""
        if self.market_cap <= 0:
            return 0.0
        return self.volume_24h / self.market_cap
    
    def liquidity_to_mcap_ratio(self) -> float:
        """Higher ratio = better liquidity for trading"""
        if self.market_cap <= 0:
            return 0.0
        return self.liquidity_usd / self.market_cap


@dataclass
class HypeScore:
    """Composite hype score for ranking"""
    token: TokenMetrics
    
    # Individual scores (0-100)
    momentum_score: float = 0.0      # Recent price action
    volume_score: float = 0.0        # Volume spike
    social_score: float = 0.0        # Social sentiment
    risk_adjusted_score: float = 0.0 # Risk-adjusted potential
    
    # Composite
    total_hype_score: float = 0.0
    category: HypeCategory = HypeCategory.STABLE
    risk_level: RiskLevel = RiskLevel.MODERATE
    
    def to_dict(self) -> Dict:
        return {
            "token": asdict(self.token),
            "scores": {
                "momentum": round(self.momentum_score, 2),
                "volume": round(self.volume_score, 2),
                "social": round(self.social_score, 2),
                "risk_adjusted": round(self.risk_adjusted_score, 2),
                "total_hype": round(self.total_hype_score, 2),
            },
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "recommendation": self._get_recommendation()
        }
    
    def _get_recommendation(self) -> str:
        if self.total_hype_score >= 80:
            return "STRONG_HYPE - High potential but watch for dumps"
        elif self.total_hype_score >= 60:
            return "GOOD_HYPE - Decent momentum, manageable risk"
        elif self.total_hype_score >= 40:
            return "MODERATE - Some interest, proceed with caution"
        else:
            return "LOW_HYPE - Not much buzz currently"


class TokenScreener:
    """Screen and rank Solana tokens by hype"""
    
    # Minimum thresholds for consideration
    MIN_LIQUIDITY_USD = 20_000       # $20k min liquidity (filters dead/rugged pools)
    MIN_VOLUME_24H = 20_000          # $20k min volume
    MIN_MARKET_CAP = 30_000          # $30k min market cap / FDV
    
    # Scoring weights
    WEIGHT_MOMENTUM = 0.35
    WEIGHT_VOLUME = 0.30
    WEIGHT_SOCIAL = 0.20
    WEIGHT_RISK = 0.15
    
    def __init__(
        self,
        data_file: Optional[str] = None,
        min_liquidity_usd: Optional[float] = None,
        min_volume_24h: Optional[float] = None,
        min_market_cap: Optional[float] = None,
    ):
        self.tokens: List[TokenMetrics] = []
        self.hype_scores: List[HypeScore] = []
        self.data_file = Path(data_file) if data_file else None
        self.min_liquidity_usd = min_liquidity_usd if min_liquidity_usd is not None else self.MIN_LIQUIDITY_USD
        self.min_volume_24h = min_volume_24h if min_volume_24h is not None else self.MIN_VOLUME_24H
        self.min_market_cap = min_market_cap if min_market_cap is not None else self.MIN_MARKET_CAP

    async def fetch_live_tokens(
        self,
        min_liquidity: Optional[float] = None,
        min_volume: Optional[float] = None,
        max_tokens: int = 40,
    ) -> List[TokenMetrics]:
        """Fetch real-time Solana memecoins from DexScreener and apply safety/liquidity filters."""
        from snail_scalp.real_data_fetcher import DexScreenerFetcher

        min_liq = min_liquidity if min_liquidity is not None else self.min_liquidity_usd
        min_vol = min_volume if min_volume is not None else self.min_volume_24h

        fetcher = DexScreenerFetcher()
        tokens_map: Dict[str, Dict] = {}

        # 1. Fetch boosted / trending token profiles
        try:
            profiles = await fetcher.fetch_token_profiles()
            for p in profiles:
                addr = p.get("tokenAddress")
                if addr:
                    tokens_map[addr] = p
        except Exception as e:
            print(f"[WARN] DexScreener profiles lookup: {e}")

        # 2. Search for active Solana pairs
        search_pairs = []
        try:
            search_pairs = await fetcher.search_solana_pairs("solana")
            for sp in search_pairs:
                base = sp.get("baseToken", {})
                addr = base.get("address")
                if addr and addr not in tokens_map:
                    tokens_map[addr] = {"tokenAddress": addr}
        except Exception as e:
            print(f"[WARN] DexScreener search lookup: {e}")

        # 3. Batch lookup pair data for candidate tokens
        addrs = list(tokens_map.keys())[:max_tokens]
        raw_pairs: List[Dict] = []
        if addrs:
            try:
                raw_pairs = await fetcher.get_tokens_batch(addrs)
            except Exception as e:
                print(f"[WARN] DexScreener batch lookup: {e}")

        if not raw_pairs and search_pairs:
            raw_pairs = search_pairs

        # 4. Filter and select best pool per token
        best_pairs_by_mint: Dict[str, Dict] = {}
        for pair in raw_pairs:
            if pair.get("chainId") != "solana":
                continue
            base = pair.get("baseToken", {})
            addr = base.get("address")
            if not addr:
                continue

            liq = float(pair.get("liquidity", {}).get("usd", 0) or 0)
            vol = float(pair.get("volume", {}).get("h24", 0) or 0)
            price = float(pair.get("priceUsd", 0) or 0)

            # Safety gate: liquidity and volume filters
            if liq < min_liq or vol < min_vol or price <= 0:
                continue

            # Pick highest liquidity pair for this token
            current_best_liq = float(best_pairs_by_mint.get(addr, {}).get("liquidity", {}).get("usd", 0) or 0)
            if addr not in best_pairs_by_mint or liq > current_best_liq:
                best_pairs_by_mint[addr] = pair

        metrics_list: List[TokenMetrics] = []
        for addr, pair in best_pairs_by_mint.items():
            base = pair.get("baseToken", {})
            metrics_list.append(TokenMetrics(
                symbol=base.get("symbol", "UNKNOWN")[:12],
                name=base.get("name", "Unknown"),
                address=addr,
                price_usd=float(pair.get("priceUsd", 0) or 0),
                market_cap=float(pair.get("marketCap") or pair.get("fdv") or 0),
                volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                change_1h=float(pair.get("priceChange", {}).get("h1", 0) or 0),
                change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                change_7d=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                change_30d=0.0,
                holders=0,
                fdv=float(pair.get("fdv", 0) or 0)
            ))

        if metrics_list:
            self.tokens = metrics_list
            try:
                Path("data").mkdir(parents=True, exist_ok=True)
                cache_file = Path("data/live_screened_tokens.json")
                with open(cache_file, "w") as f:
                    json.dump({
                        "generated_at": datetime.now().isoformat(),
                        "source": "DexScreener Live API",
                        "tokens": [
                            {
                                "symbol": m.symbol,
                                "name": m.name,
                                "contract_address": m.address,
                                "metrics": asdict(m)
                            }
                            for m in metrics_list
                        ]
                    }, f, indent=2)
            except Exception:
                pass
        elif self.tokens:
            pass
        elif Path("data/top10_solana_coins.json").exists():
            self.load_from_json("data/top10_solana_coins.json")

        return self.tokens

    def fetch_live_tokens_sync(
        self,
        min_liquidity: Optional[float] = None,
        min_volume: Optional[float] = None,
        max_tokens: int = 40,
    ) -> List[TokenMetrics]:
        """Synchronous wrapper for fetch_live_tokens."""
        try:
            return asyncio.run(self.fetch_live_tokens(min_liquidity, min_volume, max_tokens))
        except RuntimeError:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(
                    asyncio.run, self.fetch_live_tokens(min_liquidity, min_volume, max_tokens)
                ).result()
        
    def load_from_json(self, filepath: str) -> List[TokenMetrics]:
        """Load token data from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.tokens = []
        for item in data.get('tokens', []):
            m = item.get('metrics', item)  # Support both nested and flat structures
            self.tokens.append(TokenMetrics(
                symbol=item['symbol'],
                name=item['name'],
                address=item.get('contract_address', item.get('address', '')),
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
        return self.tokens
    
    def filter_basic(self, tokens: Optional[List[TokenMetrics]] = None) -> List[TokenMetrics]:
        """Apply basic liquidity/volume filters"""
        tokens = tokens or self.tokens
        
        filtered = []
        for t in tokens:
            # Skip if doesn't meet minimums
            if t.liquidity_usd < self.min_liquidity_usd:
                continue
            if t.volume_24h < self.min_volume_24h:
                continue
            if t.market_cap < self.min_market_cap:
                continue
            filtered.append(t)
        
        return filtered
    
    def calculate_momentum_score(self, token: TokenMetrics) -> float:
        """Score based on price momentum (0-100)"""
        scores = []
        
        # 24h change weight: 40%
        if token.change_24h > 100:
            scores.append(100 * 0.4)
        elif token.change_24h > 50:
            scores.append(90 * 0.4)
        elif token.change_24h > 20:
            scores.append(80 * 0.4)
        elif token.change_24h > 10:
            scores.append(70 * 0.4)
        elif token.change_24h > 5:
            scores.append(60 * 0.4)
        elif token.change_24h > 0:
            scores.append(40 * 0.4)
        else:
            scores.append(max(0, 20 + token.change_24h) * 0.4)
        
        # 7d trend weight: 35%
        if token.change_7d > 200:
            scores.append(100 * 0.35)
        elif token.change_7d > 100:
            scores.append(90 * 0.35)
        elif token.change_7d > 50:
            scores.append(80 * 0.35)
        elif token.change_7d > 20:
            scores.append(60 * 0.35)
        elif token.change_7d > 0:
            scores.append(40 * 0.35)
        else:
            scores.append(max(0, 20 + token.change_7d / 5) * 0.35)
        
        # 1h momentum (immediate action) weight: 25%
        if token.change_1h > 20:
            scores.append(100 * 0.25)
        elif token.change_1h > 10:
            scores.append(85 * 0.25)
        elif token.change_1h > 5:
            scores.append(70 * 0.25)
        elif token.change_1h > 0:
            scores.append(50 * 0.25)
        else:
            scores.append(max(0, 30 + token.change_1h) * 0.25)
        
        return sum(scores)
    
    def calculate_volume_score(self, token: TokenMetrics) -> float:
        """Score based on volume activity (0-100)"""
        vmc_ratio = token.volume_to_mcap_ratio()
        
        # Higher volume/market cap = more interest
        if vmc_ratio > 1.0:
            return 100
        elif vmc_ratio > 0.5:
            return 85
        elif vmc_ratio > 0.3:
            return 75
        elif vmc_ratio > 0.2:
            return 65
        elif vmc_ratio > 0.1:
            return 50
        elif vmc_ratio > 0.05:
            return 35
        else:
            return 20
    
    def calculate_social_score(self, token: TokenMetrics) -> float:
        """Estimate social sentiment from available metrics (0-100)"""
        score = 50  # Base score
        
        # Holder growth proxy (if we had historical data)
        if token.holders > 10_000:
            score += 20
        elif token.holders > 5_000:
            score += 15
        elif token.holders > 1_000:
            score += 10
        
        # Volume spike indicates interest
        vmc = token.volume_to_mcap_ratio()
        if vmc > 0.5:
            score += 15
        elif vmc > 0.3:
            score += 10
        
        # Recent price action generates buzz
        if token.change_24h > 20:
            score += 15
        elif token.change_24h > 10:
            score += 10
        
        return min(100, score)
    
    def calculate_risk_adjusted_score(self, token: TokenMetrics) -> float:
        """Score potential adjusted for risk (0-100)"""
        # Higher liquidity = lower risk = better score
        liquidity_score = 0
        lmc = token.liquidity_to_mcap_ratio()
        if lmc > 0.5:
            liquidity_score = 100
        elif lmc > 0.3:
            liquidity_score = 80
        elif lmc > 0.2:
            liquidity_score = 65
        elif lmc > 0.1:
            liquidity_score = 50
        else:
            liquidity_score = 30
        
        # Market cap size (smaller = more potential but riskier)
        size_score = 0
        if token.market_cap > 1_000_000_000:  # >$1B
            size_score = 40
        elif token.market_cap > 100_000_000:  # >$100M
            size_score = 60
        elif token.market_cap > 50_000_000:   # >$50M
            size_score = 75
        elif token.market_cap > 10_000_000:   # >$10M
            size_score = 85
        else:
            size_score = 95  # Small caps have highest potential
        
        # Volatility risk (extreme pumps = high risk)
        volatility_penalty = 0
        if token.change_24h > 50:
            volatility_penalty = 20
        elif token.change_24h > 30:
            volatility_penalty = 10
        
        return (liquidity_score * 0.4 + size_score * 0.6) - volatility_penalty
    
    def determine_category(self, token: TokenMetrics) -> HypeCategory:
        """Classify hype level"""
        if token.change_24h > 50:
            return HypeCategory.EXTREME
        elif token.change_24h > 20:
            return HypeCategory.HIGH
        elif token.change_24h > 5:
            return HypeCategory.MODERATE
        else:
            return HypeCategory.STABLE
    
    def determine_risk_level(self, token: TokenMetrics) -> RiskLevel:
        """Assess risk level"""
        # Check for extreme pumps
        if token.change_24h > 100 or token.change_7d > 500:
            return RiskLevel.EXTREME
        
        # Low liquidity = high risk
        if token.liquidity_usd < 500_000:
            return RiskLevel.HIGH
        
        # Small market cap = moderate-high risk
        if token.market_cap < 10_000_000:
            return RiskLevel.HIGH
        elif token.market_cap < 100_000_000:
            return RiskLevel.MODERATE
        elif token.market_cap < 1_000_000_000:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL
    
    def score_tokens(self, tokens: Optional[List[TokenMetrics]] = None) -> List[HypeScore]:
        """Calculate hype scores for all tokens"""
        tokens = tokens or self.tokens
        tokens = self.filter_basic(tokens)
        
        self.hype_scores = []
        for token in tokens:
            momentum = self.calculate_momentum_score(token)
            volume = self.calculate_volume_score(token)
            social = self.calculate_social_score(token)
            risk_adj = self.calculate_risk_adjusted_score(token)
            
            total = (
                momentum * self.WEIGHT_MOMENTUM +
                volume * self.WEIGHT_VOLUME +
                social * self.WEIGHT_SOCIAL +
                risk_adj * self.WEIGHT_RISK
            )
            
            hype_score = HypeScore(
                token=token,
                momentum_score=momentum,
                volume_score=volume,
                social_score=social,
                risk_adjusted_score=risk_adj,
                total_hype_score=total,
                category=self.determine_category(token),
                risk_level=self.determine_risk_level(token)
            )
            self.hype_scores.append(hype_score)
        
        # Sort by total hype score descending
        self.hype_scores.sort(key=lambda x: x.total_hype_score, reverse=True)
        return self.hype_scores
    
    def get_top_picks(self, n: int = 10, min_risk_level: Optional[RiskLevel] = None) -> List[HypeScore]:
        """Get top N tokens by hype score"""
        scores = self.hype_scores
        
        if min_risk_level:
            # Filter out higher risk levels
            risk_values = {RiskLevel.MINIMAL: 1, RiskLevel.LOW: 2, 
                          RiskLevel.MODERATE: 3, RiskLevel.HIGH: 4, RiskLevel.EXTREME: 5}
            max_risk = risk_values.get(min_risk_level, 5)
            scores = [s for s in scores if risk_values.get(s.risk_level, 5) <= max_risk]
        
        return scores[:n]
    
    def get_by_category(self, category: HypeCategory) -> List[HypeScore]:
        """Get tokens filtered by hype category"""
        return [s for s in self.hype_scores if s.category == category]
    
    def export_report(self, filepath: str, top_n: int = 10):
        """Export screening report to JSON"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_screened": len(self.tokens),
            "total_qualified": len(self.hype_scores),
            "top_picks": [s.to_dict() for s in self.get_top_picks(top_n)],
            "by_category": {
                "extreme": [s.to_dict() for s in self.get_by_category(HypeCategory.EXTREME)],
                "high": [s.to_dict() for s in self.get_by_category(HypeCategory.HIGH)],
                "moderate": [s.to_dict() for s in self.get_by_category(HypeCategory.MODERATE)],
                "stable": [s.to_dict() for s in self.get_by_category(HypeCategory.STABLE)],
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def print_summary(self, top_n: int = 10):
        """Print formatted summary to console"""
        print("\n" + "="*80)
        print("🔥 SOLANA TOKEN HYPE SCREENING REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"Total Tokens: {len(self.tokens)} | Qualified: {len(self.hype_scores)}")
        print("-"*80)
        
        print(f"\n[DATA] TOP {top_n} BY HYPE SCORE:\n")
        print(f"{'Rank':<6}{'Symbol':<12}{'24h%':<10}{'7d%':<10}{'Vol/MCap':<12}{'Hype':<10}{'Risk':<10}{'Score'}")
        print("-"*80)
        
        for i, score in enumerate(self.get_top_picks(top_n), 1):
            t = score.token
            vmc = t.volume_to_mcap_ratio()
            print(f"{i:<6}{t.symbol:<12}{t.change_24h:>+7.1f}%  {t.change_7d:>+7.1f}%  "
                  f"{vmc:>8.2f}x  {score.category.value:<10}{score.risk_level.name:<10}"
                  f"{score.total_hype_score:.1f}")
        
        print("\n" + "="*80)
        print("[RISE] RECOMMENDATIONS:")
        print("-"*80)
        
        extreme = self.get_by_category(HypeCategory.EXTREME)
        high = self.get_by_category(HypeCategory.HIGH)
        
        if extreme:
            print(f"\n[WARN]  EXTREME HYPE ({len(extreme)} tokens):")
            print("   High risk of dumps. Only trade with tight stops.")
            for s in extreme[:3]:
                print(f"   • {s.token.symbol}: +{s.token.change_24h:.1f}% (24h)")
        
        if high:
            print(f"\n🚀 HIGH HYPE ({len(high)} tokens):")
            print("   Good momentum with manageable risk.")
            for s in high[:5]:
                print(f"   • {s.token.symbol}: +{s.token.change_24h:.1f}% (24h), "
                      f"Vol/MCap: {s.token.volume_to_mcap_ratio():.2f}x")
        
        top_scalp = self.get_top_picks(5)
        if top_scalp:
            print("\n" + "="*80)
            print("🎯 TOP 3-5 CANDIDATES FOR USDT SCALPING ON SOLANA (USDT Base):")
            print("="*80)
            for i, score in enumerate(top_scalp[:5], 1):
                t = score.token
                print(f"{i}. {t.symbol:<10} | Price: ${t.price_usd:<12.6f} | 24h: {t.change_24h:>+7.1f}% | 1h: {t.change_1h:>+6.1f}%")
                print(f"   Address:   {t.address}")
                print(f"   Liquidity: ${t.liquidity_usd:>10,.0f} | 24h Vol: ${t.volume_24h:>10,.0f} | Hype: {score.total_hype_score:.1f}/100")
                print(f"   Route:     USDT (Es9vMFrza...) -> {t.symbol} ({t.address[:8]}...) via Jupiter")
                print("-"*80)

        print("\n" + "="*80)


# Pre-loaded top Solana ecosystem coins (from CoinGecko research)
TOP_SOLANA_COINS = [
    {
        "symbol": "BOOB",
        "name": "boob",
        "address": "boobtokenaddress",
        "price_usd": 0.0024,
        "market_cap": 2_400_204,
        "volume_24h": 349_895,
        "liquidity_usd": 720_000,
        "change_1h": 3.2,
        "change_24h": 98.8,
        "change_7d": 140.0,
        "change_30d": 0.0,
        "holders": 2500,
        "fdv": 2_400_204
    },
    {
        "symbol": "GBOY",
        "name": "GBOY",
        "address": "gboytokenaddress",
        "price_usd": 0.008303,
        "market_cap": 6_668_107,
        "volume_24h": 212_582,
        "liquidity_usd": 1_500_000,
        "change_1h": 19.5,
        "change_24h": 41.0,
        "change_7d": 20.1,
        "change_30d": 25.5,
        "holders": 4500,
        "fdv": 8_280_169
    },
    {
        "symbol": "SHARK",
        "name": "Greenland Shark",
        "address": "sharktokenaddress",
        "price_usd": 0.002856,
        "market_cap": 2_763_340,
        "volume_24h": 14_037_598,
        "liquidity_usd": 800_000,
        "change_1h": 6.3,
        "change_24h": 25.0,
        "change_7d": 0.0,
        "change_30d": 0.0,
        "holders": 1800,
        "fdv": 2_763_340
    },
    {
        "symbol": "BIRB",
        "name": "Moonbirds",
        "address": "birbtokenaddress",
        "price_usd": 0.3129,
        "market_cap": 88_876_687,
        "volume_24h": 324_721_544,
        "liquidity_usd": 22_000_000,
        "change_1h": 2.3,
        "change_24h": 26.8,
        "change_7d": 0.0,
        "change_30d": 0.0,
        "holders": 12500,
        "fdv": 311_848_026
    },
    {
        "symbol": "COPPERINU",
        "name": "copper inu",
        "address": "copperinutokenaddress",
        "price_usd": 0.006442,
        "market_cap": 6_448_952,
        "volume_24h": 11_804_461,
        "liquidity_usd": 1_600_000,
        "change_1h": 3.2,
        "change_24h": 29.7,
        "change_7d": 42.9,
        "change_30d": 0.0,
        "holders": 3200,
        "fdv": 6_448_952
    },
    {
        "symbol": "WOULD",
        "name": "would",
        "address": "wouldtokenaddress",
        "price_usd": 0.05106,
        "market_cap": 50_797_708,
        "volume_24h": 152_531,
        "liquidity_usd": 10_000_000,
        "change_1h": 0.4,
        "change_24h": 20.1,
        "change_7d": 47.4,
        "change_30d": 19.6,
        "holders": 8500,
        "fdv": 50_797_708
    },
    {
        "symbol": "PENGUIN",
        "name": "Nietzschean Penguin",
        "address": "penguintokenaddress",
        "price_usd": 0.03104,
        "market_cap": 31_011_667,
        "volume_24h": 35_985_319,
        "liquidity_usd": 6_500_000,
        "change_1h": 3.3,
        "change_24h": 16.1,
        "change_7d": 68.6,
        "change_30d": 0.0,
        "holders": 6200,
        "fdv": 31_011_667
    },
    {
        "symbol": "FROG",
        "name": "just a frog",
        "address": "frogtokenaddress",
        "price_usd": 0.03043,
        "market_cap": 30_426_041,
        "volume_24h": 16_012,
        "liquidity_usd": 6_000_000,
        "change_1h": 2.3,
        "change_24h": 16.1,
        "change_7d": 34.6,
        "change_30d": 0.0,
        "holders": 4800,
        "fdv": 30_426_041
    },
    {
        "symbol": "67COIN",
        "name": "67COIN",
        "address": "67cointokenaddress",
        "price_usd": 0.003586,
        "market_cap": 3_588_679,
        "volume_24h": 53_370,
        "liquidity_usd": 900_000,
        "change_1h": 0.0,
        "change_24h": 22.9,
        "change_7d": 3934.4,
        "change_30d": 746.2,
        "holders": 1500,
        "fdv": 3_588_679
    },
    {
        "symbol": "FARTCOIN",
        "name": "Fartcoin",
        "address": "ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz",
        "price_usd": 0.2191,
        "market_cap": 219_041_259,
        "volume_24h": 70_732_118,
        "liquidity_usd": 55_000_000,
        "change_1h": 3.0,
        "change_24h": 3.3,
        "change_7d": 28.9,
        "change_30d": 40.4,
        "holders": 45000,
        "fdv": 219_041_259
    }
]


def create_demo_data(filepath: str = "data/top_solana_coins.json"):
    """Create demo data file with top Solana coins"""
    data = {
        "generated_at": datetime.now().isoformat(),
        "source": "CoinGecko Solana Ecosystem",
        "tokens": TOP_SOLANA_COINS
    }
    
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    return filepath


if __name__ == "__main__":
    # Demo usage
    create_demo_data()
    
    screener = TokenScreener()
    screener.load_from_json("data/top_solana_coins.json")
    screener.score_tokens()
    screener.print_summary(10)
    screener.export_report("data/hype_screening_report.json", 10)
    
    print("\n[OK] Demo complete! Check data/hype_screening_report.json for full results.")
