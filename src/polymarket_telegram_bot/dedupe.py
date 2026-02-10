from __future__ import annotations

import time
from collections import OrderedDict


class TradeDeduper:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._seen: OrderedDict[str, float] = OrderedDict()

    def is_new(self, key: str) -> bool:
        now = time.time()
        self._purge(now)
        if key in self._seen:
            self._seen.move_to_end(key)
            return False
        self._seen[key] = now
        return True

    def _purge(self, now: float) -> None:
        cutoff = now - self.ttl_seconds
        while self._seen:
            first_key = next(iter(self._seen))
            if self._seen[first_key] >= cutoff:
                break
            self._seen.popitem(last=False)
