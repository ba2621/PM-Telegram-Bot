from polymarket_telegram_bot.formatting import (
    build_market_link,
    build_trade_link,
    format_alert_message,
    short_address,
    side_to_text,
)
from polymarket_telegram_bot.types import AlertPayload


def test_side_to_text() -> None:
    assert side_to_text("BUY") == "Bought"
    assert side_to_text("SELL") == "Sold"
    assert side_to_text("OTHER") == "Traded"


def test_short_address() -> None:
    assert short_address("0x1234567890abcdef") == "0x1234...cdef"


def test_links() -> None:
    assert build_trade_link("0xabc") == "https://polygonscan.com/tx/0xabc"
    assert build_market_link("https://polymarket.com/event", "my-event") == "https://polymarket.com/event/my-event"


def test_format_alert_message_contains_required_fields() -> None:
    payload = AlertPayload(
        market_title="Will X happen?",
        outcome="Yes",
        side_text="Bought",
        amount_usd=125000,
        trader_tag="0x1234...abcd",
        timestamp_iso="2026-02-10T12:00:00Z",
        market_url="https://polymarket.com/event/will-x-happen",
        trade_url="https://polygonscan.com/tx/0xabc",
    )

    text = format_alert_message(payload)
    assert "Will X happen?" in text
    assert "📈 <b>Action:</b> Bought Yes" in text
    assert "$125,000" in text
    assert "0x1234...abcd" in text
    assert "Open market" in text
    assert "View trade" in text
