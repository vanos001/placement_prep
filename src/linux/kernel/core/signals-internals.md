# Signal Delivery Internals: Queues, Restarts, and the Path into a Handler

Two other pages in this book cover signals from other angles: [Signals in Linux](../processes/signals.md) walks the `task_struct` fields and the standard signal table, and [Signals](../../sysprog/signals.md) covers the programming interface — `sigaction()`, async-signal-safety, `sigwait()` threads. This page is the mechanism-level deep dive: what the kernel does *between* `kill()` in one process and the first instruction of a handler in another. It follows one signal through the pending sets, the thread-selection decision, the dequeue loop, the interrupted-syscall restart machinery, and the frame the handler wakes up on. Topics that only make sense at that depth — real-time queue overflow, `pselect`/`signalfd` race-freedom, `SA_ONSTACK`, seccomp's `SIGSYS`, and why high-rate signals are a pathology — live here.

## 1. Two pending sets and a budget

Every thread carries a `struct sigpending pending` (thread-directed), and the process-wide `signal_struct` carries `shared_pending` (process-directed). Both are the same shape: a `sigset_t` bitmask plus a list of queued `sigqueue` nodes holding a `kernel_siginfo`.

```text
 task_struct (thread A)             signal_struct (process)
 +---------------------+            +---------------------------+
 | pending             |            | shared_pending            |
 |   .signal  bitmask  |            |   .signal  bitmask        |
 |   .list    [nodes]  |            |   .list    [nodes]        |
 | blocked   bitmask   |            +---------------------------+
 +---------------------+            consumed by ANY thread whose
   consumed only by thread A        blocked mask admits the signal
```

Routing is decided at send time:

- `kill(pid, sig)` lands on `shared_pending`; a process-directed signal is not owned by any thread yet. `complete_signal()` picks one eligible thread to deliver it (section 2).
- `tgkill(tgid, tid, sig)` and hardware faults land on the specific task's `pending`. Hardware faults (`SIGSEGV`, `SIGBUS`) are always thread-directed — the faulting thread is the only one that can handle them meaningfully.

Standard signals (1–31) never allocate a queue node: `__send_signal_locked()` takes the `legacy_queue()` path and merely sets the bit. Send it five times while it is undelivered and it is *coalesced* — one delivery. Real-time signals allocate a `sigqueue` node and are appended to `.list`, one node per send. Both classes set the same bitmask bit.

Node allocation is charged to the *user*, not the process: `__sigqueue_alloc()` bumps `user->sigpending` and fails once it reaches the per-user `RLIMIT_SIGPENDING` resource limit (documented in [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html)). One noisy user can therefore exhaust the signal budget for all of their processes. The failure mode depends on the caller: `sigqueue(3)` returns `-EAGAIN`, but kernel-internal senders may silently drop the signal — a queue-full real-time send is simply lost unless the sender checked.

## 2. Which thread gets it

For a process-directed signal, `complete_signal()` walks the thread group looking for a target via `wants_signal()`: a task qualifies if the signal is not in its `blocked` mask, it has not exited, it is not already stopping, and its disposition is not `SIG_IGN`. The scan prefers threads that are not blocked in the kernel over threads sleeping in `TASK_INTERRUPTIBLE`, and it will wake a sleeping eligible thread if none is running. If every thread blocks the signal, the bit just sits in `shared_pending` until some thread unmasks it. The practical consequences:

| Rule | Effect you can observe |
|---|---|
| `blocked` mask is per-thread | A process-directed signal may hit "any" thread; pin handling by masking it in all threads but one |
| Own `pending` drains before `shared_pending` | A thread's own `tgkill` signal outranks a `kill()` one already queued |
| Within one pending set, Linux delivers standard signals before queued real-time ones | `signal(7)` states Linux gives standard signals priority; since standard signals are 1–31 and real-time are 32–64, this coincides with lowest-number-first |
| Multiple real-time signals | Lowest number first; same number in FIFO send order |
| Multiple standard signals | Order unspecified by POSIX, coalesced by Linux |

`get_signal()` dequeues from `current->pending` first, then `signal->shared_pending` — so "lowest first" is only true *within* a set, a subtlety the demo in section 8 exhibits.

## 3. Disposition: the dequeue loop

Delivery happens at kernel exit points — return from a syscall, from an interrupt, or before resuming userspace — whenever the `TIF_SIGPENDING` flag is set on the task. The architecture code then calls into `get_signal()`, which loops:

1. Dequeue the lowest eligible signal from `pending`, else `shared_pending`.
2. If disposition is `SIG_IGN`, discard it and continue (this is why ignored signals never wake you).
3. If `SIG_DFL`, the kernel applies the default action itself — group terminate, group stop, continue — and loops; the signal never reaches userspace.
4. Otherwise a handler is installed: the pending `sigqueue` node becomes the `siginfo_t`, the `sa_mask` plus the signal itself (unless `SA_NODEFER`) are pushed onto the thread's `blocked` mask, and the architecture code builds the signal frame.

That frame is a userspace structure (`rt_sigframe` on x86-64) containing the saved register context (`ucontext_t`), the `siginfo_t`, and a return address pointing at a restorer trampoline that executes `rt_sigreturn`. Delivery is therefore two extra transitions of userspace/kernel boundary per signal, a fact that dominates section 8.

## 4. Interrupted syscalls and the four restart codes

When a blocking syscall is interrupted by signal delivery, the syscall implementation returns a private negative error — the restart code — which the syscall exit path consults *after* the handler question is settled. These codes never reach userspace as `errno`:

| Kernel code | Meaning | If `SA_RESTART` set | If not |
|---|---|---|---|
| `-ERESTARTSYS` | Generic interruptible wait | Restart the syscall | Return `-EINTR` |
| `-ERESTARTNOINTR` | No side effects yet | Always restart | Always restart |
| `-ERESTARTNOHAND` | Wait was for a signal | Return `-EINTR` (a handler exists) | Restart |
| `-ERESTART_RESTARTBLOCK` | Timed wait, deadline adjusted | Restart via `restart_syscall(2)` with recomputed timeout | Return `-EINTR` |

Three details worth knowing cold:

- Restart is not always "call the syscall again from the top." `-ERESTART_RESTARTBLOCK` re-enters through `restart_syscall(2)`, which rewinds to the blocked call with the *remaining* timeout, so a 5-second `clock_nanosleep` interrupted at 4.9s does not sleep another 5 seconds.
- Some interfaces are never restarted regardless of `SA_RESTART`. [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html) lists the file-descriptor multiplexing interfaces — `select(2)`, `pselect(2)`, `poll(2)`, `ppoll(2)`, `epoll_wait(2)`, `epoll_pwait(2)` — plus `pause(2)`, `sigsuspend(2)`, the `sigwait*()` family, SysV IPC waits, `nanosleep`/`clock_nanosleep`, and `io_getevents(2)`. Event loops must treat `EINTR` as a normal, expected wakeup, not an error.
- `SA_RESTART` is a property of the *receiving* disposition, chosen per signal number in `sigaction()`. One handler installed with `SA_RESTART` for `SIGUSR1` and one without for `SIGALRM` gives you restarts for the former and `EINTR` for the latter — from the same blocking call.

The restart codes are why a naive sleep-and-retry loop is wrong: `while (read(fd,...) == -1 && errno == EINTR) continue;` re-sleeps for the *full* original duration on timed waits instead of the remainder. Libraries wrap this correctly precisely because they know which restart code the kernel used.

## 5. Race-free waiting: pselect, ppoll, signalfd

The classic event-loop race: a signal can arrive *after* you check the flag but *before* you call `select()`, so `select()` sleeps through a signal that was already pending. The textbook pattern `sigprocmask(SIG_BLOCK,...); check; sigprocmask(SIG_UNBLOCK,...); select()` has an unblock-to-sleep window it cannot close.

The kernel closes it by making mask installation and sleeping one atomic step. `pselect6()` / `ppoll()` take a signal mask argument: the kernel installs the new mask, *then* tests readiness, then sleeps — the pending-signal check happens with the new mask already in force, so a signal arriving mid-call wakes the wait instead of slipping past it. On return the old mask is restored. The signal is then delivered (these calls are in the never-restarted list — by design, so you get the `EINTR` wakeup you asked for).

`signalfd(2)` converts signals into file-descriptor readiness: block the signals first (otherwise a conventional handler wins the race and the fd sees nothing), then `read()` a `signalfd_siginfo` — a fixed **128-byte** record whose fields mirror `siginfo_t`. Because the queue drains as plain reads, signals become one more fd in an [epoll](../../sysprog/epoll.md) set, [self-pipe tricks become obsolete](../../sysprog/poll-select.md), and one `epoll_wait` wakeup can drain *many* queued signals in a batch. The API-level usage patterns are covered in [poll vs select](../../sysprog/poll-select.md) and [event-driven programming](../../sysprog/event-driven.md); the kernel-side mechanism is exactly the same `sigpending` queue, consumed through a file operation instead of a frame on your stack.

## 6. The alternate signal stack and SA_ONSTACK

A handler for `SIGSEGV` that overflows its stack cannot run: the kernel would push a signal frame onto the very stack that just faulted. `sigaltstack()` registers a per-thread memory region; a handler installed with `SA_ONSTACK` gets its frame built on that region instead.

The sharp edges:

- The altstack is per-thread. Threads created after registration inherit it; threads created before do not — register it before spawning workers.
- While running on the altstack, `sigaltstack()` reports `SS_ONSTACK`; another `SA_ONSTACK` delivery reuses the same region and corrupts itself. Nesting is unsupported by design.
- `SS_AUTODISARM` (Linux 4.7) removes the altstack registration while the handler runs, so a fault inside the handler gets the kernel's raw default handling (typically a clean death) instead of recursive frame corruption.
- Since glibc 2.34, `SIGSTKSZ`/`MINSIGSTKSZ` are no longer compile-time constants — allocate at runtime. [sigaltstack(2)](https://man7.org/linux/man-pages/man2/sigaltstack.2.html) documents the constants and the flag semantics.

Sanitizer builds (`ASan`) and runtimes with guard pages make this mandatory, not optional: their internal fault reporting *is* a `SA_ONSTACK` handler.

## 7. SIGSYS: the signal seccomp fires

When a seccomp filter returns `SECCOMP_RET_TRAP`, the kernel does not run the syscall; it delivers `SIGSYS` to the *triggering thread*, with a distinctive `siginfo_t`: `si_signo == SIGSYS`, `si_code == SYS_SECCOMP`, plus `si_call_addr` (the instruction address of the offending syscall), `si_syscall` (its number), and `si_arch` ([seccomp_filter docs](https://docs.kernel.org/userspace-api/seccomp_filter.html)). `SECCOMP_RET_KILL_THREAD` kills the thread with exit status `SIGSYS`; `SECCOMP_RET_KILL_PROCESS` kills the whole group. Sandbox runtimes use the trap form to convert policy violations into catchable, loggable faults — [seccomp and sandboxing](https://lwn.net/Articles/332974/) traces the history of that design. The filter mechanics live in [kernel seccomp](../security/seccomp.md) and [seccomp-BPF](../../containers/seccomp-bpf.md); the user-facing wrappers in [seccomp programming](../../sysprog/seccomp.md). Note the asymmetry with section 2: `SIGSYS` from seccomp is thread-directed by construction — the violating thread is known — and it interacts badly with thread pools if your handler assumes the "main" thread fired it.

## 8. High-rate signals are a pathology

Per delivered signal the kernel pays: a `sigqueue` node (real-time), a frame build, a handler entry, and a `rt_sigreturn` syscall — at least two user/kernel crossings per event, plus whatever the handler does. Under a flood of standard signals, delivery collapses to one event per wakeup while senders coalesce; under a flood of real-time signals, the per-user budget (`RLIMIT_SIGPENDING`) exhausts and senders start taking `-EAGAIN` or silent drops. Either way the queue is the story: simulate it.

```python
#!/usr/bin/env python3
"""Simulate the kernel signal queue: standard vs real-time, task vs shared
pending sets, lowest-number-first dequeue, and RLIMIT_SIGPENDING overflow.
Pure stdlib, deterministic. Models kernel/signal.c behaviour, not the code."""

SIG_LIMIT = 64
RTMIN = 34

class SigQueue:
    """One pending set: a bitmask (dedupe for standard signals) plus an
    ordered list of queued siginfo nodes (real-time signals only)."""
    def __init__(self, label):
        self.label = label
        self.bits = set()          # pending signal numbers (set of bits)
        self.queue = []            # list of (signo, si_int) - queued nodes
        self.dropped = 0           # silently dropped (standard-signal coalescing)

    def send(self, signo, payload=None, user_budget=None):
        if signo < RTMIN:
            # legacy_queue(): one bit only - N sends collapse into one
            if signo in self.bits:
                self.dropped += 1
            self.bits.add(signo)
            return "bit-set"
        # real-time: must allocate a sigqueue node under the user's budget
        if user_budget is not None and user_budget <= 0:
            return "EAGAIN"        # __sigqueue_alloc() failed -> EAGAIN
        if user_budget is not None:
            user_budget -= 1
        self.queue.append((signo, payload))
        self.bits.add(signo)
        return "queued"

    def next_signal(self):
        """__next_signal(): scan bit 1..64, take the LOWEST pending number.
        Standard signals therefore outrank queued real-time ones."""
        for signo in sorted(self.bits):
            node = next(((n for n in self.queue if n[0] == signo)), None)
            self.bits.discard(signo)
            if node:
                self.queue.remove(node)
                return signo, f"dequeue node (si_int={node[1]})"
            return signo, "dequeue bit (no payload)"
        return None, "empty"

budget = 10                              # user->sigpending budget for RT nodes
shared = SigQueue("signal->shared_pending")   # process-directed
task_a = SigQueue("task A->pending")          # thread-directed
task_b = SigQueue("task B->pending")

print(f"RT queue budget (RLIMIT_SIGPENDING-style): {budget}")
print(f"-- flood phase: 14x SIGUSR1(10), 14x SIGRTMIN(={RTMIN}) --")
for _ in range(14):
    shared.send(10, user_budget=budget)          # standard: never allocates
    r2 = shared.send(RTMIN, payload=1, user_budget=budget)
    budget = max(budget - (r2 == "queued"), 0)
print(f"shared pending bits after flood : {sorted(shared.bits)}")
print(f"queued RT nodes still alive     : {len(shared.queue)} (each si_int=1)")
print(f"SIGUSR1 duplicates coalesced    : {shared.dropped} (bit stays set)")
print(f"RT sends rejected with EAGAIN   : {14 - len(shared.queue)} (budget hit 0)")

print("\n-- delivery round: each thread drains OWN pending set first,\n"
      "   lowest-numbered signal first within each set (next_signal()) --")
task_a.send(50, payload="A"); shared.send(2); task_b.send(RTMIN+1, payload="B")
for name, q in (("A", task_a), ("B", task_b)):
    s, how = q.next_signal()             # get_signal(): own set first...
    print(f"thread {name}: own   -> SIG{s} ({how})")
    s2, how2 = shared.next_signal()      # ...then shared (process-directed)
    print(f"thread {name}: shared-> SIG{s2 if s2 else '-'} ({how2})")

print("\n-- final pending state --")
for q in (shared, task_a, task_b):
    print(f"{q.label:28s} bits={sorted(q.bits)} queue={q.queue}")
```

Real output:

```text
RT queue budget (RLIMIT_SIGPENDING-style): 10
-- flood phase: 14x SIGUSR1(10), 14x SIGRTMIN(=34) --
shared pending bits after flood : [10, 34]
queued RT nodes still alive     : 10 (each si_int=1)
SIGUSR1 duplicates coalesced    : 13 (bit stays set)
RT sends rejected with EAGAIN   : 4 (budget hit 0)

-- delivery round: each thread drains OWN pending set first,
   lowest-numbered signal first within each set (next_signal()) --
thread A: own   -> SIG50 (dequeue node (si_int=A))
thread A: shared-> SIG2 (dequeue bit (no payload))
thread B: own   -> SIG35 (dequeue node (si_int=B))
thread B: shared-> SIG10 (dequeue bit (no payload))

-- final pending state --
signal->shared_pending       bits=[34] queue=[(34, 1), (34, 1), (34, 1), (34, 1), (34, 1), (34, 1), (34, 1), (34, 1), (34, 1), (34, 1)]
task A->pending              bits=[] queue=[]
task B->pending              bits=[] queue=[]
```

Read the transcript against the rules: 14 standard sends coalesce into one bit (13 dropped), 10 of 14 real-time sends fit the budget and the rest bounce with `EAGAIN`, thread A's thread-directed `SIG50` outranks the already-pending process-directed `SIG2` because own-sets drain first, and the shared set then hands out standard `SIG2` before the queued `SIG34` — standard priority in action. If your design needs per-event reliability at high rates, the queue is the wrong tool: batch through `signalfd` reads, or move to an eventfd/timerfd/pipe transport and keep signals for what they are for — death, stop/continue, and faults.

## References

- [signal(7) — signal overview, queuing, interruption and restart rules](https://man7.org/linux/man-pages/man7/signal.7.html)
- [sigaltstack(2) — alternate stack, SS_AUTODISARM, MINSIGSTKSZ](https://man7.org/linux/man-pages/man2/sigaltstack.2.html)
- [signalfd(2) — signals as fd readiness, signalfd_siginfo layout](https://man7.org/linux/man-pages/man2/signalfd.2.html)
- [select(2) — pselect6/ppoll semantics and the never-restart list](https://man7.org/linux/man-pages/man2/select.2.html)
- [seccomp user-space filter documentation — SECCOMP_RET_TRAP, SIGSYS siginfo](https://docs.kernel.org/userspace-api/seccomp_filter.html)
- [LWN: Seccomp and sandboxing](https://lwn.net/Articles/332974/)

## Related Topics

- [Signals in Linux](../processes/signals.md) — signal table, `task_struct` fields, `sigaction` structure
- [Signals (API level)](../../sysprog/signals.md) — handlers, async-signal-safety, `sigwait` threads
- [task_struct Deep Dive](../processes/task-struct.md) — `pending`, `blocked`, `sighand` fields
- [Hardware Exceptions](../interrupts/exceptions.md) — how page faults become thread-directed `SIGSEGV`
- [Kernel seccomp](../security/seccomp.md) — filter actions and their priority order
- [poll vs select](../../sysprog/poll-select.md) — `pselect`/`signalfd` usage patterns in event loops
- [Processes and Threads](../processes/processes-and-threads.md) — thread groups and shared state
