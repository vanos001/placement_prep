# The rt_sig* Kernel ABI — rt_sigaction, rt_sigprocmask, and Friends (IF-014 – IF-016)

Almost nobody calls the `rt_sig*` system calls directly — and that is the point of this
chapter. The glibc wrappers you use (`sigaction(3)`, `sigprocmask(3)`, `sigsuspend(3)`,
`sigpending(3)`, `sigtimedwait(3)`) hide a per-architecture binary interface that differs in
struct layout, flag-bit values, `how`-constant values, and the ownership of the signal
trampoline. This matters when you read `strace(1)` output, write a libc or a runtime,
implement seccomp filters, or port to a new architecture. (IF-016 is the cross-link inventory
at the end: the existing per-syscall pages this chapter supplements.)

## Why the rt_* syscalls exist

Per [signal(7)](https://man7.org/linux/man-pages/man7/signal.7.html) and the VERSIONS sections
of the man pages: Linux 2.0 and earlier tracked signal masks in a fixed 32-bit `sigset_t`. The
real-time range (32–64, 128 on mips — see
[real-time signals](../signals/real-time-signals.md)) needed wider sets, so Linux 2.2 added a
parallel family of syscalls taking a `kernel_sigset_t` of `_NSIG` bits plus an explicit size
argument:

| Old (Linux ≤ 2.0) | New (Linux ≥ 2.2) |
|-------------------|-------------------|
| `sigaction(2)`    | `rt_sigaction(2)` |
| `sigprocmask(2)`  | `rt_sigprocmask(2)` |
| `sigpending(2)`   | `rt_sigpending(2)` |
| `sigsuspend(2)`   | `rt_sigsuspend(2)` |
| `sigtimedwait(2)` | `rt_sigtimedwait(2)` |
| `sigreturn(2)`    | `rt_sigreturn(2)` |

The glibc wrappers transparently call the `rt_*` forms where available (per
[sigaction(2)](https://man7.org/linux/man-pages/man2/sigaction.2.html) and
[sigprocmask(2)](https://man7.org/linux/man-pages/man2/sigprocmask.2.html) VERSIONS).

## rt_sigaction(2) (IF-014)

```c
/* no glibc wrapper — libc's sigaction(3) *is* the wrapper */
int syscall(SYS_rt_sigaction, int signum,
            const struct kernel_sigaction *act,
            struct kernel_sigaction *oldact,
            size_t sigsetsize);
```

The fourth argument, **`sigsetsize`**, specifies the size in bytes of the `sa_mask` sets in
both structs; it is currently required to equal `sizeof(sigset_t)` (8 bytes on 64-bit, 8× the
kernel long — i.e. `_NSIG/_NSIG_BPW` words) or the call fails `EINVAL` (per sigaction(2)
VERSIONS). The size exists so the kernel can grow the ABI without breaking old binaries —
newer kernels reject mismatched sizes instead of guessing.

### The kernel struct differs per architecture

The *libc* `struct sigaction` is a POSIX-visible fiction; the kernel's per-arch UAPI struct is
what crosses the syscall boundary (all layouts below verified in the UAPI headers):

| Architecture | Kernel `struct sigaction` field order (user-space view) | Notes |
|--------------|----------------------------------------------------------|-------|
| asm-generic (arm64, riscv, loongarch inherit) | `handler; flags; restorer*; mask` | mask last "for extensibility"; restorer present only when the arch defines `SA_RESTORER` |
| x86-64 | `handler; flags; restorer; mask` | `SA_RESTORER = 0x04000000` |
| x86 (i386) | `handler|sigaction` (union); `mask; flags; restorer` | mask **before** flags — the classic i386 layout |
| arm | `handler|sigaction` (union); `mask; flags; restorer` | also defines `SA_THIRTYTWO 0x02000000` |
| s390 | union; `flags; restorer; mask` | header comments document a historic 31-bit/64-bit split that made the uapi struct unusable — glibc has always used its own definitions |
| powerpc | `handler; flags; restorer; mask` | also `struct old_sigaction` (32-bit mask) for the legacy syscall |
| m68k | union; `mask; flags; restorer` | i386-style ordering; no `SA_RESTORER` bit defined |
| mips | `flags (unsigned int!); handler; mask` | **no restorer field at all** — the `SA_RESTORER` functionality was removed for 2.5.48, only the bit definition remains as a placeholder; `stack_t` field order also differs (`ss_sp, ss_size, ss_flags`) |
| alpha | union; `mask; int flags` | no restorer; `int` flags |
| sparc | `__new_sigaction`: `handler; flags; restorer; mask` (restorer "not used by Linux/SPARC yet") | separate `__old_sigaction` with 32-bit mask |
| sh | includes asm-generic; adds `SA_RESTORER 0x04000000` and `struct old_sigaction` | |

The `SA_*` flag *values* also differ per architecture — asm-generic uses
`SA_NOCLDSTOP 0x1, SA_NOCLDWAIT 0x2, SA_SIGINFO 0x4, … SA_ONSTACK 0x08000000, SA_RESTART
0x10000000, SA_NODEFER 0x40000000, SA_RESETHAND 0x80000000`, while **alpha** packs
`ONSTACK/RESTART/NOCLDSTOP/NODEFER/RESETHAND/NOCLDWAIT/SIGINFO` into bits 0–6, **sparc** uses
`0x8/0x1/0x2/0x4/0x20/0x100/0x200`, **mips** has `SA_SIGINFO = 0x8` and `SA_NOCLDWAIT =
0x10000`, and **parisc** uses low bits `0x1–0x80` with no `SA_RESTORER` (all verified in the
respective `arch/*/include/uapi/asm/signal.h`). Likewise the `how` constants for
`rt_sigprocmask` are `0/1/2` (BLOCK/UNBLOCK/SETMASK) on asm-generic but `1/2/3` on alpha and
mips and `1/2/4` on sparc. **Conclusion for IF-014/IF-015: any code constructing these structs
by hand must be written per architecture from the headers — this is exactly why libcs exist.**

### sa_restorer: why glibc inserts its own trampoline

Per sigaction(2) VERSIONS and [sigreturn(2)](https://man7.org/linux/man-pages/man2/sigreturn.2.html)
NOTES: when a handler returns, control passes to a piece of user-space code called the
*signal trampoline*, which invokes `sigreturn(2)`/`rt_sigreturn(2)` to restore the interrupted
context (mask, alternate stack, registers) from the frame the kernel built on the user stack.
The kernel does not provide this code itself; it is supplied per architecture:

- Historically it lived **on the user stack**; contemporary systems mark the stack
  non-executable, so the trampoline now lives in the **vDSO** (e.g. x86-64) **or in the C
  library** (per sigreturn(2) NOTES).
- Where the trampoline is in the C library, the glibc `sigaction` wrapper **writes the
  trampoline's address into `act.sa_restorer` and sets the `SA_RESTORER` flag** before
  invoking `rt_sigaction(2)` (per sigaction(2) VERSIONS). Applications must never set these —
  the libc owns the code that matches its own unwinding and stack layout.
- On architectures without `SA_RESTORER` (mips, alpha, parisc), the kernel arranges the
  return path itself (fixed entry points / vDSO) — another reason the struct layouts differ.

glibc also filters *its* reserved signals here: the `sigaction` wrapper refuses (`EINVAL`)
attempts to install handlers for the two NPTL-internal real-time signals (per sigaction(2)
VERSIONS; see [real-time signals](../signals/real-time-signals.md)).

## rt_sigprocmask(2) (IF-015)

```c
int syscall(SYS_rt_sigprocmask, int how,
            const kernel_sigset_t *set, kernel_sigset_t *oldset,
            size_t sigsetsize);
```

Same shape as the libc call plus the trailing `sigsetsize` (fixed arch-specific value, per
sigprocmask(2) VERSIONS). The `how` constants are the per-arch kernel values discussed above;
glibc translates POSIX `SIG_BLOCK`/`SIG_UNBLOCK`/`SIG_SETMASK`. The legacy `sigprocmask`
syscall (32-bit `old_kernel_sigset_t`) still exists but is deprecated. The glibc wrapper
additionally **silently ignores** attempts to block the two NPTL-internal RT signals (per
sigprocmask(2) VERSIONS) — behavior applications relying on "block everything"
(`sigfillset`) get for free.

## Cross-link inventory: related kernel-side pages (IF-016)

The book already documents the kernel side of the family; this section is the entry point to
those pages (semantics at the syscall level, syscall numbers, kernel versions):

- [rt_sigaction(2)](../../syscalls/signals-time/rt_sigaction.md) — raw ABI, per-arch struct notes
- [rt_sigprocmask(2)](../../syscalls/signals-time/rt_sigprocmask.md) — mask manipulation at the syscall level
- [rt_sigsuspend(2)](../../syscalls/signals-time/rt_sigsuspend.md) — the atomic mask swap behind `sigsuspend(3)`
- [sigaltstack(2)](../../syscalls/signals-time/sigaltstack.md) — alternate handler stacks used with `SA_ONSTACK`
- [sigreturn(2)](../../syscalls/signals-time/sigreturn.md) — the trampoline's destination, frame layout
- [pause(2)](../../syscalls/signals-time/pause.md) — the "sleep until any signal" primitive
- [kill(2)](../../syscalls/signals-time/kill.md) and [tgkill(2)](../../syscalls/signals-time/tgkill.md) — the sending side
- Application-level counterparts: [sigaction and signal](./sigaction-signal.md),
  [signal masks](./signal-masks.md), [sigwait and sigsuspend](./sigwait-sigsuspend.md)

## Related Topics

- [sigaction and signal](./sigaction-signal.md) — the libc contract these syscalls implement
- [Standard signals](../signals/standard-signals.md) — per-arch numbering and flag constants
- [Real-time signals](../signals/real-time-signals.md) — why the sets widened in 2.2
- [Per-syscall pages: signals and time](../../syscalls/signals-time/overview.md)

## References

- *sigaction(2)* (VERSIONS: C library/kernel differences, rt_sigaction), man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigaction.2.html>
- *sigprocmask(2)* (VERSIONS: rt_sigprocmask), man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigprocmask.2.html>
- *sigreturn(2)* (trampoline ownership), man-pages 6.19, <https://man7.org/linux/man-pages/man2/sigreturn.2.html>
- *signal(7)*, <https://man7.org/linux/man-pages/man7/signal.7.html> (old/new syscall table)
- *Linux kernel UAPI headers* (struct layouts and flag values, verified): [`include/uapi/asm-generic/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/asm-generic/signal.h), [`include/uapi/asm-generic/signal-defs.h`](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/asm-generic/signal-defs.h), [`arch/x86/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/include/uapi/asm/signal.h), [`arch/mips/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/mips/include/uapi/asm/signal.h), [`arch/alpha/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/alpha/include/uapi/asm/signal.h), [`arch/sparc/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/sparc/include/uapi/asm/signal.h), [`arch/parisc/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/parisc/include/uapi/asm/signal.h), [`arch/s390/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/s390/include/uapi/asm/signal.h), [`arch/arm/include/uapi/asm/signal.h`](https://raw.githubusercontent.com/torvalds/linux/master/arch/arm/include/uapi/asm/signal.h)
