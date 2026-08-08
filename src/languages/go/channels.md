# Go Channels

## Overview

Channels are Go's primary mechanism for communication between goroutines. They embody Go's concurrency philosophy: "Don't communicate by sharing memory; share memory by communicating."

## Channel Types

### Unbuffered Channels

```go
ch := make(chan int) // Capacity: 0

// Synchronous: sender blocks until receiver is ready
go func() { ch <- 42 }() // Blocks until someone reads
v := <-ch                 // Blocks until someone sends
```

### Buffered Channels

```go
ch := make(chan int, 5) // Capacity: 5

// Asynchronous: blocks only when full/empty
ch <- 1  // Doesn't block (buffer has space)
ch <- 2
ch <- 3
ch <- 4
ch <- 5
ch <- 6  // BLOCKS! Buffer is full
```

## Channel Operations

| Operation | Syntax | Behavior |
|-----------|--------|----------|
| **Send** | `ch <- v` | Blocks if full |
| **Receive** | `v := <-ch` | Blocks if empty |
| **Close** | `close(ch)` | No more sends |
| **Select** | `select { case... }` | Multiplex channels |

## Select Statement

```go
select {
case msg := <-ch1:
    fmt.Println("Received from ch1:", msg)
case ch2 <- 42:
    fmt.Println("Sent to ch2")
case <-time.After(time.Second):
    fmt.Println("Timeout after 1 second")
default:
    fmt.Println("No channel ready (non-blocking)")
}
```

### Select Rules

1. **Random selection** — If multiple cases are ready, one is chosen randomly
2. **Blocking** — Without `default`, select blocks until one case is ready
3. **Nil channels** — Cases on nil channels are never selected
4. **Empty select** — `select {}` blocks forever

## Channel Patterns

### Fan-out / Fan-in

```go
func fanOut(input <-chan int, workers int) []<-chan int {
    channels := make([]<-chan int, workers)
    for i := 0; i < workers; i++ {
        channels[i] = worker(input)
    }
    return channels
}

func fanIn(channels ...<-chan int) <-chan int {
    var wg sync.WaitGroup
    merged := make(chan int)
    for _, ch := range channels {
        wg.Add(1)
        go func(c <-chan int) {
            defer wg.Done()
            for v := range c {
                merged <- v
            }
        }(ch)
    }
    go func() { wg.Wait(); close(merged) }()
    return merged
}
```

### Pipeline

```go
func pipeline() {
    nums := generator(1, 2, 3, 4, 5)
    squared := square(nums)
    doubled := double(squared)
    for v := range doubled {
        fmt.Println(v) // 4, 16, 36, 64, 100
    }
}

func generator(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        for _, n := range nums {
            out <- n
        }
        close(out)
    }()
    return out
}

func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        for n := range in {
            out <- n * n
        }
        close(out)
    }()
    return out
}
```

### Worker Pool

```go
func workerPool(jobs <-chan int, results chan<- int, workers int) {
    var wg sync.WaitGroup
    for i := 0; i < workers; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for job := range jobs {
                results <- process(job)
            }
        }(i)
    }
    go func() { wg.Wait(); close(results) }()
}
```

## Advanced Channel Patterns

### Range Over Channels

```go
func producer(ch chan<- int) {
    for i := 0; i < 5; i++ {
        ch <- i
    }
    close(ch)  // MUST close for range to terminate
}

func main() {
    ch := make(chan int)
    go producer(ch)

    // range automatically stops when channel is closed
    for v := range ch {
        fmt.Println(v)  // 0, 1, 2, 3, 4
    }
}
```

### Done / Quit Pattern

```go
func worker(done <-chan struct{}, jobs <-chan int) {
    for {
        select {
        case <-done:
            fmt.Println("Worker shutting down")
            return
        case job, ok := <-jobs:
            if !ok {
                return  // Channel closed
            }
            fmt.Printf("Processing job %d\n", job)
        }
    }
}

func main() {
    jobs := make(chan int, 10)
    done := make(chan struct{})

    go worker(done, jobs)

    // Send some jobs
    for i := 0; i < 5; i++ {
        jobs <- i
    }

    // Signal worker to stop
    close(done)
}
```

### Timeout Pattern

```go
func fetchWithTimeout(url string, timeout time.Duration) (string, error) {
    result := make(chan string, 1)
    errCh := make(chan error, 1)

    go func() {
        resp, err := http.Get(url)
        if err != nil {
            errCh <- err
            return
        }
        defer resp.Body.Close()
        body, _ := io.ReadAll(resp.Body)
        result <- string(body)
    }()

    select {
    case body := <-result:
        return body, nil
    case err := <-errCh:
        return "", err
    case <-time.After(timeout):
        return "", fmt.Errorf("timeout after %v", timeout)
    }
}
```

### Or-Done Channel

```go
// orDone wraps a channel to allow cancellation
func orDone(done <-chan struct{}, c <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for {
            select {
            case <-done:
                return
            case v, ok := <-c:
                if !ok {
                    return
                }
                select {
                case out <- v:
                case <-done:
                    return
                }
            }
        }
    }()
    return out
}
```

### Tee Channel

```go
// tee splits one channel into two
func tee(done <-chan struct{}, in <-chan int) (<-chan int, <-chan int) {
    out1 := make(chan int)
    out2 := make(chan int)
    go func() {
        defer close(out1)
        defer close(out2)
        for val := range orDone(done, in) {
            // Send to both channels
n            var out1, out2 = out1, out2
            for i := 0; i < 2; i++ {
                select {
                case <-done:
                    return
                case out1 <- val:
                    out1 = nil  // Sent to out1
                case out2 <- val:
                    out2 = nil  // Sent to out2
                }
            }
        }
    }()
    return out1, out2
}
```

### Bridge Channel (Channel of Channels)

```go
// bridge flattens a channel of channels into a single channel
func bridge(done <-chan struct{}, chanStream <-chan <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for stream := range chanStream {
            for val := range orDone(done, stream) {
                select {
                case out <- val:
                case <-done:
                    return
                }
            }
        }
    }()
    return out
}
```

## Common Pitfalls

### 1. Sending on Closed Channel

```go
ch := make(chan int)
close(ch)
ch <- 1 // PANIC: send on closed channel
```

### 2. Receiving from Closed Channel

```go
ch := make(chan int, 1)
ch <- 42
close(ch)
v := <-ch  // Returns 42 (remaining value)
v = <-ch   // Returns 0 (zero value, no panic)
```

### 3. Deadlock

```go
ch := make(chan int)
ch <- 1 // DEADLOCK: no goroutine to receive
```

### 4. Goroutine Leak

```go
func leaky() <-chan int {
    ch := make(chan int)
    go func() {
        ch <- expensiveOperation()
        // If nobody reads ch, goroutine leaks
    }()
    return ch
}
```

## Interview Questions

### Q: Buffered vs unbuffered channels?

**A:** Unbuffered channels are synchronous — sender blocks until receiver is ready (and vice versa). Buffered channels are asynchronous up to their capacity — sender blocks only when buffer is full, receiver blocks only when buffer is empty.

### Q: What happens when you close a channel?

**A:** All blocked receivers get the zero value. Remaining values can still be received. Sending on a closed channel panics. Closing an already-closed channel panics. Range loops over a closed channel terminate.

### Q: How to detect a closed channel?

```go
v, ok := <-ch
if !ok {
    // Channel is closed and empty
}
```

### Q: When to use channels vs mutexes?

| Use Channels | Use Mutexes |
|--------------|-------------|
| Transfer ownership of data | Protect shared state |
| Coordinate goroutines | Simple read/write protection |
| Pipeline patterns | Counter, cache |
| Signaling (done, quit) | Performance-critical sections |

## References

- [Go Blog — Share Memory by Communicating](https://go.dev/blog/codelab-share)
- [Effective Go — Channels](https://go.dev/doc/effective_go#channels)
- [Go Concurrency Patterns — Rob Pike](https://www.youtube.com/watch?v=f6kdp27TYZs)
- [Advanced Go Concurrency Patterns — Sameer Ajmani](https://www.youtube.com/watch?v=QDDwwePbDtw)

## Related Topics

- [Go Scheduler](./scheduler.md) — How goroutines are scheduled
- [Go Memory Model](./memory-model.md) — Channel synchronization guarantees
- [Concurrency Patterns](../../concurrency/) — General patterns
