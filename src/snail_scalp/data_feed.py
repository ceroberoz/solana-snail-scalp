"""Rate-Limited Data Fetching with Simulation Support"""

import aiohttp
import asyncio
import time
import csv
import random
from typing import Optional, Dict, List, Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from snail_scalp.config import api_config


@dataclass
class PriceData:
    price: float
    volume24h: float
    liquidity: float
    timestamp: float
    source: str = "live"  # "live" or "simulated"


class DataFeed:
    """Live data feed from DexScreener with rate limiting"""

    def __init__(self):
        self.last_call = 0
        self.min_interval = 5  # 5 seconds between calls minimum
        self.daily_calls = 0
        self.max_daily_calls = 100  # Stay under DexScreener limits

    async def get_price_data(
        self, session: aiohttp.ClientSession, pair_address: str
    ) -> Optional[PriceData]:
        """Fetch with strict rate limiting"""
        if self.daily_calls >= self.max_daily_calls:
            print("[WARN] Daily API limit reached. Stopping.")
            return None

        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)

        try:
            url = api_config.dexscreener.format(pair=pair_address)
            async with session.get(url, timeout=10) as resp:
                self.last_call = time.time()
                self.daily_calls += 1

                if resp.status == 429:
                    print("⏳ Rate limited. Backing off 60s...")
                    await asyncio.sleep(60)
                    return None

                if resp.status == 200:
                    data = await resp.json()
                    pair = data.get("pairs", [{}])[0]
                    return PriceData(
                        price=float(pair.get("priceUsd", 0)),
                        volume24h=float(pair.get("volume", {}).get("h24", 0)),
                        liquidity=float(pair.get("liquidity", {}).get("usd", 0)),
                        timestamp=time.time(),
                        source="live",
                    )
        except Exception as e:
            print(f"❌ Data fetch error: {e}")
            return None

    async def get_ohlcv(self) -> List[Dict]:
        """
        Note: Free tier limitation - DexScreener doesn't provide historical OHLCV easily.
        For 15m candles, you may need to aggregate yourself or use Birdeye (30k CU/month free).
        """
        return []


class SimulationDataFeed:
    """Simulated data feed from log/historical data"""

    def __init__(self, log_file: str, speed_multiplier: float = 1.0):
        self.log_file = Path(log_file)
        self.speed_multiplier = speed_multiplier
        self.data_iterator: Optional[Iterator[PriceData]] = None
        self.current_data: Optional[PriceData] = None
        self.last_timestamp: Optional[float] = None
        self.skip_sleep = False  # Set to True to fast-forward without delays
        self._load_data()

    def _load_data(self):
        """Load price data from CSV log file"""
        if not self.log_file.exists():
            raise FileNotFoundError(f"Simulation log file not found: {self.log_file}")

        self.data_points = []
        with open(self.log_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.data_points.append(
                    PriceData(
                        price=float(row["price"]),
                        volume24h=float(row.get("volume24h", 0)),
                        liquidity=float(row.get("liquidity", 0)),
                        timestamp=float(row["timestamp"]),
                        source="simulated",
                    )
                )

        if not self.data_points:
            raise ValueError("No data points found in log file")

        self.data_iterator = iter(self.data_points)
        print(f"[DATA] Loaded {len(self.data_points)} data points for simulation")

    async def get_price_data(
        self, session: Optional[aiohttp.ClientSession] = None, pair_address: str = ""
    ) -> Optional[PriceData]:
        """Get next simulated price data point"""
        try:
            data = next(self.data_iterator)

            # Simulate realistic delay based on time difference
            if self.last_timestamp is not None and not self.skip_sleep:
                time_diff = data.timestamp - self.last_timestamp
                delay = (time_diff / self.speed_multiplier) if time_diff > 0 else 0
                if delay > 0:
                    await asyncio.sleep(min(delay, 0.5))  # Cap at 0.5 seconds for faster sim

            self.last_timestamp = data.timestamp
            self.current_data = data
            return data

        except StopIteration:
            print("🏁 Simulation data exhausted")
            return None

    def reset(self):
        """Reset simulation to beginning"""
        self.data_iterator = iter(self.data_points)
        self.last_timestamp = None
        self.current_data = None
        print("[RESET] Simulation reset")


class HybridDataFeed:
    """Can switch between live and simulation modes"""

    def __init__(
        self,
        simulate: bool = False,
        log_file: str = "data/sample_price_data.csv",
        speed_multiplier: float = 1.0,
    ):
        self.simulate = simulate
        self.live_feed = DataFeed()
        self.sim_feed: Optional[SimulationDataFeed] = None

        if simulate:
            self.sim_feed = SimulationDataFeed(log_file, speed_multiplier)

    async def get_price_data(
        self,
        session: Optional[aiohttp.ClientSession] = None,
        pair_address: str = "",
    ) -> Optional[PriceData]:
        """Get price data from appropriate source"""
        if self.simulate and self.sim_feed:
            return await self.sim_feed.get_price_data()
        else:
            if session is None:
                raise ValueError("Live mode requires an aiohttp session")
            return await self.live_feed.get_price_data(session, pair_address)

    def is_simulation(self) -> bool:
        return self.simulate
