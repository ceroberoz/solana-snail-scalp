"""CLI exit-code contract."""

import sys

import pytest

from snail_scalp import cli


def test_multi_live_refusal_returns_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["snail_scalp", "--multi", "--live"])

    assert cli.main() == 1
    assert "Multi-token live trading is not implemented" in capsys.readouterr().out


def test_help_exits_zero(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["snail_scalp", "--help"])

    with pytest.raises(SystemExit) as exc:
        cli.main()

    assert exc.value.code == 0
