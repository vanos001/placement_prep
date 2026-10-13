# /sys/class/chromeos

| Field | Value |
|---|---|
| Subsystem | ChromeOS EC class (embedded controller devices under `drivers/platform/chrome`); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); live host does not expose the class |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-chromeos` plus driver files `sysfs-class-chromeos-driver-cros-ec-lightbar` and `sysfs-class-chromeos-driver-cros-ec-vbc` |
| Since | 4.2 (flashinfo, reboot, version, lightbar/*: August 2015); `kb_wake_angle` 4.17; `usbpdmuxinfo`/`ap_mode_entry` February 2025 (no KernelVersion stated) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/chromeos |
| Ledger ID | SYSC-chromeos |

## What it represents

One directory per ChromeOS embedded controller (EC) device, named by the EC device name (for example `cros_ec`). The EC is a microcontroller that manages keyboard, battery charging, fans and similar platform hardware independently of the CPU. The class exposes EC identity, flash layout, reboot control and EC-feature knobs; two driver-specific sub-trees (lightbar, verified boot context) are documented in their own ABI files. The 2025 additions (`usbpdmuxinfo`, `ap_mode_entry`) show the class is still growing around Type-C/USB4 role negotiation between the AP and the EC.

## Relationship to the device model

Each `<ec-device-name>` directory is a class view of an EC device registered by the ChromeOS EC drivers. The class holds no bus of its own; the files below are attributes attached to the EC device. The lightbar files appear only when the `cros-ec-lightbar` driver is bound, and `vbc/vboot_context` only when the `cros-ec-vbc` driver is present, so the per-device file set is driver-conditional.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<ec>/flashinfo` | RO | EC flash information | always | ABI `sysfs-class-chromeos`, 4.2 |
| `<ec>/kb_wake_angle` | RW | degrees 0-360; keyboard-wake lid angle | always | ABI, 4.17 |
| `<ec>/reboot` | WO | `cancel`, `ro`, `rw`, `cold`, `disable-jump`, `hibernate`, `at-shutdown` | always | ABI, 4.2 |
| `<ec>/version` | RO | EC software and hardware version | always | ABI, 4.2 |
| `cros_ec/usbpdmuxinfo` | RO | per-Type-C-port flags: USB, DP, POLARITY, HPD_IRQ, HPD_LVL, SAFE, TBT, USB4 | cros_ec | ABI, February 2025 |
| `cros_ec/ap_mode_entry` | RO | whether the EC waits for AP direction for Type-C altmodes/USB4 | cros_ec | ABI, February 2025 |
| `<ec>/lightbar/brightness` | RW | 0-255 overall brightness | lightbar driver | ABI driver file, 4.2 |
| `<ec>/lightbar/interval_msec` | RO | ms rate limit between lightbar accesses | lightbar driver | ABI driver file, 4.2 |
| `<ec>/lightbar/led_rgb` | RW | LED,RED,GREEN,BLU quadruples, 0-255; LED 4 = all segments | lightbar driver | ABI driver file, 4.2 |
| `<ec>/lightbar/program` | WO | custom lightbar sequence upload | lightbar driver | ABI driver file, 4.2 |
| `<ec>/lightbar/sequence` | RW | current/selected built-in sequence | lightbar driver | ABI driver file, 4.2 |
| `<ec>/lightbar/userspace_control` | RW | take control away from kernel sequences | lightbar driver | ABI driver file, 4.2 |
| `<ec>/lightbar/version` | RO | lightbar version | lightbar driver | ABI driver file, 4.2 |
| `<ec>/vbc/vboot_context` | RW | verified-boot context in EC NVRAM | cros-ec-vbc driver | ABI driver file, 4.4 |

## Safety and writes

Reads are safe but rate-limited: the ABI states the EC throttles all lightbar accesses to `interval_msec` milliseconds, and reads block until the interval lapses. `reboot` directs the EC itself to jump between RO/RW images, cold-reboot or hibernate it; a wrong write can disturb the machine's power management. `kb_wake_angle` and vboot context change persisted platform behavior. Treat every write as root-only system administration on ChromeOS hardware.

## References

- `Documentation/ABI/testing/sysfs-class-chromeos` (cached copy; 6 What entries)
- `Documentation/ABI/testing/sysfs-class-chromeos-driver-cros-ec-lightbar`, `...-driver-cros-ec-vbc` (cached copies)
- `drivers/platform/chrome/` implementation: not in cached tree
- Live check: /sys/class/chromeos absent (kernel 5.10.134, read-only enumeration)
- Sibling pages: [power_supply](./power_supply.md); coverage: [ledger](../ledger.md)
