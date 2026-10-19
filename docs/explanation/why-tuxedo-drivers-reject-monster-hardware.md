# Why `tuxedo-drivers` reject Monster hardware

**Status:** verified
**Applies to:** every Monster SKU reporting a `MONSTER` DMI vendor string
**Verified on:** Ubuntu 24.04 · kernel 6.17+ · Arch Linux · kernel 7.1.8 ·
`tuxedo-drivers` 4.22.2 · 2026-08-13; Arch Linux · kernel 7.2.11 ·
`tuxedo-drivers` 4.25.0 · 2026-10-19
**See also:** [unlock the keyboard backlight and touchpad](../how-to/unlock-keyboard-backlight-and-touchpad.md)

## In short

`tuxedo-drivers` contains a compatibility gate that loads only on machines
whose DMI vendor string is exactly `TUXEDO`. Monster notebooks report
`MONSTER`, so the driver refuses to initialise and exits with `No such
device`. Everything the driver owns — keyboard backlight, fan control, the EC
interface — is unavailable until that check is patched, and one of the
casualties is a touchpad that can be left stranded in hardware.

## The DMI gate

Monster ships rebadged Clevo barebones, so the hardware underneath is exactly
what `tuxedo-drivers` was written for. The only thing standing between the two
is a string comparison in
`tuxedo_compatibility_check/tuxedo_compatibility_check.c`, which matches
`DMI_CHASSIS_VENDOR` against `TUXEDO`. Adding a second entry matching
`DMI_SYS_VENDOR` against `MONSTER` is the entire fix.

The failure is silent in the way that wastes the most time. `modprobe` reports
`No such device`, which reads like missing hardware rather than a refused
match — and the hardware is right there.

The gate grew between versions but not in a way that helps. In 4.25.0 the
table has three entries, matching `DMI_SYS_VENDOR`, `DMI_BOARD_VENDOR` and
`DMI_CHASSIS_VENDOR` against `TUXEDO`, and still nothing for `MONSTER`. A
source comment above it says "Going forward we only run the drivers on in
house tested devices". The same fix applies, and it is lost whenever an update
replaces the patched source tree.

On kernel 6.17 and later a second problem stacks on top: the kernel ships a
built-in `tuxedo_io` v0.3.9 while the DKMS package provides v0.3.6, so the two
collide on module version.

## Why the touchpad gets stuck, and why not always

Clevo boards keep a touchpad enable flag in the Embedded Controller, and it
survives reboots. The flag is written through `/dev/tuxedo_io` — a device node
that only exists once the driver loads. When the DMI gate blocks the driver,
a flag already sitting at `0` has nothing left that can set it back to `1`.
The touchpad is disabled in hardware, and the software that would re-enable it
is the software that cannot load.

This does not affect every board, and the difference matters when you are
diagnosing. On the Arch install the EC flag read `0` while the touchpad
worked perfectly throughout, because that machine's touchpad
(`FTCS1000:01 2808:0222`) is a generic `i2c_hid` device that is not gated
through `tuxedo_io` at all. Read the flag, but believe the touchpad.

## Why the Fn keys still do nothing under Hyprland

Once patched, the driver emits correct, standard Linux input events — verified
by decoding the `KEY=` bitmap for the `TUXEDO Keyboard` device in
`/proc/bus/input/devices` against `/usr/include/linux/input-event-codes.h`.

But `sparse_keymap` drivers only *report* an event. Something in userspace has
to act on it. GNOME's settings daemon does, which is why the backlight keys
work there with no configuration. Hyprland does not, so the events are
delivered and go nowhere. `tccd` does not listen to the device either —
checked, it holds no open file descriptor on the `event*` node — it only
manages brightness over UPower D-Bus once something tells it to.

That makes the fix compositor-level key bindings rather than anything driver
related. The mapping itself lives in the driver source, `clevo_keyboard.h`.
One quirk worth knowing: the touchpad toggle arrives as `KEY_F21`.
The driver source comments on this itself, calling it "the weirdly named
touchpad toggle key that is implemented as KEY_F21 everywhere (instead of
KEY_TOUCHPAD_TOGGLE or on/off)".

`Fn` never reaches the operating system as a separate modifier. The keyboard
firmware consumes it and sends the remapped key directly, which is why these
binds carry no modifier mask.
