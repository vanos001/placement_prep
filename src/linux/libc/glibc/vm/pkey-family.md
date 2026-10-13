# `pkey_alloc` / `pkey_free` / `pkey_get` / `pkey_set` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/mman.h` via `bits/mman-shared.h` lines 66-78, all under `__USE_GNU` (chain: `sys/mman.h` -> `bits/mman.h` -> `bits/mman-linux.h` -> `bits/mman-shared.h`) |
| Standards | Linux-specific (kernel 4.9; glibc 2.27) |
| Exported | `pkey_alloc@@GLIBC_2.27`, `pkey_free@@GLIBC_2.27`, `pkey_get@@GLIBC_2.27`, `pkey_set@@GLIBC_2.27` (nm, host glibc 2.41) |
| Thread-safety | per-thread by definition (the rights live in the thread's PKRU); no ATTRIBUTES table in pkey_alloc.2 |
| Ledger ID | GLIBC-pkey_alloc, GLIBC-pkey_free, GLIBC-pkey_get, GLIBC-pkey_set |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <sys/mman.h>

int pkey_alloc(unsigned int flags, unsigned int access_rights);
int pkey_free(int pkey);
int pkey_get(int key);
int pkey_set(int key, unsigned int access_rights);
/* bits/mman-shared.h:46-48 */
#define PKEY_DISABLE_ACCESS 0x1
#define PKEY_DISABLE_WRITE  0x2
```

Everything is inside `#ifdef __USE_GNU` (bits/mman-shared.h lines 23-86);
plain `-std=c99` builds need `#define _GNU_SOURCE` first.

## Semantics

`pkey_alloc(flags, access_rights)` allocates a protection key and seeds
its per-thread rights mask from `access_rights` (0, or
`PKEY_DISABLE_ACCESS` / `PKEY_DISABLE_WRITE`, bits may be ORed); `flags`
is reserved and must be 0. It returns a positive key on success. The key
is then attached to memory with `pkey_mprotect` (see the mprotect family
page); afterwards the CPU enforces the key's rights on top of the page
protections (pkey_alloc.2). `pkey_free` releases the key for reuse;
calling it on a key still assigned to live mappings is undefined.
`pkey_set` updates the current thread's rights for a key;
`pkey_get` returns them (bits/mman-shared.h comments, lines 62-74).

## Gotchas and portability

- `pkey_alloc` is the portable support probe: it is always safe to call
  and fails with `ENOSPC` when the CPU/kernel lacks pkeys -- applications
  must handle that, since available keys can shrink at any time
  (pkey_alloc.2 NOTES/ERRORS).
- Keys are scarce: about 15 user keys on x86 (pkey_alloc.2 ERRORS);
  kernel-internal use can reduce that.
- Rights are per-thread (PKRU register on x86), so new threads start with
  the allocation-time rights, and `pkey_set` in one thread does not affect
  others.
- musl 1.2.5: absent -- no pkey declarations in `include/sys/mman.h`, no
  `src/` files; raw `syscall(SYS_pkey_alloc, ...)` only.

## Errors

`EINVAL` (invalid `pkey`, `flags` or `access_rights`), `ENOSPC` (all keys
allocated, or pkeys unsupported on CPU/kernel) for `pkey_alloc`;
`EINVAL`/`ENOSPC` semantics per pkey_alloc.2 (which covers `pkey_free`;
`pkey_get`/`pkey_set` have no man page and are documented only in
bits/mman-shared.h comments).

## References

- man2: `pkey_alloc.2` (covers `pkey_free`; `pkey_mprotect.2` is a `.so` link to mprotect.2)
- headers: `/usr/include/x86_64-linux-gnu/bits/mman-shared.h` (lines 45-82)
- symbols: `nm -D --with-symbol-versions libc.so.6`
