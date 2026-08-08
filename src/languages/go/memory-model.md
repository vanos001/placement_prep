# Go Memory Model

## Overview

Go's memory model defines the conditions under which reads of a variable in one goroutine are guaranteed to observe writes to the same variable in another goroutine. Understanding this is crucial for writing correct concurrent programs.

## Happens-Before Relationships

An event **e1 happens-before** event **e2** if e1 is ordered before e2 and e1's effects are visible to e2.

### Guaranteed Happens-Before

1. **Within a goroutine** — Statements execute in program order
2. **Channel operations** — Send happens-before corresponding receive completes
3. **Mutex operations** — `Unlock` happens-before subsequent `Lock`
4. **sync.Once** — `Do` call happens-before `f()` returns
5. **sync.WaitGroup** — `Wait` returns after all `Done` calls
6. **sync/atomic** — Atomic operations provide sequential consistency

## Channel Synchronization

```go
var data int
var done = make(chan bool)

// Goroutine 1
go func() {
    data = 42          // (1) Write
    done <- true       // (2) Send
}()

// Goroutine 2
<-done                 // (3) Receive — happens after (2)
fmt.Println(data)      // (4) Guaranteed to see 42
```

The send on `done` happens-before the receive, establishing a happens-before from (1) to (4).

## Mutex Synchronization

```go
var mu sync.Mutex
var balance int

// Goroutine 1
mu.Lock()
balance = 100          // (1) Write
mu.Unlock()            // (2) Unlock

// Goroutine 2
mu.Lock()              // (3) Lock — happens after (2)
fmt.Println(balance)   // (4) Guaranteed to see 100
mu.Unlock()
```

## Data Races

A **data race** occurs when two goroutines access the same variable concurrently and at least one is a write.

```go
// DATA RACE!
var counter int

for i := 0; i < 1000; i++ {
    go func() {
        counter++ // Read + Write without synchronization
    }()
}
```

### Detecting Data Races

```bash
go run -race main.go
go test -race ./...
```

The race detector uses ThreadSanitizer and adds ~10x overhead but catches races at runtime.

### Fixing Data Races

```go
// Fix 1: Mutex
var mu sync.Mutex
var counter int

func increment() {
    mu.Lock()
    defer mu.Unlock()
    counter++
}

// Fix 2: Atomic
var counter int64

func increment() {
    atomic.AddInt64(&counter, 1)
}

// Fix 3: Channel
var counter int64
var ops = make(chan struct{})

// Single goroutine owns the counter
go func() {
    for range ops {
        counter++
    }
}()
```

## sync Package

| Primitive | Use Case | Performance |
|-----------|----------|-------------|
| `Mutex` | Mutual exclusion | Good for short critical sections |
| `RWMutex` | Multiple readers, single writer | Better for read-heavy workloads |
| `WaitGroup` | Wait for goroutines to finish | Lightweight |
| `Once` | One-time initialization | Very fast after first call |
| `Cond` | Wait for condition | Complex, rarely needed |
| `Map` | Concurrent map | Good for read-heavy, stable key sets |
| `Pool` | Object reuse | Reduces GC pressure |
| `atomic` | Low-level atomic ops | Fastest |

### sync.Once

```go
var once sync.Once
var instance *Database

func GetDatabase() *Database {
    once.Do(func() {
        instance = connectToDatabase()
    })
    return instance
}
```

### sync.Pool

```go
var bufPool = sync.Pool{
    New: func() interface{} {
        return new(bytes.Buffer)
    },
}

func process(data []byte) {
    buf := bufPool.Get().(*bytes.Buffer)
    defer bufPool.Put(buf)
    buf.Reset()
    buf.Write(data)
    // use buf...
}
```

## Interview Questions

### Q: What is a data race?

**A:** When two goroutines access the same variable concurrently, at least one is a write, and there's no synchronization. The Go runtime's race detector can find these. Data races lead to undefined behavior.

### Q: Mutex vs Channel for synchronization?

**A:** Use mutexes to protect shared state (simple read/write). Use channels to communicate between goroutines (transfer ownership, coordinate). Channels are higher-level and often clearer, but mutexes are faster for simple cases.

### Q: What does the race detector do?

**A:** It instruments code at runtime to detect unsynchronized concurrent memory access. It uses happens-before analysis. It adds ~10x slowdown and ~5-10x memory overhead. Enable with `-race` flag.

### Q: How does sync.Pool reduce GC pressure?

**A:** Objects in Pool are reused instead of allocated fresh each time. The pool is cleared during GC, but between GC cycles, objects are reused. This reduces allocation rate and thus GC work. Good for temporary buffers.

## Related Topics

- [Go Channels](./channels.md) — Channel-based synchronization
- [Go Scheduler](./scheduler.md) — Goroutine scheduling
- [Concurrency](../../concurrency/) — General concurrency concepts
- [OS Synchronization](../../os/processes/ipc.md) — OS-level synchronization
