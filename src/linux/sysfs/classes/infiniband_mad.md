# /sys/class/infiniband_mad

| Field | Value |
|---|---|
| Subsystem | RDMA userspace MAD access, drivers/infiniband/core/user_mad.c (class `umad_class`, name "infiniband_mad") |
| Config gate | CONFIG_INFINIBAND_USER_MAD, "InfiniBand userspace MAD support", depends on INFINIBAND (drivers/infiniband/Kconfig) |
| ABI documentation | Documentation/ABI/stable/sysfs-class-infiniband (umad/issm section, 5 What: entries) |
| Since | v2.6.12 (all entries, dated Apr 2005) |
| Live (5.10.134 host) | none observed (no RDMA hardware in the container) |
| Ledger ID | SYSC-infiniband_mad |

## What it represents

One device per port of each InfiniBand device for management-datagram access: `umad<N>` for MAD traffic and `issm<N>` for the subnet-manager port bit. A two-port HCA gets two umad and two issm devices; a switch gets one of each for port 0 (ABI description). The class-level `abi_version` counts user-visible ABI breaks.

## Relationship to the device model

Class devices are named umad%d and issm%d (user_mad.c dev_set_name) and carry the devnode callback "infiniband/%s", so the char device nodes land in /dev/infiniband/. Each umad/issm device is associated with one port of the HCA named by its `ibdev` attribute.

## Attributes (source: ABI stable/sysfs-class-infiniband; class code user_mad.c)

| Attribute | R/W | Meaning |
|---|---|---|
| `abi_version` | RO | Class attr; incremented when umad/issm userspace ABI compatibility breaks (user_mad.c returns IB_USER_MAD_ABI_VERSION) |
| `umad<N>/ibdev` | RO | InfiniBand device name this port belongs to |
| `umad<N>/port` | RO | Port number |
| `issm<N>/ibdev` | RO | InfiniBand device name |
| `issm<N>/port` | RO | Port number |

## Safety and writes

All five attributes are read-only. Opening the issm device sets the IsSM bit in the port capability mask (documented in the infiniband.md cap_mask row); MAD traffic itself flows through /dev/infiniband/umadN. None observed on the container host.

## References

- Documentation/ABI/stable/sysfs-class-infiniband
- drivers/infiniband/core/user_mad.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [InfiniBand storage page](../../storage/infiniband.md), [infiniband](./infiniband.md), [infiniband_verbs](./infiniband_verbs.md)
