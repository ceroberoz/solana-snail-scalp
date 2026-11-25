"""Execution policy config: defaults, profile overrides, and enforced bounds."""

import pytest

from snail_scalp.config import (
    ExecutionConfig,
    Stage,
    apply_profile,
    execution_config,
)


@pytest.fixture(autouse=True)
def clean_profile():
    """Reset global config before and after each test so state does not leak."""
    apply_profile("default")
    execution_config.stage = Stage.PAPER
    yield
    apply_profile("default")
    execution_config.stage = Stage.PAPER


def test_defaults():
    config = ExecutionConfig()
    assert config.slots == 3
    assert config.reserve_pct == 20.0
    assert config.slippage_pct == 1.2
    assert config.exit_poll_seconds == 4.0
    assert config.stage is Stage.PAPER
    assert config.priority_fee_enabled is False


@pytest.mark.parametrize("profile", ["balanced", "aggressive"])
def test_profiles_stay_within_bounds(profile):
    apply_profile(profile)
    assert 1.2 <= execution_config.slippage_pct <= 1.5
    assert 3 <= execution_config.exit_poll_seconds <= 5
    assert execution_config.slots == 3
    assert execution_config.reserve_pct == 20.0
    assert execution_config.stage is Stage.PAPER


def test_default_profile_restores_defaults():
    apply_profile("aggressive")
    apply_profile("default")
    assert execution_config.slots == 3
    assert execution_config.reserve_pct == 20.0
    assert execution_config.slippage_pct == 1.2
    assert execution_config.exit_poll_seconds == 4.0
    assert execution_config.stage is Stage.PAPER
    assert execution_config.priority_fee_enabled is False


def test_profiles_never_change_stage():
    execution_config.stage = Stage.LIVE
    for profile in ("default", "balanced", "aggressive"):
        apply_profile(profile)
        assert execution_config.stage is Stage.LIVE


@pytest.mark.parametrize(
    "overrides",
    [
        {"slots": 0},
        {"reserve_pct": 100},
        {"slippage_pct": 0},
        {"exit_poll_seconds": 0.1},
    ],
)
def test_out_of_bounds_rejected(overrides):
    with pytest.raises(ValueError):
        ExecutionConfig(**overrides)


def test_stage_accepts_string():
    assert ExecutionConfig(stage="live").stage is Stage.LIVE


def test_stage_rejects_unknown_value():
    with pytest.raises(ValueError):
        ExecutionConfig(stage="bogus")
