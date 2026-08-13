# I/O Software Layers

## Overview

The I/O software stack is organized into well-defined layers, each with a specific responsibility. This layered architecture provides modularity, portability, and the ability to add new devices without modifying upper layers. The design follows the principle of **abstraction** — each layer hides the complexity of the layer below it.

## Motivation

Without layers, every application would need device-specific code for every peripheral. Imagine a program that has to understand SATA command sets just to read a file! The layered approach means:

- Applications use generic `read()`/`write()` calls
- The OS translates these into device-specific operations
- New devices can be added by writing a driver without changing the kernel or applications

## The Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   User-Level I/O Software                │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Libraries (stdio, printf, cin/cout)              │  │
│  │  Format I/O, buffering in user space              │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                    System Call Interface                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  read(), write(), open(), close(), ioctl()        │  │
│  │  Transition from user mode → kernel mode          │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│              Device-Independent OS Software              │
│  ┌───────────────────────────────────────────────────┐  │
│  │  • Uniform device naming (/dev/sda, /dev/tty0)    │  │
│  │  • Device protection and access control           │  │
│  │  • Buffering and caching                          │  │
│  │  • Allocation and deallocation of devices         │  │
│  │  • Error reporting                                │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                   Device Drivers                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  • Translate generic I/O requests → device cmds   │  │
│  │  • Handle device-specific register programming    │  │
│  │  • Manage device state and power                  │  │
│  │  • One driver per device type                     │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                 Interrupt Handlers                       │
│  ┌───────────────────────────────────────────────────┐  │
│  │  • Handle hardware interrupts from devices        │  │
│  │  • Wake up waiting processes                      │  │
│  │  • Schedule bottom-half processing (softirqs)     │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                    Hardware Layer                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Physical devices, controllers, buses              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Layer Details

### Layer 1: User-Level I/O Libraries

These provide convenient, high-level interfaces to applications.

```c
// C standard library (stdio)
FILE *fp = fopen("/tmp/data.txt", "r");
char buf[256];
fgets(buf, 256, fp);  // Buffered read with newline handling
fclose(fp);

// The library maintains its own buffer (typically 4KB-8KB)
// Multiple fgets() calls may be served from the buffer
// without triggering system calls
```

**Key functions**: `printf`, `scanf`, `fprintf`, `fread`, `fwrite`

**What happens**: The C library (`glibc` on Linux) maintains user-space buffers. When you call `printf("Hello")`, the string may be buffered in user space and only flushed to the kernel on `\n`, a full buffer, or explicit `fflush()`.

### Layer 2: System Call Interface

The boundary between user space and kernel space.

```c
// Direct system calls bypass stdio buffering
ssize_t n = read(fd, buf, count);   // Read from file descriptor
ssize_t n = write(fd, buf, count);  // Write to file descriptor
int fd = open("/dev/sda", O_RDONLY); // Open a device
int ret = ioctl(fd, BLKGETSIZE, &size); // Device-specific control

// System calls trigger a trap (software interrupt) to switch to kernel mode
// on x86: syscall instruction (or int 0x80 on older systems)
```

**File descriptors** are small non-negative integers that the kernel uses to index into a per-process file descriptor table, which points to open file structures, which eventually reference the device and driver.

```
Process FD Table     Open File Table      Inode/VNode
┌─────┐             ┌──────────────┐     ┌──────────────┐
│  0  │──stdin────►│ offset: 0    │────►│ /dev/tty0    │
│  1  │──stdout───►│ offset: 0    │────►│ /dev/tty0    │
│  2  │──stderr───►│ offset: 0    │────►│ /dev/tty0    │
│  3  │───────────►│ offset: 1024 │────►│ /tmp/data.txt│
│  4  │───────────►│ offset: 512  │────►│ /dev/sda     │
└─────┘             └──────────────┘     └──────────────┘
```

### Layer 3: Device-Independent OS Software

This layer provides services common to all devices:

**1. Uniform Naming**
```bash
# All devices appear as files in /dev/
/dev/sda        # First SCSI/SATA disk
/dev/ttyUSB0    # USB serial port
/dev/null       # Null device (discard writes, return EOF on read)
/dev/zero       # Returns zero bytes
/dev/random     # Random number generator
```

The OS maps device names to major/minor numbers:
```bash
ls -la /dev/sda
# brw-rw---- 1 root disk 8, 0 Aug  2 10:00 /dev/sda
#                major number ^  ^ minor number
# major = device driver type, minor = specific device instance
```

**2. Buffering and Caching**
- Kernel buffer cache caches recently accessed disk blocks
- Page cache caches file data in memory pages
- Read-ahead: kernel speculatively reads blocks that may be needed soon

**3. Error Reporting**
```c
// Kernel translates low-level errors to errno values
if (read(fd, buf, count) == -1) {
    perror("read");  // "read: Input/output error"
    // errno = EIO (5) — generic I/O error
}
```

**4. Device Allocation**
- Exclusive devices (printers) must be locked during use
- Shared devices (disks) can serve concurrent requests

### Layer 4: Device Drivers

The most hardware-specific layer. Each driver translates generic requests into device-specific operations.

```c
// Simplified Linux block device driver skeleton
static int mydisk_read(struct block_device *bdev, sector_t sector,
                       struct page *page) {
    // 1. Convert sector number to device-specific address
    // 2. Program device registers with command, address, count
    // 3. Start DMA transfer
    // 4. Wait for completion (or return and let interrupt handle it)
    return 0;
}

// Driver registers itself with the kernel
static struct block_device_operations mydisk_ops = {
    .owner = THIS_MODULE,
    .open  = mydisk_open,
    .release = mydisk_release,
};
```

### Layer 5: Interrupt Handlers

Handle asynchronous hardware signals.

```c
// Linux interrupt handler
static irqreturn_t mydisk_interrupt(int irq, void *dev_id) {
    struct mydisk_dev *dev = dev_id;
    
    // Read status register
    u32 status = readl(dev->regs + STATUS_REG);
    
    if (status & COMPLETION_BIT) {
        // Transfer complete — wake up waiting process
        complete(&dev->completion);
    }
    
    // Acknowledge interrupt to device
    writel(ACK_BIT, dev->regs + STATUS_REG);
    
    return IRQ_HANDLED;
}
```

## Tracing a Complete I/O Request

```
┌──────────────────────────────────────────────────────────────┐
│  Application: read(fd, buf, 4096)                            │
│     │                                                        │
│     ▼                                                        │
│  System Call Interface: sys_read()                           │
│     │  • Validate fd, check permissions                      │
│     │  • Look up file structure → inode → device             │
│     ▼                                                        │
│  Device-Independent Layer:                                   │
│     │  • Check page cache — HIT? Return cached data          │
│     │  • MISS: Allocate buffer, submit bio to block layer    │
│     ▼                                                        │
│  I/O Scheduler:                                              │
│     │  • Merge adjacent requests                             │
│     │  • Reorder for seek optimization                       │
│     ▼                                                        │
│  Device Driver (e.g., AHCI/SATA):                           │
│     │  • Program DMA engine with physical address            │
│     │  • Build command (READ DMA EXT)                        │
│     │  • Write to command slot in HBA memory                 │
│     │  • Ring doorbell register                              │
│     ▼                                                        │
│  Hardware:                                                   │
│     │  • Disk controller processes command                   │
│     │  • Head seeks to track, waits for sector               │
│     │  • DMA transfers data to memory                        │
│     │  • Controller raises interrupt                         │
│     ▼                                                        │
│  Interrupt Handler:                                          │
│     │  • Read completion status                              │
│     │  • Schedule bottom-half (softirq/tasklet)              │
│     ▼                                                        │
│  Bottom-Half:                                                │
│     │  • Update page cache                                   │
│     │  • Wake up process blocked on read()                   │
│     ▼                                                        │
│  Return to user space: read() returns 4096                   │
└──────────────────────────────────────────────────────────────┘
```

## Real-World Linux Examples

### Examining the I/O Stack

```bash
# View registered device drivers
ls /sys/bus/pci/drivers/
# ahci  e1000e  xhci_hcd  ...

# View block device drivers
cat /proc/devices
# Character devices:
#   4 tty
#   10 misc
# Block devices:
#   8 sd
#   9 md
# 253 device-mapper

# Trace a read() system call
strace -e trace=read cat /tmp/test.txt
# read(3, "Hello, World!\n", 131072) = 14

# View I/O statistics
iostat -x 1
# Device  r/s    w/s   rkB/s  wkB/s  await  %util
# sda     100.0  50.0  4000   2000   2.5    15.0
```

### The VFS Layer

```bash
# Linux VFS (Virtual File System) provides the device-independent layer
# All I/O goes through VFS, which dispatches to the correct driver

# View VFS cache statistics
cat /proc/meminfo | grep -E "Cached|Buffers"
# Buffers:     204800 kB
# Cached:     2048000 kB
```

### Kernel I/O Stack Tracing

```bash
# Use ftrace to trace I/O path
cd /sys/kernel/debug/tracing
echo block_rq_issue > set_event  # Trace block I/O requests
cat trace_pipe
# kworker/0:1-1234  [000]  1234.567890: block_rq_issue: 8,0 R 4096 () 12345678

# Use blktrace for detailed block I/O analysis
sudo blktrace -d /dev/sda -o - | blkparse -i -
```

## Interview Questions

### Beginner

**Q: Why do we need a layered I/O architecture?**
A: Layers provide abstraction, modularity, and portability. Applications don't need device-specific code. New devices can be supported by adding a driver without modifying the kernel or applications. Each layer has a clear responsibility, making the system easier to maintain and debug.

**Q: What is the role of the device-independent layer?**
A: It provides services common to all devices: uniform naming (`/dev/*`), buffering and caching, error reporting, device allocation/locking, and abstract device operations. This layer ensures that device drivers only need to implement device-specific logic.

### Intermediate

**Q: Explain the difference between blocking and non-blocking I/O. When would you use each?**
A:
- **Blocking I/O**: The calling process is suspended until the I/O operation completes. Simple to program but wastes CPU if the process has other work. Default mode for `read()`/`write()`.
- **Non-blocking I/O**: Returns immediately with whatever data is available (or `EAGAIN` if none). Used with event loops (`select()`, `poll()`, `epoll()`) for high-concurrency servers.
- **Asynchronous I/O (AIO)**: Process submits request and continues; kernel notifies when complete. Used for high-performance I/O (databases, `io_uring` on Linux).

```c
// Blocking
n = read(fd, buf, 4096);  // Blocks until data available

// Non-blocking
fcntl(fd, F_SETFL, O_NONBLOCK);
n = read(fd, buf, 4096);  // Returns immediately, may return -EAGAIN

// Async I/O (io_uring)
io_uring_prep_read(sqe, fd, buf, 4096, 0);
io_uring_submit(&ring);  // Non-blocking submission
io_uring_wait_cqe(&ring, &cqe);  // Wait for completion
```

### FAANG-Level

**Q: Linux has both the page cache and the buffer cache. Why both? What is the relationship?**
A:
- **Buffer cache**: Caches raw disk blocks (used by the block layer). Operates on `buffer_head` structures.
- **Page cache**: Caches file data as pages. Operates on `page` structures mapped from files.

In modern Linux (2.4+), they are unified. File I/O goes through the page cache; metadata (superblocks, inodes) goes through the buffer cache, but the underlying physical pages are shared. This avoids double-caching.

When you `read()` a file:
1. Kernel checks page cache for the file's page
2. If found, returns data directly (cache hit)
3. If not, allocates a page, submits a bio (block I/O) to read from disk
4. The bio goes through the I/O scheduler → device driver → hardware

**Key insight**: `mmap()` maps page cache pages directly into the process address space, avoiding the `copy_to_user()` overhead of `read()`.

## Common Mistakes

1. **Thinking `read()`/`write()` always go to disk**: The page cache means most reads are served from memory. Only cache misses trigger disk I/O.
2. **Confusing user-space and kernel-space buffers**: `stdio` has its own buffer in user space; the kernel has separate buffers. `fflush()` flushes user-space buffer to kernel; `fsync()` flushes kernel buffers to disk.
3. **Assuming layers are always sequential**: Modern I/O paths (like `io_uring`) can bypass some layers for performance.
4. **Ignoring the VFS abstraction**: All I/O goes through VFS, even device I/O. Understanding VFS is critical for understanding Linux I/O.

## Summary

| Layer | Responsibility | Example |
|-------|---------------|---------|
| User Libraries | Format, user-space buffering | `printf`, `fread` |
| System Call Interface | Kernel entry, fd management | `read()`, `write()`, `open()` |
| Device-Independent | Naming, caching, error handling | VFS, page cache |
| Device Drivers | Device-specific commands | `ahci`, `e1000e` |
| Interrupt Handlers | Async completion handling | IRQ handlers |
| Hardware | Physical data transfer | Controllers, buses, devices |

## Cross-References

- [Hardware](hardware.md) — I/O hardware fundamentals
- [Device Drivers](device-drivers.md) — Deep dive into driver architecture
- [Interrupts](interrupts.md) — Interrupt handling mechanisms
- [Buffering](buffering.md) — Buffering and caching strategies
- [DMA](dma.md) — Direct Memory Access


## Cross References

- [Device Drivers](device-drivers.md)
- [VFS](../filesystems/vfs.md)
- [Buffering](buffering.md)
- [I/O Architecture](../../arch/io/README.md)
