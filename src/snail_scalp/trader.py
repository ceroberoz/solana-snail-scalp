"""Execution Logic with Live and Simulation Modes"""

import time
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum


class TradeStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    PARTIAL = "partial"


class CloseReason(Enum):
    TP1 = "tp1"
    TP2 = "tp2"
    STOP_LOSS = "stop_loss"
    MANUAL = "manual"


@dataclass
class Trade:
    entry_price: float
    size_usd: float
    entry_time: float
    dca_done: bool = False
    tp1_hit: bool = False
    status: TradeStatus = TradeStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[float] = None
    close_reason: Optional[CloseReason] = None
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    
    # US-2.3: Trailing stop tracking
    highest_price: float = 0.0
    last_trailing_update: float = 0.0
    
    # US-2.2: Breakeven stop price
    breakeven_stop_price: float = 0.0
    
    # US-2.6: Partial scaling tracking
    scale_levels_hit: List[bool] = None  # Track which scale levels hit
    final_position_size: float = 0.0  # Remaining size after scaling
    
    # US-1.5: Market regime at entry
    entry_regime: str = ""
    
    def __post_init__(self):
        if self.highest_price == 0.0:
            self.highest_price = self.entry_price
        if self.scale_levels_hit is None:
            self.scale_levels_hit = []
        if self.final_position_size == 0.0:
            self.final_position_size = self.size_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_price": self.entry_price,
            "size_usd": self.size_usd,
            "entry_time": self.entry_time,
            "entry_time_str": datetime.fromtimestamp(self.entry_time).isoformat(),
            "dca_done": self.dca_done,
            "tp1_hit": self.tp1_hit,
            "status": self.status.value,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time,
            "exit_time_str": datetime.fromtimestamp(self.exit_time).isoformat()
            if self.exit_time
            else None,
            "close_reason": self.close_reason.value if self.close_reason else None,
            "pnl_usd": self.pnl_usd,
            "pnl_pct": self.pnl_pct,
        }


class Trader:
    """Main trading execution handler"""

    def __init__(
        self,
        strategy_config: Dict[str, Any],
        risk_manager,
        simulate: bool = False,
        results_file: str = "data/trades.json",
    ):
        self.config = strategy_config
        self.risk = risk_manager
        self.simulate = simulate
        self.results_file = Path(results_file)

        # Use different results file for simulation
        if simulate:
            self.results_file = Path("data/simulation_trades.json")

        self.active_position: Optional[Trade] = None
        self.trade_history: List[Trade] = []
        self.total_pnl: float = 0.0

        # Load existing history
        self._load_history()

    def _load_history(self):
        """Load trade history from file"""
        if self.results_file.exists():
            try:
                with open(self.results_file, "r") as f:
                    data = json.load(f)
                    print(f"[LOAD] Loaded {len(data.get('trades', []))} historical trades")
            except Exception as e:
                print(f"[WARN] Could not load trade history: {e}")

    def _save_history(self):
        """Save trade history to file"""
        history = {
            "total_pnl": self.total_pnl,
            "total_trades": len(self.trade_history),
            "trades": [t.to_dict() for t in self.trade_history],
        }
        with open(self.results_file, "w") as f:
            json.dump(history, f, indent=2)

    async def check_entry(
        self, current_price: float, indicators, available_capital: float = 20.0,
        symbol: str = "", active_symbols: List[str] = None, correlation_tracker = None
    ) -> bool:
        """Evaluate if we should enter a position with Sprint 5-6 features"""
        if self.active_position:
            return False

        if not self.risk.can_trade_today():
            return False

        if not self.risk.is_trading_window():
            return False

        # US-1.5: Check market regime (skip choppy markets)
        if self.config.get("use_regime_detection", True):
            regime = indicators.detect_market_regime(
                self.config.get("regime_adx_threshold", 25.0)
            )
            if regime == "CHOPPY" and self.config.get("skip_choppy_markets", True):
                print(f"[SKIP] Market regime is CHOPPY - skipping trade")
                return False
        else:
            regime = "UNKNOWN"

        if indicators.is_entry_signal(
            current_price,
            rsi_min=self.config.get("rsi_oversold_min", 25),
            rsi_max=self.config.get("rsi_oversold_max", 35),
            min_band_width=self.config.get("min_band_width_percent", 2.0),
        ):
            # US-3.3: Check correlation risk before entry
            if correlation_tracker and active_symbols and symbol:
                use_corr = self.config.get("use_correlation_check", True)
                max_corr = self.config.get("max_correlated_positions", 2)
                if use_corr:
                    allowed, correlated = correlation_tracker.check_correlation_risk(
                        symbol, active_symbols, max_corr
                    )
                    if not allowed:
                        print(f"[SKIP] Correlation risk: {symbol} correlated with {correlated}")
                        return False
            
            return await self._execute_entry(current_price, indicators, available_capital, regime)

        return False

    async def _execute_entry(self, price: float, indicators, available_capital: float, regime: str = "") -> bool:
        """Execute entry order with Sprint 5-6 enhancements"""
        base_size = self.config.get("primary_allocation", 3.0)
        
        # US-3.2: Dynamic position sizing based on confidence
        if self.config.get("use_dynamic_sizing", True):
            confidence = indicators.calculate_confidence_score()
            min_ratio = self.config.get("min_position_ratio", 0.5)
            max_ratio = self.config.get("max_position_ratio", 1.5)
            
            # Size = Base * (0.5 + confidence/100)
            size_multiplier = min_ratio + (confidence / 100.0)
            size_multiplier = max(min_ratio, min(max_ratio, size_multiplier))
            
            # US-1.5: Adjust by regime
            if self.config.get("position_size_by_regime", True) and regime:
                regime_multipliers = {
                    "TRENDING_UP": 1.2,
                    "TRENDING_DOWN": 0.7,  # Reduce size in downtrend
                    "RANGING": 1.0,
                    "CHOPPY": 0.6,  # Should not reach here due to skip
                }
                size_multiplier *= regime_multipliers.get(regime, 1.0)
            
            size_usd = base_size * size_multiplier
            print(f"   Confidence: {confidence:.0f}/100, Multiplier: {size_multiplier:.2f}x")
            if regime:
                print(f"   Regime: {regime}")
        else:
            size_usd = base_size

        size_usd = self.risk.check_position_size(
            available_capital,
            "primary",
            size_usd,
        )

        print(f"\n[ENTRY] ENTRY SIGNAL at ${price:.4f}")
        print(f"   Size: ${size_usd:.2f} USDC")

        # In simulation, we just log it
        if self.simulate:
            print(f"   [SIMULATION] Position opened")
        else:
            # TODO: Jupiter API integration here
            print(f"   [LIVE] Jupiter swap would execute here")

        # US-2.6: Initialize partial scaling tracking
        scale_config = self.config.get("partial_scale_levels", ((0.25, 1.5), (0.25, 2.5), (0.25, 4.0)))
        scale_levels_hit = [False] * len(scale_config)
        
        self.active_position = Trade(
            entry_price=price, 
            size_usd=size_usd, 
            entry_time=time.time(),
            scale_levels_hit=scale_levels_hit,
            final_position_size=size_usd,
            entry_regime=regime
        )

        print(f"[OK] Position opened: ${size_usd:.2f} @ ${price:.4f}")
        return True

    async def manage_position(self, current_price: float, indicators):
        """Check exits and DCA opportunities with Sprint 3-4 enhancements"""
        if not self.active_position:
            return

        pos = self.active_position
        entry = pos.entry_price
        pnl_pct = (current_price - entry) / entry * 100
        current_time = time.time()

        # US-2.5: Check time-based exit (max hold time)
        use_time_exit = self.config.get("use_time_exit", True)
        max_hold_minutes = self.config.get("max_hold_time_minutes", 120)
        if use_time_exit:
            hold_time_minutes = (current_time - pos.entry_time) / 60
            if hold_time_minutes >= max_hold_minutes:
                print(f"\n[TIME] TIME EXIT at ${current_price:.4f} (held {hold_time_minutes:.0f}min, max {max_hold_minutes}min)")
                await self._close_position(current_price, CloseReason.MANUAL)
                return

        # Check DCA opportunity (down 1%, haven't DCA'd yet) - US-3.1: DCA size = 50% of original
        dca_trigger = self.config.get("dca_trigger_percent", 1.0)
        if pnl_pct <= -dca_trigger and not pos.dca_done:
            # US-3.1: DCA size is 50% of original position (not 100%)
            dca_size_ratio = self.config.get("dca_allocation_ratio", 0.5)
            dca_size = pos.size_usd * dca_size_ratio
            
            # Check if we have enough capital
            available = self.risk.check_position_size(
                pos.size_usd * 3,  # Approximate available
                "dca",
                dca_size,
            )
            
            if available >= dca_size > 0:
                print(f"\n[DCA] DCA Trigger at ${current_price:.4f} (down {pnl_pct:.2f}%)")
                print(f"   DCA size: ${dca_size:.2f} (50% of original ${pos.size_usd:.2f})")
                # Execute DCA
                old_size = pos.size_usd
                pos.size_usd += dca_size
                pos.entry_price = (entry * old_size + current_price * dca_size) / pos.size_usd
                pos.dca_done = True
                print(f"   New avg entry: ${pos.entry_price:.4f}, Total: ${pos.size_usd:.2f}")

        # US-2.3: Update highest price and trailing stop tracking
        use_trailing = self.config.get("use_trailing_stop", True)
        trailing_pct = self.config.get("trailing_stop_percent", 1.0)
        trailing_interval = self.config.get("trailing_update_interval", 300)
        
        if current_price > pos.highest_price:
            pos.highest_price = current_price

        # Check Stop Loss - US-2.1: ATR-based stop, US-2.2: Breakeven stop after TP1
        use_atr = self.config.get("use_atr_stop", True)
        atr_multiplier = self.config.get("stop_loss_atr_multiplier", 1.5)
        max_stop_pct = self.config.get("stop_loss_max_percent", 3.0)
        use_breakeven = self.config.get("use_breakeven_stop", True)
        
        # Calculate base stop price
        exit_levels = indicators.get_exit_levels(
            entry, use_atr=use_atr, atr_multiplier=atr_multiplier, max_stop_pct=max_stop_pct
        )
        stop_price = exit_levels.stop
        
        # US-2.2: After TP1, move stop to breakeven + buffer
        if pos.tp1_hit and use_breakeven and pos.breakeven_stop_price == 0.0:
            buffer_pct = self.config.get("breakeven_buffer_percent", 0.1)
            breakeven_price = entry * (1 + buffer_pct / 100)
            # Don't move stop below breakeven after TP1
            if stop_price < breakeven_price:
                pos.breakeven_stop_price = breakeven_price
                print(f"\n[BREAKEVEN] Stop moved to breakeven: ${breakeven_price:.4f} (+{buffer_pct}% buffer)")
        
        # Use breakeven stop if set (higher than regular stop)
        if pos.breakeven_stop_price > 0:
            stop_price = max(stop_price, pos.breakeven_stop_price)
        
        # US-2.3: Trailing stop after TP1 (don't trail below breakeven)
        if pos.tp1_hit and use_trailing:
            time_since_update = current_time - pos.last_trailing_update
            if time_since_update >= trailing_interval:
                trailing_stop = pos.highest_price * (1 - trailing_pct / 100)
                # Don't trail below breakeven
                min_stop = pos.breakeven_stop_price if pos.breakeven_stop_price > 0 else entry
                effective_trailing = max(trailing_stop, min_stop)
                if effective_trailing > stop_price:
                    stop_price = effective_trailing
                    print(f"\n[TRAIL] Trailing stop updated: ${stop_price:.4f} (1% below high ${pos.highest_price:.4f})")
                pos.last_trailing_update = current_time
        
        stop_loss_pct = (entry - stop_price) / entry * 100
        
        if current_price <= stop_price:
            reason_str = "STOP LOSS"
            if pos.tp1_hit and pos.breakeven_stop_price > 0 and current_price <= pos.breakeven_stop_price:
                reason_str = "BREAKEVEN STOP"
            elif pos.tp1_hit and use_trailing:
                reason_str = "TRAILING STOP"
            print(f"\n[STOP] {reason_str} at ${current_price:.4f} ({pnl_pct:.2f}%) [Stop: ${stop_price:.4f}, {-stop_loss_pct:.2f}%]")
            await self._close_position(current_price, CloseReason.STOP_LOSS)
            return

        # US-2.6: Partial Profit Scaling (25%, 50%, 75%) + Final Trailing
        use_partial = self.config.get("use_partial_scaling", True)
        if use_partial:
            scale_config = self.config.get("partial_scale_levels", ((0.25, 1.5), (0.25, 2.5), (0.25, 4.0)))
            
            for i, (portion, profit_pct) in enumerate(scale_config):
                if i < len(pos.scale_levels_hit) and not pos.scale_levels_hit[i]:
                    target_price = entry * (1 + profit_pct / 100)
                    if current_price >= target_price:
                        # Close portion at this level
                        close_size = pos.final_position_size * portion
                        actual_portion = close_size / pos.size_usd if pos.size_usd > 0 else 0
                        actual_portion = min(actual_portion, 1.0)  # Cap at 100%
                        
                        print(f"\n[SCALE-{i+1}] Scale out at +{profit_pct}%")
                        await self._partial_close(current_price, actual_portion, CloseReason.TP1)
                        pos.scale_levels_hit[i] = True
                        
                        # If this was the last scale level, enable final trailing
                        if i == len(scale_config) - 1:
                            pos.tp1_hit = True  # Enable trailing stop logic
                            print("   Final 25% using trailing stop")
                        break  # Only one scale per check
        else:
            # Legacy TP1/TP2 logic
            use_atr_targets = self.config.get("use_atr_targets", True)
            if use_atr_targets and indicators.calculate_atr() > 0:
                atr = indicators.calculate_atr()
                tp1_mult = self.config.get("tp1_atr_multiplier", 1.0)
                tp2_mult = self.config.get("tp2_atr_multiplier", 2.0)
                tp_min = self.config.get("tp_min_percent", 2.0)
                tp_max = self.config.get("tp_max_percent", 8.0)
                
                tp1_atr_pct = max(min(atr / entry * tp1_mult * 100, tp_max), tp_min)
                tp2_atr_pct = max(min(atr / entry * tp2_mult * 100, tp_max), tp_min)
                
                tp1_price = entry * (1 + tp1_atr_pct / 100)
                tp2_price = entry * (1 + tp2_atr_pct / 100)
            else:
                tp1_price = entry * (1 + self.config.get("tp1_percent", 2.5) / 100)
                tp2_price = entry * (1 + self.config.get("tp2_percent", 4.0) / 100)

            if current_price >= tp1_price and not pos.tp1_hit:
                tp1_pct = (tp1_price - entry) / entry * 100
                print(f"\n[TP1] TP1 HIT at ${current_price:.4f} ({pnl_pct:.2f}%) [Target: ${tp1_price:.4f}, +{tp1_pct:.2f}%]")
                await self._partial_close(current_price, 0.5, CloseReason.TP1)
                pos.tp1_hit = True

            if current_price >= tp2_price and pos.tp1_hit:
                tp2_pct = (tp2_price - entry) / entry * 100
                print(f"\n[TP2] TP2 HIT at ${current_price:.4f} ({pnl_pct:.2f}%) [Target: ${tp2_price:.4f}, +{tp2_pct:.2f}%]")
                await self._close_position(current_price, CloseReason.TP2)

    async def _partial_close(self, price: float, portion: float, reason: CloseReason):
        """Close portion of position (TP1)"""
        pos = self.active_position
        size = pos.size_usd * portion
        pnl = (price - pos.entry_price) / pos.entry_price * size

        print(f"   Closing {portion * 100:.0f}% (${size:.2f}) PnL: ${pnl:.2f}")

        # Update position
        pos.size_usd -= size
        pos.pnl_usd += pnl
        pos.status = TradeStatus.PARTIAL

        # Record partial trade
        self.risk.record_trade(pnl)
        self.total_pnl += pnl

    async def _close_position(self, price: float, reason: CloseReason):
        """Close full position"""
        pos = self.active_position
        entry = pos.entry_price
        size = pos.size_usd

        # Calculate remaining PnL
        remaining_pnl = (price - entry) / entry * size
        total_pnl = pos.pnl_usd + remaining_pnl
        total_pct = (price - entry) / entry * 100

        print(f"\n[CLOSE] Position Closed ({reason.value})")
        print(f"   Entry: ${entry:.4f} -> Exit: ${price:.4f}")
        print(f"   Total PnL: ${total_pnl:.2f} ({total_pct:.2f}%)")

        # Update position record
        pos.exit_price = price
        pos.exit_time = time.time()
        pos.close_reason = reason
        pos.pnl_usd = total_pnl
        pos.pnl_pct = total_pct
        pos.status = TradeStatus.CLOSED

        # Record and save
        self.risk.record_trade(total_pnl)
        self.total_pnl += total_pnl
        self.trade_history.append(pos)
        self._save_history()

        # Clear active position
        self.active_position = None

    def get_summary(self) -> Dict[str, Any]:
        """Get trading summary"""
        return {
            "total_pnl": self.total_pnl,
            "total_trades": len(self.trade_history),
            "active_position": self.active_position.to_dict() if self.active_position else None,
            "win_rate": sum(1 for t in self.trade_history if t.pnl_usd > 0)
            / len(self.trade_history)
            * 100
            if self.trade_history
            else 0,
        }

    def reset(self):
        """Reset trader state"""
        self.active_position = None
        self.trade_history = []
        self.total_pnl = 0.0
        if self.results_file.exists():
            self.results_file.unlink()
        print("[RESET] Trader reset")
