# mmap(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 9 / 90 / 222 / - |
| Since (kernel) | 1.0 |
| Man page | man2/mmap.2 (cached, dated 2021-03-22; companion man2/mmap2.2 is indexed under descriptors-io) |
| glibc wrapper | yes, in libc; on 32-bit the wrapper calls mmap2(2) with the offset adjusted (man "C library/kernel differences") |
| Aliases covered | none (munmap has its own page [munmap](munmap.md)) |
| Ledger ID | SC-mmap |

## Purpose

`mmap()` creates a new mapping in the calling process's virtual address
space, backed by a file (`length` bytes at `offset` of the file on `fd`)
or, with `MAP_ANONYMOUS`, by zero-filled memory: the kernel's universal
interface for memory-mapped file I/O, shared memory, allocators, loaders,
and stacks. `addr` is a hint unless `MAP_FIXED` is given.

## Synopsis

```c
#include <sys/mman.h>
void *mmap(void *addr, size_t length, int prot, int flags,
           int fd, off_t offset);
```

## Arguments and behavior

`addr` = NULL lets the kernel choose a page-aligned address (the portable
form); non-NULL is a hint, rounded down since 2.6.24. With `MAP_FIXED` the
address is enforced and overlapping mappings are discarded. `length` must
be > 0 (EINVAL when 0, since 2.6.12); `offset` must be a page-size multiple
(huge-page size for hugetlb). `fd` may be closed right after a successful
call; `prot` must not conflict with the file's open mode; mappings survive
`fork(2)` unchanged.

## Return value and errors

Returns the mapped address; on failure `MAP_FAILED` (`(void *) -1`) with
`errno`: `EACCES`, `EAGAIN`, `EBADF`, `EEXIST` (MAP_FIXED_NOREPLACE
collision), `EINVAL` (bad arguments; no MAP_PRIVATE/MAP_SHARED/
MAP_SHARED_VALIDATE), `ENFILE`, `ENODEV`, `ENOMEM` (no memory; mapping
count; `RLIMIT_DATA` since 4.7), `EOVERFLOW` (32-bit large-file
page-count overflow), `EPERM` (PROT_EXEC on no-exec mount; file seal;
unprivileged MAP_HUGETLB), `ETXTBSY`. Use of the mapping can raise
`SIGSEGV` (write to read-only) or `SIGBUS` (past file end).

## Flags and constants

`prot`: `PROT_NONE`, `PROT_READ`, `PROT_WRITE`, `PROT_EXEC` (full PROT_*
list under [mprotect](mprotect.md)). `flags` values verified in installed
glibc headers (`bits/mman-linux.h`, `bits/mman-map-flags-generic.h`):

| Flag | Value | Since / note |
|---|---|---|
| MAP_SHARED | 0x01 | updates visible to other mappings and the file |
| MAP_PRIVATE | 0x02 | private copy-on-write |
| MAP_SHARED_VALIDATE | 0x03 | 4.15; unknown flags fail with EOPNOTSUPP |
| MAP_DROPPABLE | 0x08 | in headers; man page coverage gap |
| MAP_FIXED | 0x10 | enforce addr exactly; clobbers overlaps |
| MAP_ANONYMOUS (=MAP_ANON) | 0x20 | no file; fd ignored; shared anon since 2.4 |
| MAP_GROWSDOWN | 0x00100 | stack-like, grows downward |
| MAP_LOCKED | 0x02000 | 2.5.37; weak mlock, never fails the mmap |
| MAP_NORESERVE | 0x04000 | skip swap reservation |
| MAP_POPULATE | 0x08000 | 2.5.46; prefault page tables |
| MAP_NONBLOCK | 0x10000 | 2.5.46; POPULATE no-op since 2.6.23 |
| MAP_STACK | 0x20000 | 2.6.27; currently a no-op on Linux |
| MAP_HUGETLB | 0x40000 | 2.6.32; huge-page mapping |
| MAP_SYNC | 0x80000 | 4.15; DAX-only, needs MAP_SHARED_VALIDATE |
| MAP_FIXED_NOREPLACE | 0x100000 | 4.17; EEXIST instead of clobbering |
| MAP_HUGE_* / MAP_HUGE_SHIFT | bits 26-31 | 3.8; log2 page-size encoding |

`MAP_32BIT` (x86-64 only) lives in the x86 glibc bits; `MAP_UNINITIALIZED`
(2.6.33) is honored only with `CONFIG_MMAP_ALLOW_UNINITIALIZED`. Only
`MAP_FIXED` is POSIX; the rest need `_DEFAULT_SOURCE` (glibc >= 2.19) or
`_BSD_SOURCE`/`_SVID_SOURCE` earlier.

## Security and notes

- Numbering trap: **i386 slot 90 is the `old_mmap` entry**
  (`sys_old_mmap` / `compat_sys_ia32_mmap`, cached `syscall_32.tbl`);
  32-bit programs actually use mmap2 (i386/arm 192). arm32 EABI has no
  `mmap` row (hub arm "-"); the old arm OABI table has slot 90 `oabi mmap`.
- `MAP_FIXED` clobbers pre-existing mappings and is hazardous in
  multithreaded programs (man "Using MAP_FIXED safely"); since 4.17
  `MAP_FIXED_NOREPLACE` is the atomic, EEXIST-returning alternative.
- `PROT_WRITE` implies `PROT_READ` on some architectures (e.g. i386);
  whether `PROT_READ` implies `PROT_EXEC` is arch dependent.
- Writes past file end in the trailing partial page stay in page cache
  (POSIX deviation, man BUGS); `msync(2)` before unmap may flush them,
  except on tmpfs. `MAP_NORESERVE` gives no OOM guarantee: the kernel may
  kill the process under pressure (man BUGS).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/mmap.2` (full).
- Flag values: `/usr/include/x86_64-linux-gnu/bits/mman-linux.h`,
  `bits/mman-map-flags-generic.h`.
- Numbers: cached `syscall_64.tbl`, `syscall_32.tbl` (old_mmap),
  `syscall_generic.tbl`, `syscall_arm.tbl`; hub [overview](overview.md);
  worklog Task 1-b verified i386 90 = `old_mmap`.
