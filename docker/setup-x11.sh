#!/usr/bin/env bash
# Setup X11 auth for Docker containers.
# Supports local/VNC displays (:0, :1, ...) and SSH-forwarded displays (localhost:10.0).

set -euo pipefail

XAUTH_FILE="/tmp/.docker.xauth"

if [[ -z "${DISPLAY:-}" ]]; then
    echo "Error: DISPLAY is not set."
    echo "Set DISPLAY first (examples: :0, :1, localhost:10.0)."
    exit 1
fi

# Detect SSH-forwarded DISPLAYs, where unix socket validation is not applicable.
is_ssh_x11=false
case "$DISPLAY" in
    localhost:*|127.0.0.1:*|[[]::1[]]:*)
        is_ssh_x11=true
        ;;
esac

if [[ "$is_ssh_x11" == false ]]; then
    # Validate that the local/VNC target display socket exists (e.g. :0 or :1).
    display_num="${DISPLAY##*:}"
    display_num="${display_num%%.*}"
    x_socket="/tmp/.X11-unix/X${display_num}"
    if [[ ! -S "$x_socket" ]]; then
        echo "Error: X display socket not found: $x_socket"
        echo "For VNC, start it first (example): systemctl --user start vncserver@1"
        echo "Then export DISPLAY correctly (example): export DISPLAY=:1"
        exit 1
    fi
fi

if ! command -v xauth >/dev/null 2>&1; then
    echo "Error: xauth is not installed. Install it first: sudo apt install -y xauth"
    exit 1
fi

touch "$XAUTH_FILE"
chmod 600 "$XAUTH_FILE"

# Rebuild container auth from the active X cookie so root in the container can connect.
if xauth nlist "$DISPLAY" | sed -e 's/^..../ffff/' | xauth -f "$XAUTH_FILE" nmerge - >/dev/null 2>&1; then
    :
else
    echo "Warning: could not extract Xauthority cookie for DISPLAY=$DISPLAY"
fi

# For local/VNC displays, allow local docker clients.
# For SSH-forwarded displays, xhost often cannot modify remote access controls; cookie auth is enough.
if command -v xhost >/dev/null 2>&1; then
    if [[ "$is_ssh_x11" == false ]]; then
        xhost +local:docker >/dev/null 2>&1 || true
        xhost +SI:localuser:root >/dev/null 2>&1 || true
    fi
fi

echo "DISPLAY=$DISPLAY"
echo "XAUTH file ready: $XAUTH_FILE"
if [[ "$is_ssh_x11" == true ]]; then
    echo "Detected SSH-forwarded display. Use host networking for the container so localhost X11 tunnel is reachable."
fi
echo "You can now run: docker compose up -d"
