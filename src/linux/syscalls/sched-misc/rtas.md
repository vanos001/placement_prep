# rtas(2) (PowerPC)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (PowerPC table only) |
| Since (kernel) | 2.6.2 (syscalls(2): "PowerPC/PowerPC64 only") |
| Man page | none (no man2/rtas.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-rtas |

## Purpose

rtas() lets privileged userspace invoke RTAS (Run-Time Abstraction Services) functions -- the Open Firmware/CHRP firmware call-out layer on PowerPC: platform operations like reading the RTC, event scanning, or LED control are implemented in firmware, and the kernel multiplexes userspace RTAS requests into those calls (the ppc64 platform-services design). The kernel gates which RTAS functions userspace may call directly, routing the rest through root-owned /proc/ppc64/rtas-style controls.

## Synopsis

```c
/* PowerPC syscall */
long syscall(SYS_rtas, struct rtas_args *args);
```

## Arguments and behavior

One argument: a rtas_args structure carrying the RTAS function token and its arguments; the kernel copies the args in, validates the token against its userspace-allowed list, invokes firmware, and copies results back (kernel arch/powerpc/kernel/rtas.c sys_rtas design).

## Return value and errors

Returns the RTAS call's status value; a negated error on the raw path for invalid args or a disallowed token.

## Flags and constants

RTAS function tokens are firmware-defined (per the CHRP/PAPR specifications); the kernel maintains the allow-list.

## Security and notes

Source-limited: no man page exists and the implementation was not fetched this round -- the entry names that gap and describes the PAPR/CHRP design role. Interview angle: rtas(2) is a syscall whose real interface is firmware, a category of one in the Linux tables. Cross-reference: [reboot](reboot.md), [pciconfig_read](pciconfig_read.md).

## References

- man-pages syscalls(2) (rtas(2), 2.6.2, PowerPC only)
- Ledger row SC-rtas

