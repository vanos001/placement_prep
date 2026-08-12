# bpftrace One-Liner Cookbook

## Introduction

bpftrace is a high-level tracing language for Linux built on eBPF. It provides a
concise, awk-inspired syntax for writing powerful tracing programs as one-liners or
short scripts. This cookbook organizes practical bpftrace recipes by subsystem:
disk I/O, networking, memory, scheduler, filesystem, security, and more.

Each recipe includes the one-liner, explanation, and sample output. For bpftrace
installation and language reference, see the [BPF & bpftrace](./bpf-bpftrace.md) page.

## Prerequisites

```bash
# Install bpftrace
sudo apt install bpftrace      # Debian/Ubuntu
sudo dnf install bpftrace       # Fedora
sudo pacman -S bpftrace         # Arch

# Verify
bpftrace --version
sudo bpftrace -l 'tracepoint:*' | wc -l   # List available tracepoints

# Check kernel requirements
uname -r   # 5.4+ recommended, 5.10+ for full features
```

## Disk I/O

### Trace Block I/O Requests

```bash
# Count block I/O requests by process
sudo bpftrace -e 'tracepoint:block:block_rq_issue { @[comm] = count(); }'
```

**Sample output:**

```
@[dd]: 1523
@[fio]: 8921
@[jbd2/sda1-8]: 45
@[kworker/u8:3]: 12
```

### Block I/O Latency Histogram

```bash
# I/O latency distribution (microseconds)
sudo bpftrace -e '
tracepoint:block:block_rq_complete {
    @usecs = hist(args->nr_sector * 1000000 / (nsecs - nsecs));
}
'
```

```bash
# Simpler: latency from issue to complete
sudo bpftrace -e '
tracepoint:block:block_rq_issue {
    @start[args->dev, args->sector] = nsecs;
}
tracepoint:block:block_rq_complete /@start[args->dev, args->sector]/ {
    @lat_usecs = hist((nsecs - @start[args->dev, args->sector]) / 1000);
    delete(@start[args->dev, args->sector]);
}
'
```

**Sample output:**

```
@lat_usecs:
[0]                  12 |@                       |
[1]                  89 |@@@@@@                   |
[2, 4)              234 |@@@@@@@@@@@@@@@@         |
[4, 8)              456 |@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ |
[8, 16)             312 |@@@@@@@@@@@@@@@@@@@@@@@@@|
[16, 32)            189 |@@@@@@@@@@@@@@@          |
[32, 64)             67 |@@@@@                    |
[64, 128)            23 |@@                       |
[128, 256)            5 |@                        |
[256, 512)            2 |@                        |
```

### I/O Size Distribution

```bash
# I/O request size distribution (sectors)
sudo bpftrace -e '
tracepoint:block:block_rq_issue {
    @sectors = hist(args->nr_sector);
}
'
```

### I/O by Device and Operation

```bash
# I/O count by device and direction (R/W)
sudo bpftrace -e '
tracepoint:block:block_rq_issue {
    @[args->dev, args->rwbs] = count();
}
'
```

### Slow I/O Tracing

```bash
# Trace I/O requests taking more than 10ms
sudo bpftrace -e '
tracepoint:block:block_rq_issue {
    @start[args->dev, args->sector] = nsecs;
}
tracepoint:block:block_rq_complete
    /(@ns = @start[args->dev, args->sector]) && (nsecs - @ns) > 10000000/ {
    printf("%-16s %d %d sectors %d ms\n",
           comm, pid, args->nr_sector,
           (nsecs - @ns) / 1000000);
    delete(@start[args->dev, args->sector]);
}
'
```

### I/O Queue Depth

```bash
# Track block I/O queue depth over time
sudo bpftrace -e '
tracepoint:block:block_rq_issue { @depth++; }
tracepoint:block:block_rq_complete { @depth--; }
interval:s:1 { printf("queue depth: %d\n", @depth); }
'
```

### Disk I/O Throughput

```bash
# I/O throughput per second by device
sudo bpftrace -e '
tracepoint:block:block_rq_issue {
    @bytes[args->dev] = sum(args->nr_sector * 512);
}
interval:s:1 {
    print(@bytes);
    clear(@bytes);
}
'
```

## Networking

### TCP Connection Tracing

```bash
# Trace TCP connections (active open)
sudo bpftrace -e '
kprobe:tcp_connect {
    $sk = (struct sock *)arg0;
    $daddr = ntop($sk->__sk_common.skc_daddr);
    $dport = $sk->__sk_common.skc_dport;
    printf("TCP connect: %s:%d pid=%d comm=%s\n",
           $daddr, $dport, pid, comm);
}
'
```

```bash
# Trace TCP connections using tracepoints
sudo bpftrace -e '
tracepoint:tcp:tcp_connect {
    $sk = (struct sock *)args->skaddr;
    $daddr = ntop($sk->__sk_common.skc_daddr);
    $dport = $sk->__sk_common.skc_dport;
    printf("%-6d %-16s %s:%d\n", pid, comm, $daddr, $dport);
}
'
```

### TCP Disconnect and Errors

```bash
# Trace TCP resets
sudo bpftrace -e '
tracepoint:tcp:tcp_receive_reset {
    printf("TCP RST: pid=%d comm=%s\n", pid, comm);
}
tracepoint:tcp:tcp_send_reset {
    printf("TCP RST sent: pid=%d comm=%s\n", pid, comm);
}
'
```

### TCP Retransmissions

```bash
# Count TCP retransmissions by process
sudo bpftrace -e '
kprobe:tcp_retransmit_skb {
    @[comm, pid] = count();
}
'
```

### Network Packet Count

```bash
# Packets received per interface per second
sudo bpftrace -e '
tracepoint:net:netif_receive_skb {
    @[args->name] = count();
}
interval:s:1 {
    print(@);
    clear(@);
}
'
```

### TCP Send/Receive Bytes

```bash
# TCP bytes sent by process
sudo bpftrace -e '
kprobe:tcp_sendmsg {
    @bytes_out[comm, pid] = sum((int)arg2);
}
'
```

### DNS Query Tracing

```bash
# Trace UDP port 53 traffic (DNS)
sudo bpftrace -e '
kprobe:udp_sendmsg {
    $sk = (struct sock *)arg0;
    $dport = $sk->__sk_common.skc_dport;
    if ($dport == htons(53)) {
        printf("DNS query: pid=%d comm=%s\n", pid, comm);
    }
}
'
```

### Socket Buffer Usage

```bash
# Track socket buffer usage
sudo bpftrace -e '
kprobe:sock_alloc_send_pskb {
    @alloc[comm, pid] = count();
}
kprobe:__kfree_skb {
    @free[comm, pid] = count();
}
'
```

### Network Latency (TCP RTT)

```bash
# Track TCP RTT samples
sudo bpftrace -e '
kprobe:tcp_rcv_established {
    $sk = (struct sock *)arg0;
    $rtt = $sk->tcp_mstamp;  // simplified
    @rtt[comm] = hist($rtt);
}
'
```

## Memory

### Page Allocation Tracing

```bash
# Page allocation requests by process
sudo bpftrace -e '
kprobe:__alloc_pages {
    @pages[comm, pid] = sum(1 << (int)arg1);  // order
}
'
```

### Page Fault Counting

```bash
# Page faults per process
sudo bpftrace -e '
software:page-faults:1 {
    @[comm, pid] = count();
}
'
```

### Major Page Faults

```bash
# Major page faults (disk I/O required)
sudo bpftrace -e '
software:page-faults:1 {
    if (args->type & 1) {  // major fault bit
        @[comm, pid] = count();
    }
}
'
```

### OOM Killer Tracing

```bash
# Trace OOM killer invocations
sudo bpftrace -e '
kprobe:oom_kill_process {
    printf("OOM: killing pid=%d comm=%s\n",
           ((struct task_struct *)arg1)->pid,
           ((struct task_struct *)arg1)->comm);
}
kprobe:select_bad_process {
    printf("OOM: selecting bad process...\n");
}
'
```

### Slab Allocation

```bash
# Slab allocation by call site
sudo bpftrace -e '
tracepoint:kmem:kmalloc {
    @bytes[args->call_site] = sum(args->bytes_alloc);
    @count[args->call_site] = count();
}
'
```

### Memory Compaction

```bash
# Track memory compaction events
sudo bpftrace -e '
tracepoint:compaction:mm_compaction_begin {
    printf("compaction begin: zone=%s\n", args->zone);
}
tracepoint:compaction:mm_compaction_end {
    printf("compaction end: status=%d\n", args->status);
}
'
```

### Huge Page Allocation

```bash
# Trace transparent huge page events
sudo bpftrace -e '
kprobe:__do_huge_pmd_anonymous_page {
    @thp[comm, pid] = count();
}
kprobe:collapse_huge_page {
    @collapse[comm, pid] = count();
}
'
```

### Memory Pressure Events

```bash
# Trace memory pressure (PSI)
sudo bpftrace -e '
tracepoint:psi:psi_memory {
    printf("memory pressure: some=%llu full=%llu\n",
           args->total, args->total);
}
'
```

## Scheduler

### Context Switch Tracing

```bash
# Context switches per process
sudo bpftrace -e '
tracepoint:sched:sched_switch {
    @[args->prev_comm] = count();
}
'
```

### Scheduling Latency

```bash
# Time from wakeup to actually running (scheduling latency)
sudo bpftrace -e '
tracepoint:sched:sched_wakeup {
    @qtime[args->pid] = nsecs;
}
tracepoint:sched:sched_switch
    /@qtime[args->next_pid]/ {
    @sched_lat_usecs[args->next_comm] =
        hist((nsecs - @qtime[args->next_pid]) / 1000);
    delete(@qtime[args->next_pid]);
}
'
```

### CPU Migration

```bash
# Track CPU migrations by process
sudo bpftrace -e '
tracepoint:sched:sched_migrate_task {
    printf("%-6d %-16s %d -> %d\n",
           args->pid, args->comm,
           args->orig_cpu, args->dest_cpu);
    @[args->comm] = count();
}
'
```

### Run Queue Length

```bash
# Per-CPU run queue length
sudo bpftrace -e '
tracepoint:sched:sched_wakeup { @rq[cpu]++; }
tracepoint:sched:sched_switch { @rq[cpu]--; }
interval:s:1 {
    printf("--- Run Queue Length ---\n");
    print(@rq);
}
'
```

### Process Runtime Distribution

```bash
# How long each process runs between context switches
sudo bpftrace -e '
tracepoint:sched:sched_switch {
    @runtime[args->prev_comm] = hist(args->prev_state == 0 ?
        (nsecs - @switch_ts[args->prev_pid]) / 1000 : 0);
    @switch_ts[args->next_pid] = nsecs;
}
'
```

### Wakeup Chain Tracing

```bash
# Who wakes up a specific process
sudo bpftrace -e '
tracepoint:sched:sched_wakeup /args->pid == 1234/ {
    printf("PID %d woke up by PID %d (%s)\n",
           args->pid, pid, comm);
    print(kstack);
}
'
```

### Preemption Tracing

```bash
# Trace involuntary context switches (preemption)
sudo bpftrace -e '
tracepoint:sched:sched_switch /args->prev_state == 0/ {
    printf("PREEMPTED: %s (pid=%d) by %s (pid=%d) cpu=%d\n",
           args->prev_comm, args->prev_pid,
           args->next_comm, args->next_pid, cpu);
}
'
```

## Filesystem

### VFS Operation Latency

```bash
# VFS read latency by process
sudo bpftrace -e '
kprobe:vfs_read { @start[pid] = nsecs; }
kretprobe:vfs_read /@start[pid]/ {
    @vfs_read_usecs[comm] = hist((nsecs - @start[pid]) / 1000);
    delete(@start[pid]);
}
'
```

### File Open Tracing

```bash
# Trace file opens with filenames
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_openat {
    printf("%-6d %-16s %s\n", pid, comm,
           str(args->filename));
}
'
```

### ext4 Specific Tracing

```bash
# ext4 write latency
sudo bpftrace -e '
kprobe:ext4_file_write_iter { @start[pid] = nsecs; }
kretprobe:ext4_file_write_iter /@start[pid]/ {
    @ext4_write_usecs[comm] = hist((nsecs - @start[pid]) / 1000);
    delete(@start[pid]);
}
'
```

### Filesystem Sync Tracing

```bash
# Trace fsync calls
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_fsync {
    printf("fsync: pid=%d comm=%s fd=%d\n",
           pid, comm, args->fd);
}
tracepoint:syscalls:sys_enter_fdatasync {
    printf("fdatasync: pid=%d comm=%s fd=%d\n",
           pid, comm, args->fd);
}
'
```

### Inode Cache Hits

```bash
# dentry/inode cache lookup stats
sudo bpftrace -e '
kprobe:d_lookup { @lookups[comm] = count(); }
kprobe:d_alloc { @allocs[comm] = count(); }
'
```

## Security

### Syscall Auditing

```bash
# Count syscalls by type
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter {
    @syscalls[args->id] = count();
}
'
```

### File Access Auditing

```bash
# Trace all file access (open/openat) with flags
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_openat {
    printf("%-6d %-16s %s flags=%x\n",
           pid, comm, str(args->filename), args->flags);
}
'
```

### Capability Checks

```bash
# Trace capability checks
sudo bpftrace -e '
kprobe:cap_capable {
    $cap = (int)arg1;
    printf("cap_check: pid=%d comm=%s cap=%d\n",
           pid, comm, $cap);
}
'
```

### Signal Tracing

```bash
# Trace signals sent between processes
sudo bpftrace -e '
tracepoint:signal:signal_generate {
    printf("signal %d sent to pid=%d by pid=%d (%s)\n",
           args->sig, args->pid, pid, comm);
}
'
```

### Mount/Unmount Tracing

```bash
# Trace mount operations
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_mount {
    printf("mount: pid=%d comm=%s dev=%s dir=%s\n",
           pid, comm,
           str(args->dev_name),
           str(args->dir_name));
}
'
```

## Containers and Namespaces

### Container Process Tracing

```bash
# Trace processes by cgroup (container)
sudo bpftrace -e '
tracepoint:sched:sched_process_exec {
    $task = (struct task_struct *)bpf_get_current_task();
    $cgrp = $task->cgroups->subsys[0]->cgroup->kn->name;
    printf("exec: pid=%d comm=%s cgroup=%s\n",
           pid, comm, str($cgrp));
}
'
```

### Namespace-Aware Tracing

```bash
# Trace with network namespace info
sudo bpftrace -e '
kprobe:tcp_connect {
    $sk = (struct sock *)arg0;
    $net = $sk->__sk_common.skc_net.net->ns.inum;
    printf("tcp_connect: pid=%d netns=%u\n", pid, $net);
}
'
```

### Syscall Filtering by Container

```bash
# Count syscalls by container (cgroup)
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter {
    $task = (struct task_struct *)bpf_get_current_task();
    $cgrp_id = $task->cgroups->subsys[0]->cgroup->kn->id.id;
    @[$cgrp_id] = count();
}
'
```

## Profiling

### CPU Profiling (On-CPU)

```bash
# On-CPU stack profile at 99 Hz
sudo bpftrace -e 'profile:hz:99 { @[kstack] = count(); }'
```

### User-Space Profiling

```bash
# User-space stack profile
sudo bpftrace -e 'profile:hz:99 { @[ustack] = count(); }'
```

### Per-Process CPU Profile

```bash
# CPU profile per process
sudo bpftrace -e 'profile:hz:99 { @[comm, kstack] = count(); }'
```

### Off-CPU Profiling

```bash
# Off-CPU time with stack traces
sudo bpftrace -e '
tracepoint:sched:sched_switch {
    @offcpu_start[args->prev_pid] = nsecs;
    @offcpu_comm[args->prev_pid] = str(args->prev_comm);
}
profile:ms:1 /@offcpu_start[pid]/ {
    $dur = nsecs - @offcpu_start[pid];
    @offcpu_ms[@offcpu_comm[pid], kstack] = sum($dur / 1000000);
    delete(@offcpu_start[pid]);
}
'
```

### Cache Miss Profiling

```bash
# Stack traces on cache misses
sudo bpftrace -e 'hardware:cache-misses:1000 { @[kstack] = count(); }'
```

### Branch Miss Profiling

```bash
# Stack traces on branch misses
sudo bpftrace -e 'hardware:branch-misses:1000 { @[kstack] = count(); }'
```

## Timed and Interval Scripts

### One-Second Summary

```bash
# Print summary every second
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_read {
    @reads[comm] = count();
}
interval:s:1 {
    print(@reads);
    clear(@reads);
}
'
```

### Top Processes by Syscall Rate

```bash
# Top 10 processes by syscall rate (updates every second)
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter {
    @count[comm] = count();
}
interval:s:1 {
    print(@count, 10);
    clear(@count);
}
'
```

### Timed Trace with Auto-Stop

```bash
# Trace for exactly 10 seconds then exit
sudo bpftrace -e '
tracepoint:block:block_rq_issue { @[comm] = count(); }
interval:s:10 { exit(); }
'
```

### Periodic Histogram Dump

```bash
# Dump latency histogram every 5 seconds
sudo bpftrace -e '
kprobe:vfs_read { @start[pid] = nsecs; }
kretprobe:vfs_read /@start[pid]/ {
    @us = hist((nsecs - @start[pid]) / 1000);
    delete(@start[pid]);
}
interval:s:5 {
    print(@us);
    clear(@us);
}
'
```

## Advanced Techniques

### Map-Driven Filtering

```bash
# Filter by PID list stored in a map
# (Create the filter map first, then trace)
sudo bpftrace -e '
BEGIN {
    // Trace only these PIDs
    @filter[1234] = 1;
    @filter[5678] = 1;
}
tracepoint:raw_syscalls:sys_enter /@filter[pid]/ {
    @syscalls[args->id] = count();
}
'
```

### Histogram with Custom Buckets

```bash
# Latency with custom bucket boundaries
sudo bpftrace -e '
kprobe:vfs_read { @start[pid] = nsecs; }
kretprobe:vfs_read /@start[pid]/ {
    $us = (nsecs - @start[pid]) / 1000;
    if ($us < 10) @bucket["<10us"] = count();
    else if ($us < 100) @bucket["10-100us"] = count();
    else if ($us < 1000) @bucket["100us-1ms"] = count();
    else if ($us < 10000) @bucket["1-10ms"] = count();
    else @bucket[">10ms"] = count();
    delete(@start[pid]);
}
'
```

### Process Lifetime Tracking

```bash
# Track process creation and exit
sudo bpftrace -e '
tracepoint:sched:sched_process_fork {
    printf("FORK: parent=%d (%s) child=%d\n",
           args->parent_pid, args->parent_comm,
           args->child_pid);
}
tracepoint:sched:sched_process_exit {
    printf("EXIT: pid=%d (%s) code=%d\n",
           args->pid, args->comm, args->exit_code);
}
'
```

### Function Call Counting

```bash
# Count calls to specific kernel functions
sudo bpftrace -e '
kprobe:tcp_sendmsg { @tcp_send++; }
kprobe:tcp_recvmsg { @tcp_recv++; }
kprobe:tcp_connect { @tcp_conn++; }
kprobe:tcp_close { @tcp_close++; }
interval:s:5 {
    printf("--- TCP Stats ---\n");
    print(@tcp_send);
    print(@tcp_recv);
    print(@tcp_conn);
    print(@tcp_close);
}
'
```

### Conditional Aggregation

```bash
# Only track slow operations (>1ms)
sudo bpftrace -e '
kprobe:vfs_read { @start[pid] = nsecs; }
kretprobe:vfs_read /@start[pid]/ {
    $us = (nsecs - @start[pid]) / 1000;
    if ($us > 1000) {
        @slow_reads[comm, kstack(3)] = count();
    }
    delete(@start[pid]);
}
'
```

## System-Wide Observability

### All Syscalls Per Second

```bash
# Total syscall rate
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter { @++; }
interval:s:1 { printf("syscalls/sec: %d\n", @); @ = 0; }
'
```

### System Call Latency

```bash
# Syscall latency by type
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter {
    @start[args->id, pid] = nsecs;
}
tracepoint:raw_syscalls:sys_exit
    /@start[args->id, pid]/ {
    @lat_us[args->id] = hist((nsecs - @start[args->id, pid]) / 1000);
    delete(@start[args->id, pid]);
}
'
```

### Interrupt Latency

```bash
# IRQ handler duration
sudo bpftrace -e '
tracepoint:irq:irq_handler_entry { @start[args->irq] = nsecs; }
tracepoint:irq:irq_handler_exit /@start[args->irq]/ {
    @irq_us[args->irq, args->name] = hist((nsecs - @start[args->irq]) / 1000);
    delete(@start[args->irq]);
}
'
```

### Softirq Latency

```bash
# Softirq handler duration
sudo bpftrace -e '
tracepoint:irq:softirq_entry { @start[cpu] = nsecs; }
tracepoint:irq:softirq_exit /@start[cpu]/ {
    @softirq_us[args->vec_nr] = hist((nsecs - @start[cpu]) / 1000);
    delete(@start[cpu]);
}
'
```

### Timer Interrupt Drift

```bash
# Check timer interrupt regularity
sudo bpftrace -e '
tracepoint:irq:irq_handler_entry /args->irq == 0/ {
    if (@last) {
        @drift_us = hist((nsecs - @last) / 1000);
    }
    @last = nsecs;
}
'
```

## Quick Reference

### Probe Types

| Type | Syntax | Example |
|------|--------|---------|
| kprobe | `kprobe:func` | `kprobe:tcp_sendmsg` |
| kretprobe | `kretprobe:func` | `kretprobe:vfs_read` |
| uprobe | `uprobe:/path:func` | `uprobe:/lib/libc.so.6:malloc` |
| tracepoint | `tracepoint:cat:event` | `tracepoint:sched:sched_switch` |
| profile | `profile:hz:N` | `profile:hz:99` |
| interval | `interval:s:N` | `interval:s:5` |
| software | `software:event:N` | `software:page-faults:1` |
| hardware | `hardware:event:N` | `hardware:cache-misses:1000` |

### Built-in Variables

| Variable | Description |
|----------|-------------|
| `pid` | Process ID (thread) |
| `tid` | Thread ID |
| `uid` | User ID |
| `gid` | Group ID |
| `nsecs` | Nanosecond timestamp |
| `elapsed` | Time since bpftrace start |
| `comm` | Process name |
| `kstack` | Kernel stack trace |
| `ustack` | User stack trace |
| `arg0-argN` | Function arguments |
| `retval` | Return value (kretprobe) |
| `func` | Function name |
| `probe` | Full probe name |
| `cpu` | Current CPU |
| `cgroup` | Cgroup ID |

### Map Functions

| Function | Description |
|----------|-------------|
| `@map = count()` | Increment counter |
| `@map[key] = count()` | Per-key counter |
| `@map[key] = sum(val)` | Per-key sum |
| `@map[key] = hist(val)` | Histogram |
| `@map[key] = lhist(val, min, max, step)` | Linear histogram |
| `@map[key] = min(val)` | Minimum |
| `@map[key] = max(val)` | Maximum |
| `@map[key] = avg(val)` | Average |
| `@map[key] = stats(val)` | Statistics (count, avg, total) |
| `print(@map)` | Print map |
| `print(@map, N)` | Print top N entries |
| `clear(@map)` | Clear map |
| `delete(@map[key])` | Delete key |

## Summary

| Subsystem | Key Recipes | Primary Probes |
|-----------|-------------|----------------|
| Disk I/O | Latency, throughput, queue depth | `block_rq_*`, `vfs_*` |
| Networking | Connections, retrans, RTT | `tcp_*`, `netif_*` |
| Memory | Page faults, allocations, OOM | `kmem:*`, `page-faults` |
| Scheduler | Latency, migration, runtime | `sched_*` |
| Filesystem | VFS ops, open tracing, cache | `vfs_*`, `syscalls:*_openat` |
| Security | Syscall audit, capabilities | `raw_syscalls`, `signal` |
| Containers | cgroup filtering, namespace | `sched_process_*` |
| Profiling | CPU, off-CPU, cache | `profile:*`, `hardware:*` |

These one-liners form the building blocks for Linux observability. Combine them,
pipe output to files, and build monitoring scripts. For complex analysis, save
the bpftrace script to a `.bt` file and run it with `sudo bpftrace script.bt`.
