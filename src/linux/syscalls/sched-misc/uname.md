# olduname(2) / oldolduname(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | oldolduname -- / 59 / -- / --; olduname -- / 109 / -- / -- |
| Since (kernel) | 1.0 (both slots) |
| Man page | man2/uname.2 (man-pages 6.19 HTML set, fetched 2026-10-17) -- HISTORY documents the three-generation sequence; modern uname is a separate page in this encyclopedia ([uname](../process/uname.md)) |
| glibc wrapper | none for the dead slots; the glibc uname(3) wrapper "invokes the most recent version of the system call provided by the kernel" (uname.2, HISTORY, C library/kernel differences) |
| Aliases covered | oldolduname (SC-oldolduname), olduname (SC-olduname) |
| Ledger ID | SC-oldolduname |

## Purpose

olduname() and oldolduname() are the first two generations of the uname interface, kept as i386 compat slots: sys_olduname() (slot __NR_olduname) and sys_olduname's predecessor sys_oldolduname() (slot __NR_oldolduname) filled progressively shorter `struct utsname` layouts before the current sys_newuname() settled the family (uname.2, HISTORY, C library/kernel differences).

## Synopsis

```c
/* dead slots; layouts per uname.2 HISTORY */
long syscall(SYS_oldolduname, struct oldold_utsname *buf); /* 9-char fields */
long syscall(SYS_olduname,    struct old_utsname *buf);    /* 65-char fields */
```

## Arguments and behavior

Per uname.2 HISTORY: the first version "used length 9 for all fields; the second used 65; the third also uses 65 but adds the domainname field" -- so oldolduname fills six 9-character fields, olduname six 65-character fields, and newuname (the modern call, see [uname](../process/uname.md)) adds `domainname`. The glibc wrapper hides the generations from applications entirely (uname.2, HISTORY).

## Return value and errors

0 on success; -1 with EFAULT for a bad buffer, matching the modern call's error set (uname.2, ERRORS).

## Flags and constants

None.

## Security and notes

The three-slot sequence is the cleanest interview illustration of struct-layout ABI churn in Linux: field-length growth (9 -> 65 -> 65+domainname) forced new numbers while the old slots stayed frozen for 1.x-era i386 binaries. The man page's adjacent guidance stands: never hard-code UTSLEN-style constants, "just use sizeof(...)" (uname.2, VERSIONS). Cross-reference: [uname](../process/uname.md), [gethostname](../net-ipc/gethostname.md), [getdomainname](../net-ipc/getdomainname.md), [sethostname(2) via the net-ipc pages](../net-ipc/gethostname.md).

## References

- https://man7.org/linux/man-pages/man2/uname.2.html (HISTORY: the sys_olduname/sys_oldolduname slots)
- worklog: no olduname/oldolduname symbols in glibc 2.41 (nm -D, 2026-10-17)
