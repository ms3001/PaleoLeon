#!/usr/bin/env bash
# PaleoLeon launcher — macOS
# Bootstraps uv on first run, then launches the dashboard.
set -eo pipefail

PALEO_HOME="${PALEOLEON_HOME:-$HOME/.paleoleon}"
mkdir -p "$PALEO_HOME"

if command -v uv >/dev/null 2>&1; then
    UV=$(command -v uv)
elif [ -x "$PALEO_HOME/uv" ]; then
    UV="$PALEO_HOME/uv"
else
    echo "First run: installing uv into $PALEO_HOME ..."
    if ! curl -LsSf https://astral.sh/uv/install.sh \
        | UV_INSTALL_DIR="$PALEO_HOME" UV_UNMANAGED_INSTALL="$PALEO_HOME" sh; then
        echo
        echo "Failed to download uv. Are you connected to the internet?"
        echo "Press Enter to close."
        read -r _
        exit 1
    fi
    UV="$PALEO_HOME/uv"
fi

echo "Launching PaleoLeon..."
exec "$UV" tool run --refresh \
    --from "git+https://github.com/ms3001/PaleoLeon" paleoleon
