# File Operations

## Introduction

File operations are the interface between user-space I/O system calls and the kernel's filesystem implementations. When a user process calls `read()`, `write()`, `open()`, `close()`, or performs memory-mapped I/O, the VFS layer dispatches these calls through a `file_operations` structure that each filesystem or device driver provides.

The `file_operations` structure is arguably the most frequently invoked interface in the entire Linux kernel. It handles everything from simple `cat` commands to complex asynchronous I/O, zero-copy transfers, and file locking.

## The `file_operations` Structure

### Definition

```c
/* Simplified from include/linux/fs.h */
struct file_operations {
    struct module *owner;
    loff_t (*llseek)(struct file *, loff_t, int);
    ssize_t (*read)(struct file *, char __user *, size_t, loff_t *);
    ssize_t (*write)(struct file *, const char __user *, size_t, loff_t *);
    ssize_t (*read_iter)(struct kiocb *, struct iov_iter *);
    ssize_t (*write_iter)(struct kiocb *, struct iov_iter *);
    int (*iopoll)(struct kiocb *kiocb, bool spin);
    int (*iterate_shared)(struct file *, struct dir_context *);
    __poll_t (*poll)(struct file *, struct poll_table_struct *);
    long (*unlocked_ioctl)(struct file *, unsigned int, unsigned long);
    long (*compat_ioctl)(struct file *, unsigned int, unsigned long);
    int (*mmap)(struct file *, struct vm_area_struct *);
    unsigned long mmap_supported_flags;
    int (*open)(struct inode *, struct file *);
    int (*flush)(struct file *, fl_owner_t id);
    int (*release)(struct inode *, struct file *);
    int (*fsync)(struct file *, loff_t, loff_t, int datasync);
    int (*fasync)(int, struct file *, int);
    int (*lock)(struct file *, int, struct file_lock *);
    ssize_t (*splice_read)(struct file *, loff_t *, struct pipe_inode_info *,
                           size_t, unsigned int);
    ssize_t (*splice_write)(struct pipe_inode_info *, struct file *,
                            loff_t *, size_t, unsigned int);
    int (*setlease)(struct file *, int, struct file_lock **, void **);
    long (*fallocate)(struct file *file, int mode, loff_t offset, loff_t len);
    void (*show_fdinfo)(struct seq_file *m, struct file *f);
    ssize_t (*copy_file_range)(struct file *, loff_t, struct file *,
                               loff_t, size_t, unsigned int);
    loff_t (*remap_file_range)(struct file *file_in, loff_t pos_in,
                               struct file *file_out, loff_t pos_out,
                               loff_t len, unsigned int remap_flags);
    int (*fadvise)(struct file *, loff_t, loff_t, int);
};
```

### Operation Categories

```mermaid
graph TD
    subgraph "Read/Write Path"
        READ[read -- traditional buffered read]
        WRITE[write -- traditional buffered write]
        READ_ITER[read_iter -- vectored/iter read]
        WRITE_ITER[write_iter -- vectored/iter write]
        SPLICE_READ[splice_read -- zero-copy read to pipe]
        SPLICE_WRITE[splice_write -- zero-copy write from pipe]
        COPY_FILE_RANGE[copy_file_range -- server-side copy]
    end
    subgraph "File Lifecycle"
        OPEN[open -- file opened]
        RELEASE[release -- last close]
        FLUSH[flush -- each close]
    end
    subgraph "Position"
        LLSEEK[llseek -- change file position]
    end
    subgraph "Synchronization"
        FSYNC[fsync -- flush data+metadata]
        FDATASYNS[fdatasync -- flush data only]
    end
    subgraph "Locking"
        LOCK[lock -- POSIX/FL locks]
        SETLEASE[setlease -- delegation leases]
    end
    subgraph "Memory Mapping"
        MMAP[mmap -- map file to virtual memory]
    end
    subgraph "Async I/O"
        READ_ITER["read_iter (with IOCB_NOWAIT)"]
        IOPOLL[iopoll -- completion polling]
    end
```

## The Read Path

### Traditional `read()` Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant VFS as VFS Layer
    participant PageCache as Page Cache
    participant FS as Filesystem
    participant Disk as Block Device

    App->>VFS: read(fd, buf, count)
    VFS->>VFS: fdget() → struct file
    VFS->>VFS: Verify permissions
    VFS->>VFS: rw_verify_area(READ, pos, count)
    VFS->>FS: file->f_op->read(file, buf, count, andpos)
    FS->>PageCache: find/get pages in cache
    alt Cache hit
        PageCache-->>FS: Page data available
        FS->>VFS: copy_to_user(buf, page_data, count)
    else Cache miss
        PageCache->>Disk: Submit read I/O
        Disk-->>PageCache: I/O complete, page filled
        PageCache-->>FS: Page data available
        FS->>VFS: copy_to_user(buf, page_data, count)
    end
    VFS-->>App: Return bytes read
```

### Modern `read_iter()` Flow

Modern filesystems implement `read_iter()` using the `iov_iter` interface, which supports scatter-gather I/O:

```c
/* Generic implementation: generic_file_read_iter() */
ssize_t generic_file_read_iter(struct kiocb *iocb, struct iov_iter *iter) {
    struct file *file = iocb->ki_filp;
    ssize_t retval = 0;

    if (iocb->ki_flags & IOCB_DIRECT) {
        /* Direct I/O: bypass page cache */
        retval = mapping->a_ops->direct_IO(iocb, iter);
    } else {
        /* Buffered I/O: use page cache */
        retval = filemap_read(iocb, iter, retval);
    }
    return retval;
}
```

### Direct I/O vs Buffered I/O

```mermaid
graph LR
    subgraph "Buffered I/O"
        A1[App] -->|read/write| PC1[Page Cache]
        PC1 -->|readahead/writeback| B1[Block Device]
    end
    subgraph "Direct I/O"
        A2[App] -->|O_DIRECT| B2[Block Device]
        Note2[Page cache bypassed]
    end
```

```bash
# Buffered I/O (default)
$ dd if=/dev/sda of=/tmp/file bs=1M count=100

# Direct I/O (bypass page cache)
$ dd if=/dev/sda of=/tmp/file bs=1M count=100 iflag=direct

# In C code
int fd = open("/data/file", O_RDWR | O_DIRECT);
```

## The Write Path

### Buffered Write Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant VFS as VFS
    participant PC as Page Cache
    participant WB as Writeback Thread
    participant Disk as Disk

    App->>VFS: write(fd, data, count)
    VFS->>PC: Grab/create page in cache
    VFS->>PC: Copy user data to page
    VFS->>PC: Mark page dirty
    VFS->>VFS: Update inode size, mtime
    VFS-->>App: Return bytes written (data NOT on disk yet)

    Note over PC,WB: Later, writeback triggers
    WB->>PC: Find dirty pages
    WB->>Disk: Write pages to disk
    Disk-->>WB: I/O complete
    WB->>PC: Clear dirty flag
```

### Write Ordering

```bash
# Check write ordering constraints
$ cat /proc/sys/vm/dirty_ratio
20

$ cat /proc/sys/vm/dirty_background_ratio
10

$ cat /proc/sys/vm/dirty_expire_centisecs
3000

# Force data to disk
$ sync                    # All filesystems
$ sync /data              # Specific mountpoint
$ fdatasync(fd)           # Per-file in C
```

## `open()` and `release()`

### File Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Allocated: open(2)
    Allocated --> InUse: fd installed in process
    InUse --> InUse: read/write/mmap/etc
    InUse --> LastClose: close(2) -- fd count → 0
    LastClose --> [*]: release() called

    note right of Allocated
        struct file allocated
        f_op set from inode->i_fop
        f_pos = 0
    end note

    note right of LastClose
        release() is called once
        when ALL references are gone
        (dup, fork, etc. create refs)
    end note
```

### `open()` Implementation

```c
/* Example: ext4_file_open() */
static int ext4_file_open(struct inode *inode, struct file *filp) {
    struct super_block *sb = inode->i_sb;

    /* Check for filesystem errors */
    if (EXT4_SB(sb)->s_mount_state & EXT4_ERROR_FS)
        return -EFSCORRUPTED;

    /* Set up DAX mode if applicable */
    if (IS_DAX(inode))
        filp->f_flags |= O_DAX;

    /* Call generic open */
    return generic_file_open(inode, filp);
}
```

### `flush()` vs `release()`

- **`flush()`**: Called on **every** `close()` system call, including dup'd file descriptors. Used for cleanup that should happen per-close (e.g., clearing advisory locks held by the process).
- **`release()`**: Called when the **last** reference to a `struct file` is gone. Used for final cleanup (freeing private data, releasing hardware resources).

```bash
# Demonstrate flush vs release
$ exec 3>/tmp/test     # Open fd 3
$ exec 4>&3            # dup: fd 4 → same struct file
$ exec 3>&-            # close fd 3 → flush() called
$ exec 4>&-            # close fd 4 → flush() called, then release()
```

## Asynchronous I/O (AIO)

### io_uring

Modern Linux uses `io_uring` for efficient async I/O:

```c
#include <liburing.h>

int main() {
    struct io_uring ring;
    io_uring_queue_init(256, &ring, 0);

    /* Prepare a read */
    struct io_uring_sqe *sqe = io_uring_get_sqe(&ring);
    io_uring_prep_read(sqe, fd, buf, 4096, 0);
    sqe->flags |= IOSQE_ASYNC;

    /* Submit */
    io_uring_submit(&ring);

    /* Wait for completion */
    struct io_uring_cqe *cqe;
    io_uring_wait_cqe(&ring, &cqe);
    int result = cqe->res;
    io_uring_cqe_seen(&ring, cqe);
}
```

### Legacy AIO

```c
#include <linux/aio_abi.h>
#include <sys/syscall.h>

/* Legacy AIO via syscalls */
aio_context_t ctx = 0;
syscall(__NR_io_setup, 128, &ctx);

struct iocb cb = {
    .aio_fildes = fd,
    .aio_lio_opcode = IOCB_CMD_PREAD,
    .aio_buf = (uint64_t)buf,
    .aio_nbytes = 4096,
    .aio_offset = 0,
};

struct iocb *cbs[1] = { &cb };
syscall(__NR_io_submit, ctx, 1, cbs);

struct io_event events[1];
syscall(__NR_io_getevents, ctx, 1, 1, events, NULL);
```

## splice and sendfile

### splice — Zero-Copy Data Movement

`splice()` moves data between a file descriptor and a pipe without copying through userspace:

```mermaid
graph LR
    subgraph "Traditional read+write"
        A1[Source FD] -->|copy_to_user| U1[Userspace Buffer]
        U1 -->|copy_from_user| D1[Destination FD]
    end
    subgraph "splice"
        A2[Source FD] -->|page cache| P2[Pipe Buffer]
        P2 -->|page cache| D2[Destination FD]
    end
```

```c
/* splice from file to pipe, then from pipe to socket */
int pfd[2];
pipe(pfd);

/* Move data from file to pipe (no copy) */
splice(file_fd, NULL, pfd[1], NULL, 4096, SPLICE_F_MOVE);

/* Move data from pipe to socket (no copy) */
splice(pfd[0], NULL, socket_fd, NULL, 4096, SPLICE_F_MOVE);
```

### sendfile

`sendfile()` is a specialized splice from file to socket:

```c
#include <sys/sendfile.h>

/* Send file directly to socket — zero copy */
sendfile(socket_fd, file_fd, &offset, count);
```

### copy_file_range (NFSv4.2)

Server-side copy for NFS:

```c
#include <unistd.h>

/* Copy between two file descriptors — may be offloaded to server */
copy_file_range(src_fd, &src_off, dst_fd, &dst_off, len, 0);
```

## File Locking

### Advisory Locking (flock / fcntl)

```mermaid
graph TD
    subgraph "flock -- Whole File Locks"
        FL1[LOCK_SH -- Shared lock]
        FL2[LOCK_EX -- Exclusive lock]
        FL3[LOCK_UN -- Unlock]
        FL4[LOCK_NB -- Non-blocking]
    end
    subgraph "fcntl -- POSIX Record Locks"
        FC1[F_RDLCK -- Read lock]
        FC2[F_WRLCK -- Write lock]
        FC3[F_UNLCK -- Unlock]
        FC4[F_SETLK -- Non-blocking]
        FC5[F_SETLKW -- Blocking]
    end
```

```c
/* flock: whole-file locking */
#include <sys/file.h>
int fd = open("/data/file", O_RDWR);
flock(fd, LOCK_EX);        /* Exclusive lock */
/* ... critical section ... */
flock(fd, LOCK_UN);        /* Unlock */

/* fcntl: POSIX record locking (byte-range) */
#include <fcntl.h>
struct flock fl = {
    .l_type   = F_WRLCK,    /* Write lock */
    .l_whence = SEEK_SET,
    .l_start  = 0,           /* Lock from byte 0 */
    .l_len    = 1024,        /* Lock 1024 bytes */
};
fcntl(fd, F_SETLKW, &fl);  /* Blocking set lock */
```

### Mandatory Locking (Deprecated)

```bash
# Mandatory locking requires:
# 1. Filesystem mounted with -o mand
# 2. File has SGID bit set, group execute bit cleared
mount -o mand /dev/sdb1 /mnt/mand
chmod g+s,g-x /mnt/mand/locked_file
# Note: mandatory locking is deprecated and removed in recent kernels
```

### leases — Delegation Locks

```c
/* Set a lease (delegation) on a file */
fcntl(fd, F_SETLEASE, F_RDLCK);  /* Read lease */
fcntl(fd, F_SETLEASE, F_WRLCK);  /* Write lease */

/* When another process tries to open for write,
 * the lease holder receives SIGIO and has time
 * to flush data before the lease is broken */
fcntl(fd, F_SETLEASE, F_UNLCK);  /* Break lease */
```

## fsync and fdatasync

```bash
# fsync: flush data AND metadata to disk
# fdatasync: flush data only (skip metadata if size unchanged)
# sync_file_range: fine-grained control over what gets flushed

$ strace -e trace=fsync,fdatasync dd if=/dev/zero of=/tmp/test bs=4k count=1 conv=fdatasync
fdatasync(1)    = 0
```

## Implementation Details

### Key Source Files

- **`fs/read_write.c`** — `read(2)`, `write(2)`, `lseek(2)` system call implementations
- **`fs/file_table.c`** — `struct file` allocation and management
- **`fs/splice.c`** — `splice(2)` and `sendfile(2)` implementations
- **`fs/locks.c`** — File locking implementation
- **`include/linux/fs.h`** — `file_operations` definition
- **`mm/filemap.c`** — Buffered I/O through the page cache

### The `struct file`

```c
struct file {
    union {
        struct llist_node   f_llist;
        struct rcu_head     f_rcuhead;
        unsigned int        f_iocb_flags;
    };
    struct path             f_path;       /* Mount point + dentry */
    struct inode           *f_inode;      /* Cached inode pointer */
    const struct file_operations *f_op;   /* File operations */
    spinlock_t              f_lock;
    atomic_long_t           f_count;      /* Reference count */
    unsigned int            f_flags;      /* O_RDONLY, O_NONBLOCK, etc. */
    fmode_t                 f_mode;       /* FMODE_READ, FMODE_WRITE, etc. */
    struct mutex            f_pos_lock;
    loff_t                  f_pos;        /* Current file position */
    struct fown_struct      f_owner;
    void                   *private_data; /* FS/driver private data */
    struct address_space   *f_mapping;    /* Page cache mapping */
};
```

## fallocate — Disk Space Allocation

`fallocate()` pre-allocates disk space without writing data, useful for reducing fragmentation:

```c
#include <fcntl.h>
#include <unistd.h>

int fd = open("/data/file", O_RDWR | O_CREAT, 0644);

/* Pre-allocate 1GB without writing zeros */
fallocate(fd, 0, 0, 1ULL << 30);
/* File now has 1GB of allocated blocks on disk */
/* lseek(fd, 0, SEEK_END) returns 1GB */

/* Allocate a hole (sparse file) */
fallocate(fd, FALLOC_FL_KEEP_SIZE, 0, 1ULL << 30);
/* Space allocated but file size unchanged */

/* Punch a hole (deallocate range) */
fallocate(fd, FALLOC_FL_PUNCH_HOLE | FALLOC_FL_KEEP_SIZE,
          1024*1024, 512*1024);
/* Deallocate 512KB starting at 1MB offset */

/* Collapse range (remove data, shift remaining) */
fallocate(fd, FALLOC_FL_COLLAPSE_RANGE, 0, 4096);
/* Remove first 4096 bytes, file shrinks */

/* Zero range */
fallocate(fd, FALLOC_FL_ZERO_RANGE, 0, 4096);
/* Zero first 4096 bytes (may punch hole on some FSes) */
```

### fallocate Flags

| Flag | Description |
|------|-------------|
| `0` | Allocate (default) |
| `FALLOC_FL_KEEP_SIZE` | Don't change file size |
| `FALLOC_FL_PUNCH_HOLE` | Deallocate (must pair with KEEP_SIZE) |
| `FALLOC_FL_COLLAPSE_RANGE` | Remove range, shift data |
| `FALLOC_FL_ZERO_RANGE` | Zero range (may deallocate) |
| `FALLOC_FL_INSERT_RANGE` | Insert space, shift data |
| `FALLOC_FL_UNSHARE_RANGE` | Unshare shared extents (COW) |

## copy_file_range — Server-Side Copy

`copy_file_range()` copies data between two file descriptors entirely in kernel space:

```c
#include <unistd.h>

int src_fd = open("/data/source.bin", O_RDONLY);
int dst_fd = open("/data/dest.bin", O_WRONLY | O_CREAT, 0644);
loff_t src_off = 0, dst_off = 0;
size_t len = 1ULL << 30;  /* 1GB */

/* Copy entirely in kernel — zero user-space copies */
ssize_t copied = copy_file_range(src_fd, &src_off, dst_fd, &dst_off, len, 0);
```

### NFS Server-Side Copy

On NFSv4.2+, `copy_file_range()` can offload the copy to the NFS server:

```mermaid
graph LR
    subgraph "Without copy_file_range"
        C1[Client] -->|"read data"| S1[Server]
        S1 -->|"data"| C1
        C1 -->|"write data"| S1
    end
    subgraph "With copy_file_range"
        C2[Client] -->|"copy on server"| S2[Server]
        S2 -->|"done"| C2
    end
```

```bash
# NFS server-side copy (no data transfer over network)
cp --reflink=auto /nfs/source.bin /nfs/dest.bin
# If NFSv4.2 server supports it, copy happens entirely on server
```

## File Descriptor Passing (SCM_RIGHTS)

File descriptors can be passed between unrelated processes via Unix domain sockets:

```c
#include <sys/socket.h>
#include <sys/un.h>

/* Sender: pass an fd */
int send_fd(int sock, int fd) {
    struct msghdr msg = {0};
    char buf[CMSG_SPACE(sizeof(int))];
    struct iovec io = { .iov_base = "x", .iov_len = 1 };
    struct cmsghdr *cmsg;

    msg.msg_iov = &io;
    msg.msg_iovlen = 1;
    msg.msg_control = buf;
    msg.msg_controllen = sizeof(buf);

    cmsg = CMSG_FIRSTHDR(&msg);
    cmsg->cmsg_level = SOL_SOCKET;
    cmsg->cmsg_type = SCM_RIGHTS;
    cmsg->cmsg_len = CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(cmsg), &fd, sizeof(fd));

    return sendmsg(sock, &msg, 0);
}

/* Receiver: receive the fd */
int recv_fd(int sock) {
    struct msghdr msg = {0};
    char buf[CMSG_SPACE(sizeof(int))];
    char dummy;
    struct iovec io = { .iov_base = &dummy, .iov_len = 1 };
    struct cmsghdr *cmsg;
    int fd;

    msg.msg_iov = &io;
    msg.msg_iovlen = 1;
    msg.msg_control = buf;
    msg.msg_controllen = sizeof(buf);

    recvmsg(sock, &msg, 0);
    cmsg = CMSG_FIRSTHDR(&msg);
    memcpy(&fd, CMSG_DATA(cmsg), sizeof(fd));
    return fd;
}
```

### FD Passing Use Cases

- **D-Bus**: passes file descriptors for D-Bus activation
- **systemd**: passes sockets to services (socket activation)
- **Wayland**: passes shared memory buffers between compositor and clients
- **Containers**: passes memfds between host and container

## Readahead and Prefetch

The kernel automatically prefetches data into the page cache:

```c
/* Readahead is triggered by:
 * 1. Sequential read pattern detection
 * 2. Explicit madvise(MADV_WILLNEED)
 * 3. posix_fadvise(POSIX_FADV_WILLNEED)
 * 4. fadvise64() syscall
 */

/* Application hints */
#include <fcntl.h>

/* Tell kernel we'll need this range soon */
posix_fadvise(fd, offset, len, POSIX_FADV_WILLNEED);

/* Tell kernel we won't need this anymore */
posix_fadvise(fd, offset, len, POSIX_FADV_DONTNEED);

/* Tell kernel access will be sequential */
posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL);

/* Tell kernel access will be random */
posix_fadvise(fd, 0, 0, POSIX_FADV_RANDOM);

/* Tell kernel we'll need this once (no caching) */
posix_fadvise(fd, 0, 0, POSIX_FADV_NOREUSE);
```

### Readahead Tuning

```bash
# Per-device readahead setting
echo 256 > /sys/block/sda/queue/read_ahead_kb  # 256KB readahead

# Default readahead
cat /sys/block/sda/queue/read_ahead_kb
# 128 (default)

# For sequential workloads (large file reads)
echo 2048 > /sys/block/sda/queue/read_ahead_kb

# For random workloads (databases)
echo 16 > /sys/block/sda/queue/read_ahead_kb
```

## File Advisory Locking Patterns

### Cooperative Locking

```c
/* Pattern: lock file to ensure single instance */
int acquire_lock(const char *path) {
    int fd = open(path, O_CREAT | O_RDWR, 0600);
    if (fd < 0) return -1;

    if (flock(fd, LOCK_EX | LOCK_NB) < 0) {
        if (errno == EWOULDBLOCK) {
            close(fd);
            return -1;  /* Another instance holds the lock */
        }
    }

    /* Write PID to lock file */
    ftruncate(fd, 0);
    dprintf(fd, "%d\n", getpid());
    return fd;  /* Keep fd open to hold lock */
}
```

### Byte-Range Locking for Databases

```c
/* Lock a specific record (byte range) for update */
int lock_record(int fd, off_t offset, size_t len) {
    struct flock fl = {
        .l_type   = F_WRLCK,
        .l_whence = SEEK_SET,
        .l_start  = offset,
        .l_len    = len,
    };
    return fcntl(fd, F_SETLKW, &fl);  /* Blocking */
}

/* Read lock (shared) */
int read_lock(int fd, off_t offset, size_t len) {
    struct flock fl = {
        .l_type   = F_RDLCK,
        .l_whence = SEEK_SET,
        .l_start  = offset,
        .l_len    = len,
    };
    return fcntl(fd, F_SETLKW, &fl);
}
```

## DAX (Direct Access) Mode

DAX bypasses the page cache for persistent memory (NVDIMM) and some SSDs:

```bash
# Enable DAX on a filesystem
mount -o dax /dev/pmem0 /mnt/pmem

# Or per-file DAX (since Linux 5.10)
xfs_io -c 'chattr +x' /mnt/pmem/file

# Check DAX status
xfs_info /mnt/pmem | grep dax
stat /mnt/pmem/file | grep -i dax
```

### DAX vs Buffered I/O

```mermaid
graph LR
    subgraph "Buffered I/O"
        A1[App] -->|read/write| PC[Page Cache]
        PC -->|writeback| B1[Block Device]
    end
    subgraph "DAX"
        A2[App] -->|load/store| PM[Persistent Memory]
        Note2["No page cache, no block layer"]
    end
```

DAX provides byte-addressable load/store access to persistent memory, achieving near-DRAM latency for reads.

## References

- [VFS file operations documentation](https://www.kernel.org/doc/html/latest/filesystems/vfs.html#file-operations)
- [include/linux/fs.h source](https://github.com/torvalds/linux/blob/master/include/linux/fs.h)
- [io_uring documentation](https://www.kernel.org/doc/html/latest/userspace-api/io_uring.html)
- [fallocate(2) man page](https://man7.org/linux/man-pages/man2/fallocate.2.html)
- [copy_file_range(2) man page](https://man7.org/linux/man-pages/man2/copy_file_range.2.html)
- [posix_fadvise(2) man page](https://man7.org/linux/man-pages/man2/posix_fadvise.2.html)
- [flock(2) man page](https://man7.org/linux/man-pages/man2/flock.2.html)
- https://kernel.dk/io_uring.pdf — "Efficient I/O with io_uring"
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)

## Related Topics

- [inode](./inode.md) — Inodes define default file operations
- [superblock](./superblock.md) — File operations work within superblock context
- [buffer-cache](../memory/buffer-cache.md) — How buffered I/O interacts with the page cache
- [f2fs](./f2fs.md) — F2FS file operations for flash storage
- [Disk I/O](../hardware/disk-io.md) — Block layer below file operations
- [Page Cache](../memory/page-cache.md) — Memory caching for file I/O
