# Polymarket Large Trade Telegram Bot - Technical Specification

## 1. Purpose
The service monitors Polymarket trades in near real time and sends Telegram alerts when trade notional exceeds a configurable USD threshold.

Primary alert fields:
- Market name
- Buy/Sell action + outcome
- Amount (USD)
- Trader tag (address-shortened fallback)
- Market link
- Trade link

## 2. Scope
In scope:
- Streaming Polymarket market feed via websocket
- Threshold filtering (`notional_usd > ALERT_THRESHOLD_USD`)
- Telegram notifications to one target chat
- Trade deduplication with TTL
- Basic metadata enrichment from Gamma

Out of scope:
- Guaranteed exactly-once delivery across process restarts
- Historical backfill
- Advanced identity resolution (ENS currently placeholder)
- Persistent queueing / durable offsets

## 3. Code Structure
- `run.py`: entry script.
- `src/polymarket_telegram_bot/main.py`: runtime bootstrap and logging setup.
- `src/polymarket_telegram_bot/config.py`: env loading and settings model.
- `src/polymarket_telegram_bot/service.py`: orchestration, filtering, enrichment, sending, metrics.
- `src/polymarket_telegram_bot/polymarket_stream.py`: websocket connection + subscription + parsing.
- `src/polymarket_telegram_bot/enrichment.py`: market metadata + outcome mapping.
- `src/polymarket_telegram_bot/formatting.py`: alert rendering and utility helpers.
- `src/polymarket_telegram_bot/telegram_notifier.py`: Telegram API sender with retry/backoff.
- `src/polymarket_telegram_bot/dedupe.py`: in-memory dedupe cache.
- `src/polymarket_telegram_bot/types.py`: dataclasses for normalized objects.

## 4. Runtime Data Flow
1. Startup loads `.env` into `Settings`.
2. Stream client fetches active markets from Gamma and derives `clobTokenIds`.
3. Service subscribes to websocket in chunks of asset IDs.
4. Incoming websocket frames are parsed into `NormalizedTrade`.
5. Service computes notional and applies threshold.
6. Dedupe key check prevents repeated alert for same trade.
7. Metadata resolver maps token -> market title, outcome, event slug.
8. Formatter builds Telegram HTML message.
9. Notifier posts to Telegram `sendMessage`.
10. Health metrics emitted periodically.

## 5. Trade Normalization
`NormalizedTrade` fields:
- `trade_id`
- `tx_hash`
- `timestamp` (seconds)
- `token_id`
- `side`
- `price`
- `size`
- `notional_usd` (`price * size`)
- `maker_address`
- `taker_address`

Accepted parser shapes include `price` or `last_trade_price`, and `asset_id`/`token_id`/`market` identifiers.

## 6. Alert Composition
Current alert layout uses Telegram HTML parse mode and emojis.

Rendered fields:
- `🚨 Large Polymarket Trade`
- `🧠 Market`
- `📈 Action` (`Bought/Sold/Traded + outcome`)
- `💵 Amount`
- `👤 Trader`
- `🕒 Time`
- `🔗 Open market | View trade`

## 7. Configuration
Required env vars:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Optional env vars:
- `POLY_WS_URL` (default `wss://ws-subscriptions-clob.polymarket.com/ws/market`)
- `POLY_WS_CHANNEL` (default `market`)
- `POLY_API_BASE` (default `https://gamma-api.polymarket.com`)
- `POLY_CLOB_BASE` (default `https://clob.polymarket.com`)
- `POLY_MARKET_BASE` (default `https://polymarket.com/event`)
- `POLY_MAX_ASSETS` (default `5000`)
- `ALERT_THRESHOLD_USD` (default `100000`)
- `DEDUP_TTL_SECONDS` (default `3600`)
- `HEALTH_LOG_INTERVAL_SECONDS` (default `60`)
- `ENS_RPC_URL` (optional, currently not actively used)
- `LOG_LEVEL` (default `INFO`)
- `POLY_WS_SUBSCRIBE_MESSAGE` (optional custom JSON subscription payload)

## 8. Reliability and Error Handling
- Websocket reconnect with exponential backoff.
- Telegram 429 handling via `retry_after` with retry loop.
- Metadata fetch failures degrade gracefully to token-based placeholders.
- Dedupe cache is in-memory only (resets on process restart).

## 9. Observability
Periodic health log includes:
- `ws_messages`
- `trades_seen`
- `over_threshold`
- `alerts_sent`
- `alerts_failed`

## 10. Security Notes
- `.env` contains secrets and is gitignored.
- Bot token must be rotated immediately if exposed.
- Avoid posting tokens in logs/screenshots/commits.

## 11. Testing
Run:
```bash
PYTHONPATH=src pytest -q
```

Current test coverage includes:
- Trade parsing/normalization
- Dedupe TTL behavior
- Message formatting
- Threshold behavior
- Outcome mapping from `clobTokenIds` + `outcomes`

## 12. Deployment Notes
- Railway build uses `nixpacks.toml`:
  - Install: `pip install --no-cache-dir -r requirements.txt`
  - Start: `PYTHONPATH=src python run.py`
- `Dockerfile` is included as a fallback deployment path.

## 13. Known Limitations
- Burst delivery can occur due to market activity patterns and feed batching.
- Trader identity may be `Unknown` when maker/taker is unavailable.
- CLOB enrichment fallback may return 404 for some token IDs (non-fatal).
- No persistent state store for replay-safe deduplication.

## 14. Future Improvements
- Add durable dedupe store (SQLite/Redis).
- Improve identity resolution (ENS + cached reverse lookup).
- Add per-market/category filters.
- Add optional rate control (digest mode for low thresholds).
- Add Prometheus metrics endpoint.
