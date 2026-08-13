# Buffering

## Overview

Buffering is the technique of using intermediate memory areas (buffers) to hold data while it is being transferred between two devices or between a device and a process. Buffering is essential because producers and consumers of data often operate at different speeds, in different-sized units, or with different timing requirements.

## Motivation

Why do we need buffering?

1. **Speed mismatch**: A CPU writes data at GHz speeds; a disk writes at ~100 MB/s. Without buffering, the CPU would block on every byte.
2. **Block vs. stream**: Disks transfer data in fixed-size blocks (e.g., 4KB); applications may read character-by-character. Buffers reconcile these units.
3. **Copy semantics**: When a process writes data, it expects the `write()` to return immediately. The OS buffers the data and writes it to the device asynchronously.
4. **Double buffering**: Allows the CPU to process one buffer while the device fills/empties another.

## Buffering Strategies

### 1. Single Buffering

The simplest approach: one buffer is used for the transfer.

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│         │    │  Single  │    │         │
│ Device  │───►│  Buffer  │───►│ Process │
│         │    │ (4 KB)   │    │         │
└─────────┘    └─────────┘    └─────────┘

Timeline:
Device: [Fill Buffer] [Wait] [Fill Buffer] [Wait]
Process:         [Process]         [Process]
                 [Wait]            [Wait]
```

**Problem**: The process and device must take turns. If the device fills the buffer, the process must wait, and vice versa. This is essentially single-producer, single-consumer with one slot.

### 2. Double Buffering

Two buffers alternate: while one is being filled by the device, the other is being processed by the CPU.

```
┌─────────┐    ┌─────────┐    ┌─────────┐
│         │    │ Buffer A │    │         │
│ Device  │───►│ (4 KB)   │───►│         │
│         │    ├─────────┤    │ Process │
│         │    │ Buffer B │    │         │
│         │    │ (4 KB)   │    │         │
└─────────┘    └─────────┘    └─────────┘

Timeline:
Device:  [Fill A] [Fill B] [Fill A] [Fill B]
Process:      [Proc A] [Proc B] [Proc A]
         ^ Overlap! Device and CPU work simultaneously
```

**Advantage**: Overlaps I/O with computation. While the device fills buffer B, the CPU processes buffer A.

**Used in**: Video frame buffers (back-buffering), audio streaming, GPU rendering (front/back buffers).

### 3. Circular Buffer (Ring Buffer)

A fixed-size circular queue where the producer writes to the head and the consumer reads from the tail.

```
        ┌───────────────────────────┐
        │                           │
        ▼                           │
    ┌─────┬─────┬─────┬─────┬─────┐
    │  A  │  B  │  C  │  D  │  E  │
    └─────┴─────┴─────┴─────┴─────┘
        ▲                 ▲
      Tail              Head
    (Consumer)        (Producer)

    Consumer reads: A → B → ...
    Producer writes: F, G, ... (wraps around)
```

**Key properties**:
- Fixed size, no memory allocation during operation
- Producer and consumer can operate at different rates
- Full/empty detection via count, flags, or reserved slot

```c
// Circular buffer implementation
#define BUF_SIZE 1024

struct circ_buf {
    char data[BUF_SIZE];
    int head;  // Write position
    int tail;  // Read position
    int count; // Number of items
};

void produce(struct circ_buf *buf, char c) {
    while (buf->count == BUF_SIZE) ; // Wait if full (spinlock)
    buf->data[buf->head] = c;
    buf->head = (buf->head + 1) % BUF_SIZE;
    buf->count++;
}

char consume(struct circ_buf *buf) {
    while (buf->count == 0) ; // Wait if empty
    char c = buf->data[buf->tail];
    buf->tail = (buf->tail + 1) % BUF_SIZE;
    buf->count--;
    return c;
}
```

**Used in**: Kernel network buffers (sk_buff queues), serial port buffers, audio streaming, Linux kernel tracing (`ftrace` ring buffer).

### 4. Buffer Pool

A pool of buffers managed by the OS, allocated and released dynamically as needed.

```
┌──────────────────────────────────────────┐
│              Buffer Pool                  │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐       │
│  │ Buf │ │ Buf │ │ Buf │ │ Buf │ ...    │
│  │  0  │ │  1  │ │  2  │ │  3  │       │
│  └─────┘ └─────┘ └─────┘ └─────┘       │
│      ▲        ▲        ▲                │
│      │        │        │                │
│   Request  Request  Request              │
│    from     from     from                │
│   Disk     Network   Pipe                │
└──────────────────────────────────────────┘
```

**Linux implementation**: The kernel uses `kmalloc()` and `kmem_cache` (slab allocator) to manage buffer pools. The `bio` (block I/O) structures and `sk_buff` (network) structures are allocated from dedicated caches.

```bash
# View kernel slab allocator statistics
cat /proc/slabinfo
# name            <active_objs> <num_objs> <objsize> <objperslab> <pagesperslab>
# ext4_inode_cache    12345    12500      1024       16          4
# dentry              50000    51200       192       42          2
# bio                  1000     1024       176       23          1
```

## Buffering in the Linux Kernel

### Page Cache

The primary buffer mechanism for file I/O in Linux.

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  User Space │     │   Page Cache    │     │   Block Dev  │
│             │     │                 │     │              │
│  read() ────┼────►│  ┌───────────┐  │     │              │
│             │     │  │ Page: 4KB │  │────►│  Disk Block  │
│  write() ───┼────►│  │ (cached)  │  │     │              │
│             │     │  └───────────┘  │     │              │
└─────────────┘     └─────────────────┘     └──────────────┘

read() path:
1. Check page cache → HIT? Return data (no disk I/O!)
2. MISS? Allocate page, read from disk, cache it, return to user

write() path:
1. Write to page cache (mark page dirty)
2. write() returns immediately to user
3. Kernel flushes dirty pages to disk later (writeback)
```

### Write-Through vs Write-Back

```
Write-Through:
  write() ──► Page Cache ──► Disk ──► return
  ✓ Data always on disk
  ✗ Slower (every write hits disk)

Write-Back (Linux default):
  write() ──► Page Cache ──► return (immediately)
              [Dirty page in cache]
              ... later (writeback) ...
              Page Cache ──► Disk
  ✓ Fast writes
  ✗ Risk of data loss on crash (dirty pages lost)
  ✓ Linux mitigates with periodic writeback (every 30s by default)
```

```bash
# View dirty page writeback settings
cat /proc/sys/vm/dirty_expire_centisecs   # 3000 (30 seconds)
cat /proc/sys/vm/dirty_writeback_centisecs # 500 (5 seconds)
cat /proc/sys/vm/dirty_ratio              # 20 (20% of RAM)
cat /proc/sys/vm/dirty_background_ratio   # 10 (10% of RAM)

# Force flush all dirty pages
sync

# View current dirty pages
grep -E "Dirty|Writeback" /proc/meminfo
# Dirty:           1234 kB
# Writeback:          0 kB
```

### Direct I/O (Bypassing Buffering)

```c
// Open file with O_DIRECT to bypass page cache
int fd = open("/dev/sda", O_RDONLY | O_DIRECT);

// Buffer must be aligned (typically 512 bytes or 4KB)
void *buf;
posix_memalign(&buf, 4096, 4096);
read(fd, buf, 4096);  // Direct DMA to/from user buffer

// Use cases: Databases (MySQL, PostgreSQL), VMs — they manage their own cache
```

## Real-World Applications

### Network Buffering (TCP)

```
┌──────────┐  Socket Buffer  ┌──────────┐  NIC Ring Buffer  ┌──────┐
│  App     │  (sndbuf)       │  Kernel  │  (TX ring)        │  NIC │
│  send()──┼────────────────►│  TCP ────┼──────────────────►│      │
│          │                 │  Stack   │                   │      │
└──────────┘                 └──────────┘                   └──────┘

Socket buffer: 128KB-16MB (configurable via SO_SNDBUF)
NIC ring buffer: 256-4096 descriptors
```

```bash
# View socket buffer sizes
sysctl net.core.rmem_max    # Max receive buffer
sysctl net.core.wmem_max    # Max send buffer
sysctl net.ipv4.tcp_rmem    # TCP receive buffer: min default max
sysctl net.ipv4.tcp_wmem    # TCP send buffer: min default max

# Example:
# net.ipv4.tcp_rmem = 4096 131072 6291456
# min=4KB, default=128KB, max=6MB
```

### Pipe Buffering

```bash
# Linux pipe buffer: 64KB (since kernel 2.6.11)
# Can be changed via fcntl(fd, F_SETPIPE_SZ, size) up to 1MB

cat /proc/sys/fs/pipe-max-size  # 1048576 (1MB)

# Example: Large pipe transfer
dd if=/dev/zero bs=1M count=100 | wc -c
# Data flows through 64KB pipe buffer; dd and wc run concurrently
```

### stdio Buffering Modes

```c
// Three stdio buffering modes:

// 1. Fully buffered (default for files)
// Buffer flushed when full, on fflush(), or on fclose()
FILE *fp = fopen("file.txt", "w");  // Fully buffered

// 2. Line buffered (default for terminals)
// Buffer flushed on newline, fflush(), or fclose()
printf("Hello\n");  // Flushed immediately (newline)

// 3. Unbuffered (stderr)
// Every character written immediately
fprintf(stderr, "Error!\n");  // No buffering

// Change buffering mode:
setvbuf(fp, buf, _IOFBF, 4096);  // Fully buffered
setvbuf(fp, buf, _IOLBF, 4096);  // Line buffered
setvbuf(fp, buf, _IONBF, 0);     // Unbuffered
```

## Interview Questions

### Beginner

**Q: What is buffering and why is it needed?**
A: Buffering uses intermediate memory areas to hold data during transfer between devices or between a device and a process. It's needed to handle speed mismatches (CPU vs disk), reconcile different data sizes (blocks vs streams), and allow asynchronous operation where the producer and consumer don't have to synchronize on every byte.

**Q: What is the difference between double buffering and circular buffering?**
A: Double buffering uses exactly two buffers that alternate — one is filled while the other is drained. It's simple and good for steady streaming. Circular buffering uses a ring of N buffers with a head and tail pointer, allowing more flexibility in handling bursty traffic and varying rates. Circular buffers are more general-purpose and are the standard in kernel I/O.

### Intermediate

**Q: Explain write-back caching and its implications for data integrity.**
A: In write-back caching, `write()` returns after copying data to the page cache, without waiting for the data to reach disk. The kernel later flushes dirty pages to disk asynchronously. This gives fast writes but risks data loss on power failure (dirty pages in RAM are lost). Linux mitigates this with:
- Periodic writeback (default every 30 seconds)
- `fsync()` / `fdatasync()` to force flush specific files
- Journaling filesystems (ext4) that can recover metadata

Applications requiring durability (databases) use `O_DIRECT` + `fsync()` or `O_SYNC`.

**Q: When would you use `O_DIRECT` and what are the tradeoffs?**
A: `O_DIRECT` bypasses the page cache, transferring data directly between the disk and user-space buffers via DMA. Use it when:
- The application has its own cache (databases like PostgreSQL, MySQL)
- You don't want to pollute the page cache with large sequential scans
- You need precise control over when data hits disk

Tradeoffs:
- Buffers must be aligned to block size (typically 512B or 4KB)
- No read-ahead or caching benefits from the kernel
- Can be slower for small random reads (no cache hits)
- Requires the application to handle its own caching

### FAANG-Level

**Q: Design a buffering strategy for a real-time video streaming server that must handle 4K video at 60fps to multiple clients with varying network speeds.**

A:

```
Architecture:

Source (4K60) → Decode Buffer → Encode Buffer → Per-Client Ring Buffers → Network

Buffer Design:
1. Source Buffer (Double Buffer): Two frame buffers for decode/render overlap
2. Encode Buffer (Single): One frame at a time (encode is fast)
3. Per-Client Ring Buffer (Circular, 3-10 frames):
   - Fast clients: Buffer stays near empty (consuming fast)
   - Slow clients: Buffer fills up; drop oldest frames if full
   - Back-pressure: If buffer full, signal encoder to lower quality

Adaptive Bitrate:
- Monitor each client's ring buffer fill level
- If fill > 80%: Switch to lower quality (1080p30)
- If fill < 20%: Switch to higher quality (4K60)
- Use BBR-like algorithm for rate estimation

Memory Layout:
- Use huge pages (2MB) for frame buffers to reduce TLB misses
- Zero-copy: mmap() NIC TX buffers, write encoded frames directly
- Avoid copies between stages using buffer passing (like Linux's bio chains)
```

## Common Mistakes

1. **Forgetting about write-back caching**: Writing to a file doesn't guarantee data is on disk. Always `fsync()` for critical data.
2. **Buffer overflow**: Writing past the end of a buffer corrupts adjacent memory. Always validate buffer sizes.
3. **Double buffering everywhere**: Not always needed. For latency-sensitive applications, single or zero buffering may be better.
4. **Ignoring buffer alignment with O_DIRECT**: Unaligned buffers cause `EINVAL`. Use `posix_memalign()`.
5. **Not handling partial reads/writes**: A `read()` may return fewer bytes than requested. Always loop until all data is transferred.

## Summary

| Strategy | Buffers | Overlap? | Use Case |
|----------|---------|----------|----------|
| Single | 1 | No | Simple, low-throughput |
| Double | 2 | Yes | Streaming (video, audio) |
| Circular | N | Yes | Variable-rate I/O, kernel buffers |
| Pool | N (dynamic) | Yes | General kernel I/O |

| Mechanism | Buffer Size | Purpose |
|-----------|------------|---------|
| Page Cache | RAM pages (4KB) | File data caching |
| Pipe Buffer | 64KB-1MB | Inter-process communication |
| Socket Buffer | 128KB-16MB | Network I/O |
| stdio Buffer | 4KB-8KB | User-space file I/O |
| NIC Ring Buffer | 256-4096 descriptors | Network packet buffering |

## Cross-References

- [Software Layers](software-layers.md) — Where buffering fits in the I/O stack
- [DMA](dma.md) — How buffers are used with DMA transfers
- [Disk Scheduling](disk-scheduling.md) — How buffered requests are scheduled
- [Device Drivers](device-drivers.md) — How drivers manage buffers


## Cross References

- [I/O Software Layers](software-layers.md)
- [Buffer Pool](../../dbms/caching/buffer-pool.md)
- [Buffer Management](../../dbms/storage/buffer-management.md)
- [Cache Hierarchy](../../arch/memory-hierarchy/README.md)
