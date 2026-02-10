<<<<<<< HEAD
# PM-Telegram-Bot
This is a telegram bot to get alerts for prediction markets
=======
# Polymarket Large Trade Telegram Bot

Sends a Telegram message to your configured chat whenever a Polymarket trade exceeds a USD threshold (default: `$100,000`).

## Alert contents
- Market name
- Buy/sell action
- USD amount
- Trader tag (shortened wallet; ENS hook ready)
- Market link
- Trade link (PolygonScan)

## Setup

1. Create and activate a virtualenv.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy env template and set values:

```bash
cp .env.example .env
```

Required:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Run

```bash
PYTHONPATH=src python run.py
```

## Notes
- The bot uses Polymarket websocket streaming and reconnects automatically.
- On startup it auto-discovers active token IDs from Gamma and subscribes to the market WS.
- Duplicate alerts are suppressed with a TTL-based dedupe cache.
- If metadata lookup fails, alerts still send with token fallback labels.

## Testing

```bash
PYTHONPATH=src pytest -q
```
>>>>>>> eee92bc (Initial commit)
