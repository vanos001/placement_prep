# Completion Variables

## Introduction

A **completion** is a Linux kernel synchronization primitive designed for the pattern: "one thread tells another that something is done." Unlike semaphores or mutexes, completions are purpose-built for signaling—they have minimal overhead and avoid the pitfalls of using other primitives for this use case.

Completions solve a common problem in kernel code: Thread A starts an operation (e.g., DMA transfer, hardware command) and needs to wait for Thread B (or an interrupt handler) to signal that the operation finished. Before completions existed, developers misused semaphores for this, which led to race conditions and subtle bugs. Completions were added by Ingo Molnár in Linux 2.4.7 specifically to address this.

## The `completion` Structure

```c
#include <linux/completion.h>

struct completion {
    unsigned int done;          /* Signaling state */
    wait_queue_head_t wait;     /* Wait queue */
};
```

The structure is deliberately simple: a counter (`done`) and a wait queue. When `done` is nonzero, the completion has been signaled.

## Declaring and Initializing Completions

### Static Declaration

```c
/* Statically declared, initialized at compile time */
DECLARE_COMPLETION(my_completion);

/* With a specific wait queue key (for lockdep) */
DECLARE_COMPLETION_ONSTACK(my_completion);  /* On stack, for function scope */
```

### Dynamic Initialization

```c
/* Dynamically initialize */
struct completion my_comp;
init_completion(&my_comp);

/* Or with reinit (for reuse) */
reinit_completion(&my_comp);
```

### Complete Initialization Macro

```c
/* DECLARE_COMPLETION expands to: */
struct completion my_completion = {
    .done = 0,
    .wait = __WAIT_QUEUE_HEAD_INITIALIZER(my_completion.wait),
};
```

## Waiting for Completion

### `wait_for_completion()`

The primary waiting function. Sleeps until the completion is signaled:

```c
void wait_for_completion(struct completion *x);

/* Usage */
wait_for_completion(&my_completion);
/* Execution resumes here after complete() is called */
```

**Important**: This function **cannot be interrupted by signals**. The task will sleep until `complete()` is called, period. Use `wait_for_completion_interruptible()` if signal handling is needed.

### Interruptible Variants

```c
/* Returns -ERESTARTSYS if interrupted by signal */
int wait_for_completion_interruptible(struct completion *x);

/* Returns 0 on success, -ERESTARTSYS on signal, -ETIMEOUT on timeout */
int wait_for_completion_interruptible_timeout(
    struct completion *x,
    unsigned long timeout    /* jiffies */
);

/* Returns 0 on timeout, >0 (remaining jiffies) on success */
unsigned long wait_for_completion_timeout(
    struct completion *x,
    unsigned long timeout    /* jiffies */
);

/* Killable: can be interrupted by fatal signals only */
int wait_for_completion_killable(struct completion *x);

/* Returns 0 on success, -ERESTARTSYS if killed */
int wait_for_completion_killable_timeout(
    struct completion *x,
    unsigned long timeout
);
```

### Waiting with Timeout

```c
unsigned long timeout = msecs_to_jiffies(5000);  /* 5 seconds */
unsigned long ret;

ret = wait_for_completion_timeout(&my_completion, timeout);
if (ret == 0) {
    /* Timeout — completion was NOT signaled */
    pr_err("Operation timed out!\n");
    return -ETIMEDOUT;
} else {
    /* Success — ret contains remaining jiffies */
    pr_info("Completed with %lu jiffies remaining\n", ret);
}
```

## Signaling Completion

### `complete()` — Wake One Waiter

```c
void complete(struct completion *x);

/* Wakes exactly ONE waiting thread.
 * If multiple threads are waiting, only one is woken.
 * The done counter is incremented.
 * Commonly used in interrupt handlers.
 */
```

### `complete_all()` — Wake All Waiters

```c
void complete_all(struct completion *x);

/* Wakes ALL waiting threads.
 * Sets done to UINT_MAX/2 to indicate "permanently done."
 * Use when the event is a one-time occurrence that all waiters
 * should know about (e.g., device removal, shutdown).
 */
```

### `try_wait_for_completion()` — Non-blocking Check

```c
/* Returns true if completion was consumed, false otherwise */
bool try_wait_for_completion(struct completion *x);

/* Useful for polling scenarios */
if (try_wait_for_completion(&my_completion)) {
    /* Got it! */
} else {
    /* Not ready yet */
}
```

### `completion_done()` — Check Without Consuming

```c
/* Returns true if completion is signaled, false otherwise.
 * Does NOT consume the completion (doesn't decrement done).
 */
bool completion_done(struct completion *x);
```

## Typical Usage Pattern

### Producer-Consumer Example

```c
#include <linux/module.h>
#include <linux/completion.h>
#include <linux/kthread.h>
#include <linux/delay.h>

static DECLARE_COMPLETION(data_ready);
static int shared_data;

/* Producer thread */
static int producer_thread(void *data) {
    pr_info("Producer: generating data...\n");
    msleep(2000);  /* Simulate work */
    
    shared_data = 42;
    
    pr_info("Producer: data ready, signaling completion\n");
    complete(&data_ready);  /* Signal the consumer */
    
    return 0;
}

/* Consumer (module init) */
static int __init comp_demo_init(void) {
    pr_info("Consumer: starting producer\n");
    kthread_run(producer_thread, NULL, "producer");
    
    pr_info("Consumer: waiting for data...\n");
    wait_for_completion(&data_ready);
    
    pr_info("Consumer: got data = %d\n", shared_data);
    return 0;
}

static void __exit comp_demo_exit(void) {
    pr_info("Module unloaded\n");
}

module_init(comp_demo_init);
module_exit(comp_demo_exit);
MODULE_LICENSE("GPL");
```

**Expected output:**
```
Consumer: starting producer
Consumer: waiting for data...
Producer: generating data...
Producer: data ready, signaling completion
Consumer: got data = 42
```

### DMA Transfer Completion

```c
#include <linux/completion.h>
#include <linux/dma-mapping.h>

struct dma_context {
    struct completion transfer_done;
    dma_addr_t dma_handle;
    void *buffer;
};

/* DMA completion callback (called from interrupt handler) */
static void dma_callback(void *data) {
    struct dma_context *ctx = data;
    complete(&ctx->transfer_done);  /* Signal completion from IRQ */
}

/* Initiate and wait for DMA transfer */
int do_dma_transfer(struct device *dev, struct dma_context *ctx) {
    init_completion(&ctx->transfer_done);
    
    /* Allocate DMA buffer */
    ctx->buffer = dma_alloc_coherent(dev, BUFFER_SIZE,
                                      &ctx->dma_handle, GFP_KERNEL);
    
    /* Start async DMA transfer */
    start_dma_transfer(dev, ctx->dma_handle, BUFFER_SIZE,
                       dma_callback, ctx);
    
    /* Wait for interrupt-driven completion */
    if (wait_for_completion_timeout(&ctx->transfer_done,
                                     msecs_to_jiffies(5000)) == 0) {
        dev_err(dev, "DMA transfer timed out!\n");
        return -ETIMEDOUT;
    }
    
    dev_info(dev, "DMA transfer complete\n");
    return 0;
}
```

### Device Probe Synchronization

```c
/* Common pattern: driver probe waits for firmware load */
static DECLARE_COMPLETION(fw_loaded);

static void firmware_cb(const struct firmware *fw, void *ctx) {
    if (fw) {
        process_firmware(fw);
        release_firmware(fw);
    }
    complete(&fw_loaded);
}

static int my_driver_probe(struct platform_device *pdev) {
    int ret;
    
    init_completion(&fw_loaded);
    
    ret = request_firmware_nowait(THIS_MODULE, true,
                                   "mydevice.bin",
                                   &pdev->dev, GFP_KERNEL,
                                   NULL, firmware_cb);
    if (ret)
        return ret;
    
    /* Wait for firmware to be loaded */
    if (!wait_for_completion_timeout(&fw_loaded,
                                      msecs_to_jiffies(10000))) {
        dev_err(&pdev->dev, "Firmware load timed out\n");
        return -ETIMEDOUT;
    }
    
    return 0;
}
```

## Completion Lifecycle Diagram

```mermaid
sequenceDiagram
    participant Waiter as Waiting Thread
    participant Comp as Completion (done=0)
    participant Signaler as Signaling Thread/IRQ

    Waiter->>Comp: wait_for_completion()
    Note over Waiter: Thread sleeps (TASK_UNINTERRUPTIBLE)
    Note over Comp: done still 0
    
    Signaler->>Signaler: Perform operation (DMA, HW cmd, etc.)
    Signaler->>Comp: complete()
    Note over Comp: done = 1
    
    Comp->>Waiter: Wake up!
    Note over Waiter: Resumes execution
    Note over Comp: done = 0 (consumed)
```

### Multiple Waiters Scenario

```mermaid
sequenceDiagram
    participant T1 as Thread 1
    participant T2 as Thread 2
    participant T3 as Thread 3
    participant Comp as Completion (done=0)
    participant Sig as Signaler

    T1->>Comp: wait_for_completion() → sleeps
    T2->>Comp: wait_for_completion() → sleeps
    T3->>Comp: wait_for_completion() → sleeps
    
    Sig->>Comp: complete()
    Note over Comp: done++, wakes ONE waiter
    Comp->>T1: Wake up!
    Note over T2,T3: Still sleeping
    
    Sig->>Comp: complete_all()
    Note over Comp: done = UINT_MAX/2
    Comp->>T2: Wake up!
    Comp->>T3: Wake up!
    Note over T2,T3: Both woken
```

## complete() vs complete_all()

```mermaid
graph TD
    subgraph "complete()"
        C1["Thread 1: wait_for_completion()"] --> S1["Signal: complete()"]
        S1 --> W1["Only Thread 1 wakes"]
        C2["Thread 2: wait_for_completion()"] --> S1
        S1 --> ST2["Thread 2 stays asleep"]
    end
    
    subgraph "complete_all()"
        CA1["Thread 1: wait_for_completion()"] --> SA1["Signal: complete_all()"]
        CA2["Thread 2: wait_for_completion()"] --> SA1
        SA1 --> WA1["Thread 1 wakes"]
        SA1 --> WA2["Thread 2 wakes"]
    end
```

## Completion vs Semaphore vs Mutex

Choosing the right synchronization primitive is critical. Here's when to use each:

| Scenario | Use | Why |
|----------|-----|-----|
| "Wait for event/signal" | **Completion** | Purpose-built, no ownership issues |
| "Protect shared data" | **Mutex** | Has ownership, sleepable |
| "Protect shared data (atomic)" | **Spinlock** | No sleeping, fast |
| "Count resources" | **Semaphore** | Counting allows multiple holders |
| "Wait for condition" | **Wait queue** | More flexible, condition-based |

### Common Anti-pattern: Semaphore as Completion

```c
/* WRONG: Using semaphore for signaling (race condition!) */
struct semaphore sem;
sema_init(&sem, 0);

/* Thread A: */
down(&sem);  /* Wait for signal */

/* Thread B: */
up(&sem);    /* Signal */

/* Problem: if up() happens BEFORE down(),
 * the semaphore count is 1 and down() returns immediately.
 * This seems fine, but consider:
 * - What if you need to use it twice?
 * - What if multiple threads need to be signaled?
 * - The semantics are confusing and error-prone
 */

/* RIGHT: Use completion */
DECLARE_COMPLETION(done);
wait_for_completion(&done);   /* Always correct */
complete(&done);              /* Clear semantics */
```

### When NOT to Use Completions

```c
/* Don't use completions for mutual exclusion */
/* WRONG: Protecting a critical section with a completion */
wait_for_completion(&lock);  /* This doesn't make sense */
/* ... critical section ... */
complete(&lock);             /* Use a mutex instead! */

/* Don't use completions for counting/semaphore behavior */
/* WRONG: Multiple complete() calls to allow multiple entries */
complete(&comp);
complete(&comp);
complete(&comp);
/* Three waiters will be woken, but semantics are unclear */
/* Use a semaphore with count=3 instead */
```

## Reusing Completions

Completions can be reused by calling `reinit_completion()`:

```c
static DECLARE_COMPLETION(request_done);

void process_request(void) {
    reinit_completion(&request_done);  /* Reset done to 0 */
    
    submit_request();
    
    if (!wait_for_completion_timeout(&request_done,
                                      msecs_to_jiffies(1000))) {
        handle_timeout();
    }
}

/* Called from IRQ when request finishes */
void request_complete_irq(void) {
    complete(&request_done);
}
```

## Implementation Details

The completion implementation is efficient:

```c
/* Simplified kernel implementation */
void complete(struct completion *x) {
    unsigned long flags;
    spin_lock_irqsave(&x->wait.lock, flags);
    x->done++;
    __wake_up_locked(&x->wait, TASK_NORMAL, 1);
    spin_unlock_irqrestore(&x->wait.lock, flags);
}

void complete_all(struct completion *x) {
    unsigned long flags;
    spin_lock_irqsave(&x->wait.lock, flags);
    x->done += UINT_MAX / 2;
    __wake_up_locked(&x->wait, TASK_NORMAL, 0);  /* Wake all */
    spin_unlock_irqrestore(&x->wait.lock, flags);
}

void __sched wait_for_completion(struct completion *x) {
    might_sleep();
    spin_lock_irq(&x->wait.lock);
    if (x->done == 0) {
        DECLARE_WAITQUEUE(wait, current);
        __add_wait_queue_tail_exclusive(&x->wait, &wait);
        do {
            __set_current_state(TASK_UNINTERRUPTIBLE);
            spin_unlock_irq(&x->wait.lock);
            schedule();
            spin_lock_irq(&x->wait.lock);
        } while (!x->done);
        __remove_wait_queue(&x->wait, &wait);
    }
    x->done--;
    spin_unlock_irq(&x->wait.lock);
}
```

### Key Implementation Details

1. **Spinlock protection**: The `done` counter and wait queue are protected by `x->wait.lock`, a spinlock with IRQs disabled.

2. **`might_sleep()` check**: `wait_for_completion()` calls `might_sleep()` which warns if called in atomic context (holding a spinlock, in interrupt, etc.).

3. **`complete_all()` sets done to UINT_MAX/2**: This is a large sentinel value that ensures `done` will never wrap to 0. Any number of `complete()` calls after `complete_all()` will not change the state — the completion is permanently signaled.

4. **Memory barriers**: The spinlock acquire/release provides implicit memory barriers, ensuring that data written before `complete()` is visible to the waiter after `wait_for_completion()` returns.

5. **`wait_for_completion()` decrement**: After being woken, the waiter decrements `done`. This means each `complete()` call wakes exactly one waiter, and the completion can be reused.

## Performance Characteristics

| Operation | Cost (uncontended) | Cost (contended) |
|-----------|-------------------|------------------|
| `init_completion()` | ~5ns | N/A |
| `complete()` | ~30ns | ~100ns (IRQ save/restore + wake) |
| `complete_all()` | ~30ns + N×wake | ~100ns + N×wake |
| `wait_for_completion()` (already done) | ~15ns | N/A |
| `wait_for_completion()` (must sleep) | ~1-10µs | context switch cost |
| `wait_for_completion_timeout()` | ~15ns (done) | timer setup + context switch |

**Optimization**: If the completion is already signaled when `wait_for_completion()` is called, it returns immediately without sleeping. This is the fast path and costs only a spinlock acquire/release pair.

### Completion vs Wait Queue vs Semaphore

```mermaid
graph TD
    A["Need to wait for an event?"] --> B{"One-shot or repeated?"}
    B -->|One-shot| C{"Multiple waiters?"}
    B -->|Repeated| D["Use wait_queue + condition"]
    C -->|Yes| E["Use completion + complete_all()"]
    C -->|No| F["Use completion + complete()"]
    A --> G{"Need to count resources?"}
    G -->|Yes| H["Use semaphore"]
    G -->|No| I{"Need mutual exclusion?"}
    I -->|Yes| J["Use mutex"]
    I -->|No| K["Use completion"]
```

## Completion Reuse Anti-Patterns

### Anti-Pattern: Forgetting reinit_completion()

```c
/* BUG: Reusing completion without reinit */
static DECLARE_COMPLETION(done);

void process_request(void) {
    /* BUG: done might still be 1 from previous call! */
    submit_request();
    wait_for_completion(&done);  /* Returns immediately if done=1 */
}

/* CORRECT */
void process_request(void) {
    reinit_completion(&done);  /* Reset done to 0 */
    submit_request();
    wait_for_completion(&done);  /* Properly waits */
}
```

### Anti-Pattern: Using complete_all() When complete() Suffices

```c
/* BAD: complete_all() permanently signals the completion */
complete_all(&done);

/* If you later want to reuse it: */
reinit_completion(&done);  /* Must call this! */

/* BETTER: Use complete() for reusable completions */
complete(&done);  /* Wakes one waiter, done resets to 0 */
```

### Anti-Pattern: Completion as a Lock

```c
/* WRONG: Using completion for mutual exclusion */
wait_for_completion(&lock);  /* First call sleeps forever! */
/* ... critical section ... */
complete(&lock);

/* Use a mutex instead */
mutex_lock(&lock);
/* ... critical section ... */
mutex_unlock(&lock);
```

## Real-World Kernel Usage

### 1. I2C/SPI Driver Probe

```c
static DECLARE_COMPLETION(xfer_done);

static irqreturn_t spi_irq_handler(int irq, void *dev_id)
{
    complete(&xfer_done);
    return IRQ_HANDLED;
}

static int spi_transfer(struct spi_device *spi, u8 *buf, int len)
{
    reinit_completion(&xfer_done);

    spi_start_transfer(spi, buf, len);

    if (!wait_for_completion_timeout(&xfer_done,
                                      msecs_to_jiffies(1000))) {
        dev_err(&spi->dev, "SPI transfer timed out\n");
        return -ETIMEDOUT;
    }
    return 0;
}
```

### 2. USB Gadget Request Completion

```c
static void usb_request_complete(struct usb_ep *ep,
                                  struct usb_request *req)
{
    struct completion *done = req->context;
    complete(done);
}

int usb_transfer(struct usb_ep *ep, void *buf, int len)
{
    DECLARE_COMPLETION(done);
    struct usb_request *req;

    req = usb_ep_alloc_request(ep, GFP_KERNEL);
    req->buf = buf;
    req->length = len;
    req->context = &done;
    req->complete = usb_request_complete;

    usb_ep_queue(ep, req, GFP_KERNEL);
    wait_for_completion(&done);

    usb_ep_free_request(ep, req);
    return req->actual;
}
```

### 3. Module Init Synchronization

```c
static DECLARE_COMPLETION(kthread_ready);

static int worker_thread(void *data)
{
    /* Signal that thread is running */
    complete(&kthread_ready);

    while (!kthread_should_stop()) {
        do_work();
        msleep(100);
    }
    return 0;
}

static int __init my_module_init(void)
{
    struct task_struct *tsk;

    tsk = kthread_run(worker_thread, NULL, "my_worker");
    if (IS_ERR(tsk))
        return PTR_ERR(tsk);

    /* Wait for thread to be fully initialized */
    wait_for_completion(&kthread_ready);

    pr_info("Worker thread started\n");
    return 0;
}
```

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Linux kernel completion API](https://www.kernel.org/doc/Documentation/scheduler/completion.txt) — Official documentation
- [completions.h](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/completion.h) — Kernel header source
- [completion.c](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/sched/completion.c) — Implementation
- [LWN: Completions](https://lwn.net/Articles/313685/) — LWN article on completions

## Related Topics

- [Semaphores](./semaphores.md) — Counting synchronization primitive
- [Read-Write Locks](./rwlocks.md) — Reader/writer synchronization
- [Per-CPU Variables](./per-cpu.md) — Lock-free per-CPU data
