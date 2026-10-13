# /sys/class/rnbd-client

| Field | Value |
|---|---|
| Subsystem | RNBD-client (RDMA Network Block Device, client side), over RTRS sessions; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-rnbd-client` (3 What: entries); mapped devices also documented in `Documentation/ABI/testing/sysfs-block-rnbd` |
| Since | 5.7 (Feb 2020, all entries) |
| Live (5.10.134 host) | class absent: /sys/class/rnbd-client does not exist in this container |
| Ledger ID | SYSC-rnbd-client |

## What it represents

The client-side control interface of RNBD, which maps a block device
exported by an RNBD server over an RTRS RDMA session. The class holds a
single ctl directory with the map_device writer and a devices/ tree of
symlinks, one per mapped device. Mapping is done entirely by writing a
formatted string to map_device; unmapping uses the per-block-device
unmap_device file documented in sysfs-block-rnbd, not in this class.

## Relationship to the device model

Successful mapping creates, per the ABI: a /dev/rnbdN device file, a
/sys/block/rnbdN/ directory (the block-device side, covered by
[block](./block.md) plus `sysfs-block-rnbd`), and a symlink
/sys/class/rnbd-client/ctl/devices/<device_id>@<session_name> pointing at
/sys/block/`<dev-name>`. The device_id is the device_path with slashes
replaced by exclamation marks. Sessions, paths, and multipath policy live in
the sibling RTRS classes ([rtrs-client](./rtrs-client.md),
[rtrs-server](./rtrs-server.md)).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| ctl/map_device | WO (usage on read) | map string: `sessname=<name> path=<[src,]dst> [path=...] device_path=<path on server> [access_mode=<ro\|rw\|migration>]`; reads return the usage text | always | ABI testing sysfs-class-rnbd-client, 5.7 |
| ctl/devices/ | RO | one symlink `<device_id>@<session_name>` per mapped device, pointing to /sys/block/rnbdN/ | per mapped device | ABI, 5.7 |

map_device options: path addresses are `ip:<ipv4>`, `ip:<ipv6>` or
`gid:<gid>`; multiple path= entries create multiple connections following the
RTRS mp_policy; nr_poll_queues sets poll-mode queues (-1 means number of
CPUs) and demands a unique session per device; default access_mode is rw and
the server allows rw export only once (second rw mapping needs migration).
Errors: EEXIST already mapped, EINVAL bad format, ENOENT path not on server.

## Safety and writes

Reading anything is safe (map_device answers with usage). Writing
map_device creates a block device backed by remote storage over RDMA;
getting sessname/device_path wrong fails as above. The ABI notes access
modes are enforced server-side (see [rnbd-server](./rnbd-server.md)).
Nothing is live here: no class directory in the container, so no live read
was done.

## References

- `Documentation/ABI/testing/sysfs-class-rnbd-client`, `Documentation/ABI/testing/sysfs-block-rnbd` (cached copies)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-rnbd-client
- sysfs-attrs.json entry `rnbd-client` (2 paths); live enumeration: class absent, kernel 5.10.134
- Related pages: [rtrs-client](./rtrs-client.md), [rnbd-server](./rnbd-server.md), [block](./block.md); coverage: [ledger](../ledger.md)
