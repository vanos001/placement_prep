# Pktgen — Packet Generator

## Overview

Pktgen (Packet Generator) is a high-performance network packet generation tool built into the Linux kernel as a module. It can craft and transmit packets at near-wire speed, making it invaluable for network performance testing, NIC benchmarking, router stress testing, and protocol development. Pktgen operates from kernel space, eliminating userspace overhead and achieving packet rates that userspace tools cannot match.

Pktgen was originally written by Robert Olsson in 2001 and has been part of the mainline kernel since 2.6.x. It supports IPv4, IPv6, UDP, TCP, and MPLS traffic generation with extensive configurability.

## Architecture

Pktgen uses a per-CPU thread model where each thread manages one or more network interfaces. The control interface is exposed through `/proc/net/pktgen/`:

```
/proc/net/pktgen/
├── kpktgend_0          # Control for CPU 0's thread
├── kpktgend_1          # Control for CPU 1's thread
├── ...
├── eth0                # Configuration for eth0
├── eth1                # Configuration for eth1
└── pgctrl              # Global start/stop/reset
```

### Thread Model

Each CPU runs a `kpktgend_N` kernel thread. The thread iterates over its assigned interfaces, constructs packets, and pushes them to the network driver's transmit queue. By binding threads to CPUs and interfaces to queues, pktgen can saturate multiple NIC queues simultaneously.

### Packet Construction Pipeline

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  kpktgend_N     │     │  SKB Allocation │     │  Driver TX      │
│  kernel thread  │────►│  + Header Fill  │────►│  ndo_start_xmit │
│                 │     │  + Payload Gen  │     │  (or burst)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │                       │                       ▼
   Per-CPU loop          clone_skb              NIC TX queue
   (spin until done)     optimization           → Wire
```

## Module Loading

```bash
# Load the pktgen module
modprobe pktgen

# Verify it loaded
ls /proc/net/pktgen/
# Should show kpktgend_0, kpktgend_1, etc.

# Remove when done
rmmod pktgen
```

## Scripting Interface

Pktgen is controlled by writing commands to the `/proc/net/pktgen/` files. A typical script:

```bash
#!/bin/bash
# pktgen_example.sh — Generate UDP traffic from eth0

PGDEV=/proc/net/pktgen
DEV=eth0

# Reset all interfaces
echo "reset" > $PGDEV/pgctrl

# Configure the interface
echo "add_device $DEV" > $PGDEV/kpktgend_0
echo "count 0"          > $PGDEV/$DEV      # 0 = unlimited
echo "pkt_size 64"      > $PGDEV/$DEV
echo "dst 10.0.0.1"     > $PGDEV/$DEV
echo "src 10.0.0.2"     > $PGDEV/$DEV
echo "dst_mac 00:11:22:33:44:55" > $PGDEV/$DEV
echo "udp_dst 9"        > $PGDEV/$DEV      # Destination port
echo "udp_src 1234"     > $PGDEV/$DEV      # Source port
echo "flag UDPSRC_RND"  > $PGDEV/$DEV      # Randomize source port

# Start transmission
echo "start" > $PGDEV/pgctrl
```

## Core Configuration Parameters

### Packet Count and Size

```bash
# Number of packets (0 = continuous until stopped)
echo "count 1000000" > /proc/net/pktgen/eth0

# Packet size in bytes (including Ethernet header)
echo "pkt_size 1500" > /proc/net/pktgen/eth0

# Minimum/max size for random variation
echo "min_pkt_size 64" > /proc/net/pktgen/eth0
echo "max_pkt_size 1514" > /proc/net/pktgen/eth0
```

### Rate Control

```bash
# Rate in packets per second
echo "rate 100000" > /proc/net/pktgen/eth0

# Rate as percentage of link speed
echo "ratep 50" > /proc/net/pktgen/eth0  # 50% of line rate

# Delay between packets in nanoseconds
echo "delay 1000" > /proc/net/pktgen/eth0  # 1µs between packets
```

### Source and Destination

```bash
# Source/destination IP
echo "src 192.168.1.100" > /proc/net/pktgen/eth0
echo "dst 192.168.1.200" > /proc/net/pktgen/eth0

# MAC addresses
echo "dst_mac 00:11:22:33:44:55" > /proc/net/pktgen/eth0

# Source/destination ports (for UDP/TCP)
echo "udp_src 1234" > /proc/net/pktgen/eth0
echo "udp_dst 80"   > /proc/net/pktgen/eth0

# VLAN
echo "vlan_id 100" > /proc/net/pktgen/eth0
echo "vlan_p 3"    > /proc/net/pktgen/eth0  # Priority
```

### IPv6 Support

```bash
echo "dst6 fd00::1"  > /proc/net/pktgen/eth0
echo "src6 fd00::2"  > /proc/net/pktgen/eth0
echo "flow_label 0x12345" > /proc/net/pktgen/eth0
```

### TCP Packet Generation

```bash
# Generate TCP SYN packets
echo "tcp_data_offset 0" > /proc/net/pktgen/eth0
echo "flag TCP_SYN" > /proc/net/pktgen/eth0

# Set TCP flags individually
echo "tcp_urg 0" > /proc/net/pktgen/eth0
echo "tcp_ack 0" > /proc/net/pktgen/eth0
echo "tcp_psh 0" > /proc/net/pktgen/eth0
echo "tcp_rst 0" > /proc/net/pktgen/eth0
echo "tcp_syn 1" > /proc/net/pktgen/eth0
echo "tcp_fin 0" > /proc/net/pktgen/eth0

# TCP sequence numbers
echo "tcp_seq 1000" > /proc/net/pktgen/eth0
echo "tcp_ack_seq 0" > /proc/net/pktgen/eth0

# TCP window
echo "tcp_window 65535" > /proc/net/pktgen/eth0
```

### Custom Payload

```bash
# Set custom payload (hex string)
echo "data 0xdeadbeef0123456789abcdef" > /proc/net/pktgen/eth0

# Or specify a file for payload data
# (not directly supported - use script to set hex data)
PAYLOAD=$(python3 -c "print('0x' + 'ab' * 100)")
echo "data $PAYLOAD" > /proc/net/pktgen/eth0
```

## clone_skb: Packet Cloning

The `clone_skb` parameter controls how pktgen reuses packet buffers:

```bash
# Clone SKB N times before rebuilding (0 = rebuild every packet)
echo "clone_skb 1000" > /proc/net/pktgen/eth0
```

### How clone_skb Works

When `clone_skb` is set to a non-zero value, pktgen creates a template packet and then uses `skb_clone()` to create lightweight clones. Cloning shares the packet data buffer, only duplicating the SKB metadata structure. This dramatically reduces per-packet overhead:

- **clone_skb 0**: Every packet is built from scratch (most flexible, slowest)
- **clone_skb 1000**: Clone the template 1000 times before rebuilding (faster, less flexible)
- **clone_skb N**: For best performance with static packet headers

### When to Use clone_skb

| Scenario | clone_skb | Reason |
|---|---|---|
| Static headers, benchmark NIC | High (1000+) | Maximum throughput |
| Random source/dest IPs | 0 | Each packet must be unique |
| Incrementing counters | 0 | Payload changes per packet |
| Raw performance test | High | Minimize packet construction cost |

### Limitations

When `clone_skb > 0`, certain randomization features are disabled because cloned packets share the same data buffer. For example, `FLAG_IPDST_RND` requires `clone_skb 0`.

## Burst Mode

Burst mode allows pktgen to send multiple packets per call to the driver's `ndo_start_xmit()`, reducing per-packet overhead significantly:

```bash
# Send up to 32 packets per burst
echo "burst 32" > /proc/net/pktgen/eth0
```

### How Burst Works

Without burst, pktgen calls the driver's transmit function once per packet. With burst enabled, pktgen prepares multiple packets and submits them together using `dev_queue_xmit()` or direct driver calls. This amortizes the cost of:
- Lock acquisition
- DMA mapping
- Doorbell writes to the NIC
- Interrupt coalescing

### Burst Performance Impact

Typical improvement with burst mode:

| burst | Packets/sec (approx) | Notes |
|---|---|---|
| 1 | 1,000,000 | Baseline, one packet per xmit call |
| 8 | 3,000,000 | ~3x improvement |
| 32 | 8,000,000 | ~8x improvement |
| 64 | 10,000,000 | Near line rate for 64B on 10GbE |

### Interaction with clone_skb

Burst mode and clone_skb complement each other. Clone_skb reduces packet construction cost, while burst reduces driver call overhead. Using both together yields the highest throughput.

## Flags

Pktgen supports various flags to control packet generation behavior:

```bash
# List of available flags
echo "flag IPDST_RND"   > /proc/net/pktgen/eth0  # Random destination IP
echo "flag IPSRC_RND"   > /proc/net/pktgen/eth0  # Random source IP
echo "flag UDPSRC_RND"  > /proc/net/pktgen/eth0  # Random source port
echo "flag UDPDST_RND"  > /proc/net/pktgen/eth0  # Random destination port
echo "flag MACSRC_RND"  > /proc/net/pktgen/eth0  # Random source MAC
echo "flag MACDST_RND"  > /proc/net/pktgen/eth0  # Random destination MAC
echo "flag MPLS_RND"    > /proc/net/pktgen/eth0  # Random MPLS label
echo "flag VID_RND"     > /proc/net/pktgen/eth0  # Random VLAN ID
echo "flag SVID_RND"    > /proc/net/pktgen/eth0  # Random SVLAN ID
echo "flag FLOW_SEQ"    > /proc/net/pktgen/eth0  # Sequential flow
echo "flag QUEUE_MAP_CPU" > /proc/net/pktgen/eth0  # Map queue to CPU
echo "flag NODE"        > /proc/net/pktgen/eth0  # NUMA node allocation
echo "flag NO_TIMESTAMP" > /proc/net/pktgen/eth0  # Disable timestamping
```

### Flag Combinations

Multiple flags can be combined:

```bash
echo "flag IPSRC_RND IPDST_RND UDPSRC_RND" > /proc/net/pktgen/eth0
```

### IP Range Control

When using random IP flags, set the range:

```bash
# Destination IP range for randomization
echo "dst_min 10.0.0.1"   > /proc/net/pktgen/eth0
echo "dst_max 10.0.0.254" > /proc/net/pktgen/eth0

# Source IP range
echo "src_min 192.168.1.1" > /proc/net/pktgen/eth0
echo "src_max 192.168.1.254" > /proc/net/pktgen/eth0
```

### Port Range Control

```bash
# Source port range for randomization
echo "udp_src_min 1024" > /proc/net/pktgen/eth0
echo "udp_src_max 65535" > /proc/net/pktgen/eth0

# Destination port range
echo "udp_dst_min 80" > /proc/net/pktgen/eth0
echo "udp_dst_max 80" > /proc/net/pktgen/eth0
```

## Multi-Queue and CPU Affinity

For maximum performance, bind pktgen threads to CPUs and assign interfaces to specific threads:

```bash
# Assign eth0 to CPU 0's thread
echo "add_device eth0" > /proc/net/pktgen/kpktgend_0

# Remove from another thread if needed
echo "rem_device eth0" > /proc/net/pktgen/kpktgend_1

# Set CPU affinity for the thread
echo "cpu 0" > /proc/net/pktgen/eth0
```

### NUMA-Aware Configuration

```bash
# Set NUMA node for memory allocation
echo "node 0" > /proc/net/pktgen/eth0

# Bind to specific CPU on NUMA node 0
echo "cpu 0" > /proc/net/pktgen/eth0

# For multi-NIC, use NIC's NUMA node
# Check NIC NUMA node:
cat /sys/class/net/eth0/device/numa_node
# 0 means NUMA node 0
```

### Multi-NIC Benchmarking

```bash
#!/bin/bash
# Benchmark two NICs simultaneously

PGDEV=/proc/net/pktgen

echo "reset" > $PGDEV/pgctrl

# NIC 1 on CPU 0 (NUMA node 0)
echo "add_device eth0" > $PGDEV/kpktgend_0
echo "count 0" > $PGDEV/eth0
echo "pkt_size 64" > $PGDEV/eth0
echo "dst 10.0.1.1" > $PGDEV/eth0
echo "burst 32" > $PGDEV/eth0
echo "clone_skb 1000" > $PGDEV/eth0
echo "node 0" > $PGDEV/eth0

# NIC 2 on CPU 1 (NUMA node 0)
echo "add_device eth1" > $PGDEV/kpktgend_1
echo "count 0" > $PGDEV/eth1
echo "pkt_size 64" > $PGDEV/eth1
echo "dst 10.0.2.1" > $PGDEV/eth1
echo "burst 32" > $PGDEV/eth1
echo "clone_skb 1000" > $PGDEV/eth1
echo "node 0" > $PGDEV/eth1

echo "start" > $PGDEV/pgctrl
```

### Multi-Queue NIC with Multiple Threads

```bash
#!/bin/bash
# Saturate a multi-queue 100GbE NIC

PGDEV=/proc/net/pktgen
DEV=eth0

echo "reset" > $PGDEV/pgctrl

# Get number of TX queues
NUM_QUEUES=$(ethtool -l $DEV | grep "Combined" | head -1 | awk '{print $2}')
echo "NIC has $NUM_QUEUES TX queues"

# Create one pktgen thread per queue
for i in $(seq 0 $((NUM_QUEUES - 1))); do
    CPU=$i
    echo "add_device $DEV@$i" > $PGDEV/kpktgend_$CPU
    echo "count 0" > $PGDEV/${DEV}@$i
    echo "pkt_size 64" > $PGDEV/${DEV}@$i
    echo "clone_skb 1000" > $PGDEV/${DEV}@$i
    echo "burst 64" > $PGDEV/${DEV}@$i
    echo "dst 10.0.0.1" > $PGDEV/${DEV}@$i
    echo "cpu $CPU" > $PGDEV/${DEV}@$i
    echo "queue_map_min $i" > $PGDEV/${DEV}@$i
    echo "queue_map_max $i" > $PGDEV/${DEV}@$i
done

echo "start" > $PGDEV/pgctrl
sleep 10
echo "stop" > $PGDEV/pgctrl
```

## MPLS Support

Pktgen can generate MPLS-encapsulated traffic:

```bash
# Set MPLS labels
echo "mpls 0"        > /proc/net/pktgen/eth0  # Bottom of stack
echo "mpls 100"      > /proc/net/pktgen/eth0  # Label 1
echo "mpls 200"      > /proc/net/pktgen/eth0  # Label 2 (outer)
echo "flag MPLS_RND" > /proc/net/pktgen/eth0  # Randomize labels
```

### MPLS Label Stack

```bash
#!/bin/bash
# Generate MPLS traffic with label stack

PGDEV=/proc/net/pktgen
DEV=eth0

echo "reset" > $PGDEV/pgctrl
echo "add_device $DEV" > $PGDEV/kpktgend_0

echo "count 0" > $PGDEV/$DEV
echo "pkt_size 64" > $PGDEV/$DEV
echo "clone_skb 1000" > $PGDEV/$DEV

# MPLS: outer label 100, inner label 200
echo "mpls 200" > $PGDEV/$DEV  # Inner (bottom of stack)
echo "mpls 100" > $PGDEV/$DEV  # Outer

echo "dst 10.0.0.1" > $PGDEV/$DEV
echo "dst_mac 00:11:22:33:44:55" > $PGDEV/$DEV

echo "start" > $PGDEV/pgctrl
```

## Monitoring Output

Pktgen provides per-device statistics:

```bash
cat /proc/net/pktgen/eth0
# Output includes:
#   Current count:     5000000
#   Requested count:   0 (unlimited)
#   OK:                5000000
#   Errors:            0
#   Bytes sent:        320000000
#   Rate:              1500000 pps
#   Started:           yes
#   Running:           yes
```

### Detailed Statistics

```bash
# Get detailed stats while running
cat /proc/net/pktgen/eth0

# Stats include:
# - pkts_sent: Total packets transmitted
# - pkts_rcvd: Packets received (if loopback)
# - errors: Transmission errors
# - bytes_sent: Total bytes
# - elapsed_ns: Time elapsed in nanoseconds
# - current_pps: Current packets per second
# - current_bps: Current bits per second
```

### Real-time Monitoring Script

```bash
#!/bin/bash
# Monitor pktgen output in real-time

PGDEV=/proc/net/pktgen
DEV=eth0

echo "Monitoring pktgen on $DEV (Ctrl+C to stop)..."
echo "-------------------------------------------"

while true; do
    STATS=$(cat $PGDEV/$DEV 2>/dev/null)
    PKTS=$(echo "$STATS" | grep "Current count" | awk '{print $NF}')
    RATE=$(echo "$STATS" | grep "Rate" | awk '{print $NF}')
    ERRS=$(echo "$STATS" | grep "Errors" | awk '{print $NF}')
    BYTES=$(echo "$STATS" | grep "Bytes" | awk '{print $NF}')

    printf "Pkts: %-12s Rate: %-12s Errors: %-6s Bytes: %s\n" \
        "$PKTS" "$RATE" "$ERRS" "$BYTES"
    sleep 1
done
```

## Global Control

```bash
# Start all configured interfaces
echo "start" > /proc/net/pktgen/pgctrl

# Stop all
echo "stop" > /proc/net/pktgen/pgctrl

# Reset all configuration
echo "reset" > /proc/net/pktgen/pgctrl
```

## Performance Tips

1. **Use burst mode**: `burst 32` or higher for maximum throughput
2. **Clone packets**: `clone_skb 1000` when headers are static
3. **Bind to CPUs**: Pin threads to specific CPUs, avoid cross-NUMA
4. **Disable interrupts**: For the receiving side, use `echo 1 > /proc/irq/N/smp_affinity` or CPU isolation
5. **Increase ring buffers**: `ethtool -G eth0 rx 4096 tx 4096`
6. **Use huge pages**: Reduces TLB pressure for large packet buffers
7. **Disable NAPI busy polling**: Avoid contention with pktgen threads
8. **Use queue_map_cpu**: Map pktgen threads to NIC TX queues
9. **Disable timestamping**: `flag NO_TIMESTAMP` reduces per-packet overhead
10. **Increase kernel stack size**: For complex packet headers, ensure `CONFIG_16KSTACKS` or similar

### NIC Tuning for Maximum PPS

```bash
# Increase TX ring buffer
ethtool -G eth0 tx 4096

# Disable interrupt coalescing (for lowest latency)
ethtool -C eth0 tx-usecs 0 tx-frames 0

# Set IRQ affinity
echo 1 > /proc/irq/<irq_num>/smp_affinity

# Disable GRO/GSO/TSO for accurate small packet testing
ethtool -K eth0 gro off gso off tso off

# Set interrupt moderation to minimum
ethtool -C eth0 adaptive-rx off adaptive-tx off
```

### CPU Isolation for Pktgen

```bash
# Isolate CPUs 2-7 from the kernel scheduler
# Add to kernel command line:
isolcpus=2-7 nohz_full=2-7

# Or use cgroups to isolate
cgcreate -g cpuset:/pktgen
cgset -r cpuset.cpus=2-7 pktgen
cgset -r cpuset.mems=0 pktgen

# Run pktgen threads in isolated CPUs
```

## Example: Line Rate Test

```bash
#!/bin/bash
# Push 10GbE to line rate with 64-byte packets

PGDEV=/proc/net/pktgen
DEV=eth0

echo "reset" > $PGDEV/pgctrl
echo "add_device $DEV" > $PGDEV/kpktgend_0

echo "count 0"          > $PGDEV/$DEV
echo "pkt_size 64"      > $PGDEV/$DEV
echo "clone_skb 1000"   > $PGDEV/$DEV
echo "burst 64"         > $PGDEV/$DEV
echo "dst 10.0.0.1"     > $PGDEV/$DEV
echo "dst_mac ff:ff:ff:ff:ff:ff" > $PGDEV/$DEV

echo "start" > $PGDEV/pgctrl

# Monitor
sleep 10
cat $PGDEV/$DEV

echo "stop" > $PGDEV/pgctrl
```

## Example: Stress Test with Random Traffic

```bash
#!/bin/bash
# Stress test with randomized source/destination

PGDEV=/proc/net/pktgen
DEV=eth0

echo "reset" > $PGDEV/pgctrl
echo "add_device $DEV" > $PGDEV/kpktgend_0

echo "count 0" > $PGDEV/$DEV
echo "pkt_size 128" > $PGDEV/$DEV
echo "clone_skb 0" > $PGDEV/$DEV  # Must be 0 for randomization
echo "burst 32" > $PGDEV/$DEV

# Randomize everything
echo "flag IPSRC_RND IPDST_RND UDPSRC_RND UDPDST_RND" > $PGDEV/$DEV
echo "src_min 10.0.0.1" > $PGDEV/$DEV
echo "src_max 10.0.0.254" > $PGDEV/$DEV
echo "dst_min 10.0.1.1" > $PGDEV/$DEV
echo "dst_max 10.0.1.254" > $PGDEV/$DEV
echo "udp_src_min 1024" > $PGDEV/$DEV
echo "udp_src_max 65535" > $PGDEV/$DEV
echo "udp_dst_min 1" > $PGDEV/$DEV
echo "udp_dst_max 1024" > $PGDEV/$DEV

echo "start" > $PGDEV/pgctrl
```

## Example: VLAN-Tagged Traffic

```bash
#!/bin/bash
# Generate VLAN-tagged traffic

PGDEV=/proc/net/pktgen
DEV=eth0

echo "reset" > $PGDEV/pgctrl
echo "add_device $DEV" > $PGDEV/kpktgend_0

echo "count 100000" > $PGDEV/$DEV
echo "pkt_size 1518" > $PGDEV/$DEV
echo "vlan_id 100" > $PGDEV/$DEV
echo "vlan_p 5" > $PGDEV/$DEV  # Priority 5
echo "dst 192.168.100.2" > $PGDEV/$DEV
echo "src 192.168.100.1" > $PGDEV/$DEV
echo "dst_mac 00:11:22:33:44:55" > $PGDEV/$DEV

echo "start" > $PGDEV/pgctrl
```

## Userspace Frontend: pktgen-dpdk

For even higher performance, the `pg` tool (part of the kernel source at `samples/pktgen/`) provides a simplified C interface. External tools like `pktgen-dpdk` use DPDK to bypass the kernel entirely for multi-million packets-per-second rates, but the in-kernel pktgen remains the most portable and easiest to use.

### Comparison with Userspace Tools

| Tool | PPS (64B, 10GbE) | Kernel Bypass | Ease of Use |
|------|-------------------|---------------|-------------|
| pktgen (kernel) | ~14.8 Mpps | No | Easy (proc) |
| tcpreplay | ~2 Mpps | No | Easy |
| TRex | ~14.8 Mpps | Optional | Medium |
| pktgen-dpdk | ~14.8 Mpps | Yes | Complex |
| moongen | ~14.8 Mpps | Yes | Medium |

## Receiving Side Configuration

When testing with pktgen, configure the receiver to accurately measure incoming traffic:

```bash
# On the receiving host

# Enable promiscuous mode
ip link set eth0 promisc on

# Use tcpdump to verify
tcpdump -i eth0 -c 1000 -nn

# Or use a dedicated receiver
# AF_PACKET with TPACKET_V3 for high-speed capture

# Disable iptables on the receiver to avoid drops
iptables -P INPUT ACCEPT
iptables -F

# Increase receive buffer
sysctl -w net.core.rmem_max=16777216
sysctl -w net.core.rmem_default=16777216

# Monitor drops
ethtool -S eth0 | grep -i drop
```

## Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| Low packet rate | No burst/clone | Set `burst 32` and `clone_skb 1000` |
| Errors on output | Driver rejects packets | Check `dst_mac`, ensure link is up |
| Single CPU used | Thread not assigned | Use `kpktgend_N` to spread across CPUs |
| Cannot load module | Not compiled | Enable `CONFIG_NET_PKTGEN` in kernel config |
| Packets not seen on receiver | Wrong MAC/IP | Verify addressing; use promiscuous mode |
| High CPU usage | No clone_skb | Enable `clone_skb` for static headers |
| OOM errors | Large packet sizes | Reduce `pkt_size` or increase system memory |
| Interface not found | Wrong interface name | Check `ip link show` for correct names |
| Permission denied | Not root | Run as root or with `CAP_NET_RAW` |

## Kernel Configuration

```
CONFIG_NET_PKTGEN=m    # Or =y for built-in
```

### Compile-time Options

```bash
# Check if pktgen is available
modprobe pktgen 2>/dev/null && echo "pktgen available" || echo "not available"

# If not available, rebuild kernel with CONFIG_NET_PKTGEN=m
# Or check distribution packages:
apt install linux-modules-extra-$(uname -r)  # Debian/Ubuntu
```

## Further Reading

- **Kernel documentation**: `Documentation/networking/pktgen.rst`
- **Source**: `net/core/pktgen.c` — core pktgen implementation
- **Robert Olsson's original paper**: "Pktgen — the Linux network packet generator"
- **LWN article**: ["Pktgen revisited"](https://lwn.net/Articles/256347/)
- **Man page**: `man pktgen` (if available from your distribution)
- **Related**: [Network Performance Tuning](../../performance/network.md)
- **Related**: NIC Multi-Queue — RSS/RPS and queue configuration
- **Related**: [Traffic Control](./tc.md) — Linux traffic shaping
