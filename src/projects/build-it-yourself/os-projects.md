# OS Build-It-Yourself Projects

## 1. Build a Minimal x86 Kernel

Write a kernel that boots from BIOS, sets up the GDT (Global Descriptor Table) and IDT (Interrupt Descriptor Table), handles interrupts, and implements basic syscalls (`write`, `exit`). You will write a bootloader stub (or use GRUB with Multiboot), switch from real mode to 32-bit/64-bit protected mode, configure segment descriptors, set up an IDT with handlers for timer interrupts, keyboard, and page faults, and implement a syscall interface via `int 0x80` or `syscall` instruction.

**Key concepts**: x86 boot sequence, real vs protected mode, GDT segment descriptors, IDT and interrupt handling, PIC/APIC configuration, kernel entry/exit, ring transitions. **Complexity**: Advanced (5-8 weeks). **References**: [osdev.org](https://wiki.osdev.org/), Philipp Oppermann's "Writing an OS in Rust", MIT xv6.

## 2. Build a Scheduler

Implement a process scheduler supporting FIFO, Shortest Job First (SJF), and Round Robin scheduling. Create process control blocks (PCBs), maintain ready/waiting/run queues, trigger context switches via timer interrupts, and save/restore register state. Extend to support priority scheduling and multi-level feedback queues (MLFQ) for bonus depth.

**Key concepts**: PCB structure, context switching (save/restore registers, stack pointer, program counter), timer interrupt-driven preemption, scheduling algorithms, priority inversion, run queues. **Complexity**: Intermediate (3-5 weeks). **References**: xv6 scheduler (`proc.c`), Linux CFS source (`kernel/sched/fair.c`), OSTEP Chapter 7.

## 3. Build a Memory Allocator

Implement three allocation strategies: a buddy system allocator (power-of-two splitting/merging), a slab allocator (fixed-size object caches with per-CPU partial slabs), and a first-fit allocator over a free list. Compare fragmentation, allocation latency, and memory utilization across workloads. Implement `malloc`/`free` with metadata headers.

**Key concepts**: Internal vs external fragmentation, buddy system split/merge, slab allocator object caching, free list management, alignment requirements, metadata overhead, arena allocation. **Complexity**: Intermediate (3-4 weeks). **References**: glibc malloc internals (`ptmalloc`), jemalloc source, Linux slab allocator (`mm/slab.c`).

## 4. Build a Filesystem

Implement a simple filesystem with an on-disk superblock, inode table, directory entries (linked list or tree), and data blocks. Support `create`, `read`, `write`, `unlink`, `mkdir`, and `readdir` operations. Build a minimal VFS layer that abstracts operations so you can plug in different filesystem backends. Persist to a raw disk image file.

**Key concepts**: On-disk data structures, inode design, block allocation (bitmap or free list), directory entry format, FFS cylinder groups, VFS abstraction layer, journaling concepts. **Complexity**: Intermediate (4-5 weeks). **References**: xv6 filesystem, FFS paper (McKusick et al.), Linux VFS (`fs/`), ext4 design docs.

## 5. Build a Shell

Build a Unix shell supporting command parsing (tokenization, quoting, variable expansion), piped command execution, I/O redirection (`>`, `<`, `>>`, `2>&1`), job control (foreground/background with `&`, `fg`, `bg`), signal handling (`SIGINT`, `SIGTSTP`, `SIGCHLD`), and built-in commands (`cd`, `exit`, `export`). Use `fork`/`exec`/`waitpid` and `pipe()`/`dup2()`.

**Key concepts**: Process creation (fork/exec), file descriptor management, pipe IPC, signal handling, terminal control (tcsetpgrp), process groups, job control. **Complexity**: Beginner-Intermediate (2-3 weeks). **References**: xv6 sh.c, bash source (for reference, not reading), Stephen Brennan's "Write a Shell" tutorial.

## 6. Build a Userspace TCP Stack

Implement a TCP/IP stack in userspace over a TUN/TAP device or raw sockets. Implement the TCP state machine (LISTEN, SYN_SENT, ESTABLISHED, FIN_WAIT, etc.), retransmission with exponential backoff and Karn's algorithm, sliding window flow control, and basic congestion control (slow start, congestion avoidance). Provide a `socket()`/`bind()`/`listen()`/`accept()`/`connect()` API.

**Key concepts**: TCP state machine (11 states), three-way handshake, four-way close, sequence/acknowledgment numbers, retransmission timeout (RTO) calculation, sliding window, congestion window (cwnd), slow start, congestion avoidance. **Complexity**: Advanced (5-7 weeks). **References**: TCP RFC 793, lwIP source, `seastar` (ScyllaDB's userspace stack), TCP Illustrated (Stevens).

## 7. Build a Debugger

Build a debugger using `ptrace` that can attach to a process, set/remove software breakpoints (INT3 injection), single-step through instructions, read/write registers and memory, inspect the call stack via DWARF unwind information, and print local variables. Support a basic command REPL (`break`, `step`, `next`, `continue`, `regs`, `stack`, `memory`).

**Key concepts**: `ptrace` system call (PTRACE_ATTACH, PTRACE_PEEKDATA, PTRACE_POKEDATA, PTRACE_SINGLESTEP), ELF parsing, DWARF debug info, software breakpoints (INT3), register context, stack unwinding (frame pointer vs DWARF CFI). **Complexity**: Advanced (4-6 weeks). **References**: `man ptrace`, Stephen Brennan's "Write a Debugger" series, GDB source, Breakpad.

## 8. Build an eBPF Tracer

Write a tool that loads an eBPF program into the kernel via the `bpf()` syscall, attaches it to a kprobe or tracepoint, reads data from a perf event buffer or ring buffer, and prints formatted output. Start with tracing `sys_enter_openat` to log file opens, then extend to trace function entry/exit with timestamps, filter by PID, and aggregate statistics (count, latency histograms).

**Key concepts**: eBPF program types (kprobe, tracepoint), BPF bytecode, `bpf()` syscall (BPF_PROG_LOAD, BPF_OBJ_GET), maps (hash, array), perf buffer (`BPF_MAP_TYPE_PERF_EVENT_ARRAY`), ring buffer (`BPF_MAP_TYPE_RINGBUF`), libbpf API. **Complexity**: Intermediate (2-4 weeks). **References**: libbpf-bootstrap, bpftrace source, BCC tools collection, `samples/bpf/` in Linux kernel.

> **Interview Angle**: Pick 1-2 of these projects to discuss in depth. A candidate who has built a TCP state machine or a scheduler and can explain the edge cases (simultaneous open, priority inversion) demonstrates systems-level thinking that is hard to fake.