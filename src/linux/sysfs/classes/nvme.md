# /sys/class/nvme

| Field | Value |
|---|---|
| Subsystem | NVMe host driver; drivers/nvme/host/core.c (nvme_class) + drivers/nvme/host/sysfs.c (nvme_dev_attrs[]) |
| Config gate | CONFIG_NVME_CORE |
| ABI documentation | Documentation/ABI/stable/sysfs-nvme (66 What: entries; 39 at class level /sys/class/nvme/nvmeX/, the rest under /sys/block/nvmeXnY/ and /sys/class/nvme-subsystem/) |
| Since | January 2016 (KernelVersion 4.5: model, serial, firmware_rev) through 2026 entries in master |
| Live (5.10.134 host) | Class directory exists but is empty (0 controllers in this container); no live verification of attribute values |
| Ledger ID | SYSC-nvme |

## What it represents

One directory per NVMe controller (nvmeX). The class device carries the
controller identity (model, serial, firmware_rev), its transport parameters
(transport, address, subsysnqn for fabrics), its timeouts and reconnect
policy, and the two write-only maintenance triggers reset_controller and
rescan_controller. The per-namespace attributes documented in the same ABI
file (uuid, eui, nsid, wwid, nguid, ana_state, queue_depth, csi, nuse) are
NOT class attributes: they appear on the namespace block devices under
/sys/block/nvmeXnY/ and belong to the [block](./block.md) page.

## Relationship to the device model

nvme_class is registered in drivers/nvme/host/core.c; controller devices get
class = &nvme_class, a parent under the PCI or fabric device, and the attr
group nvme_dev_attrs_group from sysfs.c. Some attributes are hidden per
controller by nvme_dev_attrs_are_visible(): delete_controller requires
ctrl->ops->delete_ctrl, address requires ops->get_address, and hostnqn,
hostid, ctrl_loss_tmo, reconnect_delay, fast_io_fail_tmo plus the two
dhchap_secret files appear only for fabrics controllers (ctrl->opts set).
uevent adds NVME_TRTYPE, NVME_TRADDR and related variables. Sibling classes
nvme-subsystem (6 ABI entries: model, serial, firmware_rev, subsysnqn,
iopolicy, subsystype) and nvme-generic exist for multipath fabrics setups.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| model, serial, firmware_rev | RO | identify strings | ABI stable/sysfs-nvme, 4.5; sysfs.c nvme_id_show |
| cntlid | RO | controller id assigned by subsystem | ABI, 4.6 |
| state | RO | live/resetting/connecting/disconnecting/deleting/dead | ABI; sysfs.c nvme_sysfs_show_state |
| transport | RO | pcie, rdma, fc, tcp, loop | ABI; DEVICE_ATTR_RO(transport) |
| address | RO | transport address, fabrics only (visible callback) | ABI; sysfs.c |
| subsysnqn | RO | subsystem NQN | ABI |
| reset_controller, rescan_controller | WO | trigger controller reset/rescan | ABI; S_IWUSR only |
| delete_controller | WO | fabrics disconnect; hidden without ops->delete_ctrl | ABI; sysfs.c |
| ctrl_loss_tmo, reconnect_delay, fast_io_fail_tmo | RW | seconds; fabrics only | ABI |
| admin_timeout, io_timeout | RW | seconds, command timeouts | ABI; sysfs.c |
| kato | RO | keep-alive timeout, milliseconds | ABI |
| queue_count, sqsize | RO | I/O queue count and submission queue size | ABI |
| numa_node | RO | NUMA node of the device | ABI |
| hostnqn, hostid | RO | host identity, fabrics only | ABI |
| cmbloc, cmbsz, cmb, hmb | RO | controller memory buffer presence and size | ABI |
| quirks | RO | hex controller quirk flags | ABI; sysfs.c DEVICE_ATTR_RO(quirks) |
| dhchap_secret, dhchap_ctrl_secret | RW | NVMe in-band auth secrets; CONFIG_NVME_HOST_AUTH | ABI |
| passthru_err_log_enabled | RW | passthrough error log switch | ABI |
| diag/reset_count, diag/reconnect_count, diag/command_error_count | RW | diagnostic counters | ABI |

## Safety and writes

Reads are safe. The write-only files act on the controller: writing
reset_controller resets live NVMe hardware and rescan_controller re-reads the
namespace list; delete_controller detaches a fabrics controller. The
timeout/tuning files change recovery behavior of a storage device that a
mounted filesystem may be using. No attribute value on this page could be
read on the 5.10.134 host because the container has no NVMe device: live
presence, permission bits and value examples are unknown here, and this page
deliberately reports none.

## References

- Documentation/ABI/stable/sysfs-nvme (cached at source-cache/linux-sparse)
- drivers/nvme/host/core.c and drivers/nvme/host/sysfs.c, fetched from raw.githubusercontent.com/torvalds/linux/master
- Live enumeration /sys/class/nvme (empty, read-only, kernel 5.10.134)
- Sibling pages: [block](./block.md); coverage: [ledger](../ledger.md)
