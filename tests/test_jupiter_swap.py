import asyncio
import json
import os
import sys
import tempfile
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from snail_scalp.jupiter import JupiterClient, from_base_units, swap, to_base_units

USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
MEME = "MeMeToKeN111111111111111111111111111111111"


def test_usdt_to_meme_executes_with_quote_amounts():
    quote = {
        "inAmount": "2500000",
        "outAmount": "123456789012",
        "priceImpactPct": "0.42",
        "transaction": "unsigned-tx",
        "requestId": "req-usdt-meme",
    }
    execute_result = {"signature": "sig-usdt-meme"}
    with patch.object(JupiterClient, "get_quote", new_callable=AsyncMock, return_value=quote) as get_quote, \
         patch.object(JupiterClient, "execute", new_callable=AsyncMock, return_value=execute_result) as execute, \
         patch("snail_scalp.jupiter.load_keypair", return_value=object()), \
         patch("snail_scalp.jupiter.sign_transaction", return_value="signed-tx"):
        result = asyncio.run(swap(USDT, MEME, 1_000_000, taker="taker"))

    assert result["status"] == "executed"
    assert result["input_mint"] == USDT
    assert result["output_mint"] == MEME
    assert result["in_amount"] == 2_500_000
    assert result["out_amount"] == 123_456_789_012
    assert result["in_ui_amount"] == 2.5
    assert result["out_ui_amount"] == 123.456789012
    assert result["price_impact_pct"] == 0.42
    assert result["signature"] == "sig-usdt-meme"
    assert get_quote.await_args.args[2] == 1_000_000
    execute.assert_awaited_once_with("signed-tx", "req-usdt-meme")


def test_meme_to_usdt_executes_with_quote_amounts():
    quote = {
        "inAmount": "5000000000",
        "outAmount": "7500000",
        "priceImpactPct": "0.9",
        "transaction": "unsigned-tx-2",
        "requestId": "req-meme-usdt",
    }
    execute_result = {"signature": "sig-meme-usdt"}
    with patch.object(JupiterClient, "get_quote", new_callable=AsyncMock, return_value=quote), \
         patch.object(JupiterClient, "execute", new_callable=AsyncMock, return_value=execute_result) as execute, \
         patch("snail_scalp.jupiter.load_keypair", return_value=object()), \
         patch("snail_scalp.jupiter.sign_transaction", return_value="signed-tx-2"):
        result = asyncio.run(swap(
            MEME, USDT, 987_654_321,
            input_decimals=9, output_decimals=6, max_price_impact_pct=1.0,
        ))

    assert result["status"] == "executed"
    assert result["input_mint"] == MEME
    assert result["output_mint"] == USDT
    assert result["in_amount"] == 5_000_000_000
    assert result["out_amount"] == 7_500_000
    assert result["in_ui_amount"] == 5.0
    assert result["out_ui_amount"] == 7.5
    assert result["price_impact_pct"] == 0.9
    assert result["signature"] == "sig-meme-usdt"
    execute.assert_awaited_once()


def test_price_impact_above_cap_blocks_signing_and_execution():
    quote = {
        "inAmount": "2500000",
        "outAmount": "123456789012",
        "priceImpactPct": "2.75",
        "transaction": "unsigned-tx",
        "requestId": "req-impact",
    }
    with patch.object(JupiterClient, "get_quote", new_callable=AsyncMock, return_value=quote), \
         patch.object(JupiterClient, "execute", new_callable=AsyncMock) as execute, \
         patch("snail_scalp.jupiter.load_keypair", return_value=object()) as load_keypair, \
         patch("snail_scalp.jupiter.sign_transaction") as sign_transaction:
        result = asyncio.run(swap(USDT, MEME, 1_000_000))

    assert result["status"] == "price_impact_exceeded"
    assert result["price_impact_pct"] == 2.75
    assert result["quote"] == quote
    load_keypair.assert_not_called()
    sign_transaction.assert_not_called()
    execute.assert_not_called()


def test_non_numeric_price_impact_is_zero():
    quote = {
        "inAmount": "1000000",
        "outAmount": "2000000000",
        "priceImpactPct": "not-a-number",
        "transaction": "unsigned-tx",
        "requestId": "req-bad-impact",
    }
    with patch.object(JupiterClient, "get_quote", new_callable=AsyncMock, return_value=quote), \
         patch.object(JupiterClient, "execute", new_callable=AsyncMock, return_value={"signature": "sig-ok"}), \
         patch("snail_scalp.jupiter.load_keypair", return_value=object()), \
         patch("snail_scalp.jupiter.sign_transaction", return_value="signed-tx"):
        result = asyncio.run(swap(USDT, MEME, 1_000_000))

    assert result["status"] == "executed"
    assert result["price_impact_pct"] == 0.0


def test_ui_conversion_helpers_handle_6_and_9_decimals():
    assert to_base_units("1.234567", 6) == 1_234_567
    assert to_base_units(2.5, 6) == 2_500_000
    assert to_base_units(0.000000001, 9) == 1
    assert from_base_units(1_234_567, 6) == 1.234567
    assert from_base_units(2_500_000, 6) == 2.5
    assert from_base_units(123_456_789_012, 9) == 123.456789012


def test_pending_signature_returns_file_without_executing():
    quote = {
        "inAmount": "1000000",
        "outAmount": "2000000000",
        "priceImpactPct": "0.1",
        "transaction": "unsigned-tx",
        "requestId": "req-pending",
    }
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            os.chdir(tmpdir)
            with patch.object(JupiterClient, "get_quote", new_callable=AsyncMock, return_value=quote), \
                 patch.object(JupiterClient, "execute", new_callable=AsyncMock) as execute, \
                 patch("snail_scalp.jupiter.load_keypair", return_value=None), \
                 patch("snail_scalp.jupiter.sign_transaction") as sign_transaction:
                result = asyncio.run(swap(USDT, MEME, 777_777))
        finally:
            os.chdir(original_cwd)

        pending_path = os.path.join(tmpdir, "data", "pending_swap.json")
        assert os.path.exists(pending_path)
        with open(pending_path) as handle:
            pending = json.load(handle)

    assert result["status"] == "pending_signature"
    assert result["pending_file"] == "data/pending_swap.json"
    assert pending["amount"] == 777_777
    assert pending["transaction"] == "unsigned-tx"
    assert pending["quote"] == quote
    sign_transaction.assert_not_called()
    execute.assert_not_called()
