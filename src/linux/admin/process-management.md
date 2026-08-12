# Process Management

## Introduction

Process management is one of the most frequent tasks in Linux system administration. Understanding how to list, monitor, prioritize, and control processes is essential for maintaining system health, debugging issues, and managing resources effectively. Every running program on Linux is a process, and the kernel provides a rich set of tools for inspecting and controlling them.

## Listing Processes

### `ps` — Process Snapshot

The `ps` command shows a snapshot of current processes. Its syntax varies between BSD and System V styles:

```bash
# BSD style (no dash)
ps aux
# USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
# root         1  0.0  0.0 169436 13264 ?        Ss   Jul15   0:45 /sbin/init
# root         2  0.0  0.0      0     0 ?        S    Jul15   0:00 [kthreadd]
# root       456  0.0  0.0  72308  5684 ?        Ss   Jul15   1:23 /usr/sbin/sshd
# www-data   789  0.5  1.2 234567 45678 ?        Sl   Jul20  12:34 /usr/sbin/nginx
# postgres  1024  2.3  4.5 987654 123456 ?       Ssl  Jul15  45:67 /usr/lib/postgres

# System V style (with dash)
ps -ef
# UID        PID  PPID  C STIME TTY          TIME CMD
# root         1     0  0 Jul15 ?        00:00:45 /sbin/init
# root         2     0  0 Jul15 ?        00:00:00 [kthreadd]

# Process tree (BSD style)
ps auxf
# Shows parent-child relationships with tree formatting

# Process tree (System V style)
ps -ejH
# Or with forest format
ps -eo pid,ppid,stat,comm --forest
#   PID  PPID STAT COMMAND
#     1     0 Ss   systemd
#   456     1 Ss   └─ sshd
#   789   456 Ss       └─ sshd
#  1024   789 S            └─ bash
#  2048  1024 R                └─ ps

# Custom output format
ps -eo pid,ppid,user,%cpu,%mem,vsz,rss,tty,stat,start,time,comm
# PID  PPID USER     %CPU %MEM    VSZ   RSS TT       STAT  STARTED     TIME COMMAND

# Threads
ps -eLf
# Shows LWP (lightweight process = thread) column

# Show environment of a process
ps eww -p 1234

# Show command line arguments
ps -p 1234 -o args=
# /usr/sbin/nginx -g daemon off;

# Find processes by name
ps -C nginx
ps aux | grep nginx

# Top CPU consumers
ps aux --sort=-%cpu | head -10

# Top memory consumers
ps aux --sort=-%mem | head -10

# Show elapsed time
ps -eo pid,etime,comm | sort -k2 -r | head -10
#   PID     ELAPSED COMMAND
#     1    7-02:15:30 systemd
#   456    7-02:15:30 sshd
```

### `ps` Output Columns Explained

| Column | Description |
|--------|-------------|
| `PID` | Process ID |
| `PPID` | Parent process ID |
| `USER` | Process owner |
| `%CPU` | CPU usage percentage |
| `%MEM` | Memory usage percentage |
| `VSZ` | Virtual memory size (KB) |
| `RSS` | Resident set size (physical memory, KB) |
| `TTY` | Controlling terminal (? = none) |
| `STAT` | Process state |
| `START` | Start time |
| `TIME` | Cumulative CPU time |

### Process States (STAT)

| State | Code | Description |
|-------|------|-------------|
| Running | `R` | Running or runnable |
| Sleeping | `S` | Interruptible sleep |
| Disk sleep | `D` | Uninterruptible sleep (usually I/O) |
| Stopped | `T` | Stopped by signal |
| Zombie | `Z` | Terminated, waiting for parent to reap |
| Traced | `t` | Stopped by debugger |
| Dead | `X` | Dead (should never be seen) |

**Modifier flags:**
- `s` — Session leader
- `+` — Foreground process group
- `l` — Multi-threaded
- `<` — High priority (nice < 0)
- `N` — Low priority (nice > 0)

## Real-Time Monitoring

### `top`

```bash
top
# top - 14:32:01 up 7 days,  2:15,  1 user,  load average: 0.50, 0.75, 0.80
# Tasks: 234 total,   2 running, 232 sleeping,   0 stopped,   0 zombie
# %Cpu(s):  5.2 us,  1.3 sy,  0.0 ni, 92.8 id,  0.5 wa,  0.0 hi,  0.2 si,  0.0 st
# MiB Mem :  16384.0 total,   8192.0 free,   4096.0 used,   4096.0 buff/cache
# MiB Swap:   4096.0 total,   4096.0 free,      0.0 used.  11264.0 avail Mem
#
#   PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
#  1234 postgres  20   0  987654 123456  12345 S   5.2   0.7  45:67.89 postgres
#  5678 www-data  20   0  234567  45678   5678 R   2.1   0.3  12:34.56 nginx

# Interactive commands in top:
# 1      — Toggle individual CPU cores
# M      — Sort by memory
# P      — Sort by CPU (default)
# T      — Sort by time
# k      — Kill a process (enter PID)
# r      — Renice a process
# f      — Select display fields
# c      — Show full command line
# H      — Show threads
# V      — Forest view (tree)
# W      — Save configuration
```

### `htop`

`htop` is an enhanced interactive process viewer:

```bash
htop
# Features:
# - Color-coded display
# - Mouse support
# - Tree view (F5)
# - Search (F3) and filter (F4)
# - Sort by various columns (F6)
# - Kill processes with signals (F9)
# - Nice adjustment (F7/F8)

# Configuration stored in ~/.config/htop/htoprc
```

### `btop` / `glances` — Modern Alternatives

```bash
# btop — Beautiful system monitor
btop

# glances — Comprehensive system monitoring
glances
glances -w  # Web interface on port 61208
```

## Process Signals

### Signal Types

```bash
# List all signals
kill -l
#  1) SIGHUP       2) SIGINT       3) SIGQUIT      4) SIGILL
#  5) SIGTRAP      6) SIGABRT      7) SIGBUS       8) SIGFPE
#  9) SIGKILL     10) SIGUSR1     11) SIGSEGV     12) SIGUSR2
# 13) SIGPIPE     14) SIGALRM     15) SIGTERM     16) SIGSTKFLT
# 17) SIGCHLD     18) SIGCONT     19) SIGSTOP     20) SIGTSTP
# 21) SIGTTIN     22) SIGTTOU     23) SIGURG      24) SIGXCPU
# 25) SIGXFSZ     26) SIGVTALRM   27) SIGPROF     28) SIGWINCH
# 29) SIGIO       30) SIGPWR      31) SIGSYS      34) SIGRTMIN
```

### Common Signals

| Signal | Number | Default Action | Description |
|--------|--------|---------------|-------------|
| `SIGHUP` | 1 | Terminate | Hangup (reload config for daemons) |
| `SIGINT` | 2 | Terminate | Interrupt (Ctrl+C) |
| `SIGQUIT` | 3 | Core dump | Quit (Ctrl+\\) |
| `SIGKILL` | 9 | Terminate | Force kill (uncatchable) |
| `SIGTERM` | 15 | Terminate | Graceful termination (default for `kill`) |
| `SIGSTOP` | 19 | Stop | Pause process (uncatchable) |
| `SIGCONT` | 18 | Continue | Resume stopped process |
| `SIGUSR1` | 10 | Terminate | User-defined (often reopen logs) |
| `SIGUSR2` | 12 | Terminate | User-defined |

### Sending Signals

```bash
# Send SIGTERM (default, graceful)
kill 1234
kill -15 1234
kill -TERM 1234

# Send SIGKILL (force kill)
kill -9 1234
kill -KILL 1234

# Send SIGHUP (reload config)
kill -HUP 1234
# Most daemons: nginx, sshd, etc. reload config on HUP

# Send to process group
kill -TERM -1234    # Negative PID = process group

# Send to all processes (DANGEROUS)
kill -TERM -1       # All processes you can signal
killall -TERM nginx # All processes named nginx

# pkill — kill by pattern
pkill -f "python.*myapp"  # Match full command line
pkill -u myuser            # All processes of user

# killall — kill by name
killall nginx              # Kill all nginx processes
killall -s HUP nginx       # Send HUP to all nginx

# Signal handling in scripts
trap 'echo "Caught SIGTERM, cleaning up..."; exit' TERM
trap 'echo "Caught SIGINT"; exit' INT
```

## Process Priority with `nice` and `renice`

```bash
# Start with lower priority (higher nice value)
nice -n 10 ./cpu_intensive_job

# Start with higher priority (needs root)
nice -n -5 ./critical_service

# Change priority of running process
renice 15 -p 1234              # Set PID 1234 to nice 15
renice -5 -p 1234              # Needs root for negative nice
renice 10 -u myuser            # All processes of myuser
renice 10 -g mygroup           # All processes in group

# View nice values
ps -eo pid,ni,comm | head -10
#   PID  NI COMMAND
#     1   0 systemd
#   456  10 batch_job
#   789 -10 critical_svc

# I/O priority
ionice -c 3 ./backup.sh        # Idle I/O class
ionice -c 2 -n 7 ./batch_job   # Best-effort, lowest priority
ionice -p 1234                  # Check I/O priority of PID

# Real-time priority (needs root/capability)
chrt -f 50 ./realtime_app      # SCHED_FIFO priority 50
chrt -r 30 ./realtime_app      # SCHED_RR priority 30
chrt -p 1234                    # Check scheduling policy

# See Process Priorities page for full details
```

## systemd Process Management

### systemd-cgtop

```bash
# Real-time cgroup resource monitoring
systemd-cgtop
# Control Group                        Tasks   %CPU   Memory  Input/s Output/s
# /                                      678    5.2     4.0G   100K    200K
# /system.slice                           45    2.1     1.2G    50K    100K
# /system.slice/postgresql.service        12    1.5     800M    30K     80K
# /system.slice/nginx.service              8    0.5     200M    10K     50K
# /user.slice                             23    0.3     500M     5K     20K
```

### systemd Resource Controls

```bash
# View service cgroup
systemctl show nginx.service | grep -E "^(CPU|Memory|Tasks|IO)"
# CPUShares=18446744073709551615
# MemoryMax=18446744073709551615
# TasksMax=4915

# Set runtime limits
systemctl set-property nginx.service CPUQuota=50%
systemctl set-property nginx.service MemoryMax=512M
systemctl set-property nginx.service TasksMax=100

# Persistent limits (in unit file)
# [Service]
# CPUQuota=50%
# MemoryMax=512M
# MemoryHigh=384M
# IOWeight=100
# TasksMax=100
```

### Service Management

```bash
# Start/stop/restart
systemctl start nginx
systemctl stop nginx
systemctl restart nginx
systemctl reload nginx       # Reload config without restart

# Status
systemctl status nginx
# ● nginx.service - A high performance web server
#      Loaded: loaded (/lib/systemd/system/nginx.service; enabled)
#      Active: active (running) since Mon 2025-07-21 10:00:00 UTC; 4h ago
#    Main PID: 789 (nginx)
#       Tasks: 3 (limit: 4915)
#      Memory: 12.5M
#         CPU: 1.234s
#      CGroup: /system.slice/nginx.service
#              ├─789 "nginx: master process /usr/sbin/nginx"
#              ├─790 "nginx: worker process"
#              └─791 "nginx: worker process"

# Enable/disable (start on boot)
systemctl enable nginx
systemctl disable nginx

# List failed services
systemctl --failed

# List all services
systemctl list-units --type=service

# View logs
journalctl -u nginx --since "1 hour ago"
journalctl -u nginx -f  # Follow
```

## Advanced Process Inspection

### `strace` — System Call Tracing

```bash
# Trace system calls of a running process
strace -p 1234

# Trace a new command
strace ls /tmp

# Show only specific syscalls
strace -e trace=open,read,write -p 1234

# Count syscalls
strace -c ls /tmp
# % time     seconds  usecs/call     calls    errors syscall
# ------ ----------- ----------- --------- --------- ----------------
#  50.00    0.001000         100        10           read
#  30.00    0.000600          60        10           write
#  20.00    0.000400          40        10           open

# Show timestamps
strace -T -p 1234  # Time spent in each syscall

# Trace child processes
strace -f -p 1234

# Output to file
strace -o trace.log -p 1234
```

### `lsof` — Open Files

```bash
# All open files
lsof

# Files opened by process
lsof -p 1234

# Processes using a file
lsof /var/log/syslog

# Network connections
lsof -i :80
lsof -i tcp:443
lsof -i -P -n  # All network, numeric

# Files opened by user
lsof -u myuser

# Count open files per process
lsof | awk '{print $2}' | sort | uniq -c | sort -rn | head

# Check file descriptor limits
lsof -p 1234 | wc -l
cat /proc/1234/limits | grep "open files"
# Max open files            1024                 1048576              files
```

### `/proc` Filesystem

```bash
# Process details
cat /proc/1234/status     # Process status summary
cat /proc/1234/cmdline    # Command line (null-separated)
cat /proc/1234/environ    # Environment variables
cat /proc/1234/limits     # Resource limits
cat /proc/1234/maps       # Memory mappings
cat /proc/1234/fd/        # Open file descriptors
ls -la /proc/1234/fd/     # Show what FDs point to
cat /proc/1234/io         # I/O statistics
cat /proc/1234/stat       # Detailed process stats
cat /proc/1234/sched      # Scheduler statistics

# System-wide
cat /proc/cpuinfo         # CPU information
cat /proc/meminfo         # Memory information
cat /proc/loadavg         # Load average
cat /proc/uptime          # Uptime
cat /proc/stat            # CPU statistics
```

## Process Management Workflow

```mermaid
graph TD
    A["Identify issue"] --> B["ps aux | grep ..."]
    B --> C{"Process state?"}
    C -->|"Running (high CPU)"| D["top/htop → nice/kill"]
    C -->|"Zombie"| E["Check parent → kill parent"]
    C -->|"D state (stuck I/O)"| F["Check I/O → disk issues"]
    C -->|"Too many processes"| G["cgroup limits / ulimit"]
    D --> H["kill -TERM → wait → kill -9"]
    E --> I["ps -o pid,ppid,stat -p <zombie>"]
    F --> J["iotop, iostat, dmesg"]
    G --> K["systemctl set-property ..."]
    
    style A fill:#e53e3e,color:#fff
    style D fill:#3182ce,color:#fff
    style E fill:#d69e2e,color:#fff
    style F fill:#d69e2e,color:#fff
```

## Cgroups v2 — Modern Resource Control

Linux Control Groups v2 (unified hierarchy) is the modern resource management framework:

### Cgroups v2 Architecture

```mermaid
graph TB
    subgraph Unified_Hierarchy
        ROOT["/sys/fs/cgroup/\n(root cgroup)"]
        SYS["system.slice"]
        USR["user.slice"]
        CUSTOM["custom.slice"]
        NGINX["nginx.service"]
        PG["postgresql.service"]
        APP["myapp.service"]
    end
    ROOT --> SYS
    ROOT --> USR
    ROOT --> CUSTOM
    SYS --> NGINX
    SYS --> PG
    CUSTOM --> APP
```

### Cgroups v2 Filesystem Interface

```bash
# Mount cgroups v2
mount -t cgroup2 none /sys/fs/cgroup

# View cgroup tree
cat /sys/fs/cgroup/cgroup.controllers
# cpuset cpu io memory hugetlb pids rdma misc

# Create a cgroup
mkdir /sys/fs/cgroup/myapp

# Enable controllers for children
echo "+cpu +memory +io +pids" > /sys/fs/cgroup/cgroup.subtree_control

# Assign process to cgroup
echo $PID > /sys/fs/cgroup/myapp/cgroup.procs

# View processes in cgroup
cat /sys/fs/cgroup/myapp/cgroup.procs

# Remove cgroup (must be empty)
rmdir /sys/fs/cgroup/myapp
```

### CPU Controller

```bash
# Set CPU weight (relative share, 1-10000, default 100)
echo 200 > /sys/fs/cgroup/myapp/cpu.weight

# Set CPU max (hard limit)
echo "50000 100000" > /sys/fs/cgroup/myapp/cpu.max
# 50ms per 100ms period = 50% CPU

# CPU pressure (PSI — Pressure Stall Information)
cat /sys/fs/cgroup/myapp/cpu.pressure
# some avg10=2.50 avg60=1.23 avg300=0.89 total=12345678
# full avg10=0.00 avg60=0.00 avg300=0.00 total=0

# Top-level CPU pressure
cat /proc/pressure/cpu
```

### Memory Controller

```bash
# Set memory hard limit (OOM-kill if exceeded)
echo 512M > /sys/fs/cgroup/myapp/memory.max

# Set memory high (throttle, don't kill)
echo 384M > /sys/fs/cgroup/myapp/memory.high

# Set memory low (best-effort protection)
echo 256M > /sys/fs/cgroup/myapp/memory.low

# Swap limit
echo 100M > /sys/fs/cgroup/myapp/memory.swap.max

# View memory usage
cat /sys/fs/cgroup/myapp/memory.current
cat /sys/fs/cgroup/myapp/memory.stat

# Memory pressure
cat /sys/fs/cgroup/myapp/memory.pressure
# some avg10=5.20 avg60=3.10 avg300=1.50 total=98765432
# full avg10=1.20 avg60=0.50 avg300=0.20 total=12345678
```

### I/O Controller

```bash
# Set I/O weight (relative, 1-10000)
echo "default 200" > /sys/fs/cgroup/myapp/io.weight

# Set I/O max (bytes per second)
echo "8:0 rbps=50000000 wbps=25000000" > /sys/fs/cgroup/myapp/io.max
# 8:0 = major:minor device number

# View I/O usage
cat /sys/fs/cgroup/myapp/io.stat
# 8:0 rbytes=123456789 wbytes=987654321 rios=1234 wios=5678
```

### PIDs Controller

```bash
# Limit number of processes in cgroup
echo 100 > /sys/fs/cgroup/myapp/pids.max

# View current PID count
cat /sys/fs/cgroup/myapp/pids.current
```

### systemd Integration with cgroups v2

```bash
# systemd uses cgroups v2 by default (unified hierarchy)
systemd-cgls          # Show cgroup tree
systemd-cgtop         # Real-time cgroup monitoring

# Set resource limits via systemd
systemctl set-property myapp.service CPUQuota=50%
systemctl set-property myapp.service MemoryMax=512M
systemctl set-property myapp.service IOReadBandwidthMax="/dev/sda 50M"

# Persistent limits in unit file:
# [Service]
# CPUQuota=50%
# CPUWeight=200
# MemoryMax=512M
# MemoryHigh=384M
# MemoryLow=256M
# IOWeight=200
# TasksMax=100
# AllowedCPUs=0-3

# Delegate cgroup to user (unprivileged resource control)
systemctl set-property user-1000.slice Delegate=yes
```

## Zombie Processes

Zombies are terminated processes whose parent hasn't called `wait()`. They consume no resources but waste PID space:

```bash
# Find zombie processes
ps aux | awk '$8 == "Z" {print}'
# Or:
ps -eo pid,ppid,stat,comm | grep ' Z '

# Zombie state: Z (zombie) or Z+ (zombie, foreground)

# Why zombies exist:
# 1. Parent process didn't call wait()/waitpid()
# 2. Parent is busy or buggy
# 3. Parent is in D state (uninterruptible sleep)

# Clean up zombies:

# Method 1: Signal parent to reap children
kill -SIGCHLD <PPID>

# Method 2: Kill parent (zombie re-parented to init, which reaps)
kill -TERM <PPID>
# If parent is also zombie, try:
kill -9 <PPID>

# Method 3: Find and fix the buggy parent
pstree -p <PPID>
strace -p <PPID> -e trace=process

# Method 4: Re-parent to init (last resort)
# Modern kernels: PR_SET_CHILD_SUBREAPER
prctl(PR_SET_CHILD_SUBREAPER, 1)  # In parent code

# Monitor zombie count
watch -n 1 'ps aux | awk "\$8 == \"Z\" {count++} END {print \"Zombies:\", count+0}"'

# Kernel limit on zombies
sysctl kernel.pid_max  # Max PIDs (default 32768)
```

## Process Accounting

### Kernel Process Accounting

```bash
# Enable process accounting (logs all process exits)
apt install acct
systemctl enable --now acct

# View accounting data
lastcomm              # Show last commands executed
lastcomm -u myuser    # Commands by user
lastcomm -comm=ssh    # Commands by name

# Summary by user
sa -u
# root    0.01 cpu   1234k mem   0 io  156 pts/0
# myuser  0.05 cpu   2345k mem   12 io  89 pts/1

# Summary by command
sa -m
# root     0.02 cpu  1500k mem  5 io
# myuser   0.08 cpu  3000k mem  15 io

# Accounting file
# /var/log/account/pacct (binary format)
# /var/log/account/savacct (summary)
# /var/log/account/usracct (per-user summary)
```

### auditd — Process Auditing

```bash
# Enable audit rules for process tracking
auditctl -a always,exit -F arch=b64 -S execve -k process_exec

# Search audit logs
ausearch -k process_exec -ts today

# Process creation/destruction
ausearch -m USER_START,USER_END -ts today
```

## Process Namespaces

Namespaces isolate process views of the system:

```mermaid
graph TB
    subgraph Host
        PID_NS["PID namespace<br>Process IDs"]
        NET_NS["NET namespace<br>Network stack"]
        MNT_NS["MNT namespace<br>Mount points"]
        USER_NS["USER namespace<br>UID/GID mapping"]
        UTS_NS["UTS namespace<br>Hostname"]
        IPC_NS["IPC namespace<br>Shared memory, semaphores"]
        CGROUP_NS["CGROUP namespace<br>Cgroup root"]
        TIME_NS["TIME namespace<br>System clocks"]
    end
```

### Creating Namespaces

```bash
# Run command in new namespace
unshare --pid --mount --net --uts --ipc --fork /bin/bash

# With user namespace (no root needed)
unshare --user --map-root-user /bin/bash

# Enter existing namespace
nsenter --target $PID --pid --net --mount /bin/bash

# View namespace info
ls -la /proc/$PID/ns/
# lrwxrwxrwx 1 root root 0 ... cgroup -> 'cgroup:[4026531835]'
# lrwxrwxrwx 1 root root 0 ... ipc -> 'ipc:[4026531839]'
# lrwxrwxrwx 1 root root 0 ... mnt -> 'mnt:[4026531841]'
# lrwxrwxrwx 1 root root 0 ... net -> 'net:[4026531969]'
# lrwxrwxrwx 1 root root 0 ... pid -> 'pid:[4026531836]'
# lrwxrwxrwx 1 root root 0 ... user -> 'user:[4026531837]'
# lrwxrwxrwx 1 root root 0 ... uts -> 'uts:[4026531838]'

# Compare namespaces
ls -la /proc/$PID1/ns/ /proc/$PID2/ns/
```

### Practical Namespace Examples

```bash
# Network namespace for isolated network testing
ip netns add testnet
ip netns exec testnet ip addr
ip netns exec testnet ping 8.8.8.8  # Fails — isolated!

# Connect namespaces with veth pair
ip link add veth0 type veth peer name veth1
ip link set veth1 netns testnet
ip addr add 10.0.0.1/24 dev veth0
ip link set veth0 up
ip netns exec testnet ip addr add 10.0.0.2/24 dev veth1
ip netns exec testnet ip link set veth1 up

# Mount namespace for isolated testing
unshare --mount /bin/bash
mount -t tmpfs tmpfs /tmp  # Only visible in this namespace

# PID namespace
unshare --pid --fork /bin/bash
echo $$  # PID 1 in new namespace!
ps aux   # Only sees processes in this namespace
```

## Resource Limits with `ulimit` and `prlimit`

```bash
# View current limits
ulimit -a
# core file size          (blocks, -c) 0
# data seg size           (kbytes, -d) unlimited
# scheduling priority             (-e) 0
# file size               (blocks, -f) unlimited
# max locked memory       (kbytes, -l) 64
# max memory size         (kbytes, -m) unlimited
# open files                      (-n) 1024
# pipe size            (512 bytes, -p) 8
# POSIX message queues     (bytes, -q) 819200
# real-time priority              (-r) 0
# stack size              (kbytes, -s) 8192
# cpu time               (seconds, -t) unlimited
# max user processes              (-u) 15677
# virtual memory          (kbytes, -v) unlimited
# file locks                      (-x) unlimited

# Set limits for current shell
ulimit -n 65536   # Open files
ulimit -u 4096    # Max processes

# Permanently in /etc/security/limits.conf:
# myuser  soft  nofile  65536
# myuser  hard  nofile  131072
# myuser  soft  nproc   4096
# myuser  hard  nproc   8192

# View/set limits for running process
prlimit -p $PID
prlimit -p $PID --nofile=65536:131072

# /proc interface
cat /proc/$PID/limits
# Limit                     Soft Limit Hard Limit
# Max cpu time              unlimited  unlimited
# Max file size             unlimited  unlimited
# Max data size             unlimited  unlimited
# Max stack size            8388608    unlimited
# Max core file size        0          unlimited
# Max resident set          unlimited  unlimited
# Max processes             15677      15677
# Max open files            1024       1048576
# Max locked memory         67108864   67108864
```

## Process Security Features

### seccomp — System Call Filtering

```bash
# List syscalls used by a process
strace -c -p $PID 2>&1 | tail -20

# Create seccomp filter (sandboxing)
# Using bwrap (bubblewrap) for sandboxing:
bwrap --ro-bind / / --dev /dev --proc /proc \
    --unshare-all --die-with-parent \
    /usr/bin/myapp

# systemd service with seccomp
# [Service]
# SystemCallFilter=@system-service
# SystemCallArchitectures=native
# MemoryDenyWriteExecute=yes
# ProtectSystem=strict
# ProtectHome=yes
```

### Capabilities

```bash
# View process capabilities
capsh --print
cat /proc/$PID/status | grep Cap

# Drop capabilities from a process
setcap cap_net_raw+ep /usr/bin/myapp

# Run with minimal capabilities
capsh --drop=all -- -c "./myapp"

# systemd service with capabilities
# [Service]
# CapabilityBoundingSet=CAP_NET_BIND_SERVICE
# AmbientCapabilities=CAP_NET_BIND_SERVICE
# NoNewPrivileges=yes
```

## Process Debugging Deep Dive

### GDB Attach to Running Process

```bash
# Attach GDB to running process (for debugging hangs)
gdb -p $PID
(gdb) bt           # Backtrace
(gdb) thread apply all bt  # All threads backtrace
(gdb) info threads
(gdb) thread 3
(gdb) bt
(gdb) detach

# Generate core dump without killing
gcore $PID
# Creates core.$PID file
```

### `/proc` Filesystem Deep Dive

```bash
# Process memory map
wc -l /proc/$PID/maps  # Number of memory regions
pmap -x $PID           # Detailed memory map

# Process memory usage details
cat /proc/$PID/statm
# total resident shared text lib data dt (pages)

# Process I/O statistics
cat /proc/$PID/io
# rchar: 1234567890
# wchar: 987654321
# syscr: 12345
# syscw: 6789
# read_bytes: 0
# write_bytes: 0
# cancelled_write_bytes: 0

# Process status details
cat /proc/$PID/status
# Name:   myapp
# Umask:  0022
# State:  S (sleeping)
# Tgid:   1234
# Ngid:   0
# Pid:    1234
# PPid:   567
# TracerPid: 0
# FDSize: 64
# Groups: 1000 1001
# VmPeak: 2345678 kB
# VmSize: 1234567 kB
# VmRSS:   123456 kB
# voluntary_ctxt_switches: 12345
# nonvoluntary_ctxt_switches: 678

# Process mount namespace info
cat /proc/$PID/mountinfo

# Process network connections
cat /proc/$PID/net/tcp
# Or: ss -p | grep $PID
```

## References

- [ps(1) man page](https://man7.org/linux/man-pages/man1/ps.1.html)
- [top(1) man page](https://man7.org/linux/man-pages/man1/top.1.html)
- [kill(1) man page](https://man7.org/linux/man-pages/man1/kill.1.html)
- [strace(1) man page](https://man7.org/linux/man-pages/man1/strace.1.html)
- [lsof(8) man page](https://man7.org/linux/man-pages/man8/lsof.8.html)
- [proc(5) man page](https://man7.org/linux/man-pages/man5/proc.5.html)

## Related Topics

- [Process Priorities](../kernel/processes/priorities.md) — Nice values, RT scheduling
- [Cgroups](../kernel/processes/cgroups.md) — Resource control
- [Process Groups](../kernel/processes/process-groups.md) — Sessions and job control
- [System Administration Overview](./overview.md) — Monitoring practices
