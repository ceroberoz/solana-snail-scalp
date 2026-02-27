"""Trading session management for Asian market optimization (M3.1)

M3.1: Asian Session Trading
- Asian session: 00:00-09:00 UTC (higher position size)
- London session: 08:00-17:00 UTC
- NY session: 13:00-22:00 UTC
- London/NY overlap: 13:00-17:00 UTC (reduce size - high volatility)

Singapore is the forex hub for Asia Pacific:
- Asian session = most liquid for USD/SGD
- Local business hours overlap with Asian session
- MAS interventions often occur during Asian hours
"""

import logging
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class TradingSession(Enum):
    """Forex trading sessions (UTC)"""

    ASIAN = "asian"  # 00:00-09:00 UTC (Singapore/Tokyo active)
    LONDON = "london"  # 08:00-17:00 UTC (London active)
    NEW_YORK = "new_york"  # 13:00-22:00 UTC (New York active)
    OVERLAP = "overlap"  # 13:00-17:00 UTC (London + NY - volatile)


@dataclass
class SessionConfig:
    """Configuration for a trading session"""

    name: str
    start_time: time
    end_time: time
    position_multiplier: float  # Multiplier for position size
    description: str


# Default session configuration
DEFAULT_SESSIONS = {
    TradingSession.ASIAN: SessionConfig(
        name="Asian",
        start_time=time(0, 0),  # 00:00 UTC
        end_time=time(9, 0),  # 09:00 UTC
        position_multiplier=1.5,  # 1.5x size (highest liquidity for SGD)
        description="Singapore/Tokyo session - best for USD/SGD",
    ),
    TradingSession.LONDON: SessionConfig(
        name="London",
        start_time=time(8, 0),  # 08:00 UTC
        end_time=time(13, 0),  # 13:00 UTC (before NY overlap)
        position_multiplier=1.0,  # Normal size
        description="London session - moderate volatility",
    ),
    TradingSession.OVERLAP: SessionConfig(
        name="London/NY Overlap",
        start_time=time(13, 0),  # 13:00 UTC
        end_time=time(17, 0),  # 17:00 UTC
        position_multiplier=0.7,  # 0.7x size (high volatility)
        description="London/NY overlap - high volatility, reduce size",
    ),
    TradingSession.NEW_YORK: SessionConfig(
        name="New York",
        start_time=time(17, 0),  # 17:00 UTC (after overlap)
        end_time=time(22, 0),  # 22:00 UTC
        position_multiplier=0.8,  # 0.8x size (lower liquidity)
        description="NY session only - lower liquidity",
    ),
}


class SessionManager:
    """
    Manages trading sessions and position sizing adjustments

    Features:
    - Detect current trading session from UTC time
    - Calculate position size multipliers based on session
    - Filter trading hours for backtesting
    - Track session statistics
    """

    def __init__(self, sessions: Optional[dict] = None):
        """
        Initialize session manager

        Args:
            sessions: Optional custom session configuration (defaults to DEFAULT_SESSIONS)
        """
        self.sessions = sessions or DEFAULT_SESSIONS
        self.session_stats = {session: 0 for session in TradingSession}
        self.last_session: Optional[TradingSession] = None
        logger.info("SessionManager initialized with %d sessions", len(self.sessions))

    def get_current_session(self, current_time: datetime) -> TradingSession:
        """
        Get the current trading session

        Args:
            current_time: Current datetime (timezone-aware or UTC)

        Returns:
            TradingSession enum value
        """
        # Ensure we're working with timezone-naive UTC
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)

        current_time_only = current_time.time()

        # Check each session (in priority order - overlap before individual sessions)
        if self._is_time_in_range(current_time_only, time(13, 0), time(17, 0)):
            return TradingSession.OVERLAP
        elif self._is_time_in_range(current_time_only, time(0, 0), time(9, 0)):
            return TradingSession.ASIAN
        elif self._is_time_in_range(current_time_only, time(8, 0), time(13, 0)):
            return TradingSession.LONDON
        elif self._is_time_in_range(current_time_only, time(17, 0), time(22, 0)):
            return TradingSession.NEW_YORK
        else:
            # Outside defined sessions (22:00-00:00 UTC)
            # Treat as low liquidity - return ASIAN for next day continuity
            return TradingSession.ASIAN

    def _is_time_in_range(self, check_time: time, start: time, end: time) -> bool:
        """Check if a time falls within a range (handles midnight crossing)"""
        if start < end:
            return start <= check_time < end
        else:
            # Range crosses midnight (not used in current config but for completeness)
            return check_time >= start or check_time < end

    def get_position_multiplier(self, current_time: datetime) -> float:
        """
        Get position size multiplier for current session

        Args:
            current_time: Current datetime

        Returns:
            Multiplier value (e.g., 1.5 for 1.5x size)
        """
        session = self.get_current_session(current_time)
        config = self.sessions.get(session, DEFAULT_SESSIONS[TradingSession.ASIAN])

        # Track session stats
        self.session_stats[session] += 1
        if session != self.last_session:
            logger.info(
                f"Session changed to {config.name} ({config.position_multiplier}x multiplier)"
            )
            self.last_session = session

        return config.position_multiplier

    def adjust_position_size(
        self,
        base_size: float,
        current_time: datetime,
        min_multiplier: float = 0.5,
        max_multiplier: float = 2.0,
    ) -> float:
        """
        Adjust position size based on trading session

        Args:
            base_size: Base position size in lots
            current_time: Current datetime
            min_multiplier: Minimum allowed multiplier
            max_multiplier: Maximum allowed multiplier

        Returns:
            Adjusted position size
        """
        multiplier = self.get_position_multiplier(current_time)

        # Clamp multiplier to safe bounds
        multiplier = max(min_multiplier, min(max_multiplier, multiplier))

        adjusted_size = base_size * multiplier

        logger.debug(
            f"Position size adjusted: {base_size:.2f} -> {adjusted_size:.2f} "
            f"(multiplier: {multiplier:.1f}x)"
        )

        return adjusted_size

    def get_session_info(self, current_time: datetime) -> dict:
        """
        Get detailed information about current session

        Args:
            current_time: Current datetime

        Returns:
            Dictionary with session information
        """
        session = self.get_current_session(current_time)
        config = self.sessions.get(session, DEFAULT_SESSIONS[TradingSession.ASIAN])

        return {
            "session": session.value,
            "session_name": config.name,
            "start_time": config.start_time,
            "end_time": config.end_time,
            "position_multiplier": config.position_multiplier,
            "description": config.description,
            "current_time": current_time,
        }

    def is_asian_session(self, current_time: datetime) -> bool:
        """
        Check if currently in Asian session (for quick checks)

        Args:
            current_time: Current datetime

        Returns:
            True if in Asian session (00:00-09:00 UTC)
        """
        session = self.get_current_session(current_time)
        return session == TradingSession.ASIAN

    def is_high_volatility_period(self, current_time: datetime) -> bool:
        """
        Check if currently in high volatility period (overlap)

        Args:
            current_time: Current datetime

        Returns:
            True if in London/NY overlap (high volatility)
        """
        session = self.get_current_session(current_time)
        return session == TradingSession.OVERLAP

    def filter_dataframe_by_session(
        self, df: pd.DataFrame, allowed_sessions: Optional[list] = None
    ) -> pd.DataFrame:
        """
        Filter DataFrame to only include specific trading sessions

        Args:
            df: DataFrame with DatetimeIndex
            allowed_sessions: List of TradingSession to include (default: all)

        Returns:
            Filtered DataFrame
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame must have DatetimeIndex")

        if allowed_sessions is None:
            allowed_sessions = list(TradingSession)

        allowed_values = {s.value for s in allowed_sessions}

        def is_allowed_session(dt: datetime) -> bool:
            session = self.get_current_session(dt)
            return session.value in allowed_values

        mask = df.index.map(is_allowed_session)
        return df[mask].copy()

    def get_session_statistics(self) -> dict:
        """
        Get statistics about session usage

        Returns:
            Dictionary with session counts
        """
        total = sum(self.session_stats.values())
        if total == 0:
            return {session.value: 0 for session in TradingSession}

        return {
            session.value: {"count": count, "percentage": (count / total * 100) if total > 0 else 0}
            for session, count in self.session_stats.items()
        }

    def reset_statistics(self):
        """Reset session statistics"""
        self.session_stats = {session: 0 for session in TradingSession}
        self.last_session = None


def get_session_manager(sessions: Optional[dict] = None) -> SessionManager:
    """Factory function to create a SessionManager instance"""
    return SessionManager(sessions=sessions)


# Convenience function for quick session checks
def get_position_multiplier(current_time: datetime) -> float:
    """
    Quick function to get position multiplier without creating SessionManager

    Args:
        current_time: Current datetime

    Returns:
        Position multiplier for current session
    """
    manager = SessionManager()
    return manager.get_position_multiplier(current_time)
