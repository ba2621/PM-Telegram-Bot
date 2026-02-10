from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from .formatting import short_address
from .types import MarketMetadata

logger = logging.getLogger(__name__)


class MarketMetadataResolver:
    def __init__(self, api_base: str, timeout: float = 15.0) -> None:
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
        self._cache: dict[str, MarketMetadata] = {}
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self._client.aclose()

    async def resolve(self, token_id: str) -> MarketMetadata:
        cached = self._cache.get(token_id)
        if cached:
            return cached

        async with self._lock:
            cached = self._cache.get(token_id)
            if cached:
                return cached

            meta = await self._fetch_market_metadata(token_id)
            self._cache[token_id] = meta
            return meta

    async def _fetch_market_metadata(self, token_id: str) -> MarketMetadata:
        # Try multiple query styles because deployed APIs vary by field naming.
        candidates = [
            ("/markets", {"clob_token_ids": token_id, "limit": 1}),
            ("/markets", {"clobTokenIds": token_id, "limit": 1}),
            ("/markets", {"id": token_id, "limit": 1}),
        ]

        for path, params in candidates:
            try:
                data = await self._get(path, params=params)
            except Exception as exc:
                logger.debug("Market metadata request failed for %s %s: %s", path, params, exc)
                continue

            market = self._extract_market(data, token_id)
            if market is None:
                continue

            title = str(
                market.get("question")
                or market.get("title")
                or market.get("groupItemTitle")
                or f"Token {token_id}"
            )
            outcome = self._extract_outcome(market, token_id)
            event_slug = self._extract_event_slug(market)
            return MarketMetadata(market_title=title, outcome=outcome, event_slug=event_slug)

        return MarketMetadata(market_title=f"Token {token_id}", outcome=None, event_slug=None)

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        resp = await self._client.get(f"{self.api_base}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _extract_market(data: Any, token_id: str) -> dict[str, Any] | None:
        markets: list[dict[str, Any]] = []
        if isinstance(data, list):
            markets = [m for m in data if isinstance(m, dict)]
        elif isinstance(data, dict):
            if isinstance(data.get("markets"), list):
                markets = [m for m in data["markets"] if isinstance(m, dict)]
            elif all(k in data for k in ("id", "question")):
                markets = [data]

        if not markets:
            return None

        for m in markets:
            ids = m.get("clobTokenIds")
            if isinstance(ids, str) and token_id in ids:
                return m
            if isinstance(ids, list) and token_id in [str(x) for x in ids]:
                return m
            if str(m.get("id", "")) == token_id:
                return m

        return markets[0]

    @staticmethod
    def _extract_event_slug(market: dict[str, Any]) -> str | None:
        events = market.get("events")
        if isinstance(events, list) and events:
            first = events[0]
            if isinstance(first, dict):
                slug = first.get("slug")
                if isinstance(slug, str) and slug:
                    return slug
        slug = market.get("slug")
        if isinstance(slug, str) and slug:
            return slug
        return None

    @staticmethod
    def _extract_outcome(market: dict[str, Any], token_id: str) -> str | None:
        # First, try explicit one-to-one mapping from clob token to outcome label.
        token_ids = _to_list(market.get("clobTokenIds"))
        outcomes = _to_list(market.get("outcomes"))
        if token_ids and outcomes and len(token_ids) == len(outcomes):
            token_text = str(token_id)
            for idx, tid in enumerate(token_ids):
                if str(tid) == token_text:
                    outcome = outcomes[idx]
                    if isinstance(outcome, str) and outcome.strip():
                        return outcome

        # Fallback to simple fields for single-outcome styles.
        for key in ("outcome", "subtitle"):
            value = market.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return None


def _to_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


class IdentityResolver:
    def __init__(self, ens_rpc_url: str | None = None) -> None:
        self.ens_rpc_url = ens_rpc_url

    async def resolve_tag(self, address: str | None) -> str:
        # Placeholder for future ENS lookup. Today we use short address fallback.
        return short_address(address)
