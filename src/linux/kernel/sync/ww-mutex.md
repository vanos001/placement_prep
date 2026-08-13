# Wound/Wait Mutexes (ww_mutex)

## Introduction

Wound/Wait mutexes (`ww_mutex`) are a specialized locking mechanism in the Linux kernel
designed to handle **multi-lock acquisition** scenarios without deadlocks. Unlike
traditional mutexes, which can deadlock when multiple threads acquire locks in different
orders, ww_mutexes use a priority-based protocol where older transactions either
**wound** (force rollback of) younger holders or **wait** for them, depending on
the protocol variant. This mechanism is critical for GPU drivers and other subsystems
where multiple resources must be locked simultaneously.

## The Deadlock Problem

Consider two threads trying to acquire two locks:

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant L1 as Lock A
    participant L2 as Lock B
    participant T2 as Thread 2

    T1->>L1: acquire(A) ✓
    T2->>L2: acquire(B) ✓
    T1->>L2: acquire(B) → BLOCKED (held by T2)
    T2->>L1: acquire(A) → DEADLOCK!
```

Traditional solutions (lock ordering) don't work when the set of locks needed
is dynamic and determined at runtime, as in GPU memory management where buffer
objects (BOs) are locked based on user-space requests.

### Why Static Lock Ordering Fails

```mermaid
graph TD
    A["Task 1 needs BOs: A, B, C"] --> B["Sort by address: A < B < C"]
    C["Task 2 needs BOs: B, C, D"] --> D["Sort by address: B < C < D"]
    B --> E["Lock A, then B, then C"]
    D --> F["Lock B, then C, then D"]
    E --> G["Works if addresses are known"]
    F --> G
    G --> H["But: address order ≠ creation order<br>Tasks discover needed BOs at runtime"]
    H --> I["ww_mutex solves this!"]

    style I fill:#38a169,color:#fff
```

## Wound/Wait Protocol

The protocol assigns a **wound context** (a monotonically increasing ticket number)
to each transaction. Two variants exist:

### Wound-Wait (Default in Linux)

- **Older thread wounds younger**: The older thread signals the younger to back off.
  The younger holder detects the wound and releases its locks, then retries.
- **Older thread waits for older**: If the holder is older, the requester waits.

### Wait-Wound

- **Older thread waits for younger**: The older thread waits, knowing the younger
  will finish quickly.
- **Younger thread backs off**: If the requester is younger, it backs off immediately
  and retries.

Linux uses the **Wound-Wait** variant by default.

```mermaid
graph TD
    A[Thread tries to acquire lock held by another] --> B{Compare timestamps}
    B -->|I am older| C[Wound the holder]
    B -->|I am younger| D[Wait for holder]
    C --> E[Holder detects wound, backs off]
    E --> F[Holder releases locks, retries]
    D --> G[Holder finishes, releases lock]
    G --> H[I acquire lock]
```

### Protocol Comparison

| Property | Wound-Wait (Linux) | Wait-Wound |
|----------|-------------------|------------|
| Older thread behavior | Wounds younger holder | Waits for younger holder |
| Younger thread behavior | Waits for older holder | Backs off immediately |
| Who restarts? | Younger (wounded) | Younger (backs off) |
| Starvation risk | Lower (older always wins) | Higher (older may wait for many young) |
| Implementation | Linux default | Alternative algorithm |

## Data Structures

### ww_acquire_ctx

The acquisition context tracks the state of a multi-lock transaction:

```c
struct ww_acquire_ctx {
    struct ww_class *ww_class;  /* Class (per subsystem) */
    unsigned long stamp;         /* Unique ticket/timestamp */
    unsigned int acquired;       /* Number of locks acquired */
    unsigned int done_acquire;   /* Set when all locks acquired */
    unsigned int contending;     /* Set if we were wounded */
    struct task_struct *task;    /* Owning task */
    /* ... internal fields ... */
};
```

### ww_mutex

Each ww_mutex wraps a standard mutex with wound/wait metadata:

```c
struct ww_mutex {
    struct mutex base;            /* Underlying mutex */
    struct ww_acquire_ctx *ctx;   /* Current owner's context */
    struct ww_class *ww_class;    /* Associated class */
};
```

### ww_class

The class groups related ww_mutexes and provides the protocol configuration:

```c
struct ww_class {
    atomic_long_t stamp;          /* Global ticket counter */
    struct lock_class_key acquire_key;
    struct lock_class_key mutex_key;
    const char *name;
    struct lock_class_key acquire_name;
};
```

### Structure Relationships

```mermaid
graph TD
    subgraph "ww_class (one per subsystem)"
        CLS["ww_class<br>stamp: atomic counter<br>name: 'reservation'"]
    end
    subgraph "ww_acquire_ctx (one per transaction)"
        CTX["ww_acquire_ctx<br>stamp: 42 (from class counter)<br>acquired: 3<br>contending: 0"]
    end
    subgraph "ww_mutex instances"
        L1["ww_mutex (BO A)<br>ctx: &amp;ctx"]
        L2["ww_mutex (BO B)<br>ctx: &amp;ctx"]
        L3["ww_mutex (BO C)<br>ctx: NULL (free)"]
    end
    CLS -->|"stamp++"| CTX
    CTX -->|"owns"| L1
    CTX -->|"owns"| L2
```

## API Usage

### Initialization

```c
/* Define a ww_class (typically one per subsystem) */
static DEFINE_WW_CLASS(my_ww_class);

/* Initialize a ww_mutex */
struct ww_mutex my_lock;
ww_mutex_init(&my_lock, &my_ww_class);
```

### Acquisition Pattern

The standard pattern acquires all locks within a single `ww_acquire_ctx`,
with a retry loop for handling wounds:

```c
int lock_multiple_bos(struct my_object **objs, int count)
{
    struct ww_acquire_ctx ctx;
    struct my_object *contended = NULL;
    int ret, i;

retry:
    /* Begin acquisition context */
    ww_acquire_init(&ctx, &my_ww_class);

    /* Acquire all locks */
    for (i = 0; i < count; i++) {
        if (objs[i] == contended) {
            contended = NULL;
            continue;  /* Skip the contended one, it's already unlocked */
        }

        ret = ww_mutex_lock(&objs[i]->lock, &ctx);
        if (ret == -EDEADLK) {
            /* We were wounded - back off */
            contended = objs[i];

            /* Drop all locks acquired so far */
            for (int j = i - 1; j >= 0; j--)
                ww_mutex_unlock(&objs[j]->lock);

            /* Wait for the contended lock to be released */
            ww_mutex_lock_slow(&contended->lock, &ctx);
            ww_mutex_unlock(&contended->lock);

            /* Restart the entire acquisition */
            goto retry;
        }
    }

    /* All locks acquired - do work */
    ww_acquire_fini(&ctx);
    return 0;
}
```

### The "Slow" Path

`ww_mutex_lock_slow()` is the key function for the wound-wait protocol. It waits
for the contended lock but also participates in the wound protocol:

```c
/* Wait for contended lock (slow path) */
ret = ww_mutex_lock_slow(&contended_lock, &ctx);
if (ret == -EDEADLK) {
    /* Still deadlocked — must retry */
    goto retry;
}
```

### API Reference

| Function | Description |
|----------|-------------|
| `ww_acquire_init(ctx, class)` | Begin a new acquisition context |
| `ww_mutex_lock(lock, ctx)` | Try to acquire; returns `-EDEADLK` if wounded |
| `ww_mutex_lock_slow(lock, ctx)` | Block until lock is available (slow path) |
| `ww_mutex_unlock(lock)` | Release a ww_mutex |
| `ww_acquire_fini(ctx)` | End the acquisition (all locks must be released) |
| `ww_mutex_trylock(lock)` | Non-blocking attempt (no wound check) |
| `ww_mutex_init(lock, class)` | Initialize a ww_mutex |
| `ww_mutex_destroy(lock)` | Destroy a ww_mutex |

## GPU Driver Use Case

The primary users of ww_mutexes are GPU drivers. The TTM (Translation Table Manager)
memory manager uses ww_mutexes to lock buffer objects:

```mermaid
graph TD
    A[GPU Command Submission] --> B[Identify BOs needed]
    B --> C[Sort BOs by address]
    C --> D[Lock BOs in order with ww_mutex]
    D --> E{All locked?}
    E -->|Yes| F[Execute GPU operations]
    E -->|EDEADLK| G[Wounded: back off]
    G --> H[Drop locks]
    H --> I[Wait for contended BO]
    I --> C
    F --> J[Release all locks]
```

### Real-World Example: amdgpu

```c
/* drivers/gpu/drm/amd/amdgpu/amdgpu_cs.c (simplified) */
int amdgpu_cs_ioctl(struct drm_device *dev, void *data,
                    struct drm_file *filp)
{
    struct amdgpu_cs_parser parser;
    struct ww_acquire_ctx ticket;
    int r;

    /* Parse the command submission and gather BO list */
    r = amdgpu_cs_parser_init(&parser, data, filp);
    if (r)
        return r;

    /* Lock all BOs with ww_mutex */
    r = ttm_eu_reserve_buffers(&ticket, &parser->validated, true);
    if (r)
        goto error;

    /* Execute the command submission */
    r = amdgpu_cs_ib_fill(parser.adev, &parser);

    /* Unlock all BOs */
    ttm_eu_backoff_reservation(&ticket, &parser->validated);

    return r;
}
```

### TTM Reserve/Backoff

The TTM library provides helpers built on ww_mutex:

```c
/* Reserve all buffer objects in the list */
int ttm_eu_reserve_buffers(struct ww_acquire_ctx *ticket,
                           struct list_head *list,
                           bool intr)
{
    struct ttm_validate_buffer *entry;
    int ret;

retry:
    ww_acquire_init(ticket, &reservation_ww_class);

    list_for_each_entry(entry, list, head) {
        struct dma_resv *resv = entry->bo->base.resv;

        ret = dma_resv_lock(resv, ticket);
        if (ret == -EDEADLK) {
            /* Back off all and wait for contended */
            ttm_eu_backoff_reservation_reverse(ticket, list, entry);
            dma_resv_lock_slow(resv, ticket);
            goto retry;
        }
    }

    ww_acquire_fini(ticket);
    return 0;
}
```

### DMA Resv (Modern Replacement)

In modern kernels (5.4+), the reservation object API was simplified:

```c
/* include/linux/dma-resv.h */
int dma_resv_lock(struct dma_resv *obj, struct ww_acquire_ctx *ctx);
int dma_resv_lock_interruptible(struct dma_resv *obj, struct ww_acquire_ctx *ctx);
void dma_resv_unlock(struct dma_resv *obj);

/* Slow path for wound recovery */
int dma_resv_lock_slow(struct dma_resv *obj, struct ww_acquire_ctx *ctx);
```

## Implementation Details

### Wound Detection

When a thread attempts to acquire a lock held by another:

```c
/* kernel/locking/mutex.c - simplified wound logic */
static int __ww_mutex_lock_check_stamp(struct ww_mutex *lock,
                                        struct ww_acquire_ctx *ctx)
{
    struct ww_acquire_ctx *hold_ctx = READ_ONCE(lock->ctx);

    if (!hold_ctx)
        return 0;  /* Lock is not held by a ww context */

    /* If holder is older (lower stamp), we must wait */
    if (__ww_stamp_after(hold_ctx->stamp, ctx->stamp))
        return 0;  /* Wait */

    /* We are older - wound the holder */
    if (!hold_ctx->contending) {
        hold_ctx->contending = 1;
        /* Wake the holder if it's sleeping */
    }

    return -EDEADLK;  /* Back off signal */
}
```

### Stamp Ordering

The stamp is a monotonically increasing counter using `atomic_long_inc_return()`:

```c
/* include/linux/ww_mutex.h */
static inline void ww_acquire_init(struct ww_acquire_ctx *ctx,
                                    struct ww_class *ww_class)
{
    ctx->ww_class = ww_class;
    ctx->stamp = atomic_long_inc_return(&ww_class->stamp);
    ctx->acquired = 0;
    ctx->done_acquire = 0;
    ctx->contending = 0;
    ctx->task = current;
}
```

### Lock Ordering Within ww_mutex

To avoid unnecessary wounds, locks in a batch should be sorted by address
before acquisition:

```c
/* Sort by address to minimize contention */
sort(objs, count, sizeof(*objs), cmp_bo_addr, NULL);

/* Then acquire in sorted order */
for (i = 0; i < count; i++) {
    ret = ww_mutex_lock(&objs[i]->lock, &ctx);
    if (ret == -EDEADLK) { /* handle wound */ }
}
```

### The Wound Path in Detail

```mermaid
sequenceDiagram
    participant T1 as Thread 1 (stamp=42, older)
    participant T2 as Thread 2 (stamp=43, younger)
    participant Lock as ww_mutex (held by T2)

    Note over T2: T2 holds Lock, ctx->stamp=43
    T1->>Lock: ww_mutex_lock(ctx stamp=42)
    Lock->>Lock: Check: 42 < 43 → T1 is older
    Lock->>T2: Set contending=1 (wound T2)
    Lock->>T1: Return -EDEADLK
    T1->>T1: Drop other locks, wait

    Note over T2: T2 checks contending flag
    T2->>T2: contending=1 → must back off
    T2->>Lock: Release lock
    T2->>T2: Restart acquisition

    T1->>Lock: ww_mutex_lock_slow() -- acquires
```

## Performance Considerations

| Scenario | Traditional mutexes | ww_mutex |
|----------|-------------------|----------|
| Single lock | Fast (no overhead) | Slightly slower (context tracking) |
| Multiple locks, no contention | Fast if ordered | Slightly slower (context setup) |
| Multiple locks, contention | Deadlock risk | Graceful backoff |
| GPU buffer objects | Requires global lock | Fine-grained locking |

### Overhead Sources

1. **Stamp allocation**: Atomic increment per transaction
2. **Context tracking**: Extra fields in mutex and context
3. **Wound propagation**: Must check and signal holders
4. **Retry cost**: Wounded transactions restart their lock acquisition

### Minimizing Overhead

```c
/* Good: Sort before locking (reduces unnecessary wounds) */
sort(objs, count, sizeof(*objs), cmp_bo_addr, NULL);
for (i = 0; i < count; i++)
    ww_mutex_lock(&objs[i]->lock, &ctx);

/* Bad: Random order (more wounds, more retries) */
for (i = 0; i < count; i++)
    ww_mutex_lock(&objs[rand() % count]->lock, &ctx);
```

## Comparison with Other Deadlock Avoidance

| Method | Approach | Limitation |
|--------|----------|-----------|
| Lock ordering | Static order | Requires known order; not dynamic |
| trylock + backoff | Non-blocking attempt | Starvation risk |
| Lockdep | Detection only (debug) | No runtime avoidance |
| ww_mutex | Priority-based preemption | Transaction restart cost |
| Hand-over-hand | Lock next, release prev | Only works for chains |

### Trylock + Backoff (Alternative)

```c
/* Simple but starvation-prone approach */
while (1) {
    if (mutex_trylock(&lock_a)) {
        if (mutex_trylock(&lock_b)) {
            /* Both acquired */
            break;
        }
        mutex_unlock(&lock_a);
    }
    /* Random backoff to reduce livelock */
    udelay(random() % 100);
}
```

This approach works but can **starve** — a thread may never succeed if others keep beating it. ww_mutex guarantees that the oldest transaction always wins.

## Debugging

### Lockdep Integration

ww_mutexes integrate with lockdep for deadlock detection during development:

```bash
# Enable lockdep in kernel config
CONFIG_LOCKDEP=y
CONFIG_DEBUG_LOCK_ALLOC=y
```

### Common Pitfalls

```c
/* WRONG: Mixing lock types */
ww_mutex_lock(&ww_lock, &ctx);
mutex_lock(&regular_lock);  /* Not tracked by ww context! */

/* WRONG: Holding locks across ww_acquire_fini */
ww_mutex_lock(&lock, &ctx);
ww_acquire_fini(&ctx);
/* Lock still held but context is gone - broken protocol! */

/* CORRECT: All locks released before fini */
ww_mutex_lock(&lock, &ctx);
do_work();
ww_mutex_unlock(&lock);
ww_acquire_fini(&ctx);
```

### Debugging Wound Events

```bash
# Enable ww_mutex debugging
CONFIG_DEBUG_WW_MUTEX_SLOWPATH=y

# Trace lock contention
echo 1 > /sys/kernel/debug/tracing/events/lock/enable
cat /sys/kernel/debug/tracing/trace_pipe | grep ww_mutex

# Check lock statistics
cat /proc/lock_stat | grep ww
```

## Lockdep Annotations for ww_mutex

Lockdep tracks ww_mutex acquisitions with special class keys to detect ordering violations between different ww_classes and between ww_mutexes and regular locks.

### Separate Lock Classes

Each `ww_class` gets its own lockdep class, so lockdep can detect when:
- Two different ww_classes are nested incorrectly
- A ww_mutex from class A is held while acquiring a regular lock in the wrong order
- A ww_mutex is held while acquiring another ww_mutex from the same class (expected, but tracked)

```c
/* include/linux/ww_mutex.h — lockdep annotation */
static inline void ww_acquire_init(struct ww_acquire_ctx *ctx,
                                    struct ww_class *ww_class)
{
    ctx->ww_class = ww_class;
    ctx->stamp = atomic_long_inc_return(&ww_class->stamp);
    /* ... */
    lock_acquire(&ww_class->acquire_key, 0, 0, 0, 1, NULL, _THIS_IP_);
}

static inline void ww_acquire_fini(struct ww_acquire_ctx *ctx)
{
    lock_release(&ctx->ww_class->acquire_key, _THIS_IP_);
    /* ... */
}
```

### Debug Configuration

```bash
# Full lockdep + ww_mutex debugging
CONFIG_LOCKDEP=y
CONFIG_DEBUG_LOCK_ALLOC=y
CONFIG_DEBUG_MUTEXES=y
CONFIG_DEBUG_WW_MUTEX_SLOWPATH=y
```

## Internal Wait Queue Mechanism

When a thread must wait (because it's younger than the holder), it sleeps on the mutex's wait queue. The wound mechanism adds extra wake-up logic:

```c
/* kernel/locking/mutex.c — __ww_mutex_lock_common() (simplified) */
static int __ww_mutex_lock(struct ww_mutex *lock,
                           struct ww_acquire_ctx *ctx)
{
    struct mutex_waiter waiter;

    /* Check if we should wound the holder */
    if (ctx) {
        struct ww_acquire_ctx *hold_ctx = READ_ONCE(lock->ctx);
        if (hold_ctx && __ww_stamp_after(ctx->stamp, hold_ctx->stamp)) {
            /* We are older — wound the holder */
            hold_ctx->contending = 1;
            wake_up_process(hold_ctx->task);  /* Wake holder to check wound */
            return -EDEADLK;
        }
    }

    /* We are younger — add ourselves to wait queue */
    waiter.task = current;
    list_add_tail(&waiter.list, &lock->base.wait_list);

    /* Sleep until woken */
    for (;;) {
        set_current_state(TASK_UNINTERRUPTIBLE);
        if (!mutex_is_locked(&lock->base))
            break;
        schedule();
    }

    /* Acquired */
    lock->ctx = ctx;
    return 0;
}
```

### Wait Queue Flow

```mermaid
sequenceDiagram
    participant T_young as Thread Y (stamp=50)
    participant WQ as Wait Queue
    participant T_old as Thread O (stamp=40)
    participant Lock as ww_mutex

    Note over Lock: Held by Thread O, ctx stamp=40
    T_young->>Lock: ww_mutex_lock(ctx stamp=50)
    Lock->>Lock: 50 > 40 → Y is younger
    Lock->>WQ: Add T_young to wait queue
    T_young->>T_young: Sleep (TASK_UNINTERRUPTIBLE)

    Note over T_old: T_old finishes work
    T_old->>Lock: ww_mutex_unlock()
    Lock->>WQ: Wake T_young
    WQ->>T_young: Wake up
    T_young->>Lock: Acquire lock (ctx stamp=50)
```

## Starvation Analysis

A key property of ww_mutex: **the oldest transaction always wins**. This guarantees that no transaction can be starved indefinitely.

### Proof Sketch

1. Each transaction gets a unique, monotonically increasing stamp
2. When two transactions contend, the older one (lower stamp) wounds the younger
3. The younger restarts, but with the same stamp (it doesn't get a new one)
4. The older transaction proceeds unimpeded
5. Since stamps are finite and ordered, each transaction will eventually be the oldest among contending transactions

### Practical Starvation Bound

In practice, a transaction may be wounded multiple times if many newer transactions run concurrently. The worst case is bounded by the number of concurrent transactions: a transaction can be wounded at most N-1 times (where N is the number of concurrent transactions), because each wound comes from a different, younger transaction.

```c
/* Simplified worst-case analysis */
/* Transaction T with stamp S */
/* At most (N-1) younger transactions can wound T */
/* After each wound, the younger transaction completes */
/* T eventually runs when all younger transactions clear */
```

## Usage Beyond GPU Drivers

While GPU drivers are the primary users, ww_mutexes are used in other subsystems:

### InfiniBand (RDMA)

```c
/* drivers/infiniband/core/ */
/* Multiple memory regions locked for DMA operations */
```

### Virtual File System (VFS)

```c
/* When multiple inodes must be locked for rename/rename operations */
/* VFS uses lock_two_nodes() which can benefit from ww_mutex patterns */
```

### Potential Future Uses

Any subsystem that needs to lock multiple resources of the same type dynamically can benefit from ww_mutex:
- Database buffer pool management
- Network packet buffer pools
- Storage device multi-queue locking

## Full Worked Example

```c
/* Complete example: locking multiple resources with ww_mutex */
#include <linux/module.h>
#include <linux/ww_mutex.h>

static DEFINE_WW_CLASS(resource_class);

struct resource {
    struct ww_mutex lock;
    int data;
};

int process_resources(struct resource **res, int count)
{
    struct ww_acquire_ctx ctx;
    struct resource *contended = NULL;
    int ret, i;

retry:
    ww_acquire_init(&ctx, &resource_class);

    /* Sort by address to minimize contention */
    sort(res, count, sizeof(*res), cmp_resource_addr, NULL);

    for (i = 0; i < count; i++) {
        if (res[i] == contended) {
            contended = NULL;
            continue;
        }

        ret = ww_mutex_lock(&res[i]->lock, &ctx);
        if (ret == -EDEADLK) {
            contended = res[i];

            /* Release all acquired locks */
            while (--i >= 0)
                ww_mutex_unlock(&res[i]->lock);

            /* Wait for contended lock */
            ww_mutex_lock_slow(&contended->lock, &ctx);
            ww_mutex_unlock(&contended->lock);

            goto retry;
        }
    }

    /* Critical section: all locks held */
    for (i = 0; i < count; i++)
        res[i]->data += 1;

    /* Release all and finalize */
    for (i = count - 1; i >= 0; i--)
        ww_mutex_unlock(&res[i]->lock);

    ww_acquire_fini(&ctx);
    return 0;
}
```

## Cross-References

- [Mutexes](mutexes.md) - Standard kernel mutexes
- [Spinlocks](spinlocks.md) - Busy-wait synchronization primitives
- [Lock Ordering](lock-ordering.md) - Lock ordering strategies
- [Lockdep](lockdep.md) - Lock dependency validator
- [RCU](rcu.md) - Read-Copy-Update synchronization
- [Block I/O Layer](../block/overview.md) - Block subsystem (uses similar patterns)
- [PCI Subsystem](../drivers/pci.md) - PCI locking patterns

## Further Reading

- [Wound/Wait mutexes documentation](https://www.kernel.org/doc/html/latest/locking/ww-mutex-design.html)
- [Original ww_mutex patch series (lore.kernel.org)](https://lore.kernel.org/lkml/?q=ww_mutex)
- [TTM reservation API](https://docs.kernel.org/gpu/drm-mm.html#the-reservation-object)
- [Maarten Lankhorst's ww_mutex talk](https://www.x.org/wiki/Events/XDC2014/XDC2014LankhorstWwMutexes/)
- [DMA Resv / Reservations (LWN.net)](https://lwn.net/Articles/783208/)
- [DRM GPU memory management](https://www.kernel.org/doc/html/latest/gpu/drm-mm.html)
