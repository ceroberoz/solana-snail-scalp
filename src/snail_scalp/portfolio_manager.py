"""Multi-Token Portfolio Manager

Manages multiple simultaneous positions across different tokens
with proper risk allocation and performance tracking.
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

from snail_scalp.token_screener import TokenMetrics, HypeScore, RiskLevel
from snail_scalp.trader import Trade, TradeStatus, CloseReason


class PositionStatus(Enum):
    PENDING = "pending"      # Waiting for entry signal
    OPEN = "open"            # Position active
    PARTIAL = "partial"      # TP1 hit, holding remaining
    CLOSED = "closed"        # Fully closed


@dataclass
class TokenPosition:
    """Position for a specific token"""
    symbol: str
    address: str
    
    # Position details
    entry_price: float = 0.0
    size_usd: float = 0.0
    entry_time: Optional[datetime] = None
    
    # Status
    status: PositionStatus = PositionStatus.PENDING
    
    # Trade management
    dca_done: bool = False
    tp1_hit: bool = False
    
    # PnL tracking
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Exit
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    close_reason: Optional[CloseReason] = None
    
    # Metadata
    hype_score_at_entry: float = 0.0
    risk_level_at_entry: RiskLevel = RiskLevel.MODERATE
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "address": self.address,
            "entry_price": self.entry_price,
            "size_usd": self.size_usd,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "status": self.status.value,
            "dca_done": self.dca_done,
            "tp1_hit": self.tp1_hit,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "exit_price": self.exit_price,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "close_reason": self.close_reason.value if self.close_reason else None,
            "hype_score_at_entry": self.hype_score_at_entry,
            "risk_level_at_entry": self.risk_level_at_entry.name,
        }


@dataclass
class PortfolioState:
    """Overall portfolio state"""
    initial_capital: float = 20.0
    available_capital: float = 20.0
    total_allocated: float = 0.0
    
    # Performance
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    
    # Tracking
    positions: Dict[str, TokenPosition] = field(default_factory=dict)
    closed_positions: List[TokenPosition] = field(default_factory=list)
    
    # Limits
    max_concurrent_positions: int = 3
    max_allocation_per_token: float = 6.0  # $6 max per token (30% of $20)
    
    @property
    def total_value(self) -> float:
        return self.initial_capital + self.total_realized_pnl + self.total_unrealized_pnl
    
    @property
    def total_return_pct(self) -> float:
        if self.initial_capital <= 0:
            return 0.0
        return ((self.total_value - self.initial_capital) / self.initial_capital) * 100
    
    @property
    def open_position_count(self) -> int:
        return sum(1 for p in self.positions.values() if p.status in [PositionStatus.OPEN, PositionStatus.PARTIAL])
    
    def can_open_position(self, size_usd: float) -> bool:
        """Check if we can open a new position"""
        if self.open_position_count >= self.max_concurrent_positions:
            return False
        if self.available_capital < size_usd:
            return False
        if size_usd > self.max_allocation_per_token:
            return False
        return True


class PortfolioManager:
    """Manages multiple token positions with risk allocation"""
    
    def __init__(
        self,
        initial_capital: float = 20.0,
        max_positions: int = 3,
        state_file: str = "data/portfolio_state.json",
        simulate: bool = False,
    ):
        self.initial_capital = initial_capital
        self.state_file = Path(state_file)
        self.simulate = simulate
        
        if simulate:
            self.state_file = Path("data/simulation_portfolio.json")
        
        self.state = self._load_state()
        
        # Ensure state is initialized
        if self.state.initial_capital == 0:
            self.state.initial_capital = initial_capital
            self.state.available_capital = initial_capital
    
    def _load_state(self) -> PortfolioState:
        """Load portfolio state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct positions
                positions = {}
                for symbol, pos_data in data.get('positions', {}).items():
                    positions[symbol] = self._dict_to_position(pos_data)
                
                closed_positions = [
                    self._dict_to_position(p) for p in data.get('closed_positions', [])
                ]
                
                return PortfolioState(
                    initial_capital=data.get('initial_capital', self.initial_capital),
                    available_capital=data.get('available_capital', self.initial_capital),
                    total_realized_pnl=data.get('total_realized_pnl', 0.0),
                    total_unrealized_pnl=data.get('total_unrealized_pnl', 0.0),
                    positions=positions,
                    closed_positions=closed_positions,
                    max_concurrent_positions=data.get('max_concurrent_positions', 3),
                    max_allocation_per_token=data.get('max_allocation_per_token', 6.0),
                )
            except Exception as e:
                print(f"[WARN] Could not load portfolio state: {e}")
        
        return PortfolioState(initial_capital=self.initial_capital, available_capital=self.initial_capital)
    
    def _save_state(self):
        """Save portfolio state to file"""
        data = {
            "initial_capital": self.state.initial_capital,
            "available_capital": self.state.available_capital,
            "total_realized_pnl": self.state.total_realized_pnl,
            "total_unrealized_pnl": self.state.total_unrealized_pnl,
            "max_concurrent_positions": self.state.max_concurrent_positions,
            "max_allocation_per_token": self.state.max_allocation_per_token,
            "positions": {k: v.to_dict() for k, v in self.state.positions.items()},
            "closed_positions": [p.to_dict() for p in self.state.closed_positions],
            "last_updated": datetime.now().isoformat(),
        }
        
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _dict_to_position(self, data: Dict) -> TokenPosition:
        """Convert dict to TokenPosition"""
        pos = TokenPosition(
            symbol=data['symbol'],
            address=data['address'],
            entry_price=data.get('entry_price', 0.0),
            size_usd=data.get('size_usd', 0.0),
            status=PositionStatus(data.get('status', 'pending')),
            dca_done=data.get('dca_done', False),
            tp1_hit=data.get('tp1_hit', False),
            realized_pnl=data.get('realized_pnl', 0.0),
            exit_price=data.get('exit_price'),
            close_reason=CloseReason(data['close_reason']) if data.get('close_reason') else None,
            hype_score_at_entry=data.get('hype_score_at_entry', 0.0),
            risk_level_at_entry=RiskLevel[data.get('risk_level_at_entry', 'MODERATE')],
        )
        
        # Parse timestamps
        if data.get('entry_time'):
            pos.entry_time = datetime.fromisoformat(data['entry_time'])
        if data.get('exit_time'):
            pos.exit_time = datetime.fromisoformat(data['exit_time'])
        
        return pos
    
    def get_position(self, symbol: str) -> Optional[TokenPosition]:
        """Get position for a specific token"""
        return self.state.positions.get(symbol)
    
    def has_open_position(self, symbol: str) -> bool:
        """Check if we have an open position for a token"""
        pos = self.state.positions.get(symbol)
        if pos:
            return pos.status in [PositionStatus.OPEN, PositionStatus.PARTIAL]
        return False
    
    def calculate_position_size(self, symbol: str, risk_level: RiskLevel) -> float:
        """Calculate appropriate position size based on risk"""
        base_size = 3.0  # $3 base
        
        # Adjust for risk
        if risk_level == RiskLevel.EXTREME:
            return min(base_size * 0.5, self.state.available_capital)
        elif risk_level == RiskLevel.HIGH:
            return min(base_size * 0.75, self.state.available_capital)
        elif risk_level == RiskLevel.MODERATE:
            return min(base_size, self.state.available_capital)
        else:  # LOW or MINIMAL
            return min(base_size, self.state.available_capital)
    
    def open_position(
        self,
        symbol: str,
        address: str,
        entry_price: float,
        size_usd: float,
        hype_score: float,
        risk_level: RiskLevel
    ) -> bool:
        """Open a new position"""
        if not self.state.can_open_position(size_usd):
            return False
        
        if self.has_open_position(symbol):
            return False
        
        position = TokenPosition(
            symbol=symbol,
            address=address,
            entry_price=entry_price,
            size_usd=size_usd,
            entry_time=datetime.now(),
            status=PositionStatus.OPEN,
            hype_score_at_entry=hype_score,
            risk_level_at_entry=risk_level,
        )
        
        self.state.positions[symbol] = position
        self.state.available_capital -= size_usd
        self.state.total_allocated += size_usd
        
        self._save_state()
        return True
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update unrealized PnL for a position"""
        pos = self.state.positions.get(symbol)
        if not pos or pos.status not in [PositionStatus.OPEN, PositionStatus.PARTIAL]:
            return
        
        # Calculate unrealized PnL
        remaining_size = pos.size_usd
        price_change = (current_price - pos.entry_price) / pos.entry_price
        pos.unrealized_pnl = remaining_size * price_change
        
        # Update total unrealized
        self._update_total_unrealized()
    
    def execute_dca(self, symbol: str, dca_price: float, dca_size: float) -> bool:
        """Execute DCA for a position"""
        pos = self.state.positions.get(symbol)
        if not pos or pos.status != PositionStatus.OPEN:
            return False
        
        if pos.dca_done:
            return False
        
        if dca_size > self.state.available_capital:
            return False
        
        # Calculate new average entry
        old_size = pos.size_usd
        pos.size_usd += dca_size
        pos.entry_price = (pos.entry_price * old_size + dca_price * dca_size) / pos.size_usd
        pos.dca_done = True
        
        self.state.available_capital -= dca_size
        self.state.total_allocated += dca_size
        
        self._save_state()
        return True
    
    def partial_close(self, symbol: str, exit_price: float, portion: float = 0.5) -> Tuple[bool, float]:
        """Close portion of position (TP1)"""
        pos = self.state.positions.get(symbol)
        if not pos or pos.status != PositionStatus.OPEN:
            return False, 0.0
        
        close_size = pos.size_usd * portion
        price_change = (exit_price - pos.entry_price) / pos.entry_price
        pnl = close_size * price_change
        
        pos.realized_pnl += pnl
        pos.size_usd -= close_size
        pos.tp1_hit = True
        pos.status = PositionStatus.PARTIAL
        
        self.state.available_capital += close_size + pnl
        self.state.total_allocated -= close_size
        self.state.total_realized_pnl += pnl
        
        self._save_state()
        return True, pnl
    
    def close_position(self, symbol: str, exit_price: float, reason: CloseReason) -> Tuple[bool, float]:
        """Close full position"""
        pos = self.state.positions.get(symbol)
        if not pos or pos.status not in [PositionStatus.OPEN, PositionStatus.PARTIAL]:
            return False, 0.0
        
        # Calculate remaining PnL
        remaining_size = pos.size_usd
        price_change = (exit_price - pos.entry_price) / pos.entry_price
        remaining_pnl = remaining_size * price_change
        
        total_pnl = pos.realized_pnl + remaining_pnl
        
        # Update position
        pos.exit_price = exit_price
        pos.exit_time = datetime.now()
        pos.close_reason = reason
        pos.status = PositionStatus.CLOSED
        pos.realized_pnl = total_pnl
        pos.unrealized_pnl = 0.0
        
        # Update portfolio
        self.state.available_capital += remaining_size + remaining_pnl
        self.state.total_allocated -= remaining_size
        self.state.total_realized_pnl += remaining_pnl
        
        # Move to closed positions
        self.state.closed_positions.append(pos)
        del self.state.positions[symbol]
        
        self._save_state()
        return True, total_pnl
    
    def _update_total_unrealized(self):
        """Recalculate total unrealized PnL"""
        self.state.total_unrealized_pnl = sum(
            p.unrealized_pnl for p in self.state.positions.values()
            if p.status in [PositionStatus.OPEN, PositionStatus.PARTIAL]
        )
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        open_positions = [
            p.to_dict() for p in self.state.positions.values()
            if p.status in [PositionStatus.OPEN, PositionStatus.PARTIAL]
        ]
        
        recent_closed = [
            p.to_dict() for p in self.state.closed_positions[-10:]  # Last 10
        ]
        
        winning_trades = sum(
            1 for p in self.state.closed_positions if p.realized_pnl > 0
        )
        total_closed = len(self.state.closed_positions)
        
        return {
            "initial_capital": self.state.initial_capital,
            "available_capital": self.state.available_capital,
            "total_allocated": self.state.total_allocated,
            "total_value": self.state.total_value,
            "total_return_pct": self.state.total_return_pct,
            "total_realized_pnl": self.state.total_realized_pnl,
            "total_unrealized_pnl": self.state.total_unrealized_pnl,
            "open_position_count": self.state.open_position_count,
            "max_positions": self.state.max_concurrent_positions,
            "win_rate": (winning_trades / total_closed * 100) if total_closed > 0 else 0,
            "total_trades": total_closed,
            "open_positions": open_positions,
            "recent_closed": recent_closed,
        }
    
    def print_portfolio(self):
        """Print portfolio status"""
        print("\n" + "="*70)
        print("PORTFOLIO STATUS")
        print("="*70)
        
        print(f"Initial Capital: ${self.state.initial_capital:.2f}")
        print(f"Available: ${self.state.available_capital:.2f}")
        print(f"Allocated: ${self.state.total_allocated:.2f}")
        print(f"Realized PnL: ${self.state.total_realized_pnl:+.2f}")
        print(f"Unrealized PnL: ${self.state.total_unrealized_pnl:+.2f}")
        print(f"Total Value: ${self.state.total_value:.2f} ({self.state.total_return_pct:+.2f}%)")
        print(f"Open Positions: {self.state.open_position_count}/{self.state.max_concurrent_positions}")
        
        if self.state.positions:
            print("\nOPEN POSITIONS:")
            for symbol, pos in self.state.positions.items():
                if pos.status in [PositionStatus.OPEN, PositionStatus.PARTIAL]:
                    print(f"  {symbol}: ${pos.size_usd:.2f} @ ${pos.entry_price:.6f} "
                          f"(PnL: ${pos.unrealized_pnl:+.2f})")
        
        print("="*70)
    
    def reset(self):
        """Reset portfolio state"""
        self.state = PortfolioState(
            initial_capital=self.initial_capital,
            available_capital=self.initial_capital
        )
        if self.state_file.exists():
            self.state_file.unlink()
        print("[INFO] Portfolio reset")
