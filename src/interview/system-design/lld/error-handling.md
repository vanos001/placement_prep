# Error Handling Design

## Why Error Handling Matters in LLD

Robust error handling is a hallmark of production-quality code. In LLD interviews, how you handle errors shows your maturity as an engineer.

## Exception Handling

### Exception Hierarchy

```
Exception
├── RuntimeException (unchecked)
│   ├── NullPointerException
│   ├── IllegalArgumentException
│   ├── IllegalStateException
│   └── UnsupportedOperationException
├── IOException (checked)
│   ├── FileNotFoundException
│   └── SocketTimeoutException
└── Custom Exceptions
    ├── PaymentException
    ├── AuthenticationException
    └── ValidationException
```

### Custom Exception Classes

```python
class AppError(Exception):
    """Base exception for application"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.code = code or "INTERNAL_ERROR"
        self.details = details or {}

class ValidationError(AppError):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field})

class NotFoundError(AppError):
    """Raised when a resource is not found"""
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            f"{resource} with id '{identifier}' not found",
            code="NOT_FOUND",
            details={"resource": resource, "identifier": identifier}
        )

class AuthenticationError(AppError):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="AUTHENTICATION_ERROR")

class AuthorizationError(AppError):
    """Raised when authorization fails"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, code="AUTHORIZATION_ERROR")

class ConflictError(AppError):
    """Raised when there's a conflict (e.g., duplicate)"""
    def __init__(self, message: str, resource: str = None):
        super().__init__(message, code="CONFLICT", details={"resource": resource})

class ExternalServiceError(AppError):
    """Raised when external service call fails"""
    def __init__(self, service: str, message: str):
        super().__init__(
            f"External service '{service}' error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            details={"service": service}
        )
```

### Exception Handling Best Practices

```python
# ❌ Bad: Catching too broadly
try:
    process_payment(order)
except Exception:
    pass  # Swallowing all errors

# ❌ Bad: Catching too narrowly
try:
    process_payment(order)
except ValueError:
    handle_error()  # Misses network errors, timeouts, etc.

# ✅ Good: Catch specific exceptions, handle appropriately
try:
    process_payment(order)
except ValidationError as e:
    log.warning(f"Validation failed: {e}")
    return {"error": e.message, "code": e.code, "details": e.details}
except ExternalServiceError as e:
    log.error(f"Payment service error: {e}")
    return {"error": "Payment temporarily unavailable", "code": "SERVICE_UNAVAILABLE"}
except Exception as e:
    log.exception(f"Unexpected error processing payment: {e}")
    return {"error": "Internal error", "code": "INTERNAL_ERROR"}
```

## Result Type (Alternative to Exceptions)

Some languages use Result types instead of exceptions for expected failures.

```python
from typing import TypeVar, Generic, Union
from dataclasses import dataclass

T = TypeVar('T')
E = TypeVar('E')

@dataclass
class Success(Generic[T]):
    value: T

@dataclass
class Failure(Generic[E]):
    error: E

Result = Union[Success[T], Failure[E]]

class PaymentResult:
    @staticmethod
    def success(transaction_id: str) -> Success[dict]:
        return Success({"transaction_id": transaction_id, "status": "success"})
    
    @staticmethod
    def failure(error: str) -> Failure[str]:
        return Failure(error)

def process_payment(amount: float) -> Result:
    if amount <= 0:
        return PaymentResult.failure("Amount must be positive")
    if amount > 10000:
        return PaymentResult.failure("Amount exceeds limit")
    
    # Process payment...
    return PaymentResult.success("txn_123")

# Usage
result = process_payment(500)
if isinstance(result, Success):
    print(f"Payment successful: {result.value}")
else:
    print(f"Payment failed: {result.error}")
```

### Java Result Type

```java
public class Result<T, E> {
    private final T value;
    private final E error;
    private final boolean isSuccess;
    
    private Result(T value, E error, boolean isSuccess) {
        this.value = value;
        this.error = error;
        this.isSuccess = isSuccess;
    }
    
    public static <T, E> Result<T, E> success(T value) {
        return new Result<>(value, null, true);
    }
    
    public static <T, E> Result<T, E> failure(E error) {
        return new Result<>(null, error, false);
    }
    
    public boolean isSuccess() { return isSuccess; }
    public boolean isFailure() { return !isSuccess; }
    public T getValue() { return value; }
    public E getError() { return error; }
    
    public <U> Result<U, E> map(Function<T, U> mapper) {
        if (isSuccess) return Result.success(mapper.apply(value));
        return Result.failure(error);
    }
    
    public Result<T, E> orElse(Function<E, Result<T, E>> handler) {
        if (isSuccess) return this;
        return handler.apply(error);
    }
}
```

## Retry Strategies

### Exponential Backoff

```python
import time
import random
from typing import Callable, TypeVar

T = TypeVar('T')

def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> T:
    """Retry a function with exponential backoff"""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise
            
            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            
            # Add jitter to prevent thundering herd
            if jitter:
                delay = delay * (0.5 + random.random())
            
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)

# Usage
def unreliable_api_call():
    import random
    if random.random() < 0.7:
        raise ConnectionError("API timeout")
    return {"status": "success"}

try:
    result = retry_with_backoff(unreliable_api_call, max_retries=3)
    print(f"Success: {result}")
except ConnectionError:
    print("All retries exhausted")
```

### Retry with Conditions

```python
from functools import wraps
from typing import Tuple, Type

def retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for retrying functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        raise
                    print(f"Retry {retries}/{max_retries} after {current_delay}s: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@retry(max_retries=3, delay=1.0, exceptions=(ConnectionError, TimeoutError))
def fetch_data(url: str) -> dict:
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    return response.json()
```

## Circuit Breaker Pattern

Prevent cascading failures by failing fast when a service is down.

```python
import time
from enum import Enum
from typing import Callable, TypeVar

T = TypeVar('T')

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
    
    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        current_state = self.state
        
        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        self._failure_count = 0
        self._state = CircuitState.CLOSED
    
    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

class CircuitBreakerOpenError(Exception):
    pass

# Usage
payment_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

def process_payment(amount: float):
    return payment_breaker.call(
        lambda: external_payment_api.charge(amount)
    )

try:
    result = process_payment(100.0)
except CircuitBreakerOpenError:
    # Fall back to alternative payment method
    use_backup_payment_processor()
```

## Error Handling in Microservices

### Error Propagation

```python
class ServiceError:
    def __init__(self, status_code: int, message: str, code: str, details: dict = None):
        self.status_code = status_code
        self.message = message
        self.code = code
        self.details = details or {}
    
    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }

# API Gateway error handler
def handle_service_error(error: ServiceError):
    return jsonify(error.to_dict()), error.status_code

# Service layer
class OrderService:
    def __init__(self, payment_client, inventory_client):
        self.payment_client = payment_client
        self.inventory_client = inventory_client
    
    def place_order(self, order_data: dict) -> dict:
        try:
            # Check inventory
            inventory_result = self.inventory_client.check_availability(order_data)
            if not inventory_result["available"]:
                raise ServiceError(409, "Item out of stock", "OUT_OF_STOCK")
            
            # Process payment
            payment_result = self.payment_client.charge(order_data["total"])
            if payment_result["status"] != "success":
                raise ServiceError(402, "Payment failed", "PAYMENT_FAILED")
            
            # Create order
            return {"order_id": "ORD-123", "status": "confirmed"}
            
        except ServiceError:
            raise  # Re-raise service errors
        except Exception as e:
            # Wrap unexpected errors
            raise ServiceError(500, "Internal server error", "INTERNAL_ERROR")
```

## Error Handling Patterns

### 1. Fail Fast
```python
def validate_order(order: dict):
    if not order.get("items"):
        raise ValidationError("Order must have items", field="items")
    if order.get("total", 0) <= 0:
        raise ValidationError("Order total must be positive", field="total")
    if not order.get("user_id"):
        raise ValidationError("User ID is required", field="user_id")
```

### 2. Graceful Degradation
```python
def get_user_recommendations(user_id: str) -> list:
    try:
        # Try personalized recommendations
        return recommendation_service.get_personalized(user_id)
    except ExternalServiceError:
        try:
            # Fall back to trending items
            return recommendation_service.get_trending()
        except ExternalServiceError:
            # Final fallback to static list
            return get_default_recommendations()
```

### 3. Bulkhead Pattern
```python
from concurrent.futures import ThreadPoolExecutor

class BulkheadExecutor:
    def __init__(self, max_concurrent: int):
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.semaphore = threading.Semaphore(max_concurrent)
    
    def execute(self, func, *args, **kwargs):
        if not self.semaphore.acquire(blocking=False):
            raise BulkheadFullError("Too many concurrent requests")
        try:
            return self.executor.submit(func, *args, **kwargs).result()
        finally:
            self.semaphore.release()
```

## Interview Tips

1. **Define error types early** — "Let me define the error types for this system"
2. **Use custom exceptions** — Don't just use generic Exception
3. **Consider retry strategies** — "We'll retry with exponential backoff"
4. **Mention circuit breaker** — "For external service calls"
5. **Show graceful degradation** — "If X fails, fall back to Y"
6. **Log errors appropriately** — "Log with context for debugging"
7. **Consider user experience** — "Show friendly error messages to users"

## Common Mistakes

- ❌ Catching and swallowing exceptions
- ❌ Using exceptions for control flow
- ❌ Not logging errors with context
- ❌ Exposing internal errors to users
- ❌ Not retrying transient failures
- ❌ Missing circuit breaker for external services

## Cross-References

- [SOLID Principles](./solid.md) — SRP for error handling classes
- [Design Patterns](./design-patterns.md) — Circuit breaker pattern
- [Concurrency Design](./concurrency-design.md) — Error handling in async
- [Notification Service](./notification-service.md) — Error handling in notifications
