from __future__ import annotations

import logging
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import APP_HOST, APP_PORT
from .ib_client import client
from .routes import accounts, dashboard, quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("paleoleon")

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting IB client thread...")
    client.start()
    yield
    log.info("Stopping IB client thread...")
    client.stop()


app = FastAPI(title="PaleoLeon", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(dashboard.router)
app.include_router(accounts.router)
app.include_router(quote.router)


def run() -> None:
    """Console entry point: launch uvicorn and open a browser."""
    import uvicorn

    url = f"http://{APP_HOST}:{APP_PORT}/"
    try:
        webbrowser.open(url)
    except Exception:
        pass
    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=False)


if __name__ == "__main__":
    run()
