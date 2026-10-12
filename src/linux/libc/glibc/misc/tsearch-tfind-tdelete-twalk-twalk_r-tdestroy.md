# `tsearch` / `tfind` / `tdelete` / `twalk` / `twalk_r` / `tdestroy` (3) - glibc

> Split from the chapter *glibc: Searching and Sorting* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `search.h` (`twalk_r`, `tdestroy` under `__USE_GNU`) |
| Standards | SVr4, POSIX.1-2001/2008 (`tsearch`, `tfind`, `tdelete`, `twalk`); GNU extensions (`twalk_r`, `tdestroy`) |
| Exported | `tsearch@@GLIBC_2.2.5`, `tfind@@GLIBC_2.2.5`, `tdelete@@GLIBC_2.2.5`, `twalk@@GLIBC_2.2.5`, `tdestroy@@GLIBC_2.2.5`, `twalk_r@@GLIBC_2.30` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `race:rootp` (`tsearch`/`tfind`/`tdelete`), `race:root` (`twalk`, `twalk_r`), MT-Safe (`tdestroy`) (`tsearch(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-tsearch, GLIBC-tfind, GLIBC-tdelete, GLIBC-twalk, GLIBC-twalk_r, GLIBC-tdestroy |

## Declaration and gates

```c
#include <search.h>

typedef enum { preorder, postorder, endorder, leaf } VISIT;
                                          /* /usr/include/search.h lines 118-125 */

void *tsearch(const void *key, void **rootp,
              int (*compar)(const void *, const void *));      /* lines 129-131 */
void *tfind(const void *key, void *const *rootp,
            int (*compar)(const void *, const void *));        /* lines 134-136 */
void *tdelete(const void *restrict key, void **restrict rootp,
              int (*compar)(const void *, const void *));      /* lines 138-140 */
void twalk(const void *root,
           void (*action)(const void *nodep, VISIT which, int depth));

#ifdef __USE_GNU                            /* lines 152-165 */
void twalk_r(const void *root,
             void (*action)(const void *nodep, VISIT which, void *closure),
             void *closure);
void tdestroy(void *root, void (*free_node)(void *nodep));
#endif
```

## Semantics

The family manages a binary search tree built from Knuth 6.2.2 Algorithm
T; nodes are opaque, hold a pointer to the user data, and `compar`
orders it. `tsearch` looks up `key`, inserting it if absent, and
returns a pointer to the node (castable to `void **` to reach the data
pointer); NULL means allocation failure. `tfind` is the pure lookup,
NULL on miss. `tdelete` removes a node and returns a pointer to its
parent, or NULL when the key was not found; deleting the root returns a
dangling pointer. `twalk` traverses depth-first, left-to-right,
invoking `action` three times per internal node (`preorder`,
`postorder` -- really the in-order visit -- and `endorder`) and once
per leaf, with the root at depth 0. `twalk_r` (glibc 2.30) passes a
`closure` instead of the depth, so state moves through the callback
without globals. `tdestroy` dismantles the whole tree, calling
`free_node` on each data pointer (`tsearch(3)`, manual *Tree Search
Function*).

## Gotchas and portability

- `twalk` takes the root pointer itself; the other five take a pointer
  to the variable that holds it (`tsearch(3)` NOTES).
- `tdelete` frees only the tree node, never the user data; pair with
  `tdestroy(root, free)` to reclaim data.
- Duplicate keys are collapsed; which existing node `tfind` returns is
  unspecified.
- musl 1.2.5 has all but `twalk_r` (`musl src/search/tsearch.c`,
  `tdestroy.c`; no `twalk_r` in `include/search.h`).

## References

- glibc manual: `search.texi`, node *Tree Search Function*
- man3: `tsearch(3)` (covers all six names)
- headers: `/usr/include/search.h`
- musl: `include/search.h`, `src/search/`
