# Rate Limiter — Machine Coding Problem

## Problem Statement

Implement a rate limiter that controls the rate of requests a client can make to an API. Support multiple algorithms.

## Requirements

### Functional Requirements
1. Limit requests per client (identified by API key/IP)
2. Support multiple algorithms: Token Bucket, Sliding Window, Fixed Window
3. Return remaining quota and retry-after time
4. Configurable limits per client
5. Thread-safe for concurrent access

### Non-Functional Requirements
- O(1) time per request check
- Low memory footprint
- Distributed-ready design (conceptual)

## Rate Limiting Algorithms

### 1. Token Bucket

**Concept:** Bucket holds tokens. Each request consumes a token. Tokens are added at a fixed rate.

```
Bucket capacity: 10 tokens
Refill rate: 2 tokens/second

Time 0: [10 tokens] → Request: ALLOW (9 left)
Time 1: [11 tokens] → capped at 10 → Request: ALLOW (9 left)
Time 5: [10 tokens] → 5 requests: ALLOW (5 left)
Time 6: [7 tokens]  → 8 requests: DENY (only 7 available)
```

```
┌─────────────────────────────────────────────┐
│            Token Bucket                      │
│                                              │
│   ┌─────────────────────┐                   │
│   │ ○ ○ ○ ○ ○ ○ ○ ○     │ ← tokens         │
│   └─────────────────────┘                   │
│          ↑                    ↑              │
│       refill              consume            │
│     (fixed rate)         (per request)       │
│                                              │
│   capacity: max tokens the bucket can hold   │
│   refillRate: tokens added per second        │
└─────────────────────────────────────────────┘
```

### 2. Sliding Window Log

**Concept:** Keep a log of timestamps. Count requests in the sliding window.

```
Window: 60 seconds, Limit: 10 requests

Log: [t1, t2, t3, ..., t10]
New request at t_new:
  - Remove entries older than (t_new - 60)
  - Count remaining entries
  - If count < 10: ALLOW, add t_new to log
  - Else: DENY
```

### 3. Sliding Window Counter

**Concept:** Hybrid of fixed window and sliding window. Weight the previous window's count.

```
Window: 60 seconds, Limit: 100

Current window count: 40
Previous window count: 80
Elapsed in current window: 20/60 = 1/3

Weighted count = 80 * (1 - 1/3) + 40 = 80 * 2/3 + 40 = 93.3
If 93.3 < 100: ALLOW
```

### 4. Fixed Window Counter

**Concept:** Divide time into fixed windows. Count requests per window.

```
Window: 60 seconds, Limit: 100

Window [0:00 - 1:00]: 95 requests → ALLOW
Window [1:00 - 2:00]: 0 requests → RESET, start counting
```

## Class Design

```
┌─────────────────────────────────────────────────┐
│                  RateLimiter                      │
├─────────────────────────────────────────────────┤
│ - strategies: Map<key, RateLimitStrategy>        │
│ - defaultStrategy: RateLimitStrategy             │
├─────────────────────────────────────────────────┤
│ + isAllowed(key): RateLimitResult                │
│ + configure(key, strategy)                       │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│             RateLimitStrategy (interface)         │
├─────────────────────────────────────────────────┤
│ + allow(key): boolean                            │
│ + getRemainingQuota(key): int                    │
│ + getRetryAfter(key): Duration                   │
└─────────────────────────────────────────────────┘
           │               │               │
           ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ TokenBucket  │  │ SlidingWindow│  │ FixedWindow  │
│   Strategy   │  │   Strategy   │  │   Strategy   │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ - capacity   │  │ - windowSize │  │ - windowSize │
│ - refillRate │  │ - maxRequests│  │ - maxRequests│
│ - tokens     │  │ - log: TreeMap│  │ - counters   │
└──────────────┘  └──────────────┘  └──────────────┘

RateLimitResult:
┌─────────────────────────┐
│ - allowed: boolean       │
│ - remainingQuota: int    │
│ - retryAfterMs: long     │
│ - limit: int             │
│ - resetTimeMs: long      │
└─────────────────────────┘
```

## Implementation (Python)

```python
import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod
from collections import deque


@dataclass
class RateLimitResult:
    allowed: bool
    remaining_quota: int
    retry_after_ms: int = 0
    limit: int = 0
    reset_time_ms: int = 0


class RateLimitStrategy(ABC):
    @abstractmethod
    def allow(self, key: str) -> RateLimitResult:
        pass

    @abstractmethod
    def get_remaining(self, key: str) -> int:
        pass


# ==================== Token Bucket ====================

class TokenBucket(RateLimitStrategy):
    def __init__(self, capacity: int, refill_rate: float):
        """
        capacity: max tokens in bucket
        refill_rate: tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: Dict[str, dict] = {}
        self.lock = threading.Lock()

    def _get_bucket(self, key: str) -> dict:
        if key not in self.buckets:
            self.buckets[key] = {
                "tokens": self.capacity,
                "last_refill": time.time()
            }
        return self.buckets[key]

    def _refill(self, bucket: dict):
        now = time.time()
        elapsed = now - bucket["last_refill"]
        new_tokens = elapsed * self.refill_rate
        bucket["tokens"] = min(
            self.capacity, bucket["tokens"] + new_tokens)
        bucket["last_refill"] = now

    def allow(self, key: str) -> RateLimitResult:
        with self.lock:
            bucket = self._get_bucket(key)
            self._refill(bucket)

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return RateLimitResult(
                    allowed=True,
                    remaining_quota=int(bucket["tokens"]),
                    limit=self.capacity
                )
            else:
                wait_time = (1 - bucket["tokens"]) / self.refill_rate
                return RateLimitResult(
                    allowed=False,
                    remaining_quota=0,
                    retry_after_ms=int(wait_time * 1000),
                    limit=self.capacity
                )

    def get_remaining(self, key: str) -> int:
        with self.lock:
            bucket = self._get_bucket(key)
            self._refill(bucket)
            return int(bucket["tokens"])


# ==================== Sliding Window Log ====================

class SlidingWindowLog(RateLimitStrategy):
    def __init__(self, window_size_sec: int, max_requests: int):
        self.window_size = window_size_sec
        self.max_requests = max_requests
        self.logs: Dict[str, deque] = {}
        self.lock = threading.Lock()

    def _cleanup(self, log: deque, now: float):
        cutoff = now - self.window_size
        while log and log[0] < cutoff:
            log.popleft()

    def allow(self, key: str) -> RateLimitResult:
        with self.lock:
            now = time.time()
            if key not in self.logs:
                self.logs[key] = deque()

            log = self.logs[key]
            self._cleanup(log, now)

            if len(log) < self.max_requests:
                log.append(now)
                return RateLimitResult(
                    allowed=True,
                    remaining_quota=self.max_requests - len(log),
                    limit=self.max_requests
                )
            else:
                retry_after = log[0] + self.window_size - now
                return RateLimitResult(
                    allowed=False,
                    remaining_quota=0,
                    retry_after_ms=int(retry_after * 1000),
                    limit=self.max_requests
                )

    def get_remaining(self, key: str) -> int:
        with self.lock:
            now = time.time()
            if key not in self.logs:
                return self.max_requests
            log = self.logs[key]
            self._cleanup(log, now)
            return self.max_requests - len(log)


# ==================== Sliding Window Counter ====================

class SlidingWindowCounter(RateLimitStrategy):
    def __init__(self, window_size_sec: int, max_requests: int):
        self.window_size = window_size_sec
        self.max_requests = max_requests
        self.counters: Dict[str, dict] = {}
        self.lock = threading.Lock()

    def _get_window_key(self, timestamp: float) -> int:
        return int(timestamp // self.window_size)

    def allow(self, key: str) -> RateLimitResult:
        with self.lock:
            now = time.time()
            current_window = self._get_window_key(now)

            if key not in self.counters:
                self.counters[key] = {
                    "current_window": current_window,
                    "current_count": 0,
                    "previous_count": 0
                }

            data = self.counters[key]

            # Update window if needed
            if current_window != data["current_window"]:
                if current_window - data["current_window"] == 1:
                    data["previous_count"] = data["current_count"]
                else:
                    data["previous_count"] = 0
                data["current_count"] = 0
                data["current_window"] = current_window

            # Calculate weighted count
            elapsed_in_window = now % self.window_size
            weight = 1 - (elapsed_in_window / self.window_size)
            weighted_count = (
                data["previous_count"] * weight + data["current_count"]
            )

            if weighted_count < self.max_requests:
                data["current_count"] += 1
                remaining = int(
                    self.max_requests - weighted_count - 1)
                return RateLimitResult(
                    allowed=True,
                    remaining_quota=max(remaining, 0),
                    limit=self.max_requests
                )
            else:
                retry_after = self.window_size - elapsed_in_window
                return RateLimitResult(
                    allowed=False,
                    remaining_quota=0,
                    retry_after_ms=int(retry_after * 1000),
                    limit=self.max_requests
                )

    def get_remaining(self, key: str) -> int:
        with self.lock:
            now = time.time()
            if key not in self.counters:
                return self.max_requests
            data = self.counters[key]
            current_window = self._get_window_key(now)
            if current_window != data["current_window"]:
                return self.max_requests
            elapsed = now % self.window_size
            weight = 1 - (elapsed / self.window_size)
            wc = data["previous_count"] * weight + data["current_count"]
            return max(0, int(self.max_requests - wc))


# ==================== Fixed Window Counter ====================

class FixedWindowCounter(RateLimitStrategy):
    def __init__(self, window_size_sec: int, max_requests: int):
        self.window_size = window_size_sec
        self.max_requests = max_requests
        self.counters: Dict[str, dict] = {}
        self.lock = threading.Lock()

    def _get_window_key(self, timestamp: float) -> int:
        return int(timestamp // self.window_size)

    def allow(self, key: str) -> RateLimitResult:
        with self.lock:
            now = time.time()
            window_key = self._get_window_key(now)

            if key not in self.counters:
                self.counters[key] = {"window": window_key, "count": 0}

            data = self.counters[key]

            # Reset if new window
            if window_key != data["window"]:
                data["window"] = window_key
                data["count"] = 0

            if data["count"] < self.max_requests:
                data["count"] += 1
                remaining = self.max_requests - data["count"]
                reset_at = (window_key + 1) * self.window_size
                return RateLimitResult(
                    allowed=True,
                    remaining_quota=remaining,
                    limit=self.max_requests,
                    reset_time_ms=int(reset_at * 1000)
                )
            else:
                reset_at = (window_key + 1) * self.window_size
                retry_after = reset_at - now
                return RateLimitResult(
                    allowed=False,
                    remaining_quota=0,
                    retry_after_ms=int(retry_after * 1000),
                    limit=self.max_requests,
                    reset_time_ms=int(reset_at * 1000)
                )

    def get_remaining(self, key: str) -> int:
        with self.lock:
            now = time.time()
            window_key = self._get_window_key(now)
            if key not in self.counters:
                return self.max_requests
            data = self.counters[key]
            if window_key != data["window"]:
                return self.max_requests
            return self.max_requests - data["count"]


# ==================== Rate Limiter (Main) ====================

class RateLimiter:
    def __init__(self, strategy: RateLimitStrategy):
        self.strategy = strategy

    def is_allowed(self, key: str) -> RateLimitResult:
        return self.strategy.allow(key)

    def get_remaining(self, key: str) -> int:
        return self.strategy.get_remaining(key)


# ==================== Demo ====================

def demo_token_bucket():
    print("\n=== Token Bucket (capacity=5, refill=1/sec) ===")
    limiter = RateLimiter(TokenBucket(capacity=5, refill_rate=1))

    # Burst of 6 requests
    for i in range(6):
        result = limiter.is_allowed("client-1")
        status = "✅ ALLOW" if result.allowed else "❌ DENY"
        print(f"  Request {i+1}: {status} "
              f"(remaining: {result.remaining_quota})")

    print("\n  Waiting 3 seconds for refill...")
    time.sleep(3)

    result = limiter.is_allowed("client-1")
    status = "✅ ALLOW" if result.allowed else "❌ DENY"
    print(f"  Request: {status} (remaining: {result.remaining_quota})")


def demo_sliding_window():
    print("\n=== Sliding Window Counter (60s, limit=5) ===")
    limiter = RateLimiter(
        SlidingWindowCounter(window_size_sec=60, max_requests=5))

    for i in range(7):
        result = limiter.is_allowed("client-2")
        status = "✅ ALLOW" if result.allowed else "❌ DENY"
        print(f"  Request {i+1}: {status} "
              f"(remaining: {result.remaining_quota})")


def demo_fixed_window():
    print("\n=== Fixed Window Counter (10s, limit=3) ===")
    limiter = RateLimiter(
        FixedWindowCounter(window_size_sec=10, max_requests=3))

    for i in range(5):
        result = limiter.is_allowed("client-3")
        status = "✅ ALLOW" if result.allowed else "❌ DENY"
        print(f"  Request {i+1}: {status} "
              f"(remaining: {result.remaining_quota})")


if __name__ == "__main__":
    demo_token_bucket()
    demo_sliding_window()
    demo_fixed_window()
```

## Algorithm Comparison

| Algorithm | Pros | Cons | Best For |
|-----------|------|------|----------|
| Token Bucket | Allows bursts, smooth rate | Memory for state | API rate limiting |
| Sliding Window Log | Precise | High memory (stores timestamps) | Low-volume, precise limits |
| Sliding Window Counter | Memory efficient, accurate | Approximate | General purpose |
| Fixed Window | Simple, low memory | Burst at window boundaries | Simple rate limits |

## Distributed Rate Limiting

For production systems with multiple servers:

```
Option 1: Centralized (Redis)
  - Store counters in Redis
  - Atomic increment with TTL
  - Single source of truth

Option 2: Local + Sync
  - Each server maintains local count
  - Periodically sync with central store
  - Allow slight over-limit

Option 3: Sticky Sessions
  - Route same client to same server
  - Simple but less fault-tolerant
```

```python
# Redis-based Token Bucket (pseudocode)
class RedisTokenBucket:
    def allow(self, key: str) -> bool:
        lua_script = """
        local tokens = redis.call('GET', KEYS[1]) or ARGV[1]
        local last_time = redis.call('GET', KEYS[2]) or ARGV[3]
        local now = ARGV[3]
        local refill = (now - last_time) * ARGV[2]
        tokens = math.min(ARGV[1], tokens + refill)
        if tokens >= 1 then
            tokens = tokens - 1
            redis.call('SET', KEYS[1], tokens)
            redis.call('SET', KEYS[2], now)
            return 1
        end
        return 0
        """
        return self.redis.eval(lua_script, 2, 
                              f"{key}:tokens", f"{key}:time",
                              self.capacity, self.refill_rate, time.time())
```

## Interview Follow-ups

1. **"How would you handle distributed rate limiting?"**
   → Redis with Lua scripts for atomic operations

2. **"How would you rate limit by different dimensions?"**
   → Per-user, per-IP, per-endpoint with separate strategies

3. **"How would you handle rate limit headers in HTTP?"**
   → Return X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset

4. **"What happens if Redis goes down?"**
   → Fallback to local rate limiting, graceful degradation
