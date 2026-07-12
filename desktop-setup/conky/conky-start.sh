#!/usr/bin/env bash
# conky-start.sh — the ONE conky backend script.
# Starts both panels (left + right) pinned to the laptop screen, then watches
# GNOME for monitor-layout changes and restarts them so they never drift to the
# wrong screen. Replaces conky-launch.sh + conky-monitor-watch.sh (2026-07-09).
set -uo pipefail
export DISPLAY="${DISPLAY:-:0}"

CONF_DIR="$HOME/.config/conky"
OUTPUT="${CONKY_OUTPUT:-eDP-1}"   # built-in laptop display

# Match the XWayland (X11) cursor to GNOME's, so hovering the conky panels
# never swaps in a wrong-sized cursor.
XCURSOR_THEME=$(gsettings get org.gnome.desktop.interface cursor-theme 2>/dev/null | tr -d "'")
XCURSOR_SIZE=$(gsettings get org.gnome.desktop.interface cursor-size 2>/dev/null)
export XCURSOR_THEME="${XCURSOR_THEME:-Yaru}" XCURSOR_SIZE="${XCURSOR_SIZE:-24}"

launch_panels() {
    pkill -x conky 2>/dev/null || true
    sleep 1

    # wait for X / XWayland at login
    for _ in $(seq 1 30); do
        xrandr --query >/dev/null 2>&1 && break
        sleep 1
    done

    # current Xinerama head index of the built-in output (for conky -m)
    idx=$(xrandr --listmonitors 2>/dev/null | awk -v o="$OUTPUT" '
        $NF==o { sub(":","",$1); print $1; exit }')

    local args=()
    [ -n "${idx:-}" ] && args=(-m "$idx")
    setsid -f conky -c "$CONF_DIR/left.conf"  "${args[@]}" >/dev/null 2>&1
    setsid -f conky -c "$CONF_DIR/right.conf" "${args[@]}" >/dev/null 2>&1
}

sleep 3   # let the monitor layout settle at login
launch_panels

# restart panels on monitor layout changes (debounced: drain the signal burst)
gdbus monitor --session \
      --dest org.gnome.Mutter.DisplayConfig \
      --object-path /org/gnome/Mutter/DisplayConfig 2>/dev/null \
| while read -r line; do
    case "$line" in
        *MonitorsChanged*)
            sleep 2
            while read -r -t 1 _; do :; done
            launch_panels
            ;;
    esac
done
