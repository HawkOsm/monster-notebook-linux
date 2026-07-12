# Display Color Calibration (X-Rite Pantone Panel) — Linux Reality Check

The Tulpar T6 V2.1 AI Creator ships with an X-Rite Pantone-certified display
panel (`TL160ADMP11-0`, vendor: Thermotrex) and the **X-Rite Color Assistant**
software on Windows. On Linux that software does not exist and the panel
runs without its factory calibration profile loaded. This file documents
exactly what is — and is not — possible to do about it.

## TL;DR

Without a colorimeter, you **cannot** reproduce the Windows X-Rite calibration
on Linux. The factory ICC is not bundled in any downloadable installer; it
lives in the panel's EEPROM, read at runtime by Windows tooling that has no
Linux equivalent. The best free fallback is an EDID-derived ICC profile,
which is informational only (no GPU LUT correction).

## Where the Factory Profile Actually Lives

The X-Rite Color Assistant ZIP from Monster's support page
(`https://mnstr-support-files.s3.eu-central-1.amazonaws.com/Drivers/Tulpar Serisi/Tulpar T6/Tulpar T6 V2.1/Xrite Color Assistant.zip`)
contains:

- `Monster_ProfileInstaller/ProfileInstaller.exe` + `ProfileInstaller.ini`
- `Monster_ProfileInstaller/RwI2CLibrary.dll` (read/write over I2C)
- `Monster_XRiteColorAssistantSetup/XRiteColorAssistantSetup.exe` (~41 MB)

The critical line in `ProfileInstaller.ini`:

```ini
profile_loader_type = Eeprom
```

The factory ICC is **stored on the panel's EEPROM**, not in the installer.
ProfileInstaller reads the profile over I2C at first run and writes it to
`C:\DisplayProfiles\ColorCalibration_<Model><Serial>.zip`. Recursively
extracting `XRiteColorAssistantSetup.exe` (with `7z`) yields **no embedded
`.icm` or `.icc` files** — only Qt/MFC binaries.

Reading the panel EEPROM from Linux would require knowing the vendor-specific
DPCD register addresses (the panel is connected via eDP, so DDC/CI is not
applicable — access is via the DP AUX channel exposed at
`/sys/class/drm/card1-eDP-1/drm_dp_aux0`). This is reverse-engineering
territory and is not documented publicly.

## What the EDID-Derived Profile Gives You

GNOME automatically generates an EDID-derived ICC at first login and stores
it in `~/.local/share/icc/edid-<md5>.icc`. For the TL160ADMP11-0 panel this
file is ~1.7 KB and contains:

- `desc` — panel description
- `wtpt` — white point (D65, from EDID bytes 33-34)
- `rXYZ`, `gXYZ`, `bXYZ` — primaries (from EDID bytes 25-32)
- `rTRC`, `gTRC`, `bTRC` — gamma curves (from EDID byte 23, typically 2.2)
- **No `vcgt` tag** — no GPU LUT correction

This profile is purely **informational**. Color-managed applications (Krita,
GIMP, Darktable, Firefox with color management enabled, RawTherapee) will
read it and convert their output to match the panel's claimed gamut. Apps
that don't read ICC profiles (most of the desktop UI, terminal, unmanaged
browser tabs) see no change.

## Assigning the EDID Profile via colord (Best Effort)

```bash
PROF_FILE="$HOME/.local/share/icc/edid-$(cat /sys/class/drm/card1-eDP-1/edid | md5sum | awk '{print $1}').icc"
colormgr import-profile "$PROF_FILE"

DEV=$(colormgr get-devices | grep -oE '/org/freedesktop/ColorManager/devices/xrandr[^ ]+' | head -1)
# Profile path uses the file's own MD5, not the EDID MD5
PROF_MD5=$(md5sum "$PROF_FILE" | awk '{print $1}')
PROF="/org/freedesktop/ColorManager/profiles/icc_${PROF_MD5}_$(whoami)_$(id -u)"

colormgr device-add-profile "$DEV" "$PROF"
colormgr device-make-profile-default "$DEV" "$PROF"
```

Note: `colormgr import-profile` is asynchronous. The daemon sometimes returns
"profile id does not exist" or "The profile was not added in time" even when
the profile is on disk and registered. A `systemctl --user restart
colord-session` plus a 2-second sleep usually fixes it. If the colord state
is wedged, opening **Settings → Color** in GNOME and picking the profile from
the GUI is the most reliable assignment method.

## Why `dispwin` Doesn't Help Either

Argyll's `dispwin` can load a profile's VCGT into the GPU LUT. Two problems:

```
$ dispwin -d 1 ~/.local/share/icc/edid-*.icc
Warning: ICC V4 not supported!
Warning: No vcgt tag found in profile - assuming linear
```

1. **Argyll only supports ICC V2**, and `lcms` generates V4 by default.
2. **The EDID profile has no VCGT tag** — there is nothing for `dispwin` to
   load even if V4 were supported.

## What Would Actually Improve Visible Quality

The visible "Windows X-Rite quality" — accurate gray ramp, correct white
point, no color cast — comes from a **VCGT** loaded into the GPU LUT, derived
from per-pixel measurements of the panel under known illumination. This
requires hardware:

- **X-Rite i1Display Pro / Calibrite Display Pro** (~€200) — best Argyll support
- **Datacolor Spyder X / Pro** (~€150) — supported
- Older **ColorMunki** units — supported but discontinued

Workflow once you have a colorimeter:

```bash
flatpak run net.displaycal.DisplayCAL
# → Calibrate & Profile → use defaults (D65, gamma 2.2, 120 cd/m²)
# → DisplayCAL writes ICC + VCGT, assigns via colord, loads VCGT into GPU LUT
# → Visible difference is immediate
```

Without a colorimeter, the only "wider-than-EDID" path is to download an ICC
measured on the same panel by a review site (Notebookcheck, TFTCentral,
LaptopMedia). At the time of this writing, no public ICC for the
`TL160ADMP11-0` panel has been located. If Notebookcheck reviews the Tulpar
T6 V2.1 in the future, their downloadable profile would be a reasonable
substitute.

## Tools Installed in This Session (2026-05-13)

```bash
sudo apt install colord gnome-color-manager argyll
flatpak install flathub net.displaycal.DisplayCAL
```

All three apt packages were already present. DisplayCAL flatpak was newly
installed. None of them produces a corrective profile without measurement
hardware.

## What Was Tried and Ruled Out (2026-05-13)

1. **Downloading the X-Rite Color Assistant installer to extract the ICC** —
   installer reads from panel EEPROM, no ICC inside.
2. **`colormgr import-profile` + `device-make-profile-default`** — colord
   state ends up wedged: profile registered on disk and via daemon, but
   `device-get-default-profile` returns "missing profile". The file in
   `~/.local/share/icc/` is correctly placed and GNOME Settings → Color
   should be able to pick it manually.
3. **`dispwin` to load profile into GPU LUT** — fails: ICC V4 unsupported and
   no VCGT tag in profile.
4. **`synthcal` + `targen` to generate a synthetic VCGT** — Argyll's
   measurement-flow tools require `.ti3` measurement input; `synthcal`
   produces a `.cal` but not a usable ICC without targen+colprof, which
   themselves want measurement data.

## Diagnostic Commands

```bash
# Identify the panel
edid-decode < /sys/class/drm/card1-eDP-1/edid | head -30
# Look for "Display Product Name" line — gives panel model

# List GNOME-auto-generated EDID profiles
ls -la ~/.local/share/icc/edid-*.icc

# Verify EDID MD5 matches the profile
md5sum /sys/class/drm/card1-eDP-1/edid
# → should match the filename suffix

# Check if any profile is assigned to the panel
DEV=$(colormgr get-devices | grep -oE '/org/freedesktop/ColorManager/devices/xrandr[^ ]+' | head -1)
colormgr device-get-default-profile "$DEV"

# Verify the panel actually reports sane chromaticities in EDID
edid-decode < /sys/class/drm/card1-eDP-1/edid | grep -A4 "Chromaticity"
```

## Useful Reference

- `~/.local/share/icc/` — user ICC profile store
- `/usr/share/color/icc/colord/` — system-provided generic profiles
  (sRGB, AdobeRGB, etc.) — assignable as last-resort fallback
- `/var/lib/colord/{mapping,storage}.db` — colord state DBs (delete only
  if you understand the consequences)
