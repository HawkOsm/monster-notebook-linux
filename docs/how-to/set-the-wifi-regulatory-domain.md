# Set the Wi-Fi regulatory domain

**Status:** verified
**Applies to:** Monster TULPAR T6 V2.1 (AI Creator) on Arch Linux; any Arch
system with `wireless-regdb` (expected, not tested); Ubuntu not tested
**Verified on:** Arch Linux · kernel 7.2.11-arch1-1 · `wireless-regdb`
2026.09.03-1 · `iw` 6.17-1 · 2026-10-21
**Symptom:** `iw reg get` prints `country 00` and the journal logs
`set-wireless-regdom failed with exit code 1` on every boot.

This sets your country in `/etc/conf.d/wireless-regdom`, so the global Wi-Fi
regulatory domain is your country instead of the world default `00`. On the
maintainer's machine Wi-Fi was faster afterwards; no before-and-after
throughput was measured.

## Before you start

- Arch Linux with the `wireless-regdb` package, which ships
  `/etc/conf.d/wireless-regdom`.
- Your two-letter ISO 3166-1 country code. The examples use `TR` for Turkey.

## Confirm the diagnosis

The domain is the world default and no country is configured:

```bash
iw reg get | sed -n '1,2p'
# expect: global
# expect: country 00: DFS-UNSET
```

```bash
grep -c '^WIRELESS_REGDOM' /etc/conf.d/wireless-regdom
# expect: 0
```

The boot error is a side effect of that. A udev rule runs
`/usr/bin/set-wireless-regdom` when `cfg80211` loads, and the script exits 1
when `WIRELESS_REGDOM` is empty. Nothing is applied.

```bash
journalctl -b | grep "set-wireless-regdom' failed"
# expect: cfg80211: Process '/usr/bin/set-wireless-regdom' failed with exit code 1.
```

## Fix

### 1. Set the country in the config file

The file lists every country as a commented-out `WIRELESS_REGDOM="XX"` line.
Uncomment yours. This block does it for Turkey; replace `TR` in both places
with your own country code.

```bash
sudo cp /etc/conf.d/wireless-regdom /etc/conf.d/wireless-regdom.bak
sudo sed -i 's/^#WIRELESS_REGDOM="TR"/WIRELESS_REGDOM="TR"/' /etc/conf.d/wireless-regdom
```

### 2. Apply it without rebooting

The file is read when `cfg80211` loads, so on its own the change takes effect
at the next boot. Apply it now:

```bash
sudo iw reg set TR
```

## Verify

```bash
iw reg get | sed -n '1,2p'
# expect: global
# expect: country TR: DFS-ETSI
```

With another country, the second line shows that country and its DFS region.

## Roll back

```bash
sudo mv /etc/conf.d/wireless-regdom.bak /etc/conf.d/wireless-regdom
```

Reboot. The global domain returns to `00`.

## Trade-offs

The domain sets the channels and transmit power that `iw reg get` lists, so
set the country you are physically in.

No throughput was measured. On this machine the Intel Wi-Fi driver had
already set `alpha2=TR` itself at boot, before the file was edited:
`journalctl -b -u wpa_supplicant` shows
`CTRL-EVENT-REGDOM-CHANGE init=DRIVER type=COUNTRY alpha2=TR`. `wpa_supplicant`
logged no reconnect after the edit. The faster Wi-Fi the maintainer saw is an
observation, not a measured result; if you measure it, record the numbers
here.
