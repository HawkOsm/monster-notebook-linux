# AX211 Bluetooth configuration

**Status:** verified
**Applies to:** Intel AX211 combo card on Ubuntu with bluez, PipeWire and
WirePlumber
**Verified on:** Ubuntu 24.04 · bluez · PipeWire 1.0.5 · WirePlumber 0.4.17 ·
2026-05-15
**See also:** [pin stable AX211 Bluetooth firmware](../how-to/pin-stable-ax211-bluetooth-firmware.md),
[why the AX211 Bluetooth firmware crashes](../explanation/ax211-bluetooth-firmware-crashes.md)

The bluez, WirePlumber and PipeWire settings applied on the Ubuntu install.
None of these fix the chip-level `Hardware error 0x0c` crashes — they reduce
how badly each crash is amplified by userspace.

These have **not** been ported to the Arch install, where all four files are
stock. Port them if a Bluetooth keyboard or headset shows the same reconnect
flakiness.

## `/etc/bluetooth/main.conf`

```ini
[General]
FastConnectable = true
AutoEnable = true
ReconnectUUIDs = 00001124-0000-1000-8000-00805f9b34fb  # HID profile (was missing — fixed 2026-05-12)
ReconnectAttempts = 7
ReconnectIntervals = 1, 2, 4, 8, 16, 32, 64
```

## `/etc/bluetooth/input.conf`

```ini
[General]
IdleTimeout = 15        # was 0 (never disconnect on idle), bumped to 15 min 2026-05-13
UserspaceHID = true
ClassicBondedOnly = false
```

`IdleTimeout = 0` means *never* disconnect on idle, so raising it to 15 is
technically a regression. In practice the disconnects here are firmware
crashes rather than idle-driven, so the difference is zero.

## `/etc/systemd/system/bluetooth.service.d/disable-sap.conf`

Runs `bluetoothd` with `--noplugin=sap`, because the SAP plugin was crashing at
startup.

## `~/.config/wireplumber/bluetooth.lua.d/51-bluez-override.lua`

Strips HSP and HFP entirely so WirePlumber never claims the "Hands-Free Voice
gateway" profile when a headset connects. Without it, every headset connection
produced this cascade:

```text
bluetoothd: Unable to get io data for Hands-Free Voice gateway: getpeername: Transport endpoint is not connected (107)
dbus-daemon: Rejected send message ... bluetoothd ... wireplumber
bluetoothd: a2dp_select_capabilities() Unable to select SEP
bluetoothd: a2dp-sink profile connect failed: Device or resource busy
gnome-shell: Failed to connect device "soundcore Liberty 4 Pro": br-connection-page-timeout
```

The cause is a WirePlumber/bluez race when negotiating two profiles at once.
bluez exposes both A2DP and HFP, WirePlumber claims both, bluetoothd refuses
the HFP claim, and the A2DP transport ends up busy because the link is
half-torn-down. A2DP-only avoids the race.

The file also sets a codec preference list, so WirePlumber offers LDAC,
aptX HD, aptX, AAC, SBC-XQ and SBC during AVDTP negotiation and the device
picks what it supports. The rules deliberately do **not** force
`device.profile`, so `pactl set-card-profile … a2dp-sink-sbc_xq` can still flip
the codec by hand — pause audio first, since some headsets disconnect when the
codec changes mid-stream.

```lua
bluez_monitor.properties["bluez5.roles"]              = "[ a2dp_sink a2dp_source ]"
bluez_monitor.properties["bluez5.autoswitch-profile"] = false
bluez_monitor.properties["bluez5.hfphsp-backend"]     = "none"
bluez_monitor.properties["bluez5.codecs"]             = "[ ldac aptx_hd aptx aac sbc_xq sbc ]"
bluez_monitor.properties["bluez5.a2dp.ldac.quality"]  = "auto"

bluez_monitor.rules = {
  { matches = { { { "device.name", "matches", "bluez_card.*" } } },
    apply_properties = {
      ["bluez5.auto-connect"] = "[ a2dp_sink ]",
    } },
}
```

**Trade-off:** the headset microphone becomes unusable, since HSP/HFP is the
only Bluetooth microphone protocol. Listening only.

A backup of the pre-fix file is kept as `51-bluez-override.lua.bak.<timestamp>`.

After editing, run `systemctl --user restart wireplumber`, then disconnect and
reconnect the headset.

## `~/.config/pipewire/pipewire.conf.d/99-bt-audio-stability.conf`

Raises the PipeWire clock quantum from the default 1024 frames (about 21 ms at
48 kHz) to 2048 frames (about 43 ms), with a 1024–8192 range. This is the most
effective mitigation for AX211 Bluetooth audio glitches short of changing
hardware: a brief `Hardware error 0x0c` blip blanks audio in under one default
quantum, while two quanta give the recovery path time to refill before the
underrun becomes audible.

```ini
context.properties = {
    default.clock.quantum       = 2048
    default.clock.min-quantum   = 1024
    default.clock.max-quantum   = 8192
}
```

**Trade-off:** about 80 ms of extra output latency on the Bluetooth path.
Imperceptible for music and video, unsuitable for live monitoring or twitch
gaming.

To revert:

```bash
rm ~/.config/pipewire/pipewire.conf.d/99-bt-audio-stability.conf
systemctl --user restart pipewire
```

## Restoring stock configuration

`/etc/bluetooth/main.conf` and `input.conf` are conffiles, so
`sudo apt install --reinstall bluez` restores the defaults. Remove
`/etc/systemd/logind.conf.d/01-no-auto-suspend.conf` and restart
`systemd-logind` to restore default lid and idle suspend behaviour.
