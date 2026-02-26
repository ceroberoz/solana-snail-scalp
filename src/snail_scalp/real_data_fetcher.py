"""Real Data Fetcher for Solana DEX

Fetches historical price data from:
- Birdeye API (recommended, free tier available)
- DexScreener (free, limited history)
- Helius RPC (if you have API key)
- Jupiter API (for live data)
"""

import asyncio
import aiohttp
import json
import csv
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class OHLCV:
    """OHLCV candle data"""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class BirdeyeDataFetcher:
    """Fetch historical data from Birdeye API
    
    Free tier: 100k credits/month
    Get API key: https://docs.birdeye.so/docs/authentication
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://public-api.birdeye.so"
        self.headers = {
            "X-API-KEY": api_key,
            "accept": "application/json",
        } if api_key else {"accept": "application/json"}
    
    async def get_token_price_history(
        self,
        token_address: str,
        timeframe: str = "1m",  # 1m, 5m, 15m, 1h, 4h, 1d
        days: int = 7,
    ) -> List[OHLCV]:
        """Fetch OHLCV data for a token"""
        
        # Calculate time range
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())
        
        url = f"{self.base_url}/defi/history_price"
        params = {
            "address": token_address,
            "address_type": "token",
            "type": timeframe,
            "time_from": start_time,
            "time_to": end_time,
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url, 
                    headers=self.headers, 
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get("data", {}).get("items", [])
                        
                        candles = []
                        for item in items:
                            candles.append(OHLCV(
                                timestamp=item.get("unixTime", 0),
                                open=item.get("open", 0),
                                high=item.get("high", 0),
                                low=item.get("low", 0),
                                close=item.get("close", 0),
                                volume=item.get("volume", 0),
                            ))
                        
                        print(f"[OK] Fetched {len(candles)} candles for {token_address[:8]}...")
                        return candles
                    else:
                        print(f"[ERROR] Birdeye API: {response.status}")
                        return []
            except Exception as e:
                print(f"[ERROR] Failed to fetch: {e}")
                return []


class DexScreenerFetcher:
    """Fetch data from DexScreener (free, no API key needed)
    
    Limitations:
    - No historical OHLCV in free tier
    - Can get current pair data and recent trades
    """
    
    def __init__(self):
        self.base_url = "https://api.dexscreener.com/latest"
    
    async def get_pair_data(self, pair_address: str) -> Optional[Dict]:
        """Get current pair data"""
        url = f"{self.base_url}/dex/pairs/solana/{pair_address}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = data.get("pairs", [])
                        return pairs[0] if pairs else None
            except Exception as e:
                print(f"[ERROR] DexScreener: {e}")
                return None
    
    async def get_token_pairs(self, token_address: str) -> List[Dict]:
        """Get all pairs for a token"""
        url = f"{self.base_url}/dex/tokens/{token_address}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("pairs", [])
            except Exception as e:
                print(f"[ERROR] DexScreener: {e}")
                return []


class RealDataSimulation:
    """Run simulation with real historical data"""
    
    def __init__(
        self,
        token_address: str,
        capital: float = 20.0,
        days: int = 7,
        api_key: Optional[str] = None,
    ):
        self.token_address = token_address
        self.capital = capital
        self.days = days
        self.fetcher = BirdeyeDataFetcher(api_key)
        self.data_file = f"data/real_{token_address[:8]}_{days}d.csv"
    
    async def fetch_and_save(self) -> str:
        """Fetch real data and save to CSV"""
        print(f"\n[DATA] Fetching {self.days} days of real data...")
        print(f"Token: {self.token_address}")
        
        candles = await self.fetcher.get_token_price_history(
            self.token_address,
            timeframe="5m",  # 5-minute candles
            days=self.days,
        )
        
        if not candles:
            print("[ERROR] No data fetched. Check token address or API key.")
            return ""
        
        # Save to CSV
        Path(self.data_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.data_file, 'w', newline='') as f:
            writer = csv.DictWriter(
                f, 
                fieldnames=["timestamp", "datetime", "price", "volume24h", "liquidity"]
            )
            writer.writeheader()
            
            for candle in candles:
                writer.writerow({
                    "timestamp": candle.timestamp,
                    "datetime": datetime.fromtimestamp(candle.timestamp).isoformat(),
                    "price": candle.close,  # Use close price
                    "volume24h": candle.volume,
                    "liquidity": 0,  # Not available in OHLCV
                })
        
        print(f"[SAVE] Saved {len(candles)} candles to {self.data_file}")
        
        # Print stats
        prices = [c.close for c in candles]
        print(f"\n[STATS] Price Range:")
        print(f"  Min: ${min(prices):.6f}")
        print(f"  Max: ${max(prices):.6f}")
        print(f"  Avg: ${sum(prices)/len(prices):.6f}")
        print(f"  Change: {((prices[-1]/prices[0])-1)*100:+.2f}%")
        
        return self.data_file
    
    async def run_simulation(self):
        """Run simulation with real data"""
        # Fetch data if not exists
        if not Path(self.data_file).exists():
            await self.fetch_and_save()
        
        print("\n" + "="*60)
        print(f"REAL DATA SIMULATION - ${self.capital:.2f} Capital")
        print("="*60)
        
        # Import here to avoid circular imports
        from snail_scalp import HybridDataFeed, TechnicalIndicators, RiskManager, Trader
        from snail_scalp.config import strategy_config
        
        # Setup components
        feed = HybridDataFeed(
            simulate=True,
            log_file=self.data_file,
            speed_multiplier=100,  # Fast
        )
        
        indicators = TechnicalIndicators()
        risk = RiskManager(simulate=True)
        
        trader = Trader(
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
            risk_manager=risk,
            simulate=True,
            results_file=f"data/real_simulation_{self.token_address[:8]}.json",
        )
        
        # Run simulation
        print("\n[RUNNING] Simulating trades...")
        
        trades_executed = 0
        max_trades = 10  # Limit for demo
        
        while trades_executed < max_trades:
            price_data = await feed.get_price_data(None, "")
            
            if not price_data:
                break
            
            current_price = price_data.price
            indicators.add_price(current_price, price_data.volume24h)
            
            # Only trade during window (9-11 UTC)
            hour = datetime.fromtimestamp(price_data.timestamp).hour
            if not (9 <= hour < 11):
                continue
            
            # Need enough data for indicators
            if len(indicators.prices) < strategy_config.bb_period:
                continue
            
            # Check entry/exit
            if not trader.active_position:
                if indicators.is_entry_signal(current_price):
                    await trader.check_entry(current_price, indicators, self.capital)
                    trades_executed += 1
            else:
                await trader.manage_position(current_price, indicators)
        
        # Results
        summary = trader.get_summary()
        print("\n" + "="*60)
        print("SIMULATION RESULTS (REAL DATA)")
        print("="*60)
        print(f"Initial Capital: ${self.capital:.2f}")
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']:.1f}%")
        print(f"Total PnL: ${summary['total_pnl']:+.2f}")
        print(f"Return: {(summary['total_pnl']/self.capital*100):+.2f}%")
        print("="*60)


# Token addresses for reference
POPULAR_SOLANA_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "FARTCOIN": "ErEsCytFqmC7WQ8c2xNBI7WVrXDJwA1dZwgz",
    "PENGU": "2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd3gnGpo2jP",
    "AI16Z": "3J5QaP1FyWDL1XR8VJVAzXoHxaH2Xz2p8p7yC8bJ5vZP",
}


async def main():
    """Example: Fetch real data and run simulation"""
    
    # Option 1: Use Birdeye (get free API key from birdeye.so)
    # api_key = "your_birdeye_api_key_here"  # Optional for some endpoints
    
    # Option 2: Use sample data file path
    print("To use real data:")
    print("1. Get Birdeye API key (free): https://birdeye.so")
    print("2. Set token address (see POPULAR_SOLANA_TOKENS)")
    print("3. Run simulation")
    
    # Example with FARTCOIN (high volume meme coin)
    token = POPULAR_SOLANA_TOKENS["FARTCOIN"]
    
    sim = RealDataSimulation(
        token_address=token,
        capital=20.0,
        days=3,  # Last 3 days
        api_key=None,  # Add your key here
    )
    
    # Check if we can fetch
    print("\n[NOTE] Without API key, using sample data...")
    print("For real data, get free API key from birdeye.so")
    
    # For demo, use existing sample data
    # await sim.run_simulation()


if __name__ == "__main__":
    asyncio.run(main())
