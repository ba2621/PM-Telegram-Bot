from __future__ import annotations

import asyncio
import logging

from .config import load_settings
from .service import AlertService


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def _main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    service = AlertService(settings)
    await service.run()


def main() -> None:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
