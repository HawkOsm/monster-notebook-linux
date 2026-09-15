# Bind Fn hotkeys under Hyprland

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 · Hyprland (Caelestia shell)
**Verified on:** Arch Linux · kernel 7.1.8 · `tuxedo-drivers` 4.22.2 ·
2026-08-13
**Symptom:** the keyboard backlight and touchpad-toggle `Fn` keys do nothing
under Hyprland, even though the driver is loaded and the same keys work under
GNOME.
**See also:** [why `tuxedo-drivers` reject Monster hardware](../explanation/why-tuxedo-drivers-reject-monster-hardware.md)

Bind the key events the driver already emits to commands that actually change
the hardware. GNOME's settings daemon does this for you; Hyprland does not, so
the events are delivered and then discarded.

## Before you start

The driver must be loaded first — see
[unlock the keyboard backlight and touchpad](unlock-keyboard-backlight-and-touchpad.md).

The touchpad toggle needs root for its `/dev/tuxedo_io` ioctl, so this setup
assumes passwordless `sudo` is configured for your user.

## Confirm the diagnosis

The keys emit standard events that nothing is consuming:

```bash
grep -A5 "TUXEDO Keyboard" /proc/bus/input/devices
```

On this board the driver maps them as follows:

| Physical key | Emitted event |
|---|---|
| Touchpad toggle | `KEY_F21` |
| Keyboard brightness up | `KEY_KBDILLUMUP` |
| Keyboard brightness down | `KEY_KBDILLUMDOWN` |
| Keyboard backlight toggle | `KEY_KBDILLUMTOGGLE` |

## Fix

### 1. Install the touchpad toggle helper

This flips the same EC flag the boot-time service writes, but on every
keypress rather than once at startup.

```python
#!/usr/bin/env python3
# /usr/local/bin/tuxedo-touchpad-toggle.py
import fcntl, ctypes, struct, sys

def _IOC(d, t, n, s): return (d << 30) | (s << 16) | (t << 8) | n
ptr = ctypes.sizeof(ctypes.c_void_p)
R_TP = _IOC(2, 0xED, 0x15, ptr)
W_TP = _IOC(1, 0xEE, 0x14, ptr)

try:
    fd = open("/dev/tuxedo_io", "rb+", buffering=0)
    buf = ctypes.create_string_buffer(8)
    fcntl.ioctl(fd, R_TP, buf)
    state = struct.unpack("i", buf[:4])[0]
    new_state = 0 if state else 1
    wb = ctypes.create_string_buffer(struct.pack("i", new_state) + b'\x00' * 4)
    fcntl.ioctl(fd, W_TP, wb)
    fd.close()
    print(new_state)
except Exception as e:
    print(f"touchpad toggle failed: {e}", file=sys.stderr)
    sys.exit(1)
```

```bash
sudo install -m 0755 tuxedo-touchpad-toggle.py /usr/local/bin/
```

### 2. Add the key bindings

Put these in `~/.config/caelestia/hypr-user.lua`, the shell's designated
user-override file, which `hyprland.lua` loads last.

```lua
local KBD_LED = "/sys/class/leds/rgb:kbd_backlight/brightness"
local KBD_LED_MAX = 255
local KBD_LED_STEP = 32

-- touchpad toggle: flips the same /dev/tuxedo_io EC flag Step 8 reads,
-- but live, on every keypress, instead of once at boot
hl.bind("F21", hl.dsp.exec_cmd(
    "bash -c 'S=$(sudo python3 /usr/local/bin/tuxedo-touchpad-toggle.py); " ..
    "notify-send -u low -i input-touchpad \"Touchpad\" \"$([ \"$S\" = 1 ] && echo Enabled || echo Disabled)\"'"
))

hl.bind("XF86KbdBrightnessUp", hl.dsp.exec_cmd(
    "bash -c 'v=$(cat " .. KBD_LED .. "); n=$((v+" .. KBD_LED_STEP .. ")); " ..
    "[ $n -gt " .. KBD_LED_MAX .. " ] && n=" .. KBD_LED_MAX .. "; " ..
    "echo $n | sudo tee " .. KBD_LED .. " >/dev/null'"
))

hl.bind("XF86KbdBrightnessDown", hl.dsp.exec_cmd(
    "bash -c 'v=$(cat " .. KBD_LED .. "); n=$((v-" .. KBD_LED_STEP .. ")); " ..
    "[ $n -lt 0 ] && n=0; echo $n | sudo tee " .. KBD_LED .. " >/dev/null'"
))

hl.bind("XF86KbdLightOnOff", hl.dsp.exec_cmd(
    "bash -c 'v=$(cat " .. KBD_LED .. "); " ..
    "if [ \"$v\" -gt 0 ]; then echo 0 | sudo tee " .. KBD_LED .. " >/dev/null; " ..
    "else echo " .. KBD_LED_MAX .. " | sudo tee " .. KBD_LED .. " >/dev/null; fi'"
))
```

`F21` and the `XF86Kbd*` names are Hyprland's standard XKB-derived keysym
names for those evdev codes. There is no modifier prefix because `Fn` is
consumed by the keyboard firmware and never reaches the OS as a separate
event — the keyboard sends the remapped key directly.

### 3. Reload

```bash
hyprctl reload
```

## Verify

```bash
hyprctl binds | grep -A6 "key: F21"
# expect: a live bind entry with modmask: 0
```

Repeat for `XF86KbdBrightnessUp` and the other keysyms. Physical `Fn` presses
cannot be tested from a shell session — press the keys by hand after
reloading.

## Roll back

Remove the bindings from `~/.config/caelestia/hypr-user.lua`, then:

```bash
hyprctl reload
sudo rm -f /usr/local/bin/tuxedo-touchpad-toggle.py
```

## Troubleshooting

**The bind appears in `hyprctl binds` but nothing happens**

The command runs as your user and writes to a root-owned sysfs path. Check
that passwordless `sudo` really is configured, by running the bound command
directly in a terminal.

**The touchpad toggles but no notification appears**

`notify-send` needs a running notification daemon. The bind itself is
unaffected.
