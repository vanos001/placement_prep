# Linux Kernel Architecture

## Introduction

The Linux kernel architecture is a carefully layered system that balances performance with maintainability. While the kernel is monolithic in the sense that all core components share a single address space, its internal design follows clear separation of concerns with well-defined interfaces between subsystems.

This chapter examines the kernel's architecture in detail: the relationships between subsystems, data flow paths, and the design decisions that make Linux both fast and flexible.

## High-Level Architecture Diagram

The following diagram shows the major components of the Linux kernel and their relationships:

```mermaid
graph TB
    subgraph "User Space"
        APP[Applications]
        GLIBC[glibc / musl]
        LIBC[System Call Interface]
    end

    subgraph "Kernel Space"
        subgraph "System Call Interface"
            SYSCALL[syscall dispatch]
        end

        subgraph "Core Subsystems"
            VFS[Virtual File System]
            MM[Memory Manager]
            SCHED[Process Scheduler]
            IPC[IPC Subsystem]
            NET[Network Stack]
            SECURITY[Security Framework]
        end

        subgraph "Support Subsystems"
            CRYPTO[Crypto API]
            IRQ[IRQ Management]
            SYNC[Synchronization]
            WORK[Workqueues]
        end

        subgraph "Hardware Abstraction"
            DEV[Device Model / Driver Framework]
            CHAR[Char Devices]
            BLOCK[Block Devices]
            NETDEV[Network Devices]
        end

        subgraph "Architecture Layer"
            ARCH[x86/ARM64/RISC-V/...]
        end
    end

    subgraph "Hardware"
        CPU[CPU / Memory]
        DISK[Storage]
        NIC[Network]
        OTHER[Other Devices]
    end

    APP --> GLIBC --> LIBC --> SYSCALL
    SYSCALL --> VFS
    SYSCALL --> MM
    SYSCALL --> SCHED
    SYSCALL --> IPC
    SYSCALL --> NET
    SYSCALL --> SECURITY

    VFS --> BLOCK
    VFS --> MM
    MM --> SCHED
    NET --> NETDEV
    DEV --> CHAR
    DEV --> BLOCK
    DEV --> NETDEV

    IRQ --> SCHED
    IRQ --> NET
    IRQ --> BLOCK
    WORK --> DEV

    BLOCK --> DISK
    NETDEV --> NIC
    CHAR --> OTHER
    ARCH --> CPU
```

## Subsystem Relationship Map

The kernel subsystems are deeply interconnected. Here is a detailed view of the dependencies:

```mermaid
graph LR
    subgraph "Data Flow Dependencies"
        VFS -->|page cache| MM
        MM -->|page faults| VFS
        MM -->|OOM killer| SCHED
        SCHED -->|context switch| ARCH
        NET -->|socket buffers| MM
        NET -->|NAPI poll| IRQ
        BLOCK -->|I/O scheduler| SCHED
        BLOCK -->|buffer heads| MM
        BLOCK -->|bio requests| DEV
        DEV -->|DMA mapping| MM
        SECURITY -->|access checks| VFS
        SECURITY -->|capability checks| SYSCALL
        IPC -->|shared memory| MM
    end
```

## The System Call Interface

The system call interface is the primary gateway between user space and kernel space. It's implemented in architecture-specific code but follows a common pattern:

### x86-64 System Call Path

```mermaid
sequenceDiagram
    participant App as User Application
    participant Libc as glibc
    participant Entry as syscall_entry (asm)
    participant Dispatch as sys_call_table
    participant Handler as sys_xxx()
    participant Return as syscall_return

    App->>Libc: write(fd, buf, count)
    Libc->>Entry: syscall instruction
    Entry->>Entry: Save registers
    Entry->>Entry: Switch to kernel stack
    Entry->>Dispatch: Lookup sys_call_table[nr]
    Dispatch->>Handler: Call sys_write()
    Handler->>Handler: Process request
    Handler-->>Entry: Return value in RAX
    Entry->>Return: Restore registers
    Return->>App: Return to user space
```

The entry point is defined in assembly:

```asm
/* arch/x86/entry/entry_64.S (simplified) */
entry_SYSCALL_64:
    swapgs
    mov    [gs:cpu_tss_rw.x86_tss.sp2], rsp  /* save user RSP */
    mov    rsp, [gs:cpu_tss_rw.x86_tss.sp0]  /* load kernel stack */
    /* save registers to pt_regs on stack */
    push   r11
    push   rcx
    push   rbp
    push   rbx
    /* ... */
    mov    rdi, rsp           /* pt_regs as first arg */
    call   do_syscall_64      /* C handler */
    /* restore and return */
    jmp    swapgs_restore_regs_and_return_to_usermode
```

The C-level dispatch:

```c
/* arch/x86/kernel/syscall_64.c */
__visible void do_syscall_64(struct pt_regs *regs)
{
    unsigned long nr = regs->orig_ax;

    if (nr < NR_syscalls) {
        regs->ax = sys_call_table[nr](
            regs->di, regs->si, regs->dx,
            regs->r10, regs->r8, regs->r9
        );
    }
}
```

## Process Scheduler Architecture

The scheduler is one of the most critical kernel subsystems. Linux implements a modular scheduling framework:

```mermaid
graph TB
    subgraph "Scheduler Framework"
        CORE[Scheduler Core]
        subgraph "Scheduling Classes"
            STOP[stop_sched_class]
            DL[dl_sched_class]
            RT[rt_sched_class]
            FAIR[fair_sched_class]
            IDLE[idle_sched_class]
        end
    end

    STOP -->|highest priority| DL
    DL -->|deadline scheduling| RT
    RT -->|real-time FIFO/RR| FAIR
    FAIR -->|CFS / EEVDF| IDLE
    IDLE -->|lowest priority| CORE

    subgraph "Per-CPU Run Queues"
        RQ0[Run Queue CPU 0]
        RQ1[Run Queue CPU 1]
        RQN[Run Queue CPU N]
    end

    CORE --> RQ0
    CORE --> RQ1
    CORE --> RQN
```

Each scheduling class has a defined interface:

```c
/* include/linux/sched.h */
struct sched_class {
    void (*enqueue_task)(struct rq *rq, struct task_struct *p, int flags);
    void (*dequeue_task)(struct rq *rq, struct task_struct *p, int flags);
    void (*yield_task)(struct rq *rq);
    void (*check_preempt_curr)(struct rq *rq, struct task_struct *p, int flags);
    struct task_struct *(*pick_next_task)(struct rq *rq);
    void (*put_prev_task)(struct rq *rq, struct task_struct *p);
    void (*set_curr_task)(struct rq *rq);
    void (*task_tick)(struct rq *rq, struct task_struct *p, int queued);
    void (*switched_to)(struct rq *rq, struct task_struct *p);
    void (*prio_changed)(struct rq *rq, struct task_struct *p, int oldprio);
    /* ... */
};
```

### CFS / EEVDF Scheduling

The Completely Fair Scheduler (CFS) uses a red-black tree keyed by **virtual runtime** (vruntime). The task with the smallest vruntime is always picked next, ensuring fair CPU time distribution.

Starting with kernel 6.6, the **EEVDF** (Earliest Eligible Virtual Deadline First) scheduler replaces CFS. EEVDF assigns each task a virtual deadline based on its request and lag, and picks the eligible task with the earliest deadline:

```c
/* kernel/sched/fair.c — EEVDF pick logic (simplified) */
static struct sched_entity *pick_eevdf(struct cfs_rq *cfs_rq)
{
    struct sched_entity *best = NULL;
    struct rb_node *node = cfs_rq->tasks_timeline.rb_leftmost;

    /* Walk the tree to find the earliest eligible virtual deadline */
    for_each_eligible_entity(se, cfs_rq) {
        if (!best || entity_before(se, best))
            best = se;
    }
    return best;
}
```

## Memory Management Architecture

The memory management subsystem is layered from low-level page allocation to high-level virtual memory abstractions:

```mermaid
graph TB
    subgraph "User Space"
        MMAP[mmap/munmap]
        BRK[brk/sbrk]
        MALLOC[malloc/free]
    end

    subgraph "Kernel Memory Management"
        subgraph "Virtual Memory"
            VMA[Virtual Memory Areas]
            PAGETABLE[Page Tables]
            FAULT[Page Fault Handler]
        end

        subgraph "Page Allocator"
            BUDDY[Buddy Allocator]
            ZONES[Memory Zones]
            PCPU[Per-CPU Page Cache]
        end

        subgraph "Object Allocator"
            SLUB[SLUB Allocator]
            KMEM[Kmem Caches]
        end

        subgraph "Page Cache"
            PGCACHE[Page Cache]
            WRITEBACK[Writeback]
        end

        subgraph "Reclaim"
            KSWAPD[kswapd]
            LRU[LRU Lists]
            OOM[OOM Killer]
        end
    end

    subgraph "Hardware"
        MMU[MMU / TLB]
        RAM[Physical RAM]
    end

    MMAP --> VMA
    BRK --> VMA
    MALLOC --> MMAP
    MALLOC --> BRK

    VMA --> PAGETABLE
    FAULT --> VMA
    FAULT --> PAGETABLE
    FAULT --> PGCACHE
    FAULT --> BUDDY

    BUDDY --> ZONES
    ZONES --> PCPU
    SLUB --> BUDDY
    KMEM --> SLUB

    PGCACHE --> WRITEBACK
    KSWAPD --> LRU
    LRU --> BUDDY
    OOM --> SCHED

    PAGETABLE --> MMU
    BUDDY --> RAM
```

### Key Memory Data Structures

```c
/* Each process has a mm_struct describing its address space */
struct mm_struct {
    struct maple_tree mm_mt;        /* VMAs stored in maple tree */
    struct rw_semaphore mmap_lock;
    unsigned long task_size;        /* size of user address space */
    pgd_t *pgd;                     /* page global directory */
    atomic_t mm_users;              /* number of processes sharing this mm */
    atomic_t mm_count;              /* reference count */
    int map_count;                  /* number of VMAs */
    unsigned long total_vm;         /* total pages mapped */
    unsigned long locked_vm;        /* pages locked in memory */
    unsigned long data_vm;          /* VM_WRITE & ~VM_SHARED */
    unsigned long stack_vm;         /* VM_GROWSUP/DOWN */
    unsigned long start_code, end_code;
    unsigned long start_data, end_data;
    unsigned long start_brk, brk;
    unsigned long start_stack;
    /* ... */
};

/* Virtual Memory Area — describes a contiguous region of virtual memory */
struct vm_area_struct {
    unsigned long vm_start;         /* start address */
    unsigned long vm_end;           /* end address */
    pgprot_t vm_page_prot;          /* access permissions */
    unsigned long vm_flags;         /* VM_READ|VM_WRITE|VM_EXEC|... */
    struct rb_node vm_rb;           /* node in mm's maple tree/rbtree */
    struct file *vm_file;           /* file mapped (NULL for anonymous) */
    void *vm_private_data;          /* driver-specific data */
    const struct vm_operations_struct *vm_ops;
    /* ... */
};
```

## Virtual File System (VFS) Architecture

VFS provides a uniform interface for all filesystems:

```mermaid
graph TB
    subgraph "System Call Layer"
        SYS_OPEN[open]
        SYS_READ[read]
        SYS_WRITE[write]
        SYS_CLOSE[close]
    end

    subgraph "VFS Layer"
        INODE[inode -- file metadata]
        DENTRY[dentry -- directory entry cache]
        FILE[struct file -- open file instance]
        SB[super_block -- filesystem instance]
    end

    subgraph "Filesystem Implementations"
        EXT4[ext4]
        XFS[XFS]
        BTRFS[Btrfs]
        TMPFS[tmpfs]
        PROCFS[procfs]
    end

    subgraph "Block Layer"
        BIO[bio -- block I/O request]
        BDI[backing_dev_info]
        IOSCHED[I/O Scheduler]
    end

    SYS_OPEN --> DENTRY
    SYS_READ --> FILE
    SYS_WRITE --> FILE
    FILE --> INODE
    INODE --> DENTRY
    DENTRY --> SB
    SB --> EXT4
    SB --> XFS
    SB --> BTRFS
    SB --> TMPFS
    EXT4 --> BIO
    XFS --> BIO
    BIO --> IOSCHED
    IOSCHED --> BDI
```

### Key VFS Objects

```c
/* struct inode — represents a filesystem object (file, directory, etc.) */
struct inode {
    umode_t                 i_mode;     /* file type and permissions */
    unsigned short          i_opflags;
    kuid_t                  i_uid;      /* owner UID */
    kgid_t                  i_gid;      /* owner GID */
    unsigned int            i_flags;
    const struct inode_operations   *i_op;
    struct super_block      *i_sb;
    struct address_space    *i_mapping; /* page cache mapping */
    unsigned long           i_ino;      /* inode number */
    loff_t                  i_size;     /* file size in bytes */
    struct timespec64       __i_atime;
    struct timespec64       __i_mtime;
    struct timespec64       __i_ctime;
    const struct file_operations    *i_fop;
    /* ... */
};

/* struct file — represents an open file */
struct file {
    struct path             f_path;     /* contains vfsmount and dentry */
    struct inode            *f_inode;
    const struct file_operations    *f_op;
    atomic_long_t           f_count;
    unsigned int            f_flags;    /* O_RDONLY, O_NONBLOCK, etc. */
    fmode_t                 f_mode;
    loff_t                  f_pos;      /* current file position */
    struct address_space    *f_mapping;
    void                    *private_data;
    /* ... */
};
```

## Network Subsystem Architecture

The networking stack follows a layered design similar to the OSI model:

```mermaid
graph TB
    subgraph "User Space"
        SOCK_APP[Socket Application]
    end

    subgraph "Socket Layer"
        SOCKET[struct socket]
        SOCK[struct sock]
        SK_BUFF[sk_buff management]
    end

    subgraph "Transport Layer"
        TCP[TCP]
        UDP[UDP]
        RAW[Raw Sockets]
    end

    subgraph "Network Layer"
        IP[IPv4 / IPv6]
        ROUTE[Routing]
        NETFILTER[Netfilter / iptables]
    end

    subgraph "Link Layer"
        DEV_CORE[Network Device Core]
        QDISC[Queueing Disciplines]
        BRIDGE[Bridging]
    end

    subgraph "Driver Layer"
        NAPI[NAPI Polling]
        NETDEV2[net_device ops]
    end

    SOCK_APP --> SOCKET
    SOCKET --> SOCK
    SOCK --> TCP
    SOCK --> UDP
    SOCK --> RAW
    TCP --> IP
    UDP --> IP
    IP --> ROUTE
    IP --> NETFILTER
    NETFILTER --> DEV_CORE
    DEV_CORE --> QDISC
    QDISC --> NAPI
    NAPI --> NETDEV2
```

### sk_buff — The Socket Buffer

The `sk_buff` is the fundamental data unit in the networking stack:

```c
/* include/linux/skbuff.h (simplified) */
struct sk_buff {
    struct sk_buff      *next, *prev;
    struct sock         *sk;           /* owning socket */
    unsigned int        len;           /* data length */
    unsigned int        data_len;      /* non-linear data length */
    __u16               mac_len;       /* MAC header length */
    __u16               hdr_len;       /* skb headroom used */
    __u16               queue_mapping;
    __u8                cloned:1;
    __u8                ip_summed:2;

    /* Transport layer header */
    __u16               transport_header;
    /* Network layer header */
    __u16               network_header;
    /* Link layer header */
    __u16               mac_header;

    /* Data pointers */
    unsigned char       *head;         /* buffer head */
    unsigned char       *data;         /* data start */
    unsigned char       *tail;         /* data end */
    unsigned char       *end;          /* buffer end */

    /* Timestamp, dev, protocol, etc. */
    ktime_t             tstamp;
    struct net_device   *dev;
    __be16              protocol;
    /* ... */
};
```

## Device Model Architecture

The Linux device model provides a unified view of all devices through **sysfs**:

```mermaid
graph TB
    subgraph "Device Model Core"
        KOBJ[kobject -- reference-counted object]
        KSET[kset -- collection of kobjects]
        KTYPE[ktype -- object type operations]
    end

    subgraph "Bus / Device / Driver Model"
        BUS[struct bus_type]
        DEVICE[struct device]
        DRIVER[struct device_driver]
    end

    subgraph "Bus Types"
        PCI[PCI bus]
        USB[USB bus]
        PLATFORM[Platform bus]
        I2C[I2C bus]
        SPI[SPI bus]
    end

    subgraph "sysfs Representation"
        SYSFS_BUS["/sys/bus/"]
        SYSFS_DEV["/sys/devices/"]
        SYSFS_CLASS["/sys/class/"]
    end

    KOBJ --> KSET
    KOBJ --> KTYPE
    BUS --> DEVICE
    BUS --> DRIVER
    DEVICE --> KOBJ
    DRIVER --> KOBJ
    PCI --> BUS
    USB --> BUS
    PLATFORM --> BUS
    BUS --> SYSFS_BUS
    DEVICE --> SYSFS_DEV
    DEVICE --> SYSFS_CLASS
```

### Device-Driver Binding

```c
/* drivers/base/bus.c — simplified binding logic */
static int driver_match_device(struct device_driver *drv,
                               struct device *dev)
{
    return drv->bus->match ? drv->bus->match(dev, drv) : 1;
}

/* drivers/pci/pci-driver.c — PCI match function */
static const struct pci_device_id *pci_match_device(
    const struct pci_device_id *ids, struct pci_dev *dev)
{
    /* Match vendor, device, subvendor, subdevice, class */
    while (ids->vendor || ids->subvendor || ids->class_mask) {
        if (pci_match_one_device(ids, dev))
            return ids;
        ids++;
    }
    return NULL;
}
```

## Interrupt Handling Architecture

Linux uses a two-phase interrupt handling model to minimize the time spent with interrupts disabled:

```mermaid
graph TB
    subgraph "Hardware Interrupt"
        HW_IRQ[Hardware IRQ Line]
    end

    subgraph "Top Half (Hard IRQ)"
        DESC[irq_desc]
        HANDLER[irq handler -- quick acknowledgment]
        ACK[Disable/acknowledge IRQ]
    end

    subgraph "Bottom Half Mechanisms"
        SOFTIRQ[softirq -- ksoftirqd]
        TASKLET[tasklet -- deprecated in 6.x]
        WORKQ[workqueue -- most common]
        THREADED[Threaded IRQs]
    end

    subgraph "Action"
        ACTION1[irqaction 1]
        ACTION2[irqaction 2]
        ACTIONN[irqaction N]
    end

    HW_IRQ --> DESC
    DESC --> HANDLER
    HANDLER --> ACK
    HANDLER --> SOFTIRQ
    HANDLER --> TASKLET
    HANDLER --> WORKQ
    HANDLER --> THREADED
    DESC --> ACTION1
    DESC --> ACTION2
    DESC --> ACTIONN
```

```bash
# View interrupt information
$ cat /proc/interrupts | head -5
           CPU0       CPU1       CPU2       CPU3
  1:          9          0          0          0   IO-APIC   1-edge      i8042
  8:          1          0          0          0   IO-APIC   8-edge      rtc0
  9:          0          0          23         0   IO-APIC   9-fasteoi   acpi
 16:         56        234          0          0   IO-APIC  16-fasteoi   ehci_hcd
 23:          0          0       1234          0   IO-APIC  23-fasteoi   nvidia

# View per-CPU softirq statistics
$ cat /proc/softirqs
                    CPU0       CPU1       CPU2       CPU3
          HI:          0          0          0          0
       TIMER:    1234567    1234566    1234567    1234566
      NET_TX:       1234       1234       1233       1234
      NET_RX:      56789      56788      56789      56788
       BLOCK:      12345      12344      12345      12344
    IRQ_POLL:          0          0          0          0
     TASKLET:       1234       1234       1233       1234
       SCHED:     234567     234566     234567     234566
     HRTIMER:          0          0          0          0
         RCU:     345678     345677     345678     345677
```

## Synchronization Primitives

The kernel provides various synchronization mechanisms for different use cases:

| Primitive | Use Case | Context |
|-----------|----------|---------|
| Spinlock | Short critical sections, IRQ-safe | Atomic (no sleep) |
| Mutex | Longer critical sections, can sleep | Process context |
| RCU | Read-mostly data, zero read overhead | Any context |
| Semaphore | Counting synchronization | Process context |
| rwlock | Many readers, few writers | Atomic |
| atomic_t | Simple counters | Any context |
| seqlock | Reader-writer, readers never block | Any context |
| Completion | Wait for event | Process context |

```c
/* Example: spinlock usage */
DEFINE_SPINLOCK(my_lock);
unsigned long flags;

spin_lock_irqsave(&my_lock, flags);  /* disable interrupts */
/* critical section — must not sleep */
spin_unlock_irqrestore(&my_lock, flags);

/* Example: mutex usage */
DEFINE_MUTEX(my_mutex);

mutex_lock(&my_mutex);
/* critical section — can sleep */
mutex_unlock(&my_mutex);

/* Example: RCU usage */
rcu_read_lock();
/* read-side critical section — no blocking */
list_for_each_entry_rcu(ptr, &my_list, list) {
    /* read data */
}
rcu_read_unlock();
```

## Kernel Configuration Architecture

The configuration system uses a hierarchy of `Kconfig` files:

```mermaid
graph TB
    KCONFIG_ROOT[Kconfig -- root]
    INIT_K[init/Kconfig]
    MM_K[mm/Kconfig]
    NET_K[net/Kconfig]
    FS_K[fs/Kconfig]
    DRV_K[drivers/Kconfig]
    ARCH_K[arch/x86/Kconfig]

    KCONFIG_ROOT --> INIT_K
    KCONFIG_ROOT --> MM_K
    KCONFIG_ROOT --> NET_K
    KCONFIG_ROOT --> FS_K
    KCONFIG_ROOT --> DRV_K
    KCONFIG_ROOT --> ARCH_K

    DRV_K --> DRV_NET_K[drivers/net/Kconfig]
    DRV_K --> DRV_USB_K[drivers/usb/Kconfig]
    DRV_NET_K --> DRV_IGB_K[drivers/net/ethernet/intel/Kconfig]
```

See [Build System](build-system.md) and [Configuration](configuration.md) for full details.

## Cross-Subsystem Data Flow Examples

### File Read Path

A `read()` system call traverses multiple subsystems:

```mermaid
sequenceDiagram
    participant App as Application
    participant VFS as VFS
    participant FS as Filesystem (ext4)
    participant PC as Page Cache
    participant MM as Memory Manager
    participant Block as Block Layer
    participant Dev as Device Driver

    App->>VFS: read(fd, buf, count)
    VFS->>VFS: fdget() → struct file
    VFS->>FS: file->f_op->read()
    FS->>PC: find_lock_page() in page cache
    alt Page in cache
        PC-->>FS: page found
    else Page not in cache
        PC->>MM: alloc_page()
        MM->>Block: submit_bio()
        Block->>Dev: queue request
        Dev-->>Block: I/O complete (IRQ)
        Block-->>PC: page populated
    end
    FS-->>VFS: data available
    VFS->>VFS: copy_to_user(buf, page_data)
    VFS-->>App: bytes read
```

### Network Packet Receive Path

```mermaid
sequenceDiagram
    participant NIC as Network Card
    participant IRQ as IRQ Handler
    participant NAPI as NAPI SoftIRQ
    participant IP as IP Layer
    participant TCP as TCP Layer
    participant Socket as Socket Buffer
    participant App as Application

    NIC->>IRQ: Hardware interrupt
    IRQ->>IRQ: Acknowledge IRQ
    IRQ->>NAPI: napi_schedule()
    NAPI->>NAPI: napi_poll() -- receive packets
    NAPI->>IP: netif_receive_skb()
    IP->>IP: Route lookup
    IP->>IP: Netfilter hooks
    IP->>TCP: tcp_v4_rcv()
    TCP->>TCP: Sequence/ordering
    TCP->>Socket: sk_data_ready()
    Socket->>App: recv() returns data
```

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Linux kernel documentation — Architecture](https://www.kernel.org/doc/html/latest/process/programming-language.html)
- [LWN: Porting the Linux kernel to a new architecture](https://lwn.net/Articles/597354/)
- [Linux Device Drivers, 3rd Edition](https://lwn.net/Kernel/LDD3/)
- [Understanding the Linux Virtual Memory Manager](https://www.kernel.org/doc/gorman/)
- [Linux Networking Architecture](https://www.kernel.org/doc/html/latest/networking/)
- [The Art of Linux Kernel Design](https://www.amazon.com/Art-Linux-Kernel-Design-Illustrating/dp/1466518030)

## Related Topics

- [Kernel Overview](overview.md) — High-level introduction
- [Build System](build-system.md) — Kconfig and Kbuild
- [Configuration](configuration.md) — Customizing the kernel
- [Kernel Modules](modules.md) — Loadable module architecture
- [Boot Process](boot-process.md) — From power-on to userspace
- [Data Structures](data-structures.md) — Core kernel data structures
