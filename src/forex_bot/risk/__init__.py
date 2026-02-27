"""Risk management module for forex trading bot

Contains:
- WeekendGapProtection: M3.2 - Close positions before weekend gaps
- SessionManager: M3.1 - Asian session position sizing
"""

from .weekend_protection import WeekendGapProtection, get_weekend_protection
from .session_manager import (
    SessionManager,
    get_session_manager,
    get_position_multiplier,
    TradingSession,
    SessionConfig,
)

__all__ = [
    "WeekendGapProtection",
    "get_weekend_protection",
    "SessionManager",
    "get_session_manager",
    "get_position_multiplier",
    "TradingSession",
    "SessionConfig",
]
