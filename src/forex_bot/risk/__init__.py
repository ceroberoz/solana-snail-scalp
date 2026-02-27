"""Risk management module for forex trading bot

Contains:
- WeekendGapProtection: M3.2 - Close positions before weekend gaps
"""

from .weekend_protection import WeekendGapProtection, get_weekend_protection

__all__ = [
    "WeekendGapProtection",
    "get_weekend_protection",
]
