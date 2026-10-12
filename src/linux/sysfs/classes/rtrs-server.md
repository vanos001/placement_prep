# /sys/class/rtrs-server

| Field | Value |
|---|---|
| Subsystem | RTRS-server (RDMA Transport, server side; transport used by RNBD); implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-rtrs-server` (7 What: entries) |
| Since | 5.7 (Feb 2020, all entries) |
| Live (5.10.134 host) | class absent: /sys/class/rtrs-server does not exist in this container |
| Ledger ID | SYSC-rtrs-server |

## What it represents

The mirror of rtrs-client on the exporting host: "When a user of RTRS API
creates a new session on a client side, a directory entry with the name of
that session is created in here" (ABI). Each session exposes its paths as
<src@dst> directories with read-only identity/state files, RDMA statistics,
and one write-only control file, disconnect. There is no add_path here:
paths are created by the client writing its own add_path, and the server
side directory appears as a result.

## Relationship to the device model

The paths/ tree is created lazily: "When new path is created by writing to
'add_path' entry on client side, a directory entry named as <source
address>@<destination address> is created on server." hca_name and hca_port
again tie paths to RDMA hardware ([infiniband](./infiniband.md)); the block
consumer on this side is [rnbd-server](./rnbd-server.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| <session-name>/paths/ | RO | one <src@dst> directory per path the client added | per session | ABI testing sysfs-class-rtrs-server, 5.7 |
| paths/<src@dst>/disconnect | WO | write "1" to disconnect the RTRS session; non-blocking, returns immediately | per path | ABI, 5.7 |
| paths/<src@dst>/hca_name | RO | name of the HCA the connection established on | per path | ABI, 5.7 |
| paths/<src@dst>/hca_port | RO | port number of the active port | per path | ABI, 5.7 |
| paths/<src@dst>/src_addr | RO | source address of the path | per path | ABI, 5.7 |
| paths/<src@dst>/dst_addr | RO | destination address of the path | per path | ABI, 5.7 |
| paths/<src@dst>/stats/rdma | RO | five values: read-count read-total-size write-count write-total-size inflights | per path | ABI, 5.7 |

Compared to the client, the server stats/ tree is smaller: no cpu_migration,
reconnects, reset_all, or cur_latency entries appear in the server ABI file.

## Safety and writes

Reads are safe. The single write, disconnect, tears down an RTRS path on
the server side; the ABI notes it is non-blocking and "returns control
immediately to the caller", so completion must be observed elsewhere (e.g.
the directory disappearing). The class is absent on the 5.10.134 host; no
live read or write was possible.

## References

- `Documentation/ABI/testing/sysfs-class-rtrs-server` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-rtrs-server
- sysfs-attrs.json entry `rtrs-server` (7 paths); live enumeration: class absent, kernel 5.10.134
- Related pages: [rtrs-client](./rtrs-client.md), [rnbd-server](./rnbd-server.md), [infiniband](./infiniband.md); coverage: [ledger](../ledger.md)
