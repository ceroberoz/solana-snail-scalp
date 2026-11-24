"""A live exit is booked only after the sell confirms."""

import asyncio

import pytest

from snail_scalp.trader import CloseReason, Trade, TradeStatus, Trader


class _FakeRisk:
    def __init__(self):
        self.trades = []

    def record_trade(self, pnl):
        self.trades.append(pnl)


def _make_trader(tmp_path, swap_ok: bool) -> Trader:
    trader = Trader(
        strategy_config={"max_slippage_percent": 0.8},
        risk_manager=_FakeRisk(),
        simulate=False,
        results_file=str(tmp_path / "trades.json"),
    )
    trader._log_trade = lambda *args, **kwargs: None

    async def fake_swap_out(size_usd, price, side="long"):
        return swap_ok

    trader._live_swap_out = fake_swap_out
    trader.active_position = Trade(entry_price=1.0, size_usd=3.0, entry_time=0.0)
    return trader


def test_failed_live_close_keeps_position_open(tmp_path):
    trader = _make_trader(tmp_path, swap_ok=False)

    asyncio.run(trader._close_position(1.1, CloseReason.STOP_LOSS))

    assert trader.active_position is not None
    assert trader.active_position.status is TradeStatus.OPEN
    assert trader.trade_history == []
    assert trader.risk.trades == []


def test_confirmed_live_close_books_the_trade(tmp_path):
    trader = _make_trader(tmp_path, swap_ok=True)

    asyncio.run(trader._close_position(1.1, CloseReason.STOP_LOSS))

    assert trader.active_position is None
    assert trader.trade_history[0].status is TradeStatus.CLOSED
    assert trader.risk.trades == [pytest.approx(0.3)]


def test_failed_live_partial_close_leaves_position_untouched(tmp_path):
    trader = _make_trader(tmp_path, swap_ok=False)

    closed = asyncio.run(trader._partial_close(1.1, 0.5, CloseReason.TP1))

    assert closed is False
    assert trader.active_position.size_usd == pytest.approx(3.0)
    assert trader.active_position.status is TradeStatus.OPEN
    assert trader.risk.trades == []


def test_confirmed_live_partial_close_halves_the_position(tmp_path):
    trader = _make_trader(tmp_path, swap_ok=True)

    closed = asyncio.run(trader._partial_close(1.1, 0.5, CloseReason.TP1))

    assert closed is True
    assert trader.active_position.size_usd == pytest.approx(1.5)
    assert trader.active_position.status is TradeStatus.PARTIAL
    assert trader.risk.trades == [pytest.approx(0.15)]
