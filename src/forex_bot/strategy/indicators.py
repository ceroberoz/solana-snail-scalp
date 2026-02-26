"""Technical indicators for forex trading (adapted from crypto)"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
from dataclasses import dataclass


# Helper functions moved outside class for standalone use
def calculate_adx(df: pd.DataFrame, period: int = 14) -> Tuple[float, float, float]:
    """Calculate ADX for trend strength"""
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    
    plus_dm[plus_dm <= minus_dm] = 0
    minus_dm[minus_dm <= plus_dm] = 0
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()
    
    return adx.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]


@dataclass
class BollingerBands:
    lower: float
    middle: float
    upper: float
    width_pips: float
    
    @property
    def width_percent(self) -> float:
        """Width as percentage of middle band"""
        if self.middle == 0:
            return 0
        return ((self.upper - self.lower) / self.middle) * 100


@dataclass
class Signal:
    is_valid: bool
    reason: str
    rsi: float
    bb_position: str  # "lower", "middle", "upper", "outside"
    confidence: int  # 0-100


class ForexIndicators:
    """
    Technical indicators optimized for USD/SGD forex trading
    
    Key differences from crypto:
    - Pips-based calculations instead of percentages
    - Adjusted for lower volatility (0.5-1.5% daily vs 5-20% crypto)
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize with price data
        
        Args:
            df: DataFrame with OHLCV columns
        """
        self.df = df.copy()
        self.pip_size = 0.0001  # 1 pip for USD/SGD
        
    def calculate_bb(self, period: int = 20, std_dev: float = 2.0) -> BollingerBands:
        """Calculate Bollinger Bands"""
        close = self.df['Close']
        
        sma = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        # Get latest values
        latest_upper = upper.iloc[-1]
        latest_lower = lower.iloc[-1]
        latest_sma = sma.iloc[-1]
        
        # Width in pips
        width_pips = (latest_upper - latest_lower) / self.pip_size
        
        return BollingerBands(
            lower=latest_lower,
            middle=latest_sma,
            upper=latest_upper,
            width_pips=width_pips
        )
    
    def calculate_rsi(self, period: int = 14) -> float:
        """Calculate RSI"""
        close = self.df['Close']
        
        # Calculate price changes
        delta = close.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = (-delta.where(delta < 0, 0))
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period).mean()
        avg_losses = losses.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def calculate_atr(self, period: int = 14) -> float:
        """Calculate Average True Range in pips"""
        high = self.df['High']
        low = self.df['Low']
        close = self.df['Close']
        
        # True Range calculation
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Return in pips
        return atr.iloc[-1] / self.pip_size
    
    def calculate_volume_ma(self, period: int = 20) -> Tuple[float, float]:
        """Calculate volume and its moving average"""
        if 'Volume' not in self.df.columns:
            return 0, 0
            
        volume = self.df['Volume']
        current = volume.iloc[-1]
        avg = volume.rolling(window=period).mean().iloc[-1]
        
        return current, avg
    
    def calculate_adx(self, period: int = 14) -> Tuple[float, float, float]:
        """Calculate ADX for trend strength"""
        return calculate_adx(self.df, period)
    
    def is_ranging_market(self, adx_threshold: float = 25.0) -> bool:
        """
        Check if market is ranging (good for mean reversion)
        ADX < 25 indicates ranging/choppy market
        """
        adx, _, _ = self.calculate_adx(period=14)
        return adx < adx_threshold
    
    def check_entry_signal(
        self,
        price: float,
        rsi_min: int = 20,
        rsi_max: int = 40,
        bb_tolerance_pips: float = 3.0,
        min_bb_width_pips: float = 10.0,
        use_volume: bool = False,
        volume_threshold: float = 1.0,
    ) -> Signal:
        """
        Check if entry conditions are met
        
        Args:
            price: Current price
            rsi_min: RSI lower bound (oversold)
            rsi_max: RSI upper bound
            bb_tolerance_pips: Tolerance for BB touch in pips
            min_bb_width_pips: Minimum BB width to trade
            use_volume: Whether to check volume confirmation
            volume_threshold: Volume vs average threshold
        """
        # Get indicators
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()
        
        # Check 1: Price at or below lower BB (with tolerance)
        tolerance = bb_tolerance_pips * self.pip_size
        at_bb = price <= (bb.lower + tolerance)
        
        # Check 2: RSI in oversold range
        rsi_ok = rsi_min <= rsi <= rsi_max
        
        # Check 3: BB width sufficient (avoid flat markets)
        volatility_ok = bb.width_pips >= min_bb_width_pips
        
        # Check 4: Volume confirmation (optional)
        volume_ok = True
        if use_volume:
            current_vol, avg_vol = self.calculate_volume_ma()
            if avg_vol > 0:
                volume_ok = current_vol >= avg_vol * volume_threshold
        
        # Calculate confidence score
        confidence = 50
        
        # RSI depth factor
        if rsi < 25:
            confidence += 20
        elif rsi < 35:
            confidence += 10
        
        # Volume factor
        if use_volume and volume_ok:
            confidence += 15
        
        # BB width factor
        if bb.width_pips > 20:
            confidence += 10
        
        # Determine BB position
        if price <= bb.lower:
            bb_position = "below_lower"
        elif price <= bb.lower + tolerance:
            bb_position = "at_lower"
        elif price <= bb.middle:
            bb_position = "lower_half"
        elif price <= bb.upper:
            bb_position = "upper_half"
        else:
            bb_position = "above_upper"
        
        # Determine if signal is valid
        is_valid = at_bb and rsi_ok and volatility_ok and volume_ok
        
        # Build reason string
        reasons = []
        if not at_bb:
            reasons.append(f"Price not at BB (price={price:.5f}, lower={bb.lower:.5f})")
        if not rsi_ok:
            reasons.append(f"RSI not in range ({rsi:.1f}, need {rsi_min}-{rsi_max})")
        if not volatility_ok:
            reasons.append(f"BB too narrow ({bb.width_pips:.1f} pips)")
        if not volume_ok:
            reasons.append("Volume below threshold")
        
        reason = "; ".join(reasons) if reasons else "Entry signal valid"
        
        return Signal(
            is_valid=is_valid,
            reason=reason,
            rsi=rsi,
            bb_position=bb_position,
            confidence=min(100, confidence)
        )
    
    def get_exit_levels(
        self,
        entry_price: float,
        target_pips: list,
        stop_pips: int,
        use_atr: bool = True,
        atr_multiplier: float = 1.5,
    ) -> dict:
        """
        Calculate exit levels
        
        Returns:
            dict with targets and stop levels
        """
        # Calculate ATR-based dynamic stop
        if use_atr:
            atr = self.calculate_atr()
            dynamic_stop_pips = max(stop_pips, atr * atr_multiplier)
        else:
            dynamic_stop_pips = stop_pips
        
        # Calculate levels
        levels = {
            "entry": entry_price,
            "stop": entry_price - (dynamic_stop_pips * self.pip_size),
            "breakeven": entry_price + (2 * self.pip_size),  # Small buffer
            "targets": [
                entry_price + (t * self.pip_size) for t in target_pips
            ],
            "stop_pips": dynamic_stop_pips,
        }
        
        return levels


def resample_ohlc(df: pd.DataFrame, timeframe: str = "1h") -> pd.DataFrame:
    """
    Resample OHLC data to different timeframe
    
    Args:
        df: DataFrame with DatetimeIndex
        timeframe: Target timeframe ("15m", "1h", "4h", "1d")
    """
    resample_map = {
        "15m": "15min",
        "30m": "30min",
        "1h": "1H",
        "4h": "4H",
        "1d": "1D",
    }
    
    freq = resample_map.get(timeframe, "1H")
    
    resampled = df.resample(freq).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum',
    }).dropna()
    
    return resampled
