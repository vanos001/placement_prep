# sysinfo(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 99 / 116 / 179 / 116 (cached kernel tables; hub agrees; the i386 row invokes compat_sys_sysinfo per syscall_32.tbl) |
| Since (kernel) | 1.0 (hub/ledger); man VERSIONS: "sysinfo() first appeared in Linux 0.98.pl6" -- both attributions stated |
| Man page | man2/sysinfo.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in `<sys/sysinfo.h>`; sysinfo@@GLIBC_2.2.5 (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-sysinfo |

## Purpose

`sysinfo()` returns statistics on main-memory and swap usage plus the load
averages, in a single 64-byte structure. All of the same information is also
available through `/proc/meminfo` and `/proc/loadavg` (man NOTES); the syscall
exists for programs that want one atomic snapshot without parsing procfs.

## Synopsis

    #include <sys/sysinfo.h>
    int sysinfo(struct sysinfo *info);

## Arguments and behavior

Since Linux 2.3.23 (i386) / 2.3.48 (all architectures) the structure is
(man page; the pre-2.3.16 variant lacked the last three fields and had no
`mem_unit` scaling):

| Field | Meaning |
|---|---|
| `uptime` | seconds since boot |
| `loads[3]` | 1, 5, and 15 minute load averages |
| `totalram`, `freeram`, `sharedram` | total / available / shared main memory |
| `bufferram` | memory used by buffers |
| `totalswap`, `freeswap` | total / available swap |
| `procs` | number of current processes (`unsigned short`) |
| `totalhigh`, `freehigh` | total / available high memory |
| `mem_unit` | memory-unit size in bytes; memory and swap fields are multiples of it |
| `_f` | padding to 64 bytes |

## Return value and errors

Returns 0 on success; -1 with `errno` = `EFAULT` when `info` is not a valid
address (the only documented error).

## Flags and constants

None.

## Security and notes

Unprivileged; no capability required. The structure layout differs between the
old and new ABIs, and memory sizes are scaled by `mem_unit`, so portable code
must use the glibc `<sys/sysinfo.h>` definition rather than hand-rolled
structs. Linux-specific; the man page says it should not be used in programs
intended to be portable. For per-CPU placement queries see getcpu(2) (page
pending in this hub); for pinning see
[sched_setaffinity(2)](sched_setaffinity.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/sysinfo.2`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (99), `syscall_32.tbl`
  (116), `syscall_generic.tbl` (179), `syscall_arm.tbl` (116)
- Online: https://man7.org/linux/man-pages/man2/sysinfo.2.html
