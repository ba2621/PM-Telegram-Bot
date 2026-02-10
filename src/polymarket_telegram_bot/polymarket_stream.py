from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
import websockets

from .types import NormalizedTrade

logger = logging.getLogger(__name__)


class PolymarketTradeStream:
    def __init__(
        self,
        ws_url: str,
        channel: str,
        gamma_api_base: str,
        max_assets: int = 5000,
        subscribe_message: dict[str, Any] | None = None,
    ) -> None:
        self.ws_url = ws_url
        self.channel = channel
        self.gamma_api_base = gamma_api_base.rstrip("/")
        self.max_assets = max_assets
        self.subscribe_message = subscribe_message

    async def trades(self) -> AsyncIterator[NormalizedTrade]:
        backoff = 1.0
        while True:
            try:
                asset_ids = await self._fetch_active_asset_ids()
                if not asset_ids and self.subscribe_message is None:
                    raise RuntimeError("No asset_ids discovered for market subscription")

                connect_url = self._connect_url()
                async with websockets.connect(connect_url, ping_interval=20, ping_timeout=20) as ws:
                    if self.subscribe_message is not None:
                        await ws.send(json.dumps(self.subscribe_message))
                    else:
                        await self._send_market_subscriptions(ws, asset_ids)
                    logger.info("Connected to Polymarket WS %s (assets=%d)", connect_url, len(asset_ids))
                    backoff = 1.0

                    async for raw in ws:
                        for trade in parse_ws_message(raw):
                            yield trade
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("WS disconnected (%s). Reconnecting in %.1fs", exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    def _connect_url(self) -> str:
        if "/ws/" in self.ws_url:
            return self.ws_url
        return f"{self.ws_url.rstrip('/')}/ws/{self.channel}"

    async def _send_market_subscriptions(self, ws: Any, asset_ids: list[str]) -> None:
        chunk_size = 300
        total = min(len(asset_ids), self.max_assets)
        for i in range(0, total, chunk_size):
            chunk = asset_ids[i : i + chunk_size]
            await ws.send(
                json.dumps(
                    {
                        "type": self.channel,
                        "assets_ids": chunk,
                    }
                )
            )

    async def _fetch_active_asset_ids(self) -> list[str]:
        # Gamma's events endpoint includes markets with clobTokenIds.
        out: list[str] = []
        seen: set[str] = set()
        limit = 100
        offset = 0
        async with httpx.AsyncClient(timeout=20) as client:
            while True:
                resp = await client.get(
                    f"{self.gamma_api_base}/events",
                    params={"closed": "false", "limit": limit, "offset": offset},
                )
                resp.raise_for_status()
                data = resp.json()
                if not isinstance(data, list) or not data:
                    break
                for event in data:
                    markets = event.get("markets", [])
                    if not isinstance(markets, list):
                        continue
                    for market in markets:
                        raw = market.get("clobTokenIds")
                        if not raw:
                            continue
                        try:
                            ids = json.loads(raw) if isinstance(raw, str) else raw
                        except Exception:
                            continue
                        if isinstance(ids, list):
                            for token_id in ids:
                                text = str(token_id).strip()
                                if text and text not in seen:
                                    seen.add(text)
                                    out.append(text)
                if len(data) < limit:
                    break
                offset += limit
        return out


def parse_ws_message(raw: str) -> list[NormalizedTrade]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    records = _extract_trade_records(payload)
    trades: list[NormalizedTrade] = []
    for record in records:
        trade = _normalize_trade(record)
        if trade is not None:
            trades.append(trade)
    return trades


def _extract_trade_records(payload: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
            return

        if not isinstance(node, dict):
            return

        if _looks_like_trade(node):
            results.append(node)
            return

        for key in ("data", "trades", "payload", "message", "result"):
            if key in node:
                visit(node[key])

    visit(payload)
    return results


def _looks_like_trade(record: dict[str, Any]) -> bool:
    keys = set(record.keys())
    return (
        (("price" in keys or "last_trade_price" in keys) and ("size" in keys or "amount" in keys))
        and ("asset_id" in keys or "token_id" in keys or "market" in keys)
    )


def _normalize_trade(record: dict[str, Any]) -> NormalizedTrade | None:
    token_id = str(
        record.get("asset_id")
        or record.get("token_id")
        or record.get("market")
        or ""
    ).strip()
    if not token_id:
        return None

    try:
        price = float(record.get("price", record.get("last_trade_price", 0)) or 0)
        size = float(record.get("size", record.get("amount", 0)) or 0)
    except (TypeError, ValueError):
        return None

    if price <= 0 or size <= 0:
        return None

    raw_ts = record.get("timestamp", record.get("ts", 0))
    try:
        timestamp = int(float(raw_ts))
    except (TypeError, ValueError):
        return None

    if timestamp > 10**12:
        timestamp //= 1000

    tx_hash_raw = record.get("transactionHash") or record.get("tx_hash") or record.get("transaction_hash")
    tx_hash = str(tx_hash_raw).strip() if tx_hash_raw else None

    side = str(record.get("side", "UNKNOWN")).upper()
    trade_id = str(record.get("id") or record.get("trade_id") or "").strip()
    if not trade_id:
        trade_id = f"{tx_hash or 'notx'}_{timestamp}_{token_id}_{price}_{size}"

    maker = _string_or_none(record.get("maker_address") or record.get("maker"))
    taker = _string_or_none(record.get("taker_address") or record.get("taker"))

    return NormalizedTrade(
        trade_id=trade_id,
        tx_hash=tx_hash,
        timestamp=timestamp,
        token_id=token_id,
        side=side,
        price=price,
        size=size,
        notional_usd=price * size,
        maker_address=maker,
        taker_address=taker,
    )


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
