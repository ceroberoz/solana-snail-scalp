"""Capital Protection and Risk Management"""

import json
import os
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class DailyStats:
    date: str
    trades_today: int = 0
    wins: int = 0
    losses: int = 0
    pnl_usd: float = 0.0
    consecutive_losses: int = 0
    max_concurrent: int = 0
    paused_until: Optional[str] = None


class RiskManager:
    """Manages trading risk and circuit breakers"""

    def __init__(
        self,
        daily_loss_limit: float = 1.50,
        max_consecutive_losses: int = 2,
        trading_start_utc: int = 9,
        trading_end_utc: int = 11,
        state_file: str = "data/trading_state.json",
        simulate: bool = False,
    ):
        self.daily_loss_limit = daily_loss_limit
        self.max_consecutive_losses = max_consecutive_losses
        self.trading_start_utc = trading_start_utc
        self.trading_end_utc = trading_end_utc
        self.state_file = Path(state_file)
        self.simulate = simulate

        # Use different state file for simulation
        if simulate:
            self.state_file = Path("data/simulation_state.json")

        self.daily_stats = self._load_state()

    def _load_state(self) -> DailyStats:
        """Persist state between restarts"""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                saved = json.load(f)
                # Reset daily stats if new day (or new simulation)
                if saved.get("date") != str(date.today()):
                    return self._new_day()
                return DailyStats(**saved)
        return self._new_day()

    def _new_day(self) -> DailyStats:
        """Create fresh daily stats"""
        return DailyStats(date=str(date.today()))

    def _save_state(self):
        """Save current state to file"""
        with open(self.state_file, "w") as f:
            json.dump(asdict(self.daily_stats), f, indent=2)

    def can_trade_today(self) -> bool:
        """Check all circuit breakers"""
        # Check pause
        if self.daily_stats.paused_until:
            pause_time = datetime.fromisoformat(self.daily_stats.paused_until)
            if datetime.now() < pause_time:
                print(f"⏸️ Trading paused until {pause_time}")
                return False
            else:
                self.daily_stats.paused_until = None
                self._save_state()

        # Daily loss limit
        if self.daily_stats.pnl_usd <= -self.daily_loss_limit:
            print(f"[STOP] Daily loss limit hit (${self.daily_stats.pnl_usd:.2f}). Stopping.")
            return False

        # Consecutive losses
        if self.daily_stats.consecutive_losses >= self.max_consecutive_losses:
            print(f"[STOP] {self.max_consecutive_losses} consecutive losses. Pausing 24h.")
            self.daily_stats.paused_until = (datetime.now() + timedelta(hours=24)).isoformat()
            self._save_state()
            return False

        return True

    def is_trading_window(self, current_time: Optional[datetime] = None) -> bool:
        """Check if within trading hours (09:00-11:00 UTC)"""
        if current_time is None:
            current_time = datetime.now()

        # Handle both timezone-aware and naive datetimes
        try:
            hour = current_time.hour
        except AttributeError:
            hour = datetime.now().hour

        return self.trading_start_utc <= hour < self.trading_end_utc

    def check_position_size(
        self, available_capital: float, allocation: str = "primary", max_position: float = 3.0
    ) -> float:
        """Return USD amount to trade"""
        if allocation == "primary":
            return min(max_position, available_capital * 0.15)
        elif allocation == "dca":
            return min(max_position, available_capital * 0.15)
        return 0.0

    def record_trade(self, pnl_usd: float):
        """Update statistics after trade"""
        self.daily_stats.trades_today += 1
        self.daily_stats.pnl_usd += pnl_usd

        if pnl_usd > 0:
            self.daily_stats.wins += 1
            self.daily_stats.consecutive_losses = 0
        else:
            self.daily_stats.losses += 1
            self.daily_stats.consecutive_losses += 1

        self._save_state()

    def get_stats(self) -> Dict[str, Any]:
        """Get current risk statistics"""
        return {
            "date": self.daily_stats.date,
            "trades_today": self.daily_stats.trades_today,
            "wins": self.daily_stats.wins,
            "losses": self.daily_stats.losses,
            "win_rate": (
                (self.daily_stats.wins / self.daily_stats.trades_today * 100)
                if self.daily_stats.trades_today > 0
                else 0
            ),
            "pnl_usd": self.daily_stats.pnl_usd,
            "consecutive_losses": self.daily_stats.consecutive_losses,
            "can_trade": self.can_trade_today(),
            "in_window": self.is_trading_window(),
        }

    def reset(self):
        """Reset all stats (useful for simulation)"""
        self.daily_stats = self._new_day()
        if self.state_file.exists():
            self.state_file.unlink()
        print("[RESET] Risk manager reset")
