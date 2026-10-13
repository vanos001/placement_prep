# /sys/class/rnbd-server

| Field | Value |
|---|---|
| Subsystem | RNBD-server (RDMA Network Block Device, server/export side), over RTRS sessions; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-rnbd-server` (7 What: entries) |
| Since | 5.7 (Feb 2020); force_close 5.10 |
| Live (5.10.134 host) | class absent: /sys/class/rnbd-server does not exist in this container |
| Ledger ID | SYSC-rnbd-server |

## What it represents

The server-side view of RNBD exports: when a client maps a device, "a
directory entry with the name of the block device is created under
/sys/class/rnbd-server/ctl/devices/", and within it a sessions/ tree records
every client the device is exported to. The server opens the local block
device named by the client (device_path prefixed with the rnbd_server
dev_search_path module parameter, which may contain %SESSNAME%) and tracks
each mapping's mode and path.

## Relationship to the device model

Each ctl/devices/<device_name>/ carries block_dev, "a symlink to the sysfs
entry of the exported device" (ABI example: block_dev ->
../../../../class/block/ram0), anchoring the class to the real block device
under [block](./block.md). Session directories appear and disappear with
client mappings: "When the device is unmapped by that client, the directory
will be removed." Client side of the same sessions:
[rnbd-client](./rnbd-client.md); transport: rtrs-client/rtrs-server.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| ctl/ | RO | container: per-device directories under ctl/devices/ appear when a client maps a device | always | ABI testing sysfs-class-rnbd-server, 5.7 |
| ctl/devices/<device_name>/block_dev | RO | symlink to the sysfs entry of the exported block device | per exported device | ABI, 5.7 |
| ctl/devices/<device_name>/sessions/ | RO | one `<session-name>` directory per client the device is exported to | per session | ABI, 5.7 |
| .../sessions/`<session-name>`/read_only | RO | '1' if mapped read-only, otherwise '0' | per session | ABI, 5.7 |
| .../sessions/`<session-name>`/mapping_path | RO | relative device path provided by the user during mapping | per session | ABI, 5.7 |
| .../sessions/`<session-name>`/access_mode | RO | device access mode: ro, rw or migration | per session | ABI, 5.7 |
| .../sessions/`<session-name>`/force_close | WO | write "1" to close the device on the server side; client keeps a dead device whose I/O gets -ENOTCONN | per session | ABI, 5.10 |

## Safety and writes

All documented files are read-only except force_close. force_close is
disruptive by design: the ABI warns that "the client side device will not
be closed, read or write to the device will get -ENOTCONN", so it yanks
storage out from under a remote user. The class is absent on the 5.10.134
host; no live read or write was possible and no value examples are reported.

## References

- `Documentation/ABI/testing/sysfs-class-rnbd-server` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-rnbd-server
- sysfs-attrs.json entry `rnbd-server` (7 paths); live enumeration: class absent, kernel 5.10.134
- Related pages: [rnbd-client](./rnbd-client.md), [rtrs-server](./rtrs-server.md), [block](./block.md); coverage: [ledger](../ledger.md)
