"""Weekend gap protection for forex trading

M3.2: Weekend Gap Protection
- Close all positions Friday 20:00 UTC
- No new entries after Friday 18:00 UTC
- Resume Sunday 22:00 UTC

Forex weekend schedule:
- Friday close: 22:00 UTC (NY close)
- Sunday open: 22:00 UTC (Sydney open)

We close early (20:00 UTC) and resume late (22:00 UTC) to avoid:
1. Low liquidity period before NY close
2. Weekend gap risk from geopolitical events
3. Thin Sunday markets with wide spreads
"""

import logging
from datetime import datetime, time, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class WeekendGapProtection:
    """
    Protects against weekend gap risk in forex trading.

    Key principles:
    - Forex markets close Friday 22:00 UTC (NY close)
    - Forex markets reopen Sunday 22:00 UTC (Sydney open)
    - We close positions 2 hours early (20:00 UTC) for safety
    - We stop new entries 4 hours before close (18:00 UTC)
    - We resume trading at Sunday 22:00 UTC when liquidity returns
    """

    # Trading schedule (UTC)
    FRIDAY_ENTRY_CUTOFF = time(18, 0)  # No new entries after Friday 18:00 UTC
    FRIDAY_POSITION_CLOSE = time(20, 0)  # Close positions Friday 20:00 UTC
    SUNDAY_TRADING_RESUME = time(22, 0)  # Resume trading Sunday 22:00 UTC

    # Market official times (for reference)
    MARKET_FRIDAY_CLOSE = time(22, 0)  # Official NY close
    MARKET_SUNDAY_OPEN = time(22, 0)  # Official Sydney open

    def __init__(self):
        """Initialize weekend protection module"""
        self.closed_due_to_weekend: bool = False
        self.last_weekend_check: Optional[datetime] = None
        logger.info("WeekendGapProtection initialized")

    def is_trading_allowed(self, current_time: datetime) -> bool:
        """
        Check if trading is currently allowed (not during weekend)

        Args:
            current_time: Current datetime (timezone-aware or UTC)

        Returns:
            True if trading is allowed, False if weekend gap protection is active
        """
        # Ensure we're working with timezone-naive UTC
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)

        weekday = current_time.weekday()  # Monday=0, Sunday=6
        current_time_only = current_time.time()

        # Friday: No trading after 20:00 UTC
        if weekday == 4:  # Friday
            if current_time_only >= self.FRIDAY_POSITION_CLOSE:
                if not self.closed_due_to_weekend:
                    logger.info(
                        f"Weekend protection: Trading closed at {current_time} (Friday {self.FRIDAY_POSITION_CLOSE})"
                    )
                    self.closed_due_to_weekend = True
                return False

        # Saturday: No trading
        if weekday == 5:  # Saturday
            if not self.closed_due_to_weekend:
                logger.info(f"Weekend protection: Trading closed at {current_time} (Saturday)")
                self.closed_due_to_weekend = True
            return False

        # Sunday: No trading before 22:00 UTC
        if weekday == 6:  # Sunday
            if current_time_only < self.SUNDAY_TRADING_RESUME:
                if not self.closed_due_to_weekend:
                    logger.info(
                        f"Weekend protection: Trading closed at {current_time} (Sunday before {self.SUNDAY_TRADING_RESUME})"
                    )
                    self.closed_due_to_weekend = True
                return False

        # Trading is allowed - reset flag if needed
        if self.closed_due_to_weekend:
            logger.info(f"Weekend protection: Trading resumed at {current_time}")
            self.closed_due_to_weekend = False

        self.last_weekend_check = current_time
        return True

    def is_entry_allowed(self, current_time: datetime) -> bool:
        """
        Check if new position entries are allowed

        More restrictive than is_trading_allowed - stops entries earlier
        to avoid holding through weekend.

        Args:
            current_time: Current datetime (timezone-aware or UTC)

        Returns:
            True if new entries are allowed, False otherwise
        """
        # Ensure we're working with timezone-naive UTC
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)

        weekday = current_time.weekday()
        current_time_only = current_time.time()

        # First check if trading is allowed at all
        if not self.is_trading_allowed(current_time):
            return False

        # Friday: No new entries after 18:00 UTC
        if weekday == 4:  # Friday
            if current_time_only >= self.FRIDAY_ENTRY_CUTOFF:
                return False

        return True

    def should_close_positions(self, current_time: datetime) -> bool:
        """
        Check if all positions should be closed due to weekend

        Args:
            current_time: Current datetime (timezone-aware or UTC)

        Returns:
            True if positions should be closed now
        """
        # Ensure we're working with timezone-naive UTC
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)

        weekday = current_time.weekday()
        current_time_only = current_time.time()

        # Friday: Close positions at 20:00 UTC
        if weekday == 4:  # Friday
            # Check if we're in the close window (20:00 - 20:59)
            if self.FRIDAY_POSITION_CLOSE <= current_time_only < time(21, 0):
                return True

        return False

    def get_time_until_trading_resumes(self, current_time: datetime) -> Optional[timedelta]:
        """
        Get time remaining until trading resumes

        Args:
            current_time: Current datetime (timezone-aware or UTC)

        Returns:
            Timedelta until trading resumes, or None if trading is currently allowed
        """
        # Ensure we're working with timezone-naive UTC
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)

        if self.is_trading_allowed(current_time):
            return None

        weekday = current_time.weekday()

        # Calculate next Sunday 22:00 UTC
        if weekday == 4:  # Friday
            days_until_sunday = 2
        elif weekday == 5:  # Saturday
            days_until_sunday = 1
        elif weekday == 6:  # Sunday
            days_until_sunday = 0
        else:
            # Shouldn't reach here if trading is closed
            return None

        next_sunday = current_time.date() + timedelta(days=days_until_sunday)
        resume_time = datetime.combine(next_sunday, self.SUNDAY_TRADING_RESUME)

        return resume_time - current_time

    def get_weekend_status(self, current_time: datetime) -> dict:
        """
        Get detailed weekend protection status

        Args:
            current_time: Current datetime (timezone-aware or UTC)

        Returns:
            Dictionary with status information
        """
        # Ensure we're working with timezone-naive UTC
        if current_time.tzinfo is not None:
            current_time = current_time.replace(tzinfo=None)

        is_trading = self.is_trading_allowed(current_time)
        is_entry = self.is_entry_allowed(current_time)
        should_close = self.should_close_positions(current_time)
        time_until = self.get_time_until_trading_resumes(current_time)

        return {
            "trading_allowed": is_trading,
            "entry_allowed": is_entry,
            "should_close_positions": should_close,
            "time_until_resume": time_until,
            "current_time_utc": current_time,
            "friday_entry_cutoff": self.FRIDAY_ENTRY_CUTOFF,
            "friday_position_close": self.FRIDAY_POSITION_CLOSE,
            "sunday_trading_resume": self.SUNDAY_TRADING_RESUME,
        }

    def filter_dataframe_for_trading_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter a DataFrame to only include trading hours (excludes weekend gap period)

        Args:
            df: DataFrame with DatetimeIndex

        Returns:
            Filtered DataFrame excluding weekend gap period
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame must have DatetimeIndex")

        def is_trading_time(dt: datetime) -> bool:
            """Check if datetime is within trading hours"""
            weekday = dt.weekday()
            time_only = dt.time()

            # Friday after 20:00 UTC - closed
            if weekday == 4 and time_only >= self.FRIDAY_POSITION_CLOSE:
                return False

            # Saturday - closed
            if weekday == 5:
                return False

            # Sunday before 22:00 UTC - closed
            if weekday == 6 and time_only < self.SUNDAY_TRADING_RESUME:
                return False

            return True

        mask = df.index.map(is_trading_time)
        return df[mask].copy()


def get_weekend_protection() -> WeekendGapProtection:
    """Factory function to get weekend protection instance"""
    return WeekendGapProtection()
