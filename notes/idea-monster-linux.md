# Idea: a monster-linux project

**Status:** open
**Last worked on:** 2026-08-13
**See also:** [the Windows-to-Linux driver map](../docs/reference/windows-to-linux-driver-map.md)

Whether a `monster-linux` project, along the lines of `asus-linux`, would be
worth building — or whether the effort belongs upstream instead.

## The premise

Monster laptops are rebranded Clevo barebones, and the TUXEDO stack already
covers the hardware:

| Layer | Component |
|---|---|
| Kernel modules | `tuxedo-drivers` — keyboard, fan, EC |
| Daemon | `tccd.service` — D-Bus profile management |
| GUI | `tuxedo-control-center` — Electron front end |

Kernel, daemon and GUI are therefore already done. Anything called
`monster-linux` would be a thin layer on top, not a new stack.

## Possible scope

- A model-quirks database: per-SKU defaults for fan curves, RGB and power
  limits.
- `monsterctl`, a CLI wrapping the `tccd` D-Bus calls.
- A GNOME quick-settings extension, along the lines of `supergfxctl-gex`, for
  switching profile and GPU mode without opening TCC.
- A branded first-run setup that picks sensible defaults from the detected SKU.

## The argument against

Building a parallel ecosystem fragments the effort. Upstreaming
Monster-specific quirks into `tuxedo-drivers` gets roughly 90% of the value for
roughly 10% of the work. The only pieces that genuinely need a separate project
are the GNOME extension and perhaps the CLI wrapper.

## Open questions

- Is there demand beyond personal use? How many Turkish Monster owners run
  Linux?
- Does TCC's D-Bus API expose enough to build a useful `monsterctl`, or would
  it need patches?
- Would TUXEDO accept upstream pull requests adding Monster SKU IDs and quirks?
