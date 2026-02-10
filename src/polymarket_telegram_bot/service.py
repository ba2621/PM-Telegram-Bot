from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx

from .config import Settings
from .dedupe import TradeDeduper
from .enrichment import IdentityResolver, MarketMetadataResolver
from .formatting import (
    build_market_link,
    build_trade_link,
    dedupe_key,
    format_alert_message,
    side_to_text,
    trade_time_iso,
)
from .polymarket_stream import PolymarketTradeStream
from .telegram_notifier import TelegramNotifier
from .types import AlertPayload, NormalizedTrade

logger = logging.getLogger(__name__)


@dataclass
class Metrics:
    ws_messages: int = 0
    trades_seen: int = 0
    trades_over_threshold: int = 0
    alerts_sent: int = 0
    alerts_failed: int = 0


class AlertService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.metrics = Metrics()
        self.deduper = TradeDeduper(settings.dedup_ttl_seconds)
        self.stream = PolymarketTradeStream(
            ws_url=settings.poly_ws_url,
            channel=settings.poly_ws_channel,
            gamma_api_base=settings.poly_api_base,
            max_assets=settings.poly_max_assets,
            subscribe_message=settings.poly_ws_subscribe_message,
        )
        self.notifier = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id)
        self.meta = MarketMetadataResolver(settings.poly_api_base)
        self.identity = IdentityResolver(settings.ens_rpc_url)
        self.clob_client = httpx.AsyncClient(timeout=15)

    async def run(self) -> None:
        health_task = asyncio.create_task(self._health_loop())
        try:
            async for trade in self.stream.trades():
                self.metrics.ws_messages += 1
                await self._handle_trade(trade)
        finally:
            health_task.cancel()
            await asyncio.gather(health_task, return_exceptions=True)
            await self.notifier.close()
            await self.meta.close()
            await self.clob_client.aclose()

    async def _handle_trade(self, trade: NormalizedTrade) -> None:
        self.metrics.trades_seen += 1

        if trade.notional_usd <= self.settings.alert_threshold_usd:
            return

        self.metrics.trades_over_threshold += 1

        key = dedupe_key(trade)
        if not self.deduper.is_new(key):
            return

        alert = await self._build_alert(trade)
        text = format_alert_message(alert)

        try:
            await self.notifier.send(text)
            self.metrics.alerts_sent += 1
            logger.info(
                "Alert sent trade_id=%s amount=%.2f market=%s",
                trade.trade_id,
                trade.notional_usd,
                alert.market_title,
            )
        except Exception as exc:
            self.metrics.alerts_failed += 1
            logger.exception("Failed to send Telegram alert for trade %s: %s", trade.trade_id, exc)

    async def _build_alert(self, trade: NormalizedTrade) -> AlertPayload:
        trade = await self._enrich_trade_details(trade)
        meta = await self.meta.resolve(trade.token_id)
        actor = self._pick_actor(trade)
        trader_tag = await self.identity.resolve_tag(actor)

        return AlertPayload(
            market_title=meta.market_title,
            outcome=meta.outcome,
            side_text=side_to_text(trade.side),
            amount_usd=trade.notional_usd,
            trader_tag=trader_tag,
            timestamp_iso=trade_time_iso(trade.timestamp),
            market_url=build_market_link(self.settings.poly_market_base, meta.event_slug),
            trade_url=build_trade_link(trade.tx_hash),
        )

    async def _enrich_trade_details(self, trade: NormalizedTrade) -> NormalizedTrade:
        # If identity/hash already present, keep original.
        if trade.tx_hash and (trade.maker_address or trade.taker_address):
            return trade

        try:
            resp = await self.clob_client.get(
                f"{self.settings.poly_clob_base.rstrip('/')}/trades-history",
                params={"market": trade.token_id},
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("data", []) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                return trade

            for row in rows[:25]:
                candidate = self._match_trade_candidate(trade, row)
                if candidate is not None:
                    return candidate
        except Exception:
            return trade

        return trade

    @staticmethod
    def _match_trade_candidate(trade: NormalizedTrade, row: dict) -> NormalizedTrade | None:
        try:
            price = float(row.get("price", 0) or 0)
            size = float(row.get("size", 0) or 0)
            raw_ts = row.get("timestamp", 0)
            ts = int(float(raw_ts))
            if ts > 10**12:
                ts //= 1000
        except Exception:
            return None

        # Loose matching: same token + similar timestamp + same price/size.
        if abs(ts - trade.timestamp) > 10:
            return None
        if abs(price - trade.price) > 1e-6:
            return None
        if abs(size - trade.size) > 1e-6:
            return None

        tx_hash_raw = row.get("transactionHash") or row.get("transaction_hash")
        tx_hash = str(tx_hash_raw).strip() if tx_hash_raw else trade.tx_hash
        maker = row.get("maker_address") or row.get("maker") or trade.maker_address
        taker = row.get("taker_address") or row.get("taker") or trade.taker_address
        side = str(row.get("side", trade.side)).upper()

        return NormalizedTrade(
            trade_id=trade.trade_id,
            tx_hash=tx_hash,
            timestamp=trade.timestamp,
            token_id=trade.token_id,
            side=side,
            price=trade.price,
            size=trade.size,
            notional_usd=trade.notional_usd,
            maker_address=str(maker).strip() if maker else None,
            taker_address=str(taker).strip() if taker else None,
        )

    @staticmethod
    def _pick_actor(trade: NormalizedTrade) -> str | None:
        if trade.side == "BUY":
            return trade.taker_address or trade.maker_address
        if trade.side == "SELL":
            return trade.maker_address or trade.taker_address
        return trade.taker_address or trade.maker_address

    async def _health_loop(self) -> None:
        while True:
            await asyncio.sleep(self.settings.health_log_interval_seconds)
            logger.info(
                (
                    "health ws_messages=%d trades_seen=%d over_threshold=%d "
                    "alerts_sent=%d alerts_failed=%d"
                ),
                self.metrics.ws_messages,
                self.metrics.trades_seen,
                self.metrics.trades_over_threshold,
                self.metrics.alerts_sent,
                self.metrics.alerts_failed,
            )
