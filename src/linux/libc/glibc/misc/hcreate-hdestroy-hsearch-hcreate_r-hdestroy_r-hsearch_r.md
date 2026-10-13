# `hcreate` / `hdestroy` / `hsearch` / `hcreate_r` / `hdestroy_r` / `hsearch_r` (3) - glibc

> Split from the chapter *glibc: Searching and Sorting* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `search.h` (`_r` variants under `__USE_GNU`) |
| Standards | SVr4, POSIX.1-2001/2008 (`hcreate`, `hdestroy`, `hsearch`); GNU extensions (`*_r` trio) |
| Exported | `hcreate@@GLIBC_2.2.5`, `hdestroy@@GLIBC_2.2.5`, `hsearch@@GLIBC_2.2.5`, `hcreate_r@@GLIBC_2.2.5`, `hdestroy_r@@GLIBC_2.2.5`, `hsearch_r@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:hsearch` (non-`_r` trio); MT-Safe `race:htab` (`_r` trio) (`hsearch(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-hcreate, GLIBC-hdestroy, GLIBC-hsearch, GLIBC-hcreate_r, GLIBC-hdestroy_r, GLIBC-hsearch_r |

## Declaration and gates

```c
#include <search.h>

typedef enum { FIND, ENTER } ACTION;      /* /usr/include/search.h lines 62-67 */
typedef struct entry {                    /* lines 69-74 */
    char *key;
    void *data;
} ENTRY;

int  hcreate(size_t nel);                 /* lines 87-93, no extra gate */
void hdestroy(void);
ENTRY *hsearch(ENTRY item, ACTION action);

#ifdef __USE_GNU                          /* lines 95-109 */
int  hcreate_r(size_t nel, struct hsearch_data *htab);
void hdestroy_r(struct hsearch_data *htab);
int  hsearch_r(ENTRY item, ACTION action, ENTRY **retval,
               struct hsearch_data *htab);
#endif
```

The whole family sits inside a
`#if defined __USE_MISC || defined __USE_XOPEN_EXTENDED`
block opened at `/usr/include/search.h` line 29, so strict ISO C
dialects hide it; the glibc default feature set exposes it.

## Semantics

`hcreate` allocates a hash table for string keys with capacity `nel`
(glibc rounds the size up; the man page suggests at least 25% headroom to
limit collisions, `hsearch(3)` NOTES). The capacity is fixed for the
table's life. Only one table exists per process for the non-reentrant
trio; `hsearch` looks a key up with `strcmp`, returning the table entry
for `FIND`, or inserting a copy of `item` for `ENTER`. `hdestroy` frees
the table so a new `hcreate` can follow. The `_r` trio operates on a
caller-owned `struct hsearch_data`, which must be zeroed before the
first `hcreate_r`; `hsearch_r` returns the result through `*retval`
instead of the function result (`hsearch(3)`).

## Gotchas and portability

- `hdestroy`/`hdestroy_r` never free the `key`/`data` buffers; the
  application keeps that bookkeeping (`hsearch(3)` NOTES).
- `ENTER` on an existing key: POSIX says only `data` semantics for
  failed searches, but glibc's implementation updates `data` on the
  stored entry, so re-`ENTER` acts as an update (`hsearch(3)` BUGS).
- Entries cannot be deleted; there is no `hdelete`.
- The non-`_r` table is global state: `MT-Unsafe race:hsearch`.
- musl 1.2.5 provides all six (`musl src/search/hsearch.c`; `_r`
  variants under `_GNU_SOURCE` in `include/search.h`).

## Errors

`hcreate`/`hcreate_r` return 0 on failure (`ENOMEM`). `hsearch` returns
NULL when `ENTER` hits a full table (`ENOMEM`) or `FIND` misses
(`ESRCH`, glibc; POSIX only specifies `ENOMEM`). `hsearch_r` returns 0
and sets `errno`; the `_r` functions fail with `EINVAL` when `htab` is
NULL.

## References

- glibc manual: `search.texi`, node *Hash Search Function*
- man3: `hsearch(3)` (covers all six names)
- headers: `/usr/include/search.h`
- musl: `include/search.h`, `src/search/hsearch.c`
