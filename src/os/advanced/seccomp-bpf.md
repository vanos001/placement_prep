# Seccomp Deep Dive: BPF Filters, Action Semantics, and Sandbox Layering

seccomp is the kernel's per-thread **syscall firewall**: as a syscall enters
the kernel, a policy decides whether it proceeds, fails, traps, or kills the
caller. Unlike an LSM, seccomp sees only the syscall number, argument values,
and the caller's instruction pointer - never the objects arguments point to.

> **Interview one-liner:** "seccomp is a one-way, per-thread BPF filter on the
> syscall ABI - it decides on `nr` and raw argument values, which is exactly
> why it cannot judge file paths; paths are LSM/Landlock territory."

## What seccomp Can and Cannot See

seccomp fires first in the kernel entry path, before LSM hooks and VFS work:

```text
  userspace                kernel entry path
------------------     -------------------------------
 app: openat() ----->  syscall entry (arch trap)
                         | audit / ptrace-stop
                         v
                       [seccomp filter tree]   sees: nr, arch,
                         |                        instruction_pointer, args[6]
                         v
                       [LSM: SELinux/AppArmor/Landlock/BPF-LSM]
                         |                 sees objects: inode, dentry, labels
                         v
                       syscall body executes
```

Inputs are a fixed 64-byte snapshot (`struct seccomp_data`). A filter can test
that a pointer argument *has some value*, but the bytes it points to are not
copied and can change between the filter's decision and the kernel's
`copy_from_user()`. This argument-pointer problem is why real policies are
written over syscall numbers plus small integer arguments (`flags`, `domain`,
`request`) - never over strings.

## Strict Mode vs Filter Mode

| Property | SECCOMP_MODE_STRICT (1) | SECCOMP_MODE_FILTER (2) |
|---|---|---|
| Entry | `SECCOMP_SET_MODE_STRICT` (op 0) | `SECCOMP_SET_MODE_FILTER` (op 1) |
| Policy | hard-coded allowlist | user-supplied cBPF over `seccomp_data` |
| Violation | thread killed (SIGKILL if last thread) | per `SECCOMP_RET_*` action |
| Since | Linux 2.6.12 (2005) | Linux 3.5 (2012) |
| Real use | effectively none - `mmap`, `openat` all die | Docker, runc, Chromium, systemd, sshd |

The man page, verbatim: *"The only system calls that the calling thread is
permitted to make are read(2), write(2), _exit(2) (but not exit_group(2)), and
sigreturn(2). Other system calls result in the termination of the calling
thread, or termination of the entire process with the SIGKILL signal when
there is only one thread."* A program cannot even `mmap` its heap, and `_exit`
(one thread) is allowed while `exit_group` (multi-threaded shutdown) is not.
Filter mode trades that rigidity for a tiny VM: a classic-BPF program
validated once at load, then executed on every syscall.

## seccomp_data and the cBPF Program Model

The layout filters jump through, from `include/uapi/linux/seccomp.h`:

| Offset | Field | Type | Filter-visible meaning |
|---|---|---|---|
| 0 | `nr` | `int` | syscall number under the caller's ABI |
| 4 | `arch` | `u32` | `AUDIT_ARCH_*` calling convention (`0xC000003E` = x86-64) |
| 8 | `instruction_pointer` | `u64` | user PC at the syscall - splits libc from JIT code |
| 16 | `args[0..5]` | `u64[6]` | raw arguments, **always 64-bit** regardless of ABI |

- **Why cBPF, not eBPF:** the program is loop-free (the verifier rejects
  cycles), bounded to `BPF_MAXINSNS` = 4096 instructions per filter with a
  32768-instruction cap across a thread's filter tree, and must terminate in a
  `RET` - straight-line evaluation, no verifier complexity, no JIT needed.
- **The `arch` check is mandatory discipline.** Syscall numbers are unique
  only per calling convention; skipping `AUDIT_ARCH_*` lets an `nr` from a
  foreign ABI be misinterpreted. Docker's profile carries `archMap` entries so
  runc emits one arch-guarded chain per ABI.
- **`instruction_pointer` is the only provenance signal**: sandboxes use it
  to allow syscalls from known text regions, deny them from JIT mappings.

## Actions: the SECCOMP_RET_* Table

A filter's `RET` carries a 32-bit value: high half is the action, low 16 bits
carry errno data. Values from `include/uapi/linux/seccomp.h`:

| Action | Value | What the syscall experiences |
|---|---|---|
| `SECCOMP_RET_KILL_PROCESS` | `0x80000000` | whole process dies (4.14+) - no handler possible |
| `SECCOMP_RET_KILL_THREAD` | `0x00000000` | calling thread dies; alias `SECCOMP_RET_KILL` |
| `SECCOMP_RET_TRAP` | `0x00030000` | `SIGSYS` with `si_code=SYS_SECCOMP`; not resumable |
| `SECCOMP_RET_ERRNO` | `0x00050000` | returns `-errno` (low 16 bits); silent, cheapest deny |
| `SECCOMP_RET_USER_NOTIF` | `0x7fc00000` | caller blocks; supervisor fd gets the request (`-ENOSYS` if none) |
| `SECCOMP_RET_TRACE` | `0x7ff00000` | hands the syscall to a `ptrace()` tracer; `-ENOSYS` if absent |
| `SECCOMP_RET_LOG` | `0x7ffc0000` | allow + audit log line (profile dry-running) |
| `SECCOMP_RET_ALLOW` | `0x7fff0000` | proceed normally |

Stacked filters (each `seccomp(SET_MODE_FILTER)` call adds one) combine per
the man page as *"the first-seen action value of highest precedence ... returned
by execution of all of the filters"* - the table order above is that
precedence, `KILL_PROCESS` strongest, `ALLOW` weakest. A second stricter
filter tightens the sandbox; nothing already denied can be loosened.

## Filter Lifecycle: Inheritance, TSYNC, and the No-Uninstall Rule

seccomp state is monotonic - it can only shrink what a thread may do:

| Fact | Mechanism |
|---|---|
| Unprivileged load | requires `PR_SET_NO_NEW_PRIVS` (makes setuid exec inert), else `CAP_SYS_ADMIN` |
| Inheritance | filters cross `fork()`/`clone()` and survive `execve()` |
| No uninstall | no delete operation; the only exit is thread death |
| Thread sync | `SECCOMP_FILTER_FLAG_TSYNC` pulls all threads onto one filter tree |

The kernel doc, verbatim, on inheritance: *"If fork/clone and execve are
allowed by @prog, any child processes will be constrained to the same filters
and system call ABI as the parent."* Runtimes exploit this by loading the
filter before exec-ing container init, so the new binary is born sandboxed;
and because there is no uninstall, the sandbox survives later credential
changes. On authorization, again verbatim: *"the task must call
prctl(PR_SET_NO_NEW_PRIVS, 1) or run with CAP_SYS_ADMIN privileges in its
namespace. If these are not true, -EACCES will be returned."* TSYNC matters
because filters are per-thread: a `pthread_create` raced after load starts
unsandboxed; with `TSYNC_ESRCH` (4.17+) an unsyncable thread yields `-ESRCH`
instead of killing the process - semantics Go's M:N scheduler relies on.

## User Notification: NEW_LISTENER, the ioctl Interface, and TOCTOU

The mechanism: the loader passes **`SECCOMP_FILTER_FLAG_NEW_LISTENER`** to
`seccomp(SECCOMP_SET_MODE_FILTER, ...)` and receives a **listener fd**,
transferable over Unix-domain fd passing; the supervisor drives it with the
`SECCOMP_IOCTL_*` operations from the uapi header:

| ioctl | Direction | Purpose |
|---|---|---|
| `SECCOMP_IOCTL_NOTIF_RECV` | supervisor <- kernel | pop `struct seccomp_notif` (id, pid, `seccomp_data`); caller stays blocked |
| `SECCOMP_IOCTL_NOTIF_SEND` | supervisor -> kernel | reply via `seccomp_notif_resp` (`val`, `error`, or `SECCOMP_USER_NOTIF_FLAG_CONTINUE`) |
| `SECCOMP_IOCTL_NOTIF_ADDFD` | supervisor -> kernel | install one of the supervisor's fds into the target (device/file proxies) |

`SECCOMP_USER_NOTIF_FLAG_CONTINUE` is the dangerous one. The uapi header says
it plainly: continuing a syscall is *"problematic because of an inherent
TOCTOU"* - while the target waits for the reply, another thread of the same
task can rewrite the memory behind any pointer argument, so the bytes the
supervisor inspected are not the bytes the kernel will use. Hence the header's
exam-answer conclusion: the notifier *"cannot be used to implement a security
policy"*; it is an interposition tool for **more**-privileged supervisors doing
safe emulation (mount helpers, `/proc` emulation, device passthrough) behind
some other enforcement layer. The same race is why the filter itself cannot
dereference `args`. Deep C coverage:
[Seccomp Notify](../../linux/containers/seccomp-notify.md).

## How Docker and Runtimes Build Default Profiles

Docker's default profile is data, not code: it lives in the
[`moby/profiles`](https://github.com/moby/profiles) repo
(`seccomp/default.json`) and is compiled to cBPF by runc via libseccomp. The
live file (inspected 2026) is a **whitelist**: `defaultAction: SCMP_ACT_ERRNO`
with `defaultErrnoRet: 1` (deny with `EPERM` anything not explicitly allowed);
`archMap` entries mapping `SCMP_ARCH_X86_64`, `SCMP_ARCH_AARCH64`, ... onto
`AUDIT_ARCH_*` values; an allow group of ~360 syscall names plus conditional
groups (`socket` gated on capabilities, `personality` restricted).

Docker's docs keep a "Significant syscalls blocked by the default profile"
table - e.g. `kexec_load` ("Deny loading a new kernel for later execution.
Also gated by CAP_SYS_BOOT") and `keyctl` ("Prevent containers from using the
kernel keyring, which is not namespaced"). Note the layering: syscalls already
gated by dropped capabilities still get an explicit deny, so the profile holds
even if the capability drop is misconfigured. Kubernetes exposes the same
machinery as `securityContext.seccompProfile` - `RuntimeDefault` (delegate to
the CRI runtime), `Localhost` (node-local custom file), `Unconfined` - see
[Kubernetes](../containers/kubernetes.md) and the Kubernetes seccomp tutorial.
Tuning is a loop: run under `SCMP_ACT_LOG`, harvest observed syscalls from
audit logs, extend the allowlist, re-ship.

## Filter Cost: What Every Syscall Pays

Evaluation is linear in instructions *executed* before the terminating `RET`;
loop-free cBPF bounds it by program length. Back-of-envelope with stated
assumptions: if a compare-and-branch step costs a few ns of kernel time, a
20-step path is tens of ns - well under 1% of a fast 200 ns syscall; even 100k
syscalls/s through a 100-step path pays about 1% of a core. That is why
seccomp ships in every container runtime while ptrace-based interposition pays
orders of magnitude more per call. The demo below makes "steps" concrete.

## seccomp vs Landlock vs AppArmor/SELinux

These answer different questions, and production sandboxes stack them:

| Mechanism | Hook point | Sees | Scope | Revocable | Load privilege |
|---|---|---|---|---|---|
| seccomp-BPF | syscall entry | nr, args, arch, PC | whole kernel ABI | no | none (`no_new_privs`) |
| Landlock | LSM hooks | file paths, rights | filesystem only | no | none (unprivileged) |
| AppArmor | LSM hooks | pathnames, objects | paths + caps | yes (admin) | root + policy |
| SELinux | LSM hooks | labeled objects | all classes | yes (admin) | root + policy |
| BPF-LSM | LSM hooks | anything BPF computes | custom, per-hook | yes | root, `CONFIG_BPF_LSM` |

The crisp formulation: **seccomp reduces the syscall surface; LSM-family
mechanisms decide access to objects**. seccomp can say "no `openat` from
JIT-mapped code" but never "no `openat` on `/etc/shadow`" - it never resolves
paths. That is [Landlock](../../linux/security/landlock.md)'s job, or
AppArmor/SELinux per [MAC](../../linux/security/mac.md), or BPF-LSM per
[eBPF Security](../../security/ebpf-security.md). Docker's real sandbox is
the conjunction: namespaces + capabilities + seccomp + an LSM.

## Demo: a cBPF Mini-VM

Raw `sock_filter` tuples (`0x20` = `LD|W|ABS`, `0x15` = `JEQ|K`, `0x06` =
`RET|K`) encode a toy seccomp policy, evaluated over synthetic `seccomp_data`
records packed as the kernel lays them out:

```python
import struct

KILL_PROCESS, KILL_THREAD, TRAP, ERRNO, ALLOW = 0x80000000, 0, 0x00030000, 0x00050000, 0x7fff0000
MASK = 0xFFFF0000                      # SECCOMP_RET_ACTION_FULL
X86_64, I386 = 0xC000003E, 0x40000003  # AUDIT_ARCH_X86_64, AUDIT_ARCH_I386

# sock_filter = (code, jt, jf, k); JEQ: A==k ? pc+=1+jt : pc+=1+jf.
# Policy: kill foreign arch + ptrace(101); trap execve(59); deny ioctl(16)
# unless request==TIOCGWINSZ (0x5413); allow the rest.
PROG = [
    (0x20, 0, 0, 4),           #  0: A <- u32[4] = arch
    (0x15, 0, 9, X86_64),      #  1: arch != x86_64 -> 11
    (0x20, 0, 0, 0),           #  2: A <- u32[0] = nr
    (0x15, 7, 0, 101),         #  3: nr == ptrace  -> 11
    (0x15, 5, 0, 59),          #  4: nr == execve  -> 10
    (0x15, 0, 2, 16),          #  5: nr != ioctl   ->  8
    (0x20, 0, 0, 24),          #  6: A <- u32[24] = args[1] low 32
    (0x15, 0, 1, 0x5413),      #  7: TIOCGWINSZ    -> 8, else 9
    (0x06, 0, 0, ALLOW),       #  8: allow
    (0x06, 0, 0, ERRNO | 25),  #  9: ERRNO(ENOTTY)
    (0x06, 0, 0, TRAP),        # 10: SIGSYS
    (0x06, 0, 0, KILL_THREAD), # 11: kill
]

def seccomp_data(nr, arch, ip, args):  # kernel's 64-byte little-endian snapshot
    args = [a & 0xFFFFFFFFFFFFFFFF for a in args]
    return struct.pack('<IIQ6Q', nr, arch, ip, *(args + [0] * (6 - len(args))))

def run(data):                         # returns (action, steps executed)
    a, pc, steps = 0, 0, 0
    while True:
        code, jt, jf, k = PROG[pc]
        steps += 1
        if code == 0x20:
            a = struct.unpack_from('<I', data, k)[0]; pc += 1
        elif code == 0x15:
            pc += 1 + (jt if a == k else jf)
        else:
            return k, steps

def decode(v):
    act, err = v & MASK, v & 0xFFFF
    return {ALLOW: 'ALLOW', TRAP: 'TRAP (SIGSYS)', KILL_PROCESS: 'KILL_PROCESS',
            ERRNO: 'ERRNO(%d)' % err}.get(act, 'KILL_THREAD')

RECORDS = [                            # (label, nr, arch, args[0..])
    ('read(0, buf, 4096)',                0,   X86_64, [0, 0x7ffd0000, 4096]),
    ('execve("/bin/sh", argv, env)',      59,  X86_64, [0x7ffd1000, 0x7ffd2000, 0]),
    ('ptrace(PTRACE_ATTACH, pid)',        101, X86_64, [16, 4242, 0, 0]),
    ('ioctl(1, TIOCGWINSZ, &ws)',         16,  X86_64, [1, 0x5413, 0x7ffd3000]),
    ('ioctl(1, 0x1234, &x)',              16,  X86_64, [1, 0x1234, 0x7ffd3000]),
    ('openat(...) under AUDIT_ARCH_I386', 295, I386,   [-100, 0x1000, 0, 0]),
]

print('filter: %d instructions = %d bytes packed (BPF_MAXINSNS cap: 4096)'
      % (len(PROG), len(PROG) * 8))
print('%-36s %4s %-7s %-15s %5s' % ('record', 'nr', 'arch', 'decision', 'steps'))
print('-' * 74)
for name, nr, arch, args in RECORDS:
    act, steps = run(seccomp_data(nr, arch, 0x555555554000, args))
    print('%-36s %4d %-7s %-15s %5d'
          % (name, nr, 'x86_64' if arch == X86_64 else 'i386', decode(act), steps))
```

Output (real run, byte-identical across two executions):

```text
filter: 12 instructions = 96 bytes packed (BPF_MAXINSNS cap: 4096)
record                                 nr arch    decision        steps
--------------------------------------------------------------------------
read(0, buf, 4096)                      0 x86_64  ALLOW               7
execve("/bin/sh", argv, env)           59 x86_64  TRAP (SIGSYS)       6
ptrace(PTRACE_ATTACH, pid)            101 x86_64  KILL_THREAD         5
ioctl(1, TIOCGWINSZ, &ws)              16 x86_64  ALLOW               9
ioctl(1, 0x1234, &x)                   16 x86_64  ERRNO(25)           9
openat(...) under AUDIT_ARCH_I386     295 i386    KILL_THREAD         3
```

`read` matches after 7 dispatched instructions, the denied `ioctl` after 9, a
foreign-arch record dies in 3 - cheap because cBPF is loop-free dispatch.

## Where Seccomp Sandboxes Break

- **Tightened until apps fail.** `EPERM` from `SCMP_ACT_ERRNO` surfaces as
  mysterious deep failures; develop under `TRAP`/`LOG`, ship `ERRNO`.
- **Per-thread state + thread pools.** Forgetting `TSYNC` leaves unsandboxed
  threads; Go runtimes and checkpointing need `TSYNC_ESRCH` semantics.
- **ABI confusion.** Skipping the `arch` guard makes a filter bypassable -
  syscall numbers are only unique per calling convention.
- **Stacking surprises.** A library's filter cannot widen yours, but a second
  `USER_NOTIF`/`TRACE` consumer can interpose on syscalls an earlier
  supervisor thought it owned; conservative deny lists also gate
  `io_uring` syscalls - see [io_uring](../kernel/io-uring.md).

## References

1. seccomp(2) man page: <https://man7.org/linux/man-pages/man2/seccomp.2.html>
2. Kernel docs, seccomp filter: <https://docs.kernel.org/userspace-api/seccomp_filter.html>
3. `include/uapi/linux/seccomp.h`: <https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/seccomp.h>
4. Docker Engine seccomp docs: <https://docs.docker.com/engine/security/seccomp/>
5. Docker default profile: <https://github.com/moby/profiles>
6. Kubernetes seccomp tutorial: <https://kubernetes.io/docs/tutorials/security/seccomp/>
