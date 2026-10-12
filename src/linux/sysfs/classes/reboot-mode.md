# /sys/class/reboot-mode

| Field | Value |
|---|---|
| Subsystem | reboot-mode framework (platform reboot reason/mode arguments); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-reboot-mode-reboot_modes` (1 What entry) |
| Since | Date March 2026 (TBD) in the ABI file; KernelVersion TBD - newer than the live 5.10.134 kernel |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/reboot-mode |
| Ledger ID | SYSC-reboot-mode |

## What it represents

A single read-only attribute, `reboot_modes`, per driver registered with the reboot-mode framework. It lists the reboot-mode arguments the current platform supports - for example `recovery fastboot bootloader` - so scripts and initramfs logic can pick a valid argument before calling `reboot(LINUX_REBOOT_CMD_RESTART2, arg)`. Drivers register the arguments from device properties named `mode-<argument>` (for example `mode-bootloader`, `mode-recovery`).

## Relationship to the device model

The ABI spells the path `/sys/class/reboot-mode/<driver>/reboot_modes` and stresses that the exact path varies with the registering driver; the file gives `/sys/class/reboot-mode/nvmem-reboot-mode/reboot_modes`, `/sys/class/reboot-mode/syscon-reboot-mode/reboot_modes` and `/sys/class/reboot-mode/qcom-pon/reboot_modes` as examples. So the class mirrors the reboot-mode provider drivers (nvmem-backed, syscon-backed, Qualcomm PoN), one directory each, rather than one directory per reboot action. It is a different mechanism from the kernel's own reboot controls under `/sys/kernel/reboot` (documented in `sysfs-kernel-reboot`, 5.11: mode, type, cpu, force - "set the kernel reboot behavior"): that interface tunes how the machine reboots, while this class only publishes the argument vocabulary the platform's reboot-mode providers accept.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<driver>/reboot_modes` | RO | space-separated list of supported reboot-mode arguments | driver registered with the framework | ABI, March 2026 (TBD) |

## Safety and writes

Nothing to write: the interface is explicitly read-only, a discovery helper for `reboot(2)` argument strings. The ABI's stated use is checking validity of the argument before triggering a reset. Note the version honesty: the ABI entry carries Date "March 2026(TBD)" and KernelVersion "TBD", i.e. the interface is newer than the cached live kernel, and nothing here could be verified against the running host.

## References

- `Documentation/ABI/testing/sysfs-class-reboot-mode-reboot_modes` (cached copy; 1 What entry)
- Implementation: not in cached tree
- Related ABI: `Documentation/ABI/testing/sysfs-kernel-reboot` (cached copy; /sys/kernel/reboot controls, a different mechanism)
- Coverage: [ledger](../ledger.md)
- Live check: /sys/class/reboot-mode absent (kernel 5.10.134, read-only enumeration)
