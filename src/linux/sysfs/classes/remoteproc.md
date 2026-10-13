# /sys/class/remoteproc

| Field | Value |
|---|---|
| Subsystem | remoteproc subsystem (remote processor lifecycle); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-remoteproc` (5 What entries) |
| Since | `firmware`/`state` October 2016 (no KernelVersion stated); `name` 5.4 (August 2019); `coredump`/`recovery` July 2020 (no KernelVersion stated) |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, no /sys/class/remoteproc |
| Ledger ID | SYSC-remoteproc |

## What it represents

One directory per remote processor - a co-processor (DSP, MCU, modem) managed by the remoteproc framework. The class controls its lifecycle: which firmware image it boots, whether it is running, what happens when it crashes. The processor state vocabulary is `offline`, `suspended`, `running`, `crashed` and `invalid`.

## Relationship to the device model

Each directory is a class view of an rproc device registered by a platform driver. State changes are string commands through `state`; firmware selection is a filename in `firmware` that takes effect on the next `start`. The crash-handling files (`recovery`, `coredump`) configure the framework's reaction to a crashed remote: automatic restart versus freeze-for-debugging, and where the dump is taken from. A companion character device interface exists separately (host header `/usr/include/linux/remoteproc_cdev.h` defines `RPROC_SET_SHUTDOWN_ON_RELEASE`, controlling automatic shutdown when the last fd closes); it is an ioctl interface, not part of this class.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `.../firmware` | RW | firmware filename; change only while stopped | rproc device | ABI, October 2016 |
| `.../state` | RW | read: offline/suspended/running/crashed/invalid; write: `start` or `stop` | rproc device | ABI, October 2016 |
| `.../name` | RO | remote processor name | rproc device | ABI, August 2019, 5.4 |
| `.../coredump` | RW | `disabled`, `enabled` (dump copied to buffer) or `inline` (read device memory directly; recovery waits for readers) | rproc device | ABI, July 2020 |
| `.../recovery` | RW | `enabled`/`disabled`; disabled leaves the processor crashed for debugging | rproc device | ABI, July 2020 |

## Safety and writes

These writes start, stop and re-image a separate processor: writing `start` boots the firmware named in `firmware`, writing `stop` halts the coprocessor, and changing `firmware` while running is refused by the documented procedure (stop first). Disabling `recovery` deliberately leaves hardware crashed - a debugging choice that keeps the system in a degraded state - and switching it back to enabled recovers any pending crash automatically. `coredump = inline` blocks the recovery process until userspace has read the dump. All of this is root territory.

## References

- `Documentation/ABI/testing/sysfs-class-remoteproc` (cached copy; 5 What entries)
- `/usr/include/linux/remoteproc_cdev.h` (host header, verified present; cdev ioctls); `/usr/include/linux/remoteproc.h` absent on the host (verified)
- Implementation: not in cached tree
- Coverage: [ledger](../ledger.md)
- Live check: /sys/class/remoteproc absent (kernel 5.10.134, read-only enumeration)
