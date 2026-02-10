import time

from polymarket_telegram_bot.dedupe import TradeDeduper


def test_dedupe_rejects_duplicate_within_ttl() -> None:
    d = TradeDeduper(ttl_seconds=60)
    assert d.is_new("a") is True
    assert d.is_new("a") is False


def test_dedupe_allows_after_ttl_expiry() -> None:
    d = TradeDeduper(ttl_seconds=1)
    assert d.is_new("a") is True
    time.sleep(1.1)
    assert d.is_new("a") is True
