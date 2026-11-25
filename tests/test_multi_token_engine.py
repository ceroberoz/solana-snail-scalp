"""Tests for Multi-Token Portfolio & Live Execution Engine (US-6.4 Phase B)."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snail_scalp import cli
from snail_scalp.config import Stage, execution_config
from snail_scalp.portfolio_manager import (
    CloseReason,
    PortfolioManager,
    PositionStatus,
    TokenPosition,
)
from snail_scalp.screening_bot import ScreeningTradingBot
from snail_scalp.token_screener import RiskLevel


def test_token_position_carries_mint_decimals_signature():
    """Verify TokenPosition carries mint, decimals, and entry_signature."""
    pos = TokenPosition(
        symbol="BONK",
        address="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        mint="DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        decimals=5,
        entry_signature="5abcd...sig",
        entry_price=0.000025,
        size_usd=5.33,
        status=PositionStatus.OPEN,
    )
    assert pos.mint == "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    assert pos.decimals == 5
    assert pos.entry_signature == "5abcd...sig"

    d = pos.to_dict()
    assert d["mint"] == pos.mint
    assert d["decimals"] == 5
    assert d["entry_signature"] == "5abcd...sig"

    # Test round trip in PortfolioManager
    pm = PortfolioManager(initial_capital=20.0, state_file="data/.test_pos_roundtrip.json")
    try:
        restored = pm._dict_to_position(d)
        assert restored.mint == pos.mint
        assert restored.decimals == 5
        assert restored.entry_signature == "5abcd...sig"
    finally:
        if pm.state_file.exists():
            pm.state_file.unlink()


def test_portfolio_manager_equal_slot_sizing_and_reserve():
    """Verify 3 equal slots with 20% reserve on $20 initial capital."""
    state_file = "data/.test_pm_slots.json"
    pm = PortfolioManager(
        initial_capital=20.0,
        max_positions=3,
        reserve_pct=20.0,
        state_file=state_file,
    )
    try:
        # Initial: $20 capital, $4 reserve (20%), $16 deployable across 3 slots -> $5.33 per slot
        slot_size = pm.calculate_position_size("MINT_1")
        assert slot_size == 5.33

        # Open Slot 1
        opened1 = pm.open_position(
            symbol="COIN1",
            address="Addr111111111111111111111111111111111111111",
            entry_price=1.0,
            size_usd=slot_size,
            mint="Addr111111111111111111111111111111111111111",
            decimals=6,
            entry_signature="sig1",
        )
        assert opened1 is True
        assert pm.state.open_position_count == 1
        assert round(pm.state.available_capital, 2) == 14.67

        # Open Slot 2
        opened2 = pm.open_position(
            symbol="COIN2",
            address="Addr222222222222222222222222222222222222222",
            entry_price=2.0,
            size_usd=slot_size,
        )
        assert opened2 is True
        assert pm.state.open_position_count == 2
        assert round(pm.state.available_capital, 2) == 9.34

        # Open Slot 3
        opened3 = pm.open_position(
            symbol="COIN3",
            address="Addr333333333333333333333333333333333333333",
            entry_price=3.0,
            size_usd=slot_size,
        )
        assert opened3 is True
        assert pm.state.open_position_count == 3
        # Remaining capital is 4.01 >= 4.00 reserve
        assert pm.state.available_capital >= 4.00

        # Attempt to open 4th position -> rejected because max 3 concurrent positions
        opened4 = pm.open_position(
            symbol="COIN4",
            address="Addr444444444444444444444444444444444444444",
            entry_price=4.0,
            size_usd=1.0,
        )
        assert opened4 is False
        assert pm.state.open_position_count == 3

    finally:
        if Path(state_file).exists():
            Path(state_file).unlink()


def test_portfolio_manager_protects_reserve_from_large_allocation():
    """Verify capital cannot dip below the 20% reserve even if slot count < 3."""
    state_file = "data/.test_pm_reserve.json"
    pm = PortfolioManager(
        initial_capital=20.0,
        max_positions=3,
        reserve_pct=20.0,
        state_file=state_file,
    )
    try:
        # Reserve is $4.00. Available is $20.00.
        # An allocation of $17.00 would leave $3.00 < $4.00 reserve -> must be rejected
        assert pm.state.can_open_position(17.0) is False

        # Open $6.00 (within max allocation and leaves $14.00 > $4.00)
        assert pm.open_position("COIN1", "Addr1", 1.0, 6.0) is True
        # Open another $6.00 -> leaves $8.00 > $4.00
        assert pm.open_position("COIN2", "Addr2", 1.0, 6.0) is True

        # Now available is $8.00. Trying to allocate $5.00 would leave $3.00 < $4.00 reserve -> rejected
        assert pm.state.can_open_position(5.0) is False
        # But allocating $4.00 leaves exactly $4.00 -> allowed
        assert pm.state.can_open_position(4.0) is True

    finally:
        if Path(state_file).exists():
            Path(state_file).unlink()


def test_cli_multi_live_stage_refusal(monkeypatch, capsys):
    """Verify --multi --live without --stage live is rejected with exit code 1."""
    monkeypatch.setattr(sys, "argv", ["snail_scalp", "--multi", "--live"])
    assert cli.main() == 1
    out = capsys.readouterr().out
    assert "[STAGE REFUSAL]" in out
    assert "--stage live" in out


def test_cli_multi_live_confirmation_refusal(monkeypatch, capsys):
    """Verify --multi --live --stage live without confirmation is rejected with exit code 1."""
    monkeypatch.setattr(sys, "argv", ["snail_scalp", "--multi", "--live", "--stage", "live"])
    # mock input returning empty or wrong text
    monkeypatch.setattr("builtins.input", lambda prompt="": "NO")
    assert cli.main() == 1
    out = capsys.readouterr().out
    assert "[ABORTED] Live trading not confirmed" in out


def test_cli_multi_live_starts_with_confirm(monkeypatch):
    """Verify --multi --live --stage live --confirm-live starts live bot."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["snail_scalp", "--multi", "--live", "--stage", "live", "--confirm-live"],
    )

    mock_run = AsyncMock()
    with patch("snail_scalp.screening_bot.ScreeningTradingBot.run", mock_run):
        assert cli.main() == 0
        mock_run.assert_called_once()


def test_cli_multi_simulation_by_default(monkeypatch):
    """Verify --multi alone starts simulation mode."""
    monkeypatch.setattr(sys, "argv", ["snail_scalp", "--multi"])

    mock_run = AsyncMock()
    with patch("snail_scalp.screening_bot.ScreeningTradingBot.run", mock_run):
        assert cli.main() == 0
        mock_run.assert_called_once()


def test_screening_bot_dispatches_simulation_vs_live():
    """Verify ScreeningTradingBot.run() splits execution based on simulate flag."""
    bot_sim = ScreeningTradingBot(initial_capital=20.0, simulate=True)
    bot_sim.screen_tokens = MagicMock()
    bot_sim.print_banner = MagicMock()
    bot_sim._run_simulation_loop = AsyncMock()
    bot_sim._run_live_loop = AsyncMock()

    asyncio.run(bot_sim.run())
    bot_sim._run_simulation_loop.assert_called_once()
    bot_sim._run_live_loop.assert_not_called()

    bot_live = ScreeningTradingBot(initial_capital=20.0, simulate=False, stage=Stage.LIVE)
    bot_live.screen_tokens = MagicMock()
    bot_live.print_banner = MagicMock()
    bot_live._run_simulation_loop = AsyncMock()
    bot_live._run_live_loop = AsyncMock()

    asyncio.run(bot_live.run())
    bot_live._run_live_loop.assert_called_once()
    bot_live._run_simulation_loop.assert_not_called()
