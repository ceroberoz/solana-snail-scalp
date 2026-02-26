"""OANDA live data and trading provider"""

import os
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import requests
import pandas as pd

from .provider import DataProvider, PriceData


logger = logging.getLogger(__name__)


class OandaEnvironment(Enum):
    PRACTICE = "practice"
    LIVE = "live"


@dataclass
class OandaConfig:
    """OANDA API configuration"""
    api_key: str
    account_id: str
    environment: OandaEnvironment = OandaEnvironment.PRACTICE
    
    @property
    def base_url(self) -> str:
        if self.environment == OandaEnvironment.LIVE:
            return "https://api-fxtrade.oanda.com/v3"
        return "https://api-fxpractice.oanda.com/v3"
    
    @property
    def stream_url(self) -> str:
        if self.environment == OandaEnvironment.LIVE:
            return "https://stream-fxtrade.oanda.com/v3"
        return "https://stream-fxpractice.oanda.com/v3"


class OandaProvider(DataProvider):
    """
    OANDA v20 API provider for live data and trading
    
    Features:
    - Real-time price quotes
    - Historical data (candles)
    - Order execution
    - Position management
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        environment: str = "practice"
    ):
        super().__init__("OANDA")
        
        # Load from environment or parameters
        self.config = OandaConfig(
            api_key=api_key or os.getenv("OANDA_API_KEY", ""),
            account_id=account_id or os.getenv("OANDA_ACCOUNT_ID", ""),
            environment=OandaEnvironment(environment) if environment in ["practice", "live"] else OandaEnvironment.PRACTICE
        )
        
        if not self.config.api_key:
            logger.warning("OANDA API key not provided")
        if not self.config.account_id:
            logger.warning("OANDA Account ID not provided")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        })
        
        logger.info(f"OandaProvider initialized ({self.config.environment.value})")
    
    def _make_request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
        """Make API request with error handling"""
        url = f"{self.config.base_url}/{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def is_available(self, symbol: str) -> bool:
        """Check if symbol is available on OANDA"""
        try:
            instrument = self._symbol_to_instrument(symbol)
            response = self._make_request("GET", f"instruments/{instrument}")
            return "instrument" in response
        except Exception:
            return False
    
    def _symbol_to_instrument(self, symbol: str) -> str:
        """Convert internal symbol to OANDA instrument format"""
        # USD_SGD -> USD_SGD
        return symbol.replace("/", "_")
    
    def get_spread(self, symbol: str) -> Optional[float]:
        """Get current spread in pips"""
        try:
            price = self.get_latest(symbol)
            if price:
                # OANDA prices are mid, we'd need bid/ask separately
                # For now, return None - use order book API for spread
                return None
        except Exception as e:
            logger.error(f"Failed to get spread: {e}")
            return None
    
    def get_latest(self, symbol: str) -> Optional[PriceData]:
        """Get latest price quote"""
        try:
            instrument = self._symbol_to_instrument(symbol)
            response = self._make_request(
                "GET",
                f"accounts/{self.config.account_id}/pricing",
                params={"instruments": instrument}
            )
            
            price_data = response.get("prices", [{}])[0]
            
            if not price_data:
                return None
            
            # Parse timestamps
            time_str = price_data.get("time", "")
            timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            
            # Use mid price (average of bid and ask)
            bid = float(price_data.get("closeoutBid", 0))
            ask = float(price_data.get("closeoutAsk", 0))
            mid = (bid + ask) / 2
            
            return PriceData(
                timestamp=timestamp,
                open=mid,  # OANDA streaming doesn't provide OHLC directly
                high=mid,
                low=mid,
                close=mid,
                volume=0  # Not provided in pricing endpoint
            )
            
        except Exception as e:
            logger.error(f"Failed to get latest price: {e}")
            return None
    
    def download(
        self,
        symbol: str,
        period: str = "1y",
        interval: str = "1h"
    ) -> pd.DataFrame:
        """
        Download historical candle data
        
        Args:
            symbol: Pair code (e.g., "USD_SGD")
            period: Time period (not used, OANDA uses from/to dates)
            interval: Candle granularity ("S5", "M1", "M15", "H1", "D")
        """
        instrument = self._symbol_to_instrument(symbol)
        
        # Map interval to OANDA granularity
        granularity_map = {
            "1m": "M1",
            "5m": "M5",
            "15m": "M15",
            "30m": "M30",
            "1h": "H1",
            "4h": "H4",
            "1d": "D",
        }
        granularity = granularity_map.get(interval, "H1")
        
        # Calculate date range
        count_map = {
            "1d": 24, "5d": 120, "1mo": 720, "3mo": 2160,
            "6mo": 4320, "1y": 8760, "2y": 17520
        }
        count = count_map.get(period, 500)
        
        # OANDA limits to 500 candles per request
        all_candles = []
        from_time = None
        
        while count > 0:
            batch_count = min(500, count)
            
            params = {
                "granularity": granularity,
                "count": batch_count,
                "price": "M",  # Mid price
            }
            
            if from_time:
                params["from"] = from_time
            
            try:
                response = self._make_request(
                    "GET",
                    f"instruments/{instrument}/candles",
                    params=params
                )
                
                candles = response.get("candles", [])
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                # Update from_time for next batch
                last_time = candles[-1].get("time")
                from_time = datetime.fromisoformat(
                    last_time.replace("Z", "+00:00")
                ).isoformat()
                
                count -= batch_count
                
            except Exception as e:
                logger.error(f"Failed to download candles: {e}")
                break
        
        # Convert to DataFrame
        if not all_candles:
            return pd.DataFrame()
        
        data = []
        for candle in all_candles:
            if not candle.get("complete", False):
                continue
                
            mid = candle.get("mid", {})
            
            data.append({
                "timestamp": datetime.fromisoformat(
                    candle["time"].replace("Z", "+00:00")
                ),
                "Open": float(mid.get("o", 0)),
                "High": float(mid.get("h", 0)),
                "Low": float(mid.get("l", 0)),
                "Close": float(mid.get("c", 0)),
                "Volume": int(candle.get("volume", 0)),
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    # ==================== Trading Methods ====================
    
    def get_account_summary(self) -> dict:
        """Get account summary"""
        try:
            response = self._make_request(
                "GET",
                f"accounts/{self.config.account_id}/summary"
            )
            return response.get("account", {})
        except Exception as e:
            logger.error(f"Failed to get account summary: {e}")
            return {}
    
    def get_positions(self) -> List[dict]:
        """Get open positions"""
        try:
            response = self._make_request(
                "GET",
                f"accounts/{self.config.account_id}/positions"
            )
            return response.get("positions", [])
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_open_trades(self) -> List[dict]:
        """Get open trades"""
        try:
            response = self._make_request(
                "GET",
                f"accounts/{self.config.account_id}/openTrades"
            )
            return response.get("trades", [])
        except Exception as e:
            logger.error(f"Failed to get open trades: {e}")
            return []
    
    def create_market_order(
        self,
        symbol: str,
        units: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> dict:
        """
        Create a market order
        
        Args:
            symbol: Pair code (e.g., "USD_SGD")
            units: Positive for buy, negative for sell
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        instrument = self._symbol_to_instrument(symbol)
        
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(int(units)),
            }
        }
        
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {
                "price": str(stop_loss)
            }
        
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {
                "price": str(take_profit)
            }
        
        try:
            response = self._make_request(
                "POST",
                f"accounts/{self.config.account_id}/orders",
                data=order_data
            )
            
            logger.info(f"Order created: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise
    
    def close_position(self, symbol: str) -> dict:
        """Close position for a symbol"""
        instrument = self._symbol_to_instrument(symbol)
        
        try:
            response = self._make_request(
                "PUT",
                f"accounts/{self.config.account_id}/positions/{instrument}/close",
                data={"longUnits": "ALL", "shortUnits": "ALL"}
            )
            logger.info(f"Position closed: {response}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            summary = self.get_account_summary()
            if summary:
                logger.info(f"Connected to OANDA account: {summary.get('alias', 'Unknown')}")
                logger.info(f"Balance: {summary.get('balance', 'Unknown')} {summary.get('currency', '')}")
                return True
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


def create_oanda_provider_from_env() -> OandaProvider:
    """Create OANDA provider from environment variables"""
    return OandaProvider(
        api_key=os.getenv("OANDA_API_KEY"),
        account_id=os.getenv("OANDA_ACCOUNT_ID"),
        environment=os.getenv("OANDA_ENVIRONMENT", "practice")
    )
