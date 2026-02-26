"""Configuration for forex pairs"""

from .pairs import (
    PairConfig,
    USD_SGD,
    USD_MYR,
    get_pair_config,
    get_phase_1_pairs,
    get_phase_2_pairs,
    PORTFOLIO_CONFIG,
)

__all__ = [
    "PairConfig",
    "USD_SGD",
    "USD_MYR",
    "get_pair_config",
    "get_phase_1_pairs",
    "get_phase_2_pairs",
    "PORTFOLIO_CONFIG",
]
