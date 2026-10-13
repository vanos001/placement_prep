# /sys/class/devlink

| Field | Value |
|---|---|
| Subsystem | Driver core; drivers/base/core.c (devlink_class, device_link_add) |
| Config gate | None; drivers/base is obj-y and the class registers from postcore_initcall(devlink_class_init) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-devlink (7 What: entries) |
| Since | May 2020 (all entries) |
| Live (5.10.134 host) | 0 entries (no device links registered; empty directory) |
| Ledger ID | SYSC-devlink |

## What it represents

The sysfs view of device links: ordered dependencies between a supplier
device and a consumer device that the driver core enforces for probe order,
suspend/resume ordering, runtime PM and sync_state. Each link is a class
device named <supplier-bus:name>--<consumer-bus:name> (dev_set_name format
"%s:%s--%s:%s" in device_link_add()). The class exists whenever the driver
core does, but the population is nonempty only when code has called
device_link_add() or device_link_add_deps, typically on hardware platforms
with firmware-described dependencies (firmware nodes, interconnects, PM
domains); simple containers and desktop boxes often have none, hence the
empty live directory.

## Relationship to the device model

The link_dev belongs to devlink_class and is not parented under either
endpoint; instead the class device carries two symlinks (supplier and
consumer, ABI entries) pointing back at the endpoint directories, and the
endpoint directories in turn get symmetric link-representation files under
their supplier_links/ and consumer_links/ subdirectories. The class device
exposes the four read-only attributes below; the state machine behind the
status file (dormant, available, consumer probing, active, supplier
unbinding) is advanced by the driver core as endpoints bind and unbind.

Name collision warning (worklog 2-e): this class has nothing to do with the
devlink netlink family used by the iproute2 `devlink` tool for switch
management (net/devlink/core.c, generic netlink family "devlink"). Same
word, different subsystems: one is driver-core device links, the other is a
networking control plane.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| status | RO | not tracked, dormant, available, consumer probing, active, supplier unbinding, unknown | ABI, May 2020; core.c DEVICE_ATTR_RO(status) |
| auto_remove_on | RO | consumer unbind, supplier unbind, or never | ABI, May 2020 |
| runtime_pm | RO | 0 (no PM impact) or 1 (affects runtime PM) | ABI, May 2020 |
| sync_state_only | RO | 0 or 1 (limits link to sync_state only) | ABI, May 2020 |
| supplier | symlink | to supplier device directory | ABI, May 2020 |
| consumer | symlink | to consumer device directory | ABI, May 2020 |

All four attributes are DEVICE_ATTR_RO in core.c; there is nothing writable
anywhere in the class. The ABI directory name spells /sys/class/devlink/
and the seven What: entries cover the directory itself plus the six files
above.

## Safety and writes

There is nothing to write: links are created and dropped by the kernel
through device_link_add()/device_link_del(), not by userspace. Reading
status is safe and is the main diagnostic (a link stuck in dormant while
its consumer waits can explain deferred probes; waiting_for_supplier in the
consumer's own directory, driver core attr, complements it). Do not confuse
this tree with the networking devlink netlink family when writing tooling
or documentation: grepping for "devlink" hits both.

## References

- Documentation/ABI/testing/sysfs-class-devlink (cached at source-cache/linux-sparse)
- drivers/base/core.c (devlink_class, devlink_attrs, device_link_add), net/devlink/core.c (the unrelated netlink family), fetched from raw.githubusercontent.com/torvalds/linux/master
- Live enumeration /sys/class/devlink (empty, read-only, kernel 5.10.134)
- Sibling pages: [net](./net.md), [nd](./nd.md); coverage: [ledger](../ledger.md)
