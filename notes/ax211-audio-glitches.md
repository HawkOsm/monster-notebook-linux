# AX211 Bluetooth audio glitches

**Status:** open
**Applies to:** Intel AX211 + soundcore Liberty 4 Pro, Ubuntu 24.04
**Last worked on:** 2026-05-15
**See also:** [why the AX211 Bluetooth firmware crashes](../docs/explanation/ax211-bluetooth-firmware-crashes.md),
[AX211 Bluetooth configuration](../docs/reference/ax211-bluetooth-configuration.md)

Brief audio drops and quality loss on the headset, persisting after firmware
build 3243 stopped the chip crashing. Not the same problem as
`Hardware error 0x0c`, though it was found while chasing it.

> **Unresolved contradiction in the original notes.** One entry concludes the
> glitches were the headset's multipoint mode juggling laptop and phone, fixable
> in the Soundcore app rather than in Linux. Another, from the same day, records
> multipoint as ruled out because the headset was paired only to the PC. Both
> claims are preserved here as written. Settle this first if you pick the
> investigation back up — it decides whether there is a Linux-side problem at
> all.

## Ruled out

| Suspect | Evidence |
|---|---|
| Chip crashes | Firmware 3243 produced zero `Hardware error 0x0c` throughout audio testing |
| Range / signal strength | `bluetoothctl` reports RSSI −7 dBm and link quality 103 — near-touching |
| Two-device BR/EDR concurrency | Glitches persisted with the keyboard disconnected, headset alone on the chip |
| System-wide audio path | Internal speakers played clean; the Bluetooth path specifically is at fault |
| PipeWire underrun headroom | Quantum raised to 4096 (~85 ms) without fixing it |

## The puzzling part

The Liberty 4 Pro is LDAC-capable but advertises only SBC and SBC-XQ during
A2DP negotiation. WirePlumber offered LDAC, aptX HD, aptX and AAC during
testing and bluez registered the endpoints, but the headset refused them all.

## Not yet investigated

- Anker firmware limiting codec advertisement based on some other state — Game
  Mode or the ANC setting, for example.
- A2DP packet loss at RF level despite the −7 dBm signal: interference inside
  the chip's link manager that never surfaces as `Hardware error 0x0c`.
- A WirePlumber or PipeWire bug specific to 1.0.5 / 0.4.17 on Ubuntu 24.04 with
  this combination.
- The headset itself. Pair it to a different Linux machine to isolate.

## Where to start next time

Capture a `btmon` trace during playback and look for retransmits and dropped
SBC frames in Wireshark's Bluetooth dissector:

```bash
sudo btmon -t -w trace.btsnoop &
# play music for a minute, then analyse trace.btsnoop in Wireshark
```

## Other threads left open on this chip

**Disable the Bluetooth MSFT extension.** `dmesg` shows
`Failed to read MSFT supported features (-19)` and
`Bad flag given (0x1) vs supported (0x0)` on every reload. These are non-fatal,
but they suggest the host driver negotiates features the firmware rejects.
Check `modinfo btusb` for an `enable_msft` parameter, or similar, that forces
it off.

**An LTS kernel between 6.8 and 6.17.** Kernel 6.17 made the Bluetooth crashes
worse, which is why the system went back to 6.8. Something in between, such as
6.12 LTS, might carry `btusb`/`btintel` fixes without the 6.17 regression. Low
priority and an uncertain win.

**External 2.4 GHz interference audit.** 5 GHz Wi-Fi rules out in-chip
coexistence, but ambient noise can still corrupt Bluetooth. Candidates checked
and found absent at the time: nearby 2.4 GHz receiver dongles (the SHARKOON
mouse is wired; "2.4GHz Wireless" is just its product string), an active
USB 3.0 device next to the laptop (USB 3.0 emits around 2.4–2.5 GHz), and a
microwave running during keyboard sessions.
