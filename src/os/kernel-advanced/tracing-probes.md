# Tracing & Probes — Deep Internals

## Overview

This chapter goes beyond the [tracing overview](../kernel/tracing.md) into the **kernel-internal implementation** of each probe mechanism. Understanding the instruction-level mechanics of kprobes, the perf_event PMU abstraction, and BPF trampolines is what separates kernel developers from users of tracing tools.

## kprobes — Instruction-Level Mechanics

### Registration and Instruction Patching

When `register_kprobe()` is called (`kernel/kprobes.c`):

```c
// Simplified from kernel/kprobes.c
int register_kprobe(struct kprobe *p)
{
    // 1. Check the target address is valid (not in __kprobes blacklist,
    //    not in .init.text that was freed, not in IRQ entry text)
    // 2. Pre-allocate a kprobe_insn_page (executable page for saved insn)
    // 3. arch_prepare_kprobe():
    //    - Save the original instruction byte(s) at the probe address
    //    - Analyze instruction to determine its length and if it's safe to probe
    //    - Copy to the 'ainsn.insn' slot (out-of-line execution buffer)
    // 4. arm_kprobe():
    //    - If optimized: try to enable jump optimization (see below)
    //    - Else: patch the target address with BREAKPOINT_INSTRUCTION (INT3 on x86)
    //      text_poke_bp() uses stop_machine() or INT3 text_poke for safety
}
```

### x86_64: INT3 Trap Path

When the probed instruction executes, the CPU generates a **debug exception (#DB)**:

```text
CPU executes INT3 at probe site
  → #DB exception → entry_INT3_compat / entry_INT3 (arch/x86/entry/entry_64.S)
    → idtentry_exc debug do_debug
      → do_debug() → kprobe_debug_handler()
        → get_kprobe() — lookup kprobe by faulting address
          → kprobe_handler()
            → kcb->kprobe_status = KPROBE_HIT_ACTIVE
            → call pre_handler(kp, regs)
            → single-step: enable TF (trap flag) in regs->flags
              → CPU single-steps the original instruction (from out-of-line copy)
              → #DB again → post_xol_handler()
                → call post_handler(kp, regs, kcb->flags)
                → restore original instruction flow
```

### Jump Optimization

If the function prologue has a 5-byte relative CALL or JMP at the probe site, kprobes can replace it with a **direct jump to a detour buffer** instead of INT3:

```text
Unoptimized:
  func:  call __fentry__     ; 5-byte CALL
         <probed insn>      ; INT3 patched here → trap → ~0.5µs

Optimized (agente optimization, kernel/kprobes.c:opt_probe()):
  func:  jmp [detour_addr]  ; 5-byte JMP replaces the 5-byte CALL
                             ; direct branch, no trap → ~0.05µs
  detour:
         call __fentry__     ; saved original CALL
         jmp back_to_func+5  ; continue after probed instruction
```

The optimization uses `text_poke_bp()` to safely patch the instruction while other CPUs might be executing it. A `stop_machine()`-free approach was added in Linux 5.x using INT3-based text patching.

### kretprobe — Return Address Replacement

```c
// kernel/kprobes.c:register_kretprobe()
// 1. Register a kprobe at function entry (pre_handler = pre_handler_kretprobe)
// 2. pre_handler replaces return address on the stack:
//    saved = *regs->sp;    // original return address
//    *regs->sp = trampoline; // kretprobe_trampoline address
//    store (ri, saved) in a per-instance kretprobe_instance
//
// When function returns, CPU pops trampoline address:
//   kretprobe_trampoline:
//     - Look up kretprobe_instance by current stack frame
//     - Call rp->handler(rp, regs) with original return value
//     - Return to saved original return address
//
// maxactive: max concurrent instances (default = max(10, 2*num_possible_cpus))
// If exceeded, nmissed++ and handler is NOT called
```

> **Interview Angle**: "Why does kretprobe have a `maxactive` and what happens when it's exceeded?" Because every in-flight call needs a `kretprobe_instance` to store the original return address. If a function is called reentrantly or from many CPUs simultaneously, you run out. Exceeding it means the return is silently not traced (`nmissed` increments).

## uprobes — User-Space Probes

uprobes work analogously to kprobes but target **user-space addresses**:

```c
// kernel/events/uprobes.c
// Registration: uprobe_register(inode, offset, consumer)
// Internals:
// 1. Insert a XOL (execute-out-of-line) breakpoint in the user page
//    via install_breakpoint() → set_bit in a per-mm xol_area VMA
// 2. On #DB in user space, the kernel's page fault / debug handler
//    checks if it's a uprobe breakpoint via find_active_uprobe()
// 3. Single-step the original instruction from a copy in the xol VMA
// 4. Call consumer->handler() with pt_regs
```

Key difference from kprobes: uprobes must handle **page faults on the xol page**, **fork/COW semantics** (child inherits uprobes via dup_mmap), and **mremap/munmap** (uprobes must be removed when the mapping goes away). The xol VMA is a special mapping inserted into the process's address space at a random address (ASLR) that holds copies of the probed instructions for single-stepping.

## tracepoints — Static Instrumentation Internals

### Macro Expansion

```c
// include/trace/events/sched.h
TRACE_EVENT(sched_switch,

    TP_PROTO(struct task_struct *prev,
             struct task_struct *next),

    TP_ARGS(prev, next),

    TP_STRUCT__entry(
        __array(  char,  prev_comm,   TASK_COMM_LEN)
        __field( pid_t, prev_pid,              )
        __array(  char,  next_comm,   TASK_COMM_LEN)
        __field( pid_t, next_pid,              )
        __field( int,   prev_state,            )
    ),

    TP_fast_assign(
        memcpy(__entry->prev_comm, prev->comm, TASK_COMM_LEN);
        __entry->prev_pid   = prev->pid;
        memcpy(__entry->next_comm, next->comm, TASK_COMM_LEN);
        __entry->next_pid   = next->pid;
        __entry->prev_state = __get_task_state(prev);
    ),

    TP_printk("prev_comm=%s prev_pid=%d prev_state=%s ==> next_comm=%s next_pid=%d",
              __entry->prev_comm, __entry->prev_pid,
              __print_symbolic(__entry->prev_state,
                { 0, "R" }, { 1, "S" }, { 2, "D" }, ...),
              __entry->next_comm, __entry->next_pid)
);
```

This macro generates:
1. A **probe function** that calls `TP_fast_assign` to fill a ring-buffer entry.
2. A **tracepoint call site** in the kernel code (`trace_sched_switch(prev, next)`).
3. A **format string** exported to tracefs for user-space tools.

### Static Keys — Zero-Cost When Disabled

```c
// The generated call site uses a static_key (jump label):
// When disabled: the tracepoint compiles to a NOP (5-byte JMP +0)
// When enabled: patched to JMP <probe_function>

// kernel/jump_label.c
// Enabled via: static_key_enable(&key) → text_poke_bp()
// This is why disabled tracepoints have ~0 overhead
```

## perf_events — PMU Abstraction

### Architecture

```text
perf_event_open() syscall
  → perf_event_alloc()
    → find_pmu_context() — find the right PMU:
      • cpu (hardware counters: cycles, instructions, cache-misses)
      • software (cpu-clock, task-clock, context-switches)
      • tracepoint (static kernel tracepoints)
      • kprobe / uprobe (dynamic)
      • bpf (BPF program attachment)
    → event->pmu->event_init(event) — PMU-specific init
    → perf_install_in_context() — add to per-CPU context
    → if sampling: allocates perf_buffer (ring buffer for samples)
```

### Hardware PMU and NMI

On x86, the **Local APIC** has a Performance Monitoring Unit (PMU) with a fixed number of counters (typically 4 fixed + 8 general-purpose on modern CPUs). When a counter overflows:

1. PMU generates a **NMI (Non-Maskable Interrupt)**.
2. NMI handler (`arch/x86/events/core.c:perf_event_nmi_handler`) reads the counter, records a sample (IP, time, tid, regs).
3. Sample is written to the **perf ring buffer** (shared with user space via mmap).
4. User space reads samples via `perf record` or direct mmap read.

```c
// Reading perf samples from user space:
struct perf_event_mmap_page *meta = mmap(NULL, page_size, PROT_READ, MAP_SHARED, fd, 0);
void *data_buf = mmap(NULL, data_size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, page_size);
// meta->data_head is atomically updated by the kernel
// meta->data_tail is updated by the reader
// Ring buffer layout: struct perf_event_header + sample data
```

> **Interview Angle**: "Why does perf use NMI instead of normal IRQs?" NMIs cannot be masked by `cli`/`sti`, so even if the kernel is in a critical section with interrupts disabled, profiling still works. This ensures accurate call graph capture without bias toward code running with interrupts enabled.

## BPF Trampolines

BPF trampolines (`kernel/bpf/trampoline.c`) are the modern replacement for kprobes for function entry/exit tracing:

```text
// Target function:
func:
  call __fentry__     ; NOP or CALL to trampoline
  <function body>
  ret

// When BPF fentry/fexit programs are attached:
__fentry__:
  ; Trampoline generated at runtime:
  push rbp
  mov rbp, rsp
  ; Save argument registers (rdi, rsi, rdx, rcx, r8, r9)
  ; Call each BPF program (up to BPF_MAX_TRAMP_PROGS)
  ; Restore argument registers (may be modified by BPF programs for fmod_ret)
  ; Jump back to func+5 (after the CALL instruction)
```

### Trampoline vs kprobe

| Aspect | BPF Trampoline (fentry) | kprobe |
|--------|------------------------|--------|
| Mechanism | CALL to trampoline (replacing `__fentry__` NOP) | INT3 breakpoint or JMP optimization |
| Overhead | ~10 ns (direct call) | 50-500 ns (trap or JMP) |
| Argument access | Typed via BTF — direct register access | Manual `PT_REGS_PARM1()` macro, no type info |
| Return value | Directly available (fexit) | kretprobe trampoline needed |
| Kernel modification | Patches `__fentry__` call site | Patches target instruction |
| Limitations | Only functions compiled with `-mfentry` (x86) or with BTF | Almost any instruction address |

The trampoline is generated by `arch_prepare_bpf_trampoline()` which emits native x86_64 machine code at runtime into an executable page. The BPF verifier checks that attached programs only call allowed helpers and access arguments via BTF-defined types.

## Comparison Table

| Mechanism | Type | Overhead (per hit) | Stability | Access to args | Kernel source |
|-----------|------|--------------------|-----------|-----------------|---------------|
| tracepoint | Static | ~0 (disabled) / ~10-50 ns | Stable ABI | Typed fields | `include/trace/events/` |
| ftrace function | Static (compiler) | ~0.5 µs | Unstable | None (just function name) | `kernel/trace/ftrace.c` |
| kprobe | Dynamic | 50-500 ns | Unstable | Via PT_REGS | `kernel/kprobes.c` |
| kretprobe | Dynamic | 300-1000 ns | Unstable | Return value only | `kernel/kprobes.c` |
| uprobe | Dynamic | ~1-5 µs (page fault) | Unstable | Via PT_REGS | `kernel/events/uprobes.c` |
| perf_event (HW) | Hardware PMU | ~100-300 ns (NMI) | Stable (arch counters) | IP, regs | `kernel/events/core.c` |
| BPF fentry/fexit | BTF-based static | ~10-50 ns | Stable (BTF) | Typed via BTF | `kernel/bpf/trampoline.c` |

## Interview Questions

### Q: How does the kprobe jump optimization actually patch the instruction?

On x86_64, `text_poke_bp()` (arch/x86/kernel/alternative.c) uses INT3-based patching: it first writes INT3 at the target (atomically, so any CPU hitting it gets the trap), then writes the remaining bytes, then replaces INT3 with the final opcode. For a 5-byte jump optimization: the original 5-byte instruction is atomically replaced with a 5-byte JMP to the detour buffer.

### Q: Why can't you put a kprobe on every instruction?

Instructions in the `.entry.text` section (IRQ/exception entry), NMI handlers, and functions marked `NOKPROBE_SYMBOL()` are blacklisted. Also, probing mid-instruction is impossible — kprobes must be placed at instruction boundaries, and some instructions (AVX-512, variable-length) make boundary detection non-trivial.

### Q: What is the relationship between perf_events and ftrace?

`perf` uses the **ftrace infrastructure** for tracepoint and kprobe events. When you run `perf record -e sched:sched_switch`, perf opens a `perf_event` fd with PMU type `tracepoint`, which internally connects to the ftrace event subsystem. The event's `event->pmu->event_init()` calls into `tracepoint_probe_register()`.

## References

- `kernel/kprobes.c` — kprobe registration, optimization, handlers
- `kernel/events/uprobes.c` — uprobe implementation, XOL pages
- `kernel/trace/trace_events.c` — tracepoint registration and static keys
- `kernel/events/core.c` — perf_event core, PMU abstraction
- `kernel/bpf/trampoline.c` — BPF trampoline generation
- `arch/x86/kernel/alternative.c` — `text_poke_bp()`, instruction patching
- `Documentation/trace/kprobes.rst`, `Documentation/trace/uprobetracer.rst`

## Related Topics

- [Tracing Overview](../kernel/tracing.md) — ftrace interface, bpftrace, BCC
- [eBPF Deep Dive](./ebpf-deep.md) — verifier, BPF trampolines, fentry/fexit
- [Boot Process](./boot-process.md) — early boot tracing with earlycon
- [Advanced OS: Sync Primitives](../advanced/sync-primitives.md) — RCU used in trace buffer management
