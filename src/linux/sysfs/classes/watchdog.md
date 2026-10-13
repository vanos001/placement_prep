# /sys/class/watchdog

| Field | Value |
|---|---|
| Subsystem | watchdog subsystem (watchdog core + drivers); implementation files not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); class absent on the live host (no watchdog device registered) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-watchdog` (13 What entries) |
| Since | August 2015 for the core files; pretimeout December 2016; pretimeout governors February 2017; access_cs0 August 2019; `options` and `fw_version` April 2023 |
| Live (5.10.134 host) | class absent: not in live-sys/class-list.txt, /sys/class/watchdog missing (verified); no watchdog hardware in the container |
| Ledger ID | SYSC-watchdog |

## What it represents

One directory per watchdog device (`watchdog0`, `watchdog1`, ...). A watchdog must be petted within its timeout or the machine reboots; the class exposes the device identity, timeout bookkeeping, boot-time status (did the last reset come from the watchdog?) and the nowayout and pretimeout policy knobs. The actual arming interface is the character device `/dev/watchdogN` with the `WDIOC_*` ioctls (declared in `/usr/include/linux/watchdog.h`, present on the host).

## Relationship to the device model

Each class device is backed by a watchdog_device registered through the watchdog core; sysfs attributes mirror selected ioctls - the ABI says so explicitly (`bootstatus` "equivalent to WDIOC_GETBOOTSTATUS", `status` "equivalent to WDIOC_GETSTATUS", `timeleft` "equivalent to WDIOC_GETTIMELEFT"). Pretimeout support splits the alarm into two stages: a governor (chosen via `pretimeout_governor`) decides what happens at the pretimeout point before the final reset. `access_cs0` exists only on the AST2400/AST2500 Aspeed SoCs after an alternate-flash boot, and the ABI restricts it to watchdog1 (wdt2).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `watchdogn/identity` | RO | identity string of the device | watchdog device | ABI, August 2015 |
| `watchdogn/bootstatus` | RO | status at boot (WDIOC_GETBOOTSTATUS equivalent) | watchdog device | ABI, August 2015 |
| `watchdogn/status` | RO | internal status bits (WDIOC_GETSTATUS equivalent) | watchdog device | ABI, August 2015 |
| `watchdogn/state` | RO | active/inactive status | watchdog device | ABI, August 2015 |
| `watchdogn/timeleft` | RO | seconds left before reset (WDIOC_GETTIMELEFT equivalent) | watchdog device | ABI, August 2015 |
| `watchdogn/timeout` | RO | current programmed timeout (ABI text: read only) | watchdog device | ABI, August 2015 |
| `watchdogn/nowayout` | RW | read 0/1; write 1 enables nowayout; cannot be undone | watchdog device | ABI, August 2015 |
| `watchdogn/pretimeout` | RO | seconds before timeout when the pretimeout interrupt fires; optional feature | pretimeout-capable | ABI, December 2016 |
| `watchdogn/pretimeout_available_governors` | RO | governors available for this watchdog | pretimeout-capable | ABI, February 2017 |
| `watchdogn/pretimeout_governor` | RW | current pretimeout governor; write selects it | pretimeout-capable | ABI, February 2017 |
| `watchdogn/options` | RO | options of the watchdog device | watchdog device | ABI, April 2023 |
| `watchdogn/fw_version` | RO | firmware version of the watchdog device | watchdog device | ABI, April 2023 |
| `watchdog1/access_cs0` | RW | non-zero write clears boot code selection and timeout counter; restores CS0 access after alt-flash boot | AST2400/2500 alternate boot | ABI, August 2019 |

## Safety and writes

`nowayout` is a one-way latch: once written 1, the watchdog can never be stopped again (the ABI says writing 0 either does nothing or returns a permission error). `pretimeout_governor` changes what happens on the pretimeout event. Reading everything is safe. Note the ABI marks `timeout` and `pretimeout` as read-only files; runtime retuning happens through the /dev ioctls (`WDIOC_SETOPTIONS`, set-timeout), not these files, per the ABI text.

## References

- `Documentation/ABI/testing/sysfs-class-watchdog` (cached copy; 13 What entries)
- `/usr/include/linux/watchdog.h` (host header, verified: WDIOC_GETSTATUS/GETBOOTSTATUS/SETOPTIONS/GETTIMELEFT)
- Implementation: not in cached tree
- Coverage: [ledger](../ledger.md)
- Live check: /sys/class/watchdog absent (kernel 5.10.134, read-only enumeration)
