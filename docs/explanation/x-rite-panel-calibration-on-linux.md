# X-Rite panel calibration on Linux

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator), panel `TL160ADMP11-0`
(Thermotrex)
**Verified on:** Ubuntu 26.04 · colord · Argyll · DisplayCAL · 2026-05-13
**See also:** [assign an EDID color profile](../how-to/assign-an-edid-color-profile.md)

## In short

Without a colorimeter you cannot reproduce the Windows X-Rite calibration on
Linux. The factory ICC is not bundled in any downloadable installer — it lives
in the panel's EEPROM and is read at runtime by Windows tooling with no Linux
equivalent. The best free fallback is an EDID-derived profile, which is
informational only and applies no GPU LUT correction.

## Where the factory profile actually lives

The X-Rite Color Assistant ZIP from Monster's support page contains three
things that matter. It is served from:

`https://mnstr-support-files.s3.eu-central-1.amazonaws.com/Drivers/Tulpar Serisi/Tulpar T6/Tulpar T6 V2.1/Xrite Color Assistant.zip`


- `Monster_ProfileInstaller/ProfileInstaller.exe` and `ProfileInstaller.ini`
- `Monster_ProfileInstaller/RwI2CLibrary.dll`, a read/write-over-I2C library
- `Monster_XRiteColorAssistantSetup/XRiteColorAssistantSetup.exe`, about 41 MB

One line in `ProfileInstaller.ini` settles the question:

```ini
profile_loader_type = Eeprom
```

The ICC is stored on the panel's EEPROM, not in the installer. ProfileInstaller
reads it over I2C on first run and writes it to
`C:\DisplayProfiles\ColorCalibration_<Model><Serial>.zip`. Recursively
extracting the setup executable with `7z` yields no `.icm` or `.icc` files at
all — only Qt and MFC binaries.

Reading that EEPROM from Linux would mean knowing the vendor-specific DPCD
register addresses. The panel is eDP, so DDC/CI does not apply; access would go
through the DP AUX channel exposed at
`/sys/class/drm/card1-eDP-1/drm_dp_aux0`. That is undocumented
reverse-engineering territory.

## What the EDID-derived profile gives you

GNOME generates an ICC from the panel's EDID at first login and stores it in
`~/.local/share/icc/edid-<md5>.icc`. For this panel it is about 1.7 KB:

| Tag | Contents | Source |
|---|---|---|
| `desc` | panel description | EDID |
| `wtpt` | white point (D65) | EDID bytes 33–34 |
| `rXYZ`, `gXYZ`, `bXYZ` | primaries | EDID bytes 25–32 |
| `rTRC`, `gTRC`, `bTRC` | gamma curves, typically 2.2 | EDID byte 23 |
| `vcgt` | **absent** — no GPU LUT correction | — |

Color-managed applications read it and convert their output to the panel's
claimed gamut. Everything that does not read ICC profiles sees no change at
all.

## Why `dispwin` does not help either

Argyll's `dispwin` can load a profile's VCGT into the GPU LUT. Two things stop
it:

```text
$ dispwin -d 1 ~/.local/share/icc/edid-*.icc
Warning: ICC V4 not supported!
Warning: No vcgt tag found in profile - assuming linear
```

Argyll supports only ICC V2, and `lcms` generates V4 by default. Even if it
supported V4, the EDID profile has no VCGT tag — there is nothing to load.

## What would actually improve visible quality

The visible "Windows X-Rite quality" — accurate gray ramp, correct white
point, no color cast — comes from a VCGT loaded into the GPU LUT and derived
from measurements of the panel under known illumination. That needs hardware:

| Device | Approximate cost | Support |
|---|---|---|
| X-Rite i1Display Pro / Calibrite Display Pro | €200 | best Argyll support |
| Datacolor Spyder X / Pro | €150 | supported |
| ColorMunki (discontinued) | — | supported |

With one in hand, the workflow is short:

```bash
flatpak run net.displaycal.DisplayCAL
# → Calibrate & Profile → use defaults (D65, gamma 2.2, 120 cd/m²)
# → DisplayCAL writes ICC + VCGT, assigns via colord, loads VCGT into GPU LUT
# → Visible difference is immediate
```

Without one, the only wider-than-EDID option is an ICC measured on the same
panel by a review site such as Notebookcheck, TFTCentral or LaptopMedia. No
public profile for `TL160ADMP11-0` has been found.

## What was tried and ruled out

1. **Downloading the X-Rite Color Assistant installer to extract the ICC.**
   The installer reads from panel EEPROM. There is no ICC inside it.
2. **`colormgr import-profile` plus `device-make-profile-default`.** colord
   ends up wedged: the profile is registered on disk and with the daemon, but
   `device-get-default-profile` still returns "missing profile". Assigning it
   through GNOME Settings → Color works.
3. **`dispwin` to load the profile into the GPU LUT.** Fails on both counts
   above — ICC V4 unsupported, and no VCGT tag to load.
4. **`synthcal` and `targen` to generate a synthetic VCGT.** Argyll's
   measurement-flow tools need `.ti3` measurement input. `synthcal` produces a
   `.cal` but not a usable ICC without `targen` and `colprof`, which want
   measurement data themselves.

The tooling installed while establishing this — `colord`,
`gnome-color-manager`, `argyll` and the DisplayCAL flatpak — produces nothing
corrective without measurement hardware.

## Where the files live

| Path | Contents |
|---|---|
| `~/.local/share/icc/` | user ICC profile store |
| `/usr/share/color/icc/colord/` | system generic profiles (sRGB, AdobeRGB), assignable as a last-resort fallback |
| `/var/lib/colord/{mapping,storage}.db` | colord state databases — delete only if you understand the consequences |
