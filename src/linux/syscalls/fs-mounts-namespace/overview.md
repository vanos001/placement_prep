# fs-mount syscalls — function index

This hub indexes the per-function pages of the `fs-mount` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable — the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 · i386 · g64 · arm) | Since | Status |
|---|---|---|---|---|
| [add_key](add_key.md) | `add_key` | x64 248 · i386 286 · g64 217 · arm 309 | 2.6.10 | documented |
| [chdir](chdir.md) | `chdir`, `fchdir` | x64 80 · i386 12 · g64 49 · arm 12 | 1.0 | documented |
| [chmod](chmod.md) | `chmod`, `fchmod`, `fchmodat` | x64 90 · i386 15 · g64 — · arm 15 | 1.0 | documented |
| [chown](chown.md) | `chown`, `fchown`, `fchownat`, `lchown` | x64 92 · i386 182 · g64 — · arm 182 | 2.2 | documented |
| [chroot](chroot.md) | `chroot` | x64 161 · i386 61 · g64 51 · arm 61 | 1.0 | documented |
| [fanotify_init](fanotify_init.md) | `fanotify_init` | x64 300 · i386 338 · g64 262 · arm 367 | 2.6.37 | documented |
| [fanotify_mark](fanotify_mark.md) | `fanotify_mark` | x64 301 · i386 339 · g64 263 · arm 368 | 2.6.37 | documented |
| [fchmodat2](fchmodat2.md) | `fchmodat2` | x64 452 · i386 452 · g64 452 · arm 452 | — | source-limited |
| [fchroot](fchroot.md) | `fchroot` | x64 472 · i386 472 · g64 472 · arm 472 | — | source-limited |
| [getxattr](getxattr.md) | `fgetxattr`, `getxattr`, `lgetxattr` | x64 193 · i386 231 · g64 10 · arm 231 | 2.6 | documented |
| [file_getattr](file_getattr.md) | `file_getattr` | x64 468 · i386 468 · g64 468 · arm 468 | — | source-limited |
| [file_setattr](file_setattr.md) | `file_setattr` | x64 469 · i386 469 · g64 469 · arm 469 | — | source-limited |
| [listxattr](listxattr.md) | `flistxattr`, `listxattr`, `llistxattr` | x64 196 · i386 234 · g64 13 · arm 234 | 2.6 | documented |
| [removexattr](removexattr.md) | `fremovexattr`, `lremovexattr`, `removexattr` | x64 199 · i386 237 · g64 16 · arm 237 | 2.6 | documented |
| [fsconfig](fsconfig.md) | `fsconfig` | x64 431 · i386 431 · g64 431 · arm 431 | 5.2 | documented |
| [setxattr](setxattr.md) | `fsetxattr`, `lsetxattr`, `setxattr` | x64 190 · i386 228 · g64 7 · arm 228 | 2.6 | documented |
| [fsmount](fsmount.md) | `fsmount` | x64 432 · i386 432 · g64 432 · arm 432 | 5.2 | documented |
| [fsopen](fsopen.md) | `fsopen` | x64 430 · i386 430 · g64 430 · arm 430 | 5.2 | documented |
| [fspick](fspick.md) | `fspick` | x64 433 · i386 433 · g64 433 · arm 433 | 5.2 | documented |
| [futimesat](futimesat.md) | `futimesat` | x64 261 · i386 299 · g64 — · arm 326 | 2.6.16 | documented |
| [getcwd](getcwd.md) | `getcwd` | x64 79 · i386 183 · g64 17 · arm 183 | 2.2 | documented |
| [getxattrat](getxattrat.md) | `getxattrat` | x64 464 · i386 464 · g64 464 · arm 464 | — | source-limited |
| [inotify_add_watch](inotify_add_watch.md) | `inotify_add_watch` | x64 254 · i386 292 · g64 27 · arm 317 | 2.6.13 | documented |
| [inotify_init](inotify_init.md) | `inotify_init`, `inotify_init1` | x64 253 · i386 291 · g64 — · arm 316 | 2.6.13 | documented |
| [inotify_rm_watch](inotify_rm_watch.md) | `inotify_rm_watch` | x64 255 · i386 293 · g64 28 · arm 318 | 2.6.13 | documented |
| [keyctl](keyctl.md) | `keyctl` | x64 250 · i386 288 · g64 219 · arm 311 | 2.6.10 | documented |
| [link](link.md) | `link`, `linkat` | x64 86 · i386 9 · g64 — · arm 9 | 1.0 | documented |
| [listmount](listmount.md) | `listmount` | x64 458 · i386 458 · g64 458 · arm 458 | — | documented |
| [listns](listns.md) | `listns` | x64 470 · i386 470 · g64 470 · arm 470 | — | source-limited |
| [listxattrat](listxattrat.md) | `listxattrat` | x64 465 · i386 465 · g64 465 · arm 465 | — | source-limited |
| [mkdir](mkdir.md) | `mkdir`, `mkdirat` | x64 83 · i386 39 · g64 — · arm 39 | 1.0 | documented |
| [mknod](mknod.md) | `mknod`, `mknodat` | x64 133 · i386 14 · g64 — · arm 14 | 1.0 | documented |
| [mount](mount.md) | `mount` | x64 165 · i386 21 · g64 40 · arm 21 | 1.0 | documented |
| [mount_setattr](mount_setattr.md) | `mount_setattr` | x64 442 · i386 442 · g64 442 · arm 442 | — | documented |
| [move_mount](move_mount.md) | `move_mount` | x64 429 · i386 429 · g64 429 · arm 429 | 5.2 | documented |
| [open_by_handle_at](open_by_handle_at.md) | `name_to_handle_at`, `open_by_handle_at` | x64 303 · i386 341 · g64 264 · arm 370 | 2.6.39 | documented |
| [open_tree](open_tree.md) | `open_tree` | x64 428 · i386 428 · g64 428 · arm 428 | 5.2 | documented |
| [open_tree_attr](open_tree_attr.md) | `open_tree_attr` | x64 467 · i386 467 · g64 467 · arm 467 | — | documented |
| [pivot_root](pivot_root.md) | `pivot_root` | x64 155 · i386 217 · g64 41 · arm 218 | 2.3.41 | documented |
| [quotactl](quotactl.md) | `quotactl` | x64 179 · i386 131 · g64 60 · arm 131 | 1.0 | documented |
| [quotactl_fd](quotactl_fd.md) | `quotactl_fd` | x64 443 · i386 443 · g64 443 · arm 443 | 5.14 | documented |
| [removexattrat](removexattrat.md) | `removexattrat` | x64 466 · i386 466 · g64 466 · arm 466 | — | source-limited |
| [rename](rename.md) | `rename`, `renameat`, `renameat2` | x64 82 · i386 38 · g64 — · arm 38 | 1.0 | documented |
| [request_key](request_key.md) | `request_key` | x64 249 · i386 287 · g64 218 · arm 310 | 2.6.10 | documented |
| [rmdir](rmdir.md) | `rmdir` | x64 84 · i386 40 · g64 — · arm 40 | 1.0 | documented |
| [setns](setns.md) | `setns` | x64 308 · i386 346 · g64 268 · arm 375 | 3.0 | documented |
| [setxattrat](setxattrat.md) | `setxattrat` | x64 463 · i386 463 · g64 463 · arm 463 | — | source-limited |
| [statmount](statmount.md) | `statmount` | x64 457 · i386 457 · g64 457 · arm 457 | — | documented |
| [symlink](symlink.md) | `symlink`, `symlinkat` | x64 88 · i386 83 · g64 — · arm 83 | 1.0 | documented |
| [umount](umount.md) | `umount`, `umount2` | x64 — · i386 22 · g64 — · arm — | 1.0 | documented |
| [unlink](unlink.md) | `unlink`, `unlinkat` | x64 87 · i386 10 · g64 — · arm 10 | 1.0 | documented |
| [unshare](unshare.md) | `unshare` | x64 272 · i386 310 · g64 97 · arm 337 | 2.6.16 | documented |
| [utime](utime.md) | `utime`, `utimes` | x64 132 · i386 30 · g64 — · arm — | 1.0 | documented |
| [utimensat](utimensat.md) | `utimensat` | x64 280 · i386 320 · g64 88 · arm 348 | 2.6.22 | documented |
| [utimensat_time64](utimensat_time64.md) | `utimensat_time64` | x64 — · i386 412 · g64 — · arm 412 | — | documented |
