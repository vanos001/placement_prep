# lookup_dcookie(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 212 / 253 / 18 / 249 (cached kernel tables; hub agrees; g64 18 is the generic-table slot) |
| Since (kernel) | 2.5.43 (man VERSIONS; hub shows 2.6); ENAMETOOLONG added 2.5.70 |
| Man page | man2/lookup_dcookie.2 (local cache, dated 2021-03-22) |
| glibc wrapper | None: glibc provides no wrapper, necessitating syscall(2); no lookup_dcookie symbol in libc (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-lookup_dcookie |

## Purpose

lookup_dcookie() maps an opaque cookie back to the full path of the directory entry it identifies: the kernel must still hold a cookie reference for the entry, and the buffer is filled with the path (suffixed " (deleted)" if the entry was removed). It is a special-purpose profiling interface, historically the bridge between oprofile's kernel-side sample cookies and human-readable paths, and it relies on a kernel driver registering the cookies. There is no normal way for a userspace program to obtain a cookie; without the registering driver the call fails EINVAL.

## Synopsis

```c
int syscall(SYS_lookup_dcookie, u64 cookie, char *buffer, size_t len);
```

## Return value and errors

Returns the length of the path string copied into the buffer; -1 with errno: EFAULT (bad buffer), EINVAL (no registered cookie mappings, or the cookie does not name a valid entry), ENAMETOOLONG (name does not fit; 2.5.70+), ENOMEM, EPERM (lacking CAP_SYS_ADMIN), ERANGE (buffer too small).

## Flags and constants

No flag arguments; the cookie is an opaque 64-bit value.

## Security and notes

- Gated by CAP_SYS_ADMIN (EPERM otherwise).
- Obscure by design: the man page notes it is "currently used only by the oprofile(1) profiler", and oprofile has been superseded by perf (see perf_event_open.md); treat the call as deprecated legacy rather than a supported path-lookup primitive. On some modern architectures the slot is a no-op returning ENOSYS (not verified this session; the cached man page documents only the errors above).

## References

- man2/lookup_dcookie.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-lookup_dcookie; [Domain hub](overview.md).
- Sibling: [perf_event_open](perf_event_open.md) (the modern profiling interface).
