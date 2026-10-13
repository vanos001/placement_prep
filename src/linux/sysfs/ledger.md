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
| SYSC-accel | `accel` | ABI-doc | — | 34 | source-limited | [./classes/accel.md](./classes/accel.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-ata_device | `ata_device` | ABI-doc | — | 9 | documented | [./classes/ata_device.md](./classes/ata_device.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-ata_link | `ata_link` | ABI-doc | — | 3 | documented | [./classes/ata_link.md](./classes/ata_link.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-ata_port | `ata_port` | ABI-doc | — | 3 | documented | [./classes/ata_port.md](./classes/ata_port.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-backlight | `backlight` | live@5.10.134 + ABI-doc | 0 | 15 | documented | — | —ABI |
| SYSC-bdi | `bdi` | live@5.10.134 + ABI-doc | 9 | 10 | documented | — | —Full |
| SYSC-block | `block` | live@5.10.134 + ABI-doc | 4 | 171 | documented | — | —Full |
| SYSC-bluetooth | `bluetooth` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-bsg | `bsg` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-bsr | `bsr` | ABI-doc | — | 3 | documented | [./classes/bsr.md](./classes/bsr.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-c2port | `c2port` | ABI-doc | — | 11 | documented | [./classes/c2port.md](./classes/c2port.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-chromeos | `chromeos` | ABI-doc | — | 14 | documented | [./classes/chromeos.md](./classes/chromeos.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-cpuid | `cpuid` | live@5.10.134 | 2 | 0 | documented | — | —chapter |
| SYSC-cxl | `cxl` | ABI-doc | — | 23 | documented | [./classes/cxl.md](./classes/cxl.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-devfreq | `devfreq` | ABI-doc | — | 14 | documented | [./classes/devfreq.md](./classes/devfreq.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-devfreq-event | `devfreq-event` | ABI-doc | — | 3 | documented | [./classes/devfreq-event.md](./classes/devfreq-event.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-devlink | `devlink` | live@5.10.134 + ABI-doc | 0 | 7 | documented | — | —chapter |
| SYSC-drm | `drm` | live@5.10.134 + ABI-doc | 1 | 1 | documented | — | —chapter |
| SYSC-extcon | `extcon` | ABI-doc | — | 6 | documented | [./classes/extcon.md](./classes/extcon.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-fc | `fc` | ABI-doc | — | 1 | documented | [./classes/fc.md](./classes/fc.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-fc_host | `fc_host` | ABI-doc | — | 3 | documented | [./classes/fc_host.md](./classes/fc_host.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-fc_remote_ports | `fc_remote_ports` | ABI-doc | — | 3 | documented | [./classes/fc_remote_ports.md](./classes/fc_remote_ports.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-firmware | `firmware` | ABI-doc | — | 7 | documented | — | —chapter |
| SYSC-firmware-attributes | `firmware-attributes` | ABI-doc | — | 11 | documented | [./classes/firmware-attributes.md](./classes/firmware-attributes.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-fpga_bridge | `fpga_bridge` | ABI-doc | — | 2 | documented | — | —chapter |
| SYSC-fpga_manager | `fpga_manager` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-fpga_region | `fpga_region` | ABI-doc | — | 1 | documented | — | —chapter |
| SYSC-genwqe | `genwqe` | ABI-doc | — | 12 | documented | [./classes/genwqe.md](./classes/genwqe.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-gism_class | `gism_class` | live@5.10.134 | 1 | 0 | source-limited | [./classes/gism_class.md](./classes/gism_class.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-gnss | `gnss` | ABI-doc | — | 1 | documented | [./classes/gnss.md](./classes/gnss.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-gpio | `gpio` | ABI-doc | — | 1 | documented | — | —DEPRECATED: |
| SYSC-graphics | `graphics` | live@5.10.134 | 1 | 0 | documented | — | —chapter |
| SYSC-hidraw | `hidraw` | ABI-doc | — | 2 | documented | [./classes/hidraw.md](./classes/hidraw.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-hwmon | `hwmon` | live@5.10.134 + ABI-doc | 0 | 120 | documented | — | —ABI |
| SYSC-i2c-adapter | `i2c-adapter` | live@5.10.134 | 0 | 0 | documented | — | —no |
| SYSC-ieee80211 | `ieee80211` | ABI-doc | — | 2 | source-limited | [./classes/ieee80211.md](./classes/ieee80211.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-infiniband | `infiniband` | ABI-doc | — | 122 | documented | — | —chapter |
| SYSC-infiniband_mad | `infiniband_mad` | ABI-doc | — | 5 | documented | — | —chapter |
| SYSC-infiniband_srp | `infiniband_srp` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-infiniband_verbs | `infiniband_verbs` | ABI-doc | — | 3 | documented | — | —chapter |
| SYSC-input | `input` | live@5.10.134 + ABI-doc | 2 | 3 | documented | — | —chapter |
| SYSC-intel_pmt | `intel_pmt` | ABI-doc | — | 14 | documented | [./classes/intel_pmt.md](./classes/intel_pmt.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-iommu | `iommu` | live@5.10.134 + ABI-doc | 0 | 7 | documented | [./classes/iommu.md](./classes/iommu.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-iscsi_connection | `iscsi_connection` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_endpoint | `iscsi_endpoint` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_host | `iscsi_host` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_iface | `iscsi_iface` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_session | `iscsi_session` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-iscsi_transport | `iscsi_transport` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-issei | `issei` | ABI-doc | — | 9 | documented | [./classes/issei.md](./classes/issei.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-lcd | `lcd` | ABI-doc | — | 3 | documented | [./classes/lcd.md](./classes/lcd.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-leds | `leds` | ABI-doc | — | 96 | documented | — | —ABI |
| SYSC-macvtap | `macvtap` | live@5.10.134 | 0 | 0 | source-limited | [./classes/macvtap.md](./classes/macvtap.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-mdio_bus | `mdio_bus` | ABI-doc | — | 16 | documented | [./classes/mdio_bus.md](./classes/mdio_bus.md) | ——chapter |
| SYSC-mei | `mei` | ABI-doc | — | 10 | documented | [./classes/mei.md](./classes/mei.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-mem | `mem` | live@5.10.134 | 8 | 0 | documented | — | —chapter |
| SYSC-mic | `mic` | ABI-doc | — | 13 | documented | [./classes/mic.md](./classes/mic.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-misc | `misc` | live@5.10.134 + ABI-doc | 75 | 2 | documented | — | —chapter |
| SYSC-msr | `msr` | live@5.10.134 | 2 | 0 | documented | — | —chapter |
| SYSC-mtd | `mtd` | ABI-doc | — | 22 | documented | — | —chapter |
| SYSC-mux | `mux` | ABI-doc | — | 2 | documented | [./classes/mux.md](./classes/mux.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-nd | `nd` | live@5.10.134 | 1 | 0 | documented | — | —chapter |
| SYSC-net | `net` | live@5.10.134 + ABI-doc | 3 | 96 | documented | — | —Full |
| SYSC-nvme | `nvme` | live@5.10.134 + ABI-doc | 0 | 39 | documented | — | —Entry |
| SYSC-nvme-generic | `nvme-generic` | live@5.10.134 | 0 | 0 | source-limited | [./classes/nvme-generic.md](./classes/nvme-generic.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-nvme-subsystem | `nvme-subsystem` | live@5.10.134 + ABI-doc | 0 | 6 | documented | [./classes/nvme-subsystem.md](./classes/nvme-subsystem.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-ocxl | `ocxl` | ABI-doc | — | 1 | documented | [./classes/ocxl.md](./classes/ocxl.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-pci_bus | `pci_bus` | live@5.10.134 | 0 | 0 | source-limited | [./classes/pci_bus.md](./classes/pci_bus.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-platform-profile | `platform-profile` | ABI-doc | — | 3 | documented | [./classes/platform-profile.md](./classes/platform-profile.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-power | `power` | ABI-doc | — | 2 | source-limited | [./classes/power.md](./classes/power.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-power_supply | `power_supply` | live@5.10.134 + ABI-doc | 0 | 82 | documented | — | —ABI |
| SYSC-powercap | `powercap` | ABI-doc | — | 3 | documented | [./classes/powercap.md](./classes/powercap.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-pps | `pps` | live@5.10.134 + ABI-doc | 0 | 8 | documented | [./classes/pps.md](./classes/pps.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-pps-gen | `pps-gen` | ABI-doc | — | 6 | documented | [./classes/pps-gen.md](./classes/pps-gen.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-ptp | `ptp` | live@5.10.134 + ABI-doc | 1 | 16 | documented | [./classes/ptp.md](./classes/ptp.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-pwm | `pwm` | ABI-doc | — | 11 | documented | — | —ABI |
| SYSC-rapidio_port | `rapidio_port` | ABI-doc | — | 2 | documented | [./classes/rapidio_port.md](./classes/rapidio_port.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-rc | `rc` | ABI-doc | — | 9 | documented | [./classes/rc.md](./classes/rc.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-reboot-mode | `reboot-mode` | ABI-doc | — | 1 | documented | [./classes/reboot-mode.md](./classes/reboot-mode.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-regulator | `regulator` | ABI-doc | — | 33 | documented | — | —ABI |
| SYSC-remoteproc | `remoteproc` | ABI-doc | — | 5 | documented | [./classes/remoteproc.md](./classes/remoteproc.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-rfkill | `rfkill` | ABI-doc | — | 7 | documented | [./classes/rfkill.md](./classes/rfkill.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-rnbd-client | `rnbd-client` | ABI-doc | — | 2 | documented | [./classes/rnbd-client.md](./classes/rnbd-client.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-rnbd-server | `rnbd-server` | ABI-doc | — | 7 | documented | [./classes/rnbd-server.md](./classes/rnbd-server.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-rtc | `rtc` | ABI-doc | — | 12 | documented | [./classes/rtc.md](./classes/rtc.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-rtrs-client | `rtrs-client` | ABI-doc | — | 17 | documented | [./classes/rtrs-client.md](./classes/rtrs-client.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-rtrs-server | `rtrs-server` | ABI-doc | — | 7 | documented | [./classes/rtrs-server.md](./classes/rtrs-server.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-scsi_device | `scsi_device` | live@5.10.134 + ABI-doc | 0 | 15 | documented | [./classes/scsi_device.md](./classes/scsi_device.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-scsi_disk | `scsi_disk` | live@5.10.134 | 0 | 0 | source-limited | [./classes/scsi_disk.md](./classes/scsi_disk.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-scsi_generic | `scsi_generic` | live@5.10.134 | 0 | 0 | source-limited | [./classes/scsi_generic.md](./classes/scsi_generic.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-scsi_host | `scsi_host` | live@5.10.134 + ABI-doc | 0 | 26 | documented | [./classes/scsi_host.md](./classes/scsi_host.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-scsi_tape | `scsi_tape` | ABI-doc | — | 10 | documented | [./classes/scsi_tape.md](./classes/scsi_tape.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-spi_master | `spi_master` | ABI-doc | — | 5 | documented | [./classes/spi_master.md](./classes/spi_master.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-srp_remote_ports | `srp_remote_ports` | ABI-doc | — | 7 | documented | [./classes/srp_remote_ports.md](./classes/srp_remote_ports.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-stm | `stm` | ABI-doc | — | 3 | documented | [./classes/stm.md](./classes/stm.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-stm_source | `stm_source` | ABI-doc | — | 1 | documented | [./classes/stm_source.md](./classes/stm_source.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-switchtec | `switchtec` | ABI-doc | — | 10 | documented | [./classes/switchtec.md](./classes/switchtec.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-tee | `tee` | ABI-doc | — | 2 | documented | [./classes/tee.md](./classes/tee.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-thermal | `thermal` | live@5.10.134 + ABI-doc | 0 | 27 | documented | — | —ABI |
| SYSC-timecard | `timecard` | ABI-doc | — | 37 | documented | [./classes/timecard.md](./classes/timecard.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-tpm | `tpm` | live@5.10.134 + ABI-doc | 0 | 20 | documented | [./classes/tpm.md](./classes/tpm.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-tpmrm | `tpmrm` | live@5.10.134 | 0 | 0 | source-limited | [./classes/tpmrm.md](./classes/tpmrm.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-tsm | `tsm` | ABI-doc | — | 1 | source-limited | [./classes/tsm.md](./classes/tsm.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-tty | `tty` | live@5.10.134 + ABI-doc | 70 | 17 | documented | — | —Full |
| SYSC-typec | `typec` | ABI-doc | — | 36 | documented | [./classes/typec.md](./classes/typec.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-uacce | `uacce` | ABI-doc | — | 8 | documented | [./classes/uacce.md](./classes/uacce.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-ubi | `ubi` | ABI-doc | — | 25 | documented | [./classes/ubi.md](./classes/ubi.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-ubiX | `ubiX` | ABI-doc | — | 1 | documented | [./classes/ubiX.md](./classes/ubiX.md) | —wave 7-b page: ABI-sourced attribute table; device-dir layout sibling of ubi.md |
| SYSC-udc | `udc` | ABI-doc | — | 12 | documented | [./classes/udc.md](./classes/udc.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-uio | `uio` | live@5.10.134 | 0 | 0 | documented | [./classes/uio.md](./classes/uio.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-usb_power_delivery | `usb_power_delivery` | ABI-doc | — | 36 | documented | [./classes/usb_power_delivery.md](./classes/usb_power_delivery.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-usb_role | `usb_role` | ABI-doc | — | 3 | documented | [./classes/usb_role.md](./classes/usb_role.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-vc | `vc` | live@5.10.134 | 6 | 0 | source-limited | — | —No |
| SYSC-vduse | `vduse` | ABI-doc | — | 4 | documented | [./classes/vduse.md](./classes/vduse.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-virtio-ports | `virtio-ports` | live@5.10.134 | 0 | 0 | documented | — | —chapter |
| SYSC-vtconsole | `vtconsole` | live@5.10.134 | 1 | 0 | source-limited | [./classes/vtconsole.md](./classes/vtconsole.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-vvu | `vvu` | live@5.10.134 | 0 | 0 | source-limited | [./classes/vvu.md](./classes/vvu.md) | —wave 7-b page: honest stub, thin/no ABI sources |
| SYSC-wakeup | `wakeup` | ABI-doc | — | 11 | documented | [./classes/wakeup.md](./classes/wakeup.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-watchdog | `watchdog` | ABI-doc | — | 13 | documented | [./classes/watchdog.md](./classes/watchdog.md) | —wave 7-b page: ABI-sourced attribute table |
| SYSC-zram-control | `zram-control` | live@5.10.134 + ABI-doc | 2 | 3 | documented | [./classes/zram-control.md](./classes/zram-control.md) | —wave 7-b page: ABI-sourced attribute table |

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
