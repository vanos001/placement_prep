# /sys/class/infiniband_verbs

| Field | Value |
|---|---|
| Subsystem | RDMA userspace verbs access, drivers/infiniband/core/uverbs_main.c (class `uverbs_class`, name "infiniband_verbs") |
| Config gate | CONFIG_INFINIBAND_USER_ACCESS, "InfiniBand userspace access (verbs and CM)", depends on MMU (drivers/infiniband/Kconfig) |
| ABI documentation | Documentation/ABI/stable/sysfs-class-infiniband (uverbs section, 3 What: entries) |
| Since | v2.6.14 (entries dated Sept 2005) |
| Live (5.10.134 host) | none observed (no RDMA hardware in the container) |
| Ledger ID | SYSC-infiniband_verbs |

## What it represents

One device per RDMA device exposing the verbs char interface: `uverbs<N>` nodes through which libibverbs issues command queues against the HCA. The class-level `abi_version` is bumped when a change breaks the uverbs userspace ABI.

## Relationship to the device model

Devices are named uverbs%d (uverbs_main.c dev_set_name) with devnode "infiniband/%s", so nodes land in /dev/infiniband/uverbsN next to the umad nodes of infiniband_mad.md. `ibdev` ties each node back to its /sys/class/infiniband device.

## Attributes (source: ABI stable/sysfs-class-infiniband; class code uverbs_main.c)

| Attribute | R/W | Meaning |
|---|---|---|
| `abi_version` | RO | Class attr; incremented on uverbs ABI-breaking changes (uverbs_main.c class_create_file) |
| `uverbs<N>/ibdev` | RO | InfiniBand device name served by this node |
| `uverbs<N>/abi_version` | RO | ABI version of the IB device specific interfaces |

## Safety and writes

All attributes are read-only. Note one source-visible detail: the uverbs devnode callback sets the device node mode to 0666 (uverbs_main.c uverbs_devnode), which is why verbs access control is normally layered with rdma-core and rdma groups rather than node permissions. None observed on the container host.

## References

- Documentation/ABI/stable/sysfs-class-infiniband
- drivers/infiniband/core/uverbs_main.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [InfiniBand storage page](../../storage/infiniband.md), [infiniband](./infiniband.md), [infiniband_mad](./infiniband_mad.md)
