# Clevo Linux fixes

Unofficial field guides for running Linux on Clevo/TONGFANG-based notebooks,
verified on Monster hardware. Every fix here was hit, diagnosed and verified
on real hardware. Monster ships rebadged Clevo barebones, so most of this
applies equally to TUXEDO, XMG/Schenker, System76 and other machines built on
the same shells.

> **Unofficial community project.** Not affiliated with, sponsored by or
> endorsed by Monster Notebook, TUXEDO Computers or Clevo. Monster, TULPAR,
> ABRA, TUXEDO and all other product names, logos and trademarks belong to
> their respective owners and are used here only to identify the hardware and
> software these notes apply to.

**Machines behind this repository:**

- **Monster TULPAR T6 V2.1 AI Creator** — Ubuntu 26.04, kernel 7.0 (daily
  driver)
- **Monster TULPAR T6 V2.1 AI Creator** — same hardware, Arch Linux +
  Hyprland, kernel 7.2
- **Monster ABRA A5 V20.2** — Ubuntu 22.04, kernel 6.8

## Find your problem

| Symptom | Guide |
|---|---|
| Keyboard backlight dead, touchpad locked at hardware level | [unlock the keyboard backlight and touchpad](docs/how-to/unlock-keyboard-backlight-and-touchpad.md) |
| **Machine hard-freezes at random — no logs, only a power cycle helps** | [stop random hard freezes from PCIe ASPM](docs/how-to/stop-random-hard-freezes-from-pcie-aspm.md) |
| Bluetooth peripherals crash-disconnect (Intel AX211, `Hardware error 0x0c`) | [pin stable AX211 Bluetooth firmware](docs/how-to/pin-stable-ax211-bluetooth-firmware.md) |
| `nvidia-smi` fails after a kernel upgrade | [restore NVIDIA after a kernel upgrade](docs/how-to/restore-nvidia-after-a-kernel-upgrade.md) |
| dGPU never idles on battery (Hyprland, hybrid graphics) | [idle the dGPU on battery under Hyprland](docs/how-to/idle-the-dgpu-on-battery-under-hyprland.md) |
| Login screen comes up black on some boots (hybrid graphics, Wayland) | [fix a black GDM greeter](docs/how-to/fix-a-black-gdm-greeter.md) |
| `pcieport … D3cold to D0` spam in the journal | [silence Thunderbolt D3cold log spam](docs/how-to/silence-thunderbolt-d3cold-log-spam.md) |
| `iw reg get` shows `country 00`, `set-wireless-regdom failed with exit code 1` in the journal (Arch) | [set the Wi-Fi regulatory domain](docs/how-to/set-the-wifi-regulatory-domain.md) |
| TUXEDO Control Center shows no fan or temperature (ABRA A5) | [show fan and temperature in TUXEDO Control Center](docs/how-to/show-fan-and-temperature-in-tuxedo-control-center.md) |
| Power-profile switcher in a custom shell does nothing | [switch power profiles from a custom shell](docs/how-to/switch-power-profiles-from-a-custom-shell.md) |
| `Fn` hotkeys dead under Hyprland | [bind Fn hotkeys under Hyprland](docs/how-to/bind-fn-hotkeys-under-hyprland.md) |
| Want a terminal thermal dashboard | [install the thermal dashboard](docs/how-to/install-the-thermal-dashboard.md) |
| Panel color looks wrong next to the Windows X-Rite profile | [assign an EDID color profile](docs/how-to/assign-an-edid-color-profile.md) |
| Bluetooth still crashing after the firmware pin | [use a USB Bluetooth adapter](docs/how-to/use-a-usb-bluetooth-adapter.md) |
| Fresh install on a TULPAR T6 V2.1 | [set up a TULPAR T6 V2.1](docs/how-to/set-up-a-tulpar-t6-v21.md) |

## Setting up a fresh install

1. [The Windows-to-Linux driver map](docs/reference/windows-to-linux-driver-map.md)
   — what every Monster driver becomes on Linux, what is always broken out of
   the box, and the recommended baseline install.
2. Your model: [set up a TULPAR T6 V2.1](docs/how-to/set-up-a-tulpar-t6-v21.md),
   alongside its [hardware reference](docs/reference/tulpar-t6-v21-hardware.md).
3. [Unlock the keyboard backlight and touchpad](docs/how-to/unlock-keyboard-backlight-and-touchpad.md)
   — you will need this one. Both are dead on every Monster until the
   `tuxedo-drivers` DMI patch is in.

## How this repository is organized

Documents are split by what you need from them, following
[Diátaxis](https://diataxis.fr/):

- **[docs/how-to/](docs/how-to/)** — you have the symptom and want it gone.
  Commands only.
- **[docs/explanation/](docs/explanation/)** — why the hardware behaves this
  way, how each fault was actually tracked down, and which promising fixes
  turned out to be dead ends.
- **[docs/reference/](docs/reference/)** — driver maps, hardware tables, EC
  register maps, `tccd` profile definitions. Things you look up.
- **[notes/](notes/)** — open investigations and abandoned efforts. Working
  state, not advice.

### Explanation

- [Why `tuxedo-drivers` reject Monster hardware](docs/explanation/why-tuxedo-drivers-reject-monster-hardware.md)
  — the `MONSTER` DMI vendor string and the compatibility gate that stops
  every EC feature from loading.
- [Why a DRAM-less NVMe freezes the machine](docs/explanation/why-a-dram-less-nvme-freezes-the-machine.md)
  — the Phison controller that will not wake from PCIe ASPM L1, and the panic
  that spent two weekends masquerading as bad RAM.
- [AX211 Bluetooth firmware crashes](docs/explanation/ax211-bluetooth-firmware-crashes.md)
  — the firmware build bisection: 3243 is stable, 3604, 3831 and 3882 all
  crash.
- [Hyprland picks the dGPU as primary renderer](docs/explanation/hyprland-picks-the-dgpu-as-primary-renderer.md)
  — why the obvious fix breaks external monitors.
- [The ABRA A5 EC never reports temperature](docs/explanation/the-abra-a5-ec-never-reports-temperature.md)
  — what the DSDT declares, what the firmware actually populates, and why
  `tccd` loses the fan reading and the temperature together.
- [`tccd` versus `power-profiles-daemon`](docs/explanation/tccd-versus-power-profiles-daemon.md)
  — two daemons, one of which owns nothing on this hardware.
- [X-Rite panel calibration on Linux](docs/explanation/x-rite-panel-calibration-on-linux.md)
  — the factory ICC lives in the panel EEPROM, not in any installer. What
  your options really are.

### Reference

- [Windows-to-Linux driver map](docs/reference/windows-to-linux-driver-map.md)
- [TULPAR T6 V2.1 hardware](docs/reference/tulpar-t6-v21-hardware.md)
- [ABRA A5 EC field map](docs/reference/abra-a5-ec-field-map.md)
- [`tccd` profiles](docs/reference/tccd-profiles.md)
- [Keyboard backlight controls](docs/reference/keyboard-backlight-controls.md)
- [AX211 Bluetooth configuration](docs/reference/ax211-bluetooth-configuration.md)
- [Thermal sensor sources](docs/reference/thermal-sensor-sources.md)

### Also in this repository

- **[drivers/abra-a5-fan/](drivers/abra-a5-fan/)** — the out-of-tree hwmon
  driver for the ABRA A5, reverse-engineered from the DSDT and EC MMIO
  registers. It supports the
  [fan and temperature how-to](docs/how-to/show-fan-and-temperature-in-tuxedo-control-center.md).
- **[bios-dumps/](bios-dumps/)** — UEFI Setup variable dumps for the TULPAR
  T6, for hunting hidden BIOS options.
- **[notes/](notes/)** — open investigations and abandoned efforts:
  [AX211 audio glitches](notes/ax211-audio-glitches.md) (open) and
  [whether a monster-linux project makes sense](notes/idea-monster-linux.md).

## Tested configurations

| Component | TULPAR T6 V2.1 AI Creator | ABRA A5 V20.2 |
|---|---|---|
| CPU | Intel Core Ultra 7 155H (Meteor Lake) | Intel Core i5-13500H (Raptor Lake) |
| GPU | NVIDIA RTX 4070 Laptop (Max-Q) | NVIDIA RTX 4050 Laptop |
| EC | ITE IT5570E | — |
| BIOS | 1.07.04TFB | N.1.13MON07 |
| OS | Ubuntu 26.04 LTS · Arch Linux | Ubuntu 22.04 LTS |
| Kernel | 7.0.0-15-generic · 7.2 | 6.8.0-124-generic |
| NVIDIA driver | 580.142 (`-open`) | — |
| `tuxedo-drivers` | 4.22.2 · 4.25.0 | 4.22.2 (+ `tuxedo-abra-fan` 1.0 out-of-tree) |
| TUXEDO Control Center | 3.0.4 | 2.1.17 |

Every guide records the exact system it was verified on, with a date, in its
own metadata block. Several were written against Ubuntu 24.04 and kernel 6.17
and have survived the move to 26.04 and kernel 7.0 unchanged.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/STYLE.md](docs/STYLE.md).
The short version: do not document a fix you have not run, date everything,
and give every how-to a rollback section.

```bash
tools/check-docs.py
```

must exit clean before a pull request.
