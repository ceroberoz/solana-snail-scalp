"""Mint Safety Checks for SPL Tokens

A token whose mint can still be inflated, or whose balances can be frozen,
must never reach the trade list. Authority lookups fail closed: when the RPC
call does not answer cleanly, the caller gets a MintSafetyError and drops the
whole candidate set instead of trading unchecked tokens.
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

import aiohttp

from snail_scalp.config import api_config

SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
MAX_ACCOUNTS_PER_CALL = 100
RPC_TIMEOUT_SECONDS = 15


class MintSafetyError(RuntimeError):
    """RPC lookup failed, so callers must fail closed."""


@dataclass
class MintAuthority:
    mint: str
    mint_authority: Optional[str]
    freeze_authority: Optional[str]
    program: str

    def rejection_reason(self) -> Optional[str]:
        """Return why this mint is unsafe to trade, or None when it is safe."""
        # Token-2022 mints stay out until their extensions are audited
        if self.program != SPL_TOKEN_PROGRAM:
            return f"unsupported token program {self.program or 'unknown'}"
        if self.freeze_authority:
            return "freeze authority active"
        if self.mint_authority:
            return "mint authority active"
        return None


def _chunks(items: List[str], size: int) -> Iterator[List[str]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def _parse_mint_account(mint: str, account: Dict) -> Optional[MintAuthority]:
    """Parse one jsonParsed account entry, or None when it is not a mint."""
    parsed = account.get("data", {}).get("parsed", {})
    if parsed.get("type") != "mint":
        return None
    info = parsed.get("info", {})
    return MintAuthority(
        mint=mint,
        mint_authority=info.get("mintAuthority"),
        freeze_authority=info.get("freezeAuthority"),
        program=account.get("owner", ""),
    )


async def _fetch_chunk(
    session: aiohttp.ClientSession,
    rpc_url: str,
    chunk: List[str],
) -> Dict[str, MintAuthority]:
    """Look up one batch of mints and return the parsed records."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getMultipleAccounts",
        "params": [chunk, {"encoding": "jsonParsed", "commitment": "confirmed"}],
    }

    try:
        async with session.post(
            rpc_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=RPC_TIMEOUT_SECONDS),
        ) as response:
            if response.status != 200:
                raise MintSafetyError(f"RPC returned HTTP {response.status}")
            body = await response.json()
    except aiohttp.ClientError as e:
        raise MintSafetyError(f"RPC request failed: {e}") from e
    except asyncio.TimeoutError as e:
        raise MintSafetyError(
            f"RPC request timed out after {RPC_TIMEOUT_SECONDS}s: {e}"
        ) from e
    except ValueError as e:
        raise MintSafetyError(f"RPC returned invalid JSON: {e}") from e

    if body.get("error"):
        raise MintSafetyError(f"RPC error: {body['error']}")

    values = (body.get("result") or {}).get("value") or []
    authorities: Dict[str, MintAuthority] = {}
    for mint, account in zip(chunk, values):
        if account is None:
            continue
        record = _parse_mint_account(mint, account)
        if record is not None:
            authorities[mint] = record
    return authorities


async def fetch_mint_authorities(
    mints: List[str],
    rpc_url: Optional[str] = None,
    session: Optional[aiohttp.ClientSession] = None,
) -> Dict[str, MintAuthority]:
    """Fetch mint and freeze authorities for each mint.

    Returns only mints the RPC parsed as SPL mints, so a missing key means
    "not found" and the caller treats it as unsafe.
    """
    unique_mints = list(dict.fromkeys(mints))
    if not unique_mints:
        return {}

    url = rpc_url or api_config.rpc
    owned_session = session is None
    if owned_session:
        session = aiohttp.ClientSession()

    authorities: Dict[str, MintAuthority] = {}
    try:
        for chunk in _chunks(unique_mints, MAX_ACCOUNTS_PER_CALL):
            authorities.update(await _fetch_chunk(session, url, chunk))
    finally:
        if owned_session:
            await session.close()
    return authorities
