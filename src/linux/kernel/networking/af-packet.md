# AF_PACKET — Raw Sockets and Packet Capture

## Overview

`AF_PACKET` is a Linux socket family that allows applications to send and receive
packets at the link layer (Layer 2) directly, bypassing the kernel's normal TCP/IP
stack processing. It is the foundation for packet capture tools (tcpdump, Wireshark),
network monitoring systems, and high-performance traffic analysis frameworks.

AF_PACKET provides access to raw Ethernet frames, making it indispensable for
network diagnostics, intrusion detection systems (IDS), and custom protocol
implementations that need to operate below the IP layer.

## History

AF_PACKET has evolved significantly since its introduction:

- **Linux 2.0**: Initial packet socket support, `TPACKET_V1` ring buffer
- **Linux 2.6**: Introduction of `TPACKET_V2` with improved alignment and VLAN
  tag support
- **Linux 3.2** (2012): `TPACKET_V3` — flexible block-based ring buffer with
  support for variable-length frames and configurable block sizes
- **Linux 3.x–5.x**: Ongoing performance improvements including busy-polling
  support, mmap enhancements, and AF_XDP integration

## Socket Creation

### Basic Raw Socket

```c
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>

int fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
```

- `SOCK_RAW`: delivers complete link-layer frames including the MAC header
- `SOCK_DGRAM`: strips the link-layer header before delivery

### Protocol Filtering

The third argument filters by EtherType:

| Value         | Meaning                           |
|---------------|-----------------------------------|
| `ETH_P_ALL`   | All protocols (promiscuous mode)  |
| `ETH_P_IP`    | IPv4 only                         |
| `ETH_P_ARP`   | ARP only                          |
| `ETH_P_IPV6`  | IPv6 only                         |
| `ETH_P_8021Q` | VLAN-tagged frames                |
| `ETH_P_LLDP`  | LLDP frames                       |

### Binding to Specific Interface

```c
#include <net/if.h>

struct sockaddr_ll addr = {
    .sll_family = AF_PACKET,
    .sll_protocol = htons(ETH_P_ALL),
    .sll_ifindex = if_nametoindex("eth0"),
};

bind(fd, (struct sockaddr *)&addr, sizeof(addr));
```

### Promiscuous Mode

To capture all traffic on a network segment (not just traffic destined for the
local host), enable promiscuous mode on the interface:

```c
struct packet_mreq mreq = {
    .mr_ifindex = ifindex,
    .mr_type = PACKET_MR_PROMISC,
};
setsockopt(fd, SOL_PACKET, PACKET_ADD_MEMBERSHIP, &mreq, sizeof(mreq));
```

```bash
# Enable promiscuous mode from command line
ip link set eth0 promisc on

# Verify
ip link show eth0 | grep PROMISC
# eth0: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP> ...

# Disable
ip link set eth0 promisc off
```

## Ring Buffers: TPACKET_V1, V2, V3

### The Problem with recvmsg()

Using standard `recvmsg()` for packet capture has significant overhead: each
packet requires a system call, kernel-to-user memory copy, and context switch.
At high packet rates, this becomes the bottleneck.

### Mmap Ring Buffers

AF_PACKET solves this by mapping a shared ring buffer between kernel and user
space. The kernel writes captured frames into the ring; the application reads
them directly from mapped memory, eliminating per-packet copies and system calls.

### TPACKET_V1 (Legacy)

The original implementation. Each frame in the ring has a fixed-size header
(`struct tpacket_hdr`) followed by the packet data. Simple but inflexible —
fixed frame size wastes memory for small packets.

### TPACKET_V2 (Improved)

Introduced in Linux 2.6. Key improvements:

- Better alignment for VLAN tag insertion (`tp_vlan_tci` field)
- Support for multiple VLAN tags (QinQ)
- `struct tpacket2_hdr` replaces `tpacket_hdr`

```c
int version = TPACKET_V2;
setsockopt(fd, SOL_PACKET, PACKET_VERSION, &version, sizeof(version));
```

### TPACKET_V3 (Block-Based)

Introduced in **Linux 3.2** by Chetan Loke. The most flexible and performant
version:

**Key Design Changes:**

1. **Block-based**: frames are grouped into blocks rather than individual frames
2. **Variable-length frames**: blocks can contain frames of different sizes
3. **Configurable block size**: tuned for L2 cache or page size alignment
4. **Timer-based flushing**: blocks are released to userspace either when full
   or after a configurable timeout (even if partially filled)

**Ring Buffer Layout:**

```
+------------------+------------------+------------------+---
|     Block 0      |     Block 1      |     Block 2      |
| [hdr][frame]...  | [hdr][frame]...  | [hdr][frame]...  |
+------------------+------------------+------------------+---
       ^                    ^
       |                    |
  kernel writes here   userspace reads here
```

**Configuration:**

```c
struct tpacket_req3 req = {
    .tp_block_size = 1 << 22,      /* 4 MiB per block */
    .tp_block_nr   = 64,           /* 64 blocks */
    .tp_frame_size = 0,             /* ignored in V3, kernel computes optimal size */
    .tp_frame_nr   = 0,            /* computed from block_size * block_nr */
    .tp_retire_blk_tov = 64,       /* block timeout in ms */
    .tp_sizeof_priv = 0,           /* private data area per block */
    .tp_feature_req_word = TP_FT_REQ_FILL_RXHASH,
};
setsockopt(fd, SOL_PACKET, PACKET_RX_RING, &req, sizeof(req));
```

**Reading Frames in V3:**

```c
/* Map the ring */
void *ring = mmap(NULL, size, PROT_READ | PROT_WRITE,
                  MAP_SHARED, fd, 0);

/* Poll for available blocks */
struct pollfd pfd = { .fd = fd, .events = POLLIN };
poll(&pfd, 1, -1);

/* Process block */
struct tpacket_block_desc *block = ring + block_offset;
if (!(block->hdr.bh1.block_status & TP_STATUS_USER))
    continue;

/* Iterate frames within block */
struct tpacket3_hdr *frame = (void *)block + block->hdr.bh1.offset_to_first_pkt;
for (uint32_t i = 0; i < block->hdr.bh1.num_pkts; i++) {
    /* Process frame at (uint8_t *)frame + frame->tp_mac */
    frame = (struct tpacket3_hdr *)((uint8_t *)frame + frame->tp_next_offset);
}

/* Release block back to kernel */
block->hdr.bh1.block_status = TP_STATUS_KERNEL;
```

### TPACKET Version Comparison

| Feature | V1 | V2 | V3 |
|---------|----|----|-----|
| Frame size | Fixed | Fixed | Variable |
| Block grouping | No | No | Yes |
| Timer flush | No | No | Yes |
| VLAN info | No | Yes (`tp_vlan_tci`) | Yes |
| Performance | Low | Medium | High |
| Complexity | Low | Medium | High |
| Use case | Legacy | tcpdump | IDS, monitoring |

## Packet Fanout

For multi-threaded capture, AF_PACKET supports **fanout** — distributing packets
across multiple sockets (and thus threads) based on configurable policies.

```c
int fanout_group = 0x1234;  /* arbitrary group ID */
int fanout_type = FANOUT_HASH;  /* or FANOUT_CPU, FANOUT_RND, etc. */
int fanout_arg = (fanout_group | (fanout_type << 16));
setsockopt(fd, SOL_PACKET, PACKET_FANOUT, &fanout_arg, sizeof(fanout_arg));
```

### Fanout Policies

| Policy              | Behavior                                    |
|---------------------|---------------------------------------------|
| `FANOUT_HASH`       | Hash-based flow distribution (per-flow affinity) |
| `FANOUT_CPU`        | Route packets to the socket on the processing CPU |
| `FANOUT_RND`        | Random distribution                         |
| `FANOUT_ROLLOVER`   | Fill sockets sequentially (rollover on full)|
| `FANOUT_CBPF`       | Custom BPF program for distribution         |
| `FANOUT_EBPF`       | Custom eBPF program for distribution        |
| `FANOUT_FLAG_DEFRAG`| Defragment IP before hashing (for flow consistency) |
| `FANOUT_FLAG_ROLLOVER` | Enable rollover as fallback on overload  |

**Note:** `FANOUT_FLAG_DEFRAG` and `FANOUT_FLAG_ROLLOVER` are modifier flags that
are OR'd with a base policy (e.g., `FANOUT_HASH | FANOUT_FLAG_DEFRAG`), not
standalone policies.

### Fanout with BPF

eBPF-based fanout allows custom packet distribution logic:

```c
/* Attach eBPF program for fanout decision */
int fanout_arg = fanout_group | (FANOUT_EBPF << 16);
setsockopt(fd, SOL_PACKET, PACKET_FANOUT, &fanout_arg, sizeof(fanout_arg));
/* Then setsockopt with PACKET_FANOUT_DATA pointing to BPF fd */
```

### Multi-threaded Capture Example

```c
#include <pthread.h>
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>

#define NUM_THREADS 4
#define FANOUT_GROUP 0xABCD

void *capture_thread(void *arg) {
    int thread_id = *(int *)arg;
    int fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));

    /* Set up TPACKET_V3 ring */
    /* ... */

    /* Join fanout group */
    int fanout = FANOUT_GROUP | (FANOUT_HASH << 16);
    setsockopt(fd, SOL_PACKET, PACKET_FANOUT, &fanout, sizeof(fanout));

    /* Capture loop */
    while (1) {
        struct pollfd pfd = { .fd = fd, .events = POLLIN };
        poll(&pfd, 1, -1);
        /* Process blocks */
    }
    return NULL;
}

int main(void) {
    pthread_t threads[NUM_THREADS];
    int ids[NUM_THREADS];

    for (int i = 0; i < NUM_THREADS; i++) {
        ids[i] = i;
        pthread_create(&threads[i], NULL, capture_thread, &ids[i]);
    }

    for (int i = 0; i < NUM_THREADS; i++)
        pthread_join(threads[i], NULL);

    return 0;
}
```

## BPF Filtering

AF_PACKET sockets support classic BPF (cBPF) filters to accept only relevant
packets in kernel space, reducing the volume of data transferred to userspace:

```c
/* tcpdump -i eth0 port 80 → compiled BPF program */
struct sock_filter filter[] = { /* ... compiled BPF bytecode ... */ };
struct sock_fprog prog = {
    .len = sizeof(filter) / sizeof(filter[0]),
    .filter = filter,
};
setsockopt(fd, SOL_SOCKET, SO_ATTACH_FILTER, &prog, sizeof(prog));
```

For more advanced filtering, eBPF programs can be attached via `SO_ATTACH_BPF`.

### Common BPF Filter Examples

```bash
# tcpdump generates cBPF bytecode
# View BPF for a filter:
tcpdump -i eth0 -d "port 80"
# (000) ldh      [12]
# (001) jeq      #0x86dd          jt 2	jf 8
# (002) ldb      [20]
# (003) jeq      #0x6             jt 4	jf 19
# ...

# Compile BPF to code for use in C:
tcpdump -i eth0 -dd "port 80"
```

### eBPF Attachment

```c
/* Attach eBPF program (more powerful than cBPF) */
int prog_fd = bpf_load_program(BPF_PROG_TYPE_SOCKET_FILTER, ...);
setsockopt(fd, SOL_SOCKET, SO_ATTACH_BPF, &prog_fd, sizeof(prog_fd));
```

## AF_PACKET vs. AF_XDP

AF_XDP (Express Data Path), introduced in Linux 4.18, is the modern successor
for high-performance packet processing:

| Aspect          | AF_PACKET            | AF_XDP                      |
|-----------------|----------------------|-----------------------------|
| Hook point      | Above driver         | Driver-level (zero-copy)    |
| Performance     | Good (mmap ring)     | Excellent (UMEM, zero-copy) |
| Hardware offload| No                   | Some NICs support it        |
| Kernel bypass   | No                   | Yes (XDP_PASS drops to stack)|
| Maturity        | Stable, widely used  | Newer, fewer drivers        |
| Use case        | Capture, monitoring  | High-speed forwarding, NFV  |

AF_PACKET remains the standard for packet capture and monitoring. AF_XDP is
preferred for high-throughput packet processing where kernel bypass is acceptable.

## Performance Considerations

### Ring Buffer Sizing

- Larger rings absorb burst traffic without packet drops
- Block size should align with L2 cache line size or page size
- Monitor `tp_drops` in `tpacket_stats` for ring overflow detection

```c
/* Get drop statistics */
struct tpacket_stats stats;
socklen_t len = sizeof(stats);
getsockopt(fd, SOL_PACKET, PACKET_STATISTICS, &stats, &len);
printf("Packets: %u, Drops: %u\n", stats.tp_packets, stats.tp_drops);
```

### Busy Polling

Enable busy polling to reduce latency by spinning in the socket poll instead
of sleeping:

```bash
# Global busy poll setting
echo 50 > /proc/sys/net/core/busy_read  # microseconds

# Per-socket option
int val = 50;  /* microseconds */
setsockopt(fd, SOL_SOCKET, SO_BUSY_POLL, &val, sizeof(val));
```

### CPU Affinity

Pin capture threads to specific CPUs and use `FANOUT_CPU` for optimal cache
behavior and NUMA locality.

```bash
# Pin process to CPU 2
taskset -c 2 ./capture_program

# Or in code
cpu_set_t cpuset;
CPU_ZERO(&cpuset);
CPU_SET(2, &cpuset);
sched_setaffinity(0, sizeof(cpuset), &cpuset);
```

### Interrupt Coalescing

Modern NICs support interrupt coalescing, which batches multiple packets before
generating an interrupt. This reduces CPU overhead but increases latency. Tune
via `ethtool -C`.

```bash
# Disable interrupt coalescing for lowest latency
ethtool -C eth0 rx-usecs 0 rx-frames 0

# Set moderate coalescing
ethtool -C eth0 rx-usecs 50 rx-frames 16

# View current settings
ethtool -c eth0
```

### NUMA Considerations

```bash
# Check NIC NUMA node
cat /sys/class/net/eth0/device/numa_node
# 0

# Allocate ring buffer on same NUMA node
# Use mmap with MAP_POPULATE to pre-fault pages
# Or use numa_alloc_onnode() from libnuma
```

## Sending Packets

AF_PACKET can also send raw frames:

```c
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>

int send_raw_frame(int fd, const unsigned char *frame, size_t len,
                   int ifindex) {
    struct sockaddr_ll addr = {
        .sll_family = AF_PACKET,
        .sll_ifindex = ifindex,
        .sll_halen = ETH_ALEN,
    };
    /* Set destination MAC */
    memcpy(addr.sll_addr, frame, 6);

    return sendto(fd, frame, len, 0,
                  (struct sockaddr *)&addr, sizeof(addr));
}
```

### TX Ring Buffer

AF_PACKET also supports TX ring buffers for high-performance sending:

```c
struct tpacket_req req = {
    .tp_block_size = 4096,
    .tp_block_nr = 64,
    .tp_frame_size = 2048,
    .tp_frame_nr = (4096 * 64) / 2048,
};
setsockopt(fd, SOL_PACKET, PACKET_TX_RING, &req, sizeof(req));

/* Map TX ring */
void *ring = mmap(NULL, req.tp_block_size * req.tp_block_nr,
                  PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

/* Get next available frame */
struct tpacket_hdr *hdr = ring;
while (hdr->tp_status != TP_STATUS_AVAILABLE)
    ;  /* spin or poll */

/* Fill frame */
memcpy((uint8_t *)hdr + hdr->tp_net, frame_data, frame_len);

/* Send */
hdr->tp_status = TP_STATUS_SEND_REQUEST;
```

## Security Implications

### Capabilities

Creating `AF_PACKET` sockets requires `CAP_NET_RAW` or membership in a user
namespace with network access. In unprivileged containers (see
[user namespace security](../../containers/user-namespace-security.md)), this
capability may not be available.

```bash
# Check if user has CAP_NET_RAW
getpcaps $$ 2>/dev/null || capsh --print | grep "Current"

# Grant CAP_NET_RAW to a binary
setcap cap_net_raw+ep /usr/local/bin/capture_tool

# Run with capability
capsh --caps="cap_net_raw+eip" -- -c "./capture_program"
```

### Kernel Lockdown

When the kernel is in **lockdown integrity** mode (see
[Kernel Lockdown](../../security/lockdown.md)), `AF_PACKET` with `ETH_P_ALL`
is restricted because raw packet injection could compromise kernel integrity.

```bash
# Check lockdown status
cat /sys/kernel/security/lockdown
# [none] integrity confidentiality
```

### Promiscuous Mode Detection

Promiscuous mode can be detected by remote hosts through crafted ARP probes
or monitoring for unexpected responses to unicast frames addressed to other
MAC addresses.

```bash
# Detection method: send ARP for IP not on local host
# If host responds, it's in promiscuous mode
# This is how tools like nmap detect promiscuous hosts
```

### Packet Injection Risks

AF_PACKET allows sending arbitrary Ethernet frames, which can be used for:
- ARP spoofing
- VLAN hopping
- STP manipulation
- DHCP spoofing

```bash
# Mitigate: restrict CAP_NET_RAW
# Use seccomp to block AF_PACKET in containers
# Use network namespaces for isolation
```

## Usage Examples

### Minimal Packet Capture (C)

```c
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <arpa/inet.h>

int main(void) {
    int fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (fd < 0) { perror("socket"); return 1; }

    unsigned char buf[65535];
    while (1) {
        ssize_t n = recvfrom(fd, buf, sizeof(buf), 0, NULL, NULL);
        if (n > 0) {
            printf("Captured %zd bytes: %02x:%02x:%02x:%02x:%02x:%02x → "
                   "%02x:%02x:%02x:%02x:%02x:%02x  EtherType=0x%04x\n",
                   n,
                   buf[6], buf[7], buf[8], buf[9], buf[10], buf[11],
                   buf[0], buf[1], buf[2], buf[3], buf[4], buf[5],
                   ntohs(*(uint16_t *)(buf + 12)));
        }
    }
}
```

### TPACKET_V3 Capture with Timeout

```c
#include <sys/mman.h>
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <poll.h>

#define BLOCK_SIZE  (1 << 22)  /* 4 MiB */
#define BLOCK_NR    64
#define FRAME_SIZE  2048

int setup_ring_v3(int fd) {
    struct tpacket_req3 req = {
        .tp_block_size     = BLOCK_SIZE,
        .tp_block_nr       = BLOCK_NR,
        .tp_frame_size     = FRAME_SIZE,
        .tp_frame_nr       = (BLOCK_SIZE * BLOCK_NR) / FRAME_SIZE,
        .tp_retire_blk_tov = 100,  /* 100ms timeout */
        .tp_sizeof_priv    = 0,
        .tp_feature_req_word = 0,
    };
    return setsockopt(fd, SOL_PACKET, PACKET_RX_RING, &req, sizeof(req));
}

int main(void) {
    int fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    int version = TPACKET_V3;
    setsockopt(fd, SOL_PACKET, PACKET_VERSION, &version, sizeof(version));
    setup_ring_v3(fd);

    size_t ring_size = BLOCK_SIZE * BLOCK_NR;
    void *ring = mmap(NULL, ring_size, PROT_READ | PROT_WRITE,
                      MAP_SHARED, fd, 0);

    struct pollfd pfd = { .fd = fd, .events = POLLIN };
    while (poll(&pfd, 1, 500) > 0) {
        struct tpacket_block_desc *bdesc = ring;
        for (int i = 0; i < BLOCK_NR; i++) {
            if (bdesc->hdr.bh1.block_status & TP_STATUS_USER) {
                /* Process frames in block */
                bdesc->hdr.bh1.block_status = TP_STATUS_KERNEL;
            }
            bdesc = (void *)bdesc + BLOCK_SIZE;
        }
    }
}
```

### tcpdump Internals

`tcpdump` uses AF_PACKET with `TPACKET_V2` (or V3 on newer versions) and cBPF
filters. Its capture pipeline:

1. Opens `AF_PACKET` socket with `SOCK_RAW`
2. Sets `TPACKET_V2` or `V3` ring buffer
3. Compiles display filter to cBPF via libpcap and attaches via `SO_ATTACH_FILTER`
4. Maps ring buffer and processes frames in a tight loop

### Simple ARP Responder

```c
/* Respond to ARP requests using AF_PACKET */
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <arpa/inet.h>

int main(void) {
    int fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ARP));
    
    unsigned char buf[65535];
    while (1) {
        ssize_t n = recvfrom(fd, buf, sizeof(buf), 0, NULL, NULL);
        if (n < 42) continue;
        
        /* Check if ARP request */
        if (buf[12] == 0x08 && buf[13] == 0x06 &&  /* ARP */
            buf[20] == 0x00 && buf[21] == 0x01 &&  /* Request */
            /* Check target IP */
            buf[38] == 192 && buf[39] == 168 && 
            buf[40] == 1 && buf[41] == 100) {
            
            /* Build ARP reply */
            unsigned char reply[42];
            /* Swap MAC addresses */
            memcpy(reply, buf + 6, 6);      /* Dest = source MAC */
            memcpy(reply + 6, "\x00\x11\x22\x33\x44\x55", 6);  /* Our MAC */
            reply[12] = 0x08; reply[13] = 0x06;  /* ARP */
            /* ... fill ARP reply fields ... */
            
            struct sockaddr_ll addr = {
                .sll_family = AF_PACKET,
                .sll_ifindex = if_nametoindex("eth0"),
                .sll_halen = 6,
            };
            memcpy(addr.sll_addr, reply, 6);
            
            sendto(fd, reply, 42, 0, 
                   (struct sockaddr *)&addr, sizeof(addr));
        }
    }
}
```

## Common Pitfalls

1. **Forgetting promiscuous mode**: without it, you only see broadcast, multicast,
   and traffic addressed to the local interface.
2. **Undersized rings**: causes packet drops under burst traffic. Monitor
   `PACKET_STATISTICS` for drop counts.
3. **V1/V2/V3 confusion**: mixing struct types across versions leads to silent
   corruption or EINVAL errors.
4. **Endianness**: EtherType in the socket call must be in network byte order
   (`htons()`).
5. **Namespaces**: AF_PACKET sockets in containers are limited by the container's
   network namespace and capabilities.
6. **VLAN offload**: NIC may strip VLAN tags before delivery. Disable `rxvlan`
   offload for accurate captures.
7. **Large rings on 32-bit**: ring buffer size limited by virtual address space.
8. **CPU affinity**: without pinning, threads may migrate between NUMA nodes.

## Debugging

```bash
# Check AF_PACKET socket stats
cat /proc/net/packet

# Monitor packet drops
watch -n 1 'cat /proc/net/packet | grep -v "^sk"'

# Check interface promiscuous mode
ip link show eth0 | grep -c PROMISC

# Verify BPF filter is attached
# (no direct proc interface - use strace)
strace -e setsockopt ./capture_program 2>&1 | grep SO_ATTACH

# Check CAP_NET_RAW
grep -i cap /proc/self/status | grep CapEff
```

## See Also

- AFXDP — modern high-performance alternative
- eBPF — programmable packet filtering and processing
- [User Namespace Security](../../containers/user-namespace-security.md) —
  capability restrictions for raw sockets
- [Kernel Lockdown](../../security/lockdown.md) — security restrictions on raw
  packet access
- [Ring Buffer](../../debugging/ring-buffer.md) — the lockless ring buffer
  architecture underlying TPACKET

## Further Reading

- **Kernel source**: `net/packet/af_packet.c`, `include/uapi/linux/if_packet.h`
- **Documentation**: `Documentation/networking/packet_mmap.rst`
- **man page**: `packet(7)`
- **LWN article**: ["The TPACKET_V3 packet capture mechanism"](https://lwn.net/Articles/418388/)
- **Chetan Loke's paper**: "Scalable Packet Capture and Analysis" — original
  TPACKET_V3 design rationale
- **libpcap**: the canonical packet capture library, abstracting AF_PACKET across
  platforms
