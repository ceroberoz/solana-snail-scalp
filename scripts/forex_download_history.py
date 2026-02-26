#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download historical forex data for backtesting

Usage:
    python scripts/download_history.py --pair USD_SGD --period 2y
    python scripts/download_history.py --all  # Download all Phase 1 pairs
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_bot.data.yahoo_provider import YahooFinanceProvider
from forex_bot.config.pairs import get_phase_1_pairs, get_phase_2_pairs


def download_pair(provider: YahooFinanceProvider, pair_code: str, period: str = "2y"):
    """Download historical data for a pair"""
    from forex_bot.config.pairs import get_pair_config
    
    config = get_pair_config(pair_code)
    
    # Yahoo Finance limitations:
    # - 1m: last 7 days only
    # - 5m, 15m, 30m, 60m: last 60 days only
    # - 1h: last 730 days (~2 years)
    # - 1d: full history
    
    # Adjust interval based on period
    if period in ["1d", "5d"]:
        interval = "15m"
    elif period in ["1mo", "3mo", "6mo"]:
        interval = "1h"  # Yahoo 15m only available for last 60 days
    else:  # 1y, 2y, etc.
        interval = "1h"  # Use 1h for longer periods
    
    print(f"\n{'='*60}")
    print(f"Downloading {config.name} ({pair_code})")
    print(f"Period: {period}, Interval: {interval} (Yahoo limit: 15m only for last 60 days)")
    print(f"{'='*60}")
    
    try:
        # Download data
        df = provider.download(
            symbol=pair_code,
            period=period,
            interval=interval,
        )
        
        # Save to parquet for efficient storage
        output_dir = Path("data/historical")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{pair_code.lower()}_{interval}_{period}.parquet"
        df.to_parquet(output_file, compression="zstd")
        
        # Stats
        print(f"✅ Downloaded {len(df)} rows")
        print(f"   Date range: {df.index[0]} to {df.index[-1]}")
        print(f"   Saved to: {output_file}")
        print(f"   File size: {output_file.stat().st_size / 1024:.1f} KB")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download historical forex data")
    parser.add_argument(
        "--pair",
        type=str,
        default="USD_SGD",
        help="Pair code (e.g., USD_SGD, USD_MYR)",
    )
    parser.add_argument(
        "--period",
        type=str,
        default="2y",
        choices=["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"],
        help="Time period to download",
    )
    parser.add_argument(
        "--all-phase1",
        action="store_true",
        help="Download all Phase 1 pairs",
    )
    parser.add_argument(
        "--all-phase2",
        action="store_true",
        help="Download all Phase 2 pairs (includes Phase 1)",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="data/cache/yahoo",
        help="Cache directory",
    )
    
    args = parser.parse_args()
    
    # Initialize provider
    print(f"Initializing Yahoo Finance provider (cache: {args.cache_dir})...")
    provider = YahooFinanceProvider(cache_dir=args.cache_dir)
    
    # Determine which pairs to download
    if args.all_phase1:
        pairs = list(get_phase_1_pairs().keys())
        print(f"\nDownloading all Phase 1 pairs: {pairs}")
    elif args.all_phase2:
        pairs = list(get_phase_2_pairs().keys())
        print(f"\nDownloading all Phase 2 pairs: {pairs}")
    else:
        pairs = [args.pair]
    
    # Download each pair
    results = []
    for pair_code in pairs:
        success = download_pair(provider, pair_code, args.period)
        results.append((pair_code, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for pair_code, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {pair_code}")
    
    # Cache stats
    stats = provider.get_cache_stats()
    print(f"\nCache Stats:")
    print(f"   Entries: {stats['cache_size']}")
    print(f"   Size: {stats['cache_volume_mb']} MB")
    print(f"   API requests (last hour): {stats['requests_last_hour']}")
    
    provider.close()
    
    # Return exit code
    return 0 if all(success for _, success in results) else 1


if __name__ == "__main__":
    sys.exit(main())
