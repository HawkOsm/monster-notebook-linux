# Use a USB Bluetooth adapter

**Status:** verified
**Applies to:** any machine with an Intel AX211 combo card (`8087:0033`)
**Verified on:** Ubuntu 24.04 · 2026-05-13
**Symptom:** the built-in AX211 Bluetooth keeps crashing with
`Hardware error 0x0c` and no firmware or configuration change has fixed it.
**See also:** [why the AX211 Bluetooth firmware crashes](../explanation/ax211-bluetooth-firmware-crashes.md),
[pin stable AX211 Bluetooth firmware](pin-stable-ax211-bluetooth-firmware.md)

Bypass the AX211's Bluetooth half with a cheap USB adapter while keeping its
Wi-Fi, which is fine. This fixes every Bluetooth device at once rather than one
peripheral, costs $5–15, and is fully reversible — unplug the adapter and the
built-in controller is back.

Try [pinning firmware build 3243](pin-stable-ax211-bluetooth-firmware.md)
first. This is the fallback when that is not enough.

## Before you start

Pick a supported chipset:

| Chipset | Bluetooth version | Notes |
|---|---|---|
| Realtek RTL8761B / RTL8761BU | 5.x | Broad Linux support since kernel 5.8; most $5–10 nano dongles |
| CSR8510 | 4.0 only | Cheap, fine for keyboards and mice, no BLE Audio |
| Broadcom BCM20702 | — | **Avoid.** Driver bitrot, needs firmware blobs scraped from Windows installers |

## Fix

### 1. Confirm the adapter enumerates

Plug it in, then:

```bash
lsusb | grep -iE "bluetooth|realtek|csr|cambridge"
dmesg | tail -30   # look for "Bluetooth: hciN: ..." with the new product/firmware line
hciconfig          # should now show 2 controllers: hci0 (AX211) and hci1 (new)
```

### 2. Disable the built-in controller

This udev rule sets `ATTR{authorized}=0` on the AX211 Bluetooth device at every
enumeration, making it invisible to `btusb` and bluez. The AX211's Wi-Fi half
is on PCIe, not USB, and is unaffected.

```bash
sudo mv /etc/udev/rules.d/99-disable-ax211-bt.rules.disabled \
        /etc/udev/rules.d/99-disable-ax211-bt.rules
sudo udevadm control --reload
sudo udevadm trigger --action=add --attr-match=idVendor=8087
```

`hci0` should disappear immediately.

### 3. Re-pair your devices to the new adapter

```bash
bluetoothctl
> power on
> scan on
# wait for the keyboard MAC to appear, then:
> pair <MAC>
> trust <MAC>
> connect <MAC>
```

## Verify

```bash
hciconfig         # only the new adapter should show
cat /sys/bus/usb/devices/3-10/authorized   # should be 0
```

Then confirm the crashes are gone by watching for about 30 minutes:

```bash
journalctl -k -f | grep -E "Hardware error|hci"
```

## Roll back

```bash
sudo rm /etc/udev/rules.d/99-disable-ax211-bt.rules
sudo udevadm control --reload
sudo udevadm trigger --action=add --attr-match=idVendor=8087
# Or just reboot — udev will not deauthorize the device without the rule.
```

## Trade-offs

A dongle occupies a USB port and sticks out. Against that, it is the only
measure here that reliably ends the crashes rather than reducing them.

Two alternatives exist and are both worse value:

- **Replace the M.2 Wi-Fi/Bluetooth card**, for example with an AX210, which
  has fewer reported coexistence issues. Requires opening the laptop.
- **Replace the peripheral with one that has its own 2.4 GHz USB receiver.**
  Bypasses AX211 Bluetooth but ties you to that one device.
