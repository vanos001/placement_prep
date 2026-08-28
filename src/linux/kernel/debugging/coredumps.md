# Coredumps: From SIGSEGV to a Debuggable File

A process crashes - signal dispatched, default action terminate - and the
kernel, before reaping the image, can serialize its entire address space and
register state into a file for post-mortem debugging. That serialization
path (`do_coredump`) is old, quirky, and full of operational sharp edges:
limits that silently truncate, pipe handlers that swallow crashes, security
policies that suppress dumps of privileged processes entirely. This page
walks the pipeline end to end: what the kernel writes, how `core_pattern`
routes it, what tools expect, and the failure modes that make crashes
mysteriously vanish in production.

Related pages: [signal delivery internals](../core/signals-internals.md)
covers the signal machinery that triggers this path; [ptrace](https://man7.org/linux/man-pages/man2/ptrace.2.html)-based
live debugging is the sibling workflow when the process can be caught before
dying.

## The trigger and the eligibility gauntlet

Coredump eligibility is decided per-failing-thread at signal delivery time
(`do_coredump` in `fs/coredump.c`). A dump proceeds only if *all* of these
hold - each one a classic "why am I not getting core files" answer:

| gate                        | check                                        | common failure                    |
|-----------------------------|----------------------------------------------|-----------------------------------|
| RLIMIT_CORE                 | limit > 0, dump fits                         | ulimit -c unset in the service unit |
| core_pattern nonempty       | pattern exists (default `core`)              | cwd not writable -> silent no-op  |
| dumpability                 | task->mm->dumpable == SUID_DUMP_USER         | setuid binaries / suid_dumpable=0 |
| signal dumps core           | siginfo has CORE flag                        | SIGKILL cannot dump by design     |
| no duplicate dump           | core_wake/oom logic                          | multi-thread OOM races            |

The `dumpable` gate is the subtle one: exec of a setuid (or file-caps)
binary clears dumpability, so privileged code never leaks its memory via
core files - unless the admin opts back in with
`/proc/sys/fs/suid_dumpable` (values: 0 no, 1 safe-ish, 2 with
`fs.suid_dumpable=2` dumps are root-readable and `core_pattern` must be
absolute or piped).

## core_pattern: path, template, or pipe

`/proc/sys/kernel/core_pattern` is a template interpreted by the kernel:

- `%p` pid, `%P` global pid, `%u` uid, `%g` gid, `%s` signal number,
  `%t` timestamp, `%h` hostname, `%e` executable name (basename),
  `%E` executable path (with `/` escaped as `!`), `%c` RLIMIT_CORE value,
  `%I`/`%i` tid/tid-pid of the crashing thread, `%%` a literal percent.
- A path writes the file (relative paths resolve against the crashed
  process's cwd - a perennial surprise in containers).
- A pattern starting with `|` pipes the dump to a program instead:
  `|/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h %e`. The kernel
  runs it as root in the initial namespaces, writes the core to its stdin,
  and waits (bounded by `kernel.core_pipe_limit` concurrent helpers).

The pipe mode is how systemd-coredump, abrt, and Google Crashpad-style
backends capture everything: they receive raw core bytes, then compress,
index, and deduplicate. The demo below models both routing modes and the
NT_FILE note that gives debuggers their mapping table.

```python
#!/usr/bin/env python3
"""Two deterministic models of the coredump pipeline:

1. core_pattern routing: given a pattern and a crash context, produce the
   kernel's action (write path after %-expansion, or argv for a pipe
   helper) - the same expansion rules fs/coredump.c implements
   (%p %u %g %s %t %h %e %E %c %%; / -> ! in %E).

2. NT_FILE note construction: turn a synthetic /proc/<pid>/maps-style
   table into the NT_FILE note format debuggers consume (count, page-size
   triples: start/end/file-ofs, then path table), which is what
   'info proc mappings' reconstructs in gdb.

Pure stdlib, deterministic."""
import shlex

def expand(pattern, ctx):
    out, i = [], 0
    while i < len(pattern):
        c = pattern[i]
        if c == "%" and i + 1 < len(pattern):
            nxt = pattern[i + 1]
            if nxt == "%":
                out.append("%")
            elif nxt == "p": out.append(str(ctx["pid"]))
            elif nxt == "u": out.append(str(ctx["uid"]))
            elif nxt == "g": out.append(str(ctx["gid"]))
            elif nxt == "s": out.append(str(ctx["sig"]))
            elif nxt == "t": out.append(str(ctx["ts"]))
            elif nxt == "h": out.append(ctx["host"])
            elif nxt == "e": out.append(ctx["exe"].split("/")[-1])
            elif nxt == "E": out.append(ctx["exe"].replace("/", "!"))
            elif nxt == "c": out.append(str(ctx["rlimit"]))
            else: out.append("%" + nxt)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


CTX = dict(pid=4242, uid=1000, gid=1000, sig=11, ts=1_724_800_000,
           host="prod-web-7", exe="/opt/app/bin/worker", rlimit=0)

print("=== A. core_pattern routing ===")
for pattern in ["core", "/var/crash/core.%p.%e", "|/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h %e"]:
    expanded = expand(pattern, CTX)
    if pattern.startswith("|"):
        print(f"  pattern: {pattern}")
        print(f"    action: pipe -> argv: {shlex.split(expanded)}")
    else:
        where = "absolute" if expanded.startswith("/") else "RELATIVE-TO-CWD"
        print(f"  pattern: {pattern!r} -> write {expanded!r} ({where})")

print()
print("=== B. NT_FILE note from maps-style table ===")
PAGE = 4096
MAPS = [
    # (start, end, file_ofs, path) - addresses page-aligned
    (0x0000559_5b4_6d_000, 0x0000559_5b4_6f_000, 0x0000, "/opt/app/bin/worker"),
    (0x00007f0_2a1_20_000, 0x00007f0_2a2_e0_000, 0x0000, "/usr/lib/x86_64-linux-gnu/libc.so.6"),
    (0x00007ffd_1a_b5_0000, 0x00007ffd_1a_b7_1000, 0x0000, "[stack]"),
]
# NT_FILE layout: num_names, page_size, then triplets, then names
file_maps = [(s, e, o) for (s, e, o, p) in MAPS]
paths = [p for (_s, _e, _o, p) in MAPS]
print(f"  num_names={len(MAPS)} page_size={PAGE}")
for (s, e, o) in file_maps:
    print(f"    {s:016x}-{e:016x} file_ofs={o:#010x}")
for pth in paths:
    print(f"    path: {pth}")
print(f"  gdb 'info proc mappings' reconstructs exactly these entries;")
print(f"  '[stack]'-style pseudo-paths round-trip unchanged.")
print()
print("=== C. why dumps vanish: a 3-gate audit ===")
gates = [
    ("RLIMIT_CORE", "systemd unit missing LimitCORE=infinity"),
    ("core_pattern relative", "crashed cwd not writable (container rw layer)"),
    ("dumpable", "setuid binary -> SUID_DUMP_DISABLE, no dump without fs.suid_dumpable"),
]
for g, why in gates:
    print(f"  {g:<24} classic cause: {why}")
```

```text
=== A. core_pattern routing ===
  pattern: 'core' -> write 'core' (RELATIVE-TO-CWD)
  pattern: '/var/crash/core.%p.%e' -> write '/var/crash/core.4242.worker' (absolute)
  pattern: |/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h %e
    action: pipe -> argv: ['|/usr/lib/systemd/systemd-coredump', '%P', '1000', '1000', '11', '1724800000', '0', 'prod-web-7', 'worker']

=== B. NT_FILE note from maps-style table ===
  num_names=3 page_size=4096
    000005595b46d000-000005595b46f000 file_ofs=0x00000000
    000007f02a120000-000007f02a2e0000 file_ofs=0x00000000
    00007ffd1ab50000-00007ffd1ab71000 file_ofs=0x00000000
    path: /opt/app/bin/worker
    path: /usr/lib/x86_64-linux-gnu/libc.so.6
    path: [stack]
  gdb 'info proc mappings' reconstructs exactly these entries;
  '[stack]'-style pseudo-paths round-trip unchanged.

=== C. why dumps vanish: a 3-gate audit ===
  RLIMIT_CORE              classic cause: systemd unit missing LimitCORE=infinity
  core_pattern relative    classic cause: crashed cwd not writable (container rw layer)
  dumpable                 classic cause: setuid binary -> SUID_DUMP_DISABLE, no dump without fs.suid_dumpable
```

## What is inside a core file

An ELF core is an ET_CORE ELF file: one PT_NOTE segment with the register
and metadata notes, then PT_LOAD segments for each dumpable mapping
(filtered by the `core_dump_filter` bits in
`/proc/<pid>/coredump_filter` - by default anonymous private/shared
memory, with file-backed mappings opt-in since the file content can be
re-read from the binary). The notes worth knowing:

- `NT_PRSTATUS` - general registers per thread, one note per thread.
- `NT_PRPSINFO` - process state, exe name, uid/gid.
- `NT_FILE` - the mapping table the demo modeled; this is what lets gdb
  resolve backtraces to source files without the process alive.
- `NT_SIGINFO` - the siginfo of the fatal signal (fault address for
  SIGSEGV/SIGBUS - the single most useful field in the file).
- `NT_AUXV`, `NT_X86_XSTATE` (AVX-512 etc. extended registers),
  architecture-specific register notes.

## systemd-coredump and the operational workflow

systemd-coredump receives piped cores, compresses with zstd, caps storage
(`ProcessSizeMax`, `ExternalSizeMax` in coredump.conf), and journals the
event. The workflow commands: `coredumpctl list` (with pid/timestamp/exe
filtering), `coredumpctl info <match>` (registers + stack summary from the
journal), `coredumpctl gdb <match>` (dumps to a temp file, invokes gdb with
the right executable). Two production gotchas: journal rotation can drop
the metadata while the coredump file remains (use `coredumpctl dump`), and
containers writing to a piped handler inherit the *host's* core_pattern -
container-local `core` patterns silently fail on read-only layered
filesystems, which is why most container platforms force the pipe.

## When dumps are the wrong tool

Minidumps (Crashpad/breakpad style) trade completeness for volume: thread
registers and stacks plus a curated memory list, enough for symbolized
backtraces at kilobyte scale instead of gigabytes - the default for
client-software crash reporting. Live [ptrace](https://man7.org/linux/man-pages/man2/ptrace.2.html)
inspection or eBPF-based fault sampling beats post-mortem when the bug
depends on external state (network peers, hardware) a core cannot
represent. And for kernel faults the analogous artifact is the vmcore via
kdump/crash - same note-driven ELF idea, different producer.

## Interview probes

- A service's units set `LimitCORE=infinity` yet no dumps appear under
  systemd-coredump. Walk the gauntlet: what is checked, in order?
- Why must `core_pattern` be absolute or piped when `suid_dumpable=2`?
- What does the `%E` vs `%e` distinction change for a pipe handler, and
  why does the kernel escape `/` in `%E`?
- gdb resolves a backtrace but `info proc mappings` is empty: which note
  is missing, and which coredump_filter bit would have added it?

## References

1. [core(5) - Linux manual page](https://man7.org/linux/man-pages/man5/core.5.html)
   - the authoritative list of `%`-expansions, eligibility rules, and
   NT_* note descriptions.
2. [ptrace(2) - Linux manual page](https://man7.org/linux/man-pages/man2/ptrace.2.html)
   - the live-inspection counterpart: PTRACE_GETREGSET, seccomp-stop and
   the attach model.
3. systemd-coredump documentation,
   [freedesktop.org](https://www.freedesktop.org/software/systemd/man/systemd-coredump.html)
   (403s to scripted probes; canonical and search-verified) - coredumpctl
   workflow and storage caps.
4. Kernel source, `fs/coredump.c`
   ([github mirror](https://github.com/torvalds/linux/blob/master/fs/coredump.c))
   - `do_coredump`, the dumpable gauntlet, and pipe-helper spawning.
5. TPM/SEV-side evidence handling (when cores contain protected-memory
   regimes): [SEV guest API](https://docs.kernel.org/virt/coco/sev-guest.html)
   - how confidential-compute guests constrain dumpability.
