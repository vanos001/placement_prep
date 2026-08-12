# System Utilities

## Rate Limiter Implementation

### Token Bucket (Python)

```python
import time
import threading

class TokenBucket:
    def __init__(self, rate, capacity):
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max tokens
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()
    
    def allow(self):
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, 
                            self.tokens + elapsed * self.rate)
            self.last_refill = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False

# Usage
limiter = TokenBucket(rate=10, capacity=20)  # 10/sec, burst of 20
if limiter.allow():
    process_request()
else:
    return_429()
```

## Circuit Breaker

```python
import time
from enum import Enum

class State(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = State.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        if self.state == State.OPEN:
            if self._should_try():
                self.state = State.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self.failure_count = 0
        self.state = State.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = State.OPEN
    
    def _should_try(self):
        return (time.monotonic() - self.last_failure_time 
                > self.recovery_timeout)
```

## Retry with Exponential Backoff

```python
import time
import random

def retry(max_retries=3, base_delay=1, max_delay=60, 
          exceptions=(Exception,)):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    time.sleep(delay + jitter)
            return wrapper
    return decorator

@retry(max_retries=3, base_delay=1, exceptions=(ConnectionError,))
def fetch_data(url):
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()
```

## Config Loader

```python
import os
import json
import yaml
from pathlib import Path

class Config:
    def __init__(self, defaults=None):
        self._data = defaults or {}
        self._sources = []
    
    def load_file(self, filepath):
        path = Path(filepath)
        if path.suffix == '.json':
            with open(path) as f:
                self._data.update(json.load(f))
        elif path.suffix in ('.yml', '.yaml'):
            with open(path) as f:
                self._data.update(yaml.safe_load(f))
        self._sources.append(str(path))
    
    def load_env(self, prefix=''):
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                self._data[config_key] = value
    
    def get(self, key, default=None):
        keys = key.split('.')
        value = self._data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value
    
    def __getitem__(self, key):
        return self.get(key)

# Usage
config = Config({'server': {'port': 8080, 'host': 'localhost'}})
config.load_file('config.yaml')
config.load_env(prefix='APP_')

port = config.get('server.port')  # 8080
host = config['server.host']      # 'localhost'
```

## Interview Questions

**Q: How does a token bucket rate limiter work?**
A: Tokens are added at a fixed rate up to a capacity. Each request consumes one token. If no tokens available, request is rejected (429). Allows bursts up to capacity while maintaining average rate. Implemented with a counter and timestamp.

**Q: Explain the circuit breaker pattern and its states.**
A: CLOSED → normal operation, requests pass through. OPEN → too many failures, requests fail fast without calling the service. HALF_OPEN → after timeout, allows a test request. If it succeeds → CLOSED; if it fails → OPEN again. Prevents cascading failures.

**Q: What's the difference between retry with backoff and circuit breaker?**
A: Retry handles transient failures (try again after delay). Circuit breaker handles sustained failures (stop trying entirely). They complement each other: circuit breaker wraps the retry logic, preventing retry storms when a service is truly down.

## References

- [Circuit Breaker Pattern — Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Stripe Rate Limiting](https://stripe.com/blog/rate-limiters)
- [Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
