# /sys/class/infiniband

| Field | Value |
|---|---|
| Subsystem | RDMA/IB core, drivers/infiniband/core/device.c (class `ib_class`, name "infiniband") and core/sysfs.c (port and counter attrs) |
| Config gate | CONFIG_INFINIBAND |
| ABI documentation | Documentation/ABI/stable/sysfs-class-infiniband (130 What: entries) |
| Since | Core device and port attrs v2.6.12; `fw_ver` 4.10; `link_layer` 2.6.37; hw_counters 4.6; gid_attrs 4.4 (dates from the ABI file) |
| Live (5.10.134 host) | none observed (no RDMA hardware in the container; class absent from the cached enumeration) |
| Ledger ID | SYSC-infiniband |

## What it represents

One device per RDMA/InfiniBand HCA (or usNIC, RoCE-capable NIC, qib/hfi1 adapter) registered by its low-level driver, with per-port and per-counter subdirectories. Sibling classes: infiniband_mad.md (umad/issm devices), infiniband_verbs.md (uverbs devices), infiniband_srp.md (SRP initiator hosts).

## Relationship to the device model

Each class device is a child of the PCI (or platform) device of the HCA. Per-port subdirectories expose link state and counters; driver-specific sections of the ABI file add files per adapter family (mthca, mlx4, mlx5, cxgb4, qib, hfi1, usnic, ocrdma, qedr, vmw_pvrdma, bnxt_re).

## Attributes (representative; the ABI file has 130 What: entries, here 12 rows)

| Attribute | R/W | Meaning (source: ABI stable/sysfs-class-infiniband) |
|---|---|---|
| `node_type`, `node_guid`, `sys_image_guid` | RO | Node type (CA, RNIC, switch, router); node and system image GUIDs (v2.6.12) |
| `node_desc` | RW | Node description, typically hostname, for IB network management (v2.6.17) |
| `fw_ver` | RO | Firmware version (v4.10) |
| `ports/<n>/lid`, `rate`, `lid_mask_count`, `sm_sl`, `sm_lid` | RO | Port LID, data rate (active width x speed), LID mask count, subnet manager SL and LID (v2.6.12) |
| `ports/<n>/state` | RO | DOWN, INIT, ARMED, ACTIVE or ACTIVE_DEFER |
| `ports/<n>/phys_state` | RO | Physical state: Sleep, Polling, LinkUp, etc |
| `ports/<n>/cap_mask` | RO | Port capability mask; two bits settable (IsCommunicationManagementSupported, IsSM) |
| `ports/<n>/link_layer` | RO | Infiniband or Ethernet link layer (v2.6.37) |
| `ports/<n>/counters/*` | RO | 21 counter files (symbol_error through port_xmit_wait) mirroring the IB PortCounters attribute |
| `hw_counters/lifespan` | RW | Cache refresh interval in ms, 0-10000, default 10 (v4.6) |
| `ports/<n>/gid_attrs/{ndevs,types}/<idx>` | RO | Netdev name and RoCE type (IB/RoCE v1 or RoCE v2) per GID index (v4.4) |
| `mthcaX/hw_rev`, `hca_type`, `board_id` (and per-driver equivalents) | RO | Hardware revision, HCA type, board id |

## Safety and writes

`node_desc` and `hw_counters/lifespan` are the documented write paths; everything else is read-only. Counter names contain intentional ABI quirks (for example `port_rcv_contraint_errors` and `VL15_dropped`) that tools parse literally. None observed on the container host.

## References

- Documentation/ABI/stable/sysfs-class-infiniband (remaining entries listed there)
- drivers/infiniband/core/device.c, core/sysfs.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [InfiniBand storage page](../../storage/infiniband.md), [infiniband_mad](./infiniband_mad.md), [infiniband_verbs](./infiniband_verbs.md), [infiniband_srp](./infiniband_srp.md)
