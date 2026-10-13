# fs-mount syscalls - function index

This hub indexes the per-function pages of the `fs-mount` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable -- the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 / i386 / g64 / arm) | Since | Status |
|---|---|---|---|---|
| [add_key](add_key.md) | `add_key` x64 248 | i386 286 | g64 217 | arm 309, `keyctl` x64 250 | i386 288 | g64 219 | arm 311, `request_key` x64 249 | i386 287 | g64 218 | arm 310 | - | 2.6.10 | documented |
| [chdir](chdir.md) | `chdir` x64 80 | i386 12 | g64 49 | arm 12, `fchdir` x64 81 | i386 133 | g64 50 | arm 133 | - | 1.0 | documented |
| [chmod](chmod.md) | `chmod` x64 90 | i386 15 | g64 -- | arm 15, `fchmod` x64 91 | i386 94 | g64 52 | arm 94, `fchmodat` x64 268 | i386 306 | g64 53 | arm 333, `fchmodat2` x64 452 | i386 452 | g64 452 | arm 452 | - | 1.0 | documented |
| [chown](chown.md) | `chown` x64 92 | i386 182 | g64 -- | arm 182, `chown32` x64 -- | i386 212 | g64 -- | arm 212, `fchown` x64 93 | i386 95 | g64 55 | arm 95, `fchown32` x64 -- | i386 207 | g64 -- | arm 207, `fchownat` x64 260 | i386 298 | g64 54 | arm 325, `lchown` x64 94 | i386 16 | g64 -- | arm 16, `lchown32` x64 -- | i386 198 | g64 -- | arm 198 | - | 2.2 | documented |
| [chroot](chroot.md) | `chroot` x64 161 | i386 61 | g64 51 | arm 61 | - | 1.0 | documented |
| [fanotify_init](fanotify_init.md) | `fanotify_init` x64 300 | i386 338 | g64 262 | arm 367 | - | 2.6.37 | documented |
| [fanotify_mark](fanotify_mark.md) | `fanotify_mark` x64 301 | i386 339 | g64 263 | arm 368 | - | 2.6.37 | documented |
| [fchroot](fchroot.md) | `fchroot` x64 472 | i386 472 | g64 472 | arm 472 | - | -- | source-limited |
| [setxattr](setxattr.md) | `fgetxattr` x64 193 | i386 231 | g64 10 | arm 231, `flistxattr` x64 196 | i386 234 | g64 13 | arm 234, `fremovexattr` x64 199 | i386 237 | g64 16 | arm 237, `fsetxattr` x64 190 | i386 228 | g64 7 | arm 228, `getxattr` x64 191 | i386 229 | g64 8 | arm 229, `lgetxattr` x64 192 | i386 230 | g64 9 | arm 230, `listxattr` x64 194 | i386 232 | g64 11 | arm 232, `llistxattr` x64 195 | i386 233 | g64 12 | arm 233, `lremovexattr` x64 198 | i386 236 | g64 15 | arm 236, `lsetxattr` x64 189 | i386 227 | g64 6 | arm 227, `removexattr` x64 197 | i386 235 | g64 14 | arm 235, `setxattr` x64 188 | i386 226 | g64 5 | arm 226 | - | 2.6 | documented |
| [file_getattr](file_getattr.md) | `file_getattr` x64 468 | i386 468 | g64 468 | arm 468 | - | -- | source-limited |
| [file_setattr](file_setattr.md) | `file_setattr` x64 469 | i386 469 | g64 469 | arm 469 | - | -- | source-limited |
| [fsconfig](fsconfig.md) | `fsconfig` x64 431 | i386 431 | g64 431 | arm 431 | - | 5.2 | documented |
| [fsmount](fsmount.md) | `fsmount` x64 432 | i386 432 | g64 432 | arm 432 | - | 5.2 | documented |
| [fsopen](fsopen.md) | `fsopen` x64 430 | i386 430 | g64 430 | arm 430 | - | 5.2 | documented |
| [fspick](fspick.md) | `fspick` x64 433 | i386 433 | g64 433 | arm 433 | - | 5.2 | documented |
| [utimensat](utimensat.md) | `futimesat` x64 261 | i386 299 | g64 -- | arm 326, `utime` x64 132 | i386 30 | g64 -- | arm --, `utimensat` x64 280 | i386 320 | g64 88 | arm 348, `utimensat_time64` x64 -- | i386 412 | g64 -- | arm 412, `utimes` x64 235 | i386 271 | g64 -- | arm 269 | - | 2.6.16 | documented |
| [getcwd](getcwd.md) | `getcwd` x64 79 | i386 183 | g64 17 | arm 183 | - | 2.2 | documented |
| [getxattrat](getxattrat.md) | `getxattrat` x64 464 | i386 464 | g64 464 | arm 464 | - | -- | source-limited |
| [inotify_add_watch](inotify_add_watch.md) | `inotify_add_watch` x64 254 | i386 292 | g64 27 | arm 317 | - | 2.6.13 | documented |
| [inotify_init](inotify_init.md) | `inotify_init` x64 253 | i386 291 | g64 -- | arm 316, `inotify_init1` x64 294 | i386 332 | g64 26 | arm 360 | - | 2.6.13 | documented |
| [inotify_rm_watch](inotify_rm_watch.md) | `inotify_rm_watch` x64 255 | i386 293 | g64 28 | arm 318 | - | 2.6.13 | documented |
| [link](link.md) | `link` x64 86 | i386 9 | g64 -- | arm 9, `linkat` x64 265 | i386 303 | g64 37 | arm 330, `symlink` x64 88 | i386 83 | g64 -- | arm 83, `symlinkat` x64 266 | i386 304 | g64 36 | arm 331 | - | 1.0 | documented |
| [statmount](statmount.md) | `listmount` x64 458 | i386 458 | g64 458 | arm 458, `statmount` x64 457 | i386 457 | g64 457 | arm 457 | - | -- | documented |
| [listns](listns.md) | `listns` x64 470 | i386 470 | g64 470 | arm 470 | - | -- | source-limited |
| [listxattrat](listxattrat.md) | `listxattrat` x64 465 | i386 465 | g64 465 | arm 465 | - | -- | source-limited |
| [mkdir](mkdir.md) | `mkdir` x64 83 | i386 39 | g64 -- | arm 39, `mkdirat` x64 258 | i386 296 | g64 34 | arm 323, `rmdir` x64 84 | i386 40 | g64 -- | arm 40 | - | 1.0 | documented |
| [mknod](mknod.md) | `mknod` x64 133 | i386 14 | g64 -- | arm 14, `mknodat` x64 259 | i386 297 | g64 33 | arm 324 | - | 1.0 | documented |
| [mount](mount.md) | `mount` x64 165 | i386 21 | g64 40 | arm 21 | - | 1.0 | documented |
| [mount_setattr](mount_setattr.md) | `mount_setattr` x64 442 | i386 442 | g64 442 | arm 442 | - | -- | documented |
| [move_mount](move_mount.md) | `move_mount` x64 429 | i386 429 | g64 429 | arm 429 | - | 5.2 | documented |
| [open_by_handle_at](open_by_handle_at.md) | `name_to_handle_at` x64 303 | i386 341 | g64 264 | arm 370, `open_by_handle_at` x64 304 | i386 342 | g64 265 | arm 371 | - | 2.6.39 | documented |
| [open_tree](open_tree.md) | `open_tree` x64 428 | i386 428 | g64 428 | arm 428 | - | 5.2 | documented |
| [open_tree_attr](open_tree_attr.md) | `open_tree_attr` x64 467 | i386 467 | g64 467 | arm 467 | - | -- | documented |
| [pivot_root](pivot_root.md) | `pivot_root` x64 155 | i386 217 | g64 41 | arm 218 | - | 2.3.41 | documented |
| [quotactl](quotactl.md) | `quotactl` x64 179 | i386 131 | g64 60 | arm 131, `quotactl_fd` x64 443 | i386 443 | g64 443 | arm 443 | - | 1.0 | documented |
| [removexattrat](removexattrat.md) | `removexattrat` x64 466 | i386 466 | g64 466 | arm 466 | - | -- | source-limited |
| [rename](rename.md) | `rename` x64 82 | i386 38 | g64 -- | arm 38, `renameat` x64 264 | i386 302 | g64 -- | arm 329, `renameat2` x64 316 | i386 353 | g64 276 | arm 382 | - | 1.0 | documented |
| [setns](setns.md) | `setns` x64 308 | i386 346 | g64 268 | arm 375 | - | 3.0 | documented |
| [setxattrat](setxattrat.md) | `setxattrat` x64 463 | i386 463 | g64 463 | arm 463 | - | -- | source-limited |
| [umount2](umount2.md) | `umount` x64 -- | i386 22 | g64 -- | arm --, `umount2` x64 166 | i386 52 | g64 39 | arm 52 | - | 1.0 | documented |
| [unlink](unlink.md) | `unlink` x64 87 | i386 10 | g64 -- | arm 10, `unlinkat` x64 263 | i386 301 | g64 35 | arm 328 | - | 1.0 | documented |
| [unshare](unshare.md) | `unshare` x64 272 | i386 310 | g64 97 | arm 337 | - | 2.6.16 | documented |
