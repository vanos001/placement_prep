# /sys/class/mic

| Field | Value |
|---|---|
| Subsystem | Intel MIC (Many Integrated Core) coprocessor devices, per the ABI text; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-mic` (13 What: entries) |
| Since | 3.13 (all base entries, October 2013); heartbeat_enable 4.4 (March 2015) |
| Live (5.10.134 host) | class absent: /sys/class/mic does not exist in this container |
| Ledger ID | SYSC-mic |

## What it represents

Per the ABI: "An Intel MIC device is a PCIe form factor add-in Coprocessor
card based on the Intel Many Integrated Core (MIC) architecture that runs a
Linux OS." The class exposes one micX directory per card (mic0, mic1, ...),
card identity (family, stepping), the card OS boot configuration (firmware,
ramdisk, cmdline, bootmode), the card OS state machine, shutdown reason, and
a crash-heartbeat switch. The last ABI addition is heartbeat_enable at 4.4
(March 2015); the cached tree contains no newer entries, and with no
drivers/ directory cached the current driver status cannot be verified from
these sources.

## Relationship to the device model

The class directory "belongs to Intel MIC devices and provides information
per MIC device"; each micX "has information specific to that MIC device".
The ABI's debugfs references (log_buf_addr/log_buf_len point at the card OS
log buffer read via debugfs) are the only cross-filesystem mentions; no
bus or device links are described in the cached text.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| family | RO | coprocessor family, e.g. "x100" | always | ABI testing sysfs-class-mic, 3.13 |
| stepping | RO | silicon stepping, e.g. "A0" or "B0" | always | ABI, 3.13 |
| state | RO/RW | read: ready, booting, online, shutting_down, resetting, reset_failed; write: boot, reset, shutdown | always | ABI, 3.13 |
| shutdown_status | RO | nop, crashed, halted, poweroff, restart | always | ABI, 3.13 |
| cmdline | RW | kernel command line for the card OS; read-then-rewrite pattern | always | ABI, 3.13 |
| firmware | RW | path under /lib/firmware/ of the card OS image | always | ABI, 3.13 |
| ramdisk | RW | path under /lib/firmware/ of the boot ramdisk | always | ABI, 3.13 |
| bootmode | RW | "linux" (boot Linux image) or "flash" (image for flash updates) | always | ABI, 3.13 |
| log_buf_addr | RW | kernel virtual address of the card OS log buffer (from card System.map) | debug aid | ABI, 3.13 |
| log_buf_len | RW | kernel virtual address where the log buffer length is read | debug aid | ABI, 3.13 |
| heartbeat_enable | RW | 1 enable / 0 disable card-crash notification; enabled by default | always | ABI, 4.4 |

## Safety and writes

Writes here boot, reset, or shut down a coprocessor: state accepts boot,
reset, and shutdown; firmware/ramdisk/cmdline/bootmode reshape the card OS
boot. log_buf_addr and log_buf_len take raw kernel virtual addresses and are
meant for the host configuration daemon, not interactive use. Disabling
heartbeat_enable pushes crash detection to userspace ("such as a network
ping"). No MIC hardware exists here, so no live value was read.

## References

- `Documentation/ABI/testing/sysfs-class-mic` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-mic
- sysfs-attrs.json entry `mic` (13 paths); live enumeration: class absent, kernel 5.10.134
- Coverage: [ledger](../ledger.md)
