# Fix: Steam Fails to Launch — "Missing X server or $DISPLAY"

**Symptom:** Steam silently exits, or the client UI never appears. `~/.local/share/Steam/logs/webhelper-linux.txt` contains:

```
pressure-vessel-wrap[...]: W: X11 socket /tmp/.X11-unix/X0 does not exist in filesystem, trying to use abstract socket instead.
[ERROR:ozone_platform_x11.cc(...)] Missing X server or $DISPLAY
[ERROR:env.cc(...)] The platform failed to initialize.  Exiting.
src/webhelper/html_chrome.cpp (...) : Assertion Failed: SDL_Init failed: No available video device
```

`xset q` from a regular terminal works fine, so the X server itself is healthy — only Steam's sandboxed `steamwebhelper` cannot reach it.

**Tested on:** Monster TULPAR T6 V2.1 · Ubuntu 24.04 · Kernel 6.17+ · Xorg session

---

## Why This Happens

Steam's `steamwebhelper` runs inside a **pressure-vessel** bubblewrap sandbox. From inside that sandbox, the X server's *abstract* unix socket (`@/tmp/.X11-unix/X0`) is not reachable — only the *filesystem* socket at `/tmp/.X11-unix/X0` is mounted into the bubble.

If anything has replaced `/tmp/.X11-unix/X0` with a broken symlink (or removed it entirely after Xorg created it), pressure-vessel falls back to the abstract socket, fails to reach it, and `steamwebhelper` exits with "Missing X server".

A common — and **wrong** — workaround that causes exactly this is to add a user-systemd unit or `tmpfiles.d` drop-in that does:

```
ln -sf X1 /tmp/.X11-unix/X0      # WRONG — clobbers the real X0 socket
```

The `-f` flag unlinks Xorg's real socket file and replaces it with a symlink to a non-existent `X1`. Every login it runs again. This is the trap to avoid.

---

## Step 1 — Find Anything That Touches `/tmp/.X11-unix/`

```bash
grep -rEn 'X11-unix|/tmp/\.X' \
  /etc/tmpfiles.d/ \
  /etc/systemd/user/ \
  /etc/xdg/autostart/ \
  ~/.config/autostart/ \
  ~/.config/systemd/user/ 2>/dev/null
```

A typical bad match looks like:

```
~/.config/systemd/user/steam-x11-x0-symlink.service:9:ExecStart=/usr/bin/ln -sf X1 /tmp/.X11-unix/X0
```

## Step 2 — Disable and Remove the Bad Unit

```bash
systemctl --user stop    steam-x11-x0-symlink.service
systemctl --user disable steam-x11-x0-symlink.service
rm -f ~/.config/systemd/user/steam-x11-x0-symlink.service
rm -f ~/.config/systemd/user/graphical-session.target.wants/steam-x11-x0-symlink.service
systemctl --user daemon-reload
```

If the offender was a `tmpfiles.d` drop-in instead, remove it from `/etc/tmpfiles.d/` (sudo) and also any matching live entry the same way.

## Step 3 — Remove the Broken Symlink

```bash
ls -la /tmp/.X11-unix/
# X0 should be a unix socket (type 's'). If it is a dangling symlink, delete it:
rm -f /tmp/.X11-unix/X0
```

## Step 4 — Get a Working Socket Back

Pick **one** of the two options below.

### 4A — Clean: log out and back in (recommended)

The X server creates `/tmp/.X11-unix/X0` as a fresh unix socket on every session start. Logging out and back in restores the correct state with no further action. Since the bad unit is now gone, the socket will not be clobbered again.

### 4B — No relog: run a userland AF_UNIX proxy

If you cannot log out right now (e.g. there are unsaved windows), bind a fresh filesystem socket at `/tmp/.X11-unix/X0` and forward it to the abstract socket Xorg is still listening on.

Save the following as `~/.local/bin/x11-fs-proxy.py`:

```python
#!/usr/bin/env python3
"""Bind /tmp/.X11-unix/X0 (filesystem) and forward to the X server's
abstract socket @/tmp/.X11-unix/X0. Restores filesystem-path access
to Xorg when the real X0 dentry has been clobbered (e.g. overwritten
by a stray `ln -sf`). Run only for the current X session; the next
login recreates the real socket and this proxy is no longer needed."""
import os
import socket
import sys
import threading

LISTEN_PATH = "/tmp/.X11-unix/X0"
ABSTRACT_PATH = "\x00/tmp/.X11-unix/X0"

def pump(src, dst):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for s, how in ((src, socket.SHUT_RD), (dst, socket.SHUT_WR)):
            try: s.shutdown(how)
            except OSError: pass

def handle(client):
    upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        upstream.connect(ABSTRACT_PATH)
    except OSError as e:
        sys.stderr.write(f"[xproxy] upstream connect failed: {e}\n")
        client.close()
        return
    threading.Thread(target=pump, args=(client, upstream), daemon=True).start()
    threading.Thread(target=pump, args=(upstream, client), daemon=True).start()

def main():
    try: os.unlink(LISTEN_PATH)
    except FileNotFoundError: pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        srv.bind(LISTEN_PATH)
    except OSError as e:
        sys.stderr.write(f"[xproxy] bind failed at {LISTEN_PATH}: {e}\n")
        sys.exit(1)
    os.chmod(LISTEN_PATH, 0o777)
    srv.listen(128)
    sys.stderr.write(f"[xproxy] listening on {LISTEN_PATH} -> @{LISTEN_PATH}\n")
    sys.stderr.flush()
    while True:
        c, _ = srv.accept()
        threading.Thread(target=handle, args=(c,), daemon=True).start()

if __name__ == "__main__":
    main()
```

Run it detached:

```bash
chmod +x ~/.local/bin/x11-fs-proxy.py
setsid nohup python3 ~/.local/bin/x11-fs-proxy.py >/tmp/x11-fs-proxy.log 2>&1 </dev/null &
disown
```

> **Do not** wire this proxy into autostart, login scripts, or systemd. It is only a session-scoped rescue. On a clean login Xorg creates the real socket itself; the proxy clobbering it would reintroduce the original problem.

---

## Verify

```bash
# Filesystem socket exists and is a real unix socket (type 's')
ls -la /tmp/.X11-unix/X0

# Raw connect succeeds
python3 -c 'import socket; s=socket.socket(socket.AF_UNIX); s.connect("/tmp/.X11-unix/X0"); print("ok")'

# X clients work via the filesystem path
DISPLAY=unix:0 xset q | head -3

# Launch Steam
/usr/games/steam steam://open/main &
tail -f ~/.local/share/Steam/logs/webhelper-linux.txt
```

Steam is healthy when the log shows lines like `Add STEAM_GAME to kAtomsToCache` and `Desktop state changed: ... size: WxH` and **no** "Missing X server" / "SDL_Init failed" errors.

---

## Troubleshooting

**`/tmp/.X11-unix/X0` is back as a broken symlink after a reboot.**

A unit reintroducing it is still active. Re-run Step 1; check `systemctl --user list-unit-files | grep -i x11` and `find /etc/tmpfiles.d -iname '*x11*' -o -iname '*steam*'`.

**Xorg is not running (Wayland session).**

This guide assumes an Xorg session — `loginctl show-session $XDG_SESSION_ID -p Type` should report `Type=x11`. On a Wayland session, Steam talks to Xwayland and the socket lives at a different path; this fix does not apply.

**Steam still fails after the proxy is up.**

Check pressure-vessel sees the new socket — restart Steam fully (`pkill -f steam` then relaunch) so a new bubblewrap mount snapshots the now-real `/tmp/.X11-unix/X0`.
