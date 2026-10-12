# memory syscalls — function index

This hub indexes the per-function pages of the `memory` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable — the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 · i386 · g64 · arm) | Since | Status |
|---|---|---|---|---|
| [brk](brk.md) | `brk` | x64 12 · i386 45 · g64 214 · arm 45 | 1.0 | documented |
| [cachestat](cachestat.md) | `cachestat` | x64 451 · i386 451 · g64 451 · arm 451 | 6.5 | documented |
| [get_mempolicy](get_mempolicy.md) | `get_mempolicy` | x64 239 · i386 275 · g64 236 · arm 320 | 2.6.6 | documented |
| [madvise](madvise.md) | `madvise` | x64 28 · i386 219 · g64 233 · arm 220 | 2.4 | documented |
| [map_shadow_stack](map_shadow_stack.md) | `map_shadow_stack` | x64 453 · i386 453 · g64 453 · arm 453 | 6.6 | documented |
| [mbind](mbind.md) | `mbind` | x64 237 · i386 274 · g64 235 · arm 319 | 2.6.6 | documented |
| [membarrier](membarrier.md) | `membarrier` | x64 324 · i386 375 · g64 283 · arm 389 | 3.17 | documented |
| [memfd_create](memfd_create.md) | `memfd_create` | x64 319 · i386 356 · g64 279 · arm 385 | 3.17 | documented |
| [memfd_secret](memfd_secret.md) | `memfd_secret` | x64 447 · i386 447 · g64 — · arm — | 5.14 | documented |
| [migrate_pages](migrate_pages.md) | `migrate_pages` | x64 256 · i386 294 · g64 238 · arm 400 | 2.6.16 | documented |
| [mincore](mincore.md) | `mincore` | x64 27 · i386 218 · g64 232 · arm 219 | 2.4 | documented |
| [mlock](mlock.md) | `mlock`, `mlock2`, `mlockall`, `munlock`, `munlockall` | x64 149 · i386 150 · g64 228 · arm 150 | 2.0 | documented |
| [mmap](mmap.md) | `mmap`, `munmap` | x64 9 · i386 90 · g64 222 · arm — | 1.0 | documented |
| [move_pages](move_pages.md) | `move_pages` | x64 279 · i386 317 · g64 239 · arm 344 | 2.6.18 | documented |
| [mprotect](mprotect.md) | `mprotect`, `pkey_mprotect` | x64 10 · i386 125 · g64 226 · arm 125 | 1.0 | documented |
| [mremap](mremap.md) | `mremap` | x64 25 · i386 163 · g64 216 · arm 163 | 2.0 | documented |
| [mseal](mseal.md) | `mseal` | x64 462 · i386 462 · g64 462 · arm 462 | 6.10 | documented |
| [msync](msync.md) | `msync` | x64 26 · i386 144 · g64 227 · arm 144 | 2.0 | documented |
| [pkey_alloc](pkey_alloc.md) | `pkey_alloc`, `pkey_free` | x64 330 · i386 381 · g64 289 · arm 395 | 4.8 | documented |
| [process_vm_readv](process_vm_readv.md) | `process_vm_readv`, `process_vm_writev` | x64 310 · i386 347 · g64 270 · arm 376 | 3.2 | documented |
| [remap_file_pages](remap_file_pages.md) | `remap_file_pages` | x64 216 · i386 257 · g64 234 · arm 253 | 2.6 | researched |
| [set_mempolicy](set_mempolicy.md) | `set_mempolicy` | x64 238 · i386 276 · g64 237 · arm 321 | 2.6.6 | documented |
| [set_mempolicy_home_node](set_mempolicy_home_node.md) | `set_mempolicy_home_node` | x64 450 · i386 450 · g64 450 · arm 450 | 5.17 | documented |
| [swapon](swapon.md) | `swapoff`, `swapon` | x64 168 · i386 115 · g64 225 · arm 115 | 1.0 | researched |
| [userfaultfd](userfaultfd.md) | `userfaultfd` | x64 323 · i386 374 · g64 282 · arm 388 | 4.3 | documented |
