"""Tests for M3.2 Weekend Gap Protection

Tests the WeekendGapProtection class to ensure:
- Positions are closed Friday 20:00 UTC
- No new entries after Friday 18:00 UTC
- Trading resumes Sunday 22:00 UTC
"""

import pytest
from datetime import datetime, time, timedelta
import pandas as pd
import numpy as np

import sys

sys.path.insert(0, "/Users/psanjaya/Labs/solana-snail-scalp/src")

from forex_bot.risk.weekend_protection import WeekendGapProtection, get_weekend_protection


class TestWeekendGapProtection:
    """Test suite for WeekendGapProtection"""

    def test_initialization(self):
        """Test that WeekendGapProtection initializes correctly"""
        wp = WeekendGapProtection()
        assert wp.closed_due_to_weekend is False
        assert wp.last_weekend_check is None

    def test_monday_trading_allowed(self):
        """Test that trading is allowed on Monday"""
        wp = WeekendGapProtection()
        monday = datetime(2026, 2, 23, 12, 0, 0)  # Monday 12:00 UTC
        assert wp.is_trading_allowed(monday) is True
        assert wp.is_entry_allowed(monday) is True

    def test_wednesday_trading_allowed(self):
        """Test that trading is allowed on Wednesday"""
        wp = WeekendGapProtection()
        wednesday = datetime(2026, 2, 25, 14, 30, 0)  # Wednesday 14:30 UTC
        assert wp.is_trading_allowed(wednesday) is True
        assert wp.is_entry_allowed(wednesday) is True

    def test_friday_morning_trading_allowed(self):
        """Test that trading is allowed Friday morning"""
        wp = WeekendGapProtection()
        friday_morning = datetime(2026, 2, 27, 10, 0, 0)  # Friday 10:00 UTC
        assert wp.is_trading_allowed(friday_morning) is True
        assert wp.is_entry_allowed(friday_morning) is True

    def test_friday_evening_entry_blocked_after_18h(self):
        """Test that new entries are blocked after Friday 18:00 UTC"""
        wp = WeekendGapProtection()
        friday_18h = datetime(2026, 2, 27, 18, 0, 0)  # Friday 18:00 UTC
        assert wp.is_trading_allowed(friday_18h) is True  # Trading still allowed
        assert wp.is_entry_allowed(friday_18h) is False  # But no new entries

    def test_friday_evening_trading_blocked_after_20h(self):
        """Test that trading is blocked after Friday 20:00 UTC"""
        wp = WeekendGapProtection()
        friday_20h = datetime(2026, 2, 27, 20, 0, 0)  # Friday 20:00 UTC
        assert wp.is_trading_allowed(friday_20h) is False
        assert wp.is_entry_allowed(friday_20h) is False

    def test_friday_night_trading_blocked(self):
        """Test that trading is blocked Friday night"""
        wp = WeekendGapProtection()
        friday_night = datetime(2026, 2, 27, 22, 0, 0)  # Friday 22:00 UTC
        assert wp.is_trading_allowed(friday_night) is False
        assert wp.is_entry_allowed(friday_night) is False

    def test_saturday_trading_blocked(self):
        """Test that trading is blocked all day Saturday"""
        wp = WeekendGapProtection()
        saturday_morning = datetime(2026, 2, 28, 8, 0, 0)  # Saturday 08:00 UTC
        saturday_night = datetime(2026, 2, 28, 20, 0, 0)  # Saturday 20:00 UTC

        assert wp.is_trading_allowed(saturday_morning) is False
        assert wp.is_trading_allowed(saturday_night) is False

    def test_sunday_morning_trading_blocked(self):
        """Test that trading is blocked Sunday before 22:00 UTC"""
        wp = WeekendGapProtection()
        sunday_afternoon = datetime(2026, 3, 1, 14, 0, 0)  # Sunday 14:00 UTC
        assert wp.is_trading_allowed(sunday_afternoon) is False

    def test_sunday_evening_trading_resumes_at_22h(self):
        """Test that trading resumes Sunday at 22:00 UTC"""
        wp = WeekendGapProtection()
        # First mark as closed
        sunday_afternoon = datetime(2026, 3, 1, 14, 0, 0)
        wp.is_trading_allowed(sunday_afternoon)
        assert wp.closed_due_to_weekend is True

        # Then check it resumes at 22:00
        sunday_22h = datetime(2026, 3, 1, 22, 0, 0)  # Sunday 22:00 UTC
        assert wp.is_trading_allowed(sunday_22h) is True
        assert wp.closed_due_to_weekend is False

    def test_sunday_night_trading_allowed(self):
        """Test that trading is allowed Sunday night after 22:00"""
        wp = WeekendGapProtection()
        sunday_night = datetime(2026, 3, 1, 23, 0, 0)  # Sunday 23:00 UTC
        assert wp.is_trading_allowed(sunday_night) is True

    def test_should_close_positions_friday_20h(self):
        """Test that positions should close at Friday 20:00 UTC"""
        wp = WeekendGapProtection()
        friday_20h = datetime(2026, 2, 27, 20, 0, 0)  # Friday 20:00 UTC
        assert wp.should_close_positions(friday_20h) is True

    def test_should_close_positions_friday_20h30(self):
        """Test that positions should close at Friday 20:30 UTC"""
        wp = WeekendGapProtection()
        friday_2030 = datetime(2026, 2, 27, 20, 30, 0)  # Friday 20:30 UTC
        assert wp.should_close_positions(friday_2030) is True

    def test_should_not_close_positions_friday_19h(self):
        """Test that positions should NOT close at Friday 19:00 UTC"""
        wp = WeekendGapProtection()
        friday_19h = datetime(2026, 2, 27, 19, 0, 0)  # Friday 19:00 UTC
        assert wp.should_close_positions(friday_19h) is False

    def test_should_not_close_positions_saturday(self):
        """Test that should_close_positions is False on Saturday (already closed)"""
        wp = WeekendGapProtection()
        saturday = datetime(2026, 2, 28, 12, 0, 0)  # Saturday 12:00 UTC
        assert wp.should_close_positions(saturday) is False

    def test_should_not_close_positions_monday(self):
        """Test that positions should NOT close on Monday"""
        wp = WeekendGapProtection()
        monday = datetime(2026, 2, 23, 12, 0, 0)  # Monday 12:00 UTC
        assert wp.should_close_positions(monday) is False

    def test_get_time_until_resume_friday_night(self):
        """Test time until trading resumes from Friday night"""
        wp = WeekendGapProtection()
        friday_20h = datetime(2026, 2, 27, 20, 0, 0)  # Friday 20:00 UTC
        time_until = wp.get_time_until_trading_resumes(friday_20h)

        # Should resume Sunday 22:00 UTC = ~50 hours later
        assert time_until is not None
        assert time_until.total_seconds() > 0

        # Check it's approximately 50 hours (Friday 20:00 to Sunday 22:00)
        expected_hours = 50
        actual_hours = time_until.total_seconds() / 3600
        assert abs(actual_hours - expected_hours) < 0.1  # Allow small tolerance

    def test_get_time_until_resume_saturday(self):
        """Test time until trading resumes from Saturday"""
        wp = WeekendGapProtection()
        saturday = datetime(2026, 2, 28, 12, 0, 0)  # Saturday 12:00 UTC
        time_until = wp.get_time_until_trading_resumes(saturday)

        assert time_until is not None
        # Should be approximately 34 hours (Saturday 12:00 to Sunday 22:00)
        expected_hours = 34
        actual_hours = time_until.total_seconds() / 3600
        assert abs(actual_hours - expected_hours) < 0.1

    def test_get_time_until_resume_sunday_morning(self):
        """Test time until trading resumes from Sunday morning"""
        wp = WeekendGapProtection()
        sunday_morning = datetime(2026, 3, 1, 8, 0, 0)  # Sunday 08:00 UTC
        time_until = wp.get_time_until_trading_resumes(sunday_morning)

        assert time_until is not None
        # Should be 14 hours (Sunday 08:00 to 22:00)
        expected_hours = 14
        actual_hours = time_until.total_seconds() / 3600
        assert abs(actual_hours - expected_hours) < 0.1

    def test_get_time_until_resume_returns_none_when_trading_allowed(self):
        """Test that get_time_until_resume returns None when trading is allowed"""
        wp = WeekendGapProtection()
        monday = datetime(2026, 2, 23, 12, 0, 0)  # Monday 12:00 UTC
        assert wp.get_time_until_trading_resumes(monday) is None

    def test_get_weekend_status(self):
        """Test that get_weekend_status returns correct status dict"""
        wp = WeekendGapProtection()
        friday_19h = datetime(2026, 2, 27, 19, 0, 0)  # Friday 19:00 UTC
        status = wp.get_weekend_status(friday_19h)

        assert "trading_allowed" in status
        assert "entry_allowed" in status
        assert "should_close_positions" in status
        assert "time_until_resume" in status
        assert "current_time_utc" in status
        assert status["trading_allowed"] is True
        assert status["entry_allowed"] is False  # After 18:00 Friday

    def test_factory_function(self):
        """Test the get_weekend_protection factory function"""
        wp = get_weekend_protection()
        assert isinstance(wp, WeekendGapProtection)

    def test_filter_dataframe_for_trading_hours(self):
        """Test filtering DataFrame to remove weekend data"""
        wp = WeekendGapProtection()

        # Create DataFrame with hourly data spanning Friday evening to Monday morning
        dates = []
        friday_18h = datetime(2026, 2, 27, 18, 0, 0)

        # Generate 72 hours of data (Friday 18:00 to Monday 18:00)
        for i in range(72):
            dates.append(friday_18h + timedelta(hours=i))

        df = pd.DataFrame(
            {
                "Open": np.random.randn(72),
                "High": np.random.randn(72),
                "Low": np.random.randn(72),
                "Close": np.random.randn(72),
                "Volume": np.random.randint(1000, 10000, 72),
            },
            index=pd.DatetimeIndex(dates),
        )

        # Filter
        filtered = wp.filter_dataframe_for_trading_hours(df)

        # Should have removed Friday 20:00 onwards and Sunday before 22:00
        assert len(filtered) < len(df)

        # Check that Friday 19:00 is still there
        friday_19h = datetime(2026, 2, 27, 19, 0, 0)
        assert friday_19h in filtered.index

        # Check that Friday 20:00 is removed
        friday_20h = datetime(2026, 2, 27, 20, 0, 0)
        assert friday_20h not in filtered.index

        # Check that Sunday 21:00 is removed
        sunday_21h = datetime(2026, 3, 1, 21, 0, 0)
        assert sunday_21h not in filtered.index

        # Check that Sunday 22:00 is present
        sunday_22h = datetime(2026, 3, 1, 22, 0, 0)
        assert sunday_22h in filtered.index

    def test_timezone_aware_datetime(self):
        """Test that timezone-aware datetimes are handled correctly"""
        import pytz

        wp = WeekendGapProtection()

        # Create timezone-aware datetime (UTC)
        utc = pytz.UTC
        friday_20h_utc = utc.localize(datetime(2026, 2, 27, 20, 0, 0))

        # Should work without error
        assert wp.is_trading_allowed(friday_20h_utc) is False


class TestWeekendProtectionEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_exact_friday_18h_boundary(self):
        """Test exact Friday 18:00 boundary for entries"""
        wp = WeekendGapProtection()
        friday_18h = datetime(2026, 2, 27, 18, 0, 0)
        assert wp.is_entry_allowed(friday_18h) is False  # Cutoff is AT 18:00

    def test_exact_friday_17h59_allowed(self):
        """Test Friday 17:59 is still allowed for entries"""
        wp = WeekendGapProtection()
        friday_1759 = datetime(2026, 2, 27, 17, 59, 0)
        assert wp.is_entry_allowed(friday_1759) is True

    def test_exact_friday_20h_boundary(self):
        """Test exact Friday 20:00 boundary for positions"""
        wp = WeekendGapProtection()
        friday_20h = datetime(2026, 2, 27, 20, 0, 0)
        assert wp.should_close_positions(friday_20h) is True

    def test_exact_sunday_22h_boundary(self):
        """Test exact Sunday 22:00 boundary for resuming trading"""
        wp = WeekendGapProtection()
        sunday_22h = datetime(2026, 3, 1, 22, 0, 0)
        assert wp.is_trading_allowed(sunday_22h) is True

    def test_exact_sunday_2159_blocked(self):
        """Test Sunday 21:59 is still blocked"""
        wp = WeekendGapProtection()
        sunday_2159 = datetime(2026, 3, 1, 21, 59, 0)
        assert wp.is_trading_allowed(sunday_2159) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
