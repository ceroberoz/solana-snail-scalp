"""Tests for M3.1 Asian Session Trading

Tests the SessionManager class to ensure:
- Asian session is properly identified (00:00-09:00 UTC)
- Position multipliers are applied correctly
- London/NY overlap is detected
- Session statistics are tracked
"""

import pytest
from datetime import datetime, time
import sys

sys.path.insert(0, "/Users/psanjaya/Labs/solana-snail-scalp/src")

from forex_bot.risk.session_manager import (
    SessionManager,
    get_session_manager,
    get_position_multiplier,
    TradingSession,
    SessionConfig,
    DEFAULT_SESSIONS,
)


class TestSessionManager:
    """Test suite for SessionManager"""

    def test_initialization(self):
        """Test that SessionManager initializes correctly"""
        sm = SessionManager()
        assert sm.sessions == DEFAULT_SESSIONS
        assert sm.last_session is None
        assert all(count == 0 for count in sm.session_stats.values())

    def test_asian_session_00h(self):
        """Test Asian session at 00:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 0, 0, 0)  # 00:00 UTC
        assert sm.get_current_session(dt) == TradingSession.ASIAN

    def test_asian_session_06h(self):
        """Test Asian session at 06:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 6, 0, 0)  # 06:00 UTC
        assert sm.get_current_session(dt) == TradingSession.ASIAN

    def test_asian_session_0859(self):
        """Test Asian session at 08:59 UTC (edge case)"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 8, 59, 0)  # 08:59 UTC
        assert sm.get_current_session(dt) == TradingSession.ASIAN

    def test_london_session_09h(self):
        """Test London session at 09:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 9, 0, 0)  # 09:00 UTC
        assert sm.get_current_session(dt) == TradingSession.LONDON

    def test_london_session_12h(self):
        """Test London session at 12:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 12, 0, 0)  # 12:00 UTC
        assert sm.get_current_session(dt) == TradingSession.LONDON

    def test_london_session_1259(self):
        """Test London session at 12:59 UTC (edge case)"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 12, 59, 0)  # 12:59 UTC
        assert sm.get_current_session(dt) == TradingSession.LONDON

    def test_overlap_session_13h(self):
        """Test London/NY overlap at 13:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 13, 0, 0)  # 13:00 UTC
        assert sm.get_current_session(dt) == TradingSession.OVERLAP

    def test_overlap_session_15h(self):
        """Test London/NY overlap at 15:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 15, 0, 0)  # 15:00 UTC
        assert sm.get_current_session(dt) == TradingSession.OVERLAP

    def test_overlap_session_1659(self):
        """Test London/NY overlap at 16:59 UTC (edge case)"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 16, 59, 0)  # 16:59 UTC
        assert sm.get_current_session(dt) == TradingSession.OVERLAP

    def test_ny_session_17h(self):
        """Test NY session at 17:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 17, 0, 0)  # 17:00 UTC
        assert sm.get_current_session(dt) == TradingSession.NEW_YORK

    def test_ny_session_20h(self):
        """Test NY session at 20:00 UTC"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 20, 0, 0)  # 20:00 UTC
        assert sm.get_current_session(dt) == TradingSession.NEW_YORK

    def test_ny_session_2159(self):
        """Test NY session at 21:59 UTC (edge case)"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 21, 59, 0)  # 21:59 UTC
        assert sm.get_current_session(dt) == TradingSession.NEW_YORK

    def test_post_ny_session_22h(self):
        """Test time after NY session at 22:00 UTC (treated as Asian)"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 22, 0, 0)  # 22:00 UTC
        # Outside defined sessions, treated as Asian for next day continuity
        assert sm.get_current_session(dt) == TradingSession.ASIAN

    def test_post_ny_session_23h(self):
        """Test time at 23:00 UTC (treated as Asian)"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 23, 0, 0)  # 23:00 UTC
        assert sm.get_current_session(dt) == TradingSession.ASIAN

    def test_asian_session_multiplier(self):
        """Test Asian session position multiplier"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 6, 0, 0)  # Asian session
        multiplier = sm.get_position_multiplier(dt)
        assert multiplier == 1.5  # Asian session multiplier

    def test_london_session_multiplier(self):
        """Test London session position multiplier"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 10, 0, 0)  # London session
        multiplier = sm.get_position_multiplier(dt)
        assert multiplier == 1.0  # London session multiplier

    def test_overlap_session_multiplier(self):
        """Test overlap session position multiplier"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 15, 0, 0)  # Overlap session
        multiplier = sm.get_position_multiplier(dt)
        assert multiplier == 0.7  # Overlap session multiplier

    def test_ny_session_multiplier(self):
        """Test NY session position multiplier"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 19, 0, 0)  # NY session
        multiplier = sm.get_position_multiplier(dt)
        assert multiplier == 0.8  # NY session multiplier

    def test_adjust_position_size_asian(self):
        """Test position size adjustment in Asian session"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 6, 0, 0)  # Asian session
        base_size = 1.0  # 1 lot
        adjusted = sm.adjust_position_size(base_size, dt)
        expected = 1.0 * 1.5  # 1.5x multiplier
        assert abs(adjusted - expected) < 0.01

    def test_adjust_position_size_overlap(self):
        """Test position size adjustment in overlap session"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 15, 0, 0)  # Overlap session
        base_size = 1.0  # 1 lot
        adjusted = sm.adjust_position_size(base_size, dt)
        expected = 1.0 * 0.7  # 0.7x multiplier
        assert abs(adjusted - expected) < 0.01

    def test_adjust_position_size_with_clamping(self):
        """Test position size adjustment with min/max clamping"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 6, 0, 0)  # Asian session
        base_size = 1.0
        # Set limits that clamp the 1.5x multiplier
        adjusted = sm.adjust_position_size(base_size, dt, min_multiplier=0.8, max_multiplier=1.2)
        assert adjusted == 1.2  # Should be clamped to 1.2x

    def test_is_asian_session_true(self):
        """Test is_asian_session returns True in Asian session"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 6, 0, 0)
        assert sm.is_asian_session(dt) is True

    def test_is_asian_session_false(self):
        """Test is_asian_session returns False in London session"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 10, 0, 0)
        assert sm.is_asian_session(dt) is False

    def test_is_high_volatility_period_true(self):
        """Test is_high_volatility_period returns True in overlap"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 15, 0, 0)
        assert sm.is_high_volatility_period(dt) is True

    def test_is_high_volatility_period_false(self):
        """Test is_high_volatility_period returns False in Asian session"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 6, 0, 0)
        assert sm.is_high_volatility_period(dt) is False

    def test_get_session_info(self):
        """Test get_session_info returns correct dict"""
        sm = SessionManager()
        dt = datetime(2026, 2, 24, 6, 0, 0)
        info = sm.get_session_info(dt)

        assert "session" in info
        assert "session_name" in info
        assert "position_multiplier" in info
        assert info["session"] == "asian"
        assert info["position_multiplier"] == 1.5

    def test_session_statistics_tracking(self):
        """Test that session statistics are tracked"""
        sm = SessionManager()

        # Simulate trades in different sessions
        sm.get_position_multiplier(datetime(2026, 2, 24, 6, 0, 0))  # Asian
        sm.get_position_multiplier(datetime(2026, 2, 24, 10, 0, 0))  # London
        sm.get_position_multiplier(datetime(2026, 2, 24, 6, 0, 0))  # Asian again

        stats = sm.get_session_statistics()
        assert stats["asian"]["count"] == 2
        assert stats["london"]["count"] == 1
        assert abs(stats["asian"]["percentage"] - 66.67) < 0.01

    def test_reset_statistics(self):
        """Test that statistics can be reset"""
        sm = SessionManager()
        sm.get_position_multiplier(datetime(2026, 2, 24, 6, 0, 0))

        assert sm.session_stats[TradingSession.ASIAN] > 0
        sm.reset_statistics()
        assert all(count == 0 for count in sm.session_stats.values())

    def test_factory_function(self):
        """Test the get_session_manager factory function"""
        sm = get_session_manager()
        assert isinstance(sm, SessionManager)

    def test_convenience_function(self):
        """Test the get_position_multiplier convenience function"""
        dt = datetime(2026, 2, 24, 6, 0, 0)  # Asian session
        multiplier = get_position_multiplier(dt)
        assert multiplier == 1.5


class TestCustomSessions:
    """Test with custom session configurations"""

    def test_custom_session_config(self):
        """Test SessionManager with custom session config"""
        custom_sessions = {
            TradingSession.ASIAN: SessionConfig(
                name="Custom Asian",
                start_time=time(0, 0),
                end_time=time(9, 0),
                position_multiplier=2.0,  # Higher multiplier
                description="Custom config",
            ),
            TradingSession.LONDON: SessionConfig(
                name="Custom London",
                start_time=time(9, 0),
                end_time=time(17, 0),
                position_multiplier=1.0,
                description="Custom config",
            ),
        }

        sm = SessionManager(sessions=custom_sessions)
        dt = datetime(2026, 2, 24, 6, 0, 0)
        multiplier = sm.get_position_multiplier(dt)
        assert multiplier == 2.0  # Custom multiplier


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_exact_session_boundaries(self):
        """Test exact boundary times between sessions"""
        sm = SessionManager()

        # 09:00 UTC - Asian ends, London starts
        dt = datetime(2026, 2, 24, 9, 0, 0)
        session = sm.get_current_session(dt)
        assert session == TradingSession.LONDON

        # 13:00 UTC - London ends, Overlap starts
        dt = datetime(2026, 2, 24, 13, 0, 0)
        session = sm.get_current_session(dt)
        assert session == TradingSession.OVERLAP

        # 17:00 UTC - Overlap ends, NY starts
        dt = datetime(2026, 2, 24, 17, 0, 0)
        session = sm.get_current_session(dt)
        assert session == TradingSession.NEW_YORK

    def test_timezone_aware_datetime(self):
        """Test with timezone-aware datetime"""
        import pytz

        sm = SessionManager()

        utc = pytz.UTC
        dt = utc.localize(datetime(2026, 2, 24, 6, 0, 0))
        session = sm.get_current_session(dt)
        assert session == TradingSession.ASIAN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
