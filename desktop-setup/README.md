# Desktop setup — Conky + Wallpaper + Theme

Backup of the GNOME desktop look (conky dashboards + wallpaper + theme) so it
can be restored after a fresh Ubuntu install. Saved 2026-05-22, conky backend
reworked 2026-07-09.

## Contents

- `conky/left.conf`, `conky/right.conf` — the two conky configs (`~/.config/conky/`).
- `conky/conky-start.sh` — **the single conky backend script** (`~/.local/bin/`).
  Launches both panels pinned to the built-in display (`eDP-1`), then watches
  GNOME's `Mutter.DisplayConfig` D-Bus for monitor-layout changes and relaunches
  them so they never drift to the wrong screen when an external display is
  (un)plugged. Replaced the old per-panel autostart entries + separate watcher
  script on 2026-07-09 — with the old approach the right panel kept getting lost.
- `conky/conky.desktop` — the one autostart entry (`~/.config/autostart/`)
  that runs `conky-start.sh` at login.
- `wallpaper/anchor-compass-bg.png` — desktop background.
- `wallpaper/anchor-compass.svg` + `wallpaper/gen-wallpaper.py` — source SVG and
  the script that renders the PNG (regenerate with `python3 gen-wallpaper.py`).
- `wallpaper/lockscreen-geometric.jpg` — lock-screen / screensaver background.

## Theme (not files in this repo — install from upstream)

The desktop uses a grey monochrome look, not stock Yaru:

- GTK + Shell theme: **Graphite-Dark** — [vinceliuice/Graphite-gtk-theme](https://github.com/vinceliuice/Graphite-gtk-theme)
- Icons: **Tela-circle-black-dark** — [vinceliuice/Tela-circle-icon-theme](https://github.com/vinceliuice/Tela-circle-icon-theme)

```bash
gsettings set org.gnome.desktop.interface gtk-theme  'Graphite-Dark'
gsettings set org.gnome.shell.extensions.user-theme name 'Graphite-Dark'
gsettings set org.gnome.desktop.interface icon-theme 'Tela-circle-black-dark'
```

## Restore after a fresh install

```bash
sudo apt install -y conky-all

# Conky configs + backend script + autostart
mkdir -p ~/.config/conky ~/.config/autostart ~/.local/bin
cp conky/left.conf conky/right.conf ~/.config/conky/
cp conky/conky-start.sh ~/.local/bin/ && chmod +x ~/.local/bin/conky-start.sh
cp conky/conky.desktop ~/.config/autostart/

# Wallpapers
mkdir -p ~/.local/share/wallpapers ~/.local/share/backgrounds
cp wallpaper/anchor-compass-bg.png wallpaper/anchor-compass.svg wallpaper/gen-wallpaper.py ~/.local/share/wallpapers/
cp wallpaper/lockscreen-geometric.jpg ~/.local/share/backgrounds/

# Apply wallpaper (desktop = light + dark, plus lock screen)
gsettings set org.gnome.desktop.background picture-uri      "file://$HOME/.local/share/wallpapers/anchor-compass-bg.png"
gsettings set org.gnome.desktop.background picture-uri-dark "file://$HOME/.local/share/wallpapers/anchor-compass-bg.png"
gsettings set org.gnome.desktop.screensaver picture-uri     "file://$HOME/.local/share/backgrounds/lockscreen-geometric.jpg"
```

Log out/in (or run `~/.local/bin/conky-start.sh` once) to bring up the panels.

Panels target the laptop's built-in `eDP-1` output; to pin them elsewhere set
`CONKY_OUTPUT` (e.g. `CONKY_OUTPUT=HDMI-1`) in the desktop entry's `Exec`.
