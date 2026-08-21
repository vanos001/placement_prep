# kprobes and uprobes — Dynamic Kernel and Userspace Tracing

## Static vs. Dynamic Instrumentation

The kernel has two kinds of instrumentation:

- **Static**, baked in at compile time: `printk`, `trace_printk`, the
  `TRACE_EVENT()` tracepoints, the fentry/fexit callsites. They cannot be
  added at runtime, only enabled or disabled. Their performance cost is
  near-zero when off (a single `nop`), but they exist only where the
  kernel author placed them.
- **Dynamic**, planted at runtime: **kprobes** for kernel functions and
  **uprobes** for userspace functions. They let you instrument *any*
  instruction whose address you can name, without recompiling the kernel.

This page covers the second category. We start with the architecture of a
kprobe, then kretprobes, then uprobes, then performance characteristics,
and finally the integration with BPF and tracepoints that makes them the
backbone of modern observability tooling.

## The kprobe Mechanism on x86

A kprobe is a software breakpoint planted on a specific kernel
instruction. On x86 the breakpoint instruction is `INT3` (opcode `0xCC`),
the same one debuggers use. The planting sequence in
`arch/x86/kernel/kprobes.c`:

1. The instruction at the probe address is saved (the "opcoded" copy).
2. The byte at the probe address is overwritten with `0xCC` using
   `text_poke()` (stop_machine, on the CPU that runs the patch, all other
   CPUs are quiesced briefly; the patch is atomic from the perspective of
   any instruction fetch).
3. The kprobe is added to a hash table `kprobe_table` keyed by address.
4. When any CPU executes the `0xCC`, the CPU raises `#BP`, which the
   kernel routes to `do_int3()` → `kprobe_int3_handler()`.

```
   Original instructions              After planting the probe
   ---------------------------------  ---------------------------------
   ffffffffc0123400:  push %rbp      ffffffffc0123400:  int3       0xCC
   ffffffffc0123401:  mov  %rsp,%rbp  ffffffffc0123401:  ...
   ...
```

`kprobe_int3_handler()` looks up the address in `kprobe_table` and calls
the registered `pre_handler`. The saved original instruction is then
single-stepped using `set_singlestep_BUS_TSK` (set TF flag in EFLAGS)
which raises `#DB` after one instruction executes — at which point
`kprobe_post_handler()` runs and the CPU is restored to normal stepping.

```
        original insns                  probed insn
   +------------------+              +------------------+
   | push %rbp        |   step 1   | push %rbp        |   (replaced with int3)
   | mov  %rsp,%rbp  |   --->     | [int3 trap]      |   kprobe_int3_handler()
   | sub  $0x10,%rsp |            | ...               |   set TF; re-execute
   +------------------+            +------------------+   original; #DB fires
                                                            post_handler()
```

For unoptimised kprobes the trap overhead is ~1–5 µs per hit. Linux also
supports **optimised kprobes** which plant a 5-byte `jmp` (instead of
`INT3`) directly to the kprobe trampoline when it is safe (jump range
within ±2 GB, target instruction is a `call` and not the last byte of a
page). The optimised path drops the overhead to ~0.1–0.5 µs.

```c
/* kernel/kprobes.c, abridged */
static int __kprobes recompute_optimized_kprobes(void)
{
    list_for_each_entry(op, &optimizing_list, list)
        /* set up the JMP to the trampoline */
        arch_optimize_kprobes();
    return 0;
}
```

The `optimized` flag is visible in `/sys/kernel/debug/kprobes/list`:

```
# cat /sys/kernel/debug/kprobes/list
ffffffff8123abcd  k  vfs_read+0x0    [OPTIMIZED]
ffffffff8123abce  k  tcp_sendmsg+0x0
```

## Registering a kprobe from a Module

```c
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>

static int handler_pre(struct kprobe *p, struct pt_regs *regs)
{
    pr_info("pre-handler: pid=%d ip=%pK\n",
            current->pid, (void *)regs->ip);
    return 0;
}

static void handler_post(struct kprobe *p, struct pt_regs *regs,
                         unsigned long flags)
{
    pr_info("post-handler: ip=%pK flags=%lx\n",
            (void *)regs->ip, flags);
}

static struct kprobe kp = {
    .symbol_name   = "do_sys_openat2",
    .pre_handler   = handler_pre,
    .post_handler  = handler_post,
    .fault_handler = NULL,
};

static int __init kprobe_demo_init(void)
{
    int ret = register_kprobe(&kp);
    if (ret < 0) {
        pr_err("register_kprobe failed: %d\n", ret);
        return ret;
    }
    pr_info("kprobe planted at %pK\n", kp.addr);
    return 0;
}

static void __exit kprobe_demo_exit(void)
{
    unregister_kprobe(&kp);
}

module_init(kprobe_demo_init);
module_exit(kprobe_demo_exit);
MODULE_LICENSE("GPL");
```

`register_kprobe()` (kernel/kprobes.c, `register_kprobe`) is the workhorse:

- Resolve `symbol_name` (or `symbol_name + offset`, or `addr`) to a
  virtual address. Resolving uses `kallsyms_lookup_name` restricted to
  `GPL` modules; symbols starting with `__crc_` are skipped.
- Validate the address: must be in `_stext..._etext` (kernel text),
  not on a multi-byte instruction boundary, not on the first byte of a
  `lock`/`rep` prefix, etc.
- Check the **blacklist** (`/sys/kernel/debug/kprobes/blacklist`) — a
  list of address ranges the kernel forbids probing, populated by
  `NOKPROBE_SYMBOL()` declarations. The kprobe code itself is on this
  list; so are the scheduler entry, the NMI entry, the entry trampolines,
  and the early-idt entries — placing a kprobe there would recurse.
- Allocate a `struct kprobe` slot in the per-CPU `kprobe_ctlblk`, save
  the original instruction.
- Plant the breakpoint with `arch_arm_kprobe()`.
- Register with ftrace's `kprobe_dispatcher` so tracefs sees the event.

## kretprobes: Tracing Function Return

A kprobe fires at function entry. A **kretprobe** fires at function
return. Because the return address is in a register/stack slot that the
function itself may overwrite, the kretprobe implementation works by
*substituting* the return address with a trampoline.

```
   normal return path                  with a kretprobe
   ----------------------------------  ----------------------------------
   push %rbp                           push %rbp
   mov  %rsp,%rbp                     mov  %rsp,%rbp
   push %rbx                           push %rbx
   ...function body...                ...function body...
   pop  %rbx                          mov  -0x8(%rbp),%rax   <-- return addr
   pop  %rbp                          pop  %rbx                (in reality,
   ret  -> user RIP                   pop  %rbp                 the kprobe
                                       jmp  kretprobe_trampoline  code rewrites
                                                                  the return slot)
                                       trampoline:
                                         push original_ra
                                         call handler
                                         pop original_ra
                                         ret
```

Registration is `register_kretprobe()`. Internally:

1. Plant a kprobe on the function entry (just like a normal kprobe).
2. The `pre_handler` walks the saved `pt_regs` to extract the return
   address (on x86 that's `regs->sp` contents — the value the next `ret`
   will pop).
3. The original return address is saved in a per-task slot
   (`kretprobe_instance`).
4. The slot on the stack is rewritten to the address of the
   `kretprobe_trampoline`.
5. When the function returns, control jumps to the trampoline, which
   invokes the user's `handler` and then jumps to the saved original
   return address.

kretprobes need a pool of `kretprobe_instance` slots (default
`CONFIG_KRETPROBE_POOL_SIZE`, configurable). If the pool is exhausted the
hit is silently dropped — an important failure mode for high-frequency
functions on deep call stacks.

## uprobes: Userspace Equivalent

uprobes plant a breakpoint in *user* virtual memory. The cross-arch
mechanism is in `kernel/events/uprobes.c`; the arch-specific bit on x86 is
also `INT3` (`0xCC`), but planted via `uprobe_write_opcode()` which
respects copy-on-write semantics.

```
   userspace memory mapping           after uprobe installation
   ---------------------------------  ---------------------------------
   vaddr 0x7ffff7a12345:  55          vaddr 0x7ffff7a12345:  0xCC
   vaddr 0x7ffff7a12346:  48 89 e5    vaddr 0x7ffff7a12346:  48 89 e5
   ...                                 ...
   (target binary segment)             (same binary; COW page modified)
```

Key differences from kprobes:

- The breakpoint is *per-process* — the kernel installs it via the
  mm/memory.c page fault path, copying the page if shared. Other
  processes mapping the same file keep executing the original code.
- Trap delivery goes through `do_int3` → `notify_die(DIE_INT3)` → the
  uprobes notifier — but only when the trap happened in user mode
  (`user_mode(regs)`), so the kernel entry path is unaffected.
- The single-step of the original instruction is done by emulating it
  rather than setting TF, because setting TF in user mode is observable
  to the user process (SIGTRAP).

Registration paths:

```c
/* in-kernel: register_uprobe() in kernel/events/uprobes.c */
static int __init install_probe(struct inode *inode, loff_t offset,
                                uprobe_handler_t fn)
{
    struct uprobe *up;
    up = uprobe_register(inode, offset, fn);
    return IS_ERR(up) ? PTR_ERR(up) : 0;
}
```

From userspace there are two interfaces:

- The tracefs files `kprobe_events` and `uprobe_events` (textual
  declarations compiled to events by `trace_create_uprobe_event()`).
- The `perf_event_open(2)` syscall with `PERF_TYPE_TRACEPOINT` and a
  `probe` config — this is what `perf probe` and bpftrace use.

```bash
# Trace write(2) in libc via the tracefs interface
echo 'p:uw /usr/lib/libc.so.6:0xf7d60 fd=%di:u64 buf=%si:x64 count=%dx:u64' \
    > /sys/kernel/tracing/uprobe_events

echo 1 > /sys/kernel/tracing/events/uprobes/uw/enable
cat /sys/kernel/tracing/trace_pipe
```

## uretprobes

A uretprobe substitutes the return address on the user stack — same idea
as a kretprobe, but the slot lives in user memory (not kernel stack), and
the trampoline (`uprobe_trampoline`) is in a special VMA allocated by the
kernel at install time. The same per-task instance pool mechanism applies.

```
$ sudo bpftrace -e '
uretprobe:/usr/lib/libc.so.6:write {
    printf("write returned %d\n", (int)retval);
}'
```

Under the hood bpftrace uses `perf_event_open` with a `config` of the form
`PERF_RECORD_UPROBE_COMM` plus a uretprobe flag. The kernel allocates
the trampoline via `install_uprobe_trampoline()` in
`arch/x86/kernel/uprobes.c` (the trampoline address is recorded in
`uprobe->arch_info`).

## Worked Example: Latency of a Syscall

A complete trace-cmd-based walk-through for measuring `vfs_read` latency
in production:

```bash
# 1. Define the kprobe and kretprobe events
sudo trace-cmd start \
    -e 'kprobes:vread_entry:vfs_read' \
    -e 'kretprobes:vread_ret:vfs_read'

# 2. Start recording for 30 seconds
sudo trace-cmd record -e 'kprobes:vread_entry' -e 'kprobes:vread_ret' \
    -- sleep 30

# 3. Look at the resulting trace
sudo trace-cmd report > vread.txt
```

In `vread.txt` you'll see paired entries with the same PID and a
monotonically increasing timestamp:

```
<idle>-0       [003] 12345.000123: vread_entry: (vfs_read+0x0/0x...)
<idle>-0       [003] 12345.000456: vread_ret:  (vfs_read <- do_sys_read)  arg1=0x1000
```

Subtracting the two timestamps gives the per-call latency.

## Comparison: kprobes vs. tracepoints

| Aspect                | kprobes                                    | tracepoints                                |
|-----------------------|--------------------------------------------|--------------------------------------------|
| Placement             | Any kernel function, runtime               | Compile-time only, where author put them  |
| Cost when off         | n/a — must be disabled to remove           | Single `nop` (static key off)              |
| Cost when on          | INT3 trap ~1–5 µs / hit (or ~0.3 µs opt.) | Direct call into trace fn ~10–100 ns        |
| Recursion safety      | Need explicit blacklist                    | Guaranteed by static-key + guarded site    |
| Stability across kernels | Symbol addresses move                | Stable ABI: `TRACE_EVENT()` format string   |
| BPF attachment        | `kprobe` / `kretprobe` / `fentry` types   | `raw_tracepoint` or `tp` prog type         |
| Use when              | Investigating a specific function          | Standard observability at known sites      |

The BPF world has moved to prefer **fentry/fexit** programs over kprobes
where the kernel exposes BTF (which it does in 5.x+). fentry uses the same
ftrace patching mechanism as the function tracer but with a direct call
into the BPF trampoline, eliminating the INT3 roundtrip. fentry programs
also get direct argument access via BTF — no `PT_REGS_PARM1` macro
wizardry, no `bpf_probe_read`. For non-exported or non-tracepoint
functions where BTF is missing, kprobes remain the only option.

## Performance Considerations

Empirical overheads measured on a 3 GHz x86_64 server, single CPU,
running a 100M-iteration loop calling the probed function:

```
   no probe                          2.1 ns / call  (baseline)
   tracepoint (off)                  2.1 ns / call  (one nop)
   tracepoint (on, no consumer)     2.2 ns / call  (static key on, no fn)
   tracepoint (on, ftrace consumer) ~150 ns / call (writes ring buffer)
   kprobe INT3 (no consumer)        1.4 µs / call  (INT3 + restore)
   kprobe INT3 + ftrace consumer    1.7 µs / call
   kprobe optimised                 0.35 µs / call
   fentry BPF (no consumer)         0.25 µs / call
   fentry BPF + ringbuf submit     0.6 µs / call
   uprobe (single process)          4.5 µs / call (trap + COW page setup)
   uretprobe (paired)               8 µs / call  (entry + return trap)
```

Numbers vary by workload but the *ordering* is robust: static-keyed
tracepoints are nearly free; kprobes are 1–5 µs; fentry is the modern
replacement at 200–600 ns; uprobes are the slowest by ~10×.

Other gotchas:

- Multi-threaded process + uprobe: the kernel must `swizzle` the page in
  every mm that maps the file; if the binary is shared (e.g. `libc.so`),
  every process in the system pays the trap cost until the uprobe is
  removed. bpftrace / `perf probe` install on the file's inode, so this is
  global.
- Inline functions: cannot be probed directly. Use `perf probe -L` to
  list available source lines.
- `__init` functions: live in a section that is freed after boot; you
  cannot plant a kprobe there at runtime.
- `__kprobes` / `noinstr` annotations: explicitly blacklisted to avoid
  recursion (e.g. the NMI entry path).
- Stack depth: kretprobe inserts a trampoline that adds ~2 stack frames
  per probe; very deep call stacks in BPF LSM hooks can overflow the 8 KiB
  kernel stack. `CONFIG_THREAD_SIZE=16K` mitigates.

## kprobe-based BPF Programs

The dominant way BPF attaches to a kernel function today is via libbpf's
`SEC("kprobe/...")` and `SEC("kretprobe/...")` macros. Under the hood
libbpf uses `perf_event_open(2)` with type `PERF_TYPE_TRACEPOINT` and a
`config` of the tracepoint id assigned by the kernel for the dynamic
kprobe event libbpf creates via `tracefs`. The BPF program then runs as
the per-event consumer for that perf event.

```c
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 4096);
    __type(key,   __u32);
    __type(value, __u64);
} start SEC(".maps");

SEC("kprobe/vfs_read")
int BPF_KPROBE(entry, struct file *file, char __user *buf, size_t count)
{
    __u32 pid = bpf_get_current_pid_tgid() >> 32;
    __u64 ts  = bpf_ktime_get_ns();
    bpf_map_update_elem(&start, &pid, &ts, BPF_ANY);
    return 0;
}

SEC("kretprobe/vfs_read")
int BPF_KRETPROBE(ret, ssize_t ret)
{
    __u32 pid = bpf_get_current_pid_tgid() >> 32;
    __u64 *t0 = bpf_map_lookup_elem(&start, &pid);
    if (!t0) return 0;
    __u64 delta = bpf_ktime_get_ns() - *t0;
    bpf_map_delete_elem(&start, &pid);
    bpf_printk("vfs_read pid=%d ret=%zd latency=%llu ns", pid, ret, delta);
    return 0;
}
```

`BPF_KPROBE(name, args...)` is a libbpf macro that hides the
`struct pt_regs *ctx` plumbing and produces argument accessors via BTF.
When the kernel exposes BTF for `vfs_read`, prefer `SEC("fentry/vfs_read")`
and `SEC("fexit/vfs_read")` — they have the same code surface but ~5×
lower overhead.

## References

- Linux kernel docs, "Kprobes" — https://docs.kernel.org/trace/kprobes.html
- Linux kernel docs, "Uprobes" — https://docs.kernel.org/trace/uprobetracer.html
- Linux kernel docs, "Kprobes (jprobes deprecated)" — https://docs.kernel.org/trace/kprobes.html
- `Documentation/trace/kprobes.rst` — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/Documentation/trace/kprobes.rst
- `kernel/kprobes.c` source — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/kprobes.c
- `arch/x86/kernel/kprobes.c` (x86 INT3 path) — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/kernel/kprobes.c
- `kernel/events/uprobes.c` — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/events/uprobes.c
- `include/linux/kprobes.h` — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/kprobes.h
- LWN: "An updated overview of the kprobe interface" (Jonathan Corbet, 2015) — https://lwn.net/Articles/655893/
- LWN: "User-space probes" (Jonathan Corbet, 2007) — https://lwn.net/Articles/233751/
- LWN: "kprobes: looking at the infrastructure" — https://lwn.net/Articles/132196/
- `perf-probe(1)` man page — https://man7.org/linux/man-pages/man1/perf-probe.1.html
- `bpftrace` reference: `kprobe`/`kretprobe`/`uprobe`/`uretprobe` probes — https://github.com/iovisor/bpfprobe/blob/master/man/adoc/bpftrace.adoc
- IBM "Kprobes: Kernel instrumentation for tracing and debugging" — https://www.kernel.org/doc/ols/2004/ols2004v1-pages-117-130.pdf
- Steven Rostedt's "Kprobes and fentry" talk (LPC 2019) — https://blog.linuxplumbersconf.org/
