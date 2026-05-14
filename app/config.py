from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


IB_HOST: str = _env("PALEOLEON_IB_HOST", "127.0.0.1")
IB_PORT: int = int(_env("PALEOLEON_IB_PORT", "4002"))
IB_CLIENT_ID: int = int(_env("PALEOLEON_IB_CLIENT_ID", "17"))

SETTINGS_DIR: Path = Path(_env("PALEOLEON_HOME", str(Path.home() / ".paleoleon")))
SETTINGS_FILE: Path = SETTINGS_DIR / "settings.json"
SCHWAB_TOKEN_FILE: Path = SETTINGS_DIR / "schwab_token.json"

REFRESH_SECONDS: int = int(_env("PALEOLEON_REFRESH_SECONDS", "15"))

APP_HOST: str = _env("PALEOLEON_HOST", "127.0.0.1")
APP_PORT: int = int(_env("PALEOLEON_PORT", "8000"))
