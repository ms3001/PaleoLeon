from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import Lock

from .config import SETTINGS_DIR, SETTINGS_FILE


@dataclass
class Settings:
    scope: str = "all"
    watchlist: list[dict] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "scope": self.scope,
            "watchlist": list(self.watchlist),
        }

    @classmethod
    def from_json(cls, data: dict) -> "Settings":
        wl = data.get("watchlist") or []
        clean: list[dict] = []
        for item in wl:
            if not isinstance(item, dict):
                continue
            sym = (item.get("symbol") or "").strip()
            if not sym:
                continue
            clean.append(
                {
                    "symbol": sym,
                    "sec_type": (item.get("sec_type") or "STK").strip() or "STK",
                    "currency": (item.get("currency") or "USD").strip() or "USD",
                }
            )
        return cls(
            scope=(data.get("scope") or "all").strip() or "all",
            watchlist=clean,
        )


_lock = Lock()


def load() -> Settings:
    with _lock:
        if not SETTINGS_FILE.exists():
            return Settings()
        try:
            data = json.loads(SETTINGS_FILE.read_text())
        except json.JSONDecodeError:
            return Settings()
        return Settings.from_json(data)


def save(settings: Settings) -> None:
    with _lock:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(settings.to_json(), indent=2))
