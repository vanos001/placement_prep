# unimplemented(2) -- afs_syscall, break, getpmsg, gtty, lock, mpx, prof, putpmsg, security, stty, tuxcall, vserver

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | afs_syscall 183 / 137 / -- / --; break -- / 17 / -- / --; getpmsg 181 / 188 / -- / --; gtty -- / 32 / -- / --; lock -- / 53 / -- / --; mpx -- / 56 / -- / --; prof -- / 44 / -- / --; putpmsg 182 / 189 / -- / --; security 185 / -- / -- / --; stty -- / 31 / -- / --; tuxcall 184 / -- / -- / --; vserver 236 / 273 / -- / 313 |
| Since (kernel) | -- (slots reserved across the 1.0/2.0/2.4 table generations; man-pages syscalls(2) lists them all in the unimplemented set) |
| Man page | man2/unimplemented.2 (man-pages 6.19 HTML set, fetched 2026-10-17) covers exactly this group: "These system calls are not implemented in the Linux kernel" |
| glibc wrapper | none -- no symbol for any of these names in glibc 2.41 (nm -D); several (stty/gtty/break/lock/mpx/prof) are classic UNIX names kept as table placeholders |
| Aliases covered | afs_syscall (SC-afs_syscall), break (SC-break), getpmsg (SC-getpmsg), gtty (SC-gtty), lock (SC-lock), mpx (SC-mpx), prof (SC-prof), putpmsg (SC-putpmsg), security (SC-security), stty (SC-stty), tuxcall (SC-tuxcall), vserver (SC-vserver) |
| Ledger ID | SC-afs_syscall (grouped page) |

## Purpose

One page for the twelve table slots that were reserved but never implemented: the STREAMS pair getpmsg/putpmsg (and the reserved x64 slots for them), the pre-POSIX tty/io names stty/gtty/break/lock/mpx/prof, the AFS placeholder afs_syscall, the x86 "security" placeholder, tuxcall (the userspace web-server hook that only ever existed in the TUX tree), and vserver (the Linux-VServer reservation that never entered mainline). unimplemented.2 states the contract for all of them.

## Synopsis

```c
/* no prototypes exist; each slot would have been invoked via syscall(2) */
```

## Arguments and behavior

There is no behavior to document: the slots exist so the table numbering is stable, and every implementation returns -ENOSYS (unimplemented.2, RETURN VALUE). On arm64/asm-generic the names simply have no rows at all -- the `--` columns are meaningful, not gaps (ledger overview, scope caveats).

## Return value and errors

Always -1 with errno set to ENOSYS (unimplemented.2, RETURN VALUE).

## Flags and constants

None.

## Security and notes

Why keep dead slots? Renumbering syscalls breaks every compiled binary; placeholders freeze the numbering forever. Interviews probe this as "why does syscall 17 exist if break(2) was never implemented" -- the answer is ABI stability, the same reason x86_64 183/184/185 stayed occupied by afs_syscall/getpmsg/putpmsg placeholders. Note the neighbors documented elsewhere in this encyclopedia: ftime (own page, [ftime](ftime.md)), ulimit ([ulimit](ulimit.md)) and profil ([profil](profil.md)) are library routines rather than kernel calls, per unimplemented.2 NOTES. Cross-reference: [ftime](ftime.md), [ulimit](ulimit.md), [profil](profil.md), [syscalls hub](overview.md).

## References

- https://man7.org/linux/man-pages/man2/unimplemented.2.html
- man-pages syscalls(2) (the unimplemented list repeats this set)
- worklog: no glibc symbols for any grouped name (nm -D, glibc 2.41, 2026-10-17)
