# Task Scheduler — Machine Coding Problem

## Problem Statement

Design a task scheduler that supports priorities, dependencies between tasks, and scheduled execution.

## Requirements

### Functional Requirements
1. Submit tasks with priority (LOW, MEDIUM, HIGH, CRITICAL)
2. Define dependencies (task B runs after task A completes)
3. Execute tasks respecting priority and dependency order
4. Support delayed/scheduled execution (run at specific time)
5. Track task status (PENDING, RUNNING, COMPLETED, FAILED)
6. Retry failed tasks with configurable retry count
7. Cancel pending tasks
8. Query task status and execution history

### Non-Functional Requirements
- Thread-safe task submission and execution
- Efficient priority-based scheduling
- Handle dependency cycles (detect and reject)

## Class Design

```
┌─────────────────────────────────────────────────────────┐
│                    TaskScheduler                         │
├─────────────────────────────────────────────────────────┤
│ - taskQueue: PriorityQueue<ScheduledTask>               │
│ - tasks: Map<taskId, Task>                              │
│ - executor: ExecutorService                             │
│ - dependencyGraph: DirectedGraph                        │
│ - workers: int                                          │
├─────────────────────────────────────────────────────────┤
│ + submit(task): taskId                                  │
│ + submitWithDelay(task, delay): taskId                  │
│ + submitWithDependencies(task, deps): taskId            │
│ + cancel(taskId): boolean                               │
│ + getStatus(taskId): TaskStatus                         │
│ + start()                                               │
│ + shutdown()                                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                       Task                               │
├─────────────────────────────────────────────────────────┤
│ - taskId: String                                        │
│ - name: String                                          │
│ - priority: Priority                                    │
│ - callable: Callable<Result>                            │
│ - status: TaskStatus                                    │
│ - retries: int                                          │
│ - maxRetries: int                                       │
│ - scheduledAt: Instant                                  │
│ - dependencies: Set<taskId>                             │
│ - result: Result                                        │
│ - error: Exception                                      │
├─────────────────────────────────────────────────────────┤
│ + execute(): Result                                     │
│ + canExecute(): boolean (all deps completed?)           │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  DependencyGraph                         │
├─────────────────────────────────────────────────────────┤
│ - adjacency: Map<taskId, Set<taskId>>                   │
│ - inDegree: Map<taskId, Integer>                        │
├─────────────────────────────────────────────────────────┤
│ + addTask(taskId)                                       │
│ + addDependency(from, to)                               │
│ + hasCycle(): boolean                                   │
│ + getExecutableTasks(): Set<taskId>                     │
│ + markComplete(taskId) → newly freed tasks              │
└─────────────────────────────────────────────────────────┘

Priority: CRITICAL(4) > HIGH(3) > MEDIUM(2) > LOW(1)
TaskStatus: PENDING → SCHEDULED → RUNNING → COMPLETED/FAILED/CANCELLED
```

## Implementation (Python)

```python
import heapq
import time
import threading
from enum import Enum, IntEnum
from typing import Callable, Any, Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import uuid


# ==================== Enums ====================

class Priority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==================== Models ====================

@dataclass
class TaskResult:
    success: bool
    value: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass(order=True)
class ScheduledTask:
    """Wrapper for priority queue ordering."""
    priority: int = field(compare=True)
    scheduled_at: float = field(compare=True)
    task_id: str = field(default="", compare=False)
    task: Any = field(default=None, compare=False)  # Task ref


class Task:
    def __init__(self, name: str, func: Callable[..., Any],
                 priority: Priority = Priority.MEDIUM,
                 max_retries: int = 0,
                 delay_seconds: float = 0,
                 dependencies: Set[str] = None):
        self.task_id = str(uuid.uuid4())[:8]
        self.name = name
        self.func = func
        self.priority = priority
        self.max_retries = max_retries
        self.retries = 0
        self.status = TaskStatus.PENDING
        self.dependencies = dependencies or set()
        self.result: Optional[TaskResult] = None
        self.created_at = time.time()
        self.scheduled_at = self.created_at + delay_seconds
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None

    def execute(self) -> TaskResult:
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()
        try:
            value = self.func()
            duration = (time.time() - self.started_at) * 1000
            self.result = TaskResult(
                success=True, value=value, duration_ms=duration)
            self.status = TaskStatus.COMPLETED
        except Exception as e:
            duration = (time.time() - self.started_at) * 1000
            self.result = TaskResult(
                success=False, error=str(e), duration_ms=duration)
            if self.retries < self.max_retries:
                self.retries += 1
                self.status = TaskStatus.PENDING
                self.scheduled_at = time.time() + (2 ** self.retries)
            else:
                self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        return self.result

    def can_execute(self, completed_tasks: Set[str]) -> bool:
        return self.dependencies.issubset(completed_tasks)

    def __str__(self):
        return (f"Task[{self.task_id}] '{self.name}' "
                f"P:{self.priority.name} S:{self.status.value}")


# ==================== Dependency Graph ====================

class DependencyGraph:
    def __init__(self):
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)
        self.in_degree: Dict[str, int] = defaultdict(int)
        self.dependents: Dict[str, Set[str]] = defaultdict(set)

    def add_task(self, task_id: str):
        if task_id not in self.adjacency:
            self.adjacency[task_id] = set()
            self.in_degree[task_id] = 0

    def add_dependency(self, task_id: str, depends_on: str):
        """task_id depends on depends_on."""
        self.adjacency[depends_on].add(task_id)
        self.dependents[task_id].add(depends_on)
        self.in_degree[task_id] = self.in_degree.get(task_id, 0) + 1

    def has_cycle(self) -> bool:
        """Detect cycle using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {n: WHITE for n in self.adjacency}

        def dfs(node):
            color[node] = GRAY
            for neighbor in self.adjacency.get(node, []):
                if color.get(neighbor) == GRAY:
                    return True
                if color.get(neighbor) == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        return any(
            dfs(n) for n in self.adjacency 
            if color[n] == WHITE
        )

    def get_ready_tasks(self, completed: Set[str], 
                        pending: Set[str]) -> Set[str]:
        """Get tasks whose dependencies are all completed."""
        ready = set()
        for task_id in pending:
            deps = self.dependents.get(task_id, set())
            if deps.issubset(completed):
                ready.add(task_id)
        return ready

    def mark_complete(self, task_id: str) -> Set[str]:
        """Mark task complete, return newly freed tasks."""
        freed = set()
        for dependent in self.adjacency.get(task_id, []):
            self.in_degree[dependent] -= 1
            if self.in_degree[dependent] == 0:
                freed.add(dependent)
        return freed


# ==================== Task Scheduler ====================

class TaskScheduler:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[ScheduledTask] = []  # min-heap
        self.completed_tasks: Set[str] = set()
        self.dep_graph = DependencyGraph()
        self.lock = threading.Lock()
        self.running = False
        self.workers: List[threading.Thread] = []
        self._queue_event = threading.Event()

    def submit(self, name: str, func: Callable,
               priority: Priority = Priority.MEDIUM,
               max_retries: int = 0,
               delay_seconds: float = 0,
               dependencies: Set[str] = None) -> str:
        """Submit a task. Returns task ID."""
        task = Task(name, func, priority, max_retries,
                    delay_seconds, dependencies or set())

        with self.lock:
            # Check for dependency cycles
            if dependencies:
                for dep in dependencies:
                    if dep not in self.tasks:
                        raise ValueError(f"Dependency {dep} not found")
                    if self.tasks[dep].status == TaskStatus.FAILED:
                        raise ValueError(
                            f"Dependency {dep} has failed")

            self.tasks[task.task_id] = task
            self.dep_graph.add_task(task.task_id)

            if dependencies:
                for dep in dependencies:
                    self.dep_graph.add_dependency(task.task_id, dep)

                if self.dep_graph.has_cycle():
                    # Rollback
                    del self.tasks[task.task_id]
                    raise ValueError(
                        "Adding this dependency creates a cycle!")

            # Check if task can run immediately
            if task.can_execute(self.completed_tasks):
                task.status = TaskStatus.SCHEDULED
                scheduled = ScheduledTask(
                    priority=-task.priority.value,
                    scheduled_at=task.scheduled_at,
                    task_id=task.task_id,
                    task=task
                )
                heapq.heappush(self.task_queue, scheduled)
                self._queue_event.set()

        return task.task_id

    def cancel(self, task_id: str) -> bool:
        with self.lock:
            task = self.tasks.get(task_id)
            if task and task.status in (
                    TaskStatus.PENDING, TaskStatus.SCHEDULED):
                task.status = TaskStatus.CANCELLED
                return True
            return False

    def get_status(self, task_id: str) -> Optional[TaskStatus]:
        task = self.tasks.get(task_id)
        return task.status if task else None

    def get_result(self, task_id: str) -> Optional[TaskResult]:
        task = self.tasks.get(task_id)
        return task.result if task else None

    def _worker_loop(self):
        while self.running:
            scheduled_task = None
            with self.lock:
                now = time.time()
                if (self.task_queue and 
                        self.task_queue[0].scheduled_at <= now):
                    scheduled_task = heapq.heappop(self.task_queue)

            if scheduled_task:
                task = scheduled_task.task
                if task.status == TaskStatus.CANCELLED:
                    continue

                # Execute
                result = task.execute()

                with self.lock:
                    if task.status == TaskStatus.COMPLETED:
                        self.completed_tasks.add(task.task_id)
                        # Release dependent tasks
                        freed = self.dep_graph.mark_complete(
                            task.task_id)
                        for freed_id in freed:
                            freed_task = self.tasks[freed_id]
                            if freed_task.can_execute(
                                    self.completed_tasks):
                                freed_task.status = TaskStatus.SCHEDULED
                                st = ScheduledTask(
                                    priority=-freed_task.priority.value,
                                    scheduled_at=freed_task.scheduled_at,
                                    task_id=freed_id,
                                    task=freed_task
                                )
                                heapq.heappush(self.task_queue, st)

                    elif task.status == TaskStatus.PENDING:
                        # Retry — re-add to queue
                        st = ScheduledTask(
                            priority=-task.priority.value,
                            scheduled_at=task.scheduled_at,
                            task_id=task.task_id,
                            task=task
                        )
                        heapq.heappush(self.task_queue, st)
            else:
                time.sleep(0.01)  # Avoid busy-wait

    def start(self):
        self.running = True
        for i in range(self.max_workers):
            t = threading.Thread(
                target=self._worker_loop, 
                daemon=True, name=f"Worker-{i}")
            t.start()
            self.workers.append(t)

    def shutdown(self):
        self.running = False
        for t in self.workers:
            t.join(timeout=5)

    def display(self):
        print(f"\n{'='*60}")
        print("  Task Scheduler Status")
        print(f"{'='*60}")
        for task in sorted(self.tasks.values(), 
                          key=lambda t: t.priority, reverse=True):
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.SCHEDULED: "📋",
                TaskStatus.RUNNING: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.CANCELLED: "🚫",
            }
            icon = status_icon.get(task.status, "?")
            print(f"  {icon} {task}")
            if task.result:
                if task.result.success:
                    print(f"     Result: {task.result.value} "
                          f"({task.result.duration_ms:.1f}ms)")
                else:
                    print(f"     Error: {task.result.error}")
        print(f"{'='*60}\n")


# ==================== Demo ====================

def main():
    scheduler = TaskScheduler(max_workers=2)
    scheduler.start()

    print("=== Task Scheduler Demo ===\n")

    # Task 1: No dependencies
    t1 = scheduler.submit(
        "Fetch Data",
        lambda: (time.sleep(0.1), "data_fetched")[1],
        priority=Priority.HIGH
    )

    # Task 2: No dependencies
    t2 = scheduler.submit(
        "Load Config",
        lambda: (time.sleep(0.05), {"db": "localhost"})[1],
        priority=Priority.CRITICAL
    )

    # Task 3: Depends on Task 1 and Task 2
    t3 = scheduler.submit(
        "Process Data",
        lambda: (time.sleep(0.1), "processed")[1],
        priority=Priority.HIGH,
        dependencies={t1, t2}
    )

    # Task 4: Depends on Task 3
    t4 = scheduler.submit(
        "Generate Report",
        lambda: (time.sleep(0.05), "report.pdf")[1],
        priority=Priority.MEDIUM,
        dependencies={t3}
    )

    # Task with retry
    attempt = [0]
    def flaky_task():
        attempt[0] += 1
        if attempt[0] < 3:
            raise RuntimeError(f"Attempt {attempt[0]} failed")
        return "success after retries"

    t5 = scheduler.submit(
        "Flaky API Call",
        flaky_task,
        priority=Priority.LOW,
        max_retries=3
    )

    # Wait for completion
    time.sleep(3)
    scheduler.display()
    scheduler.shutdown()


if __name__ == "__main__":
    main()
```

## Key Design Decisions

1. **Priority Queue (Min-Heap)**: Tasks ordered by (-priority, scheduled_at). Higher priority first, then earliest scheduled.

2. **Dependency Graph**: Directed graph with cycle detection using DFS. Tasks only enter the queue when all dependencies are met.

3. **Retry with Exponential Backoff**: Failed tasks re-schedule with `2^retry_count` seconds delay.

4. **Thread Pool**: Multiple worker threads pull from the shared priority queue.

## Interview Follow-ups

1. **"How would you handle cron-like recurring tasks?"**
   → Add `RecurrenceRule` (cron expression), re-submit after completion

2. **"How would you persist task state across restarts?"**
   → Store tasks in database, recover on startup

3. **"How would you distribute across multiple machines?"**
   → Central task queue (Redis/RabbitMP), workers pull from queue

4. **"How would you add task timeouts?"**
   → Use `Future.get(timeout)`, cancel on timeout

5. **"How would you implement work stealing?"**
   → Each worker has its own deque, steal from others when idle
