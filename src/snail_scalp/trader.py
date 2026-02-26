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
        self, current_price: float, indicators, available_capital: float = 20.0
    ) -> bool:
        """Evaluate if we should enter a position"""
        if self.active_position:
            return False

        if not self.risk.can_trade_today():
            return False

        if not self.risk.is_trading_window():
            return False

        if indicators.is_entry_signal(
            current_price,
            rsi_min=self.config.get("rsi_oversold_min", 25),
            rsi_max=self.config.get("rsi_oversold_max", 35),
            min_band_width=self.config.get("min_band_width_percent", 2.0),
        ):
            return await self._execute_entry(current_price, indicators, available_capital)

        return False

    async def _execute_entry(self, price: float, indicators, available_capital: float) -> bool:
        """Execute entry order"""
        size_usd = self.risk.check_position_size(
            available_capital,
            "primary",
            self.config.get("primary_allocation", 3.0),
        )

        print(f"\n[ENTRY] ENTRY SIGNAL at ${price:.4f}")
        print(f"   Size: ${size_usd:.2f} USDC")

        # In simulation, we just log it
        if self.simulate:
            print(f"   [SIMULATION] Position opened")
        else:
            # TODO: Jupiter API integration here
            print(f"   [LIVE] Jupiter swap would execute here")

        self.active_position = Trade(entry_price=price, size_usd=size_usd, entry_time=time.time())

        print(f"[OK] Position opened: ${size_usd:.2f} @ ${price:.4f}")
        return True

    async def manage_position(self, current_price: float, indicators):
        """Check exits and DCA opportunities"""
        if not self.active_position:
            return

        pos = self.active_position
        entry = pos.entry_price
        pnl_pct = (current_price - entry) / entry * 100

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

        # Check Stop Loss - US-2.1: ATR-based stop or fallback to fixed
        use_atr = self.config.get("use_atr_stop", True)
        atr_multiplier = self.config.get("stop_loss_atr_multiplier", 1.5)
        max_stop_pct = self.config.get("stop_loss_max_percent", 3.0)
        
        exit_levels = indicators.get_exit_levels(
            entry, use_atr=use_atr, atr_multiplier=atr_multiplier, max_stop_pct=max_stop_pct
        )
        stop_price = exit_levels.stop
        stop_loss_pct = (entry - stop_price) / entry * 100
        
        if current_price <= stop_price:
            print(f"\n[STOP] STOP LOSS at ${current_price:.4f} ({pnl_pct:.2f}%) [ATR stop: ${stop_price:.4f}, {-stop_loss_pct:.2f}%]")
            await self._close_position(current_price, CloseReason.STOP_LOSS)
            return

        # Check TP1 (2.5%)
        tp1 = self.config.get("tp1_percent", 2.5)
        if pnl_pct >= tp1 and not pos.tp1_hit:
            print(f"\n[TP1] TP1 HIT at ${current_price:.4f} ({pnl_pct:.2f}%)")
            await self._partial_close(current_price, 0.5, CloseReason.TP1)
            pos.tp1_hit = True

        # Check TP2 (4%)
        tp2 = self.config.get("tp2_percent", 4.0)
        if pnl_pct >= tp2 and pos.tp1_hit:
            print(f"\n[TP2] TP2 HIT at ${current_price:.4f} ({pnl_pct:.2f}%)")
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
