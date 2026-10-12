# /sys/class/tpm

| Field | Value |
|---|---|
| Subsystem | TPM subsystem, `drivers/char/tpm/` (`obj-$(CONFIG_TCG_TPM) += tpm.o`, torvalds/linux master) |
| Config gate | `CONFIG_TCG_TPM` (Kconfig "TPM Hardware Support"; obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/stable/sysfs-class-tpm` (13 What entries; 20 paths counted in the ledger once the ppi/ subtree from `Documentation/ABI/testing/sysfs-driver-ppi` is included) |
| Since | 2.6.12 (`device/`, `caps`, `pcrs`, `pubek`); 2.6.13 (`cancel`); 2.6.17 (`active`, `enabled`, `owned`, `temp_deactivated`); 3.1 (`durations`, `timeouts`); 3.6 (`ppi/`); 5.5 (`tpm_version_major`); 5.12 (`pcr-<H>/<N>`) |
| Live (5.10.134 host) | class directory present, 0 devices (no TPM chip in the container; class dir exists per live-sys enumeration) |
| Ledger ID | SYSC-tpm |

## What it represents

One directory per TPM chip, `tpmX`, split in two: the class-level files
(`tpm_version_major`, the `pcr-<H>/<N>` banks, the `ppi/` Physical
Presence Interface subtree) and the legacy `device/` directory holding the
TPM 1.2-era introspection files. `caps` gives manufacturer and TCG version
(hex manufacturer ID, e.g. 0x53544d20); `pcrs` dumps all Platform
Configuration Registers as a point-in-time snapshot (SHA-1, 20 bytes per
PCR, for 1.1/1.2 chips); `durations` and `timeouts` expose the vendor
command-execution times and interface timeouts in microseconds, each with a
`[original]`/`[adjusted]` marker showing whether the driver rescaled
msec-reporting chips. The 5.12 addition made PCR reads bank-addressable:
`pcr-sha256/7` returns one PCR in compact hex. `ppi/` mediates
BIOS-executed operations (request integers 1-160, 0 = none) under the PPI
specification.

## Relationship to the device model

The stable ABI anchors everything at `/sys/class/tpm/tpmX/device/`, which
is the parent hardware device under `/sys/devices/...`; the ppi entry notes
that in Linux 4.2 ppi moved to the character-device directory with a
`tpmX/device/ppi` symlink kept for backwards compatibility. The TPM's
userspace command channel is the `/dev/tpmX` character device (and the TPM
2.0 `tpmrm` flavor: sibling page [tpmrm](./tpmrm.md)); sysfs carries
identification and policy, not command I/O.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `tpmX/device/caps` | RO | manufacturer hex, TCG version, firmware version | always | ABI stable `sysfs-class-tpm` (2.6.12) |
| `tpmX/device/pcrs` | RO | PCR dump, `PCR-NN: hex` lines | always | ABI stable `sysfs-class-tpm` (2.6.12) |
| `tpmX/device/pubek` | RO | endorsement key structure; unavailable when owned (TPM 1.2) | always | ABI stable `sysfs-class-tpm` (2.6.12) |
| `tpmX/device/cancel` | WO | any value; cancels the pending command via vendor op | always | ABI stable `sysfs-class-tpm` (2.6.13) |
| `tpmX/device/{active,enabled,owned,temp_deactivated}` | RO | 0/1 flags: accepting commands / visible to OS / TakeOwnership done / temporarily deactivated | always | ABI stable `sysfs-class-tpm` (2.6.17) |
| `tpmX/device/durations` | RO | short/medium/long usecs + `[original]`/`[adjusted]` | always | ABI stable `sysfs-class-tpm` (3.1) |
| `tpmX/device/timeouts` | RO | four interface timeouts in usecs + marker | always | ABI stable `sysfs-class-tpm` (3.1) |
| `tpmX/tpm_version_major` | RO | TCG spec major version (e.g. 2) | always | ABI stable `sysfs-class-tpm` (5.5) |
| `tpmX/pcr-<H>/<N>` | RO | PCR N of hash bank H in compact hex | banks per chip | ABI stable `sysfs-class-tpm` (5.12) |
| `tpmX/ppi/` | mixed | PPI subtree: `version` (RO), `request` (RW, 0-160), `response`, `transition_action`, `tcg_operations`, `vs_operations` (RO, 1.2+ only) | only if BIOS supports PPI | ABI testing `sysfs-driver-ppi` (3.6) |

## Safety and writes

Reads are safe, with two behavioral caveats from the ABI: `pcrs` output is
only valid for a snapshot in time, and `pubek` returns nothing useful once
a 1.2 chip is owned (the driver stores no secrets, so it cannot authorize
the read). Writes: `cancel` aborts an in-flight command (vendor-specific
effect); `ppi/request` queues a pre-OS operation that the BIOS executes at
next boot -- clearing TPM ownership data is in that request range, which is
the destructive case, gated in practice by root. No capability
requirements are stated in the ABI files.

## References

- `Documentation/ABI/stable/sysfs-class-tpm`, `Documentation/ABI/testing/sysfs-driver-ppi` (cached copies; online: https://www.kernel.org/doc/Documentation/ABI/stable/sysfs-class-tpm)
- `drivers/char/tpm/Makefile`, `drivers/char/tpm/Kconfig` (torvalds/linux master; fetched)
- Ledger row SYSC-tpm (20 paths); `/sys/class/tpm` present with 0 devices per `source-cache/live-sys/class-list.txt`
- Sibling pages: [tpmrm](./tpmrm.md)
