# /sys/class/rapidio_port

| Field | Value |
|---|---|
| Subsystem | RapidIO subsystem (mport = Master Port view of on-chip RapidIO controllers and PCIe-to-RapidIO bridges); contacts Matt Porter, Alexandre Bounine; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-rapidio` (3 What: entries, all under /sys/class/rapidio_port/) |
| Since | v3.15 (Apr 2014, both attribute entries) |
| Live (5.10.134 host) | class absent: /sys/class/rapidio_port does not exist in this container |
| Ledger ID | SYSC-rapidio_port |

## What it represents

The class of RapidIO Master Ports: "On-chip RapidIO controllers and
PCIe-to-RapidIO bridges (referenced as 'Master Port' or 'mport') are
presented in sysfs as the special class of devices: rapidio_port"
(ABI). Directories are named rapidioN where N is the mport ID registered
with the RapidIO subsystem; the ABI warns that an mport ID is not the
RapidIO destination ID of the device. The two attributes report the
transport system size and the port's own destination ID.

## Relationship to the device model

The ABI includes a live ls -l of /sys/class/rapidio_port/rapidio0/ showing
the standard class furniture (device -> ../../../0000:01:00.0, subsystem ->
.../class/rapidio_port, uevent, power/) plus child RapidIO device
directories named like 00:e:0001 and 00:s:0003: "After enumeration or
discovery was performed for a given mport device, the corresponding
subdirectory will also contain subdirectories for each child RapidIO device
connected to the mport." The child fabric topology is thus attached to the
mport's class directory.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| sys_size | RO | RapidIO common transport system size: 0 small (8-bit destination ID, max 256 devices), 1 large (16-bit, max 65536 devices) | always | ABI testing sysfs-class-rapidio, v3.15 |
| port_destid | RO | destination ID of the mport; 0xFFFFFFFF means none assigned yet; enumerating mports get one via the "hdid=..." rapidio module parameter | always | ABI testing sysfs-class-rapidio, v3.15 |
| `<child device dirs>` | -- | per-child RapidIO device directories (e.g. 00:e:0001) appear after enumeration/discovery | post-enumeration | ABI example listing |

## Safety and writes

Both documented attributes are read-only; the ABI records no writable file
in this class, so enumeration and discovery are driven by module parameters
and the RapidIO subsystem rather than sysfs writes. RapidIO hardware is
absent from this x86 container, so the class does not exist on the host and
no live value was read.

## References

- `Documentation/ABI/testing/sysfs-class-rapidio` (cached copy; class paths /sys/class/rapidio_port/)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-rapidio
- sysfs-attrs.json entry `rapidio_port` (2 paths); live enumeration: class absent, kernel 5.10.134
- Coverage: [ledger](../ledger.md)
