from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

from .config import SETTINGS_DIR, SETTINGS_FILE


@dataclass
class Settings:
    visible_accounts: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    schwab_api_key: Optional[str] = None
    schwab_app_secret: Optional[str] = None
    schwab_callback_url: str = "https://127.0.0.1:8182"

    def to_json(self) -> dict:
        return {
            "visible_accounts": list(self.visible_accounts),
            "labels": dict(self.labels),
            "schwab_api_key": self.schwab_api_key,
            "schwab_app_secret": self.schwab_app_secret,
            "schwab_callback_url": self.schwab_callback_url,
        }

    @classmethod
    def from_json(cls, data: dict) -> "Settings":
        return cls(
            visible_accounts=list(data.get("visible_accounts") or []),
            labels=dict(data.get("labels") or {}),
            schwab_api_key=data.get("schwab_api_key"),
            schwab_app_secret=data.get("schwab_app_secret"),
            schwab_callback_url=data.get("schwab_callback_url") or "https://127.0.0.1:8182",
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
