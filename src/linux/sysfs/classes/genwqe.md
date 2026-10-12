# /sys/class/genwqe

| Field | Value |
|---|---|
| Subsystem | IBM GenWQE PCIe accelerator card class (ABI doc, contacts haver@linux.vnet.ibm.com / klebers@linux.vnet.ibm.com); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: no Kconfig or Makefile mentioning genwqe exists in the cached tree, and the ABI entries name no config symbol (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-driver-genwqe`; a debugfs counterpart exists at `Documentation/ABI/testing/debugfs-driver-genwqe` |
| Since | not stated in the ABI entries (dated Oct 2013; `reload_bitstream` May 2014) |
| Live (5.10.134 host) | class absent: no `genwqe` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-genwqe |

## What it represents

One directory `genwqe<n>_card` per IBM GenWQE (Generic Work Queue Engine) PCIe accelerator card. The attributes are the card-management surface: identity (`version` bitstream id, `type` e.g. "GenWQE5-A7", `appid` active application e.g. "GZIP"), state and health (`state`: "unused", "used", "error"; `tempsens` temperature sense register; `base_clock`; `freerunning_timer` and `queue_working_time` for performance/utilization measurements), and bitstream control (`curr_bitstream` active, 1 default / 0 backup; `next_bitstream` selection; `reload_bitstream` trigger). The real workload interface is the char device and DDCB queues, not sysfs; the class is the operator view.

## Relationship to the device model

Each class device is backed by a PCI function: the ABI documents `device/sriov_numvfs` under the card directory, i.e. the standard PCI SR-IOV enable knob reached through the card's `device` symlink (enable 1..15 VFs, disable by writing 0). The debugfs doc covers the same cards under `/sys/kernel/debug` (DDCB queue dump, error register dumps, per-UID chip state, "Only available for PF"), confirming the PF/VF split.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `genwqe<n>_card/version` | RO | bitstream id, e.g. '0000000330336283.00000000475a4950' | always | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/appid` | RO per ABI wording ("Identifies") | active application, e.g. 'GZIP' | always | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/type` | RO | card type, e.g. 'GenWQE5-A7' | always | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/state` | RO | "unused", "used", or "error" | always | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/{tempsens,base_clock,freerunning_timer,queue_working_time}` | RO | temperature sense register; base clock frequency; free running timer; queue working time (both timer files for perf/utilization) | always | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/curr_bitstream` | RO | currently active bitstream: 1 default, 0 backup | always | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/next_bitstream` | W ("Interface to set") | selects bitstream used on next load | always | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/reload_bitstream` | W | write 1 triggers a PCIe card reset to reload the bitstream | since May 2014 entry | ABI testing `sysfs-driver-genwqe` |
| `genwqe<n>_card/device/sriov_numvfs` | W | enable 1..15 VFs; 0 disables | PCI SR-IOV capable function | ABI testing `sysfs-driver-genwqe` |

## Safety and writes

Reads are safe. `reload_bitstream` resets the PCIe card (ABI gives the `sudo sh -c 'echo 1 > ...'` recipe; after success the card returns with the `next_bitstream` image) -- disruptive by design. `next_bitstream` changes what firmware loads next. `sriov_numvfs` creates/destroys VFs. Writability of `appid` is not stated in the ABI text and is not verified. All writes are root-only by normal sysfs permissions.

## References

- `Documentation/ABI/testing/sysfs-driver-genwqe`, `Documentation/ABI/testing/debugfs-driver-genwqe` (cached copies)
- [sysfs-driver-genwqe online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-driver-genwqe)
- `source-cache/sysfs-attrs.json` genwqe entry (12 paths, matching)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-genwqe
