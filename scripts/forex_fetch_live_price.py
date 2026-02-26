#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch live USD/SGD price from OANDA

Usage:
    python scripts/fetch_live_price.py
    python scripts/fetch_live_price.py --pair USD_MYR
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from forex_bot.data import OandaProvider


def fetch_price(pair: str = "USD_SGD"):
    """Fetch and display live price"""
    print("="*60)
    print("OANDA Live Price Feed")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Pair: {pair}")
    print("-"*60)
    
    # Create provider (reads from .env)
    provider = OandaProvider()
    
    # Test connection
    if not provider.test_connection():
        print("\n❌ Failed to connect to OANDA")
        print("\nCheck your .env file:")
        print("  1. OANDA_API_KEY is set correctly")
        print("  2. OANDA_ACCOUNT_ID is set correctly")
        print("  3. OANDA_ENVIRONMENT=practice (or live)")
        return 1
    
    # Get live price
    price = provider.get_latest(pair)
    
    if not price:
        print(f"\n❌ Failed to get price for {pair}")
        return 1
    
    # Display
    print(f"\n✅ Live Price:")
    print(f"   Timestamp: {price.timestamp}")
    print(f"   Bid/Ask Mid: {price.close:.5f}")
    print(f"   Spread est: ~2-5 pips")
    
    # Get account info
    summary = provider.get_account_summary()
    print(f"\n💰 Account:")
    print(f"   Balance: ${float(summary.get('balance', 0)):,.2f}")
    print(f"   NAV: ${float(summary.get('NAV', 0)):,.2f}")
    print(f"   Margin Available: ${float(summary.get('marginAvailable', 0)):,.2f}")
    
    # Check positions
    positions = provider.get_positions()
    if positions:
        print(f"\n📊 Open Positions:")
        for pos in positions:
            inst = pos.get('instrument', 'Unknown')
            long_units = pos.get('long', {}).get('units', '0')
            short_units = pos.get('short', {}).get('units', '0')
            if long_units != '0':
                print(f"   {inst}: LONG {long_units}")
            if short_units != '0':
                print(f"   {inst}: SHORT {short_units}")
    else:
        print(f"\n📊 Open Positions: None")
    
    print("\n" + "="*60)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Fetch live forex prices")
    parser.add_argument(
        "--pair",
        type=str,
        default="USD_SGD",
        help="Currency pair (default: USD_SGD)"
    )
    
    args = parser.parse_args()
    return fetch_price(args.pair)


if __name__ == "__main__":
    sys.exit(main())
