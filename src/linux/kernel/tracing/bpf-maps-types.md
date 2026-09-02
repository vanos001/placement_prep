# BPF Maps — Types, Operations, and Internals

## What a BPF Map Is

A BPF map is the kernel's answer to a question that an in-kernel VM
immediately raises: *where does the program keep its state between calls?*
The BPF instruction set has no global variables (other than read-only
`.rodata` and `.bss` maps), so any per-event aggregation, lookup table, or
scratch buffer has to live in a *map*. Maps are first-class kernel objects:
they have a 32-bit `id` (visible in `/proc/self/fdinfo` after `bpf(BPF_MAP_CREATE)`
returns a fd), a refcount, optional name, and a security label (SELinux,
landlock). They survive until the last fd is closed *or* they are pinned in
the bpf filesystem.

The UAPI entry point is the `bpf(2)` syscall, and the type dispatch lives in
`kernel/bpf/syscall.c` (`map_lookup_elem`, `map_update_elem`,
`map_delete_elem`, `map_push_elem`, `map_pop_elem`, `map_peek_elem`,
`map_lookup_and_delete_elem`). The actual map implementations live in
`kernel/bpf/*.c` — `hashtab.c`, `arraymap.c`, `lpm_trie.c`, `ringbuf.c`,
`cpumap.c`, `devmap.c`, `sockmap.c`, `queue_stack_maps.c`,
`bloom_filter_map.c`, `lru_map.c`, `arena.c` and friends.

## The Map Lifecycle

```
   bpf(BPF_MAP_CREATE, attr, sizeof(attr))   --- kernel
        |                                       allocates struct bpf_map *
        |                                       calls .map_alloc_check(),
        |                                       .map_alloc(), .map_meta_equal?
        v
   fd = ...                                  (returned to userspace)
        |
        |--- bpf(BPF_MAP_LOOKUP_ELEM)  --- .map_lookup_elem
        |--- bpf(BPF_MAP_UPDATE_ELEM)  --- .map_update_elem
        |--- bpf(BPF_MAP_DELETE_ELEM)  --- .map_delete_elem
        |--- bpf(BPF_MAP_PUSH_ELEM)    --- queue/stack/bloom types only
        |--- bpf(BPF_MAP_LOOKUP_AND_DELETE_ELEM)
        |
        |--- bpf_obj_pin("foo")    -- install in /sys/fs/bpf/foo
        |--- bpf_obj_get("foo")    -- reopen from path
        v
   close(fd)   -> refcount dec; if zero, .map_free() called.
```

The same lifecycle applies to maps created implicitly by libbpf when it
parses `SEC(".maps")` declarations; libbpf issues `BPF_MAP_CREATE` for each
one before `BPF_PROG_LOAD`.

## Creating a Map: The UAPI

```c
union bpf_attr attr = {
    .map_type    = BPF_MAP_TYPE_HASH,
    .key_size    = sizeof(__u32),
    .value_size  = sizeof(__u64),
    .max_entries = 1024,
    .map_flags   = BPF_F_NO_PREALLOC,      /* optional */
};
int fd = bpf(BPF_MAP_CREATE, &attr, sizeof(attr));
```

The four shape attributes (`map_type`, `key_size`, `value_size`,
`max_entries`) are immutable for the life of the map. Some types add more
fields — `BPF_MAP_TYPE_LPM_TRIE` uses the leading 32 bits of the key as a
prefix length, `BPF_MAP_TYPE_RINGBUF` ignores `key/value` and uses only
`max_entries` as the buffer size in bytes, `BPF_MAP_TYPE_ARENA` adds
`map_extra` for the host VA.

## The Map Type Catalogue

The kernel enumerates ~35 distinct map types in
`include/uapi/linux/bpf.h`. Here is the working catalogue, grouped by
purpose.

### Generic key/value stores

| Type | Backing | Lookup | Update | Delete | Notes |
|------|---------|--------|--------|--------|-------|
| `BPF_MAP_TYPE_HASH` | open-addressed hashtable | O(1)+lock | O(1)+lock | O(1)+lock | Default choice for sparse keys. |
| `BPF_MAP_TYPE_ARRAY` | flat `value[]` indexed by `u32` | O(1) | O(1) | **not supported** | All entries preallocated. Good for dense counters. |
| `BPF_MAP_TYPE_PERCPU_HASH` | per-cpu hashtable | O(1) | O(1) | O(1) | Avoids cache-line contention. |
| `BPF_MAP_TYPE_PERCPU_ARRAY` | per-cpu flat array | O(1) | O(1) | n/a | Ideal for hot counters. |
| `BPF_MAP_TYPE_LRU_HASH` | hashtable + per-cpu LRU list | O(1) | O(1) | O(1) | Evicts least-recently-used when full. |
| `BPF_MAP_TYPE_LRU_PERCPU_HASH` | same, per-cpu | O(1) | O(1) | O(1) | Lower contention, weaker LRU. |
| `BPF_MAP_TYPE_LPM_TRIE` | longest-prefix-match trie | O(key_len) | O(key_len) | O(key_len) | For routing tables. Key has `u32 prefixlen` prefix. |

### FIFO / LIFO / Bloom

| Type | Semantics |
|------|-----------|
| `BPF_MAP_TYPE_QUEUE` | FIFO push/pop, lookup unsupported |
| `BPF_MAP_TYPE_STACK` | LIFO push/pop/peek |
| `BPF_MAP_TYPE_BLOOM_FILTER` | Probabilistic membership; no value returned |

### Streaming

| Type | Semantics |
|------|-----------|
| `BPF_MAP_TYPE_RINGBUF` | Single ring buffer, lockless, BTF-typed records, replaces `PERF_EVENT_ARRAY`. |
| `BPF_MAP_TYPE_PERF_EVENT_ARRAY` | Legacy per-CPU perf ring buffer. Still used by older BCC/BCC tools. |

### Network/sockets

| Type | Purpose |
|------|---------|
| `BPF_MAP_TYPE_SOCKMAP` | Maps `sk_buff` to a `struct sock*`; redirect `sendmsg`/`recvmsg`. |
| `BPF_MAP_TYPE_SOCKHASH` | Same as SOCKMAP but uses arbitrary key (not 4-tuple); the SOCKHASH family redirects via `bpf_sk_redirect_hash()` (SOCKMAP's counterpart is `bpf_sk_redirect_map()`). |
| `BPF_MAP_TYPE_REUSEPORT_SOCKARRAY` | SO_REUSEPORT attach points. |
| `BPF_MAP_TYPE_SK_STORAGE` | Per-socket local storage. |
| `BPF_MAP_TYPE_DEVMAP` | Maps ifindex → `struct net_device*`; used by XDP redirect. |
| `BPF_MAP_TYPE_DEVMAP_HASH` | Sparse variant. |
| `BPF_MAP_TYPE_CPUMAP` | Maps CPU# → target CPU for XDP redirect to a different CPU's net stack. |
| `BPF_MAP_TYPE_XSKMAP` | AF_XDP socket maps. |

### Memory management & storage

| Type | Purpose |
|------|---------|
| `BPF_MAP_TYPE_PERCPU_CGROUP_STORAGE` | Per-cgroup counters. |
| `BPF_MAP_TYPE_CGROUP_STORAGE` | Cgroup-local store. |
| `BPF_MAP_TYPE_TASK_STORAGE` | Per-task local storage (used by BPF LSM). |
| `BPF_MAP_TYPE_INODE_STORAGE` | Per-inode local storage. |
| `BPF_MAP_TYPE_STRUCT_OPS` | Maps to a struct of function pointers used by `BPF_STRUCT_OPS`. |
| `BPF_MAP_TYPE_ARENA` (6.x) | Sparse paged VA shared between BPF and userspace (mmap-friendly). |

## Generic Map Operations

The BPF instruction `BPF_LD_MAP_FD` rewrites a load of an `imm` containing a
map fd into a `BPF_PSEUDO_MAP_FD` instruction; the verifier then resolves it
to a `struct bpf_map *` and stores it in `R1` before the helper call.

```c
/* Update a hash entry */
__u32 key = 42;
__u64 val = 0xdeadbeef;
bpf_map_update_elem(&my_hash, &key, &val, BPF_ANY);

/* Lookup with explicit NULL check (verifier requires this) */
__u64 *vp = bpf_map_lookup_elem(&my_hash, &key);
if (!vp)
    return 0;            /* verifier refuses to dereference otherwise */
__u64 cur = *vp;
```

The flags argument to `bpf_map_update_elem`:

| Flag | Meaning |
|------|---------|
| `BPF_ANY`     | Create or replace. |
| `BPF_NOEXIST` | Only create; fail if present. |
| `BPF_EXIST`   | Only replace; fail if absent. |
| `BPF_F_LOCK`  | Acquire the per-element spinlock (requires `BPF_F_LOCK`-aware map). |

## Per-CPU Maps in Practice

The hot path of a BPF counter on a busy host is the cache line containing
the counter. Without per-CPU maps, every CPU has to contend for the same
line on every increment. Per-CPU maps eliminate that contention by giving
each CPU its own copy of the value; the user space aggregator then sums
across CPUs.

```c
struct {
    __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
    __uint(max_entries, 1);
    __type(key,   __u32);
    __type(value, __u64);
} pkts SEC(".maps");

SEC("xdp")
int cnt(struct xdp_md *ctx)
{
    __u32 key = 0;
    __u64 *c = bpf_per_cpu_ptr(&pkts, bpf_get_smp_processor_id());
    /* or, more idiomatically: */
    __u64 *p = bpf_map_lookup_elem(&pkts, &key);
    if (p) __sync_fetch_and_add(p, 1);
    return XDP_PASS;
}
```

Userspace reads the per-CPU values with `bpf(BPF_MAP_LOOKUP_ELEM)` and a
NULLable `next_cpu` cursor; libbpf's `bpf_map_lookup_percpu()` iterates
for you.

```
CPU0 counter = 1 234 567
CPU1 counter = 1 234 001
CPU2 counter = ...
total = sum
```

## LRU Eviction

`LRU_HASH` and `LRU_PERCPU_HASH` evict the least-recently-used entry when
the map reaches `max_entries`. The kernel maintains two lists per LRU
namespace:

```
   +-------------+   +-----------+   +-----------+      <-- "young" list (most recent)
   |  node A     |-->|  node B   |-->|  node C    |
   +-------------+   +-----------+   +-----------+
                            ^
                            | rotate when scanning
                            v
   +-------------+   +-----------+   +-----------+      <-- "old" list
   |  node D     |-->|  node E   |-->|  node F    |
   +-------------+   +-----------+   +-----------+
```

A `lookup`/`update` of an entry in the "old" list promotes it to "young".
When the map is full, the LRU eviction scan starts from the head of the
"old" list, evicting entries until the scan budget is exhausted. The
`PERCPU_HASH` variant keeps the lists per-CPU, which is cheaper but produces
weaker global LRU (entries used heavily on one CPU are never evicted even if
they are cold everywhere else).

Tunable: `map_extra` on LRU maps in newer kernels sets the local cache
size; defaults to ~32 entries per CPU.

## LPM Trie for Routing

```c
struct {
    __uint(type, BPF_MAP_TYPE_LPM_TRIE);
    __uint(max_entries, 65536);
    __uint(key_size,    sizeof(struct bpf_lpm_trie_key_u8) + 4);  /* prefixlen + 4 bytes ipv4 */
    __uint(value_size,  sizeof(__u32));
} routes SEC(".maps");

struct bpf_lpm_trie_key_u8 k = { .prefixlen = 24 };
*(u32 *)k.data = 0xC0A80100;      /* 192.168.1.0/24 */

__u32 *nh = bpf_map_lookup_elem(&routes, &k);   /* longest-prefix match */
```

The trie node format is documented in `include/uapi/linux/lpm.h`. Lookups
walk from the root, descending into child nodes whose prefix matches the
queried key bit-by-bit, and remember the deepest node that fully matched
the key — the LPM result.

## Ring Buffers: BPF_MAP_TYPE_RINGBUF

The classic `PERF_EVENT_ARRAY` had three problems: every per-CPU buffer
wasted a full page (even if you only emitted a few records), userspace had
to poll every CPU, and reservation was costly because it was per-record
with a separate reservation step. Linux 5.8 introduced `BPF_RINGBUF` to fix
all three.

A `BPF_RINGBUF` map has a single buffer shared by all CPUs. The kernel
implements a lockless producer ring using `bpf_ringbuf_reserve()` followed
by a `bpf_ringbuf_submit()` or `bpf_ringbuf_discard()`:

```c
struct evt {
    __u64 ts;
    __u32 pid;
    __u32 len;
    char  comm[16];
};

SEC("kprobe/do_sys_openat2")
int trace_open(struct pt_regs *ctx)
{
    struct evt *e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
    if (!e)
        return 0;                       /* buffer full, drop */
    e->ts  = bpf_ktime_get_ns();
    e->pid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(e->comm, sizeof(e->comm));
    bpf_ringbuf_submit(e, 0);           /* publish */
    return 0;
}
```

The reservation protocol:

```
   +-------------------- ringbuf --------------------+
   |  free  |   REC   REC   REC   |     free         |
   +-------------------------------------------------+
              ^reserve (pos)        ^commit (pos)

   1. reserve:  producer_pos += size  (atomic)
   2. fill    : write payload into reserved slot
   3. submit  : set REC.header.b     = busy_lock -> published
                busy_wait on the consumer side if needed
```

Why ringbuf replaces perf buffer: one buffer, no per-CPU aggregation needed,
lockless, supports busy polling (`BPF_F_NO_WAKEUP`), and lets userspace
`mmap()` the same memory the kernel writes — no copies.

The userspace consumer reads `/sys/kernel/bpf/<map_fd>` is *not* the API;
you use `ring_buffer__new()` from libbpf, which `mmap`s the consumer page
and the data pages and polls with `ring_buffer__poll()`.

## SOCKHASH, DEVMAP, CPUMAP — Program-Aware Maps

These three are "program-aware": they hold kernel objects (`struct sock*`,
`struct net_device*`) and are manipulated not via `bpf_map_update_elem()`
from userspace but via `bpf_sk_redirect_map()`, `bpf_redirect_map()`, and
`bpf_redirect_cpu()` *from inside a BPF program*.

```c
SEC("sk_skb")
int redirect_in(struct __sk_buff *skb)
{
    /* SOCKHASH lookup with the 4-tuple taken from the sk_buff */
    struct { __u32 sip, dip; __u16 sport, dport; } key;
    /* fill key from skb headers... */
    return bpf_sk_redirect_hash(skb, &socks, &key, BPF_F_INGRESS);
}
```

`DEVMAP` is used by XDP for fast redirect to another NIC:

```c
SEC("xdp")
int to_other(struct xdp_md *ctx)
{
    return bpf_redirect_map(&devs, 1, 0);   /* ifindex stored at key=1 */
}
```

`CPUMAP` redirects an XDP frame to a target CPU's net stack, useful for
load-balancing receive paths without per-CPU sk_buff contention.

## Map Pinning and bpffs

The `bpf(2)` syscall fd is process-local: when the loading process exits,
the maps disappear unless something holds them. To make a map persist, pin
it in the BPF filesystem:

```bash
# Mount bpffs (usually done by systemd or your distro)
mount | grep bpf              # /sys/fs/bpf type bpf (...)
# Mount it if missing
mount -t bpf bpf /sys/fs/bpf

# Pin a map (via bpftool)
bpftool map pin id 12 /sys/fs/bpf/my_map

# Reopen later (in another process)
bpftool map show pinned /sys/fs/bpf/my_map
```

In libbpf, declare pinning intent declaratively:

```c
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 4096);
    __type(key,   __u32);
    __type(value, __u64);
    __uint(pinning, LIBBPF_PIN_BY_NAME);   /* auto-pinned to /sys/fs/bpf/<name> */
} persistent SEC(".maps");
```

`LIBBPF_PIN_BY_NAME` causes libbpf to call `bpf_obj_pin()` after
`BPF_MAP_CREATE` and to look for an existing pin (with matching
`key/value/max_entries` and BTF) before creating a new one on subsequent
loads. This is the standard mechanism for *stateful* BPF applications that
must survive a daemon restart.

## Worked Example: Counter with Histogram

A complete program demonstrating PERCPU_ARRAY, HASH and RINGBUF together:

```c
struct { __uint(type, BPF_MAP_TYPE_PERCPU_ARRAY);
         __uint(max_entries, 8);                  /* 8 latency buckets */
         __type(key, __u32); __type(value, __u64); } hist SEC(".maps");

struct { __uint(type, BPF_MAP_TYPE_HASH);
         __uint(max_entries, 1024);
         __type(key, __u32); __type(value, __u64); } start SEC(".maps");

struct evt { __u32 pid; __u64 delta_ns; };
struct { __uint(type, BPF_MAP_TYPE_RINGBUF);
         __uint(max_entries, 1 << 20); } events SEC(".maps");

SEC("kprobe/vfs_read")
int on_entry(struct pt_regs *ctx)
{
    __u32 pid = bpf_get_current_pid_tgid() >> 32;
    __u64 t   = bpf_ktime_get_ns();
    bpf_map_update_elem(&start, &pid, &t, BPF_ANY);
    return 0;
}

SEC("kretprobe/vfs_read")
int on_return(struct pt_regs *ctx)
{
    __u32 pid = bpf_get_current_pid_tgid() >> 32;
    __u64 *t0 = bpf_map_lookup_elem(&start, &pid);
    if (!t0) return 0;
    __u64 delta = bpf_ktime_get_ns() - *t0;
    bpf_map_delete_elem(&start, &pid);

    __u32 bucket = delta < 1000        ? 0 :
                   delta < 10000       ? 1 :
                   delta < 100000      ? 2 :
                   delta < 1000000     ? 3 :
                   delta < 10000000    ? 4 :
                   delta < 100000000   ? 5 :
                   delta < 1000000000  ? 6 : 7;
    __u64 *c = bpf_map_lookup_elem(&hist, &bucket);
    if (c) __sync_fetch_and_add(c, 1);

    struct evt *e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
    if (e) { e->pid = pid; e->delta_ns = delta; bpf_ringbuf_submit(e, 0); }
    return 0;
}
```

Aggregator userspace reads `hist` per-CPU, sums, and prints the histogram,
and `events` via `ring_buffer__poll()`.

## References

- Linux kernel docs, "BPF maps" — https://docs.kernel.org/bpf/map_generic.html
- Linux kernel docs, "BPF_MAP_TYPE_RINGBUF" — https://docs.kernel.org/bpf/map_ringbuf.html
- Linux kernel docs, BPF map type list — https://docs.kernel.org/userspace-api/ebpf/maps.html
- `bpf(2)` man page ( Maintainers: Alexei Starovoitov, Daniel Borkmann) — https://man7.org/linux/man-pages/man2/bpf.2.html
- libbpf map API documentation — https://libbpf.readthedocs.io/en/latest/
- `include/uapi/linux/bpf.h` (Linux 6.x) — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/uapi/linux/bpf.h
- `kernel/bpf/syscall.c` (map_create dispatch) — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/syscall.c
- `kernel/bpf/hashtab.c` (HASH/LRU/PERCPU) — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/hashtab.c
- `kernel/bpf/ringbuf.c` — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/ringbuf.c
- LWN: "BPF ring buffer" (Jonathan Corbet, 2020) — https://lwn.net/Articles/820005/
- LWN: "BPF: A general-purpose in-kernel virtual machine" — https://lwn.net/Articles/740157/
- Cilium "BPF maps" reference — https://docs.cilium.io/en/stable/bpf/
- ebpf.io project overview — https://ebpf.io/
- BPF Cookbook (libbpf) — https://github.com/libbpf/libbpf-bootstrap
