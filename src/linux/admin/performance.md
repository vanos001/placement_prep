# Performance Monitoring

Performance monitoring is the cornerstone of Linux system administration. Without
visibility into CPU, memory, disk I/O, and network behaviour, tuning is guesswork.
This chapter surveys the classic `sysstat` family of tools—`vmstat`, `iostat`,
`sar`, `mpstat`, `pidstat`—alongside the modern `dstat` aggregator, and ties them
together into a repeatable analysis workflow.

---

## 1. Overview of Tools

| Tool | Scope | Typical Interval | Output |
|------|-------|-------------------|--------|
| `vmstat` | CPU, memory, swap, I/O | 1 s | Tabular |
| `iostat` | Block-device I/O | 1 s | Per-device |
| `mpstat` | Per-CPU breakdown | 1 s | Per-core |
| `pidstat` | Per-process | 1 s | Per-PID |
| `sar` | Historical + live | 10 min (cron) | Multi-metric |
| `dstat` | Aggregated live view | 1 s | Colour-coded |

All except `dstat` ship with the **sysstat** package. Install on Debian/Ubuntu with:

```bash
sudo apt install sysstat dstat
```

Enable the `sar` data collector:

```bash
sudo systemctl enable --now sysstat
```

---

## 2. vmstat — Virtual Memory Statistics

`vmstat` prints a one-line summary of system activity since boot (or since the
last sample when given an interval).

```bash
vmstat 1 5          # 1-second interval, 5 samples
```

### Interpreting the Columns

```
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 1  0      0 512000  64000 2048000    0    0     0     0  200  400  5  2 92  1  0
```

| Column | Meaning |
|--------|---------|
| `r` | Runnable processes (waiting for CPU) |
| `b` | Blocked (waiting for I/O) |
| `swpd` | Swap used (KB) |
| `si/so` | Swap in / Swap out (KB/s) |
| `bi/bo` | Blocks in / Blocks out (KB/s) |
| `in` | Interrupts per second |
| `cs` | Context switches per second |
| `us/sy/id/wa/st` | CPU time: user / system / idle / I/O-wait / stolen |

**Rule of thumb:** If `r` consistently exceeds the number of CPU cores, the system
is CPU-bound. If `b > 0` persistently, storage I/O is the bottleneck.

---

## 3. iostat — Block Device I/O

```bash
iostat -xz 1        # extended stats, skip zero-activity devices
```

Key columns:

- **r/s, w/s** — reads/writes per second
- **rkB/s, wkB/s** — throughput
- **await** — average I/O wait time (ms). SSDs: < 1 ms; HDDs: 5–15 ms
- **%util** — device saturation. > 80 % on SSDs or > 60 % on HDDs signals trouble

```bash
# Show only NVMe devices, human-readable
iostat -xz -p nvme 1
```

---

## 4. mpstat — Per-CPU Statistics

```bash
mpstat -P ALL 1     # all CPUs, 1-second interval
```

Look for:

- **IRQ imbalance** — one core handles most interrupts
- **%soft** — high software-interrupt time suggests network or block-layer pressure

```bash
# Show only CPU 2 and 3
mpstat -P 2,3 1
```

---

## 5. pidstat — Per-Process Breakdown

`pidstat` attaches metrics to individual processes, making it invaluable for
tracing CPU hogs, disk-heavy tasks, or context-switch-heavy applications.

```bash
pidstat 1                   # CPU per process
pidstat -d 1                # disk I/O per process
pidstat -w 1                # context switches
pidstat -t -p 1234 1        # per-thread for PID 1234
```

### Example: Finding the CPU Hog

```bash
pidstat 1 | sort -nr -k3 | head -5
```

---

## 6. sar — System Activity Reporter

`sar` is the Swiss-army knife. It collects metrics via a cron job
(`/etc/cron.d/sysstat`) every 10 minutes and stores them in
`/var/log/sa/sa<DD>`.

### Live vs Historical

```bash
sar -u 1 5              # live CPU, 1-second × 5
sar -u -f /var/log/sa/sa20   # historical: 20th of month
```

### Useful Flags

| Flag | Metric |
|------|--------|
| `-u` | CPU utilisation |
| `-r` | Memory |
| `-b` | I/O |
| `-n DEV` | Network interface stats |
| `-n SOCK` | Socket statistics |
| `-q` | Run queue / load average |
| `-w` | Context switches + forks |

### Trend Analysis with sadf

`sar` data can be exported for graphing:

```bash
sadf -d /var/log/sa/sa20 -- -u > cpu_data.tsv   # TSV for gnuplot
sadf -g /var/log/sa/sa20 -- -r > mem.svg         # SVG graph
```

---

## 7. dstat — The Modern Aggregator

`dstat` replaces `vmstat`, `iostat`, and `ifstat` in one view.

```bash
dstat                    # default: CPU, disk, net, paging, system
dstat -cdnm --disk-util  # CPU + disk + net + memory + disk utilisation
dstat --top-cpu --top-mem --top-io   # top processes
```

### Output to CSV

```bash
dstat -cdnm --output /tmp/dstat.csv 5
```

---

## 8. Analysis Workflow

The following diagram shows a systematic approach to performance investigation.

```mermaid
flowchart TD
    A[Complaint: "System is slow"] --> B{Run vmstat 1 5}
    B -->|High r, low b| C[CPU-bound]
    B -->|High b| D[I/O-bound]
    B -->|High si/so| E[Memory pressure / swapping]
    C --> F[mpstat -P ALL 1]
    F -->|Single hot core| G[Check IRQ affinity / single-threaded app]
    F -->|All cores saturated| H[pidstat 1 → find CPU hog]
    D --> I[iostat -xz 1]
    I -->|%util high| J[pidstat -d 1 → find I/O hog]
    I -->|await high| K[Check scheduler / queue depth]
    E --> L[sar -r 1]
    L -->|Available low| M[Add RAM / tune overcommit]
    L -->|Swap storm| N[Check OOM killer logs]
    H --> O[Tune / fix application]
    J --> O
    G --> O
    K --> O
    M --> O
    N --> O
```

---

## 9. Practical Example: Diagnosing a Web Server Slowdown

A production Nginx server reports high latency. Here is the step-by-step drill.

### Step 1 — System Overview

```bash
vmstat 1 5
```

Output shows `r=8` (4-core machine), `b=0`, `wa=0` → CPU-bound.

### Step 2 — Per-CPU Breakdown

```bash
mpstat -P ALL 1
```

All cores at ~95 % user. No single hot core → multi-threaded workload.

### Step 3 — Top Processes

```bash
pidstat 1 3
```

`php-fpm` processes consuming 40 % each. Code-level investigation needed.

### Step 4 — Historical Trend

```bash
sar -u -f /var/log/sa/sa15
```

CPU usage ramped up since 14:00, correlating with a deploy.

### Step 5 — Verify I/O Is Not the Issue

```bash
iostat -xz 1
```

`%util` < 20 %, `await` < 2 ms. I/O is healthy.

**Conclusion:** A code change in the 14:00 deploy introduced a CPU-intensive loop.

---

## 10. Beyond sysstat: Modern Alternatives

### perf

```bash
perf stat -a sleep 5          # system-wide for 5 seconds
perf top                      # live function-level profiling
perf record -g -p 1234        # record with call graph
perf report                    # analyse recording
```

### BPF/bcc Tools

Modern eBPF-based tools provide deeper observability:

```bash
/usr/share/bcc/tools/cachestat      # page-cache hit ratio
/usr/share/bcc/tools/biolatency     # I/O latency histogram
/usr/share/bcc/tools/runqlat        # CPU run-queue latency
/usr/share/bcc/tools/tcplife        # TCP session lifetimes
```

### Prometheus + node_exporter

For long-term monitoring, expose metrics via `node_exporter` and scrape with
Prometheus. Grafana dashboards provide trend visualisation that `sar` CSV exports
cannot match.

---

## 12. The USE Method

Brendan Gregg's **USE Method** (Utilization, Saturation, Errors) is a systematic
approach to checking every resource for bottlenecks. For each resource (CPU,
memory, disk, network), ask:

| Metric | CPU | Memory | Disk | Network |
|--------|-----|--------|------|----------|
| **Utilization** | `mpstat -P ALL 1` → %usr+%sys | `free -m` → used/total | `iostat -xz 1` → %util | `sar -n DEV 1` → %ifutil |
| **Saturation** | `vmstat 1` → `r` column | `vmstat 1` → `si/so` | `iostat -xz 1` → `aqu-sz` | `ip -s link` → dropped |
| **Errors** | `dmesg` → MCE | `dmesg` → OOM | `smartctl` → errors | `ip -s link` → errors |

### USE Method Checklist Script

```bash
#!/bin/bash
# use-check.sh — Quick USE method scan

echo "=== CPU ==="
echo "Utilization:"
mpstat 1 1 | tail -1 | awk '{print "User:", $3, "%  System:", $5, "%  Idle:", $NF, "%"}'
echo "Saturation (run queue):"
vmstat 1 1 | tail -1 | awk '{print "Runnable:", $1, "Blocked:", $2}'
echo "Errors:"
dmesg | grep -i -E "mce|machine.check" | tail -3

echo ""
echo "=== MEMORY ==="
echo "Utilization:"
free -m | grep Mem | awk '{printf "Used: %dMB / %dMB (%.1f%%)\n", $3, $2, $3/$2*100}'
echo "Saturation (swap):"
vmstat 1 1 | tail -1 | awk '{print "Swap In:", $7, "Swap Out:", $8}'
echo "Errors:"
dmesg | grep -i oom | tail -3

echo ""
echo "=== DISK ==="
echo "Utilization:"
iostat -xz 1 1 | grep -E "^nvme|^sda" | awk '{print $1, "util:", $NF, "%"}'
echo "Saturation (queue):"
iostat -xz 1 1 | grep -E "^nvme|^sda" | awk '{print $1, "avg-qz:", $(NF-3)}'
echo "Errors:"
smartctl -H /dev/sda 2>/dev/null | grep -i result || echo "smartctl not available"

echo ""
echo "=== NETWORK ==="
echo "Utilization:"
sar -n DEV 1 1 | grep -E "eth0|ens" | awk '{print $1, "rx:", $5, "KB/s  tx:", $6, "KB/s"}'
echo "Saturation (drops):"
ip -s link show | grep -A1 -E "eth0|ens" | grep -E "dropped|overruns"
echo "Errors:"
ip -s link show | grep -A1 -E "eth0|ens" | grep errors
```

## 13. Performance Anti-Patterns

Common mistakes that degrade system performance:

### Anti-Pattern: Premature Optimization

```bash
# DON'T: Tune without measuring
sysctl -w vm.swappiness=1
sysctl -w net.core.somaxconn=65535
# These may not help if the bottleneck is elsewhere

# DO: Measure first, then tune
vmstat 1 5                    # Identify the bottleneck
perf stat -a -- sleep 5       # Quantify the issue
# Then tune the specific bottleneck
```

### Anti-Pattern: Ignoring the Warm-Up Phase

```bash
# DON'T: Measure cold-cache performance
fio --name=test --rw=randread --bs=4k --filename=/dev/sda
# First run includes cache warming

# DO: Warm up first, then measure
fio --name=warmup --rw=randread --bs=4k --filename=/dev/sda \
    --time_based --runtime=30
fio --name=test --rw=randread --bs=4k --filename=/dev/sda \
    --time_based --runtime=60
```

### Anti-Pattern: Single-Metric Decision Making

```bash
# DON'T: Look at only one metric
iostat -xz 1 | grep %util    # 100% util ≠ bottleneck for NVMe

# DO: Correlate multiple metrics
# High %util + low await = NVMe handling parallel I/O well
# High %util + high await = actual saturation
iostat -xz 1 | awk 'NR>3 {print $1, "util:", $NF, "await:", $(NF-5)}'
```

## 14. Continuous Performance Monitoring

### Prometheus + node_exporter Stack

For long-term monitoring, deploy the Prometheus stack:

```bash
# Install node_exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xzf node_exporter-*.tar.gz
./node_exporter &

# Scrape with Prometheus
# prometheus.yml:
# scrape_configs:
#   - job_name: 'node'
#     static_configs:
#       - targets: ['localhost:9100']
```

### sar Data Retention

Configure `sar` for longer historical data:

```bash
# /etc/default/sysstat
ENABLED="true"
HISTORY=28          # Keep 28 days of data
COMPRESSAFTER=10    # Compress after 10 days

# /etc/cron.d/sysstat
# Collect every 1 minute (default is 10)
* * * * * root /usr/lib/sysstat/sa1 1 1
# Generate daily summary at 23:53
53 23 * * * root /usr/lib/sysstat/sa2 -A
```

### Performance Regression Detection

```bash
#!/bin/bash
# perf-regression-check.sh — Compare current perf to baseline

BASELINE_DIR="/var/lib/perf-baselines"
CURRENT="$(date +%Y%m%d)"

# Collect current metrics
CPU_SCORE=$(sysbench cpu --cpu-max-prime=20000 --threads=$(nproc) --time=10 run 2>/dev/null \
    | grep "events per second" | awk '{print $NF}')
MEM_SCORE=$(sysbench memory --memory-block-size=1M --memory-total-size=10G --threads=$(nproc) --time=10 run 2>/dev/null \
    | grep -oP '[\d.]+(?= MiB/sec)')

# Compare to baseline
if [[ -f "$BASELINE_DIR/cpu.baseline" ]]; then
    BASELINE_CPU=$(cat "$BASELINE_DIR/cpu.baseline")
    DELTA=$(echo "scale=2; ($CPU_SCORE - $BASELINE_CPU) / $BASELINE_CPU * 100" | bc)
    if (( $(echo "$DELTA < -10" | bc -l) )); then
        echo "WARNING: CPU performance regressed by ${DELTA}%"
        echo "Baseline: $BASELINE_CPU  Current: $CPU_SCORE"
    fi
fi

# Save current as new baseline if first run
mkdir -p "$BASELINE_DIR"
echo "$CPU_SCORE" > "$BASELINE_DIR/cpu.baseline"
echo "$MEM_SCORE" > "$BASELINE_DIR/mem.baseline"
```

## 15. Performance Analysis Case Studies

### Case Study 1: Database Connection Storm

**Symptom:** Web application becomes unresponsive at 9 AM daily.

```bash
# Step 1: Check system overview
vmstat 1 5
# r=150 (32-core machine!), b=0, wa=0 → CPU-bound

# Step 2: Find CPU hog
pidstat 1 3 | sort -nr -k3 | head
# mysqld consuming 800% CPU

# Step 3: Check MySQL connections
mysql -e "SHOW STATUS LIKE 'Threads_connected';"
# Threads_connected: 2500  ← Way too many!

# Step 4: Check connection source
ss -tnp | grep :3306 | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head
# 2500 connections from 10.0.0.50

# Root cause: Connection pooling misconfigured at 9 AM cron batch
# Fix: Increase pool size limit, add connection backoff
```

### Case Study 2: Intermittent I/O Latency Spikes

**Symptom:** Application P99 latency spikes every 30 seconds.

```bash
# Step 1: Capture I/O pattern
iostat -xz 1 | tee /tmp/iostat.log
# Every 30s: w_await jumps from 0.5ms to 150ms

# Step 2: Identify the writer
iotop -oP -d 1 | grep -E "WRITE|write"
# kworker: writeback → dirty page flush

# Step 3: Check dirty page settings
sysctl vm.dirty_ratio vm.dirty_background_ratio vm.dirty_writeback_centisecs
# dirty_ratio=20, dirty_background_ratio=10, dirty_writeback_centisecs=500

# Step 4: Fix — reduce dirty page accumulation
sysctl -w vm.dirty_ratio=5
sysctl -w vm.dirty_background_ratio=2
sysctl -w vm.dirty_writeback_centisecs=100
# Spreads writes more evenly, eliminates 30s spikes
```

### Case Study 3: Network Throughput Ceiling

**Symptom:** iperf3 shows 3 Gbps on a 25 Gbps NIC.

```bash
# Step 1: Check link speed
ethtool eth0 | grep Speed
# Speed: 25000Mb/s → NIC is capable

# Step 2: Check TCP buffers
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.core.rmem_max
# rmem_max = 212992 (208 KB) → Way too small!

# Step 3: Calculate BDP
# 25 Gbps × 0.001s RTT = 3.125 MB
# Need at least 3.125 MB buffer

# Step 4: Fix
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.wmem_max=16777216
sysctl -w net.ipv4.tcp_rmem="4096 262144 16777216"
sysctl -w net.ipv4.tcp_wmem="4096 262144 16777216"

# Step 5: Verify
iperf3 -c 192.168.1.100 -t 30 -P 4
# [SUM] 23.5 Gbits/sec → Much better!
```

## 16. Quick Reference Cheat Sheet

```bash
# CPU
vmstat 1                        # system-wide CPU/memory
mpstat -P ALL 1                 # per-CPU
pidstat 1                       # per-process CPU
sar -u 1 5                      # historical-aware CPU

# Memory
vmstat -s                       # memory summary
sar -r 1                        # memory utilisation over time
free -h                         # quick snapshot

# Disk
iostat -xz 1                    # per-device I/O
pidstat -d 1                    # per-process disk I/O
dstat --disk-util 1             # utilisation bar

# Network
sar -n DEV 1                    # interface throughput
sar -n SOCK 1                   # socket counts
dstat -n 1                      # live net throughput

# Historical
sar -A -f /var/log/sa/sa$(date +%d)   # full report for today
sadf -g -- -A > today.svg             # SVG graph
```

---

## 17. Flame Graph Generation

Flame graphs are the standard visualization for CPU profiling:

```bash
# Generate CPU flame graph with perf
perf record -F 99 -a -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu.svg

# Generate off-CPU flame graph (shows blocking time)
perf record -e sched:sched_switch -a -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl --color=io > offcpu.svg

# Generate memory allocation flame graph
perf record -e kmem:kmalloc -a -g -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl --color=mem > mem.svg

# Differential flame graph (compare two profiles)
perf script -i before.data | stackcollapse-perf.pl > before.folded
perf script -i after.data | stackcollapse-perf.pl > after.folded
difffolded.pl before.folded after.folded | flamegraph.pl > diff.svg
```

**Reading flame graphs:**
- Width = percentage of total samples (wider = more time spent)
- Height = call stack depth (taller = deeper call chain)
- Plateaus = hot functions consuming significant CPU time

## 18. Kernel Tracepoints for Admin Performance

Key tracepoints for performance debugging:

```bash
# List available tracepoints
perf list tracepoint

# Trace scheduler latency
perf trace -e sched:sched_switch,sched:sched_wakeup -p <pid> -- sleep 5

# Trace block I/O latency
perf trace -e block:block_rq_issue,block:block_rq_complete -a -- sleep 5

# Trace page faults
perf trace -e exceptions:page_fault_user -- sleep 5

# Trace network TCP retransmits
perf trace -e tcp:tcp_retransmit_skb -a -- sleep 10

# Trace OOM killer
perf trace -e oom:oom_score_adj_update -a -- sleep 30
```

---

## Further Reading

- [Linux Performance Analysis — Brendan Gregg](https://www.brendangregg.com/linuxperf.html)
- [perf Wiki — kernel.org](https://perf.wiki.kernel.org/index.php/Main_Page)
- [sysstat Documentation](https://sebastien.godard.pagesperso-orange.fr/)
- [BPF Performance Tools — bcc](https://github.com/iovisor/bcc)
- [Linux observability tools diagram — Brendan Gregg](https://www.brendangregg.com/linuxperf.html)
- [vmstat(8) man page](https://man7.org/linux/man-pages/man8/vmstat.8.html)
- [iostat(1) man page](https://man7.org/linux/man-pages/man1/iostat.1.html)
- [sar(1) man page](https://man7.org/linux/man-pages/man1/sar.1.html)
- [pidstat(1) man page](https://man7.org/linux/man-pages/man1/pidstat.1.html)
- [Understanding the Linux Virtual Memory Manager — Mel Gorman](https://www.kernel.org/doc/gorman/)
- Gregg, B. *Systems Performance: Enterprise and the Cloud*, 2nd Edition (2020).
- [USE Method — Brendan Gregg](https://www.brendangregg.com/usemethod.html)
- [Linux Performance Analysis in 60 Seconds — Netflix](http://techblog.netflix.com/2015/11/linux-performance-analysis-in-60s.html)

---

## Related Topics

- [NUMA Optimization](../performance/numa.md)
- [Memory Performance](../performance/memory.md)
- [I/O Performance](../performance/io.md)
- [Network Performance](../performance/network.md)
- [Kernel Tuning Parameters](../performance/kernel-params.md)
- [Benchmarking](../performance/benchmarking.md)
- [CPU Performance](../performance/cpu.md)
- [Cache Statistics](../performance/cachestat.md)
