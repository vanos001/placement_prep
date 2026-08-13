# Go Interview Questions

## Language Fundamentals

### Q1: What are the zero values for different types?

| Type | Zero Value |
|------|-----------|
| `int`, `float64` | `0`, `0.0` |
| `bool` | `false` |
| `string` | `""` |
| `pointer`, `func`, `interface`, `slice`, `channel`, `map` | `nil` |
| `struct` | All fields are zero values |
| `array` | All elements are zero values |

### Q2: What is the difference between `var` and `:=`?

```go
var x int = 10      // Package or function level
var y = 10          // Type inferred
z := 10             // Short declaration, function level only

// := can declare multiple variables
a, b := 1, "hello"

// := requires at least one new variable on left
x, c := 2, "world" // x is reassigned, c is new
```

### Q3: Explain slices vs arrays.

```go
// Arrays: fixed size, value type
arr := [5]int{1, 2, 3, 4, 5}
arr2 := arr // Copy!

// Slices: dynamic, reference type
s := []int{1, 2, 3}
s2 := s // Shared underlying array!

// Slice internals
type slice struct {
    array unsafe.Pointer // Pointer to underlying array
    len   int            // Current length
    cap   int            // Capacity
}
```

### Q4: What happens when you append to a slice past capacity?

```go
s := make([]int, 2, 4) // len=2, cap=4
s = append(s, 1, 2)    // len=4, cap=4 (no reallocation)
s = append(s, 3)        // len=5, cap=8 (reallocated, doubled)

// If multiple slices share the same backing array,
// append may or may not modify the original
```

### Q5: How does `defer` work?

```go
func example() {
    fmt.Println("1")        // Executes first
    defer fmt.Println("2")  // Executes last (LIFO)
    defer fmt.Println("3")  // Executes before "2"
    fmt.Println("4")        // Executes second
}
// Output: 1, 4, 3, 2

// Arguments are evaluated immediately
x := 1
defer fmt.Println(x) // Prints 1, not 2
x = 2
```

## Concurrency

### Q6: Goroutine vs thread?

| Aspect | Goroutine | Thread |
|--------|-----------|--------|
| Stack | ~2KB (dynamic) | 1-8MB (fixed) |
| Creation | ~0.3μs | ~30μs |
| Context switch | ~0.2μs | ~1-2μs |
| Scheduling | User-space (Go runtime) | Kernel |
| Communication | Channels | Shared memory |

### Q7: How to implement a worker pool?

```go
func workerPool(jobs <-chan Job, numWorkers int) <-chan Result {
    results := make(chan Result)
    var wg sync.WaitGroup
    
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func() {
            defer wg.Done()
            for job := range jobs {
                results <- process(job)
            }
        }()
    }
    
    go func() {
        wg.Wait()
        close(results)
    }()
    
    return results
}
```

### Q8: How to gracefully shutdown a goroutine?

```go
func worker(ctx context.Context) {
    for {
        select {
        case <-ctx.Done():
            fmt.Println("Shutting down:", ctx.Err())
            return
        default:
            doWork()
        }
    }
}

ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()
go worker(ctx)
```

### Q9: What is a channel direction?

```go
func producer(ch chan<- int) { // Send-only
    ch <- 42
}

func consumer(ch <-chan int) { // Receive-only
    v := <-ch
}

// Bidirectional channels can be converted to directional
// but not the other way around
```

### Q10: Explain the `select` statement behavior.

```go
select {
case v := <-ch1:     // Random selection if multiple ready
    handle(v)
case ch2 <- 42:
    // Sent successfully
case <-time.After(time.Second):
    // Timeout
default:
    // Non-blocking: executes if no channel is ready
}
```

## Interfaces and Types

### Q11: How do interfaces work in Go?

```go
// Interface: set of method signatures
type Reader interface {
    Read(p []byte) (n int, err error)
}

// Implicit satisfaction: any type with Read method satisfies Reader
type File struct{}
func (f *File) Read(p []byte) (int, error) { /* ... */ }

// Empty interface: satisfied by any type
var anything interface{} = 42

// Type assertion
v, ok := anything.(int)
if ok {
    fmt.Println(v) // 42
}

// Type switch
switch v := anything.(type) {
case int:
    fmt.Println("int:", v)
case string:
    fmt.Println("string:", v)
}
```

### Q12: What is the difference between value and pointer receivers?

```go
type Counter struct { n int }

// Value receiver: operates on a copy
func (c Counter) Value() int { return c.n }

// Pointer receiver: operates on the original
func (c *Counter) Increment() { c.n++ }

// Rule: if any method has pointer receiver, all should
// Interface satisfaction: *T satisfies interface with value methods
// but T does NOT satisfy interface with pointer methods
```

### Q13: What are Go generics (Go 1.18+)?

```go
// Type parameters
func Map[T any, U any](s []T, f func(T) U) []U {
    result := make([]U, len(s))
    for i, v := range s {
        result[i] = f(v)
    }
    return result
}

// Type constraints
type Number interface {
    ~int | ~float64
}

func Sum[T Number](nums []T) T {
    var total T
    for _, n := range nums {
        total += n
    }
    return total
}
```

## Error Handling

### Q14: How does Go handle errors?

```go
// Errors are values
type error interface {
    Error() string
}

// Custom errors
type ValidationError struct {
    Field   string
    Message string
}
func (e *ValidationError) Error() string {
    return fmt.Sprintf("%s: %s", e.Field, e.Message)
}

// Error wrapping (Go 1.13+)
if err != nil {
    return fmt.Errorf("failed to open file: %w", err)
}

// Sentinel errors
var ErrNotFound = errors.New("not found")

// errors.Is and errors.As
if errors.Is(err, ErrNotFound) { /* ... */ }
var ve *ValidationError
if errors.As(err, &ve) { /* ... */ }
```

### Q15: panic vs error?

| Use Errors | Use panic |
|------------|-----------|
| Expected failures | Unrecoverable errors |
| User input validation | Programmer errors (bugs) |
| Network/IO failures | Init failures |
| Business logic errors | Out of memory |

```go
// recover() catches panics
func safeDiv(a, b int) (result int, err error) {
    defer func() {
        if r := recover(); r != nil {
            err = fmt.Errorf("panic: %v", r)
        }
    }()
    return a / b, nil
}
```

## Performance

### Q16: How to reduce GC pressure?

1. **Reuse objects** — `sync.Pool`
2. **Preallocate slices** — `make([]T, 0, capacity)`
3. **Avoid allocations in hot paths** — Stack allocation when possible
4. **Use value types** — Avoid unnecessary pointer indirection
5. **Reduce pointer density** — GC must scan pointers

### Q17: How to profile Go applications?

```bash
# CPU profiling
go test -cpuprofile cpu.prof -bench .
go tool pprof cpu.prof

# Memory profiling
go test -memprofile mem.prof -bench .
go tool pprof mem.prof

# HTTP profiling
import _ "net/http/pprof"
go http.ListenAndServe(":6060", nil)
```

### Q18: What is escape analysis?

```go
// The compiler decides if a variable lives on stack or heap
func foo() *int {
    x := 42    // x escapes: returned pointer
    return &x  // heap allocated
}

func bar() int {
    x := 42    // x doesn't escape
    return x   // stack allocated
}

// Check: go build -gcflags="-m" main.go
```

## System Design

### Q19: How to implement a rate limiter in Go?

```go
// Token bucket
type RateLimiter struct {
    tokens   chan struct{}
    ticker   *time.Ticker
}

func NewRateLimiter(rate int, burst int) *RateLimiter {
    rl := &RateLimiter{
        tokens: make(chan struct{}, burst),
        ticker: time.NewTicker(time.Second / time.Duration(rate)),
    }
    // Fill initial burst
    for i := 0; i < burst; i++ {
        rl.tokens <- struct{}{}
    }
    go rl.refill()
    return rl
}

func (rl *RateLimiter) refill() {
    for range rl.ticker.C {
        select {
        case rl.tokens <- struct{}{}:
        default: // Bucket full
        }
    }
}

func (rl *RateLimiter) Allow() bool {
    select {
    case <-rl.tokens:
        return true
    default:
        return false
    }
}
```

### Q20: How to implement graceful shutdown?

```go
func main() {
    srv := &http.Server{Addr: ":8080"}
    
    // Channel for shutdown signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    
    // Start server
    go func() {
        if err := srv.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatal(err)
        }
    }()
    
    <-quit // Wait for signal
    log.Println("Shutting down...")
    
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatal(err)
    }
    log.Println("Server stopped")
}
```

## Related Topics

- [Go Scheduler](./scheduler.md) — GMP model, goroutine scheduling
- [Go Channels](./channels.md) — Channel patterns and semantics
- [Go Memory Model](./memory-model.md) — Happens-before, data races
- [Concurrency](../../concurrency/) — General concurrency patterns
- [System Design](../../interview/system-design/) — Go-based system design
