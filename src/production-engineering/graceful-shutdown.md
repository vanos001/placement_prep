# Graceful Shutdown

When a production service instance needs to stop—whether due to a deployment, scaling down, or maintenance—it should not simply terminate abruptly. A graceful shutdown ensures that in-flight requests complete, connections are properly closed, resources are released, and dependent services are notified. This document covers the mechanisms and patterns for implementing graceful shutdown in production systems.

## Why Graceful Shutdown Matters

Abrupt termination of a service instance causes several problems:

- **Dropped requests**: Clients receive connection errors or incomplete responses
- **Data corruption**: In-flight writes may be partially committed, leaving data in an inconsistent state
- **Resource leaks**: Database connections, file handles, and temporary files may not be cleaned up
- **Cascading failures**: Dependent services may not handle the sudden loss of a backend gracefully
- **Poor user experience**: Users see errors during routine deployments

A well-implemented graceful shutdown eliminates these issues and enables zero-downtime deployments.

## Signals and Process Lifecycle

### SIGTERM vs SIGKILL
When a process needs to stop, the operating system sends signals:

- **SIGTERM (Signal 15)**: A polite request to terminate. The process can catch this signal, perform cleanup, and exit gracefully. This is the default signal sent by `kill` and container orchestrators.
- **SIGKILL (Signal 9)**: A forceful termination that the process cannot catch or ignore. The kernel immediately reclaims all resources. Used as a last resort when a process refuses to exit after SIGTERM.
- **SIGINT (Signal 2)**: Sent when the user presses Ctrl+C. Similar to SIGTERM but typically used for interactive processes.

### The Shutdown Sequence
A proper graceful shutdown follows this sequence:

```
1. Receive SIGTERM
2. Mark instance as "shutting down" (remove from service discovery/load balancer)
3. Stop accepting new connections/requests
4. Wait for in-flight requests to complete (with timeout)
5. Close external connections (database pools, message consumers, etc.)
6. Flush pending data (logs, metrics, buffered writes)
7. Release resources (file handles, locks, temporary files)
8. Exit with code 0
```

### Implementation in Go
```go
func main() {
    server := &http.Server{Addr: ":8080", Handler: router}
    
    // Start server in goroutine
    go func() {
        if err := server.ListenAndServe(); err != http.ErrServerClosed {
            log.Fatalf("Server error: %v", err)
        }
    }()
    
    // Wait for interrupt signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGTERM, syscall.SIGINT)
    <-quit
    
    log.Println("Shutting down gracefully...")
    
    // Give outstanding requests 30 seconds to complete
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := server.Shutdown(ctx); err != nil {
        log.Fatalf("Forced shutdown: %v", err)
    }
    
    // Close database connections
    db.Close()
    
    // Flush logs
    log.Sync()
    
    log.Println("Server stopped")
}
```

### Implementation in Python
```python
import signal
import asyncio
from aiohttp import web

class GracefulShutdown:
    def __init__(self):
        self.shutting_down = False
        self.active_requests = 0
    
    def handle_signal(self, sig):
        self.shutting_down = True
        signal_name = signal.Signals(sig).name
        print(f"Received {signal_name}, shutting down gracefully...")

shutdown_manager = GracefulShutdown()

async def middleware(app, handler):
    async def middleware_handler(request):
        if shutdown_manager.shutting_down:
            return web.Response(status=503, text="Service is shutting down")
        shutdown_manager.active_requests += 1
        try:
            response = await handler(request)
            return response
        finally:
            shutdown_manager.active_requests -= 1
    return middleware_handler

async def on_shutdown(app):
    # Wait for active requests to complete
    timeout = 30
    start = asyncio.get_event_loop().time()
    while shutdown_manager.active_requests > 0:
        if asyncio.get_event_loop().time() - start > timeout:
            print(f"Timeout: {shutdown_manager.active_requests} requests still active")
            break
        await asyncio.sleep(0.1)
    
    # Close database pools, etc.
    await app['db'].close()

app = web.Application(middlewares=[middleware])
app.on_shutdown.append(on_shutdown)

# Register signal handlers
loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, shutdown_manager.handle_signal, sig)
```

### Implementation in Java/Spring
```java
@Component
public class GracefulShutdown implements ApplicationListener<ContextClosedEvent> {
    
    private static final Logger log = LoggerFactory.getLogger(GracefulShutdown.class);
    
    @Value("${shutdown.timeout.seconds:30}")
    private int shutdownTimeout;
    
    @Override
    public void onApplicationEvent(ContextClosedEvent event) {
        log.info("Graceful shutdown initiated");
        
        // Tomcat's connector stops accepting new requests
        // Active requests continue until they complete or timeout
        
        // Custom cleanup
        closeDatabaseConnections();
        flushMetrics();
        deregisterFromServiceDiscovery();
        
        log.info("Graceful shutdown complete");
    }
}
```

## Connection Draining

### What is Connection Draining?
Connection draining (also called connection draining or slow start) is the process of gracefully removing a server from a load balancer's rotation while allowing existing connections to complete. When a server is marked for draining:

1. The load balancer stops routing new requests to the server
2. Existing connections are allowed to complete naturally
3. After a timeout period, remaining connections are forcibly closed
4. The server is removed from the pool

### Load Balancer Configuration

**AWS ALB/ELB:**
```
Deregistration Delay: 300 seconds (default)
# The load balancer waits up to 300 seconds for in-flight requests
# to complete before deregistering the target
```

**Nginx upstream draining:**
```nginx
upstream backend {
    server 10.0.0.1:8080;
    server 10.0.0.2:8080;
    server 10.0.0.3:8080 down;  # Mark as draining
}
```

**Kubernetes:**
```yaml
spec:
  terminationGracePeriodSeconds: 60  # Time allowed for graceful shutdown
  containers:
  - name: app
    lifecycle:
      preStop:
        exec:
          command: ["/bin/sh", "-c", "sleep 5"]
          # Delay before SIGTERM to allow load balancer to deregister
```

### The Pre-Stop Hook Pattern
In Kubernetes, there is a race condition between the pod receiving SIGTERM and the load balancer removing the pod from its routing table. The pre-stop hook solves this:

```
Timeline:
1. Kubernetes sends preStop hook → Pod sleeps for 5 seconds
2. During those 5 seconds, load balancer removes pod from rotation
3. Kubernetes sends SIGTERM → Pod begins graceful shutdown
4. Pod finishes in-flight requests and exits
5. If pod hasn't exited after terminationGracePeriodSeconds, SIGKILL
```

## Health Checks: Liveness vs Readiness

### Liveness Probes
A liveness probe determines if a process is alive and functioning. If the liveness probe fails, the orchestrator restarts the container. Liveness probes should check:

- The process is running and not deadlocked
- Critical internal threads are responsive
- The application can make progress

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 5
```

```python
@app.route('/health/live')
def liveness():
    """Check if the process is alive and not deadlocked."""
    # Simple check: can we respond to HTTP requests?
    # Check if critical background threads are running
    if not scheduler_thread.is_alive():
        return jsonify(status="dead"), 500
    return jsonify(status="alive"), 200
```

### Readiness Probes
A readiness probe determines if a process is ready to accept traffic. If the readiness probe fails, the orchestrator removes the pod from the service's endpoints (stops routing traffic to it) but does NOT restart the container. Readiness probes should check:

- Database connections are established and healthy
- Required caches are warmed
- Dependent services are reachable
- The application has finished initialization

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3
  timeoutSeconds: 3
```

```python
@app.route('/health/ready')
def readiness():
    """Check if the process is ready to serve traffic."""
    checks = {
        'database': check_database_connection(),
        'cache': check_redis_connection(),
        'external_api': check_dependency_health(),
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return jsonify(status="ready" if all_healthy else "not_ready", checks=checks), status_code
```

### Key Differences

| Aspect | Liveness | Readiness |
|--------|----------|-----------|
| **Purpose** | Is the process alive? | Is the process ready for traffic? |
| **Failure action** | Restart the container | Remove from load balancer |
| **When to fail** | Deadlock, crash loop, unresponsive | Missing dependencies, warming up, overloaded |
| **Recovery** | Container restart | Automatic re-addition when probe passes |
| **Frequency** | Less frequent (every 10-30s) | More frequent (every 5-10s) |

### Startup Probes
For applications with long startup times, use a startup probe to prevent the liveness probe from killing the container before it finishes initializing:

```yaml
startupProbe:
  httpGet:
    path: /health/started
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
  # Gives the app up to 300 seconds to start
```

## Graceful Shutdown in Message Consumers

Message consumers (Kafka, RabbitMQ, SQS) require special handling during shutdown:

### Kafka Consumer
```python
class GracefulKafkaConsumer:
    def __init__(self, topic, handler):
        self.consumer = KafkaConsumer(topic)
        self.handler = handler
        self.running = True
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, sig, frame):
        self.running = False
    
    def consume(self):
        while self.running:
            messages = self.consumer.poll(timeout_ms=1000)
            for topic, partition_messages in messages.items():
                for message in partition_messages:
                    self.handler(message)
                    self.consumer.commit()
        
        # Graceful close: commit offsets and leave group
        self.consumer.close()
```

### Key Considerations for Message Consumers
- Stop polling for new messages immediately on SIGTERM
- Finish processing the current message before exiting
- Commit offsets for processed messages
- Use consumer group rebalancing timeouts appropriately
- Consider the message visibility timeout (for SQS-like systems)

## Common Pitfalls

### 1. Ignoring SIGTERM
Some applications only handle SIGINT (Ctrl+C) and ignore SIGTERM. Container orchestrators send SIGTERM, so your application must handle it.

### 2. No Shutdown Timeout
Always set a maximum timeout for graceful shutdown. If a request takes too long or a resource cannot be released, the process must eventually exit to avoid hanging indefinitely.

### 3. Shared Database Connections
During shutdown, in-flight requests may try to use database connections that are being closed. Ensure connection pools drain properly and connections are not closed prematurely.

### 4. Load Balancer Deregistration Delay
There is always a delay between when a process starts shutting down and when the load balancer stops sending traffic. Use pre-stop hooks or deregistration delays to bridge this gap.

### 5. Cascading Shutdowns
In a microservices architecture, if service A calls service B, and both are shutting down simultaneously, you can get cascading timeouts. Implement circuit breakers and set appropriate timeouts.

## Summary

Graceful shutdown is not optional in production systems. It requires:

1. **Signal handling**: Catch SIGTERM and initiate shutdown sequence
2. **Traffic draining**: Stop accepting new requests, complete in-flight ones
3. **Connection draining**: Allow load balancers to deregister the instance
4. **Health check design**: Use liveness probes for restarts, readiness probes for traffic management
5. **Resource cleanup**: Close connections, flush data, release locks
6. **Timeout enforcement**: Never wait forever; use a hard timeout and exit

Implementing these patterns ensures that deployments, scaling events, and maintenance operations happen without impacting users.
