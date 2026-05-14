# PaleoLeon

A small, local-only web dashboard for a hedge fund using Interactive Brokers and thinkorswim / Schwab.

- **IB**: connects to a running IB Gateway via the TWS API (`ib_async`) and reads every sub-account under your Financial Advisor master login.
- **Schwab / thinkorswim** (Phase 2): live quote lookup via `schwab-py`.

The app runs entirely on `localhost` — no auth, no TLS, nothing leaves the machine.

## Download

One-click launchers (no Python install required):

- **macOS** — [PaleoLeon-mac.zip](https://github.com/ms3001/PaleoLeon/raw/main/assets/PaleoLeon-mac.zip)
- **Windows** — [PaleoLeon-windows.zip](https://github.com/ms3001/PaleoLeon/raw/main/assets/PaleoLeon-windows.zip)
- **Linux** — [PaleoLeon-linux.zip](https://github.com/ms3001/PaleoLeon/raw/main/assets/PaleoLeon-linux.zip)

Unzip and double-click. First run takes ~30 s to set up (downloads [`uv`](https://docs.astral.sh/uv/), Python, and the app); later runs are instant.

- macOS: right-click → **Open** the first time to bypass Gatekeeper.
- Windows: click **More info → Run anyway** if SmartScreen warns.

You also need [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php) running locally with API access enabled (Configure → Settings → API → **Enable ActiveX and Socket Clients**, port 4002 for paper / 4001 for live).

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Firm summary: NAV, cash, PnL, top positions, exposure |
| `/accounts/{id}` | Drill-in for one sub-account |
| `/settings/accounts` | Pick which sub-accounts show, give them labels |
| `/quote` | Live quote from Schwab (Phase 2; requires setup below) |

## Configuration

Environment variables (all optional):

| Variable | Default | Purpose |
| --- | --- | --- |
| `PALEOLEON_IB_HOST` | `127.0.0.1` | IB Gateway host |
| `PALEOLEON_IB_PORT` | `4002` | 4001 live, 4002 paper, 7497 TWS paper, 7496 TWS live |
| `PALEOLEON_IB_CLIENT_ID` | `17` | Any unused TWS client id |
| `PALEOLEON_PORT` | `8000` | Dashboard port |
| `PALEOLEON_REFRESH_SECONDS` | `15` | Dashboard auto-refresh |
| `PALEOLEON_HOME` | `~/.paleoleon` | Settings & Schwab token directory |

Account labels and Schwab credentials persist to `~/.paleoleon/settings.json`.

## Schwab / thinkorswim quotes (Phase 2)

1. Register an app at <https://developer.schwab.com>.
2. Open `/quote` in the dashboard, paste the app key + secret, save.
3. First quote lookup triggers the OAuth flow once; the refresh token is cached at `~/.paleoleon/schwab_token.json`.

## Run from source (advanced)

If you'd rather skip the launcher:

```bash
pip install git+https://github.com/ms3001/PaleoLeon.git
paleoleon
# or: uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

## Develop

```bash
git clone https://github.com/ms3001/PaleoLeon.git
cd PaleoLeon
pip install -e '.[dev,schwab]'
pytest
ruff check .
```

## Releasing

The launcher zips under `assets/` are committed directly so the README links work without any Actions-driven release pipeline. To cut a new build:

```bash
chmod +x launcher/PaleoLeon.command launcher/PaleoLeon.sh
(cd launcher && zip ../assets/PaleoLeon-mac.zip PaleoLeon.command)
(cd launcher && zip ../assets/PaleoLeon-linux.zip PaleoLeon.sh)
(cd launcher && zip ../assets/PaleoLeon-windows.zip PaleoLeon.bat)
git add assets/ && git commit -m "Refresh launcher zips" && git push
```

A `Release launchers` workflow exists in `.github/workflows/release.yml` that does the same thing on `git tag v*` and attaches the zips to the GitHub Release — useful once your Actions billing is unlocked.
