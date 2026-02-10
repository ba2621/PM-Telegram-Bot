from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from .types import AlertPayload, NormalizedTrade


def side_to_text(side: str) -> str:
    s = (side or "").upper()
    if s == "BUY":
        return "Bought"
    if s == "SELL":
        return "Sold"
    return "Traded"


def short_address(address: str | None) -> str:
    if not address:
        return "Unknown"
    addr = address.strip()
    if len(addr) <= 12:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def trade_time_iso(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def build_trade_link(tx_hash: str | None) -> str | None:
    if not tx_hash:
        return None
    return f"https://polygonscan.com/tx/{tx_hash}"


def build_market_link(base_url: str, event_slug: str | None) -> str | None:
    if not event_slug:
        return None
    return f"{base_url.rstrip('/')}/{event_slug}"


def format_alert_message(payload: AlertPayload) -> str:
    market_title = escape(payload.market_title)
    side_text = escape(payload.side_text)
    outcome_text = escape(payload.outcome or "N/A")
    trader_tag = escape(payload.trader_tag)
    timestamp_iso = escape(payload.timestamp_iso)

    links: list[str] = []
    if payload.market_url:
        links.append(f'<a href="{escape(payload.market_url, quote=True)}">Open market</a>')
    if payload.trade_url:
        links.append(f'<a href="{escape(payload.trade_url, quote=True)}">View trade</a>')
    link_line = " | ".join(links) if links else "No links available"

    return (
        "🚨 <b>Large Polymarket Trade</b>\n\n"
        f"🧠 <b>Market:</b> {market_title}\n"
        f"📈 <b>Action:</b> {side_text} {outcome_text}\n"
        f"💵 <b>Amount:</b> ${payload.amount_usd:,.0f}\n"
        f"👤 <b>Trader:</b> {trader_tag}\n"
        f"🕒 <b>Time:</b> {timestamp_iso}\n\n"
        f"🔗 {link_line}"
    )


def dedupe_key(trade: NormalizedTrade) -> str:
    if trade.trade_id:
        return trade.trade_id
    return f"{trade.tx_hash or 'nohash'}_{trade.timestamp}_{trade.token_id}"
