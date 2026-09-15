# Keyboard backlight controls

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator), RGB zone keyboard
**Verified on:** Ubuntu 24.04 · `tuxedo-drivers` 4.22.2 ·
`tuxedo-control-center` 3.0.4 · 2026-08-13
**See also:** [unlock the keyboard backlight and touchpad](../how-to/unlock-keyboard-backlight-and-touchpad.md)

Where the backlight controls are, and how to drive them by hand. Everything
here assumes the driver is already loaded.

## Where the control lives in TUXEDO Control Center

The slider, RGB colour picker and per-zone selector are **not** on the TCC
dashboard. They are under **TCC sidebar → Tools → Keyboard Backlight**.
`keyboardBacklightControlEnabled` lives in **Global Settings**; leave it on.

Confirm `tccd` detected the keyboard:

```bash
journalctl -u tccd | grep -i KeyboardBacklight
# Expect:
#   KeyboardBacklightListener: Detected RGB zone keyboard backlight
#   KeyboardBacklightListener: initUPower: Using /org/freedesktop/UPower/KbdBacklight
```

TCC drives the LED through the UPower D-Bus interface rather than sysfs
directly:

```bash
gdbus call --system --dest org.freedesktop.UPower \
  --object-path /org/freedesktop/UPower/KbdBacklight \
  --method org.freedesktop.UPower.KbdBacklight.GetMaxBrightness   # → (255,)
gdbus call --system --dest org.freedesktop.UPower \
  --object-path /org/freedesktop/UPower/KbdBacklight \
  --method org.freedesktop.UPower.KbdBacklight.GetBrightness      # → (current,)
```

## Manual backlight control

```bash
# Check current brightness (0–255)
cat /sys/class/leds/rgb:kbd_backlight/brightness

# Set brightness (replace 200 with any value 0–255)
echo 200 | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness

# Turn off
echo 0 | sudo tee /sys/class/leds/rgb:kbd_backlight/brightness
```

Hold `Fn` for the hardware shortcuts. These work out of the box under GNOME;
under Hyprland they need
[binding by hand](../how-to/bind-fn-hotkeys-under-hyprland.md).

| Keys | Action |
|------|--------|
| `Fn` + `/` | Toggle backlight on/off |
| `Fn` + `*` | Cycle colors |
| `Fn` + `+` | Brightness up |
| `Fn` + `-` | Brightness down |
