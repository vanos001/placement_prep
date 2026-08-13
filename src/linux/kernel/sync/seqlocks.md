# Seqlocks

## Introduction

Seqlocks (sequence locks) are a synchronization mechanism optimized for **read-mostly data** where readers must never block and can tolerate retrying. They were introduced in Linux 2.6 for the timekeeping subsystem and have since been adopted for networking statistics, VMA operations, and other read-heavy paths.

The key idea: a writer increments a **sequence counter** before and after modifying shared data. A reader reads the sequence counter, reads the data, then checks if the counter changed. If it did, a writer intervened, and the reader retries. This means readers never block — they may waste CPU cycles retrying, but they never sleep or spin on a lock.

## How Seqlocks Work

### Data Structure

```c
typedef struct {
    unsigned sequence;
    spinlock_t lock;
} seqlock_t;
```

The `sequence` counter is always even when no writer is active and odd when a writer holds the lock.

### Protocol

```mermaid
sequenceDiagram
    participant W as Writer
    participant Seq as Sequence Counter
    participant R as Reader

    Note over Seq: sequence = 4 (even = stable)
    R->>Seq: Read sequence = 4
    W->>Seq: sequence++ (now 5, odd = updating)
    W->>W: Modify shared data
    R->>R: Read shared data (may see partial update)
    W->>Seq: sequence++ (now 6, even = stable)
    R->>Seq: Read sequence = 6
    R->>R: 6 != 4 → RETRY
    R->>Seq: Read sequence = 6
    R->>R: Read shared data (consistent)
    R->>Seq: Read sequence = 6
    R->>R: 6 == 6 → SUCCESS
```

### Even/Odd Invariant

The sequence counter maintains a critical invariant:

- **Even**: No writer active, data is stable and consistent
- **Odd**: Writer is modifying data, readers should retry

```mermaid
graph LR
    E["sequence = N<br>(even)<br>STABLE"] -->|"write_seqlock()"| O["sequence = N+1<br>(odd)<br>UPDATING"]
    O -->|"write_sequnlock()"| E2["sequence = N+2<br>(even)<br>STABLE"]

    style E fill:#38a169,color:#fff
    style O fill:#e53e3e,color:#fff
    style E2 fill:#38a169,color:#fff
```

## API Reference

### Writer Side

```c
seqlock_t my_seqlock;

/* Initialize */
seqlock_init(&my_seqlock);
/* Or static: DEFINE_SEQLOCK(my_seqlock); */

/* Lock for writing — increments sequence to odd */
write_seqlock(&my_seqlock);
/* Modify shared data */
write_sequnlock(&my_seqlock);  /* Increments sequence to even */

/* With interrupt safety */
write_seqlock_irq(&my_seqlock);
write_sequnlock_irq(&my_seqlock);

write_seqlock_irqsave(&my_seqlock, flags);
write_sequnlock_irqrestore(&my_seqlock, flags);

/* With bottom-half safety */
write_seqlock_bh(&my_seqlock);
write_sequnlock_bh(&my_seqlock);

/* Try to lock for writing */
if (write_tryseqlock(&my_seqlock)) {
    /* Got lock */
    write_sequnlock(&my_seqlock);
}
```

### Reader Side

```c
unsigned int seq;
do {
    seq = read_seqbegin(&my_seqlock);
    /* Read shared data — NO locking, NO sleeping */
    val1 = shared_data.field1;
    val2 = shared_data.field2;
} while (read_seqretry(&my_seqlock, seq));
/* At this point, val1 and val2 are consistent */

/* With interrupt safety */
do {
    seq = read_seqbegin(&my_seqlock);
    /* ... */
} while (read_seqretry(&my_seqlock, seq));
```

**Critical constraint**: The reader's critical section must not modify any shared state, must not sleep, and must not have side effects that would be problematic if repeated.

### Writer Implementation

```c
/* include/linux/seqlock.h — write_seqlock() */
static inline void write_seqlock(seqlock_t *sl)
{
    spin_lock(&sl->lock);       /* Serialize writers */
    sl->sequence++;              /* Even → odd (data unstable) */
    smp_wmb();                   /* Ensure sequence update visible before data */
}

static inline void write_sequnlock(seqlock_t *sl)
{
    smp_wmb();                   /* Ensure data writes visible before sequence */
    sl->sequence++;              /* Odd → even (data stable) */
    spin_unlock(&sl->lock);
}
```

### Reader Implementation

```c
/* include/linux/seqlock.h — read_seqbegin() */
static inline unsigned read_seqbegin(const seqlock_t *sl)
{
    unsigned ret = READ_ONCE(sl->sequence);
    smp_rmb();  /* Ensure sequence read before data reads */
    return ret;
}

static inline unsigned read_seqretry(const seqlock_t *sl, unsigned start)
{
    smp_rmb();  /* Ensure data reads before sequence re-read */
    return READ_ONCE(sl->sequence) != start;
}
```

### Memory Barrier Placement

```mermaid
graph TD
    subgraph "Writer"
        W1["smp_wmb() after sequence++ (odd)"]
        W2["Write data"]
        W3["smp_wmb() before sequence++ (even)"]
    end
    subgraph "Reader"
        R1["Read sequence → start"]
        R2["smp_rmb()"]
        R3["Read data"]
        R4["smp_rmb()"]
        R5["Read sequence → end"]
        R6{"start == end?"}
        R6 -->|Yes| OK["Consistent!"]
        R6 -->|No| RETRY["Retry!"]
    end

    W1 --> W2 --> W3
    R1 --> R2 --> R3 --> R4 --> R5 --> R6

    style OK fill:#38a169,color:#fff
    style RETRY fill:#e53e3e,color:#fff
```

## Complete Example: Statistics Counter

```c
#include <linux/seqlock.h>
#include <linux/jiffies.h>

struct net_stats {
    unsigned long rx_packets;
    unsigned long tx_packets;
    unsigned long rx_bytes;
    unsigned long tx_bytes;
    unsigned long errors;
};

struct my_netdev {
    seqlock_t stats_lock;
    struct net_stats stats;
};

static void my_netdev_init(struct my_netdev *dev)
{
    seqlock_init(&dev->stats_lock);
    memset(&dev->stats, 0, sizeof(dev->stats));
}

/* Called from interrupt context when packet received */
static void update_rx_stats(struct my_netdev *dev, unsigned int bytes)
{
    /* Writer: single fast seqlock update */
    write_seqlock(&dev->stats_lock);
    dev->stats.rx_packets++;
    dev->stats.rx_bytes += bytes;
    write_sequnlock(&dev->stats_lock);
}

/* Called from process context (ethtool, /proc) */
static void get_stats(struct my_netdev *dev, struct net_stats *out)
{
    unsigned int seq;

    /* Reader: retry loop ensures consistency */
    do {
        seq = read_seqbegin(&dev->stats_lock);
        *out = dev->stats;  /* Structure copy — may see partial state */
    } while (read_seqretry(&dev->stats_lock, seq));
}
```

## seqcount_t: Lower-Level Primitive

`seqlock_t` is built on top of `seqcount_t`, which is the bare sequence counter without the spinlock:

```c
typedef struct {
    unsigned sequence;
} seqcount_t;

DEFINE_SEQCOUNT(my_seqcount);

/* Writer must serialize externally */
write_seqcount_begin(&my_seqcount);
/* Modify data */
write_seqcount_end(&my_seqcount);

/* Reader */
do {
    seq = read_seqcount_begin(&my_seqcount);
    /* Read data */
} while (read_seqcount_retry(&my_seqcount, seq));
```

`seqcount_t` is useful when you already have external serialization (e.g., a per-CPU lock) and just need the retry mechanism for readers.

### seqcount_t Implementation

```c
/* include/linux/seqlock.h */
static inline void raw_write_seqcount_begin(seqcount_t *s)
{
    s->sequence++;
    smp_wmb();
}

static inline void raw_write_seqcount_end(seqcount_t *s)
{
    smp_wmb();
    s->sequence++;
}
```

## seqcount_LOCKNAME_t Variants

The kernel provides typed seqcount variants that associate the write-side lock with the seqcount, enabling lockdep validation:

| Variant | Associated Lock | Use Case |
|---------|----------------|----------|
| `seqcount_spinlock_t` | spinlock_t | General kernel data |
| `seqcount_raw_spinlock_t` | raw_spinlock_t | RT-safe paths |
| `seqcount_rwlock_t` | rwlock_t | Reader-writer locked data |
| `seqcount_mutex_t` | mutex | Sleepable write paths |
| `seqcount_ww_mutex_t` | ww_mutex | GPU buffer objects |

```c
/* Example: seqcount with associated spinlock */
typedef struct {
    seqcount_spinlock_t seqcount;
    spinlock_t lock;
    /* protected data */
} my_data_t;

/* Writer — lockdep can verify lock is held */
spin_lock(&data->lock);
write_seqcount_begin(&data->seqcount.seqcount);
/* modify data */
write_seqcount_end(&data->seqcount.seqcount);
spin_unlock(&data->lock);
```

## Use Cases in the Linux Kernel

### Timekeeping

The primary original use case. The kernel's timekeeping data (jiffies, wall time, monotonic clock) is updated by the timer interrupt but read millions of times per second from user space:

```c
/* In kernel/time/timekeeping.c */
struct timekeeper {
    seqcount_t seq;
    /* ... timekeeping state ... */
};

/* Reader: get current time */
void ktime_get_ts64(struct timespec64 *ts)
{
    struct timekeeper *tk = &tk_core.timekeeper;
    unsigned int seq;

    do {
        seq = read_seqcount_begin(&tk->seq);
        /* Read time values */
        *ts = tk_xtime(tk);
    } while (read_seqcount_retry(&tk->seq, seq));
}
```

### VMA (Virtual Memory Area) Operations

Memory-mapped regions use seqlocks for concurrent reads:

```c
/* In mm/memory.c or include/linux/mm.h */
struct vm_area_struct {
    /* ... */
    seqcount_t vm_sequence;  /* Per-VMA seqlock */
};
```

### Network Statistics

As shown in the example above, network device statistics use seqlocks for lock-free reads from `/proc/net/dev` and `ethtool -S`.

### d_path and Mount Pathname Resolution

```c
/* In fs/dcache.c */
struct mount {
    /* ... */
    seqcount_t mnt_seqcount;
};
```

### Kernel Time Access (jiffies)

```c
/* include/linux/jiffies.h */
extern seqcount_t jiffies_lock;

/* Fast jiffies read with seqcount */
u64 get_jiffies_64(void)
{
    unsigned int seq;
    u64 ret;

    do {
        seq = read_seqcount_begin(&jiffies_lock);
        ret = jiffies_64;
    } while (read_seqcount_retry(&jiffies_lock, seq));

    return ret;
}
```

## Seqlock vs RCU

Both seqlocks and RCU optimize for read-heavy workloads, but they have different properties:

| Property | Seqlock | RCU |
|----------|---------|-----|
| Reader blocks? | No (retries) | No |
| Reader can sleep? | No | No (SRCU: yes) |
| Writer blocks reader? | Briefly (reader retries) | Never |
| Reader sees stale data? | Yes, temporarily | Yes, until grace period |
| Reader-side cost | Very low | Near-zero |
| Memory ordering | Strong (retry detects changes) | Weaker (grace period) |
| Overhead on writer | Low (sequence increment) | Grace period management |
| Use case | Read-mostly, small data | Read-mostly, pointer-based structures |

**Use seqlocks when:**
- The data being read is small and fits in a few cache lines
- Readers can tolerate retrying (low write frequency)
- You need consistent snapshots of multiple values

**Use RCU when:**
- The data structure is large (linked lists, trees, hash tables)
- Pointer-based indirection is natural
- You need zero reader-side overhead

```mermaid
graph TD
    DATA{"What kind of data?"} --> SMALL["Small, fixed-size<br>(counters, timestamps,<br>struct snapshot)"]
    DATA --> LARGE["Large, pointer-based<br>(linked lists, trees,<br>hash tables)"]
    SMALL --> SEQ["Use seqlock<br>Retry-based consistency"]
    LARGE --> RCU["Use RCU<br>Pointer-swap consistency"]

    style SEQ fill:#3182ce,color:#fff
    style RCU fill:#38a169,color:#fff
```

## Seqlock vs rwlock

| Property | Seqlock | rwlock |
|----------|---------|--------|
| Reader blocks writer? | No | Yes |
| Writer blocks reader? | Reader retries | Yes (reader waits) |
| Reader can starve writer? | No (writer priority) | Possible |
| Fairness | Writer-biased | Can be unfair either way |
| Reader-side atomic ops? | None (just reads) | Yes (atomic increment) |
| Cache-line bouncing (readers) | None | Yes (shared counter) |

Seqlocks are ideal when writes are rare and readers must never be blocked.

## The write_seqcount_barrier

For cases where you need a barrier without the full seqlock overhead:

```c
/* Writer: ensure all prior stores are visible before sequence update */
write_seqcount_begin(&seqcount);
smp_wmb();  /* All prior stores to data visible before sequence becomes odd */
/* ... modify data ... */
smp_wmb();  /* All stores to data visible before sequence becomes even */
write_seqcount_end(&seqcount);
```

## Lock Ordering with Seqlocks

Seqlocks interact with lockdep. The spinlock inside `seqlock_t` is tracked by lockdep, but the read-side is lockless and thus invisible to lockdep. This can mask ordering issues:

```c
/* Writer holds the seqlock spinlock — tracked by lockdep */
write_seqlock(&my_seqlock);
/* But also holds other locks? Lockdep doesn't know about read_seqbegin */
```

If your writer acquires other locks inside the seqlock critical section, you should annotate them for lockdep.

## Reader-Side Constraints

Because readers may execute their critical section multiple times (due to retries), the read-side code must be:

1. **Idempotent**: No side effects that cause problems if repeated
2. **Non-sleeping**: No calls to `schedule()`, `mutex_lock()`, etc.
3. **Side-effect free**: No writes to shared state
4. **Bounded**: The read-side critical section should be short

```c
/* BAD: Side effect in reader */
do {
    seq = read_seqbegin(&my_seqlock);
    counter++;  /* BUG: this may increment multiple times! */
} while (read_seqretry(&my_seqlock, seq));

/* GOOD: Read-only */
do {
    seq = read_seqbegin(&my_seqlock);
    local_copy = shared_data;
} while (read_seqretry(&my_seqlock, seq));
```

## Performance Characteristics

### Reader Overhead

The reader does:
1. Read the sequence counter (one memory load)
2. Read the shared data
3. Read the sequence counter again (one memory load)
4. Compare the two reads

If no writer intervened, this is just 2 extra loads — essentially free. Even with retries, the cost is proportional to the write rate.

### Writer Overhead

The writer does:
1. Acquire the spinlock (may contend)
2. Increment sequence counter (one atomic store)
3. Modify data
4. Increment sequence counter (one atomic store)
5. Release spinlock

The spinlock ensures only one writer at a time, but writers don't need to wait for readers.

### When Readers Retry

Readers retry only when a writer is actively modifying the data. The retry probability is approximately:

```
P(retry) ≈ (write_duration × write_frequency) / read_frequency
```

For typical read-mostly workloads (e.g., timekeeping: billions of reads per second, a few writes per second), the retry probability is negligible.

### Performance vs Alternatives

```mermaid
graph LR
    subgraph "Read Cost"
        SEQ_R["Seqlock<br>2 loads + compare<br>(essentially free)"]
        RW_R["rwlock<br>atomic inc/dec<br>(cache-line bounce)"]
        MUTEX_R["Mutex<br>lock/unlock<br>(may block)"]
    end
    subgraph "Write Cost"
        SEQ_W["Seqlock<br>spinlock + 2 inc<br>(light)"]
        RW_W["rwlock<br>spinlock<br>(blocks readers)"]
        MUTEX_W["Mutex<br>lock/unlock<br>(blocks everyone)"]
    end

    style SEQ_R fill:#38a169,color:#fff
    style RW_R fill:#d69e2e,color:#fff
    style MUTEX_R fill:#e53e3e,color:#fff
```

## Advanced: seqcount_latch_t

The **latch** variant provides two copies of the data. Writers update the inactive copy and then flip the latch. Readers always get a consistent copy without retrying:

```c
seqcount_latch_t latch;

/* Writer */
raw_write_seqcount_latch(&latch);
/* Update data[latch->sequence & 1] */
raw_write_seqcount_latch_end(&latch);

/* Reader — always gets a consistent copy */
do {
    seq = raw_read_seqcount_latch(&latch);
    /* Read data[seq & 1] */
} while (read_seqcount_latch_retry(&latch, seq));
```

This is used in the timekeeping subsystem where even the rare retry is too expensive.

### Latch Implementation

```mermaid
graph TD
    subgraph "Latch: Two Data Copies"
        D0["data[0]<br>Copy A"]
        D1["data[1]<br>Copy B"]
    end
    W["Writer"] -->|"sequence is even<br>update data[1]"| D1
    W2["Writer"] -->|"sequence is odd<br>update data[0]"| D0
    R["Reader"] -->|"seq &amp; 1 == 0<br>read data[0]"| D0
    R2["Reader"] -->|"seq &amp; 1 == 1<br>read data[1]"| D1
```

### Latch Use Case: Timekeeping

```c
/* kernel/time/timekeeping.c (simplified) */
struct tk_read_base {
    u64 cycle_last;
    u64 mult;
    u64 xtime_nsec;
    /* ... */
};

struct timekeeper {
    struct tk_read_base base[2];  /* Two copies! */
    seqcount_latch_t seq;
};

/* Reader: always gets consistent time data */
u64 ktime_get_mono_fast_ns(void)
{
    struct timekeeper *tk = &tk_core.timekeeper;
    struct tk_read_base *base;
    unsigned int seq;

    do {
        seq = raw_read_seqcount_latch(&tk->seq);
        base = &tk->base[seq & 1];  /* Read from stable copy */
    } while (read_seqcount_latch_retry(&tk->seq, seq));

    return base->xtime_nsec;
}
```

## Debugging Seqlocks

### Detecting Read-Side Violations

```c
/* CONFIG_DEBUG_LOCK_ALLOC tracks seqlock_t's internal spinlock */
/* But the read-side is invisible to lockdep */

/* Manual check: ensure read-side doesn't acquire other locks */
```

### Lock Statistics

The spinlock portion of `seqlock_t` is tracked by lockstat:

```bash
$ sudo cat /proc/lock_stat | grep seqlock
```

### Common Pitfalls

```c
/* BAD: Pointer dereference in reader */
do {
    seq = read_seqbegin(&my_seqlock);
    ptr = data->pointer;        /* OK: read pointer */
    val = ptr->field;           /* DANGER: pointer may be stale! */
} while (read_seqretry(&my_seqlock, seq));

/*
 * Seqlocks CANNOT protect data containing pointers that change.
 * If a writer updates `data->pointer`, the reader may follow
 * a freed pointer. Use RCU for pointer-based data.
 */
```

### Detecting Stale Pointer Access

```bash
# Enable KASAN to catch use-after-free from stale seqlock pointers
CONFIG_KASAN=y
CONFIG_KASAN_GENERIC=y
```

## Seqlock Internals (from docs.kernel.org)

The kernel documentation at `docs.kernel.org/locking/seqlock.html` provides the authoritative reference for sequence counters and sequential locks. Key details from the official documentation:

### Three Categories of Seqlock Readers

The documentation defines three types of readers for `seqlock_t`:

1. **Normal sequence readers**: Never block a writer, must retry if a writer is in progress. Writers do not wait for sequence readers.
2. **Locking readers** (`read_seqlock_excl`): Wait if a writer or another locking reader is in progress. Exclusive — only one locking reader can acquire it.
3. **Conditional lockless/locking readers** (`read_seqbegin_or_lock`): Try lockless first (even marker), fall back to locking read (odd marker) to avoid reader starvation during write spikes.

```c
/* Conditional reader pattern */
unsigned int seq;
int need_lock = 0;  /* Start lockless */

do {
    seq = read_seqbegin(&my_seqlock);
    if (need_lock) {
        spin_lock(&my_seqlock.lock);
        seq = 1;  /* Force odd to detect we hold lock */
    }
    /* Read data */
    need_lock = 1;  /* Next iteration, use locking path */
} while (read_seqretry(&my_seqlock, seq));

if (need_lock)
    spin_unlock(&my_seqlock.lock);
```

### Key Constraint

The documentation emphasizes: **this mechanism cannot be used if the protected data contains pointers**, as the writer can invalidate a pointer that the reader is following.

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Linux Kernel Documentation: seqlock](https://www.kernel.org/doc/html/latest/locking/seqlock.html)
- [Stephen Hemminger: "Seqlocks in Linux"](https://lwn.net/Articles/22805/)
- [Linux Kernel Source: include/linux/seqlock.h](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/seqlock.h)
- [LWN: "Sequence counters and latch counters"](https://lwn.net/Articles/633627/)
- [Sequence counters and sequential locks](https://docs.kernel.org/locking/seqlock.html) — Official kernel seqlock documentation

## Related Topics

- [Synchronization Overview](overview.md) — When and why locks are needed
- [RCU](rcu.md) — Another reader-optimized synchronization mechanism
- [Spinlocks](spinlocks.md) — Used internally by seqlock_t
- [Atomic Operations](atomic-ops.md) — Memory barriers and atomic operations
- [Lockdep](lockdep.md) — Debugging lock ordering issues
