from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    telegram_chat_id: str
    poly_ws_url: str
    poly_ws_channel: str
    poly_api_base: str
    poly_clob_base: str
    poly_market_base: str
    alert_threshold_usd: float
    dedup_ttl_seconds: int
    health_log_interval_seconds: int
    ens_rpc_url: str | None
    log_level: str
    poly_ws_subscribe_message: dict[str, Any] | None
    poly_max_assets: int


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _optional_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _optional_json(name: str) -> dict[str, Any] | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must decode to a JSON object")
    return parsed


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        telegram_bot_token=_required("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_required("TELEGRAM_CHAT_ID"),
        poly_ws_url=os.getenv(
            "POLY_WS_URL", "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        ).strip(),
        poly_ws_channel=os.getenv("POLY_WS_CHANNEL", "market").strip(),
        poly_api_base=os.getenv("POLY_API_BASE", "https://gamma-api.polymarket.com").strip(),
        poly_clob_base=os.getenv("POLY_CLOB_BASE", "https://clob.polymarket.com").strip(),
        poly_market_base=os.getenv("POLY_MARKET_BASE", "https://polymarket.com/event").strip(),
        alert_threshold_usd=_optional_float("ALERT_THRESHOLD_USD", 100000.0),
        dedup_ttl_seconds=_optional_int("DEDUP_TTL_SECONDS", 3600),
        health_log_interval_seconds=_optional_int("HEALTH_LOG_INTERVAL_SECONDS", 60),
        ens_rpc_url=os.getenv("ENS_RPC_URL", "").strip() or None,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        poly_ws_subscribe_message=_optional_json("POLY_WS_SUBSCRIBE_MESSAGE"),
        poly_max_assets=_optional_int("POLY_MAX_ASSETS", 5000),
    )
