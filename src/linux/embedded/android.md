# Android Kernel Internals

Android runs a modified Linux kernel with subsystems that do not exist in
mainline. This chapter covers the four pillars of Android-specific kernel
infrastructure: **Binder IPC**, **Anonymous Shared Memory (ashmem)**,
**wakelocks**, and the **Generic Kernel Image (GKI)**. Understanding these
components is essential for anyone porting Android to new hardware or
debugging system-level performance issues.

---

## 1. Architecture Overview

```mermaid
flowchart TB
    subgraph User Space
        APP[Android App]
        FW[Framework Services]
        ZYG[Zygote / ART]
    end
    subgraph Kernel Space
        BINDER[Binder Driver]
        ASHMEM[ashmem / memfd]
        WAKE[Wakelocks]
        GKI[GKI Module Interface]
        VENDOR[Vendor Modules]
    end
    APP -->|IPC| BINDER
    FW -->|IPC| BINDER
    APP -->|shared memory| ASHMEM
    FW -->|power mgmt| WAKE
    GKI -->|loadable modules| VENDOR
    BINDER --> VENDOR
```

---

## 2. Binder IPC

### 2.1 What Is Binder?

Binder is Android's primary inter-process communication (IPC) mechanism. It is
a character device (`/dev/binder`) that implements a custom RPC protocol on top
of a kernel driver. Every Android system service—Activity Manager, Window
Manager, SurfaceFlinger—communicates via Binder.

### 2.2 Why Not POSIX IPC?

| Feature | POSIX (pipes/sockets/shared mem) | Binder |
|---------|-----------------------------------|--------|
| Copy operations | 2 (sender → kernel → receiver) | 1 (kernel maps pages) |
| Object references | Not natively supported | Marshalled object handles |
| Security | Manual credential passing | UID/PID per-transaction |
| Thread model | Fork / pthread | Thread pool per process |

Binder achieves **one-copy IPC** by mapping pages from the sender's address
space directly into the receiver's.

### 2.3 Kernel Driver Internals

The Binder driver lives in `drivers/android/binder.c`. Key data structures:

```c
/* Simplified — actual kernel struct is more complex */
struct binder_proc {
    struct list_head threads;       /* binder_thread list */
    struct list_head nodes;         /* binder_node list */
    struct rb_root refs_by_desc;    /* binder_ref by descriptor */
    struct rb_root refs_by_node;    /* binder_ref by node */
    struct task_struct *tsk;        /* owning task */
    pid_t pid;
};

struct binder_thread {
    struct binder_proc *proc;
    struct rb_node rb_node;
    int looper;                     /* state flags */
    struct binder_transaction *transaction_stack;
    struct list_head todo;          /* pending work items */
};
```

#### Transaction Flow

```mermaid
sequenceDiagram
    participant Client
    participant Driver as Binder Driver
    participant Server

    Client->>Driver: ioctl(BINDER_WRITE_READ)
    Note right of Client: BC_TRANSACTION
    Driver->>Driver: Allocate buffer in server's space
    Driver->>Driver: Copy data (1 copy)
    Driver->>Server: Wake server thread
    Server->>Driver: BC_REPLY
    Driver->>Client: Copy reply (1 copy)
    Client->>Client: Return to caller
```

### 2.4 ioctl Commands

```bash
# Key ioctl numbers (defined in binder.h)
BINDER_SET_CONTEXT_MGR   # Register as context manager (servicemanager)
BINDER_WRITE_READ        # Main transaction ioctl
BINDER_SET_MAX_THREADS   # Set thread pool size
BINDER_VERSION           # Query driver version
```

### 2.5 The servicemanager

The `servicemanager` process registers as the context manager and acts as the
name server. Clients look up services by name:

```cpp
// C++ client example
sp<IServiceManager> sm = defaultManager();
sp<IBinder> binder = sm->getService(String16("activity"));
```

### 2.6 HwBinder and VNDK Binder

Android 8.0+ splits Binder into three domains:

| Domain | Device Node | Purpose |
|--------|-------------|---------|
| Framework Binder | `/dev/binder` | App ↔ system services |
| HwBinder | `/dev/hwbinder` | HAL ↔ vendor processes |
| VndBinder | `/dev/vndbinder` | Vendor ↔ vendor |

This separation enforces the Treble architecture, preventing vendor code from
directly calling framework services.

---

## 3. Anonymous Shared Memory (ashmem)

### 3.1 Overview

`ashmem` is Android's shared memory subsystem. In modern kernels (5.x+), it is
backed by `memfd_create()` for mainline compatibility.

```bash
# ashmem character device
ls -la /dev/ashmem
```

### 3.2 Key Features

- **Pinning / unpinning** — pages can be marked as pinned (non-evictable) or
  unpinned (can be reclaimed under memory pressure)
- **Purging** — the kernel can reclaim unpinned pages when the system is low on
  memory, a feature not available in POSIX shared memory
- **Sealing** — similar to `F_SEAL_*` on memfd, prevents further modifications

### 3.3 Usage from User Space

```c
#include <linux/ashmem.h>
#include <sys/ioctl.h>
#include <sys/mman.h>

int fd = open("/dev/ashmem", O_RDWR);
ioctl(fd, ASHMEM_SET_NAME, "my_shared_region");
ioctl(fd, ASHMEM_SET_SIZE, 4096);

void *ptr = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
// Use ptr for shared data
```

### 3.4 Migration to memfd

Android 12+ encourages `memfd_create()` for new code:

```c
#include <sys/memfd.h>

int fd = memfd_create("my_region", MFD_ALLOW_SEALING);
ftruncate(fd, 4096);
void *ptr = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
```

The kernel's `shmem.c` provides the backing for both mechanisms.

---

## 4. Wakelocks

### 4.1 Concept

Wakelocks prevent the CPU from entering deep sleep states. Android uses them
to keep the device awake during critical operations (e.g., receiving a push
notification, playing audio).

### 4.2 Kernel Wakelocks

The kernel exposes wakelocks via `/sys/power/wake_lock` and
`/sys/power/wake_unlock`:

```bash
# Acquire a kernel wakelock
echo "my_lock" > /sys/power/wake_lock

# Release it
echo "my_lock" > /sys/power/wake_unlock

# List active wakelocks
cat /sys/power/wake_lock
```

### 4.3 Wake Sources (Modern Kernels)

In Linux 4.x+, the kernel renamed "wakelocks" to **wake sources**. The user-space
interface remains, but internally:

```c
/* Modern kernel */
struct wakeup_source {
    struct wakeup_source *ws;
    ktime_t total_time;
    ktime_t max_time;
    unsigned long event_count;
    unsigned long active_count;
};
```

### 4.4 User-Space Power Management

Android's `PowerManager` service translates app requests into kernel wakelocks:

```java
PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
PowerManager.WakeLock wl = pm.newWakeLock(
    PowerManager.PARTIAL_WAKE_LOCK, "myapp:mytag");
wl.acquire();
// ... do work ...
wl.release();
```

### 4.5 Debugging Wakelocks

```bash
# Dumpsys shows user-space and kernel wakelocks
dumpsys power | grep -A 20 "Wake Locks"

# Battery historian for visual analysis
bugreport > bugreport.zip
# Upload to https://bathist.ef.lc/
```

---

## 5. Generic Kernel Image (GKI)

### 5.1 The Problem

Before GKI, every Android device shipped a custom kernel fork. Vendors modified
hundreds of files, making kernel updates nearly impossible. Security patches
took months to propagate.

### 5.2 GKI Architecture

GKI (Android 11+) separates the kernel into:

| Component | Owner | Update Path |
|-----------|-------|-------------|
| GKI kernel | Google | OTA via Google Play system updates |
| Vendor modules | SoC vendor | Shipped with vendor image |
| System-specific code | OEM | Removed from kernel |

```mermaid
flowchart LR
    subgraph GKI["GKI Kernel (Google)"]
        CORE[Core Linux]
        ANDROID[Android-specific patches]
        KMI[Kernel Module Interface]
    end
    subgraph Vendor["Vendor Modules"]
        GPU[GPU Driver]
        CAM[Camera Driver]
        DISP[Display Driver]
        WIFI[WiFi Driver]
    end
    KMI -.->|stable ABI| GPU
    KMI -.->|stable ABI| CAM
    KMI -.->|stable ABI| DISP
    KMI -.->|stable ABI| WIFI
```

### 5.3 Kernel Module Interface (KMI)

GKI guarantees a stable KMI — a list of exported symbols that vendor modules
can depend on. This list is frozen for each GKI version.

```bash
# View the KMI symbol list
cat /proc/kallsyms | grep -E "EXPORT_SYMBOL"

# Check if a module uses only KMI symbols
modprobe --show-depends my_vendor_module.ko
```

### 5.4 Building GKI

```bash
# Clone GKI kernel
git clone https://android.googlesource.com/kernel/common -b android-gki-5.10

# Build
export ARCH=arm64
make gki_defconfig
make -j$(nproc)

# Output: out/arch/arm64/boot/Image.gz
```

### 5.5 Vendor Module Development

```makefile
# Kbuild for a vendor module
obj-m += my_camera_driver.o
my_camera_driver-objs := camera_core.o camera_isp.o

# Must link against GKI-exported symbols only
```

```bash
# Build vendor module against GKI headers
make -C /path/to/gki/kernel M=$(pwd) modules
```

### 5.6 GKI Versioning

| GKI Version | Kernel Branch | Android Version |
|-------------|---------------|-----------------|
| GKI 1.0 | android-5.4 | Android 11 |
| GKI 2.0 | android-5.10, 5.15 | Android 12–13 |
| GKI 2.0+ | android-6.1, 6.6 | Android 14–15 |

---

## 6. Android Kernel Modules

### 6.1 Loadable Modules

Android devices use kernel modules extensively for hardware drivers:

```bash
# List loaded modules
lsmod

# Module configuration
cat /vendor/lib/modules/modules.load
```

### 6.2 Module Loading Order

Android uses a `modules.load` file to specify boot-time module loading order:

```
# /vendor/lib/modules/modules.load
vendor/lib/modules/mtk-scp.ko
vendor/lib/modules/mtk-adsp.ko
vendor/lib/modules/mtk-snd-common.ko
```

### 6.3 Module Signing

GKI requires vendor modules to be signed:

```bash
# Sign a module
scripts/sign-file sha256 certs/signing_key.pem \
    certs/signing_key.x509 my_module.ko
```

---

## 7. Device Tree Overlays for Android

Android devices use device tree blobs (DTBs) to describe hardware. GKI
separates the base DTB from vendor overlays:

```dts
/* Vendor overlay example */
/ {
    fragment@0 {
        target = <&i2c3>;
        __overlay__ {
            #address-cells = <1>;
            #size-cells = <0>;
            touchscreen@38 {
                compatible = "vendor,ts-controller";
                reg = <0x38>;
                interrupt-parent = <&gpio>;
                interrupts = <12 0>;
            };
        };
    };
};
```

---

## 8. Debugging Android Kernel Issues

### 8.1 Common Tools

```bash
# Kernel log
dmesg | grep -i binder
dmesg | grep -i ashmem

# Binder debug
cat /sys/kernel/debug/binder/state
cat /sys/kernel/debug/binder/transactions
cat /sys/kernel/debug/binder/stats

# Power debugging
cat /sys/kernel/debug/wakeup_sources
dumpsys batterystats
```

### 8.2 Systrace / Perfetto

```bash
# System-level tracing
perfetto -c /data/misc/perfetto-configs/config.pbtx -o trace.pb
# View at https://ui.perfetto.dev/
```

---

## 9. DMA-BUF Heaps and Buffer Sharing

### From ION to DMA-BUF Heaps

Android historically used the **ION** allocator for shared memory between the CPU, GPU, camera, and display. ION was an Android-specific kernel driver (`drivers/staging/android/ion`). Starting with Android 12 and kernel 5.6+, ION is replaced by the mainline **DMA-BUF Heaps** framework.

```mermaid
graph LR
    subgraph "Legacy (Android <12)"
        ION[ION Allocator]
        ION -->|"alloc"| HEAP_SYSTEM["system heap"]
        ION -->|"alloc"| HEAP_CMA["CMA heap"]
        ION -->|"alloc"| HEAP_CARVEOUT["carveout heap"]
    end
    subgraph "Modern (Android 12+)"
        DMABUF["DMA-BUF Heaps"]
        DMABUF -->|"alloc"| HEAP_SYSTEM2["system heap"]
        DMABUF -->|"alloc"| HEAP_CMA2["CMA heap"]
        DMABUF -->|"alloc"| HEAP_SECURE["secure heap"]
    end
```

### DMA-BUF Heaps in Practice

```bash
# List available DMA-BUF heaps
ls /dev/dma_heap/
# system  system-uncached  cma

# Allocate from user space (Android uses libdmabufheap)
# C code example:
#include <linux/dma-heap.h>
#include <sys/ioctl.h>

int heap_fd = open("/dev/dma_heap/system", O_RDWR);
struct dma_heap_allocation_data data = {
    .len = 4096 * 256,  /* 1MB */
    .fd_flags = O_RDWR | O_CLOEXEC,
};
ioctl(heap_fd, DMA_HEAP_IOCTL_ALLOC, &data);
int buf_fd = data.fd;  /* DMA-BUF file descriptor */

# Check DMA-BUF usage
cat /sys/kernel/debug/dma_buf/bufinfo
# Or with dmabuf_dump (Android tool)
dmabuf_dump
```

### Buffer Sharing Between Subsystems

DMA-BUF enables zero-copy sharing between GPU, camera, display, and codec:

```mermaid
sequenceDiagram
    participant Camera
    participant DMA as DMA-BUF
    participant GPU
    participant Display

    Camera->>DMA: Allocate buffer (DMA-BUF heap)
    Camera->>DMA: Write frame data
    Camera->>GPU: Export DMA-BUF fd
    GPU->>DMA: Import and process (GPU shader)
    GPU->>Display: Export DMA-BUF fd
    Display->>DMA: Import and scan out
    Note over Camera,Display: Zero-copy: same physical pages used throughout
```

## 10. Android Kernel Security Model

### SELinux in Android

Android enforces mandatory access control via **SELinux** in enforcing mode. Every process, file, socket, and IPC endpoint has a security context:

```bash
# View SELinux status
getenforce
# Enforcing

# View process context
ps -Z
# u:r:system_server:s0     system    1234 567 ...
# u:r:platform_app:s0:...  u0_a12   5678 567 ...

# View file context
ls -Z /system/bin/app_process
# u:object_r:zygote_exec:s0 /system/bin/app_process

# SELinux policy denials (audit log)
logcat | grep "avc: denied"
# avc: denied { read } for name="config" dev="dm-0" ...
# scontext=u:r:untrusted_app:s0:... tcontext=u:object_r:system_data_file:s0
```

### Android Security Features

| Feature | Description | Kernel Component |
|---------|-------------|------------------|
| SELinux | Mandatory access control | LSM hooks |
| seccomp-bpf | Syscall filtering | `kernel/seccomp.c` |
| Verified Boot | Kernel integrity | dm-verity |
| dm-verity | Block-level filesystem integrity | `drivers/md/dm-verity.c` |
| Namespace isolation | App sandboxing | PID/network/mount namespaces |
| MTE | Memory Tagging Extension | ARMv8.5-A hardware |

### dm-verity

dm-verity provides read-only filesystem integrity verification. The kernel checks every block read against a Merkle tree hash:

```bash
# dm-verity block device mapper
# Verity table format:
# <version> <dev> <hash_dev> <data_block_size> <hash_block_size>
# <num_data_blocks> <hash_start_block> <algorithm> <root_hash> <salt>

# View dm-verity device
dmsetup table
# 0 12345678 verity 1 /dev/sda /dev/sda 4096 4096 1543209 1 sha256 ...

# If verification fails, the kernel logs:
dmesg | grep verity
# verity: sha256 verification failed
# verity: block 12345: expected ...
```

## 11. Android Kernel Debugging Tools

### Perfetto

Perfetto is Android's system-wide tracing tool, replacing systrace:

```bash
# Capture a trace with Perfetto
perfetto -c - --txt <<EOF
buffers: {
    size_kb: 65536
    fill_policy: RING_BUFFER
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "power/cpu_frequency"
            ftrace_events: "binder/binder_transaction"
        }
    }
}
duration_ms: 10000
EOF
# View at https://ui.perfetto.dev/

# Kernel-level tracing
perfetto -c config.pbtx -o /data/misc/perfetto-traces/trace.pb
```

### Binder Debugging

```bash
# View binder state
cat /sys/kernel/debug/binder/state
# Shows all binder procs, threads, nodes, and transactions

# View binder transactions
cat /sys/kernel/debug/binder/transactions

# View binder statistics
cat /sys/kernel/debug/binder/stats

# View binder per-process info
cat /sys/kernel/debug/binder/proc/<pid>

# Trace binder transactions with ftrace
echo 1 > /sys/kernel/debug/tracing/events/binder/enable
cat /sys/kernel/debug/tracing/trace_pipe
```

### Wakelock Debugging

```bash
# View all wakeup sources (kernel)
cat /sys/kernel/debug/wakeup_sources
# name          active_count  event_count  expire_count
# wakeup_count  active_since  total_time  max_time
# last_change  prevent_suspend_time

# Android-specific: dumpsys power
dumpsys power | grep -A 30 "Wake Locks:"

# Battery historian for visual wakelock analysis
# 1. Capture bugreport
adb bugreport bugreport.zip
# 2. Upload to https://bathist.ef.lc/
```

## 12. Vendor Hooks

Android GKI 2.0 introduced **vendor hooks** — tracepoint-like hooks that allow vendor modules to inject custom behavior into the GKI kernel without modifying its source:

```c
/* Vendor hook declaration (in GKI kernel) */
DECLARE_HOOK(android_vh_binder_transaction,
    TP_PROTO(struct binder_proc *proc, struct binder_transaction *t),
    TP_ARGS(proc, t));

/* Vendor module registers a hook */
#include <trace/hooks/binder.h>

static void my_binder_hook(void *data, struct binder_proc *proc,
                           struct binder_transaction *t)
{
    /* Custom vendor logic */
}

static int __init my_module_init(void)
{
    register_trace_android_vh_binder_transaction(
        my_binder_hook, NULL);
    return 0;
}
```

### Vendor Hook Categories

| Category | Example Hooks | Purpose |
|----------|---------------|--------|
| Binder | `android_vh_binder_transaction` | IPC monitoring |
| Scheduler | `android_vh_scheduler_tick` | Custom scheduling |
| Memory | `android_vh_page_cache_forced_ra` | Read-ahead tuning |
| Network | `android_vh_tcp_rcv_established` | TCP processing |
| Power | `android_vh_cpu_idle` | Idle state management |

## 13. Android Kernel Version Matrix

| Android Version | Kernel | GKI | Key Features |
|-----------------|--------|-----|-------------|
| Android 10 | 4.14, 4.19 | — | ION, ashmem |
| Android 11 | 5.4 | GKI 1.0 | Initial GKI |
| Android 12 | 5.10 | GKI 2.0 | Vendor hooks, DMA-BUF heaps |
| Android 13 | 5.15 | GKI 2.0 | MTE support, improved binder |
| Android 14 | 6.1 | GKI 2.0+ | Rust support, erofs default |
| Android 15 | 6.6 | GKI 2.0+ | 16K page support, improved MTE |

## Further Reading

- [Android Binder IPC Mechanism — docs.kernel.org](https://docs.kernel.org/driver-api/binder.html)
- [Binder Driver Source — kernel.org](https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/android/)
- [GKI Documentation — source.android.com](https://source.android.com/docs/core/architecture/kernel/generic-kernel-image)
- [Android Kernel Module Interface](https://source.android.com/docs/core/architecture/kernel/module-interface)
- [ashmem and memfd — LWN.net](https://lwn.net/Articles/833419/)
- [Wakelocks and Android Power Management — LWN.net](https://lwn.net/Articles/479941/)
- [Android Treble Architecture](https://source.android.com/docs/core/architecture)
- [Perfetto System Profiling](https://perfetto.dev/)
- [binder(4) man page](https://man7.org/linux/man-pages/man4/binder.4.html)
- [DMA-BUF Heaps Documentation](https://docs.kernel.org/driver-api/dma-buf.html)
- [SELinux for Android](https://source.android.com/docs/security/features/selinux)
