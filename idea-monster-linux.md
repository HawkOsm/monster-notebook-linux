# Idea: monster-linux (asus-linux equivalent for Monster)

## Premise
Monster laptops are rebranded Clevo barebones. The TUXEDO stack already
covers the hardware:

- `tuxedo-drivers` — kernel modules (keyboard, fan, EC, etc.)
- `tccd.service` — DBus daemon for profiles
- `tuxedo-control-center` — Electron GUI

So the kernel + daemon + GUI layer is already done. A "monster-linux"
project would be a thin layer on top.

## Possible scope

- Model-quirks database (per-Monster-SKU defaults: fan curves, RGB,
  power limits)
- `monsterctl` CLI wrapping `tccd` DBus calls
- GNOME quick-settings extension (cf. `supergfxctl-gex`) for fast
  profile/GPU-mode toggling without opening TCC
- Branded installer / first-run setup that picks sensible defaults
  based on detected SKU

## Tradeoff

Building a parallel ecosystem fragments effort. Upstreaming
Monster-specific quirks into `tuxedo-drivers` gets ~90% of the value
for ~10% of the work — the only piece that genuinely needs a separate
project is the GNOME extension and maybe the CLI wrapper.

## Open questions

- Is there demand beyond personal use? (Turkish Monster owners on
  Linux — community size?)
- Does TCC's DBus API expose enough to build a useful `monsterctl`,
  or would it need patches?
- Would TUXEDO accept upstream PRs for Monster SKU IDs / quirks?
