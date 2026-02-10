from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, timeout: float = 15.0) -> None:
        self.chat_id = chat_id
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def send(self, text: str) -> None:
        retries = 4
        delay = 1.0

        for attempt in range(retries):
            try:
                response = await self._client.post(
                    self._url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                )

                if response.status_code == 429:
                    retry_after = 2.0
                    try:
                        payload = response.json()
                        retry_after = float(
                            payload.get("parameters", {}).get("retry_after", retry_after)
                        )
                    except Exception:
                        pass
                    logger.warning("Telegram rate limited. Sleeping %.1fs", retry_after)
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                if not data.get("ok", False):
                    raise RuntimeError(f"Telegram send failed: {data}")
                return
            except Exception as exc:
                if attempt == retries - 1:
                    raise
                logger.warning("Telegram send attempt %d failed: %s", attempt + 1, exc)
                await asyncio.sleep(delay)
                delay *= 2
