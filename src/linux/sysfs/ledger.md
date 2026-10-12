# sysfs Class Coverage Ledger

## Overview

This ledger inventories sysfs classes with **two independent, honestly
scoped sources**, and the *Source* column records which of them vouches for
each row:

1. **`live@5.10.134`** — the class directory exists in `/sys/class/` on the
   host this encyclopedia was built on (kernel 5.10.134, Alibaba Cloud
   `kangaroo` build, x86_64). Device counts are the momentary population of
   this container host and will differ on your machine. Live presence proves
   existence for *that* kernel configuration only — a driver built as module
   and not loaded, or disabled via config, removes the class entirely.
2. **`ABI-doc`** — the class has `What: /sys/class/<name>/...` entries in
   the kernel's `Documentation/ABI/` tree (torvalds/linux master). This is
   the kernel project itself promising an interface, but **not every class
   is documented there** (absence from ABI-doc is not absence from sysfs),
   and documented attributes may still vary by driver.

Neither source alone, and not their union, is a *complete* list of every
class any Linux kernel can expose — that set is configuration-dependent by
design (see [sysfs overview](./overview.md)). The *Attrs* column counts
distinct documented attribute paths found in ABI docs, a lower bound on the
attributes a class may expose; drivers routinely add their own.

**Status vocabulary** (defined in the [encyclopedia overview](../interface-encyclopedia.md)):
`not-started` → inventoried only · `researched` → sources read ·
`documented` → full class page with attribute semantics, permissions,
version/config notes, safe inspection examples and write warnings ·
`source-limited` → documented with fewer sources than the standard.

## Classes

| ID | Class | Source | Live devices | Documented attrs | Status | Chapter | Notes |
|---|---|---|---|---|---|---|---|
| SYSC-accel | `accel` | ABI-doc | — | 34 | researched | — | —remaining-coverage |
| SYSC-ata_device | `ata_device` | ABI-doc | — | 9 | researched | — | —remaining-coverage |
| SYSC-ata_link | `ata_link` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-ata_port | `ata_port` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-backlight | `backlight` | live@5.10.134 + ABI-doc | 0 | 15 | documented | — | —ABI |
| SYSC-bdi | `bdi` | live@5.10.134 + ABI-doc | 9 | 10 | documented | — | —Full |
| SYSC-block | `block` | live@5.10.134 + ABI-doc | 4 | 171 | documented | — | —Full |
| SYSC-bluetooth | `bluetooth` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-bsg | `bsg` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-bsr | `bsr` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-c2port | `c2port` | ABI-doc | — | 11 | researched | — | —remaining-coverage |
| SYSC-chromeos | `chromeos` | ABI-doc | — | 14 | researched | — | —remaining-coverage |
| SYSC-cpuid | `cpuid` | live@5.10.134 | 2 | 0 | documented | — | —chapter |
| SYSC-cxl | `cxl` | ABI-doc | — | 23 | researched | — | —remaining-coverage |
| SYSC-devfreq | `devfreq` | ABI-doc | — | 14 | researched | — | —remaining-coverage |
| SYSC-devfreq-event | `devfreq-event` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-devlink | `devlink` | live@5.10.134 + ABI-doc | 0 | 7 | documented | — | —chapter |
| SYSC-drm | `drm` | live@5.10.134 + ABI-doc | 1 | 1 | documented | — | —chapter |
| SYSC-extcon | `extcon` | ABI-doc | — | 6 | researched | — | —remaining-coverage |
| SYSC-fc | `fc` | ABI-doc | — | 1 | researched | — | —remaining-coverage |
| SYSC-fc_host | `fc_host` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-fc_remote_ports | `fc_remote_ports` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-firmware | `firmware` | ABI-doc | — | 7 | documented | — | —chapter |
| SYSC-firmware-attributes | `firmware-attributes` | ABI-doc | — | 11 | researched | — | —remaining-coverage |
| SYSC-fpga_bridge | `fpga_bridge` | ABI-doc | — | 2 | documented | — | —chapter |
| SYSC-fpga_manager | `fpga_manager` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-fpga_region | `fpga_region` | ABI-doc | — | 1 | documented | — | —chapter |
| SYSC-genwqe | `genwqe` | ABI-doc | — | 12 | researched | — | —remaining-coverage |
| SYSC-gism_class | `gism_class` | live@5.10.134 | 1 | 0 | researched | — | —remaining-coverage |
| SYSC-gnss | `gnss` | ABI-doc | — | 1 | researched | — | —remaining-coverage |
| SYSC-gpio | `gpio` | ABI-doc | — | 1 | documented | — | —DEPRECATED: |
| SYSC-graphics | `graphics` | live@5.10.134 | 1 | 0 | documented | — | —chapter |
| SYSC-hidraw | `hidraw` | ABI-doc | — | 2 | researched | — | —remaining-coverage |
| SYSC-hwmon | `hwmon` | live@5.10.134 + ABI-doc | 0 | 120 | documented | — | —ABI |
| SYSC-i2c-adapter | `i2c-adapter` | live@5.10.134 | 0 | 0 | documented | — | —no |
| SYSC-ieee80211 | `ieee80211` | ABI-doc | — | 2 | researched | — | —remaining-coverage |
| SYSC-infiniband | `infiniband` | ABI-doc | — | 122 | documented | — | —chapter |
| SYSC-infiniband_mad | `infiniband_mad` | ABI-doc | — | 5 | documented | — | —chapter |
| SYSC-infiniband_srp | `infiniband_srp` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-infiniband_verbs | `infiniband_verbs` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-input | `input` | live@5.10.134 + ABI-doc | 2 | 3 | documented | — | —chapter |
| SYSC-intel_pmt | `intel_pmt` | ABI-doc | — | 14 | researched | — | —remaining-coverage |
| SYSC-iommu | `iommu` | live@5.10.134 + ABI-doc | 0 | 7 | researched | — | —remaining-coverage |
| SYSC-iscsi_connection | `iscsi_connection` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_endpoint | `iscsi_endpoint` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_host | `iscsi_host` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_iface | `iscsi_iface` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_session | `iscsi_session` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_transport | `iscsi_transport` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-issei | `issei` | ABI-doc | — | 9 | researched | — | —remaining-coverage |
| SYSC-lcd | `lcd` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-leds | `leds` | ABI-doc | — | 96 | documented | — | —ABI |
| SYSC-macvtap | `macvtap` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-mdio_bus | `mdio_bus` | ABI-doc | — | 16 | documented | — | —chapter |
| SYSC-mei | `mei` | ABI-doc | — | 10 | researched | — | —remaining-coverage |
| SYSC-mem | `mem` | live@5.10.134 | 8 | 0 | documented | — | —chapter |
| SYSC-mic | `mic` | ABI-doc | — | 13 | researched | — | —remaining-coverage |
| SYSC-misc | `misc` | live@5.10.134 + ABI-doc | 75 | 2 | documented | — | —chapter |
| SYSC-msr | `msr` | live@5.10.134 | 2 | 0 | documented | — | —chapter |
| SYSC-mtd | `mtd` | ABI-doc | — | 22 | documented | — | —chapter |
| SYSC-mux | `mux` | ABI-doc | — | 2 | researched | — | —remaining-coverage |
| SYSC-nd | `nd` | live@5.10.134 | 1 | 0 | documented | — | —chapter |
| SYSC-net | `net` | live@5.10.134 + ABI-doc | 3 | 96 | documented | — | —Full |
| SYSC-nvme | `nvme` | live@5.10.134 + ABI-doc | 0 | 39 | documented | — | —Entry |
| SYSC-nvme-generic | `nvme-generic` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-nvme-subsystem | `nvme-subsystem` | live@5.10.134 + ABI-doc | 0 | 6 | researched | — | —remaining-coverage |
| SYSC-ocxl | `ocxl` | ABI-doc | — | 1 | researched | — | —remaining-coverage |
| SYSC-pci_bus | `pci_bus` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-platform-profile | `platform-profile` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-power | `power` | ABI-doc | — | 2 | researched | — | —remaining-coverage |
| SYSC-power_supply | `power_supply` | live@5.10.134 + ABI-doc | 0 | 82 | documented | — | —ABI |
| SYSC-powercap | `powercap` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-pps | `pps` | live@5.10.134 + ABI-doc | 0 | 8 | researched | — | —remaining-coverage |
| SYSC-pps-gen | `pps-gen` | ABI-doc | — | 6 | researched | — | —remaining-coverage |
| SYSC-ptp | `ptp` | live@5.10.134 + ABI-doc | 1 | 16 | researched | — | —remaining-coverage |
| SYSC-pwm | `pwm` | ABI-doc | — | 11 | documented | — | —ABI |
| SYSC-rapidio_port | `rapidio_port` | ABI-doc | — | 2 | researched | — | —remaining-coverage |
| SYSC-rc | `rc` | ABI-doc | — | 9 | researched | — | —remaining-coverage |
| SYSC-reboot-mode | `reboot-mode` | ABI-doc | — | 1 | researched | — | —remaining-coverage |
| SYSC-regulator | `regulator` | ABI-doc | — | 33 | documented | — | —ABI |
| SYSC-remoteproc | `remoteproc` | ABI-doc | — | 5 | researched | — | —remaining-coverage |
| SYSC-rfkill | `rfkill` | ABI-doc | — | 7 | researched | — | —remaining-coverage |
| SYSC-rnbd-client | `rnbd-client` | ABI-doc | — | 2 | researched | — | —remaining-coverage |
| SYSC-rnbd-server | `rnbd-server` | ABI-doc | — | 7 | researched | — | —remaining-coverage |
| SYSC-rtc | `rtc` | ABI-doc | — | 12 | researched | — | —remaining-coverage |
| SYSC-rtrs-client | `rtrs-client` | ABI-doc | — | 17 | researched | — | —remaining-coverage |
| SYSC-rtrs-server | `rtrs-server` | ABI-doc | — | 7 | researched | — | —remaining-coverage |
| SYSC-scsi_device | `scsi_device` | live@5.10.134 + ABI-doc | 0 | 15 | researched | — | —remaining-coverage |
| SYSC-scsi_disk | `scsi_disk` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-scsi_generic | `scsi_generic` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-scsi_host | `scsi_host` | live@5.10.134 + ABI-doc | 0 | 26 | researched | — | —remaining-coverage |
| SYSC-scsi_tape | `scsi_tape` | ABI-doc | — | 10 | researched | — | —remaining-coverage |
| SYSC-spi_master | `spi_master` | ABI-doc | — | 5 | researched | — | —remaining-coverage |
| SYSC-srp_remote_ports | `srp_remote_ports` | ABI-doc | — | 7 | researched | — | —remaining-coverage |
| SYSC-stm | `stm` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-stm_source | `stm_source` | ABI-doc | — | 1 | researched | — | —remaining-coverage |
| SYSC-switchtec | `switchtec` | ABI-doc | — | 10 | researched | — | —remaining-coverage |
| SYSC-tee | `tee` | ABI-doc | — | 2 | researched | — | —remaining-coverage |
| SYSC-thermal | `thermal` | live@5.10.134 + ABI-doc | 0 | 27 | documented | — | —ABI |
| SYSC-timecard | `timecard` | ABI-doc | — | 37 | researched | — | —remaining-coverage |
| SYSC-tpm | `tpm` | live@5.10.134 + ABI-doc | 0 | 20 | researched | — | —remaining-coverage |
| SYSC-tpmrm | `tpmrm` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-tsm | `tsm` | ABI-doc | — | 1 | researched | — | —remaining-coverage |
| SYSC-tty | `tty` | live@5.10.134 + ABI-doc | 70 | 17 | documented | — | —Full |
| SYSC-typec | `typec` | ABI-doc | — | 36 | researched | — | —remaining-coverage |
| SYSC-uacce | `uacce` | ABI-doc | — | 8 | researched | — | —remaining-coverage |
| SYSC-ubi | `ubi` | ABI-doc | — | 25 | researched | — | —remaining-coverage |
| SYSC-ubiX | `ubiX` | ABI-doc | — | 1 | researched | — | —remaining-coverage |
| SYSC-udc | `udc` | ABI-doc | — | 12 | researched | — | —remaining-coverage |
| SYSC-uio | `uio` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-usb_power_delivery | `usb_power_delivery` | ABI-doc | — | 36 | researched | — | —remaining-coverage |
| SYSC-usb_role | `usb_role` | ABI-doc | — | 3 | researched | — | —remaining-coverage |
| SYSC-vc | `vc` | live@5.10.134 | 6 | 0 | source-limited | — | —No |
| SYSC-vduse | `vduse` | ABI-doc | — | 4 | researched | — | —remaining-coverage |
| SYSC-virtio-ports | `virtio-ports` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-vtconsole | `vtconsole` | live@5.10.134 | 1 | 0 | researched | — | —remaining-coverage |
| SYSC-vvu | `vvu` | live@5.10.134 | 0 | 0 | researched | — | —remaining-coverage |
| SYSC-wakeup | `wakeup` | ABI-doc | — | 11 | researched | — | —remaining-coverage |
| SYSC-watchdog | `watchdog` | ABI-doc | — | 13 | researched | — | —remaining-coverage |
| SYSC-zram-control | `zram-control` | live@5.10.134 + ABI-doc | 2 | 3 | researched | — | —remaining-coverage |

Total classes: 120 (live: 46, ABI-documented: 95).

## sysfs interfaces that are not classes

The kernel also exposes structured state at other sysfs locations. These are
tracked here so they are not misclassified as classes (see the
[overview](./overview.md) for the taxonomy and how `/sys/class` symlinks
relate to `/sys/devices`):

| Prefix | Documented paths (count) | Chapter | Notes |
|---|---|---|---|
| `/sys/bus/*` | 60 | — | — |
| `/sys/devices/*` | 19 | — | — |
| `/sys/firmware/*` | 19 | — | — |
| `/sys/fs/*` | 12 | — | — |
| `/sys/kernel/*` | 35 | — | — |
| `/sys/module/*` | 7 | — | — |
