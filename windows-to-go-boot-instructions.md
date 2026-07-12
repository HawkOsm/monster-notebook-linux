# Windows-To-Go USB Boot Instructions — X-Rite ICC Extraction

> **Status: ABANDONED (2026-05-15).** The extraction attempt was called off —
> too much hassle for a cosmetic fix (see [xrite-resume-state.md](xrite-resume-state.md)).
> Kept because the procedure itself is sound and reusable if anyone (including
> future me) wants the factory ICC badly enough to boot Windows once for it.

One-time use: boot Windows 11 from the USB, run X-Rite Color Assistant to
read the panel's factory ICC profile from EEPROM, save the profile, reboot
to Linux, install the profile.

## Before Reboot

Two files must already exist before you boot the USB. The Linux-side prep
should have copied:

- `/dev/sda1` (ESP, 700 MB, FAT32) — UEFI boot files + boot.wim
- `/dev/sda2` (Windows, 28.6 GB, NTFS) — applied Windows 11 Home from install.wim

If you're reading this AFTER Linux prep finished, you're ready. If the
`wimlib-imagex apply` step is still running, wait until it completes.

## Step 1 — Boot the USB

1. Reboot the laptop.
2. Hold **F7** (Monster/Clevo boot menu key) right after the power-on logo
   appears. If F7 doesn't work, try **F2** (BIOS, then change boot order) or
   **F12**.
3. From the boot menu, pick the entry that mentions **"USB"** or
   **"VendorCo ProductCode"** with **UEFI** prefix.
4. The Windows boot manager will start, then Windows Setup will appear after
   loading boot.wim (~2-5 minutes on USB 2.0).

## Step 2 — At the Windows Setup Screen (Language Selection)

When you see "Microsoft Software License Terms" or the language/region
selector:

1. **Do NOT click Install Now.** That would try to install Windows on an
   internal disk, which is exactly what we want to avoid.
2. Press **Shift + F10** — a Command Prompt opens.

## Step 3 — Find the Drive Letters

Inside the cmd window, run:

```cmd
diskpart
list vol
exit
```

You'll see something like:

```
  Volume ###  Ltr  Label        Fs     Type        Size     Status
  ----------  ---  -----------  -----  ----------  -------  ---------
  Volume 0    C    ESP          FAT32  Partition    700 MB  Healthy
  Volume 1    D    Windows      NTFS   Partition   28.6 GB  Healthy
  Volume 2    E    (whatever)   ...
```

Note which letters are assigned to **ESP** (will be referred to as `<ESP>`)
and **Windows** (will be referred to as `<WIN>`). **They will probably be C
and D, but verify** — Linux's internal NVMe drives will also be visible and
may have other letters. **Do not touch the NVMe drives.**

## Step 4 — Configure Boot and Reboot

Still in cmd, run **one command** (replace `<WIN>` and `<ESP>` with the
letters from step 3):

```cmd
bcdboot <WIN>:\Windows /s <ESP>: /f UEFI
```

Example if Windows was D: and ESP was C:

```cmd
bcdboot D:\Windows /s C: /f UEFI
```

Output should say: `Boot files successfully created.`

Then reboot:

```cmd
wpeutil reboot
```

The laptop reboots. **Boot from USB again** (F7 menu) — this time the BCD on
ESP points at the applied Windows, so Windows starts directly instead of
Setup.

## Step 5 — First Boot of Windows (OOBE)

Windows starts the OOBE (Out Of Box Experience) — this is slow on USB 2.0.
Expect **15-30 minutes of waiting** with screens like "Just a moment...",
"This will take a few minutes", etc. The laptop may reboot once during this
phase — boot from USB each time.

When you reach **"Let's start by selecting your country or region"**:

1. Pick **Türkiye**, **Next**.
2. Pick keyboard layout, **Next**.
3. **At the network screen** — this is where Windows 11 Home traps you
   into a Microsoft account requirement. To bypass:
   - Press **Shift + F10** to open cmd
   - Type: `oobe\bypassnro` and press Enter
   - The system reboots, brings you back to the network screen
   - This time pick **"I don't have internet"** → **"Continue with limited
     setup"**
4. Create a local user name (e.g., `temp`) — password optional.
5. Decline all the privacy/diagnostics opt-ins (uncheck everything).
6. Wait for the desktop to load — another 5-15 minutes on USB 2.0.

## Step 6 — Install X-Rite Color Assistant

Once you have the desktop:

1. Open **Edge** (or any browser).
2. Download the X-Rite Color Assistant package from this direct URL:
   ```
   https://mnstr-support-files.s3.eu-central-1.amazonaws.com/Drivers/Tulpar Serisi/Tulpar T6/Tulpar T6 V2.1/Xrite Color Assistant.zip
   ```
3. Save to `Downloads`, right-click the .zip → **Extract All**.
4. In the extracted folder, navigate to:
   `21_PantoneInstaller\Monster_XRiteColorAssistantSetup\`
5. Right-click `XRiteColorAssistantSetup.exe` → **Run as administrator**.
6. Follow the installer (Next, Next, Finish).

## Step 7 — Run ProfileInstaller to Read the EEPROM

After the X-Rite Color Assistant install completes:

1. Navigate to `21_PantoneInstaller\Monster_ProfileInstaller\` (in the
   extracted folder).
2. Right-click `ProfileInstaller.exe` → **Run as administrator**.
3. The tool reads the panel's EEPROM via I2C and writes one or more
   `.icm` files to `C:\DisplayProfiles\` (or
   `C:\DisplayProfiles\ColorCalibration_<Model><Serial>.zip` per the INI).
4. Wait until it finishes (a few seconds).

You should see a folder `C:\DisplayProfiles\` containing:

```
C:\DisplayProfiles\
  ColorCalibration_<computer model>_<serial>.zip
  TPLCD_1601_*.icm   (the profile file we want)
```

## Step 8 — Save the ICC to a Place Linux Can Reach

The ICC is currently on `C:\` (the USB's Windows partition, which is NTFS).
Linux can read NTFS so we'll grab it from there after the next reboot. But
to be safe, also save it to a known location:

1. Open File Explorer → navigate to `C:\DisplayProfiles\`.
2. **Copy the entire `DisplayProfiles` folder** to the USB Windows
   partition root: `C:\DisplayProfiles_BACKUP\`. (This is the same drive
   but a safer named folder.)
3. Optionally, also extract the `.icm` from the zip and save it as
   `C:\TLPanel_factory.icm` for easy access.

## Step 9 — Shutdown and Boot Linux

1. Start Menu → Power → **Shut Down** (not Restart — Restart will sometimes
   re-enter Windows from the USB on boot).
2. When laptop is fully off, **remove the USB stick**.
3. Power on — laptop boots into Ubuntu normally.

## Step 10 — Install the Profile on Linux

Back at the Ubuntu desktop, re-plug the USB stick, mount the NTFS partition,
and copy the `.icm` to the user ICC store:

```bash
udisksctl mount -b /dev/sda2
cp /media/$USER/Windows/DisplayProfiles_BACKUP/TPLCD_1601_*.icm ~/.local/share/icc/
```

Then assign it in GNOME **Settings → Color** (the most reliable method — see
[fix-color-calibration.md](fix-color-calibration.md) for the colord CLI route and
its quirks). The display then has the same calibration as on Windows.

## Troubleshooting

### "bcdboot" says "Failure when attempting to copy boot files"

Probably wrong drive letters. Re-run `diskpart > list vol > exit` and
double-check. ESP must be the FAT32 700 MB volume; Windows must be the NTFS
28.6 GB volume.

### Windows Setup loops back to language selection

Boot.wim wasn't fully copied to ESP, or bootmgfw.efi is missing. Boot back
to Linux and re-run the prep step.

### The laptop boots into Linux instead of Windows on Step 4 reboot

You didn't press F7 to enter the boot menu. Default boot order goes to
Linux first. Hold F7 immediately after the Monster logo every time you want
the USB.

### Windows freezes at "Getting ready" for >30 minutes

USB 2.0 is painfully slow but not usually hung. Wait. If genuinely frozen,
hard-reset (hold power for 10 seconds) and try again.

### "Activation" complaints

Windows might not auto-activate the first boot. Doesn't matter — X-Rite
Color Assistant works without activation. Ignore the watermark.
