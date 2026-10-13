# /sys/class/rtrs-client

| Field | Value |
|---|---|
| Subsystem | RTRS-client (RDMA Transport, client side; transport used by RNBD); implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-rtrs-client` (17 What: entries) |
| Since | 5.7 (Feb 2020, all entries) |
| Live (5.10.134 host) | class absent: /sys/class/rtrs-client does not exist in this container |
| Ledger ID | SYSC-rtrs-client |

## What it represents

Sessions of the RTRS RDMA transport as seen by the client. "When a user of
RTRS API creates a new session, a directory entry with the name of that
session is created under /sys/class/rtrs-client/`<session-name>`/" (ABI).
Each session carries path management (add_path, remove_path, reconnect,
disconnect), the multipath policy, reconnect limits, and per-path state,
HCA identity, addresses, heartbeat latency, and RDMA statistics. RNBD
([rnbd-client](./rnbd-client.md)) is the documented consumer of these
sessions.

## Relationship to the device model

Paths are exposed as directories named <src@dst> under paths/ and are
created when add_path is written; hca_name and hca_port tie each path to
the RDMA Host Channel Adapter and port carrying it (the live host's RDMA
classes are covered in [infiniband](./infiniband.md)). Nothing else about
kernel object wiring is stated in the cached ABI.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<session>`/add_path | WO | `<[src,]dst>` with addr ::= [ ip:<ipv4\|ipv6> \| gid:`<gid>` ]; adds a path to the session | per session | ABI testing sysfs-class-rtrs-client, 5.7 |
| `<session>`/max_reconnect_attempts | RW | max reconnect attempts before giving up after unexpected break | per session | ABI, 5.7 |
| `<session>`/mp_policy | RW | path selection per IO: round-robin (0), min-inflight (1), min-latency (2) | per session | ABI, 5.7 |
| `<session>`/paths/ | RO | one <src@dst> directory per added path | per path | ABI, 5.7 |
| paths/<src@dst>/state | RO | "connected" if fully functional, otherwise "disconnected" | per path | ABI, 5.7 |
| paths/<src@dst>/reconnect | WO | write "1"; blocking, returns 0 on success | per path | ABI, 5.7 |
| paths/<src@dst>/disconnect | WO | write "1"; blocks until disconnected | per path | ABI, 5.7 |
| paths/<src@dst>/remove_path | WO | write "1"; disconnects and removes the path from the session | per path | ABI, 5.7 |
| paths/<src@dst>/hca_name | RO | name of the HCA the connection uses | per path | ABI, 5.7 |
| paths/<src@dst>/hca_port | RO | port number of the active port | per path | ABI, 5.7 |
| paths/<src@dst>/src_addr, dst_addr | RO | source / destination address of the path | per path | ABI, 5.7 |
| paths/<src@dst>/cur_latency | RO | heartbeat round-trip latency, changes regularly | per path | ABI, 5.7 |
| paths/<src@dst>/stats/reset_all | RW | read returns usage help; write 0 clears all statistics | per path | ABI, 5.7 |
| paths/<src@dst>/stats/cpu_migration | RO | IRQs handled on an unexpected CPU, with from:/to: CPUs | per path | ABI, 5.7 |
| paths/<src@dst>/stats/reconnects | RO | two counters: successful and failed reconnects in path lifetime | per path | ABI, 5.7 |
| paths/<src@dst>/stats/rdma | RO | six values: read-count read-total-size write-count write-total-size inflights failovered | per path | ABI, 5.7 |

## Safety and writes

Reads are safe. Writes rewire live RDMA sessions: add_path/disconnect/
remove_path/reconnect change connectivity; RTRS pins each HCA IRQ to a CPU
by design, so cpu_migration also exposes interrupt-affinity regressions.
The class is absent on the 5.10.134 host; nothing was read live.

## References

- `Documentation/ABI/testing/sysfs-class-rtrs-client` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-rtrs-client
- sysfs-attrs.json entry `rtrs-client` (17 paths); live enumeration: class absent, kernel 5.10.134
- Related pages: [rtrs-server](./rtrs-server.md), [rnbd-client](./rnbd-client.md), [infiniband](./infiniband.md); coverage: [ledger](../ledger.md)
