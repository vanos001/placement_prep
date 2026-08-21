# The Java Memory Model (JMM)

## Why a Memory Model at All?

A memory model is the contract between the language and the hardware/compiler that says "given a concurrent program, what *must* you be able to observe?" It is the answer to the question "is this `int` field, written by one thread and read by another, ever allowed to be seen as a stale value or a torn write?"

Hardware reorders instructions aggressively. Compilers reorder too. The naive mental model — *the program runs in program order* — is a lie in the presence of multiple cores with multiple cache levels. The JMM, defined in **JLS Chapter 17**, is the contract that says which reorderings are legal and which observable behaviors are allowed.

The original JLS (1996) had a memory model that was broken in well-known ways (it allowed publication of `final` fields mid-construction, and reordering of writes across `synchronized` blocks in pathological ways). JSR 133 fixed this in JDK 5; the FAQ at <https://www.cs.umd.edu/~pugh/java/memoryModel/jsr-133-faq.html> remains the canonical plain-language reference.

## The Happens-Before Order

The JMM is built on a single partial order called **happens-before**. If `A` happens-before `B`, then (a) any write done by `A` is visible to `B` and (b) the program order of `A` and `B` is preserved *as observed by `B`*. If there is no happens-before edge between two actions, they are in a *data race* and the JMM does not promise any consistent observation.

The rules that establish happens-before (JLS §17.4.5):

1. **Program order rule**: each action in a thread happens-before every action *later in program order* in that same thread.
2. **Monitor lock rule**: an `unlock` on a monitor happens-before every subsequent `lock` on that same monitor.
3. **Volatile rule**: a write to a `volatile` field happens-before every subsequent read of that field.
4. **Thread start rule**: `Thread.start()` happens-before any action in the started thread.
5. **Thread termination rule**: actions in a thread happen-before another thread successfully returns from `join()` on it.
6. **Interruption rule**: a thread calling `interrupt()` happens-before the interrupted thread detects it.
7. **`final` initializer rule**: the write of the *default* value to a `final` field happens-before the first read, and the write of the *actual* value (in the constructor) happens-before any read by another thread — *provided the constructor does not let `this` escape*.
8. **Transitivity**: if `x` happens-before `y` and `y` happens-before `z`, then `x` happens-before `z`.

A correctly synchronized program has no data races — every read sees the most recent write that happens-before it. The formal definition of "correctly synchronized" is: *the execution is consistent under all interleavings the JMM admits.*

## Visibility, Reordering, and Memory Barriers

To enforce happens-before, the JIT and hardware must *not* reorder certain memory operations across what we call memory barriers. The classic table (closely mirrored by JSR-133's `LoadLoad`, `StoreStore`, `LoadStore`, `StoreLoad` barriers):

```
   Barrier       Prevents reordering of
   ─────────────────────────────────────────────
   LoadLoad     Load1; LoadLoad; Load2     → Load1 strictly before Load2
   StoreStore   Store1; StoreStore; Store2 → Store1 strictly before Store2
   LoadStore     Load1; LoadStore; Store2  → Load1 strictly before Store2
   StoreLoad    Store1; StoreLoad; Load2   → Store1 strictly before Load2  (the most expensive)
```

A `volatile` read in HotSpot compiles to a `LoadLoad + LoadStore` pair on x86 (`mov` + acquire semantics). A `volatile` write compiles to a `StoreStore` (the compiler barrier) followed by `StoreLoad` (the expensive one — on x86 this is `mov ... ; mov $0, dummy(%rsp); mfence` historically; modern builds use `mov` to a normal address followed by an implicit `lock`-prefixed instruction, which is cheaper than `mfence`).

`final` fields use `StoreStore` at the end of the constructor (a special epilogue C2 emits for every constructor that initializes a `final`). `synchronized` uses `StoreLoad` on entry (acquire) and `StoreStore`+`LoadStore` on exit (release).

## volatile, synchronized, final

A `volatile` field in Java gives you three things at once:

1. **Visibility**: writes to a `volatile` field are visible to subsequent reads in any thread, even without synchronization.
2. **Atomicity for single reads/writes of `long`/`double** (JLS §17.7 — non-`volatile` `long`/`double` are allowed to be split into two 32-bit writes; `volatile` guarantees atomicity).
3. **No reordering** across the field access, in either direction.

What `volatile` does *not* give you is atomicity across *multiple* volatile fields. This is broken:

```java
// BROKEN — looks safe, isn't
private volatile int x, y;

public void update() {
    x = 1;  // volatile write
    y = 2;  // volatile write — a reader may observe x=1,y=0
}
```

Each write is atomic, but a reader may see them in the wrong order if the two writes happen to land in different cache lines and there's no `StoreStore` between them — which `volatile` does provide, so actually for *the same thread's* two `volatile` writes, there is a happens-before edge. But a reader doing `int a = y; int b = x;` may still see `a=2, b=0` if `x`'s cache line is stale. The lesson: don't try to encode invariants across multiple `volatile` fields.

`synchronized` is the heavyweight alternative — it gives you mutual exclusion *and* visibility. The monitor's acquire/release forms a happens-before pair, just like `volatile`. The difference is scope: `volatile` is per-field, `synchronized` is per-monitor (a whole block).

```java
class Counter {
    private long count;            // not volatile — synchronized covers it
    private final Object lock = new Object();

    void increment() {
        synchronized (lock) {     // acquire: read barrier in
            count++;
        }                         // release: write barrier out
    }

    long get() {
        synchronized (lock) {
            return count;
        }
    }
}
```

`final` fields get safe publication *for free*: if the constructor does not let `this` escape, any thread that observes a reference to the object (through any means — race, weak reference, anything) is guaranteed to see the `final` fields at least as initialized by the constructor. The non-`final` fields get no such guarantee — you can observe a partially-constructed `HashMap` if you race on publication, because the writes inside the `HashMap` constructor aren't `final`.

```java
class Safe {
    private final int x;          // safe publication: any reader sees x=42
    private int y;                // NOT safe: a reader may see y=0

    public Safe() {
        this.x = 42;
        this.y = 42;
    }
}
```

The trick that makes this work is the `StoreStore` barrier at the end of every constructor that initializes a `final` field. Without it, the constructor's writes to fields could be reordered with the store that publishes the reference itself.

## Safe Publication

The idiomatic safe-publiccation patterns:

1. **Static initializer**: anything done in `<clinit>` is visible to all threads — `<clinit>` runs under synchronization, and class initialization establishes happens-before with anyone who later reads the class.
2. **`final` fields**: per the rule above.
3. **`volatile` or `AtomicReference`**: publish the reference through a `volatile` field or an `Atomic*` reference.
4. **`synchronized` blocks on both ends**: write under one monitor, read under the same monitor.

The classic broken pattern is **double-checked locking**:

```java
// BROKEN in this naive form
class Lazy {
    private static Config config;
    public static Config get() {
        if (config == null) {
            synchronized (Lazy.class) {
                if (config == null) {
                    config = new Config();   // ⚠️
                }
            }
        }
        return config;
    }
}
```

The bug: the *first* read (`if (config == null)`) is outside the monitor. The constructor of `Config` performs several stores; if the JIT reorders the constructor's store of `Config.x` *after* the store that publishes the reference, a racing reader sees a non-null `config` whose fields are still 0/null. This is *exactly* what `final` was designed to fix; if `Config`'s fields are `final`, the publication is safe. If not, the canonical fix is `volatile`:

```java
// FIXED — volatile read acts as the load-acquire
class Lazy {
    private static volatile Config config;
    public static Config get() {
        Config local = config;     // one volatile read
        if (local == null) {
            synchronized (Lazy.class) {
                local = config;
                if (local == null) {
                    local = new Config();
                    config = local;  // one volatile write
                }
            }
        }
        return local;
    }
}
```

The local-variable trick is for performance: a `volatile` read is more expensive than a plain field load. Reading into a local once means we do the expensive read once per `get()` call instead of two or three times.

## The Standard Library — `Atomic*`, `VarHandle`, `LongAdder`

Post-JDK 9, `VarHandle` lets you express per-field memory ordering:

```java
import java.lang.invoke.MethodHandles;
import java.lang.invoke.VarHandle;
import java.nio.ByteBuffer;

class PaddedCounter {
    private static final VarHandle COUNTER;
    static {
        try {
            COUNTER = MethodHandles.lookup()
                .findVarHandle(PaddedCounter.class, "v", long.class);
        } catch (ReflectiveOperationException e) {
            throw new RuntimeException(e);
        }
    }

    private volatile long v;          // volatile so plain reads are OK

    public long getAcquire() {
        return (long) COUNTER.getAcquire(this);
    }
    public void setRelease(long x) {
        COUNTER.setRelease(this, x);
    }
    public long getOpaque() {
        return (long) COUNTER.getOpaque(this);
    }
    public boolean cas(long expected, long updated) {
        return COUNTER.compareAndSet(this, expected, updated);
    }
}
```

The access modes map onto the same barrier lattice you'd expect:

```
   Access mode       Strength              Roughly equivalent
   ──────────────────────────────────────────────────────────
   getOpaque         opaque                plain load + in-order CPU guarantee
   getAcquire        acquire               LoadLoad+LoadStore before, no LoadStore after
   getRelease        release               LoadLoad+StoreStore before, no LoadLoad after
   getVolatile       sequential-consistent volatile read
   compareAndSet     sequential-consistent volatile CAS
```

`AtomicReference` and `AtomicLong` are now implemented in terms of `VarHandle`. `LongAdder` extends the idea to striped counters for write-hot counters (a far better choice than `AtomicLong` under contention).

## Comparison to the C++11 Memory Model

C++11 introduced `std::atomic` with five orderings: `memory_order_relaxed`, `memory_order_consume`, `memory_order_acquire`, `memory_order_release`, `memory_order_acq_rel`, `memory_order_seq_cst`. The mapping is roughly:

```
   Java                 C++ equivalent (approx)
   ────────────────────────────────────────────────────────
   plain field          — (no atomicity guarantee; behaves like data race)
   volatile field       std::atomic<T> with seq_cst
   synchronized method  std::mutex with std::lock_guard
   VarHandle.getAcquire std::atomic<T>::load(memory_order_acquire)
   VarHandle.setRelease std::atomic<T>::store(memory_order_release)
   VarHandle.getOpaque  memory_order_relaxed — with compiler-barrier semantics
```

The big conceptual differences:

1. **Default safety**: Java's plain field accesses participate in races with no defined semantics — but they don't *cause* UB; they just give you whatever value the hardware sees (including, for non-`long`/`double` reads, never a torn read). C++ makes data races *undefined behavior*; the compiler can assume they don't happen and aggressively optimize accordingly.
2. **Object publication**: Java's `final`-field rule has no direct C++ analogue; in C++ you must establish the synchronization yourself.
3. **`volatile` keyword collision**: C++'s `volatile` keyword is for device-memory access, *not* memory ordering — confusingly, the two languages use the same word for wildly different things.
4. **Sequential consistency at the top**: Java's `volatile` is SC; C++ only gives you SC if you ask for `memory_order_seq_cst`. The lighter orderings (`acquire/release`) are the *default* people should reach for in C++ — in Java you have to go through `VarHandle` to get them.

## Visibility Without Synchronization: the Warning Case

```java
class Done {
    private boolean ready = false;   // not volatile
    private int answer = 0;

    public void producer() {
        answer = 42;
        ready = true;
    }

    public void consumer() {
        // may loop forever on a JIT'd build — no happens-before edge,
        // JIT is free to hoist `ready` into a register once.
        while (!ready) { /* spin */ }
        System.out.println(answer);  // may print 0
    }
}
```

This is the classic JMM pop-quiz. Two legal behaviors of the JIT make this hang:

1. The JIT may hoist `ready` out of the loop and read it once.
2. The hardware may reorder the `answer = 42` write past the `ready = true` write (no `StoreStore` barrier was inserted), so even if `ready` becomes visible, `answer` is still `0`.

The fix: mark `ready` `volatile`, or use an `AtomicBoolean`, or wrap both reads/writes in `synchronized`.

## References

- JLS Chapter 17 — Memory Model (definitive text): <https://docs.oracle.com/javase/specs/jls/se22/html/jls-17.html>
- JSR 133 FAQ by Jeremy Manson and Bill Pugh: <https://www.cs.umd.edu/~pugh/java/memoryModel/jsr-133-faq.html>
- Jeremy Manson's blog (one of the JMM authors): <https://jeremymanson.blogspot.com/search?q=memory+model>
- Aleksey Shipilev — "JMM Pragmatics" (a deep, pragmatic primer, with code): <https://shipilev.net/blog/2016/close-encounters-of-jmm-kind/>
- "Java Concurrency in Practice" by Goetz et al., ch. 3 and 16 — the canonical practitioner's reference
- Doug Lea — `VarHandle` Javadoc and overview: <https://docs.oracle.com/en/java/javase/22/docs/api/java.base/java/lang/invoke/VarHandle.html>
- JEP 193 — Variable Handles (the `VarHandle` API): <https://openjdk.org/jeps/193>
- The C++11 memory model, N3337 §1.10 and §29 — see <https://en.cppreference.com/w/cpp/atomic/memory_order> for a working summary
- Hans-J. Boehm — "Reordering Constraints for Pthread-Style Locks" (background on acquire-release as a synchronization notion): <https://www.hboehm.info/c++mm/>
- Cliff Click — "Fixing the Java Memory Model" talk notes: <https://www.youtube.com/results?search_query=cliff+click+fixing+java+memory+model>
- Sarita Adve & Hans-J. Boehm — "Memory Models: A Case For Rethinking Parallel Languages and Hardware" (background paper): <https://www.hpl.hp.com/techreports/2009/HPL-2009-199.html>
