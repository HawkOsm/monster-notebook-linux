# Assign an EDID color profile

**Status:** mitigated
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator), panel `TL160ADMP11-0`
**Verified on:** Ubuntu 26.04 · GNOME · colord · 2026-05-13
**Symptom:** the panel runs with no color profile assigned, and
color-managed applications have nothing to convert against.
**See also:** [X-Rite panel calibration on Linux](../explanation/x-rite-panel-calibration-on-linux.md)

Assign the EDID-derived ICC that GNOME generates automatically. This is the
best you can do without a colorimeter, and it is informational only — there is
no GPU LUT correction in it. Read the explanation first if you were expecting
to reproduce the Windows X-Rite calibration; you cannot.

## Before you start

Adjust `card1-eDP-1` throughout to match your panel:

```bash
ls /sys/class/drm/ | grep eDP
```

## Confirm the diagnosis

```bash
DEV=$(colormgr get-devices | grep -oE '/org/freedesktop/ColorManager/devices/xrandr[^ ]+' | head -1)
colormgr device-get-default-profile "$DEV"
# expect: missing profile, if nothing is assigned yet
```

```bash
ls -la ~/.local/share/icc/edid-*.icc
```

GNOME writes that file at first login. If it is absent, log out and back in.

## Fix

### 1. Import the profile and make it the default

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

`colormgr import-profile` is asynchronous. It may report "profile id does not
exist" or "The profile was not added in time" even when the profile is on disk
and registered. Restart the session daemon and retry:

```bash
systemctl --user restart colord-session
```

If colord stays wedged, open **Settings → Color** in GNOME and pick the
profile from the list. That is the most reliable way to assign it.

## Verify

```bash
DEV=$(colormgr get-devices | grep -oE '/org/freedesktop/ColorManager/devices/xrandr[^ ]+' | head -1)
colormgr device-get-default-profile "$DEV"
# expect: the edid- profile rather than "missing profile"
```

## Roll back

```bash
DEV=$(colormgr get-devices | grep -oE '/org/freedesktop/ColorManager/devices/xrandr[^ ]+' | head -1)
colormgr device-remove-profile "$DEV" "$PROF"
```

## Trade-offs

The profile is informational. Color-managed applications — Krita, GIMP,
Darktable, RawTherapee, Firefox with color management enabled — read it and
convert their output to the panel's claimed gamut. Everything else, including
most of the desktop UI, terminals and unmanaged browser tabs, is unaffected.

It carries no `vcgt` tag, so nothing is loaded into the GPU LUT and the
visible gray ramp and white point do not change. Only a measured profile from
a colorimeter does that.

## Troubleshooting

**Identify the panel**

```bash
edid-decode < /sys/class/drm/card1-eDP-1/edid | head -30
# expect: a "Display Product Name" line giving the panel model
```

**Check the EDID MD5 matches the profile filename**

```bash
md5sum /sys/class/drm/card1-eDP-1/edid
```

**Check the panel reports sane chromaticities**

```bash
edid-decode < /sys/class/drm/card1-eDP-1/edid | grep -A4 "Chromaticity"
```
