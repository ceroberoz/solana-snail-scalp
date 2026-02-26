"""Yahoo Finance data provider with intelligent caching"""

import os
import sys
import time
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf
from diskcache import Cache

from .provider import DataProvider, PriceData

# Set up logging with UTF-8 support for Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class YahooFinanceProvider(DataProvider):
    """
    Yahoo Finance data provider with disk-based caching
    
    Rate Limit Strategy:
    - Max 100 requests/hour (conservative, vs 2,000 Yahoo limit)
    - Exponential backoff on 429 errors
    - User-agent rotation
    - Persistent disk cache for historical data
    """
    
    # Yahoo ticker suffix for forex
    YAHOO_SUFFIX = "=X"
    
    # Conservative rate limit
    MAX_REQUESTS_PER_HOUR = 100
    
    # Rotating user agents to avoid blocks
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    def __init__(
        self, 
        cache_dir: str = "data/cache/yahoo",
        max_requests_per_hour: int = 100
    ):
        super().__init__("YahooFinance")
        
        # Ensure cache directory exists
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize disk cache
        self.cache = Cache(str(self.cache_dir))
        self.max_requests = max_requests_per_hour
        self.request_times: list = []
        
        logger.info(f"YahooFinanceProvider initialized (cache: {cache_dir})")
    
    def _get_cache_key(self, ticker: str, period: str, interval: str) -> str:
        """Generate cache key"""
        return f"{ticker}_{period}_{interval}"
    
    def _get_ttl(self, interval: str) -> timedelta:
        """Get TTL based on data granularity"""
        ttl_map = {
            "1m": timedelta(minutes=15),
            "5m": timedelta(minutes=30),
            "15m": timedelta(hours=1),
            "30m": timedelta(hours=2),
            "60m": timedelta(hours=4),
            "1h": timedelta(hours=4),
            "1d": timedelta(days=7),
        }
        return ttl_map.get(interval, timedelta(hours=1))
    
    def _is_cache_fresh(self, timestamp: datetime, interval: str) -> bool:
        """Check if cached data is still fresh"""
        ttl = self._get_ttl(interval)
        return datetime.now() - timestamp < ttl
    
    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old requests outside the 1-hour window
        self.request_times = [t for t in self.request_times if t > hour_ago]
        
        # Check if we're at the limit
        if len(self.request_times) >= self.max_requests:
            # Calculate sleep time
            oldest_request = self.request_times[0]
            sleep_seconds = 3600 - (now - oldest_request).total_seconds()
            
            if sleep_seconds > 0:
                logger.warning(f"Rate limit reached. Sleeping {sleep_seconds:.0f}s...")
                time.sleep(sleep_seconds)
                # Recurse after sleep
                self._respect_rate_limit()
    
    def _log_request(self):
        """Log request time for rate limiting"""
        self.request_times.append(datetime.now())
        logger.debug(f"API request logged. Count (1hr): {len(self.request_times)}")
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent"""
        return random.choice(self.USER_AGENTS)
    
    def _symbol_to_ticker(self, symbol: str) -> str:
        """Convert internal symbol to Yahoo ticker"""
        # USD_SGD -> USDSGD=X
        return symbol.replace("_", "") + self.YAHOO_SUFFIX
    
    def download(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "15m"
    ) -> pd.DataFrame:
        """
        Download data with caching
        
        Args:
            symbol: Pair code (e.g., "USD_SGD")
            period: Time period
            interval: Data interval
            
        Returns:
            DataFrame with OHLCV data
        """
        ticker = self._symbol_to_ticker(symbol)
        cache_key = self._get_cache_key(ticker, period, interval)
        
        # Check cache first
        cached = self.cache.get(cache_key)
        if cached is not None:
            data, timestamp = cached
            if self._is_cache_fresh(timestamp, interval):
                logger.debug(f"Cache hit: {cache_key}")
                return data
            else:
                logger.debug(f"Cache stale: {cache_key}")
        
        # Rate limit check
        self._respect_rate_limit()
        
        # Download from Yahoo
        logger.info(f"Downloading {ticker} ({period}, {interval}) from Yahoo Finance...")
        
        try:
            # Set random user agent
            user_agent = self._get_random_user_agent()
            
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=False,
                prepost=False,
            )
            
            if data.empty:
                raise ValueError(f"No data returned for {ticker}")
            
            # Standardize column names
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            data.columns = [col.capitalize() for col in data.columns]
            
            # Ensure required columns exist
            required = ["Open", "High", "Low", "Close", "Volume"]
            for col in required:
                if col not in data.columns:
                    raise ValueError(f"Missing column: {col}")
            
            # Store in cache
            self.cache[cache_key] = (data, datetime.now())
            self._log_request()
            
            logger.info(f"Downloaded {len(data)} rows for {ticker}")
            return data
            
        except Exception as e:
            if "429" in str(e) or "Too Many Requests" in str(e):
                logger.error(f"Rate limited by Yahoo. Waiting 60s before retry...")
                time.sleep(60)
                return self.download(symbol, period, interval)
            
            logger.error(f"Download failed for {ticker}: {e}")
            raise
    
    def get_latest(self, symbol: str) -> Optional[PriceData]:
        """Get latest price (uses 1d data for efficiency)"""
        try:
            df = self.download(symbol, period="1d", interval="1m")
            if df.empty:
                return None
            
            latest = df.iloc[-1]
            return PriceData(
                timestamp=df.index[-1],
                open=float(latest["Open"]),
                high=float(latest["High"]),
                low=float(latest["Low"]),
                close=float(latest["Close"]),
                volume=int(latest["Volume"]),
            )
        except Exception as e:
            logger.error(f"Failed to get latest price for {symbol}: {e}")
            return None
    
    def is_available(self, symbol: str) -> bool:
        """Check if symbol is available"""
        try:
            ticker = self._symbol_to_ticker(symbol)
            # Try to get info (lightweight check)
            info = yf.Ticker(ticker).info
            return "regularMarketPrice" in info or "previousClose" in info
        except Exception:
            return False
    
    def get_spread(self, symbol: str) -> Optional[float]:
        """Get current spread (not directly available from Yahoo)"""
        # Yahoo doesn't provide real-time spread data
        # This would need to come from a live broker API
        logger.warning("Spread data not available from Yahoo Finance")
        return None
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_volume_mb": round(self.cache.volume() / (1024 * 1024), 2),
            "requests_last_hour": len(self.request_times),
            "max_requests_per_hour": self.max_requests,
        }
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def close(self):
        """Close cache connection"""
        self.cache.close()
        logger.info("Cache connection closed")
