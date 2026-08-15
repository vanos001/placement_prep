# I/O Internals

This section covers the Linux I/O path in depth: direct I/O vs. buffered I/O, DAX for persistent memory, [mmap internals](../memory/mmap.md), [copy-on-write mechanics](../virtual-memory/cow.md), fork scalability with thousands of file descriptors, and the modern `clone3` system call.

## Direct I/O

Direct I/O (`O_DIRECT`) bypasses the page cache entirely — data is transferred between the application buffer and the storage device without being copied through the kernel's page cache. This is essential for databases (PostgreSQL, MySQL InnoDB, RocksDB) that manage their own buffer cache and would suffer double-caching if the kernel also cached the same data.

```c
int fd = open("/dev/sdb1", O_RDWR | O_DIRECT);
// Application buffer must be:
//   1. Aligned to the logical block size (typically 512 or 4096 bytes)
//   2. Size must be a multiple of the block size
//   3. Memory must be page-aligned (use posix_memalign or O_DIRECT-aware allocator)

void *buf;
posix_memalign(&buf, 4096, 4096);  // page-aligned, page-sized
pread(fd, buf, 4096, 0);  // reads directly from disk, bypassing page cache
```

### Direct I/O Requirements and Pitfalls

The alignment requirements come from the hardware: DMA engines transfer data in block-sized units, and the device's DMA mapping requires buffer addresses to be block-aligned. A misaligned `O_DIRECT` read/write returns `EINVAL`.

Direct I/O does NOT bypass the kernel's block I/O scheduler. The request still goes through `blk_mq` and the I/O scheduler (mq-deadline, bfq, none). However, there's no page cache lookup, no dirty page writeback, and no copy between kernel and user buffers. The data goes: application buffer → kernel bio → block layer → device driver → hardware DMA.

### Direct I/O and Concurrent Reads/Writes

Direct I/O has a concurrency problem: multiple concurrent `O_DIRECT` reads/writes to the same file region have no serialization through the page cache. The kernel provides a **DIO locking mechanism** (`inode->i_dio_count` and `inode_dio_wait()`) that serializes direct I/O with page cache operations (truncate, hole punch). But concurrent direct I/O requests to the same region are not serialized — the application must handle this (or use `O_DSYNC`/`fsync` for ordering).

## Buffered I/O

Buffered I/O is the default Linux I/O path. All data flows through the page cache:

```
Application: write(fd, buf, 4096)
    │
    ▼
VFS layer: check permissions, call filesystem's write_iter
    │
    ▼
Filesystem: ext4_write_iter()
    │
    ▼
Generic file I/O: generic_file_buffered_write()
    │  1. Find/create page cache page for this offset
    │  2. Copy data from userspace to page cache page
    │  3. Mark page dirty
    │  4. Return to userspace (ASYNC — write not on disk yet!)
    ▼
Writeback (later):
    │  pdflush/flush worker writes dirty pages to disk
    │  OR: fsync() forces synchronous writeback
    ▼
Block layer: bio → blk_mq → device driver
```

### Read-Ahead

The kernel's read-ahead mechanism (`mm/readahead.c`) speculatively reads pages ahead of the current access position. When sequential access is detected (accessing the next page in order), the kernel issues larger read-ahead I/Os (up to 256 KB on the first detection, growing to several MB). This converts many small random reads into fewer large sequential reads, dramatically improving throughput for sequential workloads.

The read-ahead state machine tracks per-file `ra` (read-ahead) metadata: the current read-ahead window, the async size, and the mmap_miss count (for mmap'd files). Random access patterns (frequent `lseek` or mmap misses) disable read-ahead to avoid wasting memory and I/O bandwidth.

## DAX — Direct Access

DAX (Direct Access, Linux 4.0+) enables file I/O that maps persistent memory (Intel Optane DC Persistent Memory, CXL-attached memory) directly into the process address space, bypassing both the page cache and the block layer. With DAX, `read()` and `write()` are implemented as `memcpy` from/to the persistent memory region.

```bash
# Mount a PMEM namespace with DAX
mount -o dax /dev/pmem0 /mnt/pmem

# Applications using this mount point:
# - mmap: directly maps PMEM into address space (no page cache)
# - read/write: memcpy to/from PMEM (no block I/O, no DMA)
# - No page cache duplication (PMEM IS the cache)
```

DAX requires the filesystem to support it (ext4, XFS with `-o dax`). The filesystem stores metadata in DRAM (via the normal page cache for metadata) but data pages map directly to persistent memory physical addresses. The page table entries for DAX mappings have the `MAP_SYNC` flag, which ensures `msync()` flushes CPU caches to PMEM (via `clwb` instructions on x86).

The limitation: DAX requires alignment to the device's sector size, doesn't support `O_DIRECT` (it's already direct), and filesystem operations that modify block allocation (fallocate, ftruncate) can be slower because they must update the filesystem's block maps in PMEM with proper cache flushing for crash consistency.

## mmap Internals

The [mmap basics](../memory/mmap.md) cover the API. Here we examine the kernel implementation:

### The mmap System Call Path

```
mmap(addr, length, prot, flags, fd, offset)
    │
    ▼
ksys_mmap_pgoff() → vm_mmap_pgoff()
    │
    ▼
do_mmap()
    │  1. Validate arguments (alignment, length, flags)
    │  2. Find unmapped VMA region in the process's mm
    │  3. Create a new vm_area_struct (VMA)
    │  4. Link VMA into the mm's VMA list and rb-tree
    │  5. For file-backed: call filesystem's mmap (ext4_file_mmap)
    │     → creates mapping between file pages and virtual addresses
    │  6. For MAP_ANONYMOUS: just creates an empty VMA
    │  7. Return the mapped address
    ▼
No pages are actually allocated yet! (demand paging)
```

### VMA (Virtual Memory Area)

Every `mmap` creates a `vm_area_struct` that describes a contiguous region of the virtual address space with the same properties:

```c
struct vm_area_struct {
    unsigned long vm_start, vm_end;   // address range [start, end)
    struct file *vm_file;             // backing file (NULL for anonymous)
    pgoff_t vm_pgoff;                 // offset in the file (in pages)
    vm_flags_t vm_flags;              // VM_READ, VM_WRITE, VM_EXEC, VM_MAYSHARE
    const struct vm_operations_struct *vm_ops;  // page fault, open, close handlers
    struct mm_struct *vm_mm;          // owning process's mm
    struct list_head vm_list;         // linked list of all VMAs
    struct rb_node vm_rb;             // red-black tree for fast lookup
    // ... many more fields
};
```

VMAs are stored in both a linked list (for iteration) and a red-black tree (for O(log n) lookup by address). A process with thousands of `mmap` regions (common for Java with many JAR files) can have performance issues due to VMA lookup cost — the kernel uses an interval tree for `find_vma()` but it's still O(log n) per page fault.

### Page Fault Handling (File-Backed)

When the process first accesses a mapped page, a page fault occurs:

1. Page fault handler (`do_page_fault`) finds the VMA containing the faulting address
2. For file-backed: calls `filemap_fault()` which looks up the page in the page cache
3. Cache hit: maps the page table entry to the cached page, returns to userspace
4. Cache miss: allocates a new page, submits block I/O, sleeps until I/O completes, then maps

### Page Fault Handling (Anonymous)

For `MAP_ANONYMOUS` or CoW pages: calls `do_anonymous_page()` which allocates a zeroed page from the buddy allocator (or from the per-CPU pagevec cache) and maps it. The zeroed page comes from the kernel's **zero page** on first access (a pre-zeroed page shared read-only, CoW'd on write).

## Copy-on-Write — Fork Internals

The [CoW basics](../virtual-memory/cow.md) cover the concept. The critical detail for system design is how `fork()` scales with memory size.

### Traditional fork() Scalability Problem

`fork()` creates a child process by copying the parent's entire page table (not the pages — just the page table entries). All PTEs are marked read-only. On the first write to any page by either process, a page fault triggers CoW: the page is copied, and the faulting process gets a new writable PTE.

For a process with 100 GB of mapped memory, fork copies the **entire page table hierarchy** — that's ~100 MB of page table structures (4-level tables: 1 PGD + 512 P4Ds + 262K PUDs + 128M PMDs + some PTEs, but in practice much less due to sparse mappings). The copy itself takes O(number of PTEs) time, and the TLB flush after fork invalidates all entries, causing a storm of TLB misses in both parent and child.

```bash
# Demonstrate fork() cost with large memory
# Parent maps 10 GB anonymous memory
./fork_test 10G
# Time to fork(): ~50 ms (page table copy + TLB flush)
# Time to fork() with 1 GB: ~5 ms
```

### vfork() and posix_spawn()

`vfork()` creates a child that shares the parent's address space and page tables entirely — no copy at all. The child must immediately call `execve()` (or `_exit()`). `posix_spawn()` combines fork+exec in a single kernel operation, optimizing the common case. These avoid the page table copy entirely.

### CoW during execve()

After `fork()`, the child typically calls `execve()`, which replaces the address space. The kernel is smart: if the child is the only reference to the parent's pages (after the parent has exited or called `execve`), CoW is unnecessary. The kernel detects this with reference counting and can skip the CoW overhead, directly reclaiming the pages.

## clone3 — The Modern Process Creation API

`clone3()` (Linux 5.3) replaces the old `clone()` and `fork()` with a extensible, flag-based API using a `clone_args` struct:

```c
struct clone_args {
    __aligned_u64 flags;          // CLONE_VM, CLONE_FS, CLONE_FILES, etc.
    __aligned_u64 pidfd;          // return a pidfd for the child (new!)
    __aligned_u64 child_tid;      // CLONE_CHILD_SETTID
    __aligned_u64 parent_tid;     // CLONE_PARENT_SETTID
    __aligned_u64 exit_signal;    // signal to send on child exit
    __aligned_u64 stack;          // child stack pointer
    __aligned_u64 stack_size;     // child stack size
    __aligned_u64 tls;            // TLS descriptor (CLONE_SETTLS)
    __aligned_u64 set_tid;        // PID to assign (CLONE_SET_TID)
    __aligned_u64 set_tid_size;   // number of PIDs in set_tid array
    __aligned_u64 cgroup;         // cgroup to place child in (CLONE_INTO_CGROUP, v5.7)
};

int clone3(struct clone_args *cl_args, size_t size);
```

Key advantages over `fork()`:

1. **`CLONE_INTO_CGROUP`**: Places the child directly into a specific cgroup at creation time, avoiding the race where the child briefly runs in the parent's cgroup before `setns`/`cgroup` migration. Critical for container runtimes (runc, containerd).

2. **`pidfd`**: Returns a file descriptor referring to the child process, enabling race-free process management. Unlike PID (which can be recycled), a pidfd is unique and can be used with `pidfd_send_signal()`, `pidfd_open()`, and `epoll` (for SIGCHLD). This eliminates the classic PID-recycling race in process supervisors.

3. **Extensibility**: New flags can be added to `clone_args` without changing the syscall ABI (the `size` parameter indicates which fields are valid).

## Comparison

| Mechanism | Page Cache | Kernel Copy | Block Layer | Use Case |
|-----------|-----------|-------------|-------------|----------|
| Buffered I/O | Yes | Yes (2 copies) | Yes | General purpose, sequential |
| Direct I/O | No | No (1 copy, DMA) | Yes (minimal) | Databases, self-cached apps |
| DAX | No | No (memcpy to PMEM) | No | Persistent memory workloads |
| mmap | Yes (file) | No (page table) | On demand | Memory-mapped files, shared memory |
| io_uring | Configurable | Configurable | Yes | High IOPS, async |

## Interview Questions

1. **"Why does O_DIRECT require aligned buffers?"** Answer hint: The storage device's DMA engine transfers data in block-sized units. If the buffer isn't block-aligned, a single block read/write might span two non-contiguous physical pages, requiring the kernel to allocate a temporary aligned buffer and copy — defeating the purpose of O_DIRECT. The alignment requirement ensures DMA can transfer directly from the device to the application buffer.

2. **"How does fork() scale with a process that has 100 GB of memory?"** Answer hint: `fork()` copies all page table entries (~25 MB per 100 GB with 4 KB pages), marks them read-only for CoW, and flushes the TLB. The page table copy takes O(n) time proportional to the number of mapped pages. The TLB flush causes a storm of misses in both parent and child. For process creation without memory sharing, use `posix_spawn()` or `clone3()` with `CLONE_VM` cleared. For container workloads, consider `clone3()` with `CLONE_INTO_CGROUP`.

3. **"What is DAX and when would you use it?"** Answer hint: DAX maps persistent memory (PMEM) directly into the process address space, bypassing both the page cache and the block layer. Reads and writes become memory operations (load/store), not I/O operations. Use it when: you have PMEM hardware (Intel Optane, CXL memory), your workload benefits from byte-addressable persistent storage (key-value stores, in-memory databases with persistence), and you can handle the DAX limitations (no O_DIRECT, specific alignment requirements, crash consistency responsibility for data ordering).

4. **"What problem does clone3's pidfd solve?"** Answer hint: PID recycling: a process exits, its PID is reused by a new process, and a supervisor that was tracking the old PID by number accidentally sends a signal to the new process. pidfd is a file descriptor that uniquely refers to a specific process — it can't be recycled. Combined with `pidfd_send_signal()` and `epoll` (SIGCHLD notification), pidfd enables race-free process supervision without the PID race.

## References
- Corbet, J. "Supporting O_DIRECT." LWN.net, 2004.
- Corbet, J. "DAX: direct access to persistent memory." LWN.net, 2015.
- Linux source: `mm/memory.c`, `mm/mmap.c`, `mm/filemap.c`, `fs/read_write.c`.
- Brauner, C. "clone3: a new process creation syscall." LWN.net, 2019.
