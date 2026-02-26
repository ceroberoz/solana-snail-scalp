#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test OANDA connection and fetch live data

Usage:
    export OANDA_API_KEY="your_api_key"
    export OANDA_ACCOUNT_ID="your_account_id"
    python scripts/test_oanda.py

Or set in .env file:
    OANDA_API_KEY=xxx
    OANDA_ACCOUNT_ID=xxx-xxx-xxx-xxx
    OANDA_ENVIRONMENT=practice
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forex_bot.data.oanda_provider import OandaProvider, create_oanda_provider_from_env


def test_connection():
    """Test OANDA connection"""
    print("="*60)
    print("OANDA Connection Test")
    print("="*60)
    
    # Load from environment
    api_key = os.getenv("OANDA_API_KEY", "")
    account_id = os.getenv("OANDA_ACCOUNT_ID", "")
    environment = os.getenv("OANDA_ENVIRONMENT", "practice")
    
    if not api_key:
        print("\n❌ OANDA_API_KEY not set")
        print("Get your API key from: https://www.oanda.com/demo-account/")
        return False
    
    if not account_id:
        print("\n❌ OANDA_ACCOUNT_ID not set")
        print("Find your account ID in OANDA dashboard")
        return False
    
    print(f"\nEnvironment: {environment}")
    print(f"Account ID: {account_id[:8]}...{account_id[-4:]}")
    
    # Create provider
    provider = OandaProvider(
        api_key=api_key,
        account_id=account_id,
        environment=environment
    )
    
    # Test connection
    print("\nTesting connection...")
    if not provider.test_connection():
        print("❌ Connection failed")
        return False
    
    print("✅ Connection successful")
    
    # Get account summary
    print("\nAccount Summary:")
    summary = provider.get_account_summary()
    print(f"  Account Alias: {summary.get('alias', 'N/A')}")
    print(f"  Currency: {summary.get('currency', 'N/A')}")
    print(f"  Balance: {summary.get('balance', 'N/A')}")
    print(f"  NAV: {summary.get('NAV', 'N/A')}")
    print(f"  Unrealized P&L: {summary.get('unrealizedPL', 'N/A')}")
    print(f"  Margin Available: {summary.get('marginAvailable', 'N/A')}")
    print(f"  Margin Used: {summary.get('marginUsed', 'N/A')}")
    print(f"  Open Trade Count: {summary.get('openTradeCount', 'N/A')}")
    print(f"  Open Position Count: {summary.get('openPositionCount', 'N/A')}")
    
    # Test USD/SGD price
    print("\nFetching USD/SGD price...")
    price = provider.get_latest("USD_SGD")
    
    if price:
        print(f"✅ Price data received")
        print(f"  Timestamp: {price.timestamp}")
        print(f"  Price: {price.close:.5f}")
    else:
        print("❌ Failed to get price")
        return False
    
    # Test historical data
    print("\nFetching historical data (last 5 days, 1h)...")
    try:
        df = provider.download("USD_SGD", period="5d", interval="1h")
        if not df.empty:
            print(f"✅ Historical data: {len(df)} candles")
            print(f"  Date range: {df.index[0]} to {df.index[-1]}")
            print(f"  OHLC sample:")
            print(df.tail(3).to_string())
        else:
            print("❌ No historical data")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Check positions
    print("\nOpen Positions:")
    positions = provider.get_positions()
    if positions:
        for pos in positions:
            instrument = pos.get('instrument', 'Unknown')
            long = pos.get('long', {})
            short = pos.get('short', {})
            
            if long.get('units', '0') != '0':
                print(f"  {instrument}: LONG {long.get('units')} units")
            if short.get('units', '0') != '0':
                print(f"  {instrument}: SHORT {short.get('units')} units")
    else:
        print("  No open positions")
    
    print("\n" + "="*60)
    print("All tests passed!" if price else "Some tests failed")
    print("="*60)
    
    return True


def main():
    try:
        success = test_connection()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
