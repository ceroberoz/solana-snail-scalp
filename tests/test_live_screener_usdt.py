import pytest
from unittest.mock import patch, MagicMock
from snail_scalp.config import TOKEN_IN, USDT_MINT, USDC_MINT, SOL_MINT, BASE_TOKEN_DECIMALS
from snail_scalp.token_screener import TokenScreener, TokenMetrics, RiskLevel, HypeCategory
from snail_scalp.multi_token_feed import MultiTokenFeed


def test_usdt_configuration():
    """Verify USDT is configured as base quote currency on Solana."""
    assert TOKEN_IN == USDT_MINT
    assert USDT_MINT == "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    assert USDC_MINT == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    assert SOL_MINT == "So11111111111111111111111111111111111111112"
    assert BASE_TOKEN_DECIMALS == 6


def test_token_screener_thresholds_and_filtering():
    """Verify TokenScreener filters by configurable liquidity threshold."""
    screener = TokenScreener(min_liquidity_usd=25_000, min_volume_24h=10_000, min_market_cap=20_000)
    
    tokens = [
        TokenMetrics(
            symbol="DEADRUG",
            name="Dead Rug",
            address="dead1111111111111111111111111111111111111111",
            price_usd=0.00001,
            market_cap=50_000,
            volume_24h=5_000,
            liquidity_usd=1_000,  # Below 25k -> should be filtered
        ),
        TokenMetrics(
            symbol="GOODMEME",
            name="Good Meme",
            address="good1111111111111111111111111111111111111111",
            price_usd=0.005,
            market_cap=500_000,
            volume_24h=200_000,
            liquidity_usd=50_000,  # Above 25k -> qualifies
            change_24h=45.0,
            change_1h=5.0,
        )
    ]
    
    filtered = screener.filter_basic(tokens)
    assert len(filtered) == 1
    assert filtered[0].symbol == "GOODMEME"
    
    scores = screener.score_tokens(tokens)
    assert len(scores) == 1
    assert scores[0].token.symbol == "GOODMEME"
    assert scores[0].total_hype_score > 0


def test_offline_fallback_for_screener():
    """Verify screener gracefully falls back to cached data when offline."""
    screener = TokenScreener()
    with patch("snail_scalp.real_data_fetcher.DexScreenerFetcher.fetch_token_profiles", side_effect=Exception("Network error")):
        tokens = screener.fetch_live_tokens_sync(min_liquidity=10_000)
        assert len(tokens) > 0
        assert any(t.symbol in ["BOOB", "SOL", "BONK", "COPPER"] for t in tokens)


def test_multi_token_feed_best_scalping_candidates():
    """Verify MultiTokenFeed finds candidates with memecoin liquidity thresholds."""
    feed = MultiTokenFeed(use_live=False, min_liquidity=20_000)
    candidates = feed.get_best_scalping_candidates(n=3, require_liquidity_usd=20_000)
    assert len(candidates) > 0
    assert len(candidates) <= 3
