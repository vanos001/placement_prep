# listns(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 470 / 470 / 470 / 470 |
| Since (kernel) | -- in the syscalls(2) version table and the ledger (6.15+ namespace-tree work, kernel/nstree.c) |
| Man page | none (no man2/listns.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; related namespace calls: [setns](setns.md), [unshare](unshare.md) |
| Ledger ID | SC-listns |

## Purpose

listns() enumerates namespaces visible to the caller: it fills an array of 64-bit namespace IDs, optionally filtered by namespace type and by owning user namespace, driven by a request descriptor `struct ns_id_req` (kernel/nstree.c, SYSCALL_DEFINE4(listns)). It is the query side of the namespace-tree work that also added per-namespace IDs (ns_id) and statns(2) -- the introspection piece container supervisors previously approximated by walking /proc.

## Synopsis

```c
struct ns_id_req {            /* include/uapi/linux/nsfs.h */
    __u32 size;               /* NS_ID_REQ_SIZE_VER0 = 32 */
    __u32 spare;
    __u64 ns_id;              /* last namespace ID (restart point) */
    struct {
        __u32 ns_type;        /* bit mask of namespace types to include */
        __u32 spare2;
        __u64 user_ns_id;     /* filter: owning user ns, 0 = any */
    };
};

long syscall(SYS_listns, const struct ns_id_req *req,
             __u64 *ns_ids, size_t nr_ns_ids, unsigned int flags);
```

## Arguments and behavior

`req` carries the filter: `ns_type` is a bitmask of namespace types (the uapi header defines one bit per CLONE_NEW* flag, e.g. USER_NS = 1ULL << 28, PID_NS = 1ULL << 29, NET_NS = 1ULL << 30, include/uapi/linux/nsfs.h); `user_ns_id` filters on the owning user namespace, with the special value LISTNS_CURRENT_USER (0xffffffffffffffff) meaning "the caller's user namespace" (kernel/nstree.c: `if (kreq.user_ns_id) return do_listns_userns(&klns);` and the LISTNS_CURRENT_USER comparisons). `ns_ids`/`nr_ns_ids` form the output array; the implementation caps nr_ns_ids at 1,000,000 -- larger requests fail with EOVERFLOW (`const size_t maxcount = 1000000;`, kernel/nstree.c, body). `flags` must be 0 (EINVAL otherwise). The struct is versioned: `req->size` below NS_ID_REQ_SIZE_VER0 (32) fails, and copy_struct_from_user absorbs growth (kernel/nstree.c, copy_ns_id_req).

## Return value and errors

Returns the number of namespace IDs written to `ns_ids` (a count, not bytes); a negated error on the raw path: EINVAL (flags nonzero; req->size below VER0), EOVERFLOW (nr_ns_ids above maxcount), EFAULT (req or ns_ids outside the address space), and permission errors from the user-namespace filter path (kernel/nstree.c, body).

## Flags and constants

LISTNS_CURRENT_USER (0xffffffffffffffff) -- request the caller's owning user namespace (include/uapi/linux/nsfs.h). ns_type bits mirror the CLONE_NEW* values (uapi nsfs.h).

## Security and notes

Visibility is the security story: a user namespace sees namespaces owned by it (and their descendants), which is what makes listns() safe to expose unprivileged -- the same visibility rule /proc/[pid]/ns uses, minus the procfs dependency. Namespaced container runtimes and supervisors get a stable enumeration primitive; interview angle: this turns "which namespaces exist" from a heuristics walk into a syscall, the way listmount(2) did for mounts. This page is source-limited: kernel/nstree.c and include/uapi/linux/nsfs.h (master, fall 2026) are the only reachable sources; the sibling statns(2) shares the ns_id_req structure per the header comment. Cross-reference: [setns](setns.md), [unshare](unshare.md), [clone](../process/clone.md), [statmount](statmount.md).

## References

- Kernel source: kernel/nstree.c (SYSCALL_DEFINE4(listns), torvalds/linux master, fetched 2026-10-17)
- UAPI: include/uapi/linux/nsfs.h (struct ns_id_req, LISTNS_CURRENT_USER, ns_type bits)
- asm-generic numbering: scripts/syscall.tbl line `470 common listns sys_listns`
- worklog: no glibc wrapper symbol (nm -D, glibc 2.41)
