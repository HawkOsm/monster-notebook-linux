#!/usr/bin/env python3
import subprocess, os
from PIL import Image

W, H = 2560, 1600
SIZE = 900
SVG = os.path.expanduser("~/.local/share/wallpapers/anchor-compass.svg")
TMP = "/tmp/compass-render-4x.png"
OUT = os.path.expanduser("~/.local/share/wallpapers/anchor-compass-bg.png")

# Render SVG at 4x target size, then Lanczos-downsample for sharp output
subprocess.run([
    "convert", "-density", "384", "-background", "none",
    SVG, "-resize", f"{SIZE*4}x{SIZE*4}", TMP
], check=True)

fg = Image.open(TMP).convert("RGBA")
fg = fg.resize((SIZE, SIZE), Image.LANCZOS)

bg = Image.new("RGB", (W, H), (0, 0, 0))
x = (W - SIZE) // 2
y = (H - SIZE) // 2
bg.paste(fg, (x, y), fg)
bg.save(OUT, optimize=True)
print(f"Written: {OUT}")
