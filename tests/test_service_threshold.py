import asyncio

from polymarket_telegram_bot.config import Settings
from polymarket_telegram_bot.service import AlertService
from polymarket_telegram_bot.types import MarketMetadata, NormalizedTrade


class DummyNotifier:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, text: str) -> None:
        self.messages.append(text)

    async def close(self) -> None:
        return None


class DummyMeta:
    async def resolve(self, token_id: str) -> MarketMetadata:
        return MarketMetadata("Test Market", "Yes", "test-market")

    async def close(self) -> None:
        return None


class DummyIdentity:
    async def resolve_tag(self, address: str | None) -> str:
        return "0x1234...abcd"


def _settings() -> Settings:
    return Settings(
        telegram_bot_token="t",
        telegram_chat_id="c",
        poly_ws_url="wss://example.com",
        poly_ws_channel="market",
        poly_api_base="https://gamma-api.polymarket.com",
        poly_clob_base="https://clob.polymarket.com",
        poly_market_base="https://polymarket.com/event",
        alert_threshold_usd=100000,
        dedup_ttl_seconds=3600,
        health_log_interval_seconds=1000,
        ens_rpc_url=None,
        log_level="INFO",
        poly_ws_subscribe_message=None,
        poly_max_assets=5000,
    )


def test_threshold_strictly_greater_than_100k() -> None:
    service = AlertService(_settings())
    service.notifier = DummyNotifier()
    service.meta = DummyMeta()
    service.identity = DummyIdentity()

    at_threshold = NormalizedTrade(
        trade_id="1",
        tx_hash="0x1",
        timestamp=1730000000,
        token_id="1",
        side="BUY",
        price=0.5,
        size=200000,
        notional_usd=100000,
        maker_address="0xmaker",
        taker_address="0xtaker",
    )

    over_threshold = NormalizedTrade(
        trade_id="2",
        tx_hash="0x2",
        timestamp=1730000001,
        token_id="1",
        side="BUY",
        price=0.5,
        size=200001,
        notional_usd=100000.5,
        maker_address="0xmaker",
        taker_address="0xtaker",
    )

    asyncio.run(service._handle_trade(at_threshold))
    asyncio.run(service._handle_trade(over_threshold))

    assert len(service.notifier.messages) == 1
