# desc-io syscalls - function index

This hub indexes the per-function pages of the `desc-io` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable -- the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 / i386 / g64 / arm) | Since | Status |
|---|---|---|---|---|
| [lseek](lseek.md) | `_llseek` x64 -- | i386 140 | g64 -- | arm 140, `lseek` x64 8 | i386 19 | g64 62 | arm 19 | - | 1.2 | documented |
| [access](access.md) | `access` x64 21 | i386 33 | g64 -- | arm 33, `faccessat` x64 269 | i386 307 | g64 48 | arm 334, `faccessat2` x64 439 | i386 439 | g64 439 | arm 439 | - | 1.0 | documented |
| [posix_fadvise](posix_fadvise.md) | `arm_fadvise64_64` x64 -- | i386 -- | g64 -- | arm 270, `fadvise64` x64 221 | i386 250 | g64 223 | arm --, `fadvise64_64` x64 -- | i386 272 | g64 -- | arm -- | - | -- | documented |
| [sync_file_range](sync_file_range.md) | `arm_sync_file_range` x64 -- | i386 -- | g64 -- | arm 341, `sync_file_range` x64 277 | i386 314 | g64 84 | arm --, `sync_file_range2` x64 -- | i386 -- | g64 -- | arm -- | - | -- | documented |
| [close](close.md) | `close` x64 3 | i386 6 | g64 57 | arm 6 | - | 1.0 | documented |
| [close_range](close_range.md) | `close_range` x64 436 | i386 436 | g64 436 | arm 436 | - | 5.9 | documented |
| [copy_file_range](copy_file_range.md) | `copy_file_range` x64 326 | i386 377 | g64 285 | arm 391 | - | 4.5 | documented |
| [open](open.md) | `creat` x64 85 | i386 8 | g64 -- | arm 8, `open` x64 2 | i386 5 | g64 -- | arm 5, `openat` x64 257 | i386 295 | g64 56 | arm 322 | - | 1.0 | documented |
| [dup](dup.md) | `dup` x64 32 | i386 41 | g64 23 | arm 41, `dup2` x64 33 | i386 63 | g64 -- | arm 63, `dup3` x64 292 | i386 330 | g64 24 | arm 358 | - | 1.0 | documented |
| [fallocate](fallocate.md) | `fallocate` x64 285 | i386 324 | g64 47 | arm 352 | - | 2.6.23 | documented |
| [fcntl](fcntl.md) | `fcntl` x64 72 | i386 55 | g64 25 | arm 55, `fcntl64` x64 -- | i386 221 | g64 -- | arm 221 | - | 1.0 | documented |
| [fsync](fsync.md) | `fdatasync` x64 75 | i386 148 | g64 83 | arm 148, `fsync` x64 74 | i386 118 | g64 82 | arm 118 | - | 2.0 | documented |
| [flock](flock.md) | `flock` x64 73 | i386 143 | g64 32 | arm 143 | - | 2.0 | documented |
| [stat](stat.md) | `fstat` x64 5 | i386 108 | g64 80 | arm 108, `fstat64` x64 -- | i386 197 | g64 -- | arm 197, `fstatat64` x64 -- | i386 300 | g64 -- | arm 327, `lstat` x64 6 | i386 107 | g64 -- | arm 107, `lstat64` x64 -- | i386 196 | g64 -- | arm 196, `newfstatat` x64 262 | i386 -- | g64 79 | arm --, `stat` x64 4 | i386 106 | g64 -- | arm 106, `stat64` x64 -- | i386 195 | g64 -- | arm 195 | - | 1.0 | documented |
| [statfs](statfs.md) | `fstatfs` x64 138 | i386 100 | g64 44 | arm 100, `fstatfs64` x64 -- | i386 269 | g64 -- | arm 267, `statfs` x64 137 | i386 99 | g64 43 | arm 99, `statfs64` x64 -- | i386 268 | g64 -- | arm 266 | - | 1.0 | documented |
| [truncate](truncate.md) | `ftruncate` x64 77 | i386 93 | g64 46 | arm 93, `ftruncate64` x64 -- | i386 194 | g64 -- | arm 194, `truncate` x64 76 | i386 92 | g64 45 | arm 92, `truncate64` x64 -- | i386 193 | g64 -- | arm 193 | - | 1.0 | documented |
| [getdents64](getdents64.md) | `getdents` x64 78 | i386 141 | g64 -- | arm 141, `getdents64` x64 217 | i386 220 | g64 61 | arm 217 | - | 2.0 | documented |
| [ioctl](ioctl.md) | `ioctl` x64 16 | i386 54 | g64 29 | arm 54 | - | 1.0 | documented |
| [mmap2](mmap2.md) | `mmap2` x64 -- | i386 192 | g64 -- | arm 192 | - | 2.4 | researched |
| [openat2](openat2.md) | `openat2` x64 437 | i386 437 | g64 437 | arm 437 | - | 5.6 | documented |
| [pread](pread.md) | `pread64` x64 17 | i386 180 | g64 67 | arm 180, `pwrite64` x64 18 | i386 181 | g64 68 | arm 181 | - | -- | documented |
| [readv](readv.md) | `preadv` x64 295 | i386 333 | g64 69 | arm 361, `preadv2` x64 327 | i386 378 | g64 286 | arm 392, `pwritev` x64 296 | i386 334 | g64 70 | arm 362, `pwritev2` x64 328 | i386 379 | g64 287 | arm 393, `readv` x64 19 | i386 145 | g64 65 | arm 145, `writev` x64 20 | i386 146 | g64 66 | arm 146 | - | 2.6.30 | documented |
| [read](read.md) | `read` x64 0 | i386 3 | g64 63 | arm 3 | - | 1.0 | documented |
| [readahead](readahead.md) | `readahead` x64 187 | i386 225 | g64 213 | arm 225 | - | 2.4.13 | researched |
| [readdir](readdir.md) | `readdir` x64 -- | i386 89 | g64 -- | arm -- | - | 1.0 | researched |
| [readlink](readlink.md) | `readlink` x64 89 | i386 85 | g64 -- | arm 85, `readlinkat` x64 267 | i386 305 | g64 78 | arm 332 | - | 1.0 | documented |
| [sendfile](sendfile.md) | `sendfile` x64 40 | i386 187 | g64 71 | arm 187, `sendfile64` x64 -- | i386 239 | g64 -- | arm 239 | - | 2.2 | documented |
| [splice](splice.md) | `splice` x64 275 | i386 313 | g64 76 | arm 340, `tee` x64 276 | i386 315 | g64 77 | arm 342, `vmsplice` x64 278 | i386 316 | g64 75 | arm 343 | - | 2.6.17 | documented |
| [statx](statx.md) | `statx` x64 332 | i386 383 | g64 291 | arm 397 | - | 4.11 | documented |
| [sync](sync.md) | `sync` x64 162 | i386 36 | g64 81 | arm 36, `syncfs` x64 306 | i386 344 | g64 267 | arm 373 | - | 1.0 | documented |
| [umask](umask.md) | `umask` x64 95 | i386 60 | g64 166 | arm 60 | - | 1.0 | documented |
| [write](write.md) | `write` x64 1 | i386 4 | g64 64 | arm 4 | - | 1.0 | documented |
