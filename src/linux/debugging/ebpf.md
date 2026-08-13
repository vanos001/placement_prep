# eBPF — Extended Berkeley Packet Filter

## Introduction

eBPF (extended Berkeley Packet Filter) is a revolutionary technology in the Linux kernel
that allows safe, efficient, and programmable execution of code within the kernel space
without modifying the kernel source or loading kernel modules. Originally designed for
packet filtering, eBPF has evolved into a general-purpose execution engine that powers
networking, security, tracing, and observability tools.

eBPF programs are compiled into a special bytecode, verified by the kernel's eBPF
verifier for safety, and JIT-compiled to native machine code for performance. This
makes eBPF both safe (no kernel crashes from buggy programs) and fast (near-native
execution speed).

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        User Space                              │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │   bcc tools  │  │   bpftrace   │  │ Custom BPF programs│  │
│  │ (Python API) │  │ (DSL)        │  │ (C + libbpf)       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬─────────────┘  │
└─────────┼─────────────────┼─────────────────┼─────────────────┘
          │                 │                 │
   ┌──────▼─────────────────▼─────────────────▼─────────────────┐
   │                    bpf() System Call                         │
   │              (load, attach, interact)                        │
   └──────────────────────────┬──────────────────────────────────┘
                              │
   ┌──────────────────────────▼──────────────────────────────────┐
   │                     Kernel Space                             │
   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐ │
   │  │  eBPF        │  │  eBPF        │  │  eBPF Maps       │ │
   │  │  Verifier    │  │  JIT Compiler│  │  (key-value store)│ │
   │  │              │  │              │  │                  │ │
   │  └──────────────┘  └──────────────┘  └──────────────────┘ │
   │                                                             │
   │  ┌──────────────────────────────────────────────────────┐  │
   │  │              Attachment Points                         │  │
   │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │  │
   │  │  │kprobes   │ │tracepoints│ │XDP       │ │tc        │ │  │
   │  │  │uprobes   │ │perf events│ │socket    │ │cgroup    │ │  │
   │  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘  │  │
   │  └──────────────────────────────────────────────────────┘  │
   └─────────────────────────────────────────────────────────────┘
```

## BPF Programs

### Program Types

eBPF programs are attached to different hooks in the kernel. The program type
determines what the program can do and where it can be attached. From
`docs.kernel.org/bpf/prog_type.html`, the kernel defines these program types:

| Program Type | Attachment Point | Use Case |
|-------------|-----------------|----------|
| `BPF_PROG_TYPE_SOCKET_FILTER` | Sockets | Packet filtering (classic BPF successor) |
| `BPF_PROG_TYPE_KPROBE` | Kernel functions | Kernel tracing via kprobes |
| `BPF_PROG_TYPE_SCHED_CLS` | Traffic control (TC) | Packet classification and mangling |
| `BPF_PROG_TYPE_SCHED_ACT` | Traffic control (TC) | Packet actions |
| `BPF_PROG_TYPE_XDP` | Network driver RX | High-performance packet processing (before sk_buff) |
| `BPF_PROG_TYPE_TRACEPOINT` | Kernel tracepoints | Static event tracing |
| `BPF_PROG_TYPE_PERF_EVENT` | Perf events | Performance monitoring and sampling |
| `BPF_PROG_TYPE_CGROUP_SKB` | Cgroups | Container network policy (ingress/egress) |
| `BPF_PROG_TYPE_CGROUP_SOCK` | Cgroups | Socket-level cgroup policy |
| `BPF_PROG_TYPE_LSM` | Linux Security Module | MAC security policies (BPF LSM) |
| `BPF_PROG_TYPE_SK_SKB` | Sockets | Socket-level packet forwarding (sockmap) |
| `BPF_PROG_TYPE_SK_MSG` | Sockets | sendmsg/sendfile redirection |
| `BPF_PROG_TYPE_LWT_*` | Lightweight tunnels | MPLS/IP tunnel encapsulation |
| `BPF_PROG_TYPE_FLOW_DISSECTOR` | Networking | Packet header parsing |
| `BPF_PROG_TYPE_SYSCALL` | System calls | Syscall argument filtering |
| `BPF_PROG_TYPE_STRUCT_OPS` | Kernel struct_ops | Replacing kernel function callbacks |
| `BPF_PROG_TYPE_NETFILTER` | Netfilter hooks | Packet filtering with nftables integration |

### Program Type Categories

**Networking programs** (`XDP`, `TC`, `SK_SKB`, `LWT_*`):
- Can inspect and modify packet data
- Access to `skb->data` and `skb->data_end` for direct packet access
- Helpers: `bpf_skb_load_bytes()`, `bpf_skb_store_bytes()`, `bpf_redirect()`
- XDP runs before `sk_buff` allocation — highest performance

**Tracing programs** (`KPROBE`, `TRACEPOINT`, `PERF_EVENT`, `RAW_TRACEPOINT`):
- Can access kernel memory via `bpf_probe_read()`
- Access to process context (`bpf_get_current_pid_tgid()`, `bpf_get_current_comm()`)
- Can use `bpf_trace_printk()` for debugging
- Cannot modify packet data

**Cgroup programs** (`CGROUP_SKB`, `CGROUP_SOCK`, `CGROUP_SOCK_ADDR`):
- Attach to cgroups for container network policy
- Can allow/deny connections and packets
- Used by Cilium, Calico for container networking

**Security programs** (`LSM`):
- Attach to LSM hooks for mandatory access control
- Can deny operations by returning 0
- Alternative to traditional LSM modules (AppArmor, SELinux)

**Struct ops programs** (`STRUCT_OPS`):
- Replace function pointers in kernel structs (e.g., TCP congestion control)
- Allow implementing kernel subsystems in BPF
- Used for custom TCP congestion algorithms, scheduler policies

### Writing BPF Programs

BPF programs are written in C (restricted subset) and compiled to BPF bytecode:

```c
// simple_tracepoint.c — Trace sys_enter_openat
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

// BPF map to store event counts
struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, __u64);
} event_count SEC(".maps");

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx) {
    __u32 key = 0;
    __u64 *value;

    value = bpf_map_lookup_elem(&event_count, &key);
    if (value)
        __sync_fetch_and_add(value, 1);

    return 0;
}

char LICENSE[] SEC("license") = "GPL";
```

Compile and load:
```bash
# Compile BPF program
clang -O2 -target bpf -g -c simple_tracepoint.c -o simple_tracepoint.o

# Load using bpftool
sudo bpftool prog load simple_tracepoint.o /sys/fs/bpf/simple_tracepoint

# Or use libbpf-based loader
```

### BPF Verifier

The eBPF verifier ensures program safety before loading:

```
┌──────────────────────────────────────────────┐
│              BPF Verifier                     │
│                                              │
│  1. Control flow analysis                    │
│     - No unreachable code                    │
│     - No infinite loops                      │
│     - All paths terminate                    │
│                                              │
│  2. Memory safety                            │
│     - All memory accesses are bounds-checked │
│     - No out-of-bounds reads/writes          │
│     - Stack depth ≤ 512 bytes                │
│                                              │
│  3. Type safety                              │
│     - Pointer types verified                 │
│     - No unsafe casts                        │
│     - Map access validated                   │
│                                              │
│  4. Program limits                           │
│     - Max 1M instructions (complexity)       │
│     - Max 512 bytes stack                    │
│     - Max 64 nested calls                    │
└──────────────────────────────────────────────┘
```

## BPF Maps

Maps are the primary data structure for BPF programs. They are key-value stores
accessible from both BPF programs and user space.

### Map Types (Complete Reference)

From the kernel documentation at `docs.kernel.org/bpf/map.html`, the following map types are available:

| Type | Description | Use Case |
|------|-------------|----------|
| `BPF_MAP_TYPE_HASH` | Hash table | General key-value lookup |
| `BPF_MAP_TYPE_ARRAY` | Fixed-size array | Index-based access, per-CPU stats |
| `BPF_MAP_TYPE_PROG_ARRAY` | BPF programs | Tail calls between programs |
| `BPF_MAP_TYPE_PERF_EVENT_ARRAY` | Perf events | Per-CPU event streaming |
| `BPF_MAP_TYPE_PERCPU_HASH` | Per-CPU hash table | Lock-free counters |
| `BPF_MAP_TYPE_PERCPU_ARRAY` | Per-CPU array | Per-CPU statistics |
| `BPF_MAP_TYPE_STACK_TRACE` | Stack traces | Profiling |
| `BPF_MAP_TYPE_CGROUP_ARRAY` | Cgroup refs | Cgroup-based filtering |
| `BPF_MAP_TYPE_LRU_HASH` | LRU hash table | Bounded-size cache |
| `BPF_MAP_TYPE_LRU_PERCPU_HASH` | Per-CPU LRU hash | Per-CPU bounded cache |
| `BPF_MAP_TYPE_LPM_TRIE` | Longest prefix match | IP routing/CIDR lookup |
| `BPF_MAP_TYPE_ARRAY_OF_MAPS` | Map-of-maps (array) | Map switching at runtime |
| `BPF_MAP_TYPE_HASH_OF_MAPS` | Map-of-maps (hash) | Nested data structures |
| `BPF_MAP_TYPE_DEVMAP` | Device map | XDP redirect targets |
| `BPF_MAP_TYPE_SOCKMAP` | Socket map | Socket redirection |
| `BPF_MAP_TYPE_CPUMAP` | CPU map | XDP CPU redirect |
| `BPF_MAP_TYPE_XSKMAP` | AF_XDP socket map | XDP to userspace |
| `BPF_MAP_TYPE_SOCKHASH` | Socket hash | Socket hash-based routing |
| `BPF_MAP_TYPE_RINGBUF` | Ring buffer | High-throughput event streaming |
| `BPF_MAP_TYPE_INODE_STORAGE` | Inode storage | Per-inode BPF local storage |
| `BPF_MAP_TYPE_TASK_STORAGE` | Task storage | Per-task BPF local storage |
| `BPF_MAP_TYPE_BLOOM_FILTER` | Bloom filter | Probabilistic membership test |

#### Key Map Type Details

**`BPF_MAP_TYPE_HASH`** — The workhorse map. O(1) average lookup. Supports `BPF_ANY`, `BPF_NOEXIST`, `BPF_EXIST` flags for update.

**`BPF_MAP_TYPE_ARRAY`** — Fixed size at creation. Elements are always present (zero-initialized). No delete operation. O(1) index access.

**`BPF_MAP_TYPE_RINGBUF`** — Replaced `BPF_MAP_TYPE_PERF_EVENT_ARRAY` for most event streaming. Multi-producer, single-consumer. Reserves/submit model avoids copies. `bpf_ringbuf_output()` can also be used.

**`BPF_MAP_TYPE_LPM_TRIE`** — Stores IP prefixes. `bpf_map_lookup_elem()` returns the longest matching prefix. Used for CIDR-based routing in Cilium/Calico.

**`BPF_MAP_TYPE_DEVMAP`** — Maps ifindex to `struct bpf_dentry`. Used with `bpf_redirect_map()` for XDP multi-redirect.

**`BPF_MAP_TYPE_SOCKMAP`** — Stores socket references. Enables `bpf_msg_redirect_hash()` and `bpf_sk_redirect_map()` for kernel-level socket forwarding without touching userspace.

### Map Operations

| Type | Description | Use Case |
|------|-------------|----------|
| `BPF_MAP_TYPE_HASH` | Hash table | General key-value lookup |
| `BPF_MAP_TYPE_ARRAY` | Fixed-size array | Index-based access |
| `BPF_MAP_TYPE_PERCPU_HASH` | Per-CPU hash table | Lock-free counters |
| `BPF_MAP_TYPE_PERCPU_ARRAY` | Per-CPU array | Per-CPU statistics |
| `BPF_MAP_TYPE_LRU_HASH` | LRU hash table | Bounded-size cache |
| `BPF_MAP_TYPE_RINGBUF` | Ring buffer | High-throughput event streaming |
| `BPF_MAP_TYPE_STACK_TRACE` | Stack traces | Profiling |
| `BPF_MAP_TYPE_PROG_ARRAY` | BPF programs | Tail calls |
| `BPF_MAP_TYPE_HASH_OF_MAPS` | Map of maps | Nested data structures |

### Map Operations

```c
// Define a map
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, __u32);           // PID
    __type(value, __u64);         // count
} pid_count SEC(".maps");

// Lookup
__u64 *val = bpf_map_lookup_elem(&pid_count, &pid);
if (val) {
    __sync_fetch_and_add(val, 1);
} else {
    __u64 init = 1;
    bpf_map_update_elem(&pid_count, &pid, &init, BPF_ANY);
}

// Delete
bpf_map_delete_elem(&pid_count, &pid);

// Iterate (from user space)
__u32 key, next_key;
while (bpf_map_get_next_key(fd, &key, &next_key) == 0) {
    // process next_key
    key = next_key;
}
```

### Ring Buffer (Preferred for Events)

```c
struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);  // 256KB
} events SEC(".maps");

struct event {
    __u32 pid;
    char comm[16];
    char filename[256];
};

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx) {
    struct event *e;

    // Reserve space in ring buffer
    e = bpf_ringbuf_reserve(&events, sizeof(struct event), 0);
    if (!e)
        return 0;

    // Fill event data
    e->pid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    bpf_probe_read_user_str(&e->filename, sizeof(e->filename),
                            (void *)ctx->args[1]);

    // Submit to user space
    bpf_ringbuf_submit(e, 0);
    return 0;
}
```

## BCC — BPF Compiler Collection

BCC provides a Python (and Lua) frontend for writing BPF programs. It compiles
BPF C code on the fly and provides convenient APIs.

### Installation

```bash
# Ubuntu/Debian
sudo apt install bpfcc-tools python3-bpfcc

# RHEL/Fedora
sudo dnf install bcc-tools bcc

# From source
git clone https://github.com/iovisor/bcc.git
mkdir bcc/build; cd bcc/build
cmake ..
make && sudo make install
```

### BCC Python Example

```python
#!/usr/bin/env python3
# opensnoop.py — Trace open() syscalls
from bcc import BPF

# BPF program
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct data_t {
    u32 pid;
    u64 ts;
    char comm[TASK_COMM_LEN];
    char fname[256];
};

BPF_PERF_OUTPUT(events);

TRACEPOINT_PROBE(syscalls, sys_enter_openat) {
    struct data_t data = {};

    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.ts = bpf_ktime_get_ns();
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    bpf_probe_read_user_str(&data.fname, sizeof(data.fname),
                            args->filename);

    events.perf_submit(args, &data, sizeof(data));
    return 0;
}
"""

# Load BPF program
b = BPF(text=bpf_text)

# Process events
def print_event(cpu, data, size):
    event = b["events"].event(data)
    print(f"{event.comm.decode():16s} {event.pid:6d} {event.fname.decode()}")

b["events"].open_perf_buffer(print_event)

print(f"{'COMM':16s} {'PID':>6s} FILENAME")
while True:
    b.perf_buffer_poll()
```

### BCC Tools

BCC ships with dozens of ready-to-use tools:

```bash
# List all BCC tools
ls /usr/share/bcc/tools/

# Tracing tools
sudo opensnoop              # Trace open() syscalls
sudo execsnoop              # Trace new processes
sudo biolatency             # Block I/O latency histogram
sudo cachestat              # Page cache hit/miss stats
sudo tcpconnect             # Trace TCP connections
sudo tcplife                # Trace TCP sessions with duration
sudo profile                # CPU profiling (sampling)
sudo funccount              # Count kernel function calls
sudo funclatency            # Function latency histogram
sudo trace                  # Trace arbitrary kernel functions
sudo argdist               # Distribution of function arguments
sudo drsnoop               # Trace direct reclaim events
sudo oomkill               # Trace OOM kills
sudo memleak               # Detect memory leaks
sudo hardirqs              # Hard interrupt time
sudo softirqs              # Soft interrupt time
sudo runqlat               # Run queue latency
sudo cpudist               # On-CPU time distribution
```

### Example: Using BCC Tools

```bash
# Trace all open() calls
$ sudo opensnoop
PID    COMM               FD ERR PATH
1234   bash                3   0 /etc/passwd
5678   cat                 3   0 /etc/hostname

# Block I/O latency histogram
$ sudo biolatency -D
Tracing block device I/O... Hit Ctrl-C to end.

disk = sda
     usecs          : count    distribution
         0 -> 1     : 0       |                                      |
         2 -> 3     : 0       |                                      |
         4 -> 7     : 3       |*                                     |
         8 -> 15    : 12      |*****                                 |
        16 -> 31    : 45      |********************                  |
        32 -> 63    : 89      |****************************************|
        64 -> 127   : 34      |***************                       |
       128 -> 255   : 8       |***                                   |
       256 -> 511   : 2       |*                                     |

# CPU profiling
$ sudo profile -F 99
Sampling at 99 Hertz of all threads by user + kernel stack... Hit Ctrl-C to end.

    compute_matrix
    main
    __libc_start_main
    [unknown]
    -                myprogram
        45

    memcpy_avx_unaligned_erms
    compute_matrix
    main
    __libc_start_main
    -                myprogram
        30
```

## bpftrace — High-Level Tracing Language

bpftrace provides a DTrace-like language for writing eBPF programs concisely.

### Installation

```bash
# Ubuntu/Debian
sudo apt install bpftrace

# RHEL/Fedora
sudo dnf install bpftrace

# Arch
sudo pacman -S bpftrace
```

### One-Liners

```bash
# Trace open() syscalls
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# Count syscalls by process
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'

# Histogram of read() bytes
bpftrace -e 'tracepoint:syscalls:sys_exit_read /args->ret > 0/ { @bytes = hist(args->ret); }'

# Trace process creation
bpftrace -e 'tracepoint:sched:sched_process_exec { printf("exec: %s (pid=%d)\n", comm, pid); }'

# Count function calls
bpftrace -e 'kprobe:do_sys_open { @[comm] = count(); }'

# Trace disk I/O latency
bpftrace -e 'tracepoint:block:block_rq_issue { @start[args->dev] = nsecs; } tracepoint:block:block_rq_complete /@start[args->dev]/ { @usecs = hist((nsecs - @start[args->dev]) / 1000); delete(@start[args->dev]); }'

# Trace TCP connections
bpftrace -e 'kprobe:tcp_connect { printf("connect: %s -> %d\n", comm, ((struct sock *)arg0)->__sk_common.skc_dport); }'

# Profile CPU stack traces
bpftrace -e 'profile:hz:99 { @[kstack] = count(); }'
```

### bpftrace Programs

```bt
#!/usr/bin/env bpftrace
// latency.bt — Measure syscall latency

tracepoint:raw_syscalls:sys_enter {
    @start[tid] = nsecs;
}

tracepoint:raw_syscalls:sys_exit /@start[tid]/ {
    $latency = (nsecs - @start[tid]) / 1000;
    @us = hist($latency);
    @total_us = sum($latency);
    @count = count();
    delete(@start[tid]);
}

END {
    printf("\nTotal syscalls: ");
    print(@count);
    printf("\nTotal latency (us): ");
    print(@total_us);
    printf("\nLatency histogram (us):\n");
    print(@us);
}
```

```bash
chmod +x latency.bt
sudo ./latency.bt
```

### bpftrace Language Reference

```
Probe types:
  kprobe:function          — Kernel function entry
  kretprobe:function       — Kernel function return
  uprobe:path:function     — User function entry
  uretprobe:path:function  — User function return
  tracepoint:category:name — Kernel tracepoint
  profile:hz:99            — Timed sampling
  interval:s:1             — Periodic output
  software:event:count     — Software events
  hardware:event:count     — Hardware events

Built-in variables:
  pid, tid                 — Process/thread ID
  comm                     — Process name
  nsecs                    — Nanosecond timestamp
  kstack, ustack           — Kernel/user stack trace
  arg0-arg9                — Function arguments
  retval                   — Return value
  ctx                      — Raw context

Map functions:
  @name = count()          — Count events
  @name = sum(x)           — Sum values
  @name = hist(x)          — Histogram
  @name = lhist(x,min,max,step) — Linear histogram
  @name = min(x)           — Minimum
  @name = max(x)           — Maximum
  @name = avg(x)           — Average
  @name = stats(x)         — Statistics (count, avg, total)
```

## XDP — eXpress Data Path

XDP is the lowest-level programmable hook in the Linux networking stack. It processes
packets before the kernel allocates an `sk_buff`, enabling line-rate packet processing.

### XDP Architecture

```
┌────────────────────────────────────────────────┐
│                 Network Stack                    │
│                                                 │
│  ┌──────────┐                                   │
│  │   XDP    │ ← Earliest hook point             │
│  │  Program │   (before sk_buff allocation)     │
│  └────┬─────┘                                   │
│       │ Actions:                                │
│       │  XDP_PASS    → continue to stack        │
│       │  XDP_DROP    → drop packet              │
│       │  XDP_TX      → bounce back on same NIC  │
│       │  XDP_REDIRECT→ redirect to another NIC  │
│       │  XDP_ABORTED → error (drop + trace)     │
│       ▼                                         │
│  ┌──────────┐                                   │
│  │ sk_buff  │ ← Normal kernel networking        │
│  │ allocation│                                   │
│  └──────────┘                                   │
└────────────────────────────────────────────────┘
```

### XDP Program Example

```c
// xdp_drop.c — Drop packets from specific IP
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <arpa/inet.h>

SEC("xdp")
int xdp_drop_prog(struct xdp_md *ctx) {
    void *data = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return XDP_PASS;

    if (eth->h_proto != htons(ETH_P_IP))
        return XDP_PASS;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return XDP_PASS;

    // Drop packets from 10.0.0.1
    if (ip->saddr == htonl(0x0A000001))
        return XDP_DROP;

    return XDP_PASS;
}

char _license[] SEC("license") = "GPL";
```

```bash
# Compile
clang -O2 -target bpf -g -c xdp_drop.c -o xdp_drop.o

# Load on interface
sudo ip link set dev eth0 xdp obj xdp_drop.o sec xdp

# Or using bpftool
sudo bpftool net attach xdp id 123 dev eth0

# Remove
sudo ip link set dev eth0 xdp off
```

## Tracepoints and kprobes with BPF

### Tracepoint Programs

```c
// tracepoint_example.c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

struct event {
    __u32 pid;
    char comm[16];
    char filename[256];
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} events SEC(".maps");

SEC("tracepoint/syscalls/sys_enter_openat")
int handle_openat(struct trace_event_raw_sys_enter *ctx) {
    struct event *e;

    e = bpf_ringbuf_reserve(&events, sizeof(*e), 0);
    if (!e)
        return 0;

    e->pid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(e->comm, sizeof(e->comm));

    const char *filename = (const char *)ctx->args[1];
    bpf_probe_read_user_str(e->filename, sizeof(e->filename), filename);

    bpf_ringbuf_submit(e, 0);
    return 0;
}
```

### kprobe Programs

```c
// kprobe_example.c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10240);
    __type(key, __u32);
    __type(value, __u64);
} start SEC(".maps");

SEC("kprobe/do_sys_openat2")
int BPF_KPROBE(do_sys_openat2) {
    u64 ts = bpf_ktime_get_ns();
    u32 pid = bpf_get_current_pid_tgid() >> 32;

    bpf_map_update_elem(&start, &pid, &ts, BPF_ANY);
    return 0;
}

SEC("kretprobe/do_sys_openat2")
int BPF_KRETPROBE(do_sys_openat2_ret) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 *tsp = bpf_map_lookup_elem(&start, &pid);
    if (!tsp)
        return 0;

    u64 delta = bpf_ktime_get_ns() - *tsp;
    bpf_map_delete_elem(&start, &pid);

    // Log latency (in a real tool, use a histogram map)
    bpf_printk("open latency: %llu ns\n", delta);
    return 0;
}
```

## libbpf — The Modern BPF Library

From the [kernel libbpf documentation](https://docs.kernel.org/bpf/libbpf/libbpf_overview.html),
libbpf is a C-based library containing a BPF loader that takes compiled BPF object files and
prepares and loads them into the Linux kernel. It takes the heavy lifting of loading, verifying,
and attaching BPF programs to various kernel hooks, allowing BPF application developers to focus
only on BPF program correctness and performance.

### Key Features

- **High-level and low-level APIs** for user space programs to interact with BPF programs.
  Low-level APIs wrap all bpf() syscall functionality for fine-grained control.
- **BPF object skeleton** (generated by `bpftool`) — simplifies accessing global variables
  and working with BPF programs from user space.
- **BPF-side APIs** — BPF helper definitions, BPF maps support, and tracing helpers.
- **BPF CO-RE** (Compile Once – Run Everywhere) — enables portable BPF programs that
  run across different kernel versions without modification.

### BPF App Lifecycle

libbpf manages the BPF application lifecycle through four phases:

1. **Open phase** — `bpf_object__open()` parses the BPF object file, discovers maps,
   programs, and global variables. User space can adjust program types and set initial
   global variable values before loading.

2. **Load phase** — `bpf_object__load()` creates BPF maps, resolves relocations,
   verifies and loads programs into the kernel. No program executes yet — this is
   the last chance to set up initial map state without racing with BPF code.

3. **Attach phase** — BPF programs are attached to hooks (tracepoints, kprobes,
   cgroup hooks, network pipeline, etc.) and begin performing useful work.

4. **Tear down phase** — `bpf_object__destroy()` detaches programs, unloads them,
   destroys maps, and frees all resources.

### BPF Object Skeleton

The skeleton (`.skel.h` file generated by `bpftool gen skeleton`) is the recommended
way to work with BPF programs. It provides:

- `xxx__open()` / `xxx__load()` / `xxx__attach()` / `xxx__destroy()` — lifecycle functions
- Direct struct access to all maps and programs (no string-based lookups)
- Memory-mapped global variables accessible from user space
- Embedded bytecode — no separate `.o` file to deploy

```bash
# Generate skeleton
clang -O2 -target bpf -g -c my_prog.c -o my_prog.o
bpftool gen skeleton my_prog.o > my_prog.skel.h
```

### libbpf Logging

By default, libbpf logs to stderr. Control verbosity via:
- Environment variable: `LIBBPF_LOG_LEVEL=warn|info|debug`
- Programmatic: `libbpf_set_print()` for a custom log callback

### libbpf and Rust

For Rust BPF applications, use [Libbpf-rs](https://github.com/libbpf/libbpf-rs) which
wraps libbpf in Rust-idiomatic interfaces and provides a cargo plugin for BPF compilation
and skeleton generation. Note: BPF programs themselves must still be written in C.

### CO-RE (Compile Once, Run Everywhere)

```c
// co_re_example.c — Portable kernel data access
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>

SEC("tp/task/task_rename")
int handle_task_rename(struct trace_event_raw_task_rename *ctx) {
    struct task_struct *task = (void *)bpf_get_current_task();

    // CO-RE: field access is resolved at load time
    int pid = BPF_CORE_READ(task, pid);
    int tgid = BPF_CORE_READ(task, tgid);
    char comm[16];
    BPF_CORE_READ_STR_INTO(&comm, task, comm);

    bpf_printk("rename: pid=%d tgid=%d comm=%s\n", pid, tgid, comm);
    return 0;
}
```

### libbpf Skeleton

```c
// main.c — Using generated skeleton
#include "my_prog.skel.h"

int main() {
    struct my_prog *skel;

    skel = my_prog__open();
    my_prog__load(skel);
    my_prog__attach(skel);

    // Read from maps
    while (1) {
        sleep(1);
        __u32 key = 0;
        __u64 value;
        bpf_map__lookup_elem(skel->maps.event_count, &key,
                            sizeof(key), &value, sizeof(value), 0);
        printf("Count: %lu\n", value);
    }

    my_prog__destroy(skel);
    return 0;
}
```

```bash
# Build with libbpf
clang -O2 -target bpf -g -c my_prog.c -o my_prog.o
bpftool gen skeleton my_prog.o > my_prog.skel.h
clang -o main main.c -lbpf -lelf -lz
```

## bpftool — BPF Inspection Tool

```bash
# List loaded BPF programs
sudo bpftool prog list

# Show program details
sudo bpftool prog show id 123

# Dump BPF program instructions
sudo bpftool prog dump xlated id 123

# Dump JIT-compiled code
sudo bpftool prog dump jited id 123

# List BPF maps
sudo bpftool map list

# Dump map contents
sudo bpftool map dump id 456

# Pin a program
sudo bpftool prog load my_prog.o /sys/fs/bpf/my_prog

# Attach to XDP
sudo bpftool net attach xdp id 123 dev eth0

# List BPF links
sudo bpftool link list
```

## BPF CO-RE and libbpf-bootstrap

```bash
# Clone libbpf-bootstrap
git clone https://github.com/libbpf/libbpf-bootstrap.git
cd libbpf-bootstrap

# Build minimal example
make -C examples/c minimal

# Build with custom program
# Edit examples/c/minimal.bpf.c and examples/c/minimal.c
make -C examples/c minimal
```

## Best Practices

1. **Use ring buffers over perf buffers** — better performance and multi-producer support
2. **Use CO-RE for portability** — avoid writing version-specific code
3. **Keep BPF programs small** — large programs are harder to verify and may fail
4. **Use bpftrace for quick investigations** — it's faster than writing full BPF programs
5. **Use BCC tools as a starting point** — then customize with libbpf for production
6. **Test with bpftool** — verify programs load and maps are correct
7. **Use `bpf_printk` for debugging** — output goes to `/sys/kernel/debug/tracing/trace_pipe`
8. **Handle map errors** — always check return values from map operations

## BPF Standardization (IETF)

From the kernel documentation at `docs.kernel.org/bpf/standardization/index.html`:

The BPF standardization effort is being pursued through the **IETF BPF Working Group**. The goal is to make BPF a cross-platform, standardized technology. The IETF working group is defining:

- **BPF Instruction Set Architecture (ISA)**: A formal specification of the BPF instruction set, making it possible for non-Linux implementations to be BPF-compatible.
- **BPF ABI Recommended Conventions and Guidelines v1.0**: ABI conventions for BPF programs to ensure portability.

The kernel docs at `docs.kernel.org/bpf/` serve as the authoritative reference, covering: the eBPF verifier, libbpf, BTF (BPF Type Format), the `bpf()` syscall API, helper functions, kfuncs (BPF kernel functions), program types, BPF maps, BPF iterators, and testing/debugging.

The Cilium project also maintains a comprehensive [BPF and XDP Reference Guide](https://docs.cilium.io/en/latest/bpf/) that goes into great technical depth.

## BPF Kernel Documentation Index

The kernel documentation at docs.kernel.org/bpf/ covers these topics:

- **eBPF Verifier** — The safety verifier that checks BPF programs before loading
- **libbpf** — The recommended C library for BPF applications
- **BPF Standardization** — Efforts to standardize BPF across platforms
- **BTF (BPF Type Format)** — Type information for CO-RE and debugging
- **Syscall API** — The `bpf()` system call interface
- **Helper Functions** — Kernel functions callable from BPF programs
- **kfuncs** — BPF kernel functions (newer, more flexible than helpers)
- **Program Types** — All available BPF program attachment points
- **BPF Maps** — Key-value data structures for BPF programs
- **BPF Iterators** — Iterate over kernel data structures from BPF
- **BPF Licensing** — GPL requirements for certain helper functions

## BPF Standardization

The BPF standardization effort aims to make BPF portable across different kernel versions and operating systems. Key components:

- **CO-RE (Compile Once, Run Everywhere)**: Uses BTF to resolve kernel structure layouts at load time
- **BPF Type Format (BTF)**: Compact type information embedded in the kernel and BPF programs
- **Standardized helpers/kfuncs**: A stable API surface for BPF programs

## kfuncs (BPF Kernel Functions)

kfuncs are the modern replacement for BPF helper functions. They are regular kernel functions exposed to BPF programs through a registration mechanism:

```c
/* kfunc declaration in kernel code */
__bpf_kfunc void bpf_task_acquire(struct task_struct *p);

/* Usage in BPF program */
struct task_struct *task = (struct task_struct *)bpf_get_current_task();
bpf_task_acquire(task);  /* kfunc call */
```

kfuncs provide:
- More flexibility than helpers (can access any kernel function)
- Better type safety through BTF
- Easier addition of new functionality
- Scoped availability (only certain program types can call certain kfuncs)

## BPF Design Decisions (from kernel docs)

From the kernel documentation at `docs.kernel.org/bpf/bpf_design_QA.html`:

### BPF Is NOT a Generic VM or Instruction Set

BPF is **not** a generic instruction set like x64 or arm64. It is **not** a generic virtual machine. BPF is a **generic instruction set with a C calling convention**, designed specifically to run in the Linux kernel (written in C). The instruction set is compatible with x64 and arm64 calling conventions and accounts for quirks of other architectures.

### C Calling Convention Constraints

- **Single return value**: Only register R0 is used for return values.
- **Maximum 5 arguments**: Registers R1–R5 for function arguments.
- **No access to instruction pointer or return address**.
- **No access to stack pointer** — only the frame pointer (R10) is accessible. LLVM defines R11 as the stack pointer internally but ensures generated code never uses it.

### Why C Calling Convention?

Because BPF programs run in the Linux kernel (written in C), using C calling convention enables:
- Zero-overhead calls between kernel and BPF programs
- JIT-compiled BPF programs are indistinguishable from native kernel C code
- Seamless interoperability with kernel helper functions and BPF maps

### Verifier Limits

| Limit | Value | Description |
|-------|-------|-------------|
| `BPF_MAXINSNS` | 4096 | Max instructions for unprivileged BPF programs |
| Complexity limit | 1,000,000 | Max instructions explored during analysis |
| Stack depth | 512 bytes | Maximum stack usage |
| Nested calls | ~8 | Max bpf-to-bpf call depth |

The verifier recognizes `pointer + bounded_register` expressions (not just `pointer + constant`). The development process guarantees future kernels accept all programs accepted by earlier versions.

### Instruction Design Philosophy

- **No flags register**: BPF avoided introducing a flags register (impossible to make generic across CPU architectures). Compare-and-jump instructions are used instead.
- **BPF_DIV doesn't map 1:1 to x64 div**: To avoid x64-specific complexity, plus it needs a div-by-zero runtime check.
- **Implicit prologue/epilogue**: Required because architectures like SPARC have register windows, and BPF needs safe division-by-zero handling.
- **New instructions must map to hardware**: `BPF_JLT` and `BPF_JLE` were added because they had native CPU equivalents. Instructions without HW mapping will not be accepted.

### BPF Safety Guarantees

- **Cannot call arbitrary kernel functions**: Only registered helpers and kfuncs.
- **Cannot overwrite arbitrary kernel memory**: Verifier prevents it.
- **Cannot overwrite arbitrary user memory**: Only properly validated pointers.
- **No stable ABI for kprobe attachment points**: Internal kernel functions can change.
- **Tracepoints are NOT part of the stable ABI**: They can change between kernel versions.

### BPF Stack and 32-bit Subregisters

- BPF 32-bit subregisters must zero the upper 32 bits of BPF registers.
- This makes BPF somewhat inefficient for 32-bit CPU architectures.\- True 32-bit registers will NOT be added to BPF.
- Some optimizations exist for JIT performance on 32-bit architectures.

## BPF Verifier Internals

The eBPF verifier is the safety gate that ensures BPF programs cannot crash or compromise the kernel. Understanding its internals is essential for writing complex BPF programs that pass verification.

### Two-Phase Verification

1. **DAG check**: Disallows loops and validates the control flow graph (CFG). Detects unreachable instructions.
2. **Path exploration**: Starting from the first instruction, the verifier simulates execution along all possible paths, tracking register and stack state changes.

### Register State Tracking

The verifier tracks every register's state using `struct bpf_reg_state`:

| Type | Meaning |
|------|--------|
| `NOT_INIT` | Register has not been written to (unreadable) |
| `SCALAR_VALUE` | A numeric value, not usable as a pointer |
| `PTR_TO_CTX` | Pointer to `bpf_context` (function argument R1) |
| `PTR_TO_MAP_VALUE` | Pointer to a map element value |
| `PTR_TO_MAP_VALUE_OR_NULL` | Map lookup result (becomes `PTR_TO_MAP_VALUE` after NULL check) |
| `PTR_TO_STACK` | Pointer to the BPF stack (R10 frame pointer) |
| `PTR_TO_PACKET` | Pointer to `skb->data` |
| `PTR_TO_PACKET_END` | Pointer to `skb->data + headlen` |
| `PTR_TO_SOCKET` | Pointer to `struct bpf_sock_ops` (refcounted) |

### Value Tracking (tnum)

The verifier tracks known/unknown bits using a **tnum** (tracked number): a pair of `(value, mask)`:
- Bits with `1` in the mask are unknown
- Bits with `1` in the value are known to be `1`
- Bits with `0` in both are known to be `0`

For example, reading a byte from memory sets the top 56 bits to known-zero and low 8 bits to unknown: `tnum = (0x0, 0xff)`.

### Bounds Tracking

The verifier tracks both signed and unsigned min/max values for each register:

```c
struct tnum {
    u64 value;
    u64 mask;
};

struct bpf_reg_state {
    /* Fixed offset from base */
    s32 off;
    /* Variable offset tracking */
    struct tnum var_off;
    s64 smin_value, smax_value;  /* Signed bounds */
    u64 umin_value, umax_value;  /* Unsigned bounds */
    /* ... */
};
```

Conditional branches update bounds. For example, `if (R2 > 8)` sets `umin_value = 9` on the true branch and `umax_value = 8` on the false branch.

### Bounded Loop Support (Linux 5.3+)

The verifier supports bounded loops where the loop counter has a provable upper bound:

```c
for (int i = 0; i < MAX_ITERATIONS; i++) {
    /* Verifier checks that loop terminates */
}
```

The verifier rejects loops where it cannot prove termination within `BPF_COMPLEXITY_LIMIT_INSNS` (1 million) instruction explorations.

### Pointer Arithmetic Rules

- Adding a scalar to a pointer is allowed (produces a new pointer with adjusted offset)
- Adding two pointers is forbidden (result is `SCALAR_VALUE`)
- Subtracting two pointers of the same type yields a scalar
- Pointer arithmetic must stay within bounds of the referenced object

### Direct Packet Access

For XDP and TC programs, the verifier allows direct access to packet data without `bpf_probe_read()`:

```c
void *data = (void *)(long)ctx->data;
void *data_end = (void *)(long)ctx->data_end;

struct ethhdr *eth = data;
if ((void *)(eth + 1) > data_end)
    return XDP_DROP;  /* Bounds check required */

/* After bounds check, verifier knows eth is safe to access */
```

The verifier tracks packet pointer ranges with `id`, `off`, and `r` (range) fields. After a bounds check, all copies of the pointer with the same `id` inherit the proven safe range.

### Verification Limits

| Limit | Default | Description |
|-------|---------|-------------|
| `BPF_COMPLEXITY_LIMIT_INSNS` | 1,000,000 | Max instructions explored |
| `BPF_MAXINSNS` | 4096 | Max instructions per program (unprivileged) |
| `MAX_BPF_STACK` | 512 bytes | Max stack usage |
| `MAX_CALL_FRAMES` | 8 | Max nested BPF-to-BPF calls |
| `MAX_TAIL_CALL_CNT` | 33 | Max tail call depth |

### Debugging Verifier Failures

```bash
# Get verbose verifier output
sudo bpftool prog load prog.o /sys/fs/bpf/prog 2>&1 | head -50

# Or with bpf() syscall (BPF_LOG_BUF_SIZE)
# The verifier writes its analysis to a log buffer

# Common failure patterns:
# - "R1 unbounded memory access" → missing bounds check
# - "invalid mem access 'scalar'" → pointer used as scalar
# - "math between map_value pointer and unbounded value" → unbounded pointer arithmetic
# - "back-edge from insn X to Y" → loop without provable bound
```

## BPF Helper Functions

BPF helper functions are kernel functions callable from eBPF programs. They provide the primary interface between BPF programs and the kernel, enabling map operations, time queries, packet manipulation, tracing output, and more. The authoritative reference is the `bpf-helpers(7)` man page.

From the kernel documentation at `docs.kernel.org/bpf/helpers.html`:

> *"bpf-helpers(7) maintains a list of helpers available to eBPF programs."*

### Key Helper Categories

**Map operations** (available to all program types):
- `bpf_map_lookup_elem(map, key)` — Lookup entry in a map
- `bpf_map_update_elem(map, key, value, flags)` — Add/update entry (`BPF_ANY`, `BPF_NOEXIST`, `BPF_EXIST`)
- `bpf_map_delete_elem(map, key)` — Delete entry

**Time and randomness**:
- `bpf_ktime_get_ns()` — Nanoseconds since boot (monotonic)
- `bpf_get_smp_processor_id()` — Current CPU number (stable during BPF execution)
- `bpf_get_prandom_u32()` — Pseudo-random 32-bit value (not cryptographic)

**Tracing and debugging**:
- `bpf_trace_printk(fmt, fmt_size, ...)` — Write to `/sys/kernel/tracing/trace_pipe` (max 3 args, debugging only)
- `bpf_get_current_pid_tgid()` — Returns `(tgid << 32) | pid`
- `bpf_get_current_comm(buf, size)` — Current process name
- `bpf_get_current_task()` — Pointer to current `task_struct`
- `bpf_probe_read(dst, size, unsafe_ptr)` — Safely read kernel memory
- `bpf_probe_read_user(dst, size, unsafe_ptr)` — Safely read user memory
- `bpf_probe_read_kernel(dst, size, unsafe_ptr)` — Safely read kernel memory
- `bpf_probe_read_user_str(dst, size, unsafe_ptr)` — Read user string

**Packet manipulation** (XDP/TC programs):
- `bpf_skb_store_bytes(skb, offset, from, len, flags)` — Write bytes to packet
- `bpf_l3_csum_replace(skb, offset, from, to, size)` — Recompute L3 checksum
- `bpf_l4_csum_replace(skb, offset, from, to, flags)` — Recompute L4 checksum
- `bpf_skb_load_bytes(skb, offset, to, len)` — Read bytes from packet
- `bpf_skb_pull_data(skb, len)` — Pull data into linear region

**Ring buffer** (preferred for event streaming):
- `bpf_ringbuf_reserve(ringbuf, size, flags)` — Reserve space
- `bpf_ringbuf_submit(data, flags)` — Submit reserved space
- `bpf_ringbuf_discard(data, flags)` — Discard reserved space
- `bpf_ringbuf_output(ringbuf, data, size, flags)` — Copy and submit

**Tail calls and program flow**:
- `bpf_tail_call(ctx, prog_array_map, index)` — Tail call into another BPF program
- `bpf_get_stackid(ctx, stackmap, flags)` — Get user/kernel stack ID
- `bpf_perf_event_output(ctx, map, flags, data, size)` — Output to perf event buffer

### Helper Availability by Program Type

Not all helpers are available to all program types. For example:
- `bpf_probe_read*()` is only available to tracing programs (kprobe, tracepoint, etc.)
- `bpf_skb_store_bytes()` is only available to TC and XDP programs
- `bpf_ringbuf_reserve()` is available to most program types
- `bpf_trace_printk()` is available to tracing programs (debugging only, not for production)

### Calling Convention

eBPF helpers follow strict conventions:
- Maximum **5 arguments** (eBPF calling convention: R1–R5)
- Single return value in R0
- Calls go directly into compiled kernel functions (no FFI overhead)
- Each program type has its own whitelist of callable helpers

For the complete list, see `man 7 bpf-helpers` or [bpf-helpers(7) online](https://man7.org/linux/man-pages/man7/bpf-helpers.7.html).

## BPF Iterators

From the [kernel BPF iterators documentation](https://docs.kernel.org/bpf/bpf_iterators.html), BPF iterators are a mechanism for iterating over kernel data structures from BPF programs. There are two forms: **BPF iterator programs** (stand-alone programs that generate seq_file output) and **open-coded BPF iterators** (in-kernel iteration APIs usable from any BPF program type).

### BPF Iterator Programs

A BPF iterator program is attached and activated by userspace. When read, it generates output for each entity in a kernel data structure (tasks, cgroups, BPF maps, TCP sockets, etc.). The output is formatted by the BPF program and delivered as a seq_file.

**How to use (userspace):**

```c
/* 1. Load BPF iterator program */
struct bpf_object *obj = bpf_object__open("my_iter.bpf.o");
bpf_object__load(obj);

/* 2. Create a link */
int prog_fd = bpf_program__fd(bpf_object__find_program_by_name(obj, "my_iter"));
int link_fd = bpf_link_create(prog_fd, 0, BPF_TRACE_ITER, NULL);

/* 3. Create an iterator fd */
int iter_fd = bpf_iter_create(link_fd);

/* 4. Read output (like reading a file) */
char buf[4096];
while (read(iter_fd, buf, sizeof(buf)) > 0) {
    printf("%s", buf);
}

/* 5. Cleanup */
close(iter_fd);
close(link_fd);
```

### Open-Coded BPF Iterators

Open-coded iterators are kfunc-based APIs that allow iteration from within any BPF program. They use a constructor/next/destructor pattern:

```c
/* Open-coded iterator usage (BPF program side) */
#include <vmlinux.h>
#include <bpf/bpf_helpers.h>

SEC("iter/task")
int dump_tasks(struct bpf_iter__task *ctx) {
    struct seq_file *seq = ctx->meta->seq;
    struct task_struct *task = ctx->task;

    if (!task)
        return 0;

    BPF_SEQ_PRINTF(seq, "pid=%d comm=%s\n", task->pid, task->comm);
    return 0;
}
```

**Open-coded iterator pattern (for custom iterators):**

Each open-coded iterator implements three kfuncs:

```c
/* Constructor — initialize iterator state on BPF stack */
bpf_iter_<type>_new(/* args */);

/* Next — return next element (NULL when exhausted) */
struct <element> *bpf_iter_<type>_next(struct bpf_iter_<type> *iter);

/* Destructor — cleanup resources */
void bpf_iter_<type>_destroy(struct bpf_iter_<type> *iter);
```

The BPF verifier ensures:
- Destructor is always called (even if constructor fails or next returns nothing)
- Next method eventually returns NULL (guaranteed termination)
- Iterator state is not tampered with outside constructor/next/destructor

**Using `bpf_for_each()` macro (libbpf):**

```c
/* Convenient macro for open-coded iteration */
struct task_struct *task;
bpf_for_each(task, task_iter, /* constructor args */) {
    /* process task */
    /* loop body runs for each task */
}
/* destructor called automatically */
```

### Available Iterator Types

| Iterator | Data Structure | Key Use Case |
|----------|---------------|-------------|
| `task` | `task_struct` | List all processes/threads |
| `task_file` | `task_struct` + `file` | List open files per process |
| `task_vma` | `task_struct` + `vm_area_struct` | List VMAs per process |
| `bpf_map` | `bpf_map` | Dump BPF map contents |
| `bpf_map_elem` | BPF map entries | Iterate map key-value pairs |
| `bpf_link` | `bpf_link` | List attached BPF programs |
| `tcp4` / `tcp6` | TCP sockets | Dump TCP connection table |
| `udp4` / `udp6` | UDP sockets | Dump UDP sockets |
| `netlink` | Netlink sockets | Dump netlink socket table |
| `cgroup` | `cgroup` | List cgroup hierarchy |
| `cgroup_hierarchy` | Cgroup tree | Walk cgroup tree |
| `css_task` | `css` + `task` | List tasks in cgroup |

### Why BPF Iterators?

Traditional approaches to dumping kernel data (e.g., `/proc`) have fixed output formats. To add new fields, you must patch the kernel. Tools like `ss` need kernel support for new socket options.

BPF iterators solve this by letting the BPF program control what data is collected and how it's formatted. You can add new fields, filter entries, compute statistics — all without kernel changes.

**Example: Custom TCP socket dump with BPF:**

```c
SEC("iter/tcp4")
int dump_tcp(struct bpf_iter__tcp4 *ctx) {
    struct sock_common *sk_common = ctx->sk_common;
    struct seq_file *seq = ctx->meta->seq;

    if (!sk_common)
        return 0;

    /* Only show established connections */
    if (sk_common->skc_state != TCP_ESTABLISHED)
        return 0;

    BPF_SEQ_PRINTF(seq, "%pI4:%d -> %pI4:%d\n",
                   &sk_common->skc_rcv_saddr, sk_common->skc_num,
                   &sk_common->skc_daddr, ntohs(sk_common->skc_dport));
    return 0;
}
```

### Verifier Integration

The verifier handles open-coded iterators by branching at each `next()` call:
- **NULL path** (iteration complete): Simulated first, must reach exit without looping
- **Non-NULL path** (new element): Validated with state equivalency check — if the verifier state after one iteration matches a previously validated state, the loop is proven safe (bounded by the guarantee that `next()` eventually returns NULL)

This mechanism allows the verifier to accept loops without explicit loop bounds, relying on the iterator contract instead.

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [eBPF.io](https://ebpf.io/)
- [BPF Documentation](https://docs.kernel.org/bpf/index.html)
- [BCC Project](https://github.com/iovisor/bcc)
- [bpftrace](https://github.com/bpftrace/bpftrace)
- [libbpf](https://github.com/libbpf/libbpf)
- [Cilium BPF Documentation](https://docs.cilium.io/en/latest/bpf/)
- [XDP Project](https://www.iovisor.org/technology/xdp)
- [BPF Standardization (kernel docs)](https://docs.kernel.org/bpf/standardization/index.html)
- [BPF Design Q&A (kernel docs)](https://docs.kernel.org/bpf/bpf_design_QA.html)
- [BPF Helper Functions — docs.kernel.org](https://docs.kernel.org/bpf/helpers.html)
- [bpf-helpers(7) man page](https://man7.org/linux/man-pages/man7/bpf-helpers.7.html)
- [eBPF Verifier Documentation](https://docs.kernel.org/bpf/verifier.html) — Official verifier internals (register tracking, bounds, direct packet access)
- [BPF Map Types — docs.kernel.org](https://docs.kernel.org/bpf/map.html) — Complete map type reference
- [BPF Program Types — docs.kernel.org](https://docs.kernel.org/bpf/prog_type.html)
- [BPF Iterators — docs.kernel.org](https://docs.kernel.org/bpf/bpf_iterators.html) — BPF iterator programs, open-coded iterators, available types

## Related Topics

- [ftrace](./ftrace.md) — Kernel function tracing (complementary to eBPF)
- [perf](./perf.md) — Hardware performance counters and sampling
- [strace](./strace-ltrace.md) — System call tracing (higher overhead alternative)
- [Kernel Debugging](./kernel-debugging.md) — KGDB, KDB, and crash utility
