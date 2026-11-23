"""Technical Analysis Indicators"""

import numpy as np
from collections import deque
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class BollingerBands:
    lower: float
    middle: float
    upper: float
    width_percent: float


@dataclass
class ExitLevels:
    tp1: float
    tp2: float
    stop: float


class TechnicalIndicators:
    """Bollinger Bands and RSI calculation with multi-timeframe support (US-1.4)"""

    def __init__(self, period: int = 20, enable_multi_timeframe: bool = True):
        self.period = period
        self.prices = deque(maxlen=period + 10)
        self.volumes = deque(maxlen=period + 10)
        self.highs = deque(maxlen=period + 10)
        self.lows = deque(maxlen=period + 10)
        # Cache
        self._dirty = True
        self._cache_bb = None
        self._cache_rsi = None
        self._cache_rsi_period = None
        self._cache_atr = None
        self._cache_adx = None
        self._cache_confidence = None
        
        # US-1.4: Multi-timeframe data storage
        self.enable_multi_timeframe = enable_multi_timeframe
        self.price_history_15m = deque(maxlen=50)  # Store 15m candles
        self.last_candle_time = 0
        self.current_candle_prices = []
        self.current_candle_volumes = []

    def add_price(self, price: float, volume: float = 0, high: float = None, low: float = None):
        """Add new price point (optional high/low for ATR)"""
        self.prices.append(price)
        self.volumes.append(volume)
        self.highs.append(high if high is not None else price)
        self.lows.append(low if low is not None else price)
        self._cache_bb = None
        self._cache_rsi = None
        self._cache_rsi_period = None
        self._cache_atr = None
        self._cache_adx = None
        self._cache_confidence = None

    def calculate_bb(self) -> Optional[BollingerBands]:
        """Calculate Bollinger Bands (cached)"""
        if self._cache_bb is not None:
            return self._cache_bb
        if len(self.prices) < self.period:
            self._cache_bb = None
            return None

        prices = list(self.prices)[-self.period :]
        sma = float(np.mean(prices))
        std = float(np.std(prices))

        upper = sma + (std * 2)
        lower = sma - (std * 2)
        width = ((upper - lower) / sma) * 100

        bb = BollingerBands(lower=lower, middle=sma, upper=upper, width_percent=width)
        self._cache_bb = bb
        return bb

    def calculate_rsi(self, period: int = 14) -> float:
        """Calculate Relative Strength Index (cached for default period)"""
        if period == 14 and self._cache_rsi is not None and self._cache_rsi_period == 14:
            return self._cache_rsi
        if len(self.prices) < period + 1:
            if period == 14:
                self._cache_rsi = 50.0
                self._cache_rsi_period = 14
            return 50.0  # Neutral when not enough data

        prices = list(self.prices)[-period - 1 :]
        deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]

        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = float(np.mean(gains))
        avg_loss = float(np.mean(losses))

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        if period == 14:
            self._cache_rsi = rsi
            self._cache_rsi_period = 14
        return rsi

    def is_entry_signal(
        self,
        current_price: float,
        rsi_min: int = 25,
        rsi_max: int = 35,
        min_band_width: float = 2.0,
    ) -> bool:
        """Check all entry conditions"""
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()

        if bb is None:
            return False

        # Condition 1: Price at or below lower band (with 0.5% tolerance - US-1.3)
        at_bb = current_price <= bb.lower * 1.005

        # Condition 2: RSI in oversold range
        rsi_ok = rsi_min <= rsi <= rsi_max

        # Condition 3: Band width > minimum (avoid flat markets)
        volatility_ok = bb.width_percent > min_band_width

        # Condition 4: Price is above recent low (avoid falling knives)
        recent_low = min(list(self.prices)[-5:]) if len(self.prices) >= 5 else current_price
        not_falling = current_price > recent_low * 0.99

        # Condition 5: Volume confirmation (>1.3x average - US-1.2)
        volume_ok = self._check_volume_confirmation()
        
        # Condition 6: Multi-timeframe confirmation (US-1.4)
        mtf_ok = self.check_multi_timeframe_confirm(current_price)

        return at_bb and rsi_ok and volatility_ok and not_falling and volume_ok and mtf_ok

    def is_momentum_entry_signal(
        self,
        current_price: float,
        rsi_min: int = 45,
        rsi_max: int = 70,
        min_band_width: float = 2.0,
        volume_threshold: float = 1.1,
    ) -> bool:
        """Trend-following long entry for bull markets (TRENDING_UP).

        Unlike mean-reversion (buy the lower band), momentum buys strength:
        price above the middle band, RSI in the bullish-but-not-overbought
        zone, short-term rising, with volume and 15m trend confirmation.
        """
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()
        prices = list(self.prices)

        if bb is None or len(prices) < 5:
            return False

        # Price trading above the middle band = buyers in control
        above_mid = current_price >= bb.middle * 0.995

        # Bullish RSI zone (avoid overbought blow-offs)
        rsi_ok = rsi_min <= rsi <= rsi_max

        # Avoid flat markets
        volatility_ok = bb.width_percent > min_band_width

        # Short-term momentum is rising
        rising = current_price > prices[-3]

        # Don't chase a blow-off top far above the upper band
        not_blowoff = current_price <= bb.upper * 1.02

        # Volume confirmation (lower threshold than mean-reversion)
        volume_ok = self._check_volume_confirmation(volume_threshold)

        # 15m confirmation: uptrend or RSI above 50 (opposite of mean reversion)
        mtf_ok = True
        if self.enable_multi_timeframe and len(self.price_history_15m) >= 15:
            mtf_ok = self.calculate_rsi_15m() > 50.0 or self.get_15m_trend() == "UPTREND"

        return (
            above_mid
            and rsi_ok
            and volatility_ok
            and rising
            and not_blowoff
            and volume_ok
            and mtf_ok
        )

    def is_short_entry_signal(
        self,
        current_price: float,
        rsi_min: int = 60,
        rsi_max: int = 80,
        min_band_width: float = 2.0,
    ) -> bool:
        """Check short entry conditions (mirror of long, upper band / overbought RSI)"""
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()

        if bb is None:
            return False

        # Price at or above upper band (with 0.5% tolerance)
        at_bb = current_price >= bb.upper * 0.995

        # RSI in overbought range
        rsi_ok = rsi_min <= rsi <= rsi_max

        # Band width > minimum
        volatility_ok = bb.width_percent > min_band_width

        # Price below recent high (avoid shorting into spikes)
        recent_high = max(list(self.prices)[-5:]) if len(self.prices) >= 5 else current_price
        not_rising = current_price < recent_high * 1.01

        # Volume confirmation
        volume_ok = self._check_volume_confirmation()

        # Multi-timeframe: 15m RSI > 50 (not oversold) for shorts
        mtf_ok = True
        if self.enable_multi_timeframe and len(self.price_history_15m) >= 15:
            rsi_15m = self.calculate_rsi_15m()
            mtf_ok = rsi_15m > 50.0

        return at_bb and rsi_ok and volatility_ok and not_rising and volume_ok and mtf_ok

    def get_exit_levels(self, entry_price: float) -> ExitLevels:
        """Calculate take-profit and stop-loss levels"""
        bb = self.calculate_bb()

        if bb is None:
            # Use percentage targets if bands not ready
            return ExitLevels(
                tp1=entry_price * 1.025, tp2=entry_price * 1.04, stop=entry_price * 0.985
            )

        return ExitLevels(
            tp1=bb.middle,  # Middle band
            tp2=bb.upper,  # Upper band
            stop=entry_price * 0.985,  # 1.5% hard stop
        )

    def _check_volume_confirmation(self, threshold: float = 1.3) -> bool:
        """Check if current volume is above threshold x average (US-1.2)"""
        if len(self.volumes) < self.period:
            return True  # Allow if not enough data
        
        volumes = list(self.volumes)[-self.period:]
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        current_volume = volumes[-1]
        
        if avg_volume == 0:
            return True
        
        return current_volume >= avg_volume * threshold

    def add_ohlcv(self, timestamp: float, open_p: float, high: float, low: float, 
                  close: float, volume: float, timeframe_minutes: int = 5):
        """Add OHLCV data with multi-timeframe aggregation (US-1.4)"""
        # Always add to primary (5m) data
        self.add_price(close, volume, high=high, low=low)
        
        if not self.enable_multi_timeframe:
            return
        
        # Aggregate 15m candles from 5m data
        if timeframe_minutes == 5:
            self.current_candle_prices.append(close)
            self.current_candle_volumes.append(volume)
            
            # Check if we have 3 candles (15m = 3 * 5m)
            if len(self.current_candle_prices) >= 3:
                # Form 15m candle
                open_15m = self.current_candle_prices[0]
                high_15m = max(self.current_candle_prices)
                low_15m = min(self.current_candle_prices)
                close_15m = self.current_candle_prices[-1]
                volume_15m = sum(self.current_candle_volumes)
                
                self.price_history_15m.append({
                    'open': open_15m,
                    'high': high_15m,
                    'low': low_15m,
                    'close': close_15m,
                    'volume': volume_15m
                })
                
                # Reset current candle
                self.current_candle_prices = []
                self.current_candle_volumes = []

    def calculate_rsi_15m(self, period: int = 14) -> float:
        """Calculate RSI for 15m timeframe (US-1.4)"""
        if len(self.price_history_15m) < period + 1:
            return 50.0  # Neutral if not enough data
        
        closes = [c['close'] for c in list(self.price_history_15m)[-period-1:]]
        deltas = [closes[i + 1] - closes[i] for i in range(len(closes) - 1)]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def get_15m_trend(self, lookback: int = 3) -> str:
        """Get 15m trend direction (US-1.4)"""
        if len(self.price_history_15m) < lookback + 1:
            return "UNKNOWN"
        
        candles = list(self.price_history_15m)[-lookback:]
        closes = [c['close'] for c in candles]
        
        # Simple trend: higher highs and higher lows = uptrend
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        higher_highs = all(highs[i] > highs[i-1] for i in range(1, len(highs)))
        higher_lows = all(lows[i] > lows[i-1] for i in range(1, len(lows)))
        lower_highs = all(highs[i] < highs[i-1] for i in range(1, len(highs)))
        lower_lows = all(lows[i] < lows[i-1] for i in range(1, len(lows)))
        
        if higher_highs and higher_lows:
            return "UPTREND"
        elif lower_highs and lower_lows:
            return "DOWNTREND"
        else:
            return "RANGING"

    def check_multi_timeframe_confirm(self, current_price: float, 
                                       rsi_15m_max: float = 50.0,
                                       require_uptrend: bool = False) -> bool:
        """Check 15m timeframe confirmation (US-1.4)"""
        if not self.enable_multi_timeframe:
            return True  # Allow if disabled
        
        if len(self.price_history_15m) < 15:
            return True  # Allow if not enough 15m data
        
        # 15m RSI must be < 50 (not overbought)
        rsi_15m = self.calculate_rsi_15m()
        rsi_ok = rsi_15m < rsi_15m_max
        
        # Optional: require uptrend alignment
        trend = self.get_15m_trend()
        trend_ok = (trend == "UPTREND") if require_uptrend else True
        
        return rsi_ok and trend_ok

    def calculate_atr(self, period: int = 14) -> float:
        """Calculate ATR with Wilder smoothing (cached)"""
        if self._cache_atr is not None:
            return self._cache_atr
        prices = list(self.prices)
        highs = list(self.highs) if len(self.highs) == len(prices) else prices
        lows = list(self.lows) if len(self.lows) == len(prices) else prices
        if len(prices) < period + 1:
            self._cache_atr = 0.0
            return 0.0

        # True ranges
        trs = []
        for i in range(1, len(prices)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i - 1]),
                abs(lows[i] - prices[i - 1]),
            )
            trs.append(tr)

        if len(trs) < period:
            self._cache_atr = 0.0
            return 0.0

        # Wilder smoothing
        atr = sum(trs[:period]) / period
        for tr in trs[period:]:
            atr = (atr * (period - 1) + tr) / period

        self._cache_atr = float(atr)
        return self._cache_atr

    def get_exit_levels(self, entry_price: float, use_atr: bool = True, 
                        atr_multiplier: float = 1.5, max_stop_pct: float = 3.0,
                        target_multiplier: float = 1.0) -> ExitLevels:
        """Calculate take-profit and stop-loss levels with ATR support (US-2.1)"""
        bb = self.calculate_bb()
        
        if use_atr:
            atr = self.calculate_atr()
            if atr > 0:
                # ATR-based stop: Entry - (ATR * multiplier), capped at max_stop_pct
                atr_stop = entry_price - (atr * atr_multiplier)
                max_stop = entry_price * (1 - max_stop_pct / 100)
                stop = max(atr_stop, max_stop)  # Don't exceed max_stop_pct
            else:
                stop = entry_price * 0.985  # Fallback to 1.5% hard stop
        else:
            stop = entry_price * 0.985  # 1.5% hard stop

        if bb is None:
            # Use percentage targets if bands not ready
            return ExitLevels(
                tp1=entry_price * 1.025, tp2=entry_price * 1.04, stop=stop
            )

        # Regime-aware targets: widen for momentum/trend, tighten for mean reversion
        tp1 = entry_price + (bb.middle - entry_price) * target_multiplier
        tp2 = entry_price + (bb.upper - entry_price) * target_multiplier
        return ExitLevels(
            tp1=tp1,
            tp2=tp2,
            stop=stop,
        )

    def calculate_adx(self, period: int = 14) -> Tuple[float, float, float]:
        """Calculate ADX, +DI, -DI with Wilder smoothing (cached)"""
        if self._cache_adx is not None:
            return self._cache_adx
        prices = list(self.prices)
        highs = list(self.highs) if len(self.highs) == len(prices) else prices
        lows = list(self.lows) if len(self.lows) == len(prices) else prices

        n = len(prices)
        if n < period * 2 + 1:
            res = (25.0, 20.0, 20.0)
            self._cache_adx = res
            return res

        # +DM, -DM, TR
        plus_dm = [0.0] * (n - 1)
        minus_dm = [0.0] * (n - 1)
        trs = [0.0] * (n - 1)
        for i in range(1, n):
            up = highs[i] - highs[i - 1]
            down = lows[i - 1] - lows[i]
            plus_dm[i - 1] = up if (up > down and up > 0) else 0.0
            minus_dm[i - 1] = down if (down > up and down > 0) else 0.0
            trs[i - 1] = max(
                highs[i] - lows[i],
                abs(highs[i] - prices[i - 1]),
                abs(lows[i] - prices[i - 1]),
            )

        # Wilder smoothing
        def wilder(series, p):
            out = [0.0] * len(series)
            if len(series) < p:
                return out
            out[p - 1] = sum(series[:p])
            for i in range(p, len(series)):
                out[i] = out[i - 1] - (out[i - 1] / p) + series[i]
            return out

        sm_plus = wilder(plus_dm, period)
        sm_minus = wilder(minus_dm, period)
        sm_tr = wilder(trs, period)

        plus_di_arr = [0.0] * (n - 1)
        minus_di_arr = [0.0] * (n - 1)
        dx_arr = [0.0] * (n - 1)
        for i in range(period - 1, n - 1):
            tr = sm_tr[i]
            if tr == 0:
                continue
            pdi = 100.0 * sm_plus[i] / tr
            mdi = 100.0 * sm_minus[i] / tr
            plus_di_arr[i] = pdi
            minus_di_arr[i] = mdi
            denom = pdi + mdi
            dx_arr[i] = (100.0 * abs(pdi - mdi) / denom) if denom > 0 else 0.0

        # ADX = Wilder smoothing of DX
        adx_series = wilder(dx_arr[period - 1:], period)
        adx = adx_series[-1] / period if adx_series else 25.0

        plus_di = plus_di_arr[-1]
        minus_di = minus_di_arr[-1]

        res = (float(adx), float(plus_di), float(minus_di))
        self._cache_adx = res
        return res

    def detect_market_regime(self, adx_threshold: float = 25.0) -> str:
        """Detect market regime: TRENDING_UP, TRENDING_DOWN, RANGING, CHOPPY (US-1.5)"""
        adx, plus_di, minus_di = self.calculate_adx()
        
        if adx > adx_threshold:
            # Trending market
            if plus_di > minus_di:
                return "TRENDING_UP"
            else:
                return "TRENDING_DOWN"
        else:
            # Non-trending - check if ranging or choppy
            bb = self.calculate_bb()
            if bb and bb.width_percent < 1.5:  # Narrow bands = choppy
                return "CHOPPY"
            return "RANGING"

    def calculate_confidence_score(self) -> float:
        if self._cache_confidence is not None:
            return self._cache_confidence
        """Calculate entry confidence score 0-100 (US-3.2, calibrated).

        Calibrated against trade attribution: TRENDING_UP entries win more,
        deep oversold / extreme volume often mark falling knives, so their
        bonus is reduced and regime is weighted heavily.
        """
        score = 50.0  # Base score

        # RSI depth factor (moderate oversold = higher confidence)
        rsi = self.calculate_rsi()
        if 20 <= rsi < 30:
            score += 12  # Sweet spot
        elif rsi < 20:
            score += 4   # Too deep -> possible falling knife
        elif rsi < 40:
            score += 8   # Moderate oversold

        # Volume factor (moderate above-average = higher confidence)
        if len(self.volumes) >= self.period:
            volumes = list(self.volumes)[-self.period:]
            avg_vol = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
            current_vol = volumes[-1]
            if avg_vol > 0 and current_vol >= avg_vol * 1.3 and current_vol < avg_vol * 2.0:
                score += 8   # Good volume, not extreme
            elif avg_vol > 0 and current_vol >= avg_vol * 1.3:
                score += 4   # Very high volume -> caution

        # BB width factor (moderate width = more room, extreme = risk)
        bb = self.calculate_bb()
        if bb:
            if 2.0 < bb.width_percent <= 4.0:
                score += 6   # Moderate bands
            elif bb.width_percent > 4.0:
                score += 2   # Very wide -> high volatility risk

        # Regime factor (calibrated from attribution data)
        try:
            regime = self.detect_market_regime()
        except Exception:
            regime = "RANGING"
        regime_bonus = {
            "TRENDING_UP": 12,
            "RANGING": 0,
            "TRENDING_DOWN": -8,
            "CHOPPY": -15,
        }
        score += regime_bonus.get(regime, 0)

        val = min(100.0, max(0.0, score))
        self._cache_confidence = val
        return val

    def get_stats(self) -> dict:
        """Get current indicator statistics"""
        bb = self.calculate_bb()
        rsi = self.calculate_rsi()
        atr = self.calculate_atr()
        regime = self.detect_market_regime()
        confidence = self.calculate_confidence_score()

        return {
            "bb_lower": bb.lower if bb else None,
            "bb_middle": bb.middle if bb else None,
            "bb_upper": bb.upper if bb else None,
            "bb_width": bb.width_percent if bb else None,
            "rsi": rsi,
            "atr": atr,
            "regime": regime,
            "confidence": confidence,
            "data_points": len(self.prices),
        }
