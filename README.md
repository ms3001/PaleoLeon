# PaleoLeon

A small, local-only web dashboard for a hedge fund using Interactive Brokers and thinkorswim / Schwab.

- **IB**: connects to a running IB Gateway via the TWS API (`ib_async`) and reads every sub-account under your Financial Advisor master login.
- **Schwab / thinkorswim** (Phase 2): live quote lookup via `schwab-py`.

The app runs entirely on `localhost` — no auth, no TLS, nothing leaves the machine. A static landing page is published to GitHub Pages for distribution only.

## Quick start

```bash
# install
pip install -e .

# start IB Gateway (paper port 4002 by default) and enable API access:
#   Configure -> Settings -> API -> Enable ActiveX and Socket Clients

# run
paleoleon
# or: uvicorn app.main:app --reload
```

Then visit <http://localhost:8000>.

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Firm summary: NAV, cash, PnL, top positions, exposure |
| `/accounts/{id}` | Drill-in for one sub-account |
| `/settings/accounts` | Pick which sub-accounts show, give them labels |
| `/quote` | Live quote from Schwab (requires Phase 2 deps + creds) |

## Config (env vars)

| Variable | Default | Purpose |
| --- | --- | --- |
| `PALEOLEON_IB_HOST` | `127.0.0.1` | IB Gateway host |
| `PALEOLEON_IB_PORT` | `4002` | 4001 live, 4002 paper, 7497 TWS paper, 7496 TWS live |
| `PALEOLEON_IB_CLIENT_ID` | `17` | Any unused TWS client id |
| `PALEOLEON_PORT` | `8000` | Dashboard port |
| `PALEOLEON_REFRESH_SECONDS` | `15` | Dashboard auto-refresh |
| `PALEOLEON_HOME` | `~/.paleoleon` | Settings & Schwab token directory |

## Schwab / thinkorswim (Phase 2)

1. Register an app at <https://developer.schwab.com>.
2. `pip install -e '.[schwab]'`
3. Open `/quote`, save app key + secret. First quote triggers the OAuth flow once; refresh token is cached at `~/.paleoleon/schwab_token.json`.

## Dev

```bash
pip install -e '.[dev,schwab]'
pytest
ruff check .
```

## Landing page

`docs/index.html` is published to GitHub Pages via `.github/workflows/pages.yml` on every push to `main`. After the first deploy, enable Pages in repo settings → Pages → Source: GitHub Actions.
