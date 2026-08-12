# proc Filesystem for Observability

## Introduction

The `/proc` filesystem is a pseudo-filesystem that provides a window into the kernel's internal data structures. It doesn't exist on disk—it's generated dynamically by the kernel when accessed. `/proc` is the foundation of Linux observability: every monitoring tool (`top`, `free`, `iostat`, `vmstat`, `ps`) reads from `/proc` under the hood.

Understanding `/proc` gives you direct access to kernel information without any additional tools. When `top` shows CPU usage, it's reading `/proc/stat`. When `free` shows memory, it's reading `/proc/meminfo`. When `ps` lists processes, it's reading `/proc/<pid>/status`. Knowing this lets you write custom monitoring scripts, debug issues that standard tools can't capture, and understand exactly what your system is doing.

## /proc Overview

```bash
ls /proc/
# 1  2  3  ...  self  cpuinfo  meminfo  stat  version  ...
```

The entries in `/proc` fall into two categories:

- **Numeric directories** (`1`, `2`, `3`, ...) — one per running process, containing per-process information
- **Named files** (`cpuinfo`, `meminfo`, `stat`, ...) — system-wide kernel information

### System-Wide Files

```bash
ls /proc/ | grep -v '^[0-9]' | sort
# acpi         bus/       cmdline    cpuinfo    crypto     devices
# diskstats    dma        driver/    execdomains  fb        filesystems
# fs/          interrupts  iomem     ioports    irq/       kallsyms
# kcore        keys       key-users  kmsg       kpagecount kpageflags
# loadavg      locks      mdstat     meminfo    misc       modules
# mounts       mtrr       net/       pagetypeinfo  partitions  sched_debug
# schedstat    scsi/      self       slabinfo   softirqs   stat
# swaps        sys/       sysrq-trigger  thread-self  timer_list  tty/
# uptime       version    vmallocinfo  vmstat     zoneinfo
```

### Per-Process Directories

```bash
# Each process has a directory /proc/<pid>/
ls /proc/1/
# attr/    cgroup   comm     cpu      cwd@     environ  exe@     fd/
# fdinfo/  io       limits   maps     mem      mountinfo mounts   net/
# ns/      oom_score  oom_score_adj  pagemap  personality  root@
# sched    sessionid  smaps    smaps_rollup   stat     statm    status
# syscall  task/    timers   wchan

# The 'self' symlink points to the current process's directory
ls -la /proc/self
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 /proc/self -> 12345
```

## Process Information (/proc/[pid]/)

### Process Identity

```bash
# Process ID and parent
cat /proc/1/status | head -10
# Name:   systemd
# Umask:  0000
# State:  S (sleeping)
# Tgid:   1
# Ngid:   0
# Pid:    1
# PPid:   0
# TracerPid:  0
# Uid:    0   0   0   0
# Gid:    0   0   0   0

# Command line (null-separated)
cat /proc/1/cmdline | tr '\0' ' '
# /sbin/init

# Current working directory
ls -la /proc/1/cwd
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 /proc/1/cwd -> /

# Executable path
ls -la /proc/1/exe
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 /proc/1/exe -> /lib/systemd/systemd

# Process environment (null-separated, requires root)
cat /proc/1/environ | tr '\0' '\n' | head -5
# PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
# LANG=en_US.UTF-8
# TERM=xterm-256color
```

### Process Status

```bash
cat /proc/1/status
# Name:   systemd
# Umask:  0000
# State:  S (sleeping)
# Tgid:   1
# Ngid:   0
# Pid:    1
# PPid:   0
# TracerPid:  0
# Uid:    0   0   0   0
# Gid:    0   0   0   0
# FDSize: 256
# Groups:
# NStgid: 1
# NSpid:  1
# NSpgid: 1
# NSsid:  1
# VmPeak:  12345678 kB
# VmSize:  12345678 kB
# VmLck:         0 kB
# VmPin:         0 kB
# VmHWM:    8234567 kB
# VmRSS:    8234567 kB
# RssAnon:   8234567 kB
# RssFile:    123456 kB
# RssShmem:    56789 kB
# VmData:   8234567 kB
# VmStk:       136 kB
# VmExe:    1234567 kB
# VmLib:     234567 kB
# VmPTE:      3456 kB
# VmSwap:        0 kB
# Threads: 42
# SigQ:   0/123456
# SigPnd: 0000000000000000
# ShdPnd: 0000000000000000
# SigBlk: 0000000000000000
# SigIgn: 0000000000000000
# SigCgt: 0000000000000000
# CapInh: 0000000000000000
# CapPrm: 0000003fffffffff
# CapEff: 0000003fffffffff
# CapBnd: 0000003fffffffff
# CapAmb: 0000000000000000
# NoNewPrivs: 0
# Seccomp:    0
# Seccomp_filters:    0
# Speculation_Store_Bypass:   vulnerable
# SpeculationIndirectBranch:  vulnerable
# Cpus_allowed:   ffffffff
# Cpus_allowed_list:  0-31
# Mems_allowed:   00000000,00000000,00000000,00000001
# Mems_allowed_list:  0
# voluntary_ctxt_switches:    123456
# nonvoluntary_ctxt_switches: 789
```

### Key Status Fields Explained

| Field | Description | Troubleshooting Use |
|-------|-------------|---------------------|
| `VmPeak` | Peak virtual memory size | Detect memory leaks |
| `VmRSS` | Resident Set Size (physical memory) | Current memory usage |
| `RssAnon` | Anonymous memory (heap, mmap) | Heap memory usage |
| `RssFile` | File-backed memory (shared libs) | Library memory |
| `RssShmem` | Shared memory (tmpfs, shmem) | Shared memory usage |
| `VmSwap` | Swapped-out memory | Detect swapping |
| `Threads` | Number of threads | Thread leak detection |
| `voluntary_ctxt_switches` | Voluntary context switches | I/O waiting |
| `nonvoluntary_ctxt_switches` | Involuntary switches | CPU contention |
| `Seccomp` | Seccomp filter mode | Security policy |
| `Speculation_Store_Bypass` | Spectre mitigation | Vulnerability status |

### Process I/O Statistics

```bash
cat /proc/1/io
# rchar: 1234567890
# wchar: 2345678901
# syscr: 1234567
# syscw: 2345678
# read_bytes: 1234567890
# write_bytes: 2345678901
# cancelled_write_bytes: 123456789

# Fields:
# rchar: bytes read (including from cache)
# wchar: bytes written (including to cache)
# syscr: read syscalls
# syscw: write syscalls
# read_bytes: bytes actually read from storage
# write_bytes: bytes actually written to storage
# cancelled_write_bytes: bytes cancelled before write
```

### Process Memory Map

```bash
# Memory mappings
cat /proc/1/maps | head -10
# 7f1234000-7f1256000 r-xp 00000000 08:01 1234567  /lib/libc-2.31.so
# 7f1256000-7f1278000 ---p 00022000 08:01 1234567  /lib/libc-2.31.so
# 7f1278000-7f127a000 r--p 00022000 08:01 1234567  /lib/libc-2.31.so
# 7f127a000-7f127c000 rw-p 00024000 08:01 1234567  /lib/libc-2.31.so
# 7f127c000-7f1282000 rw-p 00000000 00:00 0
# 7ffc123000-7ffc145000 rw-p 00000000 00:00 0      [stack]

# Format: address perms offset dev inode pathname
# perms: r=read, w=write, x=execute, p=private, s=shared

# Detailed memory map with page info
cat /proc/1/smaps | head -30
# 7f1234000-7f1256000 r-xp 00000000 08:01 1234567  /lib/libc-2.31.so
# Size:               136 kB
# KernelPageSize:        4 kB
# MMUPageSize:           4 kB
# Rss:                 136 kB
# Pss:                 136 kB
# Shared_Clean:          0 kB
# Shared_Dirty:          0 kB
# Private_Clean:       136 kB
# Private_Dirty:         0 kB
# Referenced:          136 kB
# Anonymous:             0 kB
# LazyFree:              0 kB
# AnonHugePages:         0 kB
# ShmemPmdMapped:        0 kB
# Shared_Hugetlb:        0 kB
# Private_Hugetlb:       0 kB
# Swap:                  0 kB
# SwapPss:               0 kB
# Locked:                0 kB
```

### Process File Descriptors

```bash
# List open file descriptors
ls -la /proc/1/fd/
# lrwx------ 1 root root 64 Jul 22 10:00 0 -> /dev/null
# lrwx------ 1 root root 64 Jul 22 10:00 1 -> /dev/null
# lrwx------ 1 root root 64 Jul 22 10:00 2 -> /dev/null
# lrwx------ 1 root root 64 Jul 22 10:00 3 -> socket:[12345]
# lrwx------ 1 root root 64 Jul 22 10:00 4 -> /var/log/syslog

# File descriptor info
cat /proc/1/fdinfo/3
# pos:    0
# flags:  02000002
# mnt_id: 12

# Count open files per process
ls /proc/1/fd/ | wc -l
# 42

# Find which process has a file open
ls -la /proc/*/fd/ 2>/dev/null | grep "deleted"
# Shows deleted files still held open
```

### Process Limits

```bash
cat /proc/1/limits
# Limit                     Soft Limit           Hard Limit           Units
# Max cpu time              unlimited            unlimited            seconds
# Max file size             unlimited            unlimited            bytes
# Max data size             unlimited            unlimited            bytes
# Max stack size            8388608              unlimited            bytes
# Max core file size        0                    unlimited            bytes
# Max resident set          unlimited            unlimited            bytes
# Max processes             123456               123456               processes
# Max open files            1024                 1048576              files
# Max locked memory         67108864             67108864             bytes
# Max address space         unlimited            unlimited            bytes
# Max file locks            unlimited            unlimited            locks
# Max pending signals       123456               123456               signals
# Max msgqueue size         819200               819200               bytes
# Max nice priority         0                    0
# Max realtime priority     0                    0
# Max realtime timeout      unlimited            unlimited            us
```

### Process Scheduling

```bash
# Scheduling information
cat /proc/1/sched
# systemd (1, #threads: 42)
# -------------------------------------------------------------------
# se.exec_start                      :    12345678.123456
# se.vruntime                        :    23456789.234567
# se.sum_exec_runtime                :    34567.890123
# nr_switches                        :    123456
# nr_voluntary_switches              :    123450
# nr_involuntary_switches            :    6
# se.statistics.wait_sum             :    1234.567890
# se.statistics.wait_max             :    45.678901
# se.statistics.wait_count           :    123450
# se.statistics.iowait_sum           :    0.000000
# se.statistics.iowait_count         :    0
```

## /proc/stat: CPU Statistics

```bash
cat /proc/stat
# cpu  123456789 7890 23456789 8901234567 67890 0 12345 0 0 0
# cpu0 30864197 1972 5864197 2225308641 16972 0 3136 0 0 0
# cpu1 30864197 1972 5864197 2225308641 16972 0 3136 0 0 0
# cpu2 30864197 1972 5864197 2225308641 16972 0 3136 0 0 0
# cpu3 30864197 1972 5864197 2225308641 16972 0 3136 0 0 0
# intr 1234567890 123 456 789 ...
# ctxt 12345678901
# btime 1626784800
# processes 1234567
# procs_running 4
# procs_blocked 0
# softirq 1234567890 123456 789012 345678 ...
```

### Fields Explained

```bash
# cpu  user nice system idle iowait irq softirq steal guest guest_nice
# user:    normal processes executing in user mode
# nice:    niced processes executing in user mode
# system:  processes executing in kernel mode
# idle:    twiddling thumbs
# iowait:  waiting for I/O to complete
# irq:     servicing hardware interrupts
# softirq: servicing software interrupts
# steal:   involuntary wait (virtual machines)
# guest:   running a virtual CPU
# guest_nice: running a niced virtual CPU
```

### CPU Utilization Calculation

```bash
#!/bin/bash
# Calculate CPU utilization from /proc/stat
# Read twice, 1 second apart, calculate difference

cpu1=$(head -1 /proc/stat)
sleep 1
cpu2=$(head -1 /proc/stat)

# Parse fields
read -r _ user1 nice1 sys1 idle1 iow1 irq1 sirq1 steal1 _ _ <<< "$cpu1"
read -r _ user2 nice2 sys2 idle2 iow2 irq2 sirq2 steal2 _ _ <<< "$cpu2"

# Calculate deltas
idle_delta=$((idle2 - idle1))
total_delta=$(( (user2+sys2+nice2+idle2+iow2+irq2+sirq2+steal2) -
                (user1+sys1+nice1+idle1+iow1+irq1+sirq1+steal1) ))

# Calculate utilization
cpu=$((100 * (total_delta - idle_delta) / total_delta))
echo "CPU: ${cpu}%"

# Per-CPU calculation
for i in $(seq 0 $(($(nproc) - 1))); do
    cpu1=$(grep "^cpu$i " /proc/stat)
    sleep 1
    cpu2=$(grep "^cpu$i " /proc/stat)
    # ... same calculation ...
done
```

## /proc/meminfo: Memory Statistics

```bash
cat /proc/meminfo
# MemTotal:       32768000 kB
# MemFree:         2048576 kB
# MemAvailable:   19922944 kB
# Buffers:          654320 kB
# Cached:         18234560 kB
# SwapCached:            0 kB
# Active:         12345678 kB
# Inactive:       18765432 kB
# Active(anon):    8234567 kB
# Inactive(anon):  1234567 kB
# Active(file):   12345678 kB
# Inactive(file): 18765432 kB
# Unevictable:      123456 kB
# Mlocked:          123456 kB
# SwapTotal:       8388608 kB
# SwapFree:        8388608 kB
# Dirty:            123456 kB
# Writeback:          1234 kB
# AnonPages:       8234567 kB
# Mapped:          2345678 kB
# Shmem:            567890 kB
# Slab:            1567890 kB
# SReclaimable:    1234567 kB
# SUnreclaim:       333323 kB
# KernelStack:       12345 kB
# PageTables:        34567 kB
# CommitLimit:    24772608 kB
# Committed_AS:   16234567 kB
# HugePages_Total:    1024
# HugePages_Free:      512
# HugePages_Rsvd:      256
# Hugepagesize:       2048 kB
```

### Key Memory Metrics

| Field | Description | How to Interpret |
|-------|-------------|------------------|
| `MemTotal` | Total usable RAM | Physical memory minus reserved |
| `MemFree` | Completely unused RAM | Don't panic if low — Linux caches aggressively |
| `MemAvailable` | Memory available for allocations | **The number to watch** — includes reclaimable cache |
| `Buffers` | Block device buffer cache | Metadata for block devices |
| `Cached` | Page cache (file data in RAM) | Reclaimable under memory pressure |
| `Active` | Recently used memory | Hot pages |
| `Inactive` | Candidate for reclaim | Cold pages |
| `Dirty` | Waiting to be written to disk | High = I/O bottleneck |
| `Writeback` | Currently being written | Active I/O |
| `Slab` | Kernel slab allocator memory | Kernel data structures |
| `SReclaimable` | Slab memory that can be freed | Available under pressure |
| `AnonPages` | Anonymous memory (heap, stack) | Process memory |
| `Mapped` | Memory-mapped files | Libraries, mmap'd files |
| `Shmem` | Shared memory (tmpfs, shmem) | Shared between processes |
| `HugePages_Total` | Allocated huge pages | For databases, VMs |
| `HugePages_Free` | Unused huge pages | Available for allocation |

### Memory Usage Calculation

```bash
# Used memory (excluding cache/buffers)
grep -E "MemTotal|MemAvailable" /proc/meminfo
# MemTotal:       32768000 kB
# MemAvailable:   19922944 kB

# Used = MemTotal - MemAvailable
used=$((32768000 - 19922944))
echo "Used: ${used} kB"

# Percentage
pct=$((100 * used / 32768000))
echo "Usage: ${pct}%"

# Cache usage
grep -E "Cached|Buffers|SReclaimable" /proc/meminfo
# Cached:         18234560 kB
# Buffers:          654320 kB
# SReclaimable:    1234567 kB

# Swap usage
grep -E "SwapTotal|SwapFree" /proc/meminfo
# SwapTotal:       8388608 kB
# SwapFree:        8388608 kB
```

## /proc/diskstats: Disk I/O Statistics

```bash
cat /proc/diskstats | grep sda
#   8 0 sda 123456 789 12345678 9012 567890 123 45678901 2345 0 6789 11357
```

### Fields (14 columns)

```bash
# 1  major: Major device number
# 2  minor: Minor device number
# 3  name: Device name
# 4  reads_completed: Total reads completed
# 5  reads_merged: Reads merged (adjacent)
# 6  sectors_read: Total sectors read (512 bytes each)
# 7  read_time_ms: Total read time (ms)
# 8  writes_completed: Total writes completed
# 9  writes_merged: Writes merged
# 10 sectors_written: Total sectors written
# 11 write_time_ms: Total write time (ms)
# 12 io_in_progress: I/Os currently in progress
# 13 io_time_ms: Time doing I/Os (ms)
# 14 weighted_io_time_ms: Weighted I/O time (ms)
```

### Calculating I/O Metrics

```bash
#!/bin/bash
# Calculate I/O metrics from /proc/diskstats
DEVICE="sda"

get_disk_stats() {
    grep " $DEVICE " /proc/diskstats
}

# Read twice, 1 second apart
stats1=$(get_disk_stats)
sleep 1
stats2=$(get_disk_stats)

# Parse fields
read -r _ _ _ r1 rm1 rs1 rt1 w1 wm1 ws1 wt1 io1 iot1 wiot1 <<< "$stats1"
read -r _ _ _ r2 rm2 rs2 rt2 w2 wm2 ws2 wt2 io2 iot2 wiot2 <<< "$stats2"

# IOPS = delta(reads + writes) / delta(time)
iops=$(( (r2 - r1 + w2 - w1) ))

# Throughput = delta(sectors * 512) / delta(time) in KB/s
throughput=$(( (rs2 - rs1 + ws2 - ws1) * 512 / 1024 ))

# Read latency = delta(read_time) / delta(read_count)
if [ $((r2 - r1)) -gt 0 ]; then
    read_lat=$(( (rt2 - rt1) / (r2 - r1) ))
else
    read_lat=0
fi

# Utilization = delta(io_time) / delta(wall_time) * 100
util=$(( (iot2 - iot1) / 10 ))

echo "IOPS: $iops | Throughput: ${throughput}KB/s | Read Latency: ${read_lat}ms | Utilization: ${util}%"
```

## /proc/net: Network Statistics

```bash
# Network interface statistics
cat /proc/net/dev
# Inter-|   Receive                                                |  Transmit
#  face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo frame compressed
#   lo: 123456789 1234567    0    0    0     0          0         0 123456789 1234567    0    0    0     0       0         0
#  eth0: 12345678901 12345678 0 1234 0     0          0    123456 23456789012 23456789 0 567 0     0       0         0

# TCP connections
cat /proc/net/tcp | head -5
# sl  local_address rem_address   st tx_queue rx_queue ...
#  0: 00000000:0050 00000000:0000 0A 00000000:00000000
#  1: 0100007F:0035 00000000:0000 0A 00000000:00000000

# Socket statistics
cat /proc/net/sockstat
# sockets: used 1234
# TCP: inuse 567 orphan 12 tw 234 alloc 789 mem 1234
# UDP: inuse 234 mem 567
# UDPLITE: inuse 0
# RAW: inuse 0
# FRAG: inuse 0 memory 0

# TCP extended statistics
cat /proc/net/netstat | head -10
# TcpExt: SyncookiesSent SyncookiesRecv SyncookiesFailed ...
# TcpExt: 0 0 0 ...

# SNMP counters
cat /proc/net/snmp | head -10
# Ip: Forwarding DefaultTTL InReceives InHdrErrors ...
# Ip: 1 64 123456789 0 ...
```

### Network Troubleshooting with /proc/net

```bash
# Count connections by state
awk '{print $4}' /proc/net/tcp | sort | uniq -c | sort -rn
#  3456 01  # ESTABLISHED
#   234 06  # TIME_WAIT
#    56 08  # CLOSE_WAIT
#    12 0A  # LISTEN

# Find connections to specific port (e.g., 80 = 0050)
grep ":0050" /proc/net/tcp

# Check for socket buffer overflows
grep -E "TcpExt:.*Overflows" /proc/net/netstat
# TcpExt: ... TCPBacklogDrop ListenOverflows ListenDrops ...
# TcpExt: ... 0 0 0 ...

# Check for retransmissions
grep "Tcp:" /proc/net/snmp | tail -1
# Tcp: ... RetransSegs ...
```

## /proc/sys: Kernel Parameters

```bash
# View all sysctl parameters
ls /proc/sys/
# abi/  debug/  dev/  fs/  kernel/  net/  vm/

# VM parameters
ls /proc/sys/vm/
# dirty_background_bytes    dirty_expire_centisecs  min_free_kbytes
# dirty_background_ratio    dirty_ratio             nr_hugepages
# dirty_bytes               dirty_writeback_centisecs  overcommit_memory
# vfs_cache_pressure        swappiness              overcommit_ratio

# Network parameters
ls /proc/sys/net/core/
# netdev_budget  netdev_max_backlog  rmem_max  somaxconn  wmem_max

# Kernel parameters
ls /proc/sys/kernel/
# pid_max  sched_latency_ns  sched_min_granularity_ns  threads-max
```

### Key sysctl Parameters

```bash
# ──── Memory Management ────
cat /proc/sys/vm/swappiness
# 60 (0-100, lower = less swapping)

cat /proc/sys/vm/dirty_ratio
# 20 (percentage of memory allowed dirty before writeback)

cat /proc/sys/vm/overcommit_memory
# 0 (0=heuristic, 1=always, 2=strict)

cat /proc/sys/vm/min_free_kbytes
# 67584 (minimum free memory in KB)

# ──── Network ────
cat /proc/sys/net/core/somaxconn
# 4096 (max listen queue backlog)

cat /proc/sys/net/core/rmem_max
# 212992 (max receive buffer size)

cat /proc/sys/net/ipv4/tcp_max_syn_backlog
# 4096 (max SYN backlog)

cat /proc/sys/net/ipv4/ip_local_port_range
# 32768    60999 (ephemeral port range)

# ──── Kernel ────
cat /proc/sys/kernel/pid_max
# 4194304 (max PID value)

cat /proc/sys/kernel/threads-max
# 123456 (max threads system-wide)

cat /proc/sys/kernel/sched_latency_ns
# 6000000 (target scheduling latency)
```

### Modifying Parameters

```bash
# Temporary (until reboot)
echo 10 > /proc/sys/vm/swappiness
echo 4096 > /proc/sys/net/core/somaxconn

# Permanent (via sysctl.conf)
echo "vm.swappiness = 10" >> /etc/sysctl.conf
sysctl -p

# Check current values
sysctl -a | grep swappiness
# vm.swappiness = 10
```

## /proc Load Average and Uptime

```bash
# Load average
cat /proc/loadavg
# 5.67 4.32 3.21 4/1234 5678
# 1-min 5-min 15-min running/total last_pid

# Uptime
cat /proc/uptime
# 3628800.45 29030400.36
# uptime_seconds idle_seconds (across all CPUs)

# System boot time
date -d "$(awk '{print $1}' /proc/stat | grep btime | cut -d' ' -f2)"
# Mon Jul 22 10:00:00 CST 2026
```

## /proc Interrupts and Softirqs

```bash
# Hardware interrupts
cat /proc/interrupts | head -5
#            CPU0       CPU1       CPU2       CPU3
#   1:         42         0         0         0   IO-APIC   2-edge      timer
#   8:          0         0         0         1   IO-APIC   8-edge      rtc0
#  16:   12345678   23456789   34567890   45678901   PCI-MSI  524289-edge  eth0

# Soft interrupts
cat /proc/softirqs | head -5
#                     CPU0       CPU1       CPU2       CPU3
#          HI:          42         56         78         90
#       TIMER:    12345678   23456789   34567890   45678901
#      NET_TX:    12345678   23456789   34567890   45678901
#      NET_RX:    12345678   23456789   34567890   45678901

# Check for interrupt imbalance
awk 'NR>1 && $2+$3+$4+$5 > 0 {print $1, $2+$3+$4+$5}' /proc/interrupts | sort -k2 -rn | head
# Shows which interrupts are most active

# Check for softirq pressure
awk 'NR>1 {sum=0; for(i=2;i<=NF;i++) sum+=$i; print $1, sum}' /proc/softirqs | sort -k2 -rn
```

## /proc CPU Information

```bash
cat /proc/cpuinfo | head -20
# processor	: 0
# vendor_id	: GenuineIntel
# cpu family	: 6
# model		: 85
# model name	: Intel(R) Xeon(R) Gold 6248 CPU @ 2.50GHz
# stepping	: 7
# microcode	: 0x5003604
# cpu MHz		: 2500.000
# cache size	: 27648 KB
# physical id	: 0
# siblings	: 16
# core id		: 0
# cpu cores	: 8
# apicid		: 0
# initial apicid	: 0
# fpu		: yes
# fpu_exception	: yes
# cpuid level	: 22
# wp		: yes
# flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr ...

# Count CPUs
grep -c processor /proc/cpuinfo
# 16

# Check CPU flags (features)
grep flags /proc/cpuinfo | head -1
# flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr ...

# Check for specific features
grep -o "sse4_2\|avx2\|avx512\|aes" /proc/cpuinfo | sort -u
# aes
# avx2
# sse4_2

# Check CPU vulnerabilities
grep . /sys/devices/system/cpu/vulnerabilities/*
# /sys/devices/system/cpu/vulnerabilities/meltdown: Mitigation: PTI
# /sys/devices/system/cpu/vulnerabilities/spectre_v1: Mitigation: ...
# /sys/devices/system/cpu/vulnerabilities/spectre_v2: Mitigation: ...
# /sys/devices/system/cpu/vulnerabilities/retbleed: Mitigation: ...
```

## Practical Monitoring Scripts

### Real-Time CPU Monitor

```bash
#!/bin/bash
# Simple CPU monitor reading /proc/stat
while true; do
    cpu1=$(head -1 /proc/stat)
    sleep 1
    cpu2=$(head -1 /proc/stat)

    idle1=$(echo $cpu1 | awk '{print $5}')
    idle2=$(echo $cpu2 | awk '{print $5}')
    total1=$(echo $cpu1 | awk '{s=0; for(i=2;i<=NF;i++) s+=$i; print s}')
    total2=$(echo $cpu2 | awk '{s=0; for(i=2;i<=NF;i++) s+=$i; print s}')

    idle=$((idle2 - idle1))
    total=$((total2 - total1))
    cpu=$((100 * (total - idle) / total))

    echo "$(date +%H:%M:%S) CPU: ${cpu}%"
done
```

### Process Memory Monitor

```bash
#!/bin/bash
# Monitor process memory via /proc
PID=$1
if [ -z "$PID" ]; then
    echo "Usage: $0 <pid>"
    exit 1
fi

while true; do
    if [ -f /proc/$PID/status ]; then
        rss=$(grep VmRSS /proc/$PID/status | awk '{print $2}')
        vmsize=$(grep VmSize /proc/$PID/status | awk '{print $2}')
        threads=$(grep Threads /proc/$PID/status | awk '{print $2}')
        fd_count=$(ls /proc/$PID/fd 2>/dev/null | wc -l)
        echo "$(date +%H:%M:%S) RSS: ${rss}kB VSZ: ${vmsize}kB Threads: ${threads} FDs: ${fd_count}"
    else
        echo "Process $PID not found"
        break
    fi
    sleep 1
done
```

### System Health Dashboard

```bash
#!/bin/bash
# Quick system health check from /proc
echo "=== System Health ==="
echo ""

# Load average
read load1 load5 load15 _ _ < /proc/loadavg
echo "Load: $load1 (1m) $load5 (5m) $load15 (15m)"

# Memory
mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
mem_avail=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
mem_pct=$((100 * (mem_total - mem_avail) / mem_total))
echo "Memory: ${mem_pct}% used ($(( mem_avail / 1024 ))MB available)"

# Swap
swap_total=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
swap_free=$(grep SwapFree /proc/meminfo | awk '{print $2}')
if [ $swap_total -gt 0 ]; then
    swap_pct=$((100 * (swap_total - swap_free) / swap_total))
    echo "Swap: ${swap_pct}% used"
fi

# Disk I/O (sda)
read _ _ _ r1 _ _ _ w1 _ _ _ _ _ _ < <(grep " sda " /proc/diskstats)
sleep 1
read _ _ _ r2 _ _ _ w2 _ _ _ _ _ _ < <(grep " sda " /proc/diskstats)
iops=$(( r2 - r1 + w2 - w1 ))
echo "Disk IOPS: $iops (sda)"

# Network (eth0)
read _ rx1 _ _ _ _ _ _ tx1 _ < <(grep "eth0:" /proc/net/dev | tr ':' ' ')
sleep 1
read _ rx2 _ _ _ _ _ _ tx2 _ < <(grep "eth0:" /proc/net/dev | tr ':' ' ')
rx_kb=$(( (rx2 - rx1) / 1024 ))
tx_kb=$(( (tx2 - tx1) / 1024 ))
echo "Network: RX ${rx_kb}KB/s TX ${tx_kb}KB/s"

# Process count
echo "Processes: $(ls -d /proc/[0-9]* 2>/dev/null | wc -l)"

# Uptime
uptime_secs=$(awk '{print int($1)}' /proc/uptime)
echo "Uptime: $((uptime_secs / 86400))d $((uptime_secs % 86400 / 3600))h"
```

### Top Processes by Memory

```bash
#!/bin/bash
# Top 10 processes by RSS
echo "Top 10 processes by memory (RSS):"
echo "PID      RSS(kB)  VSZ(kB)  COMMAND"
for pid in /proc/[0-9]*; do
    p=$(basename $pid)
    if [ -f "$pid/status" ]; then
        rss=$(grep VmRSS $pid/status 2>/dev/null | awk '{print $2}')
        vsz=$(grep VmSize $pid/status 2>/dev/null | awk '{print $2}')
        cmd=$(cat $pid/comm 2>/dev/null)
        if [ -n "$rss" ]; then
            echo "$p $rss $vsz $cmd"
        fi
    fi
done | sort -k2 -rn | head -10 | column -t
```

### Finding Memory Leaks

```bash
#!/bin/bash
# Monitor RSS growth for a process
PID=$1
INTERVAL=5
echo "Monitoring PID $PID for memory growth (Ctrl-C to stop)"
echo "Time         RSS(kB)    Growth"

prev_rss=0
while true; do
    if [ -f /proc/$PID/status ]; then
        rss=$(grep VmRSS /proc/$PID/status | awk '{print $2}')
        growth=$((rss - prev_rss))
        echo "$(date +%H:%M:%S)    $rss    +${growth}kB"
        prev_rss=$rss
    else
        echo "Process $PID exited"
        break
    fi
    sleep $INTERVAL
done
```

## How Monitoring Tools Use /proc

| Tool | /proc Files Used |
|------|-----------------|
| `top` | `/proc/stat`, `/proc/[pid]/stat`, `/proc/[pid]/status`, `/proc/meminfo` |
| `free` | `/proc/meminfo` |
| `ps` | `/proc/[pid]/stat`, `/proc/[pid]/status`, `/proc/[pid]/cmdline` |
| `vmstat` | `/proc/stat`, `/proc/meminfo`, `/proc/diskstats` |
| `iostat` | `/proc/diskstats` |
| `sar` | `/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/proc/net/dev` |
| `netstat` | `/proc/net/tcp`, `/proc/net/tcp6`, `/proc/net/unix` |
| `ss` | `/proc/net/tcp`, `/proc/net/tcp6`, `/proc/net/unix` |
| `lsof` | `/proc/[pid]/fd/` |
| `pmap` | `/proc/[pid]/maps`, `/proc/[pid]/smaps` |
| `uptime` | `/proc/loadavg`, `/proc/uptime` |
| `nproc` | `/proc/cpuinfo` |
| `df` | `/proc/mounts` |

## /proc for Security and Auditing

```bash
# Check process capabilities
cat /proc/1/status | grep Cap
# CapInh: 0000000000000000
# CapPrm: 0000003fffffffff
# CapEff: 0000003fffffffff
# CapBnd: 0000003fffffffff
# CapAmb: 0000000000000000

# Decode capabilities
capsh --decode=0000003fffffffff

# Check seccomp status
cat /proc/1/status | grep Seccomp
# Seccomp:    0 (disabled)
# Seccomp_filters:    0

# Check namespaces
ls -la /proc/1/ns/
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 cgroup -> 'cgroup:[4026531835]'
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 ipc -> 'ipc:[4026531839]'
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 mnt -> 'mnt:[4026531840]'
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 net -> 'net:[4026531969]'
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 pid -> 'pid:[4026531836]'
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 user -> 'user:[4026531837]'
# lrwxrwxrwx 1 root root 0 Jul 22 10:00 uts -> 'uts:[4026531838]'

# Check OOM score
cat /proc/1/oom_score
# 0

# Check cgroup membership
cat /proc/1/cgroup
# 0::/init.scope

# Audit: find processes with elevated capabilities
for pid in /proc/[0-9]*; do
    cap=$(grep CapEff $pid/status 2>/dev/null | awk '{print $2}')
    if [ "$cap" != "0000000000000000" ] && [ -n "$cap" ]; then
        echo "$(basename $pid): $(cat $pid/comm 2>/dev/null) CapEff=$cap"
    fi
done
```

## References

- [proc(5) man page](https://man7.org/linux/man-pages/man5/proc.5.html)
- [Linux Kernel Documentation: /proc](https://www.kernel.org/doc/html/latest/filesystems/proc.html)
- [Understanding /proc](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/)

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- <https://man7.org/linux/man-pages/man5/proc.5.html> — Complete proc(5) reference
- <https://www.kernel.org/doc/html/latest/filesystems/proc.html> — Kernel proc documentation
- <https://www.brendangregg.com/linuxperf.html> — Linux performance tools

## Related Topics

- [Observability Overview](overview.md)
- [sysfs](sysfs.md)
- [Metrics Collection](metrics.md)
- [BPF and bpftrace](bpf-bpftrace.md)
