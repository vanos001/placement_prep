# Follow-up Tree: Process Lifecycle

## Overview

"What happens when you run ./a.out?" is the systems opener that scales from a shell command to an interview about loaders, schedulers, and containers. It is beloved by infrastructure teams because every rung is *verifiable on a live machine* — the candidate who has run `strace`, read `/proc`, or debugged a zombie knows things the candidate who memorized a diagram does not. This page walks the ladder: what each follow-up tests, how to reason about it, and the answer with its edge cases. The opener also composes with this project's other chains: the memory-layout rung hands off to [Virtual Memory](./virtual-memory.md), and the container rung inherits the isolation analysis of [Processes Are Fully Isolated](../misconceptions/process-full-isolation.md).

## The Opening Question

**"What happens when you run ./a.out?"**

The expected core answer: the shell calls `fork()` to create a child process, and the child calls `execve("./a.out", argv, envp)` ([execve(2)](https://man7.org/linux/man-pages/man2/execve.2.html)). The kernel validates and parses the executable's ELF headers, maps its segments (text, data) into a fresh address space, sets up the stack with `argv`, `envp`, and the *auxiliary vector*, and — for a dynamically linked binary — maps the *dynamic linker* named in the `PT_INTERP` segment (`/lib64/ld-linux-x86-64.so.2`) and starts *it* instead of the program. The linker loads required shared libraries, applies relocations, and only then jumps to the program's entry point, which runs the C runtime startup and eventually `main`. Meanwhile the shell's parent continues: it typically `wait()`s for the child's exit status.

Why this answer is correct: it names the two-syscall structure — and the *reason* for it. fork+exec is deliberately two operations so that arbitrary state can be arranged in the child *between* them: redirected file descriptors, pipes, closed handles. A single spawn-with-arguments primitive (which Windows CreateProcess approximates) would need option flags for everything shells compose freely; the composability of the Unix shell falls out of this split. Naming the dynamic linker unprompted is the detail that tells the interviewer you have actually traced a process, not just drawn it.

## Follow-up 1: Why fork *and* exec — and What Does the Loader Actually Do?

**What it tests:** whether you can defend a 40-year-old API decision and describe the loader's work at the level of pages and relocations.

**How to reason:** treat fork+exec as an API that maximizes composition, then walk exec's work in order: identity, address space, libraries, entry.

**Answer.** Fork duplicates the calling process (modern kernels use copy-on-write, so pages are shared read-only and copied on first write — the "fork cost" is mostly page-table work, not memory); exec then *replaces* the child's program. Between the two, the shell does the composable work: opening the input file for `<`, creating the pipe for `|`, setting the environment. [fork(2)](https://man7.org/linux/man-pages/man2/fork.2.html) is the primitive; the kernel does the COW accounting. Variants exist for good reasons: `vfork` avoided page-table copies historically, and `posix_spawn` composes fork+exec+file-actions in one call — the choice libraries make when fork's cost matters on large address spaces.

The loader's work, in order: the kernel maps the ELF's `PT_LOAD` segments with the right permissions (the text segment read-execute, data read-write), maps the interpreter from `PT_INTERP`, and builds the auxiliary vector; the dynamic linker then locates libraries along its search path (`LD_LIBRARY_PATH`, then default directories — the search-order rules are in [ld.so(8)](https://man7.org/linux/man-pages/man8/ld.so.8.html)), maps them, applies relocations (patching addresses the compiler could not know), and registers lazy binding so unresolved function calls go through the PLT/GOT and are resolved on first call. The trade to volunteer: dynamic linking costs startup work and adds a dependency-resolution step that can fail at runtime, in exchange for sharing library text across processes and security patching without relinking; static linking inverts everything and is why statically linked binaries dominate containers and security-critical tools. [Drepper, "How to Write Shared Libraries"](https://www.akkadia.org/drepper/dsohowto.pdf) remains the canonical treatment of what this rung's questions cost at runtime.

## Follow-up 2: Draw the Process's Memory Layout — Why Does It Look Like That?

**What it tests:** whether the address space is a mental model or a picture — and whether you can connect it to the machinery in this project's virtual-memory chain.

**How to reason:** the layout is the residue of exec's mapping decisions, plus the growth policy of the two dynamic regions. Each region exists because a different allocator or mapping policy owns it.

**Answer.** From low addresses up: text (program code, read-execute), data (initialized globals), BSS (zero-initialized globals, mapped lazily as zero pages — the kernel does not store zeros in the file), then the **heap**, which grows upward under the allocator's control (`brk`/`mmap` — the C allocator requests large chunks from the kernel and sub-allocates), then the sparse **mmap region** (shared libraries, file mappings, large allocations), and at the top the **stack**, growing downward, with the environment and argv above it. **ASLR** randomizes the stack, mmap base, and (with PIE) the executable's own base — every "why is this address the same across runs" debugging surprise is ASLR being disabled or not. The two growth regions face each other with a gap precisely because neither the allocator nor the kernel can predict their final size; the layout is a compromise between growth direction, protection boundaries, and the page-granular mapping underneath — the translation machinery that makes all of it possible is [Virtual Memory](./virtual-memory.md), and the kernel-side catalogue is [OS Virtual Memory](../../os/virtual-memory/README.md). The security edge case worth volunteering: this layout is the modern descendant of the buffer-overflow era — stack growing down toward unmapped guard regions, non-executable stacks, and ASLR each exist because the original flat layout made "overwrite a return pointer" a reproducible attack.

## Follow-up 3: What Does a Context Switch Cost, Really?

**What it tests:** the difference between the textbook number (register save/restore) and the production number (cache and TLB pollution), which is a favorite seniority probe.

**How to reason:** split the cost into *direct* work the scheduler does and *indirect* work the next task pays because its working set left the caches.

**Answer.** Direct cost: saving the old task's registers and kernel state, choosing the next task, restoring the new one, switching address spaces (loading page-table base, flushing or tagged-flushing the TLB) — order of a microsecond, measurable, and *not* the interesting part. Indirect cost: the new task's first accesses miss L1/L2 and TLB because the previous task evicted them; with per-core caches and cold TLB entries, the effective cost is workload-dependent and can reach tens of microseconds of degraded throughput before the caches re-warm. The numbers are famously workload-specific — which is the point: an honest answer says "microseconds direct, indirect cost depends on working-set overlap and TLB behavior," and refuses to recite a single figure. Two related distinctions complete the rung: a *syscall* is not a context switch (the address space stays; only the privilege level changes — far cheaper), and a switch between *threads* of one process skips the address-space switch entirely, which is one honest reason threads are cheaper than processes. The scheduler's own logic — which queue the task lands in, what preemption costs — is the next chain outward: [Context Switching](../../os/processes/context-switching.md) for the mechanism, [OS Scheduling](../../os/scheduling/README.md) for the policy, and [Scheduling and Queueing](../connection-atlas/scheduling-queueing.md) for the queueing-theory view of what load does to all of it.

## Follow-up 4: What Is a Zombie? What Is an Orphan? Which One Is a Bug?

**What it tests:** whether you know the exit protocol — status delivery, reparenting — well enough to distinguish designed behavior from a defect.

**How to reason:** zombies and orphans are both states in the lifecycle, not anomalies. The bug question is about *who fails to do their part*.

**Answer.** A **zombie** is a terminated process that has exited but whose parent has not yet `wait()`ed: the kernel keeps the process-table entry holding the exit status (and rusage) because delivering that status is the parent's contract, and something must hold it until claimed. The parent receives `SIGCHLD` as notification. A zombie in `ps` is therefore *normal* for as long as it takes the parent to reap; a *persistent* zombie is a parent bug — it exited its loop without waiting, and the fix is `wait`/`waitpid` (or `SIG_IGN` for SIGCHLD, or `WNOHANG` polling, depending on the design). An **orphan** is a live process whose parent died first: the kernel reparents it to init (or the nearest *subreaper*), and when the orphan exits, its new parent reaps it — so orphans self-resolve, and daemonization (the double-fork trick) *deliberately* orphans a child to detach it from the session. The interview trap is the asymmetry: zombies leak process-table slots (hundreds of thousands of un-reaped children can exhaust `pid_max`), while orphans do not — so "which one is a bug" is answered by *who owes the wait*. The full state machine and the daemon pattern live in [Zombies and Orphans](../../os/processes/zombie-orphan.md).

## Follow-up 5: How Do Signals Work — and Why Are They a Poor RPC Mechanism?

**What it tests:** whether you model signals as what they are — asynchronous interruptions at arbitrary points — and can name the resulting programming hazards.

**How to reason:** a signal is delivered *between* instructions, in the context of the receiving process, with a handler that must compose with whatever the interrupted code was doing.

**Answer.** [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html) semantics: a signal is generated (by a fault, a terminal event, or [kill(2)](https://man7.org/linux/man-pages/man2/kill.2.html)), *pending* until delivered, and delivered either to a handler or to its default action (terminate, terminate+core, ignore, stop). Two signals — SIGKILL and SIGSTOP — cannot be caught, blocked, or ignored, by design: they are the kernel's reserved escape hatch, the answer to "how do you kill a process whose handler is broken." Standard signals are *not queued* (three identical pending signals coalesce into one); real-time signals (SIGRTMIN..SIGRTMAX) are queued and ordered — the detail that answers "what if I send the same signal twice?" The programming hazards are the reason the rung is hard: handlers run asynchronously at *any* instruction boundary, so they may only call async-signal-safe functions (no malloc, no stdio — the interrupted thread might be *inside* malloc holding the allocator lock), and the mainline code must mask signals around non-reentrant regions. This is why signals are a poor RPC: no payload beyond a number, no queueing (standard signals), no delivery guarantees under masking, and handlers that cannot safely share state with the mainline — the production-grade replacements are event loops (`signalfd` turns a signal into a pollable descriptor), self-pipes, and message channels. The conceptual framing that earns credit: signals are the software analogue of hardware interrupts — the same "handle it now, at an arbitrary point, with a restricted handler" contract, at process granularity — and the connection is developed in [Interrupts and Asynchrony](../connection-atlas/interrupts-async.md); the repo's signal mechanics live in [IPC: Signals](../../os/processes/ipc-signals.md).

## Follow-up 6: Now Run It in a Container — What Actually Changed?

**What it tests:** whether "container" is a word or a mechanism: namespaces, cgroups, and the honesty to say what isolation is *not*.

**How to reason:** split the question into what the process can *see* (namespaces) and what it may *consume* (cgroups), then ask what is still shared with the host.

**Answer.** Nothing about fork/exec changes; the runtime adds two wrappers around the same process. **Namespaces** virtualize the *view*: PID namespace (the container's init is PID 1 *in its namespace*), mount namespace (its own filesystem root — the image), network namespace (its own interfaces and routes), UTS, IPC, user, and cgroup namespaces — the catalogue and clone-flags live in [Namespaces](../../os/containers/namespaces.md). **Cgroups** (v2 semantics in [cgroups(7)](https://man7.org/linux/man-pages/man7/cgroups.7.html) and [Linux Cgroups v2](../../linux/containers/cgroups-v2.md)) cap the *consumption*: CPU weight/quota, memory limits, I/O — and a memory-cgroup breach triggers the OOM killer *within* the cgroup, which is why container OOMs look like abrupt SIGKILLs with healthy application logs. The rung's senior content is what is *still shared*: the kernel (a container syscall bug is a host syscall bug; there is one kernel version for all containers on a host), the page cache, and the scheduler — processes in containers are ordinary processes to the kernel, just with restricted views and budgets. That is precisely the gap between a container and a VM, documented as the sibling misconception [Containers Are VMs](../misconceptions/containers-are-vms.md); and the reason `ps` on the host sees everything is the same reason cgroup pressure signals work — visibility is a namespace property, not a physical one.

## How to Approach Unfamiliar Variations

The transferable template for "what happens when you run X" questions:

1. **Anchor on the two-syscall skeleton, then vary one stage.** Every variant — running a script (the interpreter is the exec'd binary and the script is an argument), a static binary (no PT_INTERP rung), a container image (namespace/cgroup wrapper), a setuid program (permission transition at exec) — changes exactly one stage of the same pipeline. Name the pipeline, then name the changed stage.
2. **Wherever state is created, ask who owns and reaps it.** File descriptors, children, memory mappings, signal dispositions — each has a lifecycle owner and a release contract; the zombie rung, the fd-leak question, and the daemonization twist are all that question in different clothes.
3. **Separate what a mechanism charges *now* from what it charges *later*.** fork charges page tables now and COW faults later; dynamic linking charges startup now and relocation-indirection later; a context switch charges registers now and cache warmth later. "Now vs later" turns vague trade-off talk into an inspectable claim.
4. **When the question crosses into containers or security, say what is shared.** Isolation questions are answered by enumerating the kernel resources that are *still common* — one kernel, one page cache, one scheduler — and only then by the walls.

## Interview Questions

**Q: A statically linked binary and a dynamically linked one start in 3 ms vs 25 ms. Where do the 22 ms go?**
A: Dynamic-linking startup: mapping ld.so and the shared libraries, resolving relocations, and lazy-binding setup — plus extra page faults for library text not yet resident. Mitigations in order: prelink or link-time tuning, reducing library dependencies, or static linking where the sharing benefit is absent (containers). The 22 ms is *per process start*, which is why CLI tools and per-request process spawns feel it and long-running daemons do not.

**Q: Your service spawns thousands of short-lived helper processes and eventually hits EAGAIN on fork. Diagnosis?**
A: Zombie accumulation: the spawner is not reaping (no `wait`, and SIGCHLD handling that does not loop because standard signals coalesce). Fix the reap loop (`waitpid` with `WNOHANG` until ECHILD, or SIGCHLD → self-pipe → wait loop). The diagnosis matters because the same symptom can be a real PID-limit leak elsewhere; `/proc` inspection of zombie states settles it.

**Q: Why does a signal handler that calls `printf` sometimes deadlock?**
A: The signal can be delivered while the interrupted thread is already inside `printf` holding its internal lock; the handler's `printf` re-enters the same non-reentrant code and waits for a lock the interrupted thread will never release (handlers cannot run until the mainline returns). Handlers must restrict themselves to async-signal-safe calls, or better, set a flag/write to a self-pipe and let the main loop do the printing.

**Q: A containerized process is killed with SIGKILL, application logs are clean, and exit code is 137. What happened and what do you check?**
A: 137 = 128+9: SIGKILL from outside the process — with clean logs, the top suspect is the cgroup memory limit triggering the OOM killer (check the OOM events and memory.high/pressure), next a `docker stop` timeout or an orchestrator liveness kill. The application was healthy in its own view; the budget was not. The fix is right-sizing plus memory-aware application behavior, not a bigger restart counter.

## Key Takeaways

- Running a program is fork + execve: two syscalls by design, so the shell can compose arbitrary child state between them — the loader then maps segments, applies relocations, and hands control over via the dynamic linker.
- The address-space layout is the residue of exec's mapping decisions plus two growth regions (heap up, stack down) meeting in a gap; ASLR and W^X exist because the original layout made exploits reproducible.
- Context switch cost is microseconds of direct work plus workload-dependent indirect cost from cache and TLB cooling — and a syscall is not a context switch.
- Zombies are unreaped exit statuses (a parent contract), orphans are reparented and self-resolving — only one of them is a bug, and it is the parent's.
- Signals are asynchronous interrupts with a restricted handler contract: coalescing, masking, and async-signal-safety are the system's way of saying "do not do real work here."
- Containers wrap the same fork/exec with namespaces (what you see) and cgroups (what you may use) — while one kernel, one page cache, and one scheduler remain shared.

## Cross-References

- [Virtual Memory](./virtual-memory.md) — the translation machinery beneath every address in the layout rung.
- [OS Overview](../../os/overview.md) — the repo's systems hub for everything this chain touches.
- [Process Creation](../../os/processes/creation.md) — fork, exec, and the clone-flags family in depth.
- [Zombies and Orphans](../../os/processes/zombie-orphan.md) — the full exit/reparenting state machine and daemonization.
- [IPC: Signals](../../os/processes/ipc-signals.md) — signal mechanics, masks, and delivery details.
- [Context Switching](../../os/processes/context-switching.md) — the direct/indirect cost model of rung 3, measured.
- [OS Scheduling](../../os/scheduling/README.md) — the policy layer that decides who switches and when.
- [OS Virtual Memory](../../os/virtual-memory/README.md) — demand paging and the page-fault costs of the loader's mappings.
- [Namespaces](../../os/containers/namespaces.md) — the view-virtualization half of the container rung.
- [Linux Cgroups v2](../../linux/containers/cgroups-v2.md) — the budget half, with the OOM-within-cgroup mechanics.
- [clone(2)](../../linux/syscalls/process/clone.md) — the syscall beneath fork and thread creation.
- [Scheduling and Queueing](../connection-atlas/scheduling-queueing.md) — what load does to the scheduler's queues.
- [Interrupts and Asynchrony](../connection-atlas/interrupts-async.md) — the hardware analogue of the signal contract.
- [Processes Are Fully Isolated](../misconceptions/process-full-isolation.md) — what processes do and do not share, as a documented misconception.
- [Containers Are VMs](../misconceptions/containers-are-vms.md) — the container rung's misconception, claim by claim.
- [execve(2)](https://man7.org/linux/man-pages/man2/execve.2.html), [fork(2)](https://man7.org/linux/man-pages/man2/fork.2.html), [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html), [cgroups(7)](https://man7.org/linux/man-pages/man7/cgroups.7.html), [ld.so(8)](https://man7.org/linux/man-pages/man8/ld.so.8.html) — the primary man-page sources for this chain's syscall semantics.
