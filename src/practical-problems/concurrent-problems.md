# Concurrent Programming Problems

## Producer-Consumer Pattern

### Problem
Producers generate data and put it in a shared buffer. Consumers take data from the buffer and process it. The buffer has a fixed capacity.

### Python Implementation (threading)

```python
import threading
import queue
import time
import random

class ProducerConsumer:
    def __init__(self, buffer_size=10):
        self.buffer = queue.Queue(maxsize=buffer_size)
        self.running = True
    
    def producer(self, producer_id):
        while self.running:
            item = random.randint(1, 100)
            self.buffer.put(item)  # Blocks if full
            print(f"Producer {producer_id} produced: {item}")
            time.sleep(random.uniform(0.1, 0.5))
    
    def consumer(self, consumer_id):
        while self.running:
            item = self.buffer.get()  # Blocks if empty
            print(f"Consumer {consumer_id} consumed: {item}")
            self.buffer.task_done()
            time.sleep(random.uniform(0.1, 0.3))
    
    def run(self, num_producers=2, num_consumers=3):
        threads = []
        for i in range(num_producers):
            t = threading.Thread(target=self.producer, args=(i,))
            t.start()
            threads.append(t)
        for i in range(num_consumers):
            t = threading.Thread(target=self.consumer, args=(i,))
            t.start()
            threads.append(t)
        return threads
```

### Java Implementation

```java
import java.util.concurrent.*;

public class ProducerConsumer {
    private final BlockingQueue<Integer> queue;
    
    public ProducerConsumer(int capacity) {
        this.queue = new ArrayBlockingQueue<>(capacity);
    }
    
    public void producer(int id) throws InterruptedException {
        while (true) {
            int item = ThreadLocalRandom.current().nextInt(100);
            queue.put(item);  // Blocks if full
            System.out.printf("Producer %d produced: %d%n", id, item);
        }
    }
    
    public void consumer(int id) throws InterruptedException {
        while (true) {
            int item = queue.take();  // Blocks if empty
            System.out.printf("Consumer %d consumed: %d%n", id, item);
        }
    }
}
```

## Thread Pool

### Problem
Execute tasks concurrently with a fixed number of worker threads.

### Python Implementation

```python
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor

# Simple thread pool
class SimpleThreadPool:
    def __init__(self, num_threads):
        self.tasks = Queue()
        self.threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=self._worker, daemon=True)
            t.start()
            self.threads.append(t)
    
    def _worker(self):
        while True:
            func, args, kwargs = self.tasks.get()
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"Task failed: {e}")
            finally:
                self.tasks.task_done()
    
    def submit(self, func, *args, **kwargs):
        self.tasks.put((func, args, kwargs))
    
    def wait(self):
        self.tasks.join()

# Using stdlib
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(process, item) for item in items]
    results = [f.result() for f in futures]
```

## Connection Pool

### Problem
Manage a pool of reusable database connections to avoid the overhead of creating/destroying connections.

### Python Implementation

```python
import threading
import time
from queue import Queue, Empty

class Connection:
    def __init__(self, conn_id):
        self.conn_id = conn_id
        self.in_use = False
        self.created_at = time.time()
    
    def execute(self, query):
        # Simulate query execution
        time.sleep(0.01)
        return f"Result from conn {self.conn_id}: {query}"

class ConnectionPool:
    def __init__(self, min_size=2, max_size=10, max_idle_time=300):
        self.min_size = min_size
        self.max_size = max_size
        self.max_idle_time = max_idle_time
        self.pool = Queue(maxsize=max_size)
        self.lock = threading.Lock()
        self.current_size = 0
        
        # Create minimum connections
        for i in range(min_size):
            self.pool.put(Connection(i))
            self.current_size += 1
    
    def get_connection(self, timeout=5):
        try:
            conn = self.pool.get(timeout=timeout)
            conn.in_use = True
            return conn
        except Empty:
            # Create new connection if under max
            with self.lock:
                if self.current_size < self.max_size:
                    conn = Connection(self.current_size)
                    self.current_size += 1
                    conn.in_use = True
                    return conn
            raise TimeoutError("No connections available")
    
    def release_connection(self, conn):
        conn.in_use = False
        self.pool.put(conn)
    
    def __enter__(self):
        self.conn = self.get_connection()
        return self.conn
    
    def __exit__(self, *args):
        self.release_connection(self.conn)
```

## Worker Pool

### Problem
Process a stream of tasks with a fixed number of workers, collecting results.

### Go Implementation

```go
func workerPool(numWorkers int, jobs <-chan Job, results chan<- Result) {
    var wg sync.WaitGroup
    
    for i := 0; i < numWorkers; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()
            for job := range jobs {
                result := process(job)
                results <- result
            }
        }(i)
    }
    
    wg.Wait()
    close(results)
}
```

## Interview Questions

**Q: What's the difference between a thread pool and a worker pool?**
A: Thread pool manages OS threads for reuse (avoids creation overhead). Worker pool is a pattern where workers process tasks from a queue. A thread pool often implements a worker pool, but worker pools can also use processes, coroutines, etc.

**Q: How do you handle backpressure in producer-consumer?**
A: (1) Blocking queue (producer blocks when full), (2) drop oldest/newest (lossy), (3) bounded buffer with timeout, (4) signal producer to slow down, (5) add more consumers, (6) spill to disk when buffer is full.

**Q: How do you prevent deadlocks in concurrent code?**
A: (1) Lock ordering — always acquire locks in the same order, (2) use timeouts on lock acquisition, (3) use trylock and back off on failure, (4) minimize lock scope, (5) prefer lock-free structures, (6) use deadlock detection tools.

## References

- [Python threading](https://docs.python.org/3/library/threading.html)
- [Python concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)
- [Java BlockingQueue](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/BlockingQueue.html)
