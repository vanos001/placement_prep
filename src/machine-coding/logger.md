# Logger — Machine Coding Problem

## Problem Statement

Design a logging framework that supports multiple log levels, configurable formatting, output destinations (console, file), log filtering, file rotation based on size/time, and both synchronous and asynchronous logging modes with thread safety.

## Requirements Gathering

### Functional Requirements
1. Log levels: DEBUG, INFO, WARN, ERROR, FATAL
2. Configurable output destinations (console, file, or both)
3. Structured log messages with timestamp, level, logger name, thread info
4. Log filtering by level threshold (e.g., only log WARN and above)
5. File rotation: by size (max bytes) and by time (daily)
6. File retention: keep last N log files
7. Thread-safe logging from multiple threads
8. Asynchronous logging mode (log queue + background writer)
9. Configurable log format (pattern-based)

### Non-Functional Requirements
- Minimal performance overhead (< 1ms per log call in sync mode)
- No log message loss in async mode (on graceful shutdown)
- Thread-safe without external dependencies

### Clarifying Questions
- "Should the logger support multiple output destinations simultaneously?"
- "What's the expected log volume — hundreds or millions per second?"
- "Should file rotation block the calling thread?"
- "Are structured logging formats (JSON) required?"

## Class Design

### Entity Identification
```
Nouns: Logger, LogLevel, LogMessage, Formatter, Handler,
       ConsoleHandler, FileHandler, RotatingFileHandler,
       LogFilter, AsyncAppender, Configuration
```

### Class Diagram

```
┌──────────────────────┐
│       Logger          │
├──────────────────────┤
│ - name: String        │
│ - level: LogLevel    │
│ - handlers: List      │
│ - filters: List      │
├──────────────────────┤
│ + debug(msg)         │
│ + info(msg)          │
│ + warn(msg)          │
│ + error(msg)         │
│ + fatal(msg)         │
│ + log(level, msg)    │
│ + addHandler(h)      │
│ + setLevel(level)    │
└───────────┬──────────┘
            │ dispatches to
            ▼
┌──────────────────────┐
│   Handler (Abstract)  │
├──────────────────────┤
│ - formatter: Formatter│
│ - level: LogLevel     │
│ - filter: LogFilter   │
├──────────────────────┤
│ + handle(msg)         │
│ + emit(formatted)    │
│ + close()             │
└───────────┬──────────┘
     ┌──────┴──────────┐
     ▼                 ▼
┌─────────────┐  ┌──────────────────┐
│ConsoleHandler│  │  FileHandler     │
├─────────────┤  ├──────────────────┤
│ - stream     │  │ - file_path      │
├─────────────┤  │ - file_obj        │
│ + emit(msg)  │  │ + emit(msg)      │
└─────────────┘  │ + rotate()        │
                 │ + close()         │
                 └────────┬──────────┘
                          │ extends
                          ▼
                 ┌──────────────────────┐
                 │RotatingFileHandler   │
                 ├──────────────────────┤
                 │ - max_bytes: int     │
                 │ - max_files: int     │
                 │ - current_size: int  │
                 ├──────────────────────┤
                 │ + emit(msg)          │
                 │ + _should_rotate()   │
                 │ + _do_rotation()     │
                 └──────────────────────┘

┌──────────────────────┐
│   LogMessage          │
├──────────────────────┤
│ - level: LogLevel     │
│ - message: String     │
│ - logger_name: String │
│ - timestamp: datetime │
│ - thread_id: int      │
│ - thread_name: String│
├──────────────────────┤
│ + format(fmt): str   │
└──────────────────────┘

┌──────────────────────┐
│   Formatter           │
├──────────────────────┤
│ - pattern: String     │
├──────────────────────┤
│ + format(msg): str   │
│ + setPattern(p)       │
└──────────────────────┘

┌──────────────────────┐
│   AsyncAppender       │
├──────────────────────┤
│ - queue: Queue        │
│ - worker: Thread      │
│ - handlers: List      │
├──────────────────────┤
│ + start()             │
│ + stop()              │
│ + enqueue(msg)        │
└──────────────────────┘
```

### Enums

```
LogLevel: DEBUG(10), INFO(20), WARN(30), ERROR(40), FATAL(50)
```

## Implementation

### Python Implementation

```python
import os
import sys
import threading
import time
from enum import Enum, IntEnum
from queue import Queue, Empty
from datetime import datetime
from typing import List, Optional, Callable


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    FATAL = 50


class LogMessage:
    def __init__(self, level: LogLevel, message: str,
                 logger_name: str):
        self.level = level
        self.message = message
        self.logger_name = logger_name
        self.timestamp = datetime.now()
        self.thread_id = threading.get_ident()
        self.thread_name = threading.current_thread().name


class Formatter:
    DEFAULT_PATTERN = "[{timestamp}] [{level:<5}] [{logger}] [{thread}] {message}"

    def __init__(self, pattern: str = None):
        self.pattern = pattern or self.DEFAULT_PATTERN

    def format(self, msg: LogMessage) -> str:
        return self.pattern.format(
            timestamp=msg.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            level=msg.level.name,
            logger=msg.logger_name,
            thread=msg.thread_name,
            message=msg.message,
            thread_id=msg.thread_id,
        )

    def format_json(self, msg: LogMessage) -> str:
        """Structured JSON format for machine parsing."""
        import json
        return json.dumps({
            "timestamp": msg.timestamp.isoformat(),
            "level": msg.level.name,
            "logger": msg.logger_name,
            "message": msg.message,
            "thread_id": msg.thread_id,
            "thread_name": msg.thread_name,
        })


class LogFilter:
    def __init__(self, min_level: LogLevel = LogLevel.DEBUG):
        self.min_level = min_level

    def should_log(self, msg: LogMessage) -> bool:
        return msg.level >= self.min_level


class Handler:
    def __init__(self, formatter: Formatter = None,
                 filter: LogFilter = None):
        self.formatter = formatter or Formatter()
        self.filter = filter or LogFilter()
        self._lock = threading.Lock()

    def handle(self, msg: LogMessage):
        if not self.filter.should_log(msg):
            return
        formatted = self.formatter.format(msg)
        with self._lock:
            self.emit(formatted)

    def emit(self, formatted: str):
        raise NotImplementedError

    def close(self):
        pass


class ConsoleHandler(Handler):
    def __init__(self, use_stderr: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.stream = sys.stderr if use_stderr else sys.stdout

    def emit(self, formatted: str):
        try:
            self.stream.write(formatted + "\n")
            self.stream.flush()
        except (OSError, ValueError):
            pass


class FileHandler(Handler):
    def __init__(self, file_path: str, mode: str = "a", **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.mode = mode
        self._file = None
        self._open()

    def _open(self):
        os.makedirs(os.path.dirname(self.file_path) or ".", exist_ok=True)
        self._file = open(self.file_path, self.mode, encoding="utf-8")

    def emit(self, formatted: str):
        try:
            self._file.write(formatted + "\n")
            self._file.flush()
        except (OSError, ValueError):
            pass

    def close(self):
        if self._file and not self._file.closed:
            self._file.close()


class RotatingFileHandler(FileHandler):
    def __init__(self, file_path: str, max_bytes: int = 10 * 1024 * 1024,
                 max_files: int = 5, **kwargs):
        super().__init__(file_path, **kwargs)
        self.max_bytes = max_bytes
        self.max_files = max_files
        self.current_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

    def emit(self, formatted: str):
        with self._lock:
            if self._should_rotate(len(formatted)):
                self._do_rotation()
            self._file.write(formatted + "\n")
            self.current_size += len(formatted) + 1
            self._file.flush()

    def _should_rotate(self, msg_size: int) -> bool:
        return self.current_size + msg_size > self.max_bytes

    def _do_rotation(self):
        self._file.close()
        # Shift files: app.log.4 → delete, .3 → .4, .2 → .3, .1 → .2, app.log → .1
        for i in range(self.max_files - 1, 0, -1):
            src = f"{self.file_path}.{i}"
            dst = f"{self.file_path}.{i + 1}"
            if os.path.exists(src):
                os.rename(src, dst)
        # Delete oldest if exceeding max_files
        oldest = f"{self.file_path}.{self.max_files}"
        if os.path.exists(oldest):
            os.remove(oldest)
        # Rotate current to .1
        os.rename(self.file_path, f"{self.file_path}.1")
        self._open()
        self.current_size = 0


class AsyncAppender:
    """Wraps handlers in an async queue for non-blocking logging."""

    def __init__(self, handlers: List[Handler], queue_size: int = 10000):
        self.handlers = handlers
        self.queue: Queue = Queue(maxsize=queue_size)
        self._running = False
        self._worker = None

    def start(self):
        self._running = True
        self._worker = threading.Thread(target=self._run, daemon=True)
        self._worker.start()

    def stop(self, timeout: float = 5.0):
        self._running = False
        if self._worker:
            self._worker.join(timeout=timeout)
        # Flush remaining messages
        self._flush_queue()

    def enqueue(self, msg: LogMessage):
        try:
            self.queue.put_nowait(msg)
        except Exception:
            # Fallback: log synchronously
            for h in self.handlers:
                h.handle(msg)

    def _run(self):
        while self._running or not self.queue.empty():
            try:
                msg = self.queue.get(timeout=0.1)
                for handler in self.handlers:
                    handler.handle(msg)
                self.queue.task_done()
            except Empty:
                continue

    def _flush_queue(self):
        while not self.queue.empty():
            try:
                msg = self.queue.get_nowait()
                for handler in self.handlers:
                    handler.handle(msg)
            except Empty:
                break


class Logger:
    def __init__(self, name: str, level: LogLevel = LogLevel.DEBUG):
        self.name = name
        self.level = level
        self.handlers: List[Handler] = []
        self.async_appender: Optional[AsyncAppender] = None

    def add_handler(self, handler: Handler):
        self.handlers.append(handler)

    def set_async(self, queue_size: int = 10000):
        """Switch to async mode."""
        self.async_appender = AsyncAppender(self.handlers, queue_size)
        self.async_appender.start()

    def stop_async(self):
        if self.async_appender:
            self.async_appender.stop()

    def log(self, level: LogLevel, message: str):
        if level < self.level:
            return
        msg = LogMessage(level, message, self.name)
        if self.async_appender:
            self.async_appender.enqueue(msg)
        else:
            for handler in self.handlers:
                handler.handle(msg)

    def debug(self, message: str):
        self.log(LogLevel.DEBUG, message)

    def info(self, message: str):
        self.log(LogLevel.INFO, message)

    def warn(self, message: str):
        self.log(LogLevel.WARN, message)

    def error(self, message: str):
        self.log(LogLevel.ERROR, message)

    def fatal(self, message: str):
        self.log(LogLevel.FATAL, message)


# ==================== Logger Manager ====================

class LoggerManager:
    """Singleton-style manager for named loggers."""
    _instance = None
    _loggers: dict = {}

    @classmethod
    def get_logger(cls, name: str, level: LogLevel = LogLevel.INFO) -> Logger:
        if name not in cls._loggers:
            cls._loggers[name] = Logger(name, level)
        return cls._loggers[name]

    @classmethod
    def shutdown(cls):
        for logger in cls._loggers.values():
            logger.stop_async()
            for handler in logger.handlers:
                handler.close()


def main():
    logger = LoggerManager.get_logger("App", LogLevel.DEBUG)
    logger.add_handler(ConsoleHandler())

    file_handler = RotatingFileHandler(
        "logs/app.log", max_bytes=1024, max_files=3
    )
    logger.add_handler(file_handler)

    logger.info("Application started")
    logger.debug("Loading configuration...")
    logger.warn("Deprecated API endpoint called")
    logger.error("Failed to connect to database")

    # Test from multiple threads
    def worker(thread_id):
        for i in range(5):
            logger.info(f"Worker {thread_id} message {i}")
            time.sleep(0.001)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    logger.info("All threads finished")
    LoggerManager.shutdown()


if __name__ == "__main__":
    main()
```

## Synchronous vs. Asynchronous Logging

### Synchronous
- Log call blocks until the message is written to all handlers
- Simple, no message loss
- Overhead: I/O latency per log call (disk writes can be 1-10ms)

### Asynchronous
- Log call enqueues a message to an in-memory queue (sub-microsecond)
- A background thread dequeues and writes to handlers
- Near-zero latency impact on application threads
- Risk: messages lost on crash before queue drains (mitigate with `stop()` on shutdown)

## File Rotation Strategies

| Strategy | Trigger | How |
|----------|---------|-----|
| **Size-based** | File exceeds max_bytes | Rename to .1, create new file, delete oldest |
| **Time-based** | Calendar day/week/hour | Append date to filename: `app.2025-01-15.log` |
| **Hybrid** | Size or time, whichever first | Combine both triggers |

## Extensions and Discussion Points

### 1. Structured Logging (JSON)
Add `JsonFormatter` that outputs machine-parseable JSON. Essential for production environments where logs are ingested by ELK/Datadog.

### 2. Log Aggregation
For distributed systems, send logs to a central service via HTTP or use a log shipper (Fluentd, Filebeat).

### 3. Dynamic Log Level
Change log levels at runtime without restart (e.g., via API endpoint or signal).

### 4. MDC (Mapped Diagnostic Context)
Attach contextual metadata (request ID, user ID) to all log messages within a request scope.

### 5. Lazy Evaluation
Accept callables instead of strings: `logger.debug(lambda: expensive_computation())` — only evaluate if the log level is active.

## Interview Tips

1. **Thread safety is the core challenge** — discuss `threading.Lock`, `Queue`, and potential deadlocks
2. **Async mode trade-offs**: lower latency vs. potential message loss on crash
3. **File rotation edge cases**: what if the disk is full during rotation?
4. **Production considerations**: structured logging, log levels in production, log sampling for high-volume services
5. **Compare with real frameworks**: Python's `logging` module, Java's Log4j/SLF4J — discuss what's similar and different
