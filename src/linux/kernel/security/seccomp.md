# seccomp — Secure Computing Mode

## Introduction

`seccomp` (secure computing mode) is a kernel mechanism by which a
process can voluntarily enter a sandbox in which most system calls are
disallowed. The original form, "strict mode," shipped in Linux 2.6.12
(July 2005) and grew out of Andrea Arcangeli's work on CPU isolation
for compute-heavy workloads. Strict mode is brutal: only `read()`,
`write()`, `exit()`, and `sigreturn()` are permitted. Anything else
triggers `SIGKILL`.

The interesting form is **seccomp-bpf**, merged in Linux 3.5 (July
2012) by Will Drewry. With it, a process can attach a small BPF
(Berkeley Packet Filter) program to itself. The BPF program inspects
the syscall number and (on most architectures) up to six of its
arguments and returns a verdict — kill, return `errno`, trap to a
tracer, log, or allow. This is the mechanism underlying Chrome's
renderer sandbox, Docker's default profile, and `systemd`'s
`SystemCallFilter=` directive.

> **Man page:** seccomp(2) — <https://man7.org/linux/man-pages/man2/seccomp.2.html>
> **Kernel docs:** `Documentation/userspace-api/seccomp_filter.rst`
> **Header:** `include/uapi/linux/seccomp.h`
> **Library:** `libseccomp` — <https://github.com/seccomp/libseccomp>

## Strict Mode

A process opts into strict mode by:

```c
#include <linux/seccomp.h>
#include <sys/prctl.h>

prctl(PR_SET_SECCOMP, SECCOMP_MODE_STRICT);
```

After that, calling any syscall other than `read`, `write`, `_exit`,
or `sigreturn` results in `SIGKILL` — no coredump, no chance to
handle it. This is occasionally useful for compute-only workers (the
original target was a SETI@home-style compute daemon) but useless for
anything that talks to the network, makes files, allocates memory
through `brk`, or reads the time of day.

`SECCOMP_MODE_STRICT` predates BPF and is preserved for compatibility.

## Filter Mode: BPF over syscalls

```c
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <sys/prctl.h>
#include <linux/audit.h>     /* AUDIT_ARCH_X86_64 */

struct sock_filter filter[] = {
    /* Load architecture */
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
             offsetof(struct seccomp_data, arch)),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),

    /* Load syscall number */
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
             offsetof(struct seccomp_data, nr)),

    /* Allow read(0), write(1), exit(60) */
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_read,  0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_write, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_exit,  0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),

    /* Deny everything else with EPERM */
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | 1),
};

struct sock_fprog prog = {
    .len    = sizeof(filter) / sizeof(filter[0]),
    .filter = filter,
};

/* Required: prevent setuid, setgid, file caps from granting new privs */
prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog);
```

Note two essential details:

1. **`PR_SET_NO_NEW_PRIVS` first.** Without it, an unprivileged user
   could install a filter, then exec a setuid binary (which would have
   its syscall surface reduced but still run with root privileges).
   `no_new_privs` flips a per-process flag (set in `struct
   task_struct` in `include/linux/sched.h`) that permanently disables
   setuid, file caps, and several other privilege-granting paths. It
   is inherited across fork and exec.
2. **`seccomp_data.nr` is architecture-specific.** On x86-64,
   `__NR_read` is 0; on ARM, it is 3. Multi-arch filters must check
   `seccomp_data.arch` (as above) before reading the number, otherwise
   an attacker could switch to a 32-bit personality and use a
   different syscall table. `libseccomp` handles this for you; raw
   BPF does not.

### Return values

The verdict a BPF program returns is one of these constants:

| Return                       | Action                                          |
|------------------------------|-------------------------------------------------|
| `SECCOMP_RET_KILL_THREAD`    | `SIGKILL` the calling thread                    |
| `SECCOMP_RET_KILL_PROCESS`   | `SIGKILL` the whole process (Linux 4.11+)      |
| `SECCOMP_RET_TRAP`           | raise `SIGSYS` (can be caught)                  |
| `SECCOMP_RET_ERRNO`          | syscall returns with `errno` from low 16 bits   |
| `SECCOMP_RET_TRACE`          | notified ptracers choose to allow/deny          |
| `SECCOMP_RET_LOG`            | allow + log (Linux 4.10+)                       |
| `SECCOMP_RET_USER_NOTIF`     | allow + ask userspace supervisor (Linux 5.0+)   |
| `SECCOMP_RET_ALLOW`          | allow the call                                  |

The most useful in practice are `RET_ERRNO` (for "you may not do
this, here is a friendly error") and `RET_TRAP`/`RET_USER_NOTIF` (for
"ask the supervisor to emulate it").

## Docker's Default Profile

Docker ships a default seccomp profile that blocks 44 of roughly 350
syscalls. The list is conservative: it blocks anything that
historically plagued container escapes — `keyctl`, `kexec_load`,
`mount`, `umount2`, `reboot`, `swapon`, `init_module`,
`finit_module`, `bpf`, `clone` with `CLONE_NEWUSER` plus a few
others, and most of the x32 ABI.

The profile is JSON, embedded in the `moby/moby` source at
`profiles/seccomp/default.json` and overridable with
`--security-opt seccomp=path/to/profile.json` (or `--security-opt
seccomp=unconfined` to disable entirely — almost always a mistake).

A fragment of the default profile showing the typical pattern —
*allow most syscalls, deny a specific few* — looks like this:

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "syscalls": [
    {
      "names": ["accept", "accept4", "access", "arch_prctl", "bind",
                "brk", "chdir", "chmod", "chown",
                "...about 300 more..."],
      "action": "SCMP_ACT_ALLOW",
      "args": [], "comment": "", "includes": {}, "excludes": {}
    },
    {
      "names": ["_sysctl", "bdflush", "create_module", "finit_module",
                "get_kernel_syms", "init_module", "ioperm", "iopl",
                "kcmp", "kexec_file_load", "kexec_load",
                "lookup_dcookie", "mount", "nfssvcctl",
                "open_by_handle_at", "perf_event_open", "personality",
                "pivot_root", "ptrace", "reboot",
                "remap_file_pages", "settimeofday", "swapoff",
                "swapon", "umount", "umount2", "unshare", "uselib"],
      "action": "SCMP_ACT_ERRNO",
      "args": [], "comment": "deny"
    },
    {
      "names": ["clone"],
      "action": "SCMP_ACT_ALLOW",
      "args": [
        { "index": 0, "value": 2114060288,
          "op": "SCMP_CMP_MASKED_EQ",
          "comment": "deny CLONE_NEWUSER" }
      ],
      "comment": "Allow clone except for CLONE_NEWUSER"
    }
  ]
}
```

The `clone` entry is a particularly nice illustration: the BPF runs
on the arguments, not just the syscall number. The mask `0x7E030000`
isolates the namespace-creation flags `CLONE_NEWUSER | CLONE_NEWNS |
CLONE_NEWPID | CLONE_NEWNET | CLONE_NEWIPC | CLONE_NEWUTS |
CLONE_NEWCGROUP`. If those are *not* set, the call is allowed; if
set, the comparison fails and falls through to the default
`SCMP_ACT_ERRNO`. (Docker has subsequently relaxed some of these to
allow `unshare` in modern builds because the runc incident
CVE-2019-5736 turned out not to need it; the philosophy remains.)

`libseccomp` is what parses this JSON, generates the BPF, and loads
it. Underneath, it calls `seccomp(2)` for you.

## Comparison to AppArmor and SELinux

seccomp, AppArmor, and SELinux sit at different layers of the
security stack:

```
                 | syscall args | syscall numbers | file paths | labels/types |
seccomp          |  yes (BPF)   |  yes            |  no        |  no          |
AppArmor         |  no          |  partial        |  yes       |  partial     |
SELinux          |  no          |  no             |  partial   |  yes         |
```

- **seccomp** restricts *what* syscalls a process can call,
  optionally filtering on integer argument values. It does not see
  file paths or IPC labels. It is fast (BPF is JIT-compiled) and
  per-thread.
- **AppArmor** is path-based MAC: "this binary may read these
  paths." It can also restrict network ports, capabilities, and
  rlimits. It is simpler than SELinux but coarser.
- **SELinux** is label-based MAC: every process has a security
  context (a label), every inode/socket/IPC has a label, and policy
  rules say "type A may { read, write, ioctl } type B." It is
  comprehensive and notoriously hard to write policies for.

The three are commonly combined: a Docker container gets seccomp
(syscall filter) + AppArmor (Ubuntu default) or SELinux
(Fedora/CentOS default) + dropped capabilities. The
defense-in-depth matters because each catches a different class of
mistake.

## Chrome's Sandbox

Chromium uses `seccomp-bpf` to sandbox its renderer and GPU
processes. Renderers execute untrusted web content, so they need to
be locked down: the network is managed by the browser process, file
system access is mediated through IPC, and the renderer itself should
not be able to do much beyond computation and `mmap` of GPU buffers.

Chromium's approach has two layers:

1. **`setuid` sandbox** (pre-`CLONE_NEWUSER`) — used before user
   namespaces were widely available. Still maintained for compat.
2. **`seccomp-bpf` policy** — a "denylist" plus a "broker process"
   for trapped syscalls. Trapped syscalls are forwarded over a Unix
   domain socket to a privileged broker that decides whether to honor
   them (e.g. opening a specific file the user selected).

The BPF programs are large — a typical renderer filter is ~400 BPF
instructions — and are built via `sandbox::bpf_dsl`, a small DSL that
compiles to `sock_fprog`. The flow at startup:

```
+-----------------+        fork         +----------------------+
| Browser process |  ------------------> | Renderer child       |
| (privileged)    |                     | 1. set no_new_privs   |
|                 |   socketpair(AF_UNIX)| 2. install BPF filter|
|                 |   <-----------------| 3. exec v8 / blink   |
|  Broker process |                     | 4. run untrusted JS  |
|  evaluates each |     SECCOMP_RET_TRAP |                      |
|  trapped call   |<---------------------|                      |
+-----------------+   over Unix socket   +----------------------+
```

The Chrome team's writing on the sandbox is canonical reading:

- *Sandbox design under Linux* — <https://www.chromium.org/developers/design-documents/sandbox/>
- *Linux seccomp-bpf sandbox* — <https://www.chromium.org/developers/design-documents/linux-seccomp-bpf-sandbox/>

## Inspecting seccomp on a Process

A process's seccomp state is visible in `/proc/<pid>/status`:

```
$ grep -i seccomp /proc/self/status
Seccomp:         2            <-- 0=off, 1=strict, 2=filter
Seccomp_filters: 3            <-- count of installed BPF filters
```

To dump and disassemble the BPF of an already-loaded filter on a
process you control, the `seccomp-tools` Ruby gem is the standard
tool (<https://github.com/david942j/seccomp-tools>). For ad-hoc
inspection of the rules Docker applies:

```
$ docker run --rm -it alpine /bin/sh -c \
    'apk add --no-cache ruby; gem install seccomp-tools; \
     seccomp-tools dump /bin/sh'
```

will print the BPF disassembly. This is invaluable for verifying
that your own `--security-opt seccomp=` JSON actually compiled to the
BPF you expected.

## Failure modes and gotchas

1. **Filters are not path-aware.** `open("/etc/shadow", ...)` and
   `open("/tmp/foo", ...)` are indistinguishable to a seccomp filter —
   it sees the pointer value, not the string. To filter on *which*
   file, use AppArmor.
2. **seccomp-bpf filters cannot dereference pointer arguments** (the
   verifier forbids loads other than from `seccomp_data`). So you can
   filter `open` but cannot see *what* path it was called with.
3. **Filters are inherited.** A filter installed before `fork`/`exec`
   applies to all descendants. Adding a more restrictive filter is
   fine; relaxing is not. Filters stack — each is run, and the most
   restrictive verdict wins.
4. **`SECCOMP_RET_USER_NOTIF` (Linux 5.0+) lets you do emulation.**
   A supervisor process can `ioctl(SECCOMP_IOCTL_NOTIF_RECV)` to be
   notified, evaluate the call's args via `process_vm_readv`, and
   `ioctl(SECCOMP_IOCTL_NOTIF_SEND)` to return a verdict. This is the
   modern replacement for the `RET_TRAP` + `ptrace` approach and is
   what modern container runtimes use to allow selected privileged
   syscalls (e.g. `mknod` of a device) safely.
5. **Glibc and seccomp.** Modern glibc occasionally adds new syscalls
   on hot paths (e.g. `clone3` on newer glibc). Denylisting by
   default can break subtly months later. Allowlisting (default
   deny, allow specific list) is more robust but more painful to
   maintain.

## References

1. **seccomp(2) manpage** —
   <https://man7.org/linux/man-pages/man2/seccomp.2.html>
2. **Kernel docs: user-facing API** —
   <https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.rst>
3. **Docker seccomp security profile** —
   <https://docs.docker.com/engine/security/seccomp/>
4. **Chromium sandbox design docs** —
   <https://www.chromium.org/developers/design-documents/sandbox/>
5. **`libseccomp` library home page** —
   <https://github.com/seccomp/libseccomp>
6. **LWN: "Seccomp and the road to containers"** —
   <https://lwn.net/Articles/656307/>
7. **LWN: "A seccomp user notification mechanism" (5.0 user_notif)** —
   <https://lwn.net/Articles/785741/>
8. **`seccomp-tools` (BPF disassembler)** —
   <https://github.com/david942j/seccomp-tools>
9. **`prctl(2)` — PR_SET_NO_NEW_PRIVS** —
   <https://man7.org/linux/man-pages/man2/prctl.2.html>
