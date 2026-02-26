"""Abstract base class for data providers"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass
import pandas as pd


@dataclass
class PriceData:
    """Standardized price data structure"""
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


class DataProvider(ABC):
    """Abstract base class for forex data providers"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def download(
        self, 
        symbol: str, 
        period: str = "1y", 
        interval: str = "15m"
    ) -> pd.DataFrame:
        """
        Download historical data
        
        Args:
            symbol: Pair code (e.g., "USD_SGD")
            period: Time period ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y")
            interval: Data interval ("1m", "5m", "15m", "30m", "60m", "1h", "1d")
            
        Returns:
            DataFrame with columns: [Open, High, Low, Close, Volume]
        """
        pass
    
    @abstractmethod
    def get_latest(self, symbol: str) -> Optional[PriceData]:
        """Get latest price quote"""
        pass
    
    @abstractmethod
    def is_available(self, symbol: str) -> bool:
        """Check if symbol is available from this provider"""
        pass
    
    @abstractmethod
    def get_spread(self, symbol: str) -> Optional[float]:
        """Get current spread in pips"""
        pass
