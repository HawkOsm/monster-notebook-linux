# Desktop setup — Conky + Wallpaper

Backup of the GNOME desktop look (conky dashboards + wallpaper) so it can be
restored after a fresh Ubuntu install. Saved 2026-05-22.

## Contents
- `conky/left.conf`, `conky/right.conf` — the two conky configs (`~/.config/conky/`).
- `conky/conky-daily.desktop`, `conky/conky-right.desktop` — autostart launchers
  (`~/.config/autostart/`). They poll `xdpyinfo -display :0` until Xwayland is ready,
  then launch conky with the matching config (needed on Wayland so conky doesn't
  start before the display is up).
- `wallpaper/anchor-compass-bg.png` — current desktop background.
- `wallpaper/anchor-compass.svg` + `wallpaper/gen-wallpaper.py` — source SVG and the
  script that renders the PNG (regenerate with `python3 gen-wallpaper.py`).
- `wallpaper/lockscreen-geometric.jpg` — lock-screen / screensaver background.

## Restore after a fresh install
```bash
sudo apt install -y conky-all

# Conky configs + autostart
mkdir -p ~/.config/conky ~/.config/autostart
cp conky/left.conf conky/right.conf            ~/.config/conky/
cp conky/conky-daily.desktop conky/conky-right.desktop ~/.config/autostart/

# Wallpapers
mkdir -p ~/.local/share/wallpapers ~/.local/share/backgrounds
cp wallpaper/anchor-compass-bg.png wallpaper/anchor-compass.svg wallpaper/gen-wallpaper.py ~/.local/share/wallpapers/
cp wallpaper/lockscreen-geometric.jpg ~/.local/share/backgrounds/

# Apply wallpaper (desktop = light + dark, plus lock screen)
gsettings set org.gnome.desktop.background picture-uri      "file://$HOME/.local/share/wallpapers/anchor-compass-bg.png"
gsettings set org.gnome.desktop.background picture-uri-dark "file://$HOME/.local/share/wallpapers/anchor-compass-bg.png"
gsettings set org.gnome.desktop.screensaver picture-uri     "file://$HOME/.local/share/backgrounds/lockscreen-geometric.jpg"
```
Log out/in (or run the autostart `Exec` once) to bring up the conky dashboards.
