from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedTrade:
    trade_id: str
    tx_hash: str | None
    timestamp: int
    token_id: str
    side: str
    price: float
    size: float
    notional_usd: float
    maker_address: str | None
    taker_address: str | None


@dataclass(frozen=True)
class MarketMetadata:
    market_title: str
    outcome: str | None
    event_slug: str | None


@dataclass(frozen=True)
class AlertPayload:
    market_title: str
    outcome: str | None
    side_text: str
    amount_usd: float
    trader_tag: str
    timestamp_iso: str
    market_url: str | None
    trade_url: str | None
