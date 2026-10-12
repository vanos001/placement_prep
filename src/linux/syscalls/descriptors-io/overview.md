# desc-io syscalls — function index

This hub indexes the per-function pages of the `desc-io` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable — the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 · i386 · g64 · arm) | Since | Status |
|---|---|---|---|---|
| [llseek](llseek.md) | `_llseek` | x64 — · i386 140 · g64 — · arm 140 | 1.2 | documented |
| [access](access.md) | `access`, `faccessat`, `faccessat2` | x64 21 · i386 33 · g64 — · arm 33 | 1.0 | documented |
| [posix_fadvise](posix_fadvise.md) | `arm_fadvise64_64`, `fadvise64`, `fadvise64_64` | x64 — · i386 — · g64 — · arm 270 | — | documented |
| [sync_file_range](sync_file_range.md) | `arm_sync_file_range`, `sync_file_range`, `sync_file_range2` | x64 — · i386 — · g64 — · arm 341 | — | documented |
| [close](close.md) | `close` | x64 3 · i386 6 · g64 57 · arm 6 | 1.0 | documented |
| [close_range](close_range.md) | `close_range` | x64 436 · i386 436 · g64 436 · arm 436 | 5.9 | documented |
| [copy_file_range](copy_file_range.md) | `copy_file_range` | x64 326 · i386 377 · g64 285 · arm 391 | 4.5 | documented |
| [open](open.md) | `creat`, `open`, `openat` | x64 85 · i386 8 · g64 — · arm 8 | 1.0 | documented |
| [dup](dup.md) | `dup`, `dup2`, `dup3` | x64 32 · i386 41 · g64 23 · arm 41 | 1.0 | documented |
| [fallocate](fallocate.md) | `fallocate` | x64 285 · i386 324 · g64 47 · arm 352 | 2.6.23 | documented |
| [fcntl](fcntl.md) | `fcntl`, `fcntl64` | x64 72 · i386 55 · g64 25 · arm 55 | 1.0 | documented |
| [fsync](fsync.md) | `fdatasync`, `fsync` | x64 75 · i386 148 · g64 83 · arm 148 | 2.0 | documented |
| [flock](flock.md) | `flock` | x64 73 · i386 143 · g64 32 · arm 143 | 2.0 | documented |
| [stat](stat.md) | `fstat`, `lstat`, `stat`, `stat64` | x64 5 · i386 108 · g64 80 · arm 108 | 1.0 | documented |
| [fstat](fstat.md) | `fstat64` | x64 — · i386 197 · g64 — · arm 197 | 2.4 | documented |
| [fstatat](fstatat.md) | `fstatat64`, `newfstatat` | x64 — · i386 300 · g64 — · arm 327 | 2.6.16 | documented |
| [statfs](statfs.md) | `fstatfs`, `statfs`, `statfs64` | x64 138 · i386 100 · g64 44 · arm 100 | 1.0 | documented |
| [fstatfs](fstatfs.md) | `fstatfs64` | x64 — · i386 269 · g64 — · arm 267 | 2.6 | documented |
| [truncate](truncate.md) | `ftruncate`, `truncate`, `truncate64` | x64 77 · i386 93 · g64 46 · arm 93 | 1.0 | documented |
| [ftruncate](ftruncate.md) | `ftruncate64` | x64 — · i386 194 · g64 — · arm 194 | 2.4 | documented |
| [getdents](getdents.md) | `getdents`, `getdents64` | x64 78 · i386 141 · g64 — · arm 141 | 2.0 | documented |
| [ioctl](ioctl.md) | `ioctl` | x64 16 · i386 54 · g64 29 · arm 54 | 1.0 | documented |
| [lseek](lseek.md) | `lseek` | x64 8 · i386 19 · g64 62 · arm 19 | 1.0 | documented |
| [lstat](lstat.md) | `lstat64` | x64 — · i386 196 · g64 — · arm 196 | 2.4 | documented |
| [mmap2](mmap2.md) | `mmap2` | x64 — · i386 192 · g64 — · arm 192 | 2.4 | researched |
| [openat2](openat2.md) | `openat2` | x64 437 · i386 437 · g64 437 · arm 437 | 5.6 | documented |
| [pread](pread.md) | `pread64` | x64 17 · i386 180 · g64 67 · arm 180 | — | documented |
| [readv](readv.md) | `preadv`, `preadv2`, `pwritev`, `pwritev2`, `readv`, `writev` | x64 295 · i386 333 · g64 69 · arm 361 | 2.6.30 | documented |
| [pwrite](pwrite.md) | `pwrite64` | x64 18 · i386 181 · g64 68 · arm 181 | — | documented |
| [read](read.md) | `read` | x64 0 · i386 3 · g64 63 · arm 3 | 1.0 | documented |
| [readahead](readahead.md) | `readahead` | x64 187 · i386 225 · g64 213 · arm 225 | 2.4.13 | researched |
| [readdir](readdir.md) | `readdir` | x64 — · i386 89 · g64 — · arm — | 1.0 | researched |
| [readlink](readlink.md) | `readlink`, `readlinkat` | x64 89 · i386 85 · g64 — · arm 85 | 1.0 | documented |
| [sendfile](sendfile.md) | `sendfile`, `sendfile64` | x64 40 · i386 187 · g64 71 · arm 187 | 2.2 | documented |
| [splice](splice.md) | `splice` | x64 275 · i386 313 · g64 76 · arm 340 | 2.6.17 | documented |
| [statx](statx.md) | `statx` | x64 332 · i386 383 · g64 291 · arm 397 | 4.11 | documented |
| [sync](sync.md) | `sync`, `syncfs` | x64 162 · i386 36 · g64 81 · arm 36 | 1.0 | documented |
| [tee](tee.md) | `tee` | x64 276 · i386 315 · g64 77 · arm 342 | 2.6.17 | documented |
| [umask](umask.md) | `umask` | x64 95 · i386 60 · g64 166 · arm 60 | 1.0 | documented |
| [vmsplice](vmsplice.md) | `vmsplice` | x64 278 · i386 316 · g64 75 · arm 343 | 2.6.17 | documented |
| [write](write.md) | `write` | x64 1 · i386 4 · g64 64 · arm 4 | 1.0 | documented |
