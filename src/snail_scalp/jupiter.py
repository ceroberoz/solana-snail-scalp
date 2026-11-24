"""Jupiter Swap integration for live trading (Solana).

Follows Jupiter Swap API v2:
  - GET  https://api.jup.ag/swap/v2/order   (quote + transaction)
  - POST https://api.jup.ag/swap/v2/execute (land signed tx)

Signing requires the optional `solders` package. If it is not installed, the
unsigned transaction is written to `data/pending_swap.json` for external signing.
"""

import aiohttp
import base64
import json
import math
import os
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, TypedDict

from snail_scalp.config import api_config


class SwapResult(TypedDict, total=False):
    """Result of a swap attempt. Amounts are base units unless suffixed ``_ui``."""

    status: str
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    in_ui_amount: float
    out_ui_amount: float
    price_impact_pct: float
    signature: str
    pending_file: str
    quote: Dict[str, Any]
    error: str
    result: Dict[str, Any]


class JupiterClient:
    """Minimal Jupiter v2 swap client."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("JUPITER_API_KEY")
        self.base_url = "https://api.jup.ag/swap/v2"

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    async def get_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        taker: Optional[str] = None,
        slippage_bps: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Fetch a quote (+ transaction if taker provided)."""
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
        }
        if taker:
            params["taker"] = taker
        if slippage_bps is not None:
            params["slippageBps"] = str(slippage_bps)

        url = f"{self.base_url}/order"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Jupiter quote failed: {resp.status} {text}")
                return await resp.json()

    async def execute(self, signed_transaction_b64: str, request_id: str) -> Dict[str, Any]:
        """Land a signed transaction via Jupiter /execute."""
        url = f"{self.base_url}/execute"
        payload = {
            "signedTransaction": signed_transaction_b64,
            "requestId": request_id,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=self._headers(), timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Jupiter execute failed: {resp.status} {text}")
                return await resp.json()


def load_keypair():
    """Load a Solana keypair from env/file. Returns solders Keypair or None."""
    try:
        from solders.keypair import Keypair
    except Exception:
        return None

    # Env var: base58 private key
    pk = os.getenv("SOLANA_PRIVATE_KEY")
    if pk:
        try:
            import base58
            return Keypair.from_bytes(base58.b58decode(pk))
        except Exception:
            try:
                # maybe JSON array
                arr = json.loads(pk)
                return Keypair.from_bytes(bytes(arr))
            except Exception:
                pass

    # File path
    path = os.getenv("SOLANA_KEYPAIR_PATH")
    if path and Path(path).exists():
        try:
            data = json.loads(Path(path).read_text())
            return Keypair.from_bytes(bytes(data))
        except Exception:
            pass
    return None


def sign_transaction(tx_b64: str, keypair) -> Optional[str]:
    """Sign a base64 transaction with the given keypair. Returns base64 signed tx or None."""
    if keypair is None:
        return None
    try:
        from solders.transaction import VersionedTransaction
        from solders.message import to_bytes_versioned
        import base64 as b64
        tx_bytes = b64.b64decode(tx_b64)
        tx = VersionedTransaction.from_bytes(tx_bytes)
        tx.sign([keypair])
        return b64.b64encode(bytes(tx)).decode()
    except Exception as e:
        print(f"[JUPITER] Signing failed: {e}")
        return None


def to_base_units(amount: Any, decimals: int) -> int:
    """Convert a human amount to integer base units without float drift."""
    return int(Decimal(str(amount)) * (Decimal(10) ** decimals))


def from_base_units(amount: Any, decimals: int) -> float:
    """Convert integer base units to a human amount without float drift."""
    return float(Decimal(str(amount)) / (Decimal(10) ** decimals))


def _parse_price_impact(quote: Dict[str, Any]) -> float:
    try:
        impact = float(quote.get("priceImpactPct", 0.0))
    except (TypeError, ValueError):
        return 0.0
    return impact if math.isfinite(impact) else 0.0


def _quote_amount(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def swap(input_mint: str, output_mint: str, amount: int, taker: Optional[str] = None,
               slippage_bps: int = 50, *, input_decimals: int = 6, output_decimals: int = 9,
               max_price_impact_pct: float = 1.5) -> SwapResult:
    """High-level swap helper: quote -> (sign) -> execute or save pending.

    ``amount`` is always in input base units. Quote amounts win over the request.
    """
    client = JupiterClient()
    quote = await client.get_quote(input_mint, output_mint, amount, taker=taker, slippage_bps=slippage_bps)

    price_impact_pct = _parse_price_impact(quote)
    in_amount = _quote_amount(quote.get("inAmount"), amount)
    out_amount = _quote_amount(quote.get("outAmount"), 0)
    result: SwapResult = {
        "status": "quote",
        "input_mint": input_mint,
        "output_mint": output_mint,
        "in_amount": in_amount,
        "out_amount": out_amount,
        "in_ui_amount": from_base_units(in_amount, input_decimals),
        "out_ui_amount": from_base_units(out_amount, output_decimals),
        "price_impact_pct": price_impact_pct,
        "quote": quote,
    }

    if price_impact_pct > max_price_impact_pct:
        result["status"] = "price_impact_exceeded"
        return result

    tx_b64 = quote.get("transaction")
    request_id = quote.get("requestId")

    if not tx_b64:
        # Quote only
        return result

    keypair = load_keypair()
    signed = sign_transaction(tx_b64, keypair) if keypair else None

    if signed and request_id:
        try:
            execute_result = await client.execute(signed, request_id)
        except Exception as e:
            result["status"] = "execute_failed"
            result["error"] = str(e)
            return result
        result["status"] = "executed"
        result["result"] = execute_result
        signature = execute_result.get("signature")
        if signature:
            result["signature"] = signature
        return result

    # No signer available: persist unsigned tx for external signing
    pending = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "requestId": request_id,
        "transaction": tx_b64,
        "quote": quote,
    }
    Path("data").mkdir(parents=True, exist_ok=True)
    Path("data/pending_swap.json").write_text(json.dumps(pending, indent=2))
    result["status"] = "pending_signature"
    result["pending_file"] = "data/pending_swap.json"
    return result
