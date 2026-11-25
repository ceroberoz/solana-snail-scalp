import asyncio
import json

import pytest

from snail_scalp.mint_safety import (
    SPL_TOKEN_PROGRAM,
    MintAuthority,
    MintSafetyError,
    fetch_mint_authorities,
)
from snail_scalp.token_screener import TokenScreener

MINT_A = "SafeMint111111111111111111111111111111111111"
MINT_B = "FrozenMint2222222222222222222222222222222222"
MINT_C = "Mintable3333333333333333333333333333333333"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    async def json(self):
        return self.body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append(json)
        return self.responses.pop(0)


def _mint_account(mint_authority=None, freeze_authority=None, owner=SPL_TOKEN_PROGRAM):
    return {
        "owner": owner,
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "mintAuthority": mint_authority,
                    "freezeAuthority": freeze_authority,
                    "decimals": 6,
                },
            }
        },
    }


def _rpc_body(values):
    return {"jsonrpc": "2.0", "id": 1, "result": {"value": values}}


def test_safe_mint_has_no_rejection_reason():
    record = MintAuthority(MINT_A, None, None, SPL_TOKEN_PROGRAM)
    assert record.rejection_reason() is None


def test_freeze_authority_is_rejected():
    record = MintAuthority(MINT_B, None, "FreezeAuth111", SPL_TOKEN_PROGRAM)
    assert record.rejection_reason() == "freeze authority active"


def test_mint_authority_is_rejected():
    record = MintAuthority(MINT_C, "MintAuth111", None, SPL_TOKEN_PROGRAM)
    assert record.rejection_reason() == "mint authority active"


def test_token_2022_owner_is_rejected():
    record = MintAuthority(MINT_A, None, None, TOKEN_2022_PROGRAM)
    assert "unsupported token program" in record.rejection_reason()


def test_fetch_parses_batch_and_skips_none_entries():
    body = _rpc_body([
        _mint_account(freeze_authority="FreezeA111"),
        None,
        _mint_account(mint_authority="MintC111"),
    ])
    session = FakeSession([FakeResponse(200, body)])

    records = asyncio.run(
        fetch_mint_authorities([MINT_A, MINT_B, MINT_C], rpc_url="http://rpc.test", session=session)
    )

    assert set(records) == {MINT_A, MINT_C}
    assert records[MINT_A].freeze_authority == "FreezeA111"
    assert records[MINT_C].mint_authority == "MintC111"
    assert records[MINT_C].mint == MINT_C
    assert records[MINT_A].program == SPL_TOKEN_PROGRAM


def test_json_rpc_error_raises_mint_safety_error():
    body = {"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "invalid params"}}
    session = FakeSession([FakeResponse(200, body)])

    with pytest.raises(MintSafetyError):
        asyncio.run(fetch_mint_authorities([MINT_A], rpc_url="http://rpc.test", session=session))


def test_http_429_raises_mint_safety_error():
    session = FakeSession([FakeResponse(429, {})])

    with pytest.raises(MintSafetyError):
        asyncio.run(fetch_mint_authorities([MINT_A], rpc_url="http://rpc.test", session=session))


def test_mints_are_chunked_at_one_hundred_accounts():
    mints = [f"Mint{index:04d}" for index in range(101)]
    session = FakeSession([
        FakeResponse(200, _rpc_body([None] * 100)),
        FakeResponse(200, _rpc_body([None])),
    ])

    asyncio.run(fetch_mint_authorities(mints, rpc_url="http://rpc.test", session=session))

    assert len(session.calls) == 2
    assert len(session.calls[0]["params"][0]) == 100
    assert len(session.calls[1]["params"][0]) == 1


def _pair(address, symbol, liquidity=50_000, volume=100_000):
    return {
        "chainId": "solana",
        "baseToken": {"address": address, "symbol": symbol, "name": symbol},
        "priceUsd": "0.001",
        "marketCap": 200_000,
        "volume": {"h24": volume},
        "liquidity": {"usd": liquidity},
        "priceChange": {"h1": 1.0, "h24": 5.0},
        "fdv": 200_000,
    }


def _fake_fetcher_class(pairs):
    class FakeFetcher:
        def __init__(self):
            self.pairs = pairs

        async def fetch_token_profiles(self):
            return []

        async def search_solana_pairs(self, query):
            return self.pairs

        async def get_tokens_batch(self, addresses):
            return self.pairs

    return FakeFetcher


def test_live_fetch_drops_freeze_active_token(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pairs = [_pair(MINT_A, "SAFE"), _pair(MINT_B, "FROZEN")]
    monkeypatch.setattr(
        "snail_scalp.real_data_fetcher.DexScreenerFetcher", _fake_fetcher_class(pairs)
    )

    async def fake_authorities(mints, rpc_url=None, session=None):
        return {
            MINT_A: MintAuthority(MINT_A, None, None, SPL_TOKEN_PROGRAM),
            MINT_B: MintAuthority(MINT_B, None, "FreezeB111", SPL_TOKEN_PROGRAM),
        }

    monkeypatch.setattr("snail_scalp.token_screener.fetch_mint_authorities", fake_authorities)

    tokens = asyncio.run(TokenScreener().fetch_live_tokens())

    assert [t.symbol for t in tokens] == ["SAFE"]
    cache = json.loads((tmp_path / "data" / "live_screened_tokens.json").read_text())
    assert [entry["symbol"] for entry in cache["tokens"]] == ["SAFE"]


def test_live_fetch_refuses_candidates_when_lookup_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pairs = [_pair(MINT_A, "SAFE")]
    monkeypatch.setattr(
        "snail_scalp.real_data_fetcher.DexScreenerFetcher", _fake_fetcher_class(pairs)
    )

    async def failing_authorities(mints, rpc_url=None, session=None):
        raise MintSafetyError("RPC returned HTTP 429")

    monkeypatch.setattr("snail_scalp.token_screener.fetch_mint_authorities", failing_authorities)

    screener = TokenScreener()
    tokens = asyncio.run(screener.fetch_live_tokens())

    assert tokens == []
    assert screener.tokens == []
    assert not (tmp_path / "data" / "live_screened_tokens.json").exists()
