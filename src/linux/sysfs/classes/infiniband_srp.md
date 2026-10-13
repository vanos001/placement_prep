# /sys/class/infiniband_srp

| Field | Value |
|---|---|
| Subsystem | SRP initiator, drivers/infiniband/ulp/srp/ib_srp.c (class `srp_class`, name "infiniband_srp") |
| Config gate | CONFIG_INFINIBAND_SRP, depends on SCSI and INFINIBAND_ADDR_TRANS, selects SCSI_SRP_ATTRS (drivers/infiniband/ulp/srp/Kconfig) |
| ABI documentation | Documentation/ABI/stable/sysfs-driver-ib_srp |
| Since | 2.6.15 (entries dated January 2, 2006) |
| Live (5.10.134 host) | none observed (no RDMA hardware in the container) |
| Ledger ID | SYSC-infiniband_srp |

## What it represents

One device per initiator port (`srp-<hca>-<port_number>`) through which the ib_srp driver connects to SRP targets. Writing to `add_target` is the connection control point; the resulting SCSI hosts carry their own state files under /sys/class/scsi_host, documented in the same ABI file.

## Relationship to the device model

Class devices sit above the infiniband.md HCA devices named by `ibdev`/`port` and below the SCSI transport: each successful add_target creates a SCSI host whose block devices appear in the usual block and SCSI trees. See infiniband.md for the HCA layer and the storage page for the SRP protocol role.

## Attributes (source: ABI stable/sysfs-driver-ib_srp; class code ib_srp.c)

| Attribute | R/W | Meaning |
|---|---|---|
| `add_target` | WO | Comma-separated login parameters: id_ext, ioc_guid, dgid, pkey, service_id, max_sect, max_cmd_per_lun, io_class, initiator_ext, cmd_sg_entries, allow_ext_sg, sg_tablesize, comp_vector, tl_retry_count, queue_size, max_it_iu_size |
| `ibdev` | RO | HCA name (`<hca>`) |
| `port` | RO | HCA port number |

Per-connection state lives on the created SCSI hosts instead: allow_ext_sg, ch_count, cmd_sg_entries, comp_vector, dgid, id_ext, ioc_guid, local_ib_device, local_ib_port, orig_dgid, pkey, req_lim, service_id, sgid, zero_req_lim (all documented in sysfs-driver-ib_srp as /sys/class/scsi_host/host<n>/ entries).

## Safety and writes

`add_target` initiates a fabric login; wrong parameters can connect to the wrong target, so both dgid/ioc_guid and service_id must match the target's advertised identity. queue_size minimum is 2, default 62; io_class must be 0xff00 (rev 10) or 0x0100 (rev 16a). None observed on the container host.

## References

- Documentation/ABI/stable/sysfs-driver-ib_srp
- drivers/infiniband/ulp/srp/ib_srp.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [InfiniBand storage page](../../storage/infiniband.md), [infiniband](./infiniband.md)
