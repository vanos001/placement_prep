# syzkaller: Coverage-Guided Kernel Syscall Fuzzing

syzkaller is Google's unsupervised, coverage-guided kernel fuzzer. It grew up
with the Linux kernel but also targets FreeBSD, NetBSD, OpenBSD, Fuchsia, and
Darwin/XNU. Instead of parsing files like a userspace fuzzer, it mutates
*programs*: sequences of typed system calls, executed inside disposable VMs.
Findings are tracked at [syzkaller.appspot.com](https://syzkaller.appspot.com/); syzbot
emails reports to the maintainers who can act on them.

## Why Kernel Fuzzing Is a Different Game

A userspace fuzzer links its harness to a library and calls one API. The
kernel offers no such entry point:

- **No `main()` to instrument.** Every syscall is a separate entry into kernel
  code, and state persists in descriptors, mounts, and namespaces between
  calls, so meaningful inputs are *sequences*, not blobs.
- **Crashes are expensive.** A userspace crash costs a process exit; a kernel
  crash kills the whole machine, so every round needs a fresh disposable VM.
- **Privilege asymmetry.** Reaching ioctls and mounts requires root, so the
  fuzzer can wedge the machine; sandboxed execution is mandatory, not optional.

| Aspect            | Userspace fuzzer (AFL/LibFuzzer) | Kernel fuzzer (syzkaller)        |
|-------------------|----------------------------------|----------------------------------|
| Target entry      | One harness function             | Any syscall, any order           |
| Input             | Byte buffer                      | Program: typed syscall sequence  |
| Crash unit        | Process                          | Whole VM (panic, reboot)         |
| Coverage source   | Compiler-instrumented binary     | KCOV instrumentation in kernel   |

## syzlang: Describing the Syscall Surface

Syscall signatures are not hard-coded. They are declared in **syzlang**, a
description language compiled by `syz-sysgen` into code used by the mutator
and executor. A **resource** is a value with a life cycle -- produced by one
call, consumed by others -- with subtyping flowing through the declaration:

```text
resource fd[int32]              # fd is an int32, but a special one
resource fd_socket[fd]          # fd_socket is an fd, which is an int32

open(file ptr[in, filename], flags flags[open_flags], mode flags[open_mode]) fd
socket(domain const[AF_INET], type const[SOCK_STREAM], proto int8) fd_socket
read(fd fd, buf ptr[out, array[int8]], count len[buf]) len[buf]
close(fd fd)
```

`socket(... ) fd_socket` means the return value is a socket handle, and any
argument typed `fd_socket` must be filled from a value an earlier call
produced. The same mechanism covers `fd[usb_device]`: the pseudo-syscall
`syz_usb_connect` returns such a handle, and only USB ioctls accept it. Type
constraints do the rest: `const[...]` pins a value, `flags[...]` picks bit
combinations from a named set, `len[buf]` ties a length argument to the
referenced buffer, and `ptr[in, ...]` vs `ptr[out, ...]` distinguishes input
marshalling from output capture.

The **corpus** is a population of such programs, not isolated calls: a seed
that opens a loop device, mounts a filesystem, and issues overlapping reads
exercises real state machines. Programs are stored as text; the mutator
evolves them as a whole.

## The Fuzzing Loop

```text
      +------------------ syz-manager (host) -------------------+
      |  corpus <--> mutator --> serialized program              |
      |    ^                               |                     |
      |    |                               v                     |
      |    |                     +------------------+            |
      |    |                     | VM: syz-executor |            |
      |    |                     +------------------+            |
      |    |                               |                     |
      |    +--- coverage feedback ---------+                     |
      |        (KCOV pc table -> deduped signal)                 |
      |                                                          |
      |  crash detector <--- VM console output                   |
      +----------------------------------------------------------+
```

1. **Mutate.** Pick a program and randomly insert or remove syscalls, splice
   two programs, replace a call, or mutate arguments; resource-typed
   arguments are repaired so the result stays semantically connected.
2. **Execute.** `syz-manager` boots VMs and queues the program to
   `syz-executor`, which runs the calls in child threads under a sandbox and
   collects coverage.
3. **Measure coverage.** With `CONFIG_KCOV`, a debugfs device records the
   program counters of basic blocks executed by a single thread. The executor
   turns this pc table into a *signal* of previously unseen PCs or edges;
   programs that add signal enter the corpus.
4. **Detect crashes.** `syz-manager` watches the guest console: kernel
   panics, KASAN/KCSAN reports, lockdep splats, and hung tasks map to crashes
   with a signature derived from the report; the VM restarts and the program
   is saved for reproduction.

Sanitizers multiply what the loop can see: KASAN turns silent corruption into
a use-after-free report, and KFENCE catches out-of-bounds slab accesses cheaply.

## Reproduction: From Log to C File

A saved crashing program is rarely minimal, and a raw log is hard to act on.
The `syz-repro` tool takes the stored program and kernel image, minimizes the
program by dropping calls and arguments until the crash disappears (iterating
dozens of reboots), then translates what remains into a self-contained C
reproducer. Reproducers land on the public dashboard, where bugs are grouped
by title and subsystem, each entry linking the log, the crashing program, and,
when available, the C reproducer and the fixing commit.

## Impact and the Maintainer Workflow

The dashboard's per-tree instances (upstream, linux-next, net-next, Android
kernels, and others) give maintainers a deduplicated public view of what is
failing in code they own. When syzbot finds a bug it emails subsystem
maintainers and mailing lists with the log, the reproducer, and the offending
tree and commit, plus a dashboard entry with a stable email address for
update commands. Maintainers steer the tracker by email: reply with
`#syz fix: <commit-title>` to mark a fix, or `#syz test:` to request a retest
of a candidate patch. Once a fix lands and the reproducer stops crashing, the
issue closes automatically, crediting the fix's author -- the report arrives
where the fix will be authored, with the triggering program.

## Variants and Related Kernel Fuzzers

- **USB.** syzkaller fuzzes USB host controllers through emulated devices:
  the kernel's `dummy_hcd` virtual host controller accepts fuzzer-controlled
  devices, and syzlang declares pseudo-syscalls such as `syz_usb_connect`
  that attach a device described by raw descriptors. KCOV remote coverage
  (`kcov_remote`) makes code running in softirqs and USB workqueues visible
  even though it executes outside the fuzzed thread.
- **Networking and BPF.** The descriptions cover socket, netlink, and BPF
  syscalls; combined with the BPF verifier's rejection of invalid programs,
  fuzzing targets verifier edge cases and the paths a loaded program reaches.
- **Trinity** predates syzkaller: random syscalls with enough built-in rules
  to avoid trivial crashes, but no coverage feedback and no resource model,
  so it cannot compound progress across runs.
- **kAFL/Redqueen** use Intel PT hardware tracing for coverage and
  input-to-state techniques to guess magic values, complementing syzkaller
  where KCOV instrumentation is impractical.

## Setup Anatomy: syz-manager

A minimal `syz-manager` config describes a kernel build and a VM pool; the
manager keeps the corpus and crash artifacts in `workdir`:

```json
{
    "target": "linux/amd64",
    "http": "127.0.0.1:56741",
    "workdir": "/syzkaller/workdir",
    "kernel_obj": "/linux/",
    "image": "/syzkaller/images/buildroot.img",
    "type": "qemu",
    "vm": {
        "count": 4,
        "kernel": "/linux/arch/x86/boot/bzImage",
        "cpu": 2,
        "mem": 2048
    }
}
```

`image` is the guest disk image (syzbot uses a Buildroot image); the pool
consumes `count * cpu` CPUs and `count * mem` MB of RAM. The HTTP endpoint
exposes per-VM status, corpus growth, and crash logs, mirroring the public
dashboard. A local instance is the machinery syzbot runs, scaled up:
continuous fuzzing, reproduction, and bisection of listed trees.

## Demo: Resource Flow Is the Game

The engine below parses a miniature syzlang description (four syscalls, with
`fd_socket` a subtype of `fd`), generates 10,000 random programs two ways,
and counts programs where every `fd` argument was produced by an earlier call
in the same program. Resource-aware generation reuses handles from earlier
calls (what syzkaller's resource model does); type-blind generation fills
every argument with random integers.

```python
import random
import re
DESC = """
resource fd[int32]
resource fd_socket[fd]
open(path string, flags intptr) fd
socket(domain intptr, type intptr) fd_socket
read(fd fd, count intptr) intptr
close(fd fd)
"""

def parse(text):
    res, sysc = {}, {}
    for line in text.strip().splitlines():
        line = line.strip()
        m = re.match(r"resource\s+(\w+)\[(\w+)\]$", line)
        if m:
            res[m.group(1)] = m.group(2)      # subtype -> parent
            continue
        name, rest = line.split("(", 1)
        body, _, ret = rest.rpartition(")")
        args = [a.strip().split()[-1] for a in body.split(",")] if body.strip() else []
        sysc[name] = {"args": args, "ret": ret.strip() or None}
    return res, sysc
def isa(kind, target, res):
    while kind and kind != target:
        kind = res.get(kind)                  # walk the parent chain
    return kind == target
def gen(rng, aware):
    prog, pool = [], []
    for _ in range(rng.randint(2, 6)):
        name = rng.choice(list(SYSC))
        argv = [rng.choice(pool) if isa(t, "fd", RES) and aware and pool
                else rng.randint(0, 0xFFFFFFFF) for t in SYSC[name]["args"]]
        if SYSC[name]["ret"] and isa(SYSC[name]["ret"], "fd", RES):
            h = "fd%d" % len(pool)            # virtual return slot
            pool.append(h); argv.append(h)
        prog.append((name, argv))
    return prog
def valid(prog):
    produced = set()
    for name, argv in prog:
        for t, v in zip(SYSC[name]["args"], argv):
            if isa(t, "fd", RES) and (not isinstance(v, str) or v not in produced):
                return False                  # fd from nowhere
        if SYSC[name]["ret"] and isa(SYSC[name]["ret"], "fd", RES):
            produced.add(argv[-1])
    return True
RES, SYSC = parse(DESC)
rng = random.Random(42)
N = 10000
for label, aware in (("resource-aware", True), ("type-blind", False)):
    ok = sum(valid(gen(rng, aware)) for _ in range(N))
    print("%-15s programs with valid fd chains: %5d/%d (%.1f%%)"
          % (label, ok, N, 100.0 * ok / N))
```

```text
resource-aware  programs with valid fd chains:  5022/10000 (50.2%)
type-blind      programs with valid fd chains:   999/10000 (10.0%)
```

Resource-aware generation yields five times as many programs in which every
handle flows from a real producer. The 50.2% ceiling is structural: any
program starting with a consumer (`read`, `close`) has no handle to reuse
yet -- which is why syzkaller seeds its corpus with hand-written programs.

## Related Pages

- [Fuzz Testing](./fuzz-testing.md) - coverage-guided fuzzing fundamentals in userspace terms.
- [Kernel Sanitizers](../linux/kernel/debugging/sanitizers.md) - KASAN/KCSAN, whose reports syzkaller treats as crashes.
- [KFENCE](../linux/debugging/kfence.md) - low-overhead sampled heap validation for long campaigns.
- [BPF Verifier](../linux/kernel/bpf-verifier.md) - the in-kernel gatekeeper shaping BPF fuzzing.
- [Testing README](./README.md) - where this chapter sits in the testing section.

## References

1. syzkaller repository and README: <https://github.com/google/syzkaller>
2. syzlang syntax documentation (resources, inheritance, type constraints): <https://raw.githubusercontent.com/google/syzkaller/master/docs/syscall_descriptions_syntax.md>
3. syzbot dashboard (bugs per tree, reproducers, logs): <https://syzkaller.appspot.com/>
4. syzbot workflow (`#syz fix`, `#syz test`, email reports): <https://raw.githubusercontent.com/google/syzkaller/master/docs/syzbot.md>
5. KCOV kernel documentation (coverage collection, `kcov_remote` for USB): <https://docs.kernel.org/dev-tools/kcov.html>
6. syzkaller setup documentation (kernel config, QEMU image, syz-manager): <https://raw.githubusercontent.com/google/syzkaller/master/docs/linux/setup.md>
7. syzkaller mailing list archive on lore.kernel.org: <https://lore.kernel.org/syzkaller/>
