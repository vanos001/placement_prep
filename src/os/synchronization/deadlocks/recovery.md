# Deadlock Recovery

## Overview

After deadlock detection, the system must **recover**. There are two main approaches: **process termination** (kill processes) and **resource preemption** (forcibly take resources). Both have costs that must be carefully managed.

## Recovery Strategies

### 1. Process Termination

#### Kill All Deadlocked Processes

```
Simple but drastic:
- Kill all processes in the deadlock set
- All deadlocked processes are eliminated
- Large amount of computation may be lost
```

#### Kill One Process at a Time

```
More selective:
- Kill one process, re-run detection
- Repeat until deadlock is broken
- Minimizes processes killed but adds detection overhead
```

#### Choosing Which Process to Kill

| Factor | Description |
|--------|-------------|
| **Priority** | Kill lowest-priority process |
| **Computation time** | Kill process with least work done |
| **Resources held** | Kill process holding most resources |
| **Resources needed** | Kill process needing most additional resources |
| **Remaining work** | Kill process farthest from completion |
| **Interactive vs batch** | Kill batch processes first |
| **Rollback cost** | Kill process with cheapest rollback |

### 2. Resource Preemption

Selecting a **victim** process to preempt:

```
Factors to consider:
1. Cost of rolling back the victim
2. Number of resources held by the victim
3. Remaining resources the victim needs
4. How long the victim has been running
```

#### Rollback Options

| Approach | Description |
|----------|-------------|
| **Total rollback** | Restart the process from scratch |
| **Partial rollback** | Roll back to a safe checkpoint |
| **Selective rollback** | Undo only the operations that caused deadlock |

### 3. Starvation Prevention

When selecting victims, the same process might be repeatedly killed (starvation):

```
Solution: Include age factor in victim selection
- Older processes (running longer) get higher priority
- A process that has been killed gets higher priority next time
- Use a counter: times_killed[i] — prefer killing processes with lower counts
```

## Recovery Algorithm

```
1. Detect deadlock (find deadlocked processes)
2. Select victim (based on factors above)
3. Preempt resources:
   a. Suspend the victim
   b. Roll back to checkpoint (if available)
   c. Release all resources held by victim
   d. Wake up processes waiting for these resources
4. Resume deadlocked processes (they retry their requests)
5. If deadlock persists, repeat from step 1
```

## Rollback Mechanisms

### Checkpointing

```
Process execution:
  [Start] → [CP1] → [CP2] → [CP3] → [Current]
  CP = checkpoint (save state)

On preemption: roll back to most recent checkpoint
```

### Save Points (Database Style)

```sql
SAVEPOINT sp1;
-- Operations
SAVEPOINT sp2;
-- More operations
ROLLBACK TO sp1;  -- Undo everything after sp1
```

## Comparison of Recovery Methods

| Method | Overhead | Data Loss | Starvation Risk | Complexity |
|--------|----------|-----------|-----------------|------------|
| Kill all | Low | High | None | Low |
| Kill one at a time | Medium | Medium | Medium | Medium |
| Resource preemption | High | Low | High | High |
| Checkpoint rollback | Medium | Low | Low | High |

## Interview Questions

**Q1: What are the main approaches to deadlock recovery?**

Two main approaches: (1) Process termination — kill all deadlocked processes or kill them one at a time until deadlock is resolved. (2) Resource preemption — forcibly take resources from a victim process and roll it back. Both require careful victim selection to minimize cost and prevent starvation.

**Q2: How do you select a victim process for termination or preemption?**

Consider: process priority, computation time invested, resources held, resources still needed, remaining work, rollback cost, and how many times the process has been a victim. Prefer killing low-priority, batch processes that hold many resources but have little work invested.

**Q3: What is the starvation problem in deadlock recovery?**

If the same process is repeatedly selected as a victim, it may never complete. Solution: track how many times each process has been killed and factor this into victim selection. A process that has been killed many times should get higher priority to avoid being killed again.

**Q4: What is the difference between total and partial rollback?**

Total rollback restarts the process from scratch — simple but wasteful. Partial rollback rolls back to a checkpoint — less work lost but requires checkpointing infrastructure. Database systems use savepoints for fine-grained rollback of transactions.

**Q5: Why might it be better to prevent deadlocks than to detect and recover?**

Prevention (resource ordering) has zero runtime overhead. Detection + recovery has overhead for running the detection algorithm, and recovery costs (killing processes, rolling back) can be significant. Prevention is also more predictable — no surprise process kills.

## Common Mistakes

- Not considering starvation in victim selection
- Killing processes without proper cleanup (resource leaks)
- Not handling the case where recovery itself causes new deadlocks
- Forgetting to wake up processes waiting for preempted resources
- Not having checkpointing infrastructure when using rollback

## Summary

- Recovery: kill processes or preempt resources
- Victim selection: minimize cost (priority, computation, resources, rollback)
- Starvation prevention: track kill count, factor into selection
- Rollback: total (restart) or partial (to checkpoint)
- Prevention is usually preferred over detection + recovery

## Cross-References

- [Deadlock Detection](detection.md) — finding deadlocks
- [Deadlock Prevention](prevention.md) — preventing deadlocks by design
- [Deadlock Avoidance](avoidance.md) — Banker's algorithm
- [Banker's Algorithm](bankers.md) — safe state verification


## Cross References

- [Deadlock Detection](detection.md)
- [Process Termination](../../processes/states.md)
- [Transaction Recovery](../../../dbms/transactions/recovery.md)
