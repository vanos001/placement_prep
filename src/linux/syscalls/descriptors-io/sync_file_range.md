# sync_file_range(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | sync_file_range 277 / 314 / 84 / -; arm_sync_file_range - / - / - / 341; sync_file_range2 - / - / - / - (per-call table below) |
| Since (kernel) | sync_file_range 2.6.17; arm_sync_file_range 2.6.20 (ARM); sync_file_range2 name 2.6.22 (man NOTES; hub shows -) |
| Man page | man2/sync_file_range.2 (local cache, dated 2021-03-22) |
| glibc wrapper | Declared in <fcntl.h> with _GNU_SOURCE; on architectures using sync_file_range2 glibc wraps it under the name sync_file_range() |
| Aliases covered | arm_sync_file_range, sync_file_range2 |
| Ledger ID | SC-sync_file_range, SC-arm_sync_file_range, SC-sync_file_range2 |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| sync_file_range | 277 | 314 | 84 | - | 2.6.17 |
| arm_sync_file_range | - | - | - | 341 | 2.6.20 |
| sync_file_range2 | - | - | - | - | 2.6.22 |

Ledger note: SC-sync_file_range2 shows all-dash numbers because ARM uses the arm_sync_file_range slot (341) and the rename did not change ARM's number; both rows document here.

## Purpose

sync_file_range() finely controls write-out of the page-cache pages of the byte range [offset, offset+nbytes) of fd: it can wait for already-submitted write-out, start write-out of dirty pages, and wait for completion. offset is rounded down to a page boundary and offset+nbytes-1 up; nbytes 0 means through EOF. Unlike fsync(2) it writes no metadata and does not flush disk write caches, and unlike sync(2) it is per-range, enabling an asynchronous flush-then-wait pattern without blocking the caller at submission time.

## Synopsis

```c
#define _GNU_SOURCE
#include <fcntl.h>
int sync_file_range(int fd, off64_t offset, off64_t nbytes,
                    unsigned int flags);
```

## Arguments and behavior

| Flag (linux/fs.h) | Value | Meaning |
|---|---|---|
| SYNC_FILE_RANGE_WAIT_BEFORE | 1 | Wait for write-out already submitted for the range before doing anything |
| SYNC_FILE_RANGE_WRITE | 2 | Start write-out of dirty pages in the range not yet under write-out (asynchronous) |
| SYNC_FILE_RANGE_WAIT_AFTER | 4 | Wait for write-out of the range after writing |

flags 0 is a permitted no-op. WAIT_BEFORE/WAIT_AFTER surface I/O and ENOSPC errors of the write-out. Useful combinations per the man page: WAIT_BEFORE|WRITE (data-integrity start), WRITE alone (async flush), WAIT_BEFORE or WAIT_AFTER alone (wait and collect results), and all three (full-range integrity wait). fd must refer to a regular file, block device, or directory.

## Return value and errors

Returns 0 on success; -1 with errno: EBADF, EINVAL (bad flag, offset, or nbytes), EIO, ENOMEM, ENOSPC, ESPIPE (other file types).

## Flags and constants

The header also defines SYNC_FILE_RANGE_WRITE_AND_WAIT (7), the all-three combination, as a convenience constant (/usr/include/linux/fs.h).

## Security and notes

- The man page's warning is blunt: extremely dangerous and not for portable programs. No metadata is written, so except for strict overwrites of already-instantiated blocks (impossible on copy-on-write filesystems such as btrfs) there is no crash guarantee; disk caches are not flushed.
- On architectures needing aligned 64-bit register pairs the argument order differs (sync_file_range2: fd, flags, offset, nbytes); glibc hides this.

## References

- man2/sync_file_range.2 in the cached man-pages tree.
- Header: /usr/include/linux/fs.h (SYNC_FILE_RANGE_* values).
- [Syscalls ledger](../ledger.md) rows SC-sync_file_range, SC-arm_sync_file_range, SC-sync_file_range2.
- Siblings: [fsync](fsync.md), [sync](sync.md), [posix_fadvise](posix_fadvise.md).
