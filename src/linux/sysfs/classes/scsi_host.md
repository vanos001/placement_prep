# /sys/class/scsi_host

| Field | Value |
|---|---|
| Subsystem | SCSI midlayer per-host class; documented attributes are driver/transport additions (libata/AHCI, isci, hpsa, ib_srp); core implementation file not in cached tree |
| Config gate | ib_srp host attributes: `INFINIBAND_SRP` (fetched `srp-Kconfig`, depends on SCSI && INFINIBAND_ADDR_TRANS, selects SCSI_SRP_ATTRS); the libata/AHCI/isci/hpsa attributes' config symbols are not verifiable from the cached tree (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-scsi_host` (11 entries) and `Documentation/ABI/stable/sysfs-driver-ib_srp` (15 `/sys/class/scsi_host` entries) |
| Since | 2.6.24 (`link_power_management_policy`) through 3.19 (`ch_count`); see attribute table |
| Live (5.10.134 host) | class present with 0 entries: `/sys/class/scsi_host` exists but is empty (no SCSI host adapter in the container) |
| Ledger ID | SYSC-scsi_host |

## What it represents

One directory `hostX` per SCSI host adapter instance -- the object a SCSI LLDD registers with the midlayer. The generic midlayer attributes of hosts are not covered by any cached ABI file; what the cached tree documents are driver-specific additions: libata/AHCI enclosure-management and capability views, an Intel SCU controller id, an HP Smart Array SSD Smart Path switch, the SATA link power management policy, and the ib_srp per-connection state after an SRP login.

## Relationship to the device model

`hostX` is the top object of the SCSI hierarchy: targets and LUNs below it surface as scsi_device and block children, and transport layers layer attributes onto the same hosts (ib_srp documents its 15 host attributes in the same file as the `infiniband_srp` class attributes; FC hosts get a parallel `fc_host` view). For ib_srp, `add_target` on the initiator class creates the host whose parameters these attributes report.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `hostX/link_power_management_policy` | RW | min_power, max_performance, medium_power, med_power_with_dipm | SATA (libata) hosts | ABI testing `sysfs-class-scsi_host`, since 2.6.24 |
| `hostX/em_message` / `em_message_type` | RW / RO | enclosure management LED message per AHCI spec / protocol (LED, SAF-TE, SES-2, SGPIO) | AHCI hosts with EM | ABI testing `sysfs-class-scsi_host`, since 2.6.27 |
| `hostX/em_buffer` | RW | direct access to the AHCI EM buffer | AHCI hosts with EM, since 2.6.35 | ABI testing `sysfs-class-scsi_host` |
| `hostX/em_message_supported` | RO | supported EM message types | AHCI hosts, since 2.6.39 | ABI testing `sysfs-class-scsi_host` |
| `hostX/ahci_host_caps`, `ahci_host_cap2`, `ahci_port_cmd` | RO | register dumps; ABI text "[to be documented]" | AHCI hosts, since 2.6.35 | ABI testing `sysfs-class-scsi_host` |
| `hostX/ahci_host_version` | RO | AHCI spec version implemented by the host | AHCI hosts, since 2.6.35 | ABI testing `sysfs-class-scsi_host` |
| `hostX/isci_id` | RO | 0 or 1, Intel SCU controller index | isci driver, since June 2011 | ABI testing `sysfs-class-scsi_host` |
| `hostX/acciopath_status` | RW | 0/1 SSD Smart Path feature status (hpsa) | hpsa hosts, since Nov 2013 | ABI testing `sysfs-class-scsi_host` |
| `hostX/{allow_ext_sg,ch_count,cmd_sg_entries,comp_vector,dgid,id_ext,ioc_guid,local_ib_device,local_ib_port,orig_dgid,pkey,req_lim,service_id,sgid,zero_req_lim}` | RO (readability not stated in ABI) | SRP connection state view; values set via `add_target` | ib_srp hosts, 2.6.17-3.19 | ABI stable `sysfs-driver-ib_srp` |

## Safety and writes

Reads are safe. Documented writes: `link_power_management_policy` trades latency for power (min_power may sacrifice performance); `em_message` writes LED control messages -- the ABI requires turning `sw_activity` (under `/sys/block/*/device/`) OFF first; `acciopath_status` toggles controller-wide direct I/O. Capability requirements (root) follow from normal sysfs file permissions; nothing further is stated in the ABI files.

## References

- `Documentation/ABI/testing/sysfs-class-scsi_host`, `Documentation/ABI/stable/sysfs-driver-ib_srp` (cached copies)
- [sysfs-class-scsi_host online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-scsi_host), [sysfs-driver-ib_srp online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/stable/sysfs-driver-ib_srp)
- Fetched `srp-Kconfig`; `source-cache/sysfs-attrs.json` scsi_host entry (26 paths, all from the two ABI files)
- Companion pages: [infiniband_srp](./infiniband_srp.md), [scsi_device](./scsi_device.md), [fc_host](./fc_host.md), [bsg](./bsg.md)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-scsi_host
