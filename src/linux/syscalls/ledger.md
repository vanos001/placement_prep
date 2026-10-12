# Syscall Coverage Ledger

## Overview

This ledger is the authoritative inventory for the [System Call Encyclopedia](./overview.md).
It was **generated from primary sources**, not assembled from memory:

| Column | Source |
|---|---|
| Name | Union of the union of all names in the per-arch syscall tables below |
| x86_64 numbers | `arch/x86/entry/syscalls/syscall_64.tbl` (torvalds/linux master) |
| i386 numbers | `arch/x86/entry/syscalls/syscall_32.tbl` (torvalds/linux master) |
| g64 (asm-generic) | `scripts/syscall.tbl`, abi `common` + `64` — the flattened asm-generic table shared by arm64 (via `include/uapi/asm-generic/unistd.h`), riscv, loongarch, csky |
| arm | `arch/arm/tools/syscall.tbl`, EABI columns |
| Since | man-pages `syscalls(2)` version table (kernel version in which the name first appeared) |
| Man page | presence of `man2/<name>.2` in the man-pages git tree |

`—` means the interface does not exist for that architecture (this is meaningful:
arm64 and other asm-generic architectures never had `fork`, `open`, `pipe`, `stat`
or the old socket call variants — those exist only as libc compat wrappers).

**Status vocabulary** (defined in the [encyclopedia overview](../interface-encyclopedia.md)):
`not-started` → name inventoried only · `researched` → sources read, entry drafted ·
`documented` → full entry with signature, semantics, errors, security notes, references ·
`source-limited` → documented from fewer sources than the entry should have.

**Scope caveats.** The inventory reflects the kernel sources it was generated from
(linux master, fall 2026). x32 variants (numbers ≥ 512 on x86_64) are tracked in the
[x86_64 table itself] and mentioned in notes rather than as separate rows. Multiplexed
interfaces (`ioctl`, `fcntl`, `prctl`, `bpf`, `perf_event_open`) get one ledger row each
and their sub-interfaces live in the linked chapter pages. MIPS, parisc, powerpc, s390,
sparc and alpha have their own per-architecture numbering tables which are *not* columns
here (see the [overview](./overview.md) for how their tables relate); their absence from
the numeric columns does not mean the syscall is absent on those architectures.

## Ledger

Legend for numbers columns: `x64` = x86_64, `i386` = 32-bit x86, `g64` = asm-generic
64-bit (arm64/riscv/loongarch), `arm` = arm32 EABI.

### process

| ID | Name | Numbers | Since | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| SC-acct | [acct](https://man7.org/linux/man-pages/man2/acct.2.html) | x64 163 · i386 51 · g64 89 · arm 51 | 1.0 | researched | [acct](./process/acct.md) | —brief |
| SC-arch_prctl | [arch_prctl](https://man7.org/linux/man-pages/man2/arch_prctl.2.html) | x64 158 · i386 384 · g64 — · arm — | 2.6 | researched | [arch_prctl](./process/arch_prctl.md) | —brief |
| SC-capget | [capget](https://man7.org/linux/man-pages/man2/capget.2.html) | x64 125 · i386 184 · g64 90 · arm 184 | 2.2 | documented | [capget](./process/capget.md) | —grouped |
| SC-capset | [capset](https://man7.org/linux/man-pages/man2/capset.2.html) | x64 126 · i386 185 · g64 91 · arm 185 | 2.2 | documented | [capset](./process/capget.md) | —grouped |
| SC-chown32 | [chown32](https://man7.org/linux/man-pages/man2/chown32.2.html) | x64 — · i386 212 · g64 — · arm 212 | 2.4 | not-started | [chown32](./process/chown.md) | — |
| SC-clone | [clone](https://man7.org/linux/man-pages/man2/clone.2.html) | x64 56 · i386 120 · g64 220 · arm 120 | 1.0 | documented | [clone](./process/clone.md) | —full |
| SC-clone2 | [clone2](https://man7.org/linux/man-pages/man2/clone2.2.html) | x64 — · i386 — · g64 — · arm — | 2.4 | documented | [clone2](./process/clone.md) | —grouped |
| SC-clone3 | [clone3](https://man7.org/linux/man-pages/man2/clone3.2.html) | x64 435 · i386 435 · g64 435 · arm 435 | 5.3 | documented | [clone3](./process/clone.md) | —full |
| SC-execv | execv | x64 — · i386 — · g64 — · arm — | 2.0 | not-started | [execv](./process/execv.md) | — |
| SC-execve | [execve](https://man7.org/linux/man-pages/man2/execve.2.html) | x64 59 · i386 11 · g64 221 · arm 11 | 1.0 | documented | [execve](./process/execve.md) | —full |
| SC-execveat | [execveat](https://man7.org/linux/man-pages/man2/execveat.2.html) | x64 322 · i386 358 · g64 281 · arm 387 | 3.19 | documented | [execveat](./process/execveat.md) | —grouped |
| SC-exit | [exit](https://man7.org/linux/man-pages/man2/exit.2.html) | x64 60 · i386 1 · g64 93 · arm 1 | 1.0 | documented | [exit](./process/_exit.md) | —grouped |
| SC-exit_group | [exit_group](https://man7.org/linux/man-pages/man2/exit_group.2.html) | x64 231 · i386 252 · g64 94 · arm 248 | 2.6 | documented | [exit_group](./process/exit_group.md) | —grouped |
| SC-fchown32 | [fchown32](https://man7.org/linux/man-pages/man2/fchown32.2.html) | x64 — · i386 207 · g64 — · arm 207 | 2.4 | not-started | [fchown32](./process/fchown.md) | — |
| SC-fork | [fork](https://man7.org/linux/man-pages/man2/fork.2.html) | x64 57 · i386 2 · g64 — · arm 2 | 1.0 | documented | [fork](./process/fork.md) | —full |
| SC-futex | [futex](https://man7.org/linux/man-pages/man2/futex.2.html) | x64 202 · i386 240 · g64 98 · arm 240 | 2.6 | documented | [futex](./process/futex.md) | —full |
| SC-futex_requeue | futex_requeue | x64 456 · i386 456 · g64 456 · arm 456 | 6.14 | source-limited | [futex_requeue](./process/futex.md) | —grouped |
| SC-futex_time64 | futex_time64 | x64 — · i386 422 · g64 — · arm 422 | — | documented | [futex_time64](./process/futex.md) | —grouped |
| SC-futex_wait | futex_wait | x64 455 · i386 455 · g64 455 · arm 455 | 6.14 | source-limited | [futex_wait](./process/futex.md) | —grouped |
| SC-futex_waitv | futex_waitv | x64 449 · i386 449 · g64 449 · arm 449 | — | documented | [futex_waitv](./process/futex.md) | —grouped |
| SC-futex_wake | futex_wake | x64 454 · i386 454 · g64 454 · arm 454 | 6.14 | source-limited | [futex_wake](./process/futex.md) | —grouped |
| SC-get_robust_list | [get_robust_list](https://man7.org/linux/man-pages/man2/get_robust_list.2.html) | x64 274 · i386 312 · g64 100 · arm 339 | 2.6.17 | researched | [get_robust_list](./process/get_robust_list.md) | —brief |
| SC-getegid | [getegid](https://man7.org/linux/man-pages/man2/getegid.2.html) | x64 108 · i386 50 · g64 177 · arm 50 | 1.0 | documented | [getegid](./process/getgid.md) | —grouped |
| SC-getegid32 | [getegid32](https://man7.org/linux/man-pages/man2/getegid32.2.html) | x64 — · i386 202 · g64 — · arm 202 | 2.4 | documented | [getegid32](./process/getegid.md) | —grouped |
| SC-geteuid | [geteuid](https://man7.org/linux/man-pages/man2/geteuid.2.html) | x64 107 · i386 49 · g64 175 · arm 49 | 1.0 | documented | [geteuid](./process/getuid.md) | —grouped |
| SC-geteuid32 | [geteuid32](https://man7.org/linux/man-pages/man2/geteuid32.2.html) | x64 — · i386 201 · g64 — · arm 201 | 2.4 | documented | [geteuid32](./process/geteuid.md) | —grouped |
| SC-getgid | [getgid](https://man7.org/linux/man-pages/man2/getgid.2.html) | x64 104 · i386 47 · g64 176 · arm 47 | 1.0 | documented | [getgid](./process/getgid.md) | —grouped |
| SC-getgid32 | [getgid32](https://man7.org/linux/man-pages/man2/getgid32.2.html) | x64 — · i386 200 · g64 — · arm 200 | 2.4 | documented | [getgid32](./process/getgid.md) | —grouped |
| SC-getgroups | [getgroups](https://man7.org/linux/man-pages/man2/getgroups.2.html) | x64 115 · i386 80 · g64 158 · arm 80 | 1.0 | documented | [getgroups](./process/getgroups.md) | —grouped |
| SC-getgroups32 | [getgroups32](https://man7.org/linux/man-pages/man2/getgroups32.2.html) | x64 — · i386 205 · g64 — · arm 205 | 2.4 | documented | [getgroups32](./process/getgroups.md) | —grouped |
| SC-getpgid | [getpgid](https://man7.org/linux/man-pages/man2/getpgid.2.html) | x64 121 · i386 132 · g64 155 · arm 132 | 1.0 | documented | [getpgid](./process/setpgid.md) | —grouped |
| SC-getpgrp | [getpgrp](https://man7.org/linux/man-pages/man2/getpgrp.2.html) | x64 111 · i386 65 · g64 — · arm 65 | 1.0 | documented | [getpgrp](./process/setpgid.md) | —grouped |
| SC-getpid | [getpid](https://man7.org/linux/man-pages/man2/getpid.2.html) | x64 39 · i386 20 · g64 172 · arm 20 | 1.0 | researched | [getpid](./process/getpid.md) | —covered |
| SC-getppid | [getppid](https://man7.org/linux/man-pages/man2/getppid.2.html) | x64 110 · i386 64 · g64 173 · arm 64 | 1.0 | researched | [getppid](./process/getpid.md) | —covered |
| SC-getresgid | [getresgid](https://man7.org/linux/man-pages/man2/getresgid.2.html) | x64 120 · i386 171 · g64 150 · arm 171 | 2.2 | documented | [getresgid](./process/getresuid.md) | —grouped |
| SC-getresgid32 | [getresgid32](https://man7.org/linux/man-pages/man2/getresgid32.2.html) | x64 — · i386 211 · g64 — · arm 211 | 2.4 | documented | [getresgid32](./process/getresgid.md) | —grouped |
| SC-getresuid | [getresuid](https://man7.org/linux/man-pages/man2/getresuid.2.html) | x64 118 · i386 165 · g64 148 · arm 165 | 2.2 | documented | [getresuid](./process/getresuid.md) | —grouped |
| SC-getresuid32 | [getresuid32](https://man7.org/linux/man-pages/man2/getresuid32.2.html) | x64 — · i386 209 · g64 — · arm 209 | 2.4 | documented | [getresuid32](./process/getresuid.md) | —grouped |
| SC-getrlimit | [getrlimit](https://man7.org/linux/man-pages/man2/getrlimit.2.html) | x64 97 · i386 76 · g64 — · arm — | 1.0 | not-started | [getrlimit](./process/getrlimit.md) | — |
| SC-getrusage | [getrusage](https://man7.org/linux/man-pages/man2/getrusage.2.html) | x64 98 · i386 77 · g64 165 · arm 77 | 1.0 | not-started | [getrusage](./process/getrusage.md) | — |
| SC-getsid | [getsid](https://man7.org/linux/man-pages/man2/getsid.2.html) | x64 124 · i386 147 · g64 156 · arm 147 | 2.0 | documented | [getsid](./process/getsid.md) | —grouped |
| SC-gettid | [gettid](https://man7.org/linux/man-pages/man2/gettid.2.html) | x64 186 · i386 224 · g64 178 · arm 224 | 2.4.11 | researched | [gettid](./process/gettid.md) | —covered |
| SC-getuid | [getuid](https://man7.org/linux/man-pages/man2/getuid.2.html) | x64 102 · i386 24 · g64 174 · arm 24 | 1.0 | documented | [getuid](./process/getuid.md) | —grouped |
| SC-getuid32 | [getuid32](https://man7.org/linux/man-pages/man2/getuid32.2.html) | x64 — · i386 199 · g64 — · arm 199 | 2.4 | documented | [getuid32](./process/getuid.md) | —grouped |
| SC-lchown32 | [lchown32](https://man7.org/linux/man-pages/man2/lchown32.2.html) | x64 — · i386 198 · g64 — · arm 198 | 2.4 | not-started | [lchown32](./process/lchown.md) | — |
| SC-personality | [personality](https://man7.org/linux/man-pages/man2/personality.2.html) | x64 135 · i386 136 · g64 92 · arm 136 | 1.2 | not-started | [personality](./process/personality.md) | — |
| SC-pidfd_getfd | [pidfd_getfd](https://man7.org/linux/man-pages/man2/pidfd_getfd.2.html) | x64 438 · i386 438 · g64 438 · arm 438 | 5.6 | documented | [pidfd_getfd](./process/pidfd_getfd.md) | —grouped |
| SC-pidfd_open | [pidfd_open](https://man7.org/linux/man-pages/man2/pidfd_open.2.html) | x64 434 · i386 434 · g64 434 · arm 434 | 5.3 | documented | [pidfd_open](./process/pidfd_open.md) | —full |
| SC-pidfd_send_signal | [pidfd_send_signal](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html) | x64 424 · i386 424 · g64 424 · arm 424 | 5.1 | documented | [pidfd_send_signal](./process/pidfd_send_signal.md) | —grouped |
| SC-prctl | [prctl](https://man7.org/linux/man-pages/man2/prctl.2.html) | x64 157 · i386 172 · g64 167 · arm 172 | 2.2 | documented | [prctl](./process/prctl.md) | —full |
| SC-prlimit64 | [prlimit64](https://man7.org/linux/man-pages/man2/prlimit64.2.html) | x64 302 · i386 340 · g64 261 · arm 369 | 2.6.36 | not-started | [prlimit64](./process/getrlimit.md) | — |
| SC-process_madvise | [process_madvise](https://man7.org/linux/man-pages/man2/process_madvise.2.html) | x64 440 · i386 440 · g64 440 · arm 440 | 5.10 | documented | [process_madvise](./process/process_madvise.md) | —grouped |
| SC-process_mrelease | process_mrelease | x64 448 · i386 448 · g64 448 · arm 448 | — | source-limited | [process_mrelease](./process/process_mrelease.md) | —grouped |
| SC-ptrace | [ptrace](https://man7.org/linux/man-pages/man2/ptrace.2.html) | x64 101 · i386 26 · g64 117 · arm 26 | 1.0 | researched | [ptrace](./process/ptrace.md) | —brief |
| SC-rseq | rseq | x64 334 · i386 386 · g64 293 · arm 398 | 4.18 | source-limited | [rseq](./process/rseq.md) | —no |
| SC-rseq_slice_yield | rseq_slice_yield | x64 471 · i386 471 · g64 471 · arm 471 | — | source-limited | [rseq_slice_yield](./process/rseq_slice_yield.md) | —grouped |
| SC-set_robust_list | [set_robust_list](https://man7.org/linux/man-pages/man2/set_robust_list.2.html) | x64 273 · i386 311 · g64 99 · arm 338 | 2.6.17 | researched | [set_robust_list](./process/get_robust_list.md) | —brief |
| SC-set_tid_address | [set_tid_address](https://man7.org/linux/man-pages/man2/set_tid_address.2.html) | x64 218 · i386 258 · g64 96 · arm 256 | 2.6 | documented | [set_tid_address](./process/set_tid_address.md) | —full |
| SC-setfsgid | [setfsgid](https://man7.org/linux/man-pages/man2/setfsgid.2.html) | x64 123 · i386 139 · g64 152 · arm 139 | 1.2 | documented | [setfsgid](./process/setfsgid.md) | —grouped |
| SC-setfsgid32 | [setfsgid32](https://man7.org/linux/man-pages/man2/setfsgid32.2.html) | x64 — · i386 216 · g64 — · arm 216 | 2.4 | documented | [setfsgid32](./process/setfsgid.md) | —grouped |
| SC-setfsuid | [setfsuid](https://man7.org/linux/man-pages/man2/setfsuid.2.html) | x64 122 · i386 138 · g64 151 · arm 138 | 1.2 | documented | [setfsuid](./process/setfsuid.md) | —grouped |
| SC-setfsuid32 | [setfsuid32](https://man7.org/linux/man-pages/man2/setfsuid32.2.html) | x64 — · i386 215 · g64 — · arm 215 | 2.4 | documented | [setfsuid32](./process/setfsuid.md) | —grouped |
| SC-setgid | [setgid](https://man7.org/linux/man-pages/man2/setgid.2.html) | x64 106 · i386 46 · g64 144 · arm 46 | 1.0 | documented | [setgid](./process/setgid.md) | —grouped |
| SC-setgid32 | [setgid32](https://man7.org/linux/man-pages/man2/setgid32.2.html) | x64 — · i386 214 · g64 — · arm 214 | 2.4 | documented | [setgid32](./process/setgid.md) | —grouped |
| SC-setgroups | [setgroups](https://man7.org/linux/man-pages/man2/setgroups.2.html) | x64 116 · i386 81 · g64 159 · arm 81 | 1.0 | documented | [setgroups](./process/getgroups.md) | —grouped |
| SC-setgroups32 | [setgroups32](https://man7.org/linux/man-pages/man2/setgroups32.2.html) | x64 — · i386 206 · g64 — · arm 206 | 2.4 | documented | [setgroups32](./process/setgroups.md) | —grouped |
| SC-setpgid | [setpgid](https://man7.org/linux/man-pages/man2/setpgid.2.html) | x64 109 · i386 57 · g64 154 · arm 57 | 1.0 | documented | [setpgid](./process/setpgid.md) | —grouped |
| SC-setpgrp | [setpgrp](https://man7.org/linux/man-pages/man2/setpgrp.2.html) | x64 — · i386 — · g64 — · arm — | 2.0 | documented | [setpgrp](./process/setpgid.md) | —grouped |
| SC-setregid | [setregid](https://man7.org/linux/man-pages/man2/setregid.2.html) | x64 114 · i386 71 · g64 143 · arm 71 | 1.0 | documented | [setregid](./process/setreuid.md) | —grouped |
| SC-setregid32 | [setregid32](https://man7.org/linux/man-pages/man2/setregid32.2.html) | x64 — · i386 204 · g64 — · arm 204 | 2.4 | documented | [setregid32](./process/setregid.md) | —grouped |
| SC-setresgid | [setresgid](https://man7.org/linux/man-pages/man2/setresgid.2.html) | x64 119 · i386 170 · g64 149 · arm 170 | 2.2 | documented | [setresgid](./process/setresuid.md) | —grouped |
| SC-setresgid32 | [setresgid32](https://man7.org/linux/man-pages/man2/setresgid32.2.html) | x64 — · i386 210 · g64 — · arm 210 | 2.4 | documented | [setresgid32](./process/setresgid.md) | —grouped |
| SC-setresuid | [setresuid](https://man7.org/linux/man-pages/man2/setresuid.2.html) | x64 117 · i386 164 · g64 147 · arm 164 | 2.2 | documented | [setresuid](./process/setresuid.md) | —grouped |
| SC-setresuid32 | [setresuid32](https://man7.org/linux/man-pages/man2/setresuid32.2.html) | x64 — · i386 208 · g64 — · arm 208 | 2.4 | documented | [setresuid32](./process/setresuid.md) | —grouped |
| SC-setreuid | [setreuid](https://man7.org/linux/man-pages/man2/setreuid.2.html) | x64 113 · i386 70 · g64 145 · arm 70 | 1.0 | documented | [setreuid](./process/setreuid.md) | —grouped |
| SC-setreuid32 | [setreuid32](https://man7.org/linux/man-pages/man2/setreuid32.2.html) | x64 — · i386 203 · g64 — · arm 203 | 2.4 | documented | [setreuid32](./process/setreuid.md) | —grouped |
| SC-setrlimit | [setrlimit](https://man7.org/linux/man-pages/man2/setrlimit.2.html) | x64 160 · i386 75 · g64 — · arm 75 | 1.0 | not-started | [setrlimit](./process/getrlimit.md) | — |
| SC-setsid | [setsid](https://man7.org/linux/man-pages/man2/setsid.2.html) | x64 112 · i386 66 · g64 157 · arm 66 | 1.0 | documented | [setsid](./process/setsid.md) | —grouped |
| SC-setuid | [setuid](https://man7.org/linux/man-pages/man2/setuid.2.html) | x64 105 · i386 23 · g64 146 · arm 23 | 1.0 | documented | [setuid](./process/setuid.md) | —grouped |
| SC-setuid32 | [setuid32](https://man7.org/linux/man-pages/man2/setuid32.2.html) | x64 — · i386 213 · g64 — · arm 213 | 2.4 | documented | [setuid32](./process/setuid.md) | —grouped |
| SC-ugetrlimit | [ugetrlimit](https://man7.org/linux/man-pages/man2/ugetrlimit.2.html) | x64 — · i386 191 · g64 — · arm 191 | 2.4 | not-started | [ugetrlimit](./process/getrlimit.md) | — |
| SC-uname | [uname](https://man7.org/linux/man-pages/man2/uname.2.html) | x64 63 · i386 122 · g64 160 · arm 122 | 1.0 | documented | [uname](./process/uname.md) | —full |
| SC-vfork | [vfork](https://man7.org/linux/man-pages/man2/vfork.2.html) | x64 58 · i386 190 · g64 — · arm 190 | 2.2 | documented | [vfork](./process/vfork.md) | —full |
| SC-wait4 | [wait4](https://man7.org/linux/man-pages/man2/wait4.2.html) | x64 61 · i386 114 · g64 260 · arm 114 | 1.0 | documented | [wait4](./process/wait4.md) | —full |
| SC-waitid | [waitid](https://man7.org/linux/man-pages/man2/waitid.2.html) | x64 247 · i386 284 · g64 95 · arm 280 | 2.6.10 | documented | [waitid](./process/wait.md) | —full |
| SC-waitpid | [waitpid](https://man7.org/linux/man-pages/man2/waitpid.2.html) | x64 — · i386 7 · g64 — · arm — | 1.0 | documented | [waitpid](./process/wait.md) | —grouped |

### memory

| ID | Name | Numbers | Since | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| SC-brk | [brk](https://man7.org/linux/man-pages/man2/brk.2.html) | x64 12 · i386 45 · g64 214 · arm 45 | 1.0 | documented | [brk](./memory/brk.md) | —full |
| SC-cachestat | cachestat | x64 451 · i386 451 · g64 451 · arm 451 | 6.5 | documented | [cachestat](./memory/cachestat.md) | —full |
| SC-get_mempolicy | [get_mempolicy](https://man7.org/linux/man-pages/man2/get_mempolicy.2.html) | x64 239 · i386 275 · g64 236 · arm 320 | 2.6.6 | documented | [get_mempolicy](./memory/get_mempolicy.md) | —grouped |
| SC-madvise | [madvise](https://man7.org/linux/man-pages/man2/madvise.2.html) | x64 28 · i386 219 · g64 233 · arm 220 | 2.4 | documented | [madvise](./memory/madvise.md) | —full |
| SC-map_shadow_stack | map_shadow_stack | x64 453 · i386 453 · g64 453 · arm 453 | 6.6 | documented | [map_shadow_stack](./memory/map_shadow_stack.md) | —full |
| SC-mbind | [mbind](https://man7.org/linux/man-pages/man2/mbind.2.html) | x64 237 · i386 274 · g64 235 · arm 319 | 2.6.6 | documented | [mbind](./memory/mbind.md) | —grouped |
| SC-membarrier | [membarrier](https://man7.org/linux/man-pages/man2/membarrier.2.html) | x64 324 · i386 375 · g64 283 · arm 389 | 3.17 | documented | [membarrier](./memory/membarrier.md) | —full |
| SC-memfd_create | [memfd_create](https://man7.org/linux/man-pages/man2/memfd_create.2.html) | x64 319 · i386 356 · g64 279 · arm 385 | 3.17 | documented | [memfd_create](./memory/memfd_create.md) | —full |
| SC-memfd_secret | [memfd_secret](https://man7.org/linux/man-pages/man2/memfd_secret.2.html) | x64 447 · i386 447 · g64 — · arm — | 5.14 | documented | [memfd_secret](./memory/memfd_secret.md) | —full |
| SC-migrate_pages | [migrate_pages](https://man7.org/linux/man-pages/man2/migrate_pages.2.html) | x64 256 · i386 294 · g64 238 · arm 400 | 2.6.16 | documented | [migrate_pages](./memory/migrate_pages.md) | —full |
| SC-mincore | [mincore](https://man7.org/linux/man-pages/man2/mincore.2.html) | x64 27 · i386 218 · g64 232 · arm 219 | 2.4 | documented | [mincore](./memory/mincore.md) | —full |
| SC-mlock | [mlock](https://man7.org/linux/man-pages/man2/mlock.2.html) | x64 149 · i386 150 · g64 228 · arm 150 | 2.0 | documented | [mlock](./memory/mlock.md) | —grouped |
| SC-mlock2 | [mlock2](https://man7.org/linux/man-pages/man2/mlock2.2.html) | x64 325 · i386 376 · g64 284 · arm 390 | 4.4 | documented | [mlock2](./memory/mlock.md) | —grouped; |
| SC-mlockall | [mlockall](https://man7.org/linux/man-pages/man2/mlockall.2.html) | x64 151 · i386 152 · g64 230 · arm 152 | 2.0 | documented | [mlockall](./memory/mlock.md) | —grouped; |
| SC-mmap | [mmap](https://man7.org/linux/man-pages/man2/mmap.2.html) | x64 9 · i386 90 · g64 222 · arm — | 1.0 | documented | [mmap](./memory/mmap.md) | —full |
| SC-move_pages | [move_pages](https://man7.org/linux/man-pages/man2/move_pages.2.html) | x64 279 · i386 317 · g64 239 · arm 344 | 2.6.18 | documented | [move_pages](./memory/move_pages.md) | —full |
| SC-mprotect | [mprotect](https://man7.org/linux/man-pages/man2/mprotect.2.html) | x64 10 · i386 125 · g64 226 · arm 125 | 1.0 | documented | [mprotect](./memory/mprotect.md) | —full |
| SC-mremap | [mremap](https://man7.org/linux/man-pages/man2/mremap.2.html) | x64 25 · i386 163 · g64 216 · arm 163 | 2.0 | documented | [mremap](./memory/mremap.md) | —full |
| SC-mseal | mseal | x64 462 · i386 462 · g64 462 · arm 462 | 6.10 | documented | [mseal](./memory/mseal.md) | —full |
| SC-msync | [msync](https://man7.org/linux/man-pages/man2/msync.2.html) | x64 26 · i386 144 · g64 227 · arm 144 | 2.0 | documented | [msync](./memory/msync.md) | —full |
| SC-munlock | [munlock](https://man7.org/linux/man-pages/man2/munlock.2.html) | x64 150 · i386 151 · g64 229 · arm 151 | 2.0 | documented | [munlock](./memory/mlock.md) | —grouped |
| SC-munlockall | [munlockall](https://man7.org/linux/man-pages/man2/munlockall.2.html) | x64 152 · i386 153 · g64 231 · arm 153 | 2.0 | documented | [munlockall](./memory/mlock.md) | —grouped |
| SC-munmap | [munmap](https://man7.org/linux/man-pages/man2/munmap.2.html) | x64 11 · i386 91 · g64 215 · arm 91 | 1.0 | documented | [munmap](./memory/mmap.md) | —full |
| SC-pkey_alloc | [pkey_alloc](https://man7.org/linux/man-pages/man2/pkey_alloc.2.html) | x64 330 · i386 381 · g64 289 · arm 395 | 4.8 | documented | [pkey_alloc](./memory/pkey_alloc.md) | —grouped |
| SC-pkey_free | [pkey_free](https://man7.org/linux/man-pages/man2/pkey_free.2.html) | x64 331 · i386 382 · g64 290 · arm 396 | 4.8 | documented | [pkey_free](./memory/pkey_alloc.md) | —grouped |
| SC-pkey_mprotect | [pkey_mprotect](https://man7.org/linux/man-pages/man2/pkey_mprotect.2.html) | x64 329 · i386 380 · g64 288 · arm 394 | 4.8 | documented | [pkey_mprotect](./memory/mprotect.md) | —full |
| SC-process_vm_readv | [process_vm_readv](https://man7.org/linux/man-pages/man2/process_vm_readv.2.html) | x64 310 · i386 347 · g64 270 · arm 376 | 3.2 | documented | [process_vm_readv](./memory/process_vm_readv.md) | —grouped |
| SC-process_vm_writev | [process_vm_writev](https://man7.org/linux/man-pages/man2/process_vm_writev.2.html) | x64 311 · i386 348 · g64 271 · arm 377 | 3.2 | documented | [process_vm_writev](./memory/process_vm_readv.md) | —grouped |
| SC-remap_file_pages | [remap_file_pages](https://man7.org/linux/man-pages/man2/remap_file_pages.2.html) | x64 216 · i386 257 · g64 234 · arm 253 | 2.6 | researched | [remap_file_pages](./memory/remap_file_pages.md) | —brief |
| SC-set_mempolicy | [set_mempolicy](https://man7.org/linux/man-pages/man2/set_mempolicy.2.html) | x64 238 · i386 276 · g64 237 · arm 321 | 2.6.6 | documented | [set_mempolicy](./memory/set_mempolicy.md) | —grouped |
| SC-set_mempolicy_home_node | set_mempolicy_home_node | x64 450 · i386 450 · g64 450 · arm 450 | 5.17 | documented | [set_mempolicy_home_node](./memory/set_mempolicy_home_node.md) | —grouped; |
| SC-swapoff | [swapoff](https://man7.org/linux/man-pages/man2/swapoff.2.html) | x64 168 · i386 115 · g64 225 · arm 115 | 1.0 | researched | [swapoff](./memory/swapon.md) | —brief |
| SC-swapon | [swapon](https://man7.org/linux/man-pages/man2/swapon.2.html) | x64 167 · i386 87 · g64 224 · arm 87 | 1.0 | researched | [swapon](./memory/swapon.md) | —brief |
| SC-userfaultfd | [userfaultfd](https://man7.org/linux/man-pages/man2/userfaultfd.2.html) | x64 323 · i386 374 · g64 282 · arm 388 | 4.3 | documented | [userfaultfd](./memory/userfaultfd.md) | —full |

### desc-io

| ID | Name | Numbers | Since | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| SC-_llseek | [_llseek](https://man7.org/linux/man-pages/man2/_llseek.2.html) | x64 — · i386 140 · g64 — · arm 140 | 1.2 | documented | [_llseek](./descriptors-io/llseek.md) | —grouped |
| SC-access | [access](https://man7.org/linux/man-pages/man2/access.2.html) | x64 21 · i386 33 · g64 — · arm 33 | 1.0 | documented | [access](./descriptors-io/access.md) | —access/faccessat/faccessat2 |
| SC-arm_fadvise64_64 | [arm_fadvise64_64](https://man7.org/linux/man-pages/man2/arm_fadvise64_64.2.html) | x64 — · i386 — · g64 — · arm 270 | — | documented | [arm_fadvise64_64](./descriptors-io/posix_fadvise.md) | —grouped |
| SC-arm_sync_file_range | [arm_sync_file_range](https://man7.org/linux/man-pages/man2/arm_sync_file_range.2.html) | x64 — · i386 — · g64 — · arm 341 | — | documented | [arm_sync_file_range](./descriptors-io/sync_file_range.md) | —grouped |
| SC-close | [close](https://man7.org/linux/man-pages/man2/close.2.html) | x64 3 · i386 6 · g64 57 · arm 6 | 1.0 | documented | [close](./descriptors-io/close.md) | —close |
| SC-close_range | [close_range](https://man7.org/linux/man-pages/man2/close_range.2.html) | x64 436 · i386 436 · g64 436 · arm 436 | 5.9 | documented | [close_range](./descriptors-io/close_range.md) | —close_range |
| SC-copy_file_range | [copy_file_range](https://man7.org/linux/man-pages/man2/copy_file_range.2.html) | x64 326 · i386 377 · g64 285 · arm 391 | 4.5 | documented | [copy_file_range](./descriptors-io/copy_file_range.md) | —4.5; |
| SC-creat | [creat](https://man7.org/linux/man-pages/man2/creat.2.html) | x64 85 · i386 8 · g64 — · arm 8 | 1.0 | documented | [creat](./descriptors-io/open.md) | —creat |
| SC-dup | [dup](https://man7.org/linux/man-pages/man2/dup.2.html) | x64 32 · i386 41 · g64 23 · arm 41 | 1.0 | documented | [dup](./descriptors-io/dup.md) | —dup/dup2/dup3 |
| SC-dup2 | [dup2](https://man7.org/linux/man-pages/man2/dup2.2.html) | x64 33 · i386 63 · g64 — · arm 63 | 1.0 | documented | [dup2](./descriptors-io/dup.md) | —dup/dup2/dup3 |
| SC-dup3 | [dup3](https://man7.org/linux/man-pages/man2/dup3.2.html) | x64 292 · i386 330 · g64 24 · arm 358 | 2.6.27 | documented | [dup3](./descriptors-io/dup.md) | —dup/dup2/dup3 |
| SC-faccessat | [faccessat](https://man7.org/linux/man-pages/man2/faccessat.2.html) | x64 269 · i386 307 · g64 48 · arm 334 | 2.6.16 | documented | [faccessat](./descriptors-io/access.md) | —access |
| SC-faccessat2 | [faccessat2](https://man7.org/linux/man-pages/man2/faccessat2.2.html) | x64 439 · i386 439 · g64 439 · arm 439 | 5.8 | documented | [faccessat2](./descriptors-io/access.md) | —5.8 |
| SC-fadvise64 | [fadvise64](https://man7.org/linux/man-pages/man2/fadvise64.2.html) | x64 221 · i386 250 · g64 223 · arm — | 2.6 | documented | [fadvise64](./descriptors-io/posix_fadvise.md) | —fadvise64 |
| SC-fadvise64_64 | [fadvise64_64](https://man7.org/linux/man-pages/man2/fadvise64_64.2.html) | x64 — · i386 272 · g64 — · arm — | 2.6 | documented | [fadvise64_64](./descriptors-io/posix_fadvise.md) | —grouped |
| SC-fallocate | [fallocate](https://man7.org/linux/man-pages/man2/fallocate.2.html) | x64 285 · i386 324 · g64 47 · arm 352 | 2.6.23 | documented | [fallocate](./descriptors-io/fallocate.md) | —fallocate |
| SC-fcntl | [fcntl](https://man7.org/linux/man-pages/man2/fcntl.2.html) | x64 72 · i386 55 · g64 25 · arm 55 | 1.0 | documented | [fcntl](./descriptors-io/fcntl.md) | —fcntl |
| SC-fcntl64 | [fcntl64](https://man7.org/linux/man-pages/man2/fcntl64.2.html) | x64 — · i386 221 · g64 — · arm 221 | 2.4 | documented | [fcntl64](./descriptors-io/fcntl.md) | —grouped |
| SC-fdatasync | [fdatasync](https://man7.org/linux/man-pages/man2/fdatasync.2.html) | x64 75 · i386 148 · g64 83 · arm 148 | 2.0 | documented | [fdatasync](./descriptors-io/fsync.md) | —sync |
| SC-flock | [flock](https://man7.org/linux/man-pages/man2/flock.2.html) | x64 73 · i386 143 · g64 32 · arm 143 | 2.0 | documented | [flock](./descriptors-io/flock.md) | —flock |
| SC-fstat | [fstat](https://man7.org/linux/man-pages/man2/fstat.2.html) | x64 5 · i386 108 · g64 80 · arm 108 | 1.0 | documented | [fstat](./descriptors-io/stat.md) | —stat |
| SC-fstat64 | [fstat64](https://man7.org/linux/man-pages/man2/fstat64.2.html) | x64 — · i386 197 · g64 — · arm 197 | 2.4 | documented | [fstat64](./descriptors-io/fstat.md) | —grouped |
| SC-fstatat64 | [fstatat64](https://man7.org/linux/man-pages/man2/fstatat64.2.html) | x64 — · i386 300 · g64 — · arm 327 | 2.6.16 | documented | [fstatat64](./descriptors-io/fstatat.md) | —grouped |
| SC-fstatfs | [fstatfs](https://man7.org/linux/man-pages/man2/fstatfs.2.html) | x64 138 · i386 100 · g64 44 · arm 100 | 1.0 | documented | [fstatfs](./descriptors-io/statfs.md) | —statfs/fstatfs |
| SC-fstatfs64 | [fstatfs64](https://man7.org/linux/man-pages/man2/fstatfs64.2.html) | x64 — · i386 269 · g64 — · arm 267 | 2.6 | documented | [fstatfs64](./descriptors-io/fstatfs.md) | —grouped |
| SC-fsync | [fsync](https://man7.org/linux/man-pages/man2/fsync.2.html) | x64 74 · i386 118 · g64 82 · arm 118 | 1.0 | documented | [fsync](./descriptors-io/fsync.md) | —sync |
| SC-ftruncate | [ftruncate](https://man7.org/linux/man-pages/man2/ftruncate.2.html) | x64 77 · i386 93 · g64 46 · arm 93 | 1.0 | documented | [ftruncate](./descriptors-io/truncate.md) | —truncate |
| SC-ftruncate64 | [ftruncate64](https://man7.org/linux/man-pages/man2/ftruncate64.2.html) | x64 — · i386 194 · g64 — · arm 194 | 2.4 | documented | [ftruncate64](./descriptors-io/ftruncate.md) | —grouped |
| SC-getdents | [getdents](https://man7.org/linux/man-pages/man2/getdents.2.html) | x64 78 · i386 141 · g64 — · arm 141 | 2.0 | documented | [getdents](./descriptors-io/getdents.md) | —getdents/getdents64 |
| SC-getdents64 | [getdents64](https://man7.org/linux/man-pages/man2/getdents64.2.html) | x64 217 · i386 220 · g64 61 · arm 217 | 2.4 | documented | [getdents64](./descriptors-io/getdents.md) | —getdents64 |
| SC-ioctl | [ioctl](https://man7.org/linux/man-pages/man2/ioctl.2.html) | x64 16 · i386 54 · g64 29 · arm 54 | 1.0 | documented | [ioctl](./descriptors-io/ioctl.md) | —ioctl |
| SC-lseek | [lseek](https://man7.org/linux/man-pages/man2/lseek.2.html) | x64 8 · i386 19 · g64 62 · arm 19 | 1.0 | documented | [lseek](./descriptors-io/lseek.md) | —lseek |
| SC-lstat | [lstat](https://man7.org/linux/man-pages/man2/lstat.2.html) | x64 6 · i386 107 · g64 — · arm 107 | 1.0 | documented | [lstat](./descriptors-io/stat.md) | —stat |
| SC-lstat64 | [lstat64](https://man7.org/linux/man-pages/man2/lstat64.2.html) | x64 — · i386 196 · g64 — · arm 196 | 2.4 | documented | [lstat64](./descriptors-io/lstat.md) | —grouped |
| SC-mmap2 | [mmap2](https://man7.org/linux/man-pages/man2/mmap2.2.html) | x64 — · i386 192 · g64 — · arm 192 | 2.4 | researched | [mmap2](./descriptors-io/mmap2.md) | —BRIEF |
| SC-newfstatat | [newfstatat](https://man7.org/linux/man-pages/man2/newfstatat.2.html) | x64 262 · i386 — · g64 79 · arm — | 2.6.16 | documented | [newfstatat](./descriptors-io/fstatat.md) | —stat |
| SC-open | [open](https://man7.org/linux/man-pages/man2/open.2.html) | x64 2 · i386 5 · g64 — · arm 5 | 1.0 | documented | [open](./descriptors-io/open.md) | —open |
| SC-openat | [openat](https://man7.org/linux/man-pages/man2/openat.2.html) | x64 257 · i386 295 · g64 56 · arm 322 | 2.6.16 | documented | [openat](./descriptors-io/open.md) | —openat |
| SC-openat2 | [openat2](https://man7.org/linux/man-pages/man2/openat2.2.html) | x64 437 · i386 437 · g64 437 · arm 437 | 5.6 | documented | [openat2](./descriptors-io/openat2.md) | —openat2 |
| SC-pread64 | [pread64](https://man7.org/linux/man-pages/man2/pread64.2.html) | x64 17 · i386 180 · g64 67 · arm 180 | — | documented | [pread64](./descriptors-io/pread.md) | —pread64/pwrite64 |
| SC-preadv | [preadv](https://man7.org/linux/man-pages/man2/preadv.2.html) | x64 295 · i386 333 · g64 69 · arm 361 | 2.6.30 | documented | [preadv](./descriptors-io/readv.md) | —documented |
| SC-preadv2 | [preadv2](https://man7.org/linux/man-pages/man2/preadv2.2.html) | x64 327 · i386 378 · g64 286 · arm 392 | 4.6 | documented | [preadv2](./descriptors-io/readv.md) | —preadv2/pwritev2 |
| SC-pwrite64 | [pwrite64](https://man7.org/linux/man-pages/man2/pwrite64.2.html) | x64 18 · i386 181 · g64 68 · arm 181 | — | documented | [pwrite64](./descriptors-io/pwrite.md) | —pread64/pwrite64 |
| SC-pwritev | [pwritev](https://man7.org/linux/man-pages/man2/pwritev.2.html) | x64 296 · i386 334 · g64 70 · arm 362 | 2.6.30 | documented | [pwritev](./descriptors-io/readv.md) | —documented |
| SC-pwritev2 | [pwritev2](https://man7.org/linux/man-pages/man2/pwritev2.2.html) | x64 328 · i386 379 · g64 287 · arm 393 | 4.6 | documented | [pwritev2](./descriptors-io/readv.md) | —preadv2/pwritev2 |
| SC-read | [read](https://man7.org/linux/man-pages/man2/read.2.html) | x64 0 · i386 3 · g64 63 · arm 3 | 1.0 | documented | [read](./descriptors-io/read.md) | —read |
| SC-readahead | [readahead](https://man7.org/linux/man-pages/man2/readahead.2.html) | x64 187 · i386 225 · g64 213 · arm 225 | 2.4.13 | researched | [readahead](./descriptors-io/readahead.md) | —BRIEF |
| SC-readdir | [readdir](https://man7.org/linux/man-pages/man2/readdir.2.html) | x64 — · i386 89 · g64 — · arm — | 1.0 | researched | [readdir](./descriptors-io/readdir.md) | —BRIEF |
| SC-readlink | [readlink](https://man7.org/linux/man-pages/man2/readlink.2.html) | x64 89 · i386 85 · g64 — · arm 85 | 1.0 | documented | [readlink](./descriptors-io/readlink.md) | —readlink/readlinkat |
| SC-readlinkat | [readlinkat](https://man7.org/linux/man-pages/man2/readlinkat.2.html) | x64 267 · i386 305 · g64 78 · arm 332 | 2.6.16 | documented | [readlinkat](./descriptors-io/readlink.md) | —readlink/readlinkat |
| SC-readv | [readv](https://man7.org/linux/man-pages/man2/readv.2.html) | x64 19 · i386 145 · g64 65 · arm 145 | 2.0 | documented | [readv](./descriptors-io/readv.md) | —readv/writev |
| SC-sendfile | [sendfile](https://man7.org/linux/man-pages/man2/sendfile.2.html) | x64 40 · i386 187 · g64 71 · arm 187 | 2.2 | documented | [sendfile](./descriptors-io/sendfile.md) | —sendfile |
| SC-sendfile64 | [sendfile64](https://man7.org/linux/man-pages/man2/sendfile64.2.html) | x64 — · i386 239 · g64 — · arm 239 | 2.6 | documented | [sendfile64](./descriptors-io/sendfile.md) | —grouped |
| SC-splice | [splice](https://man7.org/linux/man-pages/man2/splice.2.html) | x64 275 · i386 313 · g64 76 · arm 340 | 2.6.17 | documented | [splice](./descriptors-io/splice.md) | —splice/vmsplice/tee |
| SC-stat | [stat](https://man7.org/linux/man-pages/man2/stat.2.html) | x64 4 · i386 106 · g64 — · arm 106 | 1.0 | documented | [stat](./descriptors-io/stat.md) | —stat |
| SC-stat64 | [stat64](https://man7.org/linux/man-pages/man2/stat64.2.html) | x64 — · i386 195 · g64 — · arm 195 | 2.4 | documented | [stat64](./descriptors-io/stat.md) | —grouped |
| SC-statfs | [statfs](https://man7.org/linux/man-pages/man2/statfs.2.html) | x64 137 · i386 99 · g64 43 · arm 99 | 1.0 | documented | [statfs](./descriptors-io/statfs.md) | —statfs/fstatfs |
| SC-statfs64 | [statfs64](https://man7.org/linux/man-pages/man2/statfs64.2.html) | x64 — · i386 268 · g64 — · arm 266 | 2.6 | documented | [statfs64](./descriptors-io/statfs.md) | —grouped |
| SC-statx | [statx](https://man7.org/linux/man-pages/man2/statx.2.html) | x64 332 · i386 383 · g64 291 · arm 397 | 4.11 | documented | [statx](./descriptors-io/statx.md) | —statx |
| SC-sync | [sync](https://man7.org/linux/man-pages/man2/sync.2.html) | x64 162 · i386 36 · g64 81 · arm 36 | 1.0 | documented | [sync](./descriptors-io/sync.md) | —sync |
| SC-sync_file_range | [sync_file_range](https://man7.org/linux/man-pages/man2/sync_file_range.2.html) | x64 277 · i386 314 · g64 84 · arm — | 2.6.17 | documented | [sync_file_range](./descriptors-io/sync_file_range.md) | —sync |
| SC-sync_file_range2 | [sync_file_range2](https://man7.org/linux/man-pages/man2/sync_file_range2.2.html) | x64 — · i386 — · g64 — · arm — | 2.6.22 | documented | [sync_file_range2](./descriptors-io/sync_file_range.md) | —grouped |
| SC-syncfs | [syncfs](https://man7.org/linux/man-pages/man2/syncfs.2.html) | x64 306 · i386 344 · g64 267 · arm 373 | 2.6.39 | documented | [syncfs](./descriptors-io/sync.md) | —sync |
| SC-tee | [tee](https://man7.org/linux/man-pages/man2/tee.2.html) | x64 276 · i386 315 · g64 77 · arm 342 | 2.6.17 | documented | [tee](./descriptors-io/tee.md) | —splice/vmsplice/tee |
| SC-truncate | [truncate](https://man7.org/linux/man-pages/man2/truncate.2.html) | x64 76 · i386 92 · g64 45 · arm 92 | 1.0 | documented | [truncate](./descriptors-io/truncate.md) | —truncate |
| SC-truncate64 | [truncate64](https://man7.org/linux/man-pages/man2/truncate64.2.html) | x64 — · i386 193 · g64 — · arm 193 | 2.4 | documented | [truncate64](./descriptors-io/truncate.md) | —grouped |
| SC-umask | [umask](https://man7.org/linux/man-pages/man2/umask.2.html) | x64 95 · i386 60 · g64 166 · arm 60 | 1.0 | documented | [umask](./descriptors-io/umask.md) | —umask |
| SC-vmsplice | [vmsplice](https://man7.org/linux/man-pages/man2/vmsplice.2.html) | x64 278 · i386 316 · g64 75 · arm 343 | 2.6.17 | documented | [vmsplice](./descriptors-io/vmsplice.md) | —splice/vmsplice/tee |
| SC-write | [write](https://man7.org/linux/man-pages/man2/write.2.html) | x64 1 · i386 4 · g64 64 · arm 4 | 1.0 | documented | [write](./descriptors-io/write.md) | —write |
| SC-writev | [writev](https://man7.org/linux/man-pages/man2/writev.2.html) | x64 20 · i386 146 · g64 66 · arm 146 | 2.0 | documented | [writev](./descriptors-io/readv.md) | —readv/writev |

### fs-mount

| ID | Name | Numbers | Since | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| SC-add_key | [add_key](https://man7.org/linux/man-pages/man2/add_key.2.html) | x64 248 · i386 286 · g64 217 · arm 309 | 2.6.10 | documented | [add_key](./fs-mounts-namespace/add_key.md) | —keyring |
| SC-chdir | [chdir](https://man7.org/linux/man-pages/man2/chdir.2.html) | x64 80 · i386 12 · g64 49 · arm 12 | 1.0 | documented | [chdir](./fs-mounts-namespace/chdir.md) | —grouped |
| SC-chmod | [chmod](https://man7.org/linux/man-pages/man2/chmod.2.html) | x64 90 · i386 15 · g64 — · arm 15 | 1.0 | documented | [chmod](./fs-mounts-namespace/chmod.md) | —grouped |
| SC-chown | [chown](https://man7.org/linux/man-pages/man2/chown.2.html) | x64 92 · i386 182 · g64 — · arm 182 | 2.2 | documented | [chown](./fs-mounts-namespace/chown.md) | —grouped |
| SC-chroot | [chroot](https://man7.org/linux/man-pages/man2/chroot.2.html) | x64 161 · i386 61 · g64 51 · arm 61 | 1.0 | documented | [chroot](./fs-mounts-namespace/chroot.md) | —FULL |
| SC-fanotify_init | [fanotify_init](https://man7.org/linux/man-pages/man2/fanotify_init.2.html) | x64 300 · i386 338 · g64 262 · arm 367 | 2.6.37 | documented | [fanotify_init](./fs-mounts-namespace/fanotify_init.md) | —BRIEF |
| SC-fanotify_mark | [fanotify_mark](https://man7.org/linux/man-pages/man2/fanotify_mark.2.html) | x64 301 · i386 339 · g64 263 · arm 368 | 2.6.37 | documented | [fanotify_mark](./fs-mounts-namespace/fanotify_mark.md) | —BRIEF |
| SC-fchdir | [fchdir](https://man7.org/linux/man-pages/man2/fchdir.2.html) | x64 81 · i386 133 · g64 50 · arm 133 | 1.0 | documented | [fchdir](./fs-mounts-namespace/chdir.md) | —grouped |
| SC-fchmod | [fchmod](https://man7.org/linux/man-pages/man2/fchmod.2.html) | x64 91 · i386 94 · g64 52 · arm 94 | 1.0 | documented | [fchmod](./fs-mounts-namespace/chmod.md) | —grouped |
| SC-fchmodat | [fchmodat](https://man7.org/linux/man-pages/man2/fchmodat.2.html) | x64 268 · i386 306 · g64 53 · arm 333 | 2.6.16 | documented | [fchmodat](./fs-mounts-namespace/chmod.md) | —grouped |
| SC-fchmodat2 | fchmodat2 | x64 452 · i386 452 · g64 452 · arm 452 | — | source-limited | [fchmodat2](./fs-mounts-namespace/fchmodat2.md) | —note |
| SC-fchown | [fchown](https://man7.org/linux/man-pages/man2/fchown.2.html) | x64 93 · i386 95 · g64 55 · arm 95 | 1.0 | documented | [fchown](./fs-mounts-namespace/chown.md) | —grouped |
| SC-fchownat | [fchownat](https://man7.org/linux/man-pages/man2/fchownat.2.html) | x64 260 · i386 298 · g64 54 · arm 325 | 2.6.16 | documented | [fchownat](./fs-mounts-namespace/chown.md) | —grouped |
| SC-fchroot | fchroot | x64 472 · i386 472 · g64 472 · arm 472 | — | source-limited | [fchroot](./fs-mounts-namespace/fchroot.md) | —BRIEF |
| SC-fgetxattr | [fgetxattr](https://man7.org/linux/man-pages/man2/fgetxattr.2.html) | x64 193 · i386 231 · g64 10 · arm 231 | 2.6 | documented | [fgetxattr](./fs-mounts-namespace/getxattr.md) | —xattr |
| SC-file_getattr | file_getattr | x64 468 · i386 468 · g64 468 · arm 468 | — | source-limited | [file_getattr](./fs-mounts-namespace/file_getattr.md) | —BRIEF |
| SC-file_setattr | file_setattr | x64 469 · i386 469 · g64 469 · arm 469 | — | source-limited | [file_setattr](./fs-mounts-namespace/file_setattr.md) | —BRIEF |
| SC-flistxattr | [flistxattr](https://man7.org/linux/man-pages/man2/flistxattr.2.html) | x64 196 · i386 234 · g64 13 · arm 234 | 2.6 | documented | [flistxattr](./fs-mounts-namespace/listxattr.md) | —xattr |
| SC-fremovexattr | [fremovexattr](https://man7.org/linux/man-pages/man2/fremovexattr.2.html) | x64 199 · i386 237 · g64 16 · arm 237 | 2.6 | documented | [fremovexattr](./fs-mounts-namespace/removexattr.md) | —xattr |
| SC-fsconfig | fsconfig | x64 431 · i386 431 · g64 431 · arm 431 | 5.2 | documented | [fsconfig](./fs-mounts-namespace/fsconfig.md) | —new |
| SC-fsetxattr | [fsetxattr](https://man7.org/linux/man-pages/man2/fsetxattr.2.html) | x64 190 · i386 228 · g64 7 · arm 228 | 2.6 | documented | [fsetxattr](./fs-mounts-namespace/setxattr.md) | —xattr |
| SC-fsmount | fsmount | x64 432 · i386 432 · g64 432 · arm 432 | 5.2 | documented | [fsmount](./fs-mounts-namespace/fsmount.md) | —new |
| SC-fsopen | fsopen | x64 430 · i386 430 · g64 430 · arm 430 | 5.2 | documented | [fsopen](./fs-mounts-namespace/fsopen.md) | —new |
| SC-fspick | fspick | x64 433 · i386 433 · g64 433 · arm 433 | 5.2 | documented | [fspick](./fs-mounts-namespace/fspick.md) | —new |
| SC-futimesat | [futimesat](https://man7.org/linux/man-pages/man2/futimesat.2.html) | x64 261 · i386 299 · g64 — · arm 326 | 2.6.16 | documented | [futimesat](./fs-mounts-namespace/futimesat.md) | —timestamp |
| SC-getcwd | [getcwd](https://man7.org/linux/man-pages/man2/getcwd.2.html) | x64 79 · i386 183 · g64 17 · arm 183 | 2.2 | documented | [getcwd](./fs-mounts-namespace/getcwd.md) | —FULL |
| SC-getxattr | [getxattr](https://man7.org/linux/man-pages/man2/getxattr.2.html) | x64 191 · i386 229 · g64 8 · arm 229 | 2.6 | documented | [getxattr](./fs-mounts-namespace/getxattr.md) | —xattr |
| SC-getxattrat | getxattrat | x64 464 · i386 464 · g64 464 · arm 464 | — | source-limited | [getxattrat](./fs-mounts-namespace/getxattrat.md) | —FULL-brief |
| SC-inotify_add_watch | [inotify_add_watch](https://man7.org/linux/man-pages/man2/inotify_add_watch.2.html) | x64 254 · i386 292 · g64 27 · arm 317 | 2.6.13 | documented | [inotify_add_watch](./fs-mounts-namespace/inotify_add_watch.md) | —inotify |
| SC-inotify_init | [inotify_init](https://man7.org/linux/man-pages/man2/inotify_init.2.html) | x64 253 · i386 291 · g64 — · arm 316 | 2.6.13 | documented | [inotify_init](./fs-mounts-namespace/inotify_init.md) | —grouped |
| SC-inotify_init1 | [inotify_init1](https://man7.org/linux/man-pages/man2/inotify_init1.2.html) | x64 294 · i386 332 · g64 26 · arm 360 | 2.6.27 | documented | [inotify_init1](./fs-mounts-namespace/inotify_init.md) | —grouped |
| SC-inotify_rm_watch | [inotify_rm_watch](https://man7.org/linux/man-pages/man2/inotify_rm_watch.2.html) | x64 255 · i386 293 · g64 28 · arm 318 | 2.6.13 | documented | [inotify_rm_watch](./fs-mounts-namespace/inotify_rm_watch.md) | —grouped |
| SC-keyctl | [keyctl](https://man7.org/linux/man-pages/man2/keyctl.2.html) | x64 250 · i386 288 · g64 219 · arm 311 | 2.6.10 | documented | [keyctl](./fs-mounts-namespace/keyctl.md) | —keyring |
| SC-lchown | [lchown](https://man7.org/linux/man-pages/man2/lchown.2.html) | x64 94 · i386 16 · g64 — · arm 16 | 1.0 | documented | [lchown](./fs-mounts-namespace/chown.md) | —grouped |
| SC-lgetxattr | [lgetxattr](https://man7.org/linux/man-pages/man2/lgetxattr.2.html) | x64 192 · i386 230 · g64 9 · arm 230 | 2.6 | documented | [lgetxattr](./fs-mounts-namespace/getxattr.md) | —xattr |
| SC-link | [link](https://man7.org/linux/man-pages/man2/link.2.html) | x64 86 · i386 9 · g64 — · arm 9 | 1.0 | documented | [link](./fs-mounts-namespace/link.md) | —grouped |
| SC-linkat | [linkat](https://man7.org/linux/man-pages/man2/linkat.2.html) | x64 265 · i386 303 · g64 37 · arm 330 | 2.6.16 | documented | [linkat](./fs-mounts-namespace/link.md) | —grouped |
| SC-listmount | listmount | x64 458 · i386 458 · g64 458 · arm 458 | — | documented | [listmount](./fs-mounts-namespace/listmount.md) | —brief |
| SC-listns | listns | x64 470 · i386 470 · g64 470 · arm 470 | — | source-limited | [listns](./fs-mounts-namespace/listns.md) | —ENTRY |
| SC-listxattr | [listxattr](https://man7.org/linux/man-pages/man2/listxattr.2.html) | x64 194 · i386 232 · g64 11 · arm 232 | 2.6 | documented | [listxattr](./fs-mounts-namespace/listxattr.md) | —xattr |
| SC-listxattrat | listxattrat | x64 465 · i386 465 · g64 465 · arm 465 | — | source-limited | [listxattrat](./fs-mounts-namespace/listxattrat.md) | —kernel-sources-only |
| SC-llistxattr | [llistxattr](https://man7.org/linux/man-pages/man2/llistxattr.2.html) | x64 195 · i386 233 · g64 12 · arm 233 | 2.6 | documented | [llistxattr](./fs-mounts-namespace/listxattr.md) | —xattr |
| SC-lremovexattr | [lremovexattr](https://man7.org/linux/man-pages/man2/lremovexattr.2.html) | x64 198 · i386 236 · g64 15 · arm 236 | 2.6 | documented | [lremovexattr](./fs-mounts-namespace/removexattr.md) | —xattr |
| SC-lsetxattr | [lsetxattr](https://man7.org/linux/man-pages/man2/lsetxattr.2.html) | x64 189 · i386 227 · g64 6 · arm 227 | 2.6 | documented | [lsetxattr](./fs-mounts-namespace/setxattr.md) | —xattr |
| SC-mkdir | [mkdir](https://man7.org/linux/man-pages/man2/mkdir.2.html) | x64 83 · i386 39 · g64 — · arm 39 | 1.0 | documented | [mkdir](./fs-mounts-namespace/mkdir.md) | —grouped |
| SC-mkdirat | [mkdirat](https://man7.org/linux/man-pages/man2/mkdirat.2.html) | x64 258 · i386 296 · g64 34 · arm 323 | 2.6.16 | documented | [mkdirat](./fs-mounts-namespace/mkdir.md) | —grouped |
| SC-mknod | [mknod](https://man7.org/linux/man-pages/man2/mknod.2.html) | x64 133 · i386 14 · g64 — · arm 14 | 1.0 | documented | [mknod](./fs-mounts-namespace/mknod.md) | —grouped |
| SC-mknodat | [mknodat](https://man7.org/linux/man-pages/man2/mknodat.2.html) | x64 259 · i386 297 · g64 33 · arm 324 | 2.6.16 | documented | [mknodat](./fs-mounts-namespace/mknod.md) | —grouped |
| SC-mount | [mount](https://man7.org/linux/man-pages/man2/mount.2.html) | x64 165 · i386 21 · g64 40 · arm 21 | 1.0 | documented | [mount](./fs-mounts-namespace/mount.md) | —FULL |
| SC-mount_setattr | [mount_setattr](https://man7.org/linux/man-pages/man2/mount_setattr.2.html) | x64 442 · i386 442 · g64 442 · arm 442 | — | documented | [mount_setattr](./fs-mounts-namespace/mount_setattr.md) | —FULL |
| SC-move_mount | move_mount | x64 429 · i386 429 · g64 429 · arm 429 | 5.2 | documented | [move_mount](./fs-mounts-namespace/move_mount.md) | —new |
| SC-name_to_handle_at | [name_to_handle_at](https://man7.org/linux/man-pages/man2/name_to_handle_at.2.html) | x64 303 · i386 341 · g64 264 · arm 370 | 2.6.39 | documented | [name_to_handle_at](./fs-mounts-namespace/open_by_handle_at.md) | —grouped |
| SC-open_by_handle_at | [open_by_handle_at](https://man7.org/linux/man-pages/man2/open_by_handle_at.2.html) | x64 304 · i386 342 · g64 265 · arm 371 | 2.6.39 | researched | [open_by_handle_at](./fs-mounts-namespace/open_by_handle_at.md) | —brief |
| SC-open_tree | open_tree | x64 428 · i386 428 · g64 428 · arm 428 | 5.2 | documented | [open_tree](./fs-mounts-namespace/open_tree.md) | —new |
| SC-open_tree_attr | open_tree_attr | x64 467 · i386 467 · g64 467 · arm 467 | — | documented | [open_tree_attr](./fs-mounts-namespace/open_tree_attr.md) | —brief |
| SC-pivot_root | [pivot_root](https://man7.org/linux/man-pages/man2/pivot_root.2.html) | x64 155 · i386 217 · g64 41 · arm 218 | 2.3.41 | documented | [pivot_root](./fs-mounts-namespace/pivot_root.md) | —FULL |
| SC-quotactl | [quotactl](https://man7.org/linux/man-pages/man2/quotactl.2.html) | x64 179 · i386 131 · g64 60 · arm 131 | 1.0 | documented | [quotactl](./fs-mounts-namespace/quotactl.md) | —grouped |
| SC-quotactl_fd | quotactl_fd | x64 443 · i386 443 · g64 443 · arm 443 | 5.14 | documented | [quotactl_fd](./fs-mounts-namespace/quotactl_fd.md) | —grouped |
| SC-removexattr | [removexattr](https://man7.org/linux/man-pages/man2/removexattr.2.html) | x64 197 · i386 235 · g64 14 · arm 235 | 2.6 | documented | [removexattr](./fs-mounts-namespace/removexattr.md) | —xattr |
| SC-removexattrat | removexattrat | x64 466 · i386 466 · g64 466 · arm 466 | — | source-limited | [removexattrat](./fs-mounts-namespace/removexattrat.md) | —kernel-sources-only |
| SC-rename | [rename](https://man7.org/linux/man-pages/man2/rename.2.html) | x64 82 · i386 38 · g64 — · arm 38 | 1.0 | documented | [rename](./fs-mounts-namespace/rename.md) | —grouped |
| SC-renameat | [renameat](https://man7.org/linux/man-pages/man2/renameat.2.html) | x64 264 · i386 302 · g64 — · arm 329 | 2.6.16 | documented | [renameat](./fs-mounts-namespace/rename.md) | —grouped |
| SC-renameat2 | [renameat2](https://man7.org/linux/man-pages/man2/renameat2.2.html) | x64 316 · i386 353 · g64 276 · arm 382 | 3.15 | documented | [renameat2](./fs-mounts-namespace/rename.md) | —FULL |
| SC-request_key | [request_key](https://man7.org/linux/man-pages/man2/request_key.2.html) | x64 249 · i386 287 · g64 218 · arm 310 | 2.6.10 | documented | [request_key](./fs-mounts-namespace/request_key.md) | —keyring |
| SC-rmdir | [rmdir](https://man7.org/linux/man-pages/man2/rmdir.2.html) | x64 84 · i386 40 · g64 — · arm 40 | 1.0 | documented | [rmdir](./fs-mounts-namespace/rmdir.md) | —grouped |
| SC-setns | [setns](https://man7.org/linux/man-pages/man2/setns.2.html) | x64 308 · i386 346 · g64 268 · arm 375 | 3.0 | documented | [setns](./fs-mounts-namespace/setns.md) | —FULL |
| SC-setxattr | [setxattr](https://man7.org/linux/man-pages/man2/setxattr.2.html) | x64 188 · i386 226 · g64 5 · arm 226 | 2.6 | documented | [setxattr](./fs-mounts-namespace/setxattr.md) | —xattr |
| SC-setxattrat | setxattrat | x64 463 · i386 463 · g64 463 · arm 463 | — | source-limited | [setxattrat](./fs-mounts-namespace/setxattrat.md) | —kernel-sources-only |
| SC-statmount | statmount | x64 457 · i386 457 · g64 457 · arm 457 | — | documented | [statmount](./fs-mounts-namespace/statmount.md) | —brief |
| SC-symlink | [symlink](https://man7.org/linux/man-pages/man2/symlink.2.html) | x64 88 · i386 83 · g64 — · arm 83 | 1.0 | documented | [symlink](./fs-mounts-namespace/symlink.md) | —grouped |
| SC-symlinkat | [symlinkat](https://man7.org/linux/man-pages/man2/symlinkat.2.html) | x64 266 · i386 304 · g64 36 · arm 331 | 2.6.16 | documented | [symlinkat](./fs-mounts-namespace/symlink.md) | —grouped |
| SC-umount | [umount](https://man7.org/linux/man-pages/man2/umount.2.html) | x64 — · i386 22 · g64 — · arm — | 1.0 | documented | [umount](./fs-mounts-namespace/umount.md) | —grouped |
| SC-umount2 | [umount2](https://man7.org/linux/man-pages/man2/umount2.2.html) | x64 166 · i386 52 · g64 39 · arm 52 | 2.2 | documented | [umount2](./fs-mounts-namespace/umount.md) | —FULL |
| SC-unlink | [unlink](https://man7.org/linux/man-pages/man2/unlink.2.html) | x64 87 · i386 10 · g64 — · arm 10 | 1.0 | documented | [unlink](./fs-mounts-namespace/unlink.md) | —grouped |
| SC-unlinkat | [unlinkat](https://man7.org/linux/man-pages/man2/unlinkat.2.html) | x64 263 · i386 301 · g64 35 · arm 328 | 2.6.16 | documented | [unlinkat](./fs-mounts-namespace/unlink.md) | —grouped |
| SC-unshare | [unshare](https://man7.org/linux/man-pages/man2/unshare.2.html) | x64 272 · i386 310 · g64 97 · arm 337 | 2.6.16 | documented | [unshare](./fs-mounts-namespace/unshare.md) | —FULL |
| SC-utime | [utime](https://man7.org/linux/man-pages/man2/utime.2.html) | x64 132 · i386 30 · g64 — · arm — | 1.0 | documented | [utime](./fs-mounts-namespace/utime.md) | —timestamp |
| SC-utimensat | [utimensat](https://man7.org/linux/man-pages/man2/utimensat.2.html) | x64 280 · i386 320 · g64 88 · arm 348 | 2.6.22 | documented | [utimensat](./fs-mounts-namespace/utimensat.md) | —timestamp |
| SC-utimensat_time64 | utimensat_time64 | x64 — · i386 412 · g64 — · arm 412 | — | documented | [utimensat_time64](./fs-mounts-namespace/utimensat_time64.md) | —time64 |
| SC-utimes | [utimes](https://man7.org/linux/man-pages/man2/utimes.2.html) | x64 235 · i386 271 · g64 — · arm 269 | 2.2 | documented | [utimes](./fs-mounts-namespace/utime.md) | —timestamp |

### signal-time

| ID | Name | Numbers | Since | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| SC-adjtimex | [adjtimex](https://man7.org/linux/man-pages/man2/adjtimex.2.html) | x64 159 · i386 124 · g64 171 · arm 124 | 1.0 | documented | [adjtimex](./signals-time/adjtimex.md) | —full |
| SC-alarm | [alarm](https://man7.org/linux/man-pages/man2/alarm.2.html) | x64 37 · i386 27 · g64 — · arm — | 1.0 | documented | [alarm](./signals-time/alarm.md) | —full |
| SC-clock_adjtime | [clock_adjtime](https://man7.org/linux/man-pages/man2/clock_adjtime.2.html) | x64 305 · i386 343 · g64 266 · arm 372 | 2.6.39 | documented | [clock_adjtime](./signals-time/adjtimex.md) | —covered |
| SC-clock_adjtime64 | clock_adjtime64 | x64 — · i386 405 · g64 — · arm 405 | — | researched | [clock_adjtime64](./signals-time/clock_adjtime.md) | —time64 |
| SC-clock_getres | [clock_getres](https://man7.org/linux/man-pages/man2/clock_getres.2.html) | x64 229 · i386 266 · g64 114 · arm 264 | 2.6 | documented | [clock_getres](./signals-time/clock_getres.md) | —grouped |
| SC-clock_getres_time64 | clock_getres_time64 | x64 — · i386 406 · g64 — · arm 406 | — | researched | [clock_getres_time64](./signals-time/clock_getres.md) | —time64 |
| SC-clock_gettime | [clock_gettime](https://man7.org/linux/man-pages/man2/clock_gettime.2.html) | x64 228 · i386 265 · g64 113 · arm 263 | 2.6 | documented | [clock_gettime](./signals-time/clock_getres.md) | —full |
| SC-clock_gettime64 | clock_gettime64 | x64 — · i386 403 · g64 — · arm 403 | — | researched | [clock_gettime64](./signals-time/clock_getres.md) | —time64 |
| SC-clock_nanosleep | [clock_nanosleep](https://man7.org/linux/man-pages/man2/clock_nanosleep.2.html) | x64 230 · i386 267 · g64 115 · arm 265 | 2.6 | documented | [clock_nanosleep](./signals-time/clock_nanosleep.md) | —full |
| SC-clock_nanosleep_time64 | clock_nanosleep_time64 | x64 — · i386 407 · g64 — · arm 407 | — | researched | [clock_nanosleep_time64](./signals-time/clock_nanosleep.md) | —time64 |
| SC-clock_settime | [clock_settime](https://man7.org/linux/man-pages/man2/clock_settime.2.html) | x64 227 · i386 264 · g64 112 · arm 262 | 2.6 | documented | [clock_settime](./signals-time/clock_getres.md) | —grouped |
| SC-clock_settime64 | clock_settime64 | x64 — · i386 404 · g64 — · arm 404 | — | researched | [clock_settime64](./signals-time/clock_getres.md) | —time64 |
| SC-getitimer | [getitimer](https://man7.org/linux/man-pages/man2/getitimer.2.html) | x64 36 · i386 105 · g64 102 · arm 105 | 1.0 | documented | [getitimer](./signals-time/getitimer.md) | —grouped |
| SC-gettimeofday | [gettimeofday](https://man7.org/linux/man-pages/man2/gettimeofday.2.html) | x64 96 · i386 78 · g64 169 · arm 78 | 1.0 | documented | [gettimeofday](./signals-time/gettimeofday.md) | —grouped |
| SC-kill | [kill](https://man7.org/linux/man-pages/man2/kill.2.html) | x64 62 · i386 37 · g64 129 · arm 37 | 1.0 | documented | [kill](./signals-time/kill.md) | —full |
| SC-nanosleep | [nanosleep](https://man7.org/linux/man-pages/man2/nanosleep.2.html) | x64 35 · i386 162 · g64 101 · arm 162 | 2.0 | documented | [nanosleep](./signals-time/nanosleep.md) | —full |
| SC-pause | [pause](https://man7.org/linux/man-pages/man2/pause.2.html) | x64 34 · i386 29 · g64 — · arm 29 | 1.0 | documented | [pause](./signals-time/pause.md) | —full |
| SC-restart_syscall | [restart_syscall](https://man7.org/linux/man-pages/man2/restart_syscall.2.html) | x64 219 · i386 0 · g64 128 · arm 0 | 2.6 | documented | [restart_syscall](./signals-time/restart_syscall.md) | —full |
| SC-rt_sigaction | [rt_sigaction](https://man7.org/linux/man-pages/man2/rt_sigaction.2.html) | x64 13 · i386 174 · g64 134 · arm 174 | 2.2 | documented | [rt_sigaction](./signals-time/sigaction.md) | —full |
| SC-rt_sigpending | [rt_sigpending](https://man7.org/linux/man-pages/man2/rt_sigpending.2.html) | x64 127 · i386 176 · g64 136 · arm 176 | 2.2 | documented | [rt_sigpending](./signals-time/sigpending.md) | —full |
| SC-rt_sigprocmask | [rt_sigprocmask](https://man7.org/linux/man-pages/man2/rt_sigprocmask.2.html) | x64 14 · i386 175 · g64 135 · arm 175 | 2.2 | documented | [rt_sigprocmask](./signals-time/sigprocmask.md) | —full |
| SC-rt_sigqueueinfo | [rt_sigqueueinfo](https://man7.org/linux/man-pages/man2/rt_sigqueueinfo.2.html) | x64 129 · i386 178 · g64 138 · arm 178 | 2.2 | documented | [rt_sigqueueinfo](./signals-time/rt_sigqueueinfo.md) | —full |
| SC-rt_sigreturn | [rt_sigreturn](https://man7.org/linux/man-pages/man2/rt_sigreturn.2.html) | x64 15 · i386 173 · g64 139 · arm 173 | 2.2 | documented | [rt_sigreturn](./signals-time/sigreturn.md) | —full |
| SC-rt_sigsuspend | [rt_sigsuspend](https://man7.org/linux/man-pages/man2/rt_sigsuspend.2.html) | x64 130 · i386 179 · g64 133 · arm 179 | 2.2 | researched | [rt_sigsuspend](./signals-time/sigsuspend.md) | —covered |
| SC-rt_sigtimedwait | [rt_sigtimedwait](https://man7.org/linux/man-pages/man2/rt_sigtimedwait.2.html) | x64 128 · i386 177 · g64 137 · arm 177 | 2.2 | documented | [rt_sigtimedwait](./signals-time/sigtimedwait.md) | —full |
| SC-rt_sigtimedwait_time64 | rt_sigtimedwait_time64 | x64 — · i386 421 · g64 — · arm 421 | — | researched | [rt_sigtimedwait_time64](./signals-time/rt_sigtimedwait_time64.md) | —time64 |
| SC-rt_tgsigqueueinfo | [rt_tgsigqueueinfo](https://man7.org/linux/man-pages/man2/rt_tgsigqueueinfo.2.html) | x64 297 · i386 335 · g64 240 · arm 363 | 2.6.31 | documented | [rt_tgsigqueueinfo](./signals-time/rt_sigqueueinfo.md) | —covered |
| SC-setitimer | [setitimer](https://man7.org/linux/man-pages/man2/setitimer.2.html) | x64 38 · i386 104 · g64 103 · arm 104 | 1.0 | documented | [setitimer](./signals-time/getitimer.md) | —grouped |
| SC-settimeofday | [settimeofday](https://man7.org/linux/man-pages/man2/settimeofday.2.html) | x64 164 · i386 79 · g64 170 · arm 79 | 1.0 | documented | [settimeofday](./signals-time/gettimeofday.md) | —grouped |
| SC-sgetmask | [sgetmask](https://man7.org/linux/man-pages/man2/sgetmask.2.html) | x64 — · i386 68 · g64 — · arm — | 1.0 | researched | [sgetmask](./signals-time/sgetmask.md) | —legacy |
| SC-sigaction | [sigaction](https://man7.org/linux/man-pages/man2/sigaction.2.html) | x64 — · i386 67 · g64 — · arm 67 | 1.0 | researched | [sigaction](./signals-time/sigaction.md) | —legacy |
| SC-sigaltstack | [sigaltstack](https://man7.org/linux/man-pages/man2/sigaltstack.2.html) | x64 131 · i386 186 · g64 132 · arm 186 | 2.2 | documented | [sigaltstack](./signals-time/sigaltstack.md) | —full |
| SC-signal | [signal](https://man7.org/linux/man-pages/man2/signal.2.html) | x64 — · i386 48 · g64 — · arm — | 1.0 | researched | [signal](./signals-time/signal.md) | —legacy |
| SC-sigpending | [sigpending](https://man7.org/linux/man-pages/man2/sigpending.2.html) | x64 — · i386 73 · g64 — · arm 73 | 1.0 | researched | [sigpending](./signals-time/sigpending.md) | —legacy |
| SC-sigprocmask | [sigprocmask](https://man7.org/linux/man-pages/man2/sigprocmask.2.html) | x64 — · i386 126 · g64 — · arm 126 | 1.0 | researched | [sigprocmask](./signals-time/sigprocmask.md) | —legacy |
| SC-sigreturn | [sigreturn](https://man7.org/linux/man-pages/man2/sigreturn.2.html) | x64 — · i386 119 · g64 — · arm 119 | 1.0 | researched | [sigreturn](./signals-time/sigreturn.md) | —legacy |
| SC-sigsuspend | [sigsuspend](https://man7.org/linux/man-pages/man2/sigsuspend.2.html) | x64 — · i386 72 · g64 — · arm 72 | 1.0 | researched | [sigsuspend](./signals-time/sigsuspend.md) | —legacy |
| SC-ssetmask | [ssetmask](https://man7.org/linux/man-pages/man2/ssetmask.2.html) | x64 — · i386 69 · g64 — · arm — | 1.0 | researched | [ssetmask](./signals-time/sgetmask.md) | —legacy |
| SC-stime | [stime](https://man7.org/linux/man-pages/man2/stime.2.html) | x64 — · i386 25 · g64 — · arm — | 1.0 | source-limited | [stime](./signals-time/stime.md) | —inventory |
| SC-tgkill | [tgkill](https://man7.org/linux/man-pages/man2/tgkill.2.html) | x64 234 · i386 270 · g64 131 · arm 268 | 2.6 | documented | [tgkill](./signals-time/tkill.md) | —grouped |
| SC-time | [time](https://man7.org/linux/man-pages/man2/time.2.html) | x64 201 · i386 13 · g64 — · arm — | 1.0 | documented | [time](./signals-time/time.md) | —grouped |
| SC-timer_create | [timer_create](https://man7.org/linux/man-pages/man2/timer_create.2.html) | x64 222 · i386 259 · g64 107 · arm 257 | 2.6 | documented | [timer_create](./signals-time/timer_create.md) | —grouped |
| SC-timer_delete | [timer_delete](https://man7.org/linux/man-pages/man2/timer_delete.2.html) | x64 226 · i386 263 · g64 111 · arm 261 | 2.6 | documented | [timer_delete](./signals-time/timer_delete.md) | —grouped |
| SC-timer_getoverrun | [timer_getoverrun](https://man7.org/linux/man-pages/man2/timer_getoverrun.2.html) | x64 225 · i386 262 · g64 109 · arm 260 | 2.6 | documented | [timer_getoverrun](./signals-time/timer_getoverrun.md) | —grouped |
| SC-timer_gettime | [timer_gettime](https://man7.org/linux/man-pages/man2/timer_gettime.2.html) | x64 224 · i386 261 · g64 108 · arm 259 | 2.6 | documented | [timer_gettime](./signals-time/timer_settime.md) | —grouped |
| SC-timer_gettime64 | timer_gettime64 | x64 — · i386 408 · g64 — · arm 408 | — | researched | [timer_gettime64](./signals-time/timer_settime.md) | —time64 |
| SC-timer_settime | [timer_settime](https://man7.org/linux/man-pages/man2/timer_settime.2.html) | x64 223 · i386 260 · g64 110 · arm 258 | 2.6 | documented | [timer_settime](./signals-time/timer_settime.md) | —grouped |
| SC-timer_settime64 | timer_settime64 | x64 — · i386 409 · g64 — · arm 409 | — | researched | [timer_settime64](./signals-time/timer_settime.md) | —time64 |
| SC-times | [times](https://man7.org/linux/man-pages/man2/times.2.html) | x64 100 · i386 43 · g64 153 · arm 43 | 1.0 | documented | [times](./signals-time/times.md) | —full |
| SC-tkill | [tkill](https://man7.org/linux/man-pages/man2/tkill.2.html) | x64 200 · i386 238 · g64 130 · arm 238 | 2.6 | documented | [tkill](./signals-time/tkill.md) | —grouped |

### sched-misc

| ID | Name | Numbers | Since | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| SC-_sysctl | [_sysctl](https://man7.org/linux/man-pages/man2/_sysctl.2.html) | x64 156 · i386 149 · g64 — · arm 149 | 2.0 | source-limited | [_sysctl](./sched-misc/sysctl.md) | —inventory |
| SC-afs_syscall | [afs_syscall](https://man7.org/linux/man-pages/man2/afs_syscall.2.html) | x64 183 · i386 137 · g64 — · arm — | — | source-limited | [afs_syscall](./sched-misc/unimplemented.md) | —inventory |
| SC-alloc_hugepages | [alloc_hugepages](https://man7.org/linux/man-pages/man2/alloc_hugepages.2.html) | x64 — · i386 — · g64 — · arm — | 2.5.36 | source-limited | [alloc_hugepages](./sched-misc/alloc_hugepages.md) | —inventory |
| SC-arc_gettls | arc_gettls | x64 — · i386 — · g64 — · arm — | 3.9 | source-limited | [arc_gettls](./sched-misc/arc_gettls.md) | —inventory |
| SC-arc_settls | arc_settls | x64 — · i386 — · g64 — · arm — | 3.9 | source-limited | [arc_settls](./sched-misc/arc_settls.md) | —inventory |
| SC-arc_usr_cmpxchg | arc_usr_cmpxchg | x64 — · i386 — · g64 — · arm — | 4.9 | source-limited | [arc_usr_cmpxchg](./sched-misc/arc_usr_cmpxchg.md) | —inventory |
| SC-atomic_barrier | atomic_barrier | x64 — · i386 — · g64 — · arm — | 2.6.34 | source-limited | [atomic_barrier](./sched-misc/atomic_barrier.md) | —inventory |
| SC-atomic_cmpxchg_32 | atomic_cmpxchg_32 | x64 — · i386 — · g64 — · arm — | 2.6.34 | source-limited | [atomic_cmpxchg_32](./sched-misc/atomic_cmpxchg_32.md) | —inventory |
| SC-bdflush | [bdflush](https://man7.org/linux/man-pages/man2/bdflush.2.html) | x64 — · i386 134 · g64 — · arm 134 | 1.2 | source-limited | [bdflush](./sched-misc/bdflush.md) | —inventory |
| SC-bpf | [bpf](https://man7.org/linux/man-pages/man2/bpf.2.html) | x64 321 · i386 357 · g64 280 · arm 386 | 3.18 | documented | [bpf](./sched-misc/bpf.md) | —full |
| SC-break | [break](https://man7.org/linux/man-pages/man2/break.2.html) | x64 — · i386 17 · g64 — · arm — | — | source-limited | [break](./sched-misc/unimplemented.md) | —inventory |
| SC-breakpoint | breakpoint | x64 — · i386 — · g64 — · arm — | 2.2 | source-limited | [breakpoint](./sched-misc/breakpoint.md) | —inventory |
| SC-cacheflush | [cacheflush](https://man7.org/linux/man-pages/man2/cacheflush.2.html) | x64 — · i386 — · g64 — · arm — | 1.2 | source-limited | [cacheflush](./sched-misc/cacheflush.md) | —inventory |
| SC-create_module | [create_module](https://man7.org/linux/man-pages/man2/create_module.2.html) | x64 174 · i386 127 · g64 — · arm — | 1.0 | source-limited | [create_module](./sched-misc/create_module.md) | —inventory |
| SC-delete_module | [delete_module](https://man7.org/linux/man-pages/man2/delete_module.2.html) | x64 176 · i386 129 · g64 106 · arm 129 | 1.0 | documented | [delete_module](./sched-misc/delete_module.md) | —full |
| SC-finit_module | [finit_module](https://man7.org/linux/man-pages/man2/finit_module.2.html) | x64 313 · i386 350 · g64 273 · arm 379 | 3.8 | documented | [finit_module](./sched-misc/init_module.md) | —full |
| SC-free_hugepages | [free_hugepages](https://man7.org/linux/man-pages/man2/free_hugepages.2.html) | x64 — · i386 — · g64 — · arm — | 2.5.36 | source-limited | [free_hugepages](./sched-misc/alloc_hugepages.md) | —inventory |
| SC-ftime | ftime | x64 — · i386 35 · g64 — · arm — | — | source-limited | [ftime](./sched-misc/ftime.md) | —inventory |
| SC-get_kernel_syms | [get_kernel_syms](https://man7.org/linux/man-pages/man2/get_kernel_syms.2.html) | x64 177 · i386 130 · g64 — · arm — | 1.0 | source-limited | [get_kernel_syms](./sched-misc/get_kernel_syms.md) | —inventory |
| SC-get_thread_area | [get_thread_area](https://man7.org/linux/man-pages/man2/get_thread_area.2.html) | x64 211 · i386 244 · g64 — · arm — | 2.6 | researched | [get_thread_area](./sched-misc/set_thread_area.md) | —brief |
| SC-get_tls | get_tls | x64 — · i386 — · g64 — · arm — | 4.15 | source-limited | [get_tls](./sched-misc/get_tls.md) | —inventory |
| SC-getcpu | [getcpu](https://man7.org/linux/man-pages/man2/getcpu.2.html) | x64 309 · i386 318 · g64 168 · arm 345 | 2.6.19 | documented | [getcpu](./sched-misc/getcpu.md) | —full |
| SC-getdtablesize | getdtablesize | x64 — · i386 — · g64 — · arm — | 2.0 | source-limited | [getdtablesize](./sched-misc/getdtablesize.md) | —inventory |
| SC-getpagesize | [getpagesize](https://man7.org/linux/man-pages/man2/getpagesize.2.html) | x64 — · i386 — · g64 — · arm — | 2.0 | source-limited | [getpagesize](./sched-misc/getpagesize.md) | —inventory |
| SC-getpmsg | [getpmsg](https://man7.org/linux/man-pages/man2/getpmsg.2.html) | x64 181 · i386 188 · g64 — · arm — | — | source-limited | [getpmsg](./sched-misc/unimplemented.md) | —inventory |
| SC-getpriority | [getpriority](https://man7.org/linux/man-pages/man2/getpriority.2.html) | x64 140 · i386 96 · g64 141 · arm 96 | 1.0 | documented | [getpriority](./sched-misc/getpriority.md) | —full |
| SC-getrandom | [getrandom](https://man7.org/linux/man-pages/man2/getrandom.2.html) | x64 318 · i386 355 · g64 278 · arm 384 | 3.17 | documented | [getrandom](./sched-misc/getrandom.md) | —full |
| SC-getunwind | [getunwind](https://man7.org/linux/man-pages/man2/getunwind.2.html) | x64 — · i386 — · g64 — · arm — | 2.4.8 | source-limited | [getunwind](./sched-misc/getunwind.md) | —inventory |
| SC-getxgid | getxgid | x64 — · i386 — · g64 — · arm — | 2.0 | source-limited | [getxgid](./sched-misc/getxgid.md) | —inventory |
| SC-getxpid | getxpid | x64 — · i386 — · g64 — · arm — | 2.0 | source-limited | [getxpid](./sched-misc/getxpid.md) | —inventory |
| SC-getxuid | getxuid | x64 — · i386 — · g64 — · arm — | 2.0 | source-limited | [getxuid](./sched-misc/getxuid.md) | —inventory |
| SC-gtty | [gtty](https://man7.org/linux/man-pages/man2/gtty.2.html) | x64 — · i386 32 · g64 — · arm — | — | source-limited | [gtty](./sched-misc/unimplemented.md) | —inventory |
| SC-idle | [idle](https://man7.org/linux/man-pages/man2/idle.2.html) | x64 — · i386 112 · g64 — · arm — | — | source-limited | [idle](./sched-misc/idle.md) | —inventory |
| SC-init_module | [init_module](https://man7.org/linux/man-pages/man2/init_module.2.html) | x64 175 · i386 128 · g64 105 · arm 128 | 1.0 | documented | [init_module](./sched-misc/init_module.md) | —full |
| SC-ioperm | [ioperm](https://man7.org/linux/man-pages/man2/ioperm.2.html) | x64 173 · i386 101 · g64 — · arm — | 1.0 | researched | [ioperm](./sched-misc/ioperm.md) | —brief |
| SC-iopl | [iopl](https://man7.org/linux/man-pages/man2/iopl.2.html) | x64 172 · i386 110 · g64 — · arm — | 1.0 | researched | [iopl](./sched-misc/iopl.md) | —brief |
| SC-ioprio_get | [ioprio_get](https://man7.org/linux/man-pages/man2/ioprio_get.2.html) | x64 252 · i386 290 · g64 31 · arm 315 | 2.6.13 | documented | [ioprio_get](./sched-misc/ioprio_set.md) | —full |
| SC-ioprio_set | [ioprio_set](https://man7.org/linux/man-pages/man2/ioprio_set.2.html) | x64 251 · i386 289 · g64 30 · arm 314 | 2.6.13 | documented | [ioprio_set](./sched-misc/ioprio_set.md) | —full |
| SC-kcmp | [kcmp](https://man7.org/linux/man-pages/man2/kcmp.2.html) | x64 312 · i386 349 · g64 272 · arm 378 | 3.5 | documented | [kcmp](./sched-misc/kcmp.md) | —full |
| SC-kern_features | kern_features | x64 — · i386 — · g64 — · arm — | 3.7 | source-limited | [kern_features](./sched-misc/kern_features.md) | —inventory |
| SC-kexec_file_load | [kexec_file_load](https://man7.org/linux/man-pages/man2/kexec_file_load.2.html) | x64 320 · i386 — · g64 294 · arm 401 | 3.17 | documented | [kexec_file_load](./sched-misc/kexec_load.md) | —full |
| SC-kexec_load | [kexec_load](https://man7.org/linux/man-pages/man2/kexec_load.2.html) | x64 246 · i386 283 · g64 104 · arm 347 | 2.6.13 | documented | [kexec_load](./sched-misc/kexec_load.md) | —full |
| SC-landlock_add_rule | landlock_add_rule | x64 445 · i386 445 · g64 445 · arm 445 | 5.13 | documented | [landlock_add_rule](./sched-misc/landlock_add_rule.md) | —full |
| SC-landlock_create_ruleset | landlock_create_ruleset | x64 444 · i386 444 · g64 444 · arm 444 | 5.13 | documented | [landlock_create_ruleset](./sched-misc/landlock_create_ruleset.md) | —full |
| SC-landlock_restrict_self | landlock_restrict_self | x64 446 · i386 446 · g64 446 · arm 446 | 5.13 | documented | [landlock_restrict_self](./sched-misc/landlock_restrict_self.md) | —full |
| SC-lock | [lock](https://man7.org/linux/man-pages/man2/lock.2.html) | x64 — · i386 53 · g64 — · arm — | — | source-limited | [lock](./sched-misc/unimplemented.md) | —inventory |
| SC-lookup_dcookie | [lookup_dcookie](https://man7.org/linux/man-pages/man2/lookup_dcookie.2.html) | x64 212 · i386 253 · g64 18 · arm 249 | 2.6 | documented | [lookup_dcookie](./sched-misc/lookup_dcookie.md) | —full |
| SC-lsm_get_self_attr | lsm_get_self_attr | x64 459 · i386 459 · g64 459 · arm 459 | — | documented | [lsm_get_self_attr](./sched-misc/lsm_get_self_attr.md) | —full |
| SC-lsm_list_modules | lsm_list_modules | x64 461 · i386 461 · g64 461 · arm 461 | — | documented | [lsm_list_modules](./sched-misc/lsm_list_modules.md) | —full |
| SC-lsm_set_self_attr | lsm_set_self_attr | x64 460 · i386 460 · g64 460 · arm 460 | — | documented | [lsm_set_self_attr](./sched-misc/lsm_set_self_attr.md) | —full |
| SC-memory_ordering | memory_ordering | x64 — · i386 — · g64 — · arm — | 2.2 | source-limited | [memory_ordering](./sched-misc/memory_ordering.md) | —inventory |
| SC-modify_ldt | [modify_ldt](https://man7.org/linux/man-pages/man2/modify_ldt.2.html) | x64 154 · i386 123 · g64 — · arm — | 1.0 | source-limited | [modify_ldt](./sched-misc/modify_ldt.md) | —inventory |
| SC-mpx | [mpx](https://man7.org/linux/man-pages/man2/mpx.2.html) | x64 — · i386 56 · g64 — · arm — | — | source-limited | [mpx](./sched-misc/unimplemented.md) | —inventory |
| SC-nfsservctl | [nfsservctl](https://man7.org/linux/man-pages/man2/nfsservctl.2.html) | x64 180 · i386 169 · g64 42 · arm 169 | 2.2 | source-limited | [nfsservctl](./sched-misc/nfsservctl.md) | —inventory |
| SC-nice | [nice](https://man7.org/linux/man-pages/man2/nice.2.html) | x64 — · i386 34 · g64 — · arm 34 | 1.0 | documented | [nice](./sched-misc/nice.md) | —full |
| SC-old_adjtimex | old_adjtimex | x64 — · i386 — · g64 — · arm — | 2.0 | source-limited | [old_adjtimex](./sched-misc/old_adjtimex.md) | —inventory |
| SC-old_getrlimit | old_getrlimit | x64 — · i386 — · g64 — · arm — | 2.4 | source-limited | [old_getrlimit](./sched-misc/old_getrlimit.md) | —inventory |
| SC-oldfstat | [oldfstat](https://man7.org/linux/man-pages/man2/oldfstat.2.html) | x64 — · i386 28 · g64 — · arm — | 1.0 | source-limited | [oldfstat](./sched-misc/stat.md) | —inventory |
| SC-oldlstat | [oldlstat](https://man7.org/linux/man-pages/man2/oldlstat.2.html) | x64 — · i386 84 · g64 — · arm — | 1.0 | source-limited | [oldlstat](./sched-misc/stat.md) | —inventory |
| SC-oldolduname | [oldolduname](https://man7.org/linux/man-pages/man2/oldolduname.2.html) | x64 — · i386 59 · g64 — · arm — | 1.0 | source-limited | [oldolduname](./sched-misc/uname.md) | —inventory |
| SC-oldstat | [oldstat](https://man7.org/linux/man-pages/man2/oldstat.2.html) | x64 — · i386 18 · g64 — · arm — | 1.0 | source-limited | [oldstat](./sched-misc/stat.md) | —inventory |
| SC-oldumount | oldumount | x64 — · i386 — · g64 — · arm — | 2.4.116 | source-limited | [oldumount](./sched-misc/oldumount.md) | —inventory |
| SC-olduname | [olduname](https://man7.org/linux/man-pages/man2/olduname.2.html) | x64 — · i386 109 · g64 — · arm — | 1.0 | source-limited | [olduname](./sched-misc/uname.md) | —inventory |
| SC-or1k_atomic | or1k_atomic | x64 — · i386 — · g64 — · arm — | 3.1 | source-limited | [or1k_atomic](./sched-misc/or1k_atomic.md) | —inventory |
| SC-pciconfig_iobase | [pciconfig_iobase](https://man7.org/linux/man-pages/man2/pciconfig_iobase.2.html) | x64 — · i386 — · g64 — · arm 271 | 2.2.15 | source-limited | [pciconfig_iobase](./sched-misc/pciconfig_read.md) | —inventory |
| SC-pciconfig_read | [pciconfig_read](https://man7.org/linux/man-pages/man2/pciconfig_read.2.html) | x64 — · i386 — · g64 — · arm 272 | 2.0.26 | source-limited | [pciconfig_read](./sched-misc/pciconfig_read.md) | —inventory |
| SC-pciconfig_write | [pciconfig_write](https://man7.org/linux/man-pages/man2/pciconfig_write.2.html) | x64 — · i386 — · g64 — · arm 273 | 2.0.26 | source-limited | [pciconfig_write](./sched-misc/pciconfig_read.md) | —inventory |
| SC-perf_event_open | [perf_event_open](https://man7.org/linux/man-pages/man2/perf_event_open.2.html) | x64 298 · i386 336 · g64 241 · arm 364 | 2.6.31 | documented | [perf_event_open](./sched-misc/perf_event_open.md) | —full |
| SC-perfctr | perfctr | x64 — · i386 — · g64 — · arm — | 2.2 | source-limited | [perfctr](./sched-misc/perfctr.md) | —inventory |
| SC-perfmonctl | [perfmonctl](https://man7.org/linux/man-pages/man2/perfmonctl.2.html) | x64 — · i386 — · g64 — · arm — | 2.4 | source-limited | [perfmonctl](./sched-misc/perfmonctl.md) | —inventory |
| SC-prof | [prof](https://man7.org/linux/man-pages/man2/prof.2.html) | x64 — · i386 44 · g64 — · arm — | — | source-limited | [prof](./sched-misc/unimplemented.md) | —inventory |
| SC-profil | profil | x64 — · i386 98 · g64 — · arm — | — | source-limited | [profil](./sched-misc/profil.md) | —inventory |
| SC-putpmsg | [putpmsg](https://man7.org/linux/man-pages/man2/putpmsg.2.html) | x64 182 · i386 189 · g64 — · arm — | — | source-limited | [putpmsg](./sched-misc/unimplemented.md) | —inventory |
| SC-query_module | [query_module](https://man7.org/linux/man-pages/man2/query_module.2.html) | x64 178 · i386 167 · g64 — · arm — | 2.2 | source-limited | [query_module](./sched-misc/query_module.md) | —inventory |
| SC-reboot | [reboot](https://man7.org/linux/man-pages/man2/reboot.2.html) | x64 169 · i386 88 · g64 142 · arm 88 | 1.0 | documented | [reboot](./sched-misc/reboot.md) | —full |
| SC-riscv_flush_icache | riscv_flush_icache | x64 — · i386 — · g64 — · arm — | 4.15 | source-limited | [riscv_flush_icache](./sched-misc/riscv_flush_icache.md) | —inventory |
| SC-rtas | rtas | x64 — · i386 — · g64 — · arm — | 2.6.2 | source-limited | [rtas](./sched-misc/rtas.md) | —inventory |
| SC-s390_guarded_storage | [s390_guarded_storage](https://man7.org/linux/man-pages/man2/s390_guarded_storage.2.html) | x64 — · i386 — · g64 — · arm — | 4.12 | source-limited | [s390_guarded_storage](./sched-misc/s390_guarded_storage.md) | —inventory |
| SC-s390_pci_mmio_read | [s390_pci_mmio_read](https://man7.org/linux/man-pages/man2/s390_pci_mmio_read.2.html) | x64 — · i386 — · g64 — · arm — | 3.19 | source-limited | [s390_pci_mmio_read](./sched-misc/s390_pci_mmio_write.md) | —inventory |
| SC-s390_pci_mmio_write | [s390_pci_mmio_write](https://man7.org/linux/man-pages/man2/s390_pci_mmio_write.2.html) | x64 — · i386 — · g64 — · arm — | 3.19 | source-limited | [s390_pci_mmio_write](./sched-misc/s390_pci_mmio_write.md) | —inventory |
| SC-s390_runtime_instr | [s390_runtime_instr](https://man7.org/linux/man-pages/man2/s390_runtime_instr.2.html) | x64 — · i386 — · g64 — · arm — | 3.7 | source-limited | [s390_runtime_instr](./sched-misc/s390_runtime_instr.md) | —inventory |
| SC-s390_sthyi | [s390_sthyi](https://man7.org/linux/man-pages/man2/s390_sthyi.2.html) | x64 — · i386 — · g64 — · arm — | 4.15 | source-limited | [s390_sthyi](./sched-misc/s390_sthyi.md) | —inventory |
| SC-sched_get_affinity | sched_get_affinity | x64 — · i386 — · g64 — · arm — | 2.6 | researched | [sched_get_affinity](./sched-misc/sched_get_affinity.md) | —brief |
| SC-sched_get_priority_max | [sched_get_priority_max](https://man7.org/linux/man-pages/man2/sched_get_priority_max.2.html) | x64 146 · i386 159 · g64 125 · arm 159 | 2.0 | documented | [sched_get_priority_max](./sched-misc/sched_get_priority_max.md) | —full |
| SC-sched_get_priority_min | [sched_get_priority_min](https://man7.org/linux/man-pages/man2/sched_get_priority_min.2.html) | x64 147 · i386 160 · g64 126 · arm 160 | 2.0 | documented | [sched_get_priority_min](./sched-misc/sched_get_priority_max.md) | —full |
| SC-sched_getaffinity | [sched_getaffinity](https://man7.org/linux/man-pages/man2/sched_getaffinity.2.html) | x64 204 · i386 242 · g64 123 · arm 242 | 2.6 | documented | [sched_getaffinity](./sched-misc/sched_setaffinity.md) | —full |
| SC-sched_getattr | [sched_getattr](https://man7.org/linux/man-pages/man2/sched_getattr.2.html) | x64 315 · i386 352 · g64 275 · arm 381 | 3.14 | documented | [sched_getattr](./sched-misc/sched_setattr.md) | —full |
| SC-sched_getparam | [sched_getparam](https://man7.org/linux/man-pages/man2/sched_getparam.2.html) | x64 143 · i386 155 · g64 121 · arm 155 | 2.0 | documented | [sched_getparam](./sched-misc/sched_setparam.md) | —full |
| SC-sched_getscheduler | [sched_getscheduler](https://man7.org/linux/man-pages/man2/sched_getscheduler.2.html) | x64 145 · i386 157 · g64 120 · arm 157 | 2.0 | documented | [sched_getscheduler](./sched-misc/sched_setscheduler.md) | —full |
| SC-sched_rr_get_interval | [sched_rr_get_interval](https://man7.org/linux/man-pages/man2/sched_rr_get_interval.2.html) | x64 148 · i386 161 · g64 127 · arm 161 | 2.0 | documented | [sched_rr_get_interval](./sched-misc/sched_rr_get_interval.md) | —full |
| SC-sched_rr_get_interval_time64 | sched_rr_get_interval_time64 | x64 — · i386 423 · g64 — · arm 423 | — | source-limited | [sched_rr_get_interval_time64](./sched-misc/sched_rr_get_interval_time64.md) | —inventory |
| SC-sched_set_affinity | sched_set_affinity | x64 — · i386 — · g64 — · arm — | 2.6 | researched | [sched_set_affinity](./sched-misc/sched_set_affinity.md) | —brief |
| SC-sched_setaffinity | [sched_setaffinity](https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html) | x64 203 · i386 241 · g64 122 · arm 241 | 2.6 | documented | [sched_setaffinity](./sched-misc/sched_setaffinity.md) | —full |
| SC-sched_setattr | [sched_setattr](https://man7.org/linux/man-pages/man2/sched_setattr.2.html) | x64 314 · i386 351 · g64 274 · arm 380 | 3.14 | documented | [sched_setattr](./sched-misc/sched_setattr.md) | —full |
| SC-sched_setparam | [sched_setparam](https://man7.org/linux/man-pages/man2/sched_setparam.2.html) | x64 142 · i386 154 · g64 118 · arm 154 | 2.0 | documented | [sched_setparam](./sched-misc/sched_setparam.md) | —full |
| SC-sched_setscheduler | [sched_setscheduler](https://man7.org/linux/man-pages/man2/sched_setscheduler.2.html) | x64 144 · i386 156 · g64 119 · arm 156 | 2.0 | documented | [sched_setscheduler](./sched-misc/sched_setscheduler.md) | —full |
| SC-sched_yield | [sched_yield](https://man7.org/linux/man-pages/man2/sched_yield.2.html) | x64 24 · i386 158 · g64 124 · arm 158 | 2.0 | documented | [sched_yield](./sched-misc/sched_yield.md) | —full |
| SC-seccomp | [seccomp](https://man7.org/linux/man-pages/man2/seccomp.2.html) | x64 317 · i386 354 · g64 277 · arm 383 | 3.17 | documented | [seccomp](./sched-misc/seccomp.md) | —full |
| SC-security | [security](https://man7.org/linux/man-pages/man2/security.2.html) | x64 185 · i386 — · g64 — · arm — | — | source-limited | [security](./sched-misc/unimplemented.md) | —inventory |
| SC-set_thread_area | [set_thread_area](https://man7.org/linux/man-pages/man2/set_thread_area.2.html) | x64 205 · i386 243 · g64 — · arm — | 2.6 | researched | [set_thread_area](./sched-misc/set_thread_area.md) | —brief |
| SC-set_tls | set_tls | x64 — · i386 — · g64 — · arm — | 2.6.11 | source-limited | [set_tls](./sched-misc/set_tls.md) | —inventory |
| SC-sethae | sethae | x64 — · i386 — · g64 — · arm — | 2.0 | source-limited | [sethae](./sched-misc/sethae.md) | —inventory |
| SC-setpriority | [setpriority](https://man7.org/linux/man-pages/man2/setpriority.2.html) | x64 141 · i386 97 · g64 140 · arm 97 | 1.0 | documented | [setpriority](./sched-misc/getpriority.md) | —full |
| SC-setup | [setup](https://man7.org/linux/man-pages/man2/setup.2.html) | x64 — · i386 — · g64 — · arm — | 1.0 | source-limited | [setup](./sched-misc/setup.md) | —inventory |
| SC-spill | spill | x64 — · i386 — · g64 — · arm — | 2.6.13 | source-limited | [spill](./sched-misc/spill.md) | —inventory |
| SC-spu_create | [spu_create](https://man7.org/linux/man-pages/man2/spu_create.2.html) | x64 — · i386 — · g64 — · arm — | 2.6.16 | source-limited | [spu_create](./sched-misc/spu_create.md) | —inventory |
| SC-spu_run | [spu_run](https://man7.org/linux/man-pages/man2/spu_run.2.html) | x64 — · i386 — · g64 — · arm — | 2.6.16 | source-limited | [spu_run](./sched-misc/spu_run.md) | —inventory |
| SC-stty | [stty](https://man7.org/linux/man-pages/man2/stty.2.html) | x64 — · i386 31 · g64 — · arm — | — | source-limited | [stty](./sched-misc/unimplemented.md) | —inventory |
| SC-subpage_prot | [subpage_prot](https://man7.org/linux/man-pages/man2/subpage_prot.2.html) | x64 — · i386 — · g64 — · arm — | 2.6.25 | source-limited | [subpage_prot](./sched-misc/subpage_prot.md) | —inventory |
| SC-swapcontext | swapcontext | x64 — · i386 — · g64 — · arm — | 2.6.3 | source-limited | [swapcontext](./sched-misc/swapcontext.md) | —inventory |
| SC-switch_endian | switch_endian | x64 — · i386 — · g64 — · arm — | 4.1 | source-limited | [switch_endian](./sched-misc/switch_endian.md) | —inventory |
| SC-sys_debug_setcontext | sys_debug_setcontext | x64 — · i386 — · g64 — · arm — | 2.6.11 | source-limited | [sys_debug_setcontext](./sched-misc/sys_debug_setcontext.md) | —inventory |
| SC-syscall | [syscall](https://man7.org/linux/man-pages/man2/syscall.2.html) | x64 — · i386 — · g64 — · arm — | 1.0 | researched | [syscall](./sched-misc/syscall.md) | —brief |
| SC-sysfs | [sysfs](https://man7.org/linux/man-pages/man2/sysfs.2.html) | x64 139 · i386 135 · g64 — · arm 135 | 1.2 | source-limited | [sysfs](./sched-misc/sysfs.md) | —inventory |
| SC-sysinfo | [sysinfo](https://man7.org/linux/man-pages/man2/sysinfo.2.html) | x64 99 · i386 116 · g64 179 · arm 116 | 1.0 | documented | [sysinfo](./sched-misc/sysinfo.md) | —full |
| SC-syslog | [syslog](https://man7.org/linux/man-pages/man2/syslog.2.html) | x64 103 · i386 103 · g64 116 · arm 103 | 1.0 | documented | [syslog](./sched-misc/syslog.md) | —full |
| SC-sysmips | sysmips | x64 — · i386 — · g64 — · arm — | 2.6.0 | source-limited | [sysmips](./sched-misc/sysmips.md) | —inventory |
| SC-tuxcall | [tuxcall](https://man7.org/linux/man-pages/man2/tuxcall.2.html) | x64 184 · i386 — · g64 — · arm — | — | source-limited | [tuxcall](./sched-misc/unimplemented.md) | —inventory |
| SC-ulimit | ulimit | x64 — · i386 58 · g64 — · arm — | — | source-limited | [ulimit](./sched-misc/ulimit.md) | —inventory |
| SC-uprobe | uprobe | x64 336 · i386 — · g64 — · arm — | — | source-limited | [uprobe](./sched-misc/uprobe.md) | —inventory |
| SC-uretprobe | uretprobe | x64 335 · i386 — · g64 — · arm — | — | source-limited | [uretprobe](./sched-misc/uretprobe.md) | —inventory |
| SC-uselib | [uselib](https://man7.org/linux/man-pages/man2/uselib.2.html) | x64 134 · i386 86 · g64 — · arm 86 | 1.0 | source-limited | [uselib](./sched-misc/uselib.md) | —inventory |
| SC-usr26 | usr26 | x64 — · i386 — · g64 — · arm — | 2.4.8.1 | source-limited | [usr26](./sched-misc/usr26.md) | —inventory |
| SC-usr32 | usr32 | x64 — · i386 — · g64 — · arm — | 2.4.8.1 | source-limited | [usr32](./sched-misc/usr32.md) | —inventory |
| SC-ustat | [ustat](https://man7.org/linux/man-pages/man2/ustat.2.html) | x64 136 · i386 62 · g64 — · arm 62 | 1.0 | source-limited | [ustat](./sched-misc/ustat.md) | —inventory |
| SC-utrap_install | utrap_install | x64 — · i386 — · g64 — · arm — | 2.2 | source-limited | [utrap_install](./sched-misc/utrap_install.md) | —inventory |
| SC-vhangup | [vhangup](https://man7.org/linux/man-pages/man2/vhangup.2.html) | x64 153 · i386 111 · g64 58 · arm 111 | 1.0 | researched | [vhangup](./sched-misc/vhangup.md) | —brief |
| SC-vm86 | [vm86](https://man7.org/linux/man-pages/man2/vm86.2.html) | x64 — · i386 166 · g64 — · arm — | 2.0.28 | source-limited | [vm86](./sched-misc/vm86.md) | —inventory |
| SC-vm86old | [vm86old](https://man7.org/linux/man-pages/man2/vm86old.2.html) | x64 — · i386 113 · g64 — · arm — | 1.0 | source-limited | [vm86old](./sched-misc/vm86.md) | —inventory |
| SC-vserver | [vserver](https://man7.org/linux/man-pages/man2/vserver.2.html) | x64 236 · i386 273 · g64 — · arm 313 | — | source-limited | [vserver](./sched-misc/unimplemented.md) | —inventory |
| SC-xtensa | xtensa | x64 — · i386 — · g64 — · arm — | 2.6.13 | source-limited | [xtensa](./sched-misc/xtensa.md) | —inventory |

### net-ipc

| ID | Name | Numbers | Since | Status | Chapter | Notes |
|---|---|---|---|---|---|---|
| SC-_newselect | [_newselect](https://man7.org/linux/man-pages/man2/_newselect.2.html) | x64 — · i386 142 · g64 — · arm 142 | 2.0 | researched | [_newselect](./net-ipc/select.md) | —brief |
| SC-accept | [accept](https://man7.org/linux/man-pages/man2/accept.2.html) | x64 43 · i386 — · g64 202 · arm 285 | 2.0 | documented | [accept](./net-ipc/accept.md) | —full |
| SC-accept4 | [accept4](https://man7.org/linux/man-pages/man2/accept4.2.html) | x64 288 · i386 364 · g64 242 · arm 366 | 2.6.28 | documented | [accept4](./net-ipc/accept.md) | —full |
| SC-bind | [bind](https://man7.org/linux/man-pages/man2/bind.2.html) | x64 49 · i386 361 · g64 200 · arm 282 | 2.0 | documented | [bind](./net-ipc/bind.md) | —full |
| SC-connect | [connect](https://man7.org/linux/man-pages/man2/connect.2.html) | x64 42 · i386 362 · g64 203 · arm 283 | 2.0 | documented | [connect](./net-ipc/connect.md) | —full |
| SC-epoll_create | [epoll_create](https://man7.org/linux/man-pages/man2/epoll_create.2.html) | x64 213 · i386 254 · g64 — · arm 250 | 2.6 | documented | [epoll_create](./net-ipc/epoll_create.md) | —full |
| SC-epoll_create1 | [epoll_create1](https://man7.org/linux/man-pages/man2/epoll_create1.2.html) | x64 291 · i386 329 · g64 20 · arm 357 | 2.6.27 | documented | [epoll_create1](./net-ipc/epoll_create.md) | —full |
| SC-epoll_ctl | [epoll_ctl](https://man7.org/linux/man-pages/man2/epoll_ctl.2.html) | x64 233 · i386 255 · g64 21 · arm 251 | 2.6 | documented | [epoll_ctl](./net-ipc/epoll_ctl.md) | —full |
| SC-epoll_ctl_old | epoll_ctl_old | x64 214 · i386 — · g64 — · arm — | — | researched | [epoll_ctl_old](./net-ipc/epoll_ctl_old.md) | —brief |
| SC-epoll_pwait | [epoll_pwait](https://man7.org/linux/man-pages/man2/epoll_pwait.2.html) | x64 281 · i386 319 · g64 22 · arm 346 | 2.6.19 | documented | [epoll_pwait](./net-ipc/epoll_wait.md) | —full |
| SC-epoll_pwait2 | [epoll_pwait2](https://man7.org/linux/man-pages/man2/epoll_pwait2.2.html) | x64 441 · i386 441 · g64 441 · arm 441 | 5.11 | documented | [epoll_pwait2](./net-ipc/epoll_wait.md) | —full |
| SC-epoll_wait | [epoll_wait](https://man7.org/linux/man-pages/man2/epoll_wait.2.html) | x64 232 · i386 256 · g64 — · arm 252 | 2.6 | documented | [epoll_wait](./net-ipc/epoll_wait.md) | —full |
| SC-epoll_wait_old | epoll_wait_old | x64 215 · i386 — · g64 — · arm — | — | researched | [epoll_wait_old](./net-ipc/epoll_wait_old.md) | —brief |
| SC-eventfd | [eventfd](https://man7.org/linux/man-pages/man2/eventfd.2.html) | x64 284 · i386 323 · g64 — · arm 351 | 2.6.22 | documented | [eventfd](./net-ipc/eventfd.md) | —full |
| SC-eventfd2 | [eventfd2](https://man7.org/linux/man-pages/man2/eventfd2.2.html) | x64 290 · i386 328 · g64 19 · arm 356 | 2.6.27 | documented | [eventfd2](./net-ipc/eventfd.md) | —full |
| SC-getdomainname | [getdomainname](https://man7.org/linux/man-pages/man2/getdomainname.2.html) | x64 — · i386 — · g64 — · arm — | 2.2 | researched | [getdomainname](./net-ipc/getdomainname.md) | —brief |
| SC-gethostname | [gethostname](https://man7.org/linux/man-pages/man2/gethostname.2.html) | x64 — · i386 — · g64 — · arm — | 2.0 | researched | [gethostname](./net-ipc/gethostname.md) | —brief |
| SC-getpeername | [getpeername](https://man7.org/linux/man-pages/man2/getpeername.2.html) | x64 52 · i386 368 · g64 205 · arm 287 | 2.0 | documented | [getpeername](./net-ipc/getpeername.md) | —full |
| SC-getsockname | [getsockname](https://man7.org/linux/man-pages/man2/getsockname.2.html) | x64 51 · i386 367 · g64 204 · arm 286 | 2.0 | documented | [getsockname](./net-ipc/getsockname.md) | —full |
| SC-getsockopt | [getsockopt](https://man7.org/linux/man-pages/man2/getsockopt.2.html) | x64 55 · i386 365 · g64 209 · arm 295 | 2.0 | documented | [getsockopt](./net-ipc/getsockopt.md) | —full |
| SC-io_cancel | [io_cancel](https://man7.org/linux/man-pages/man2/io_cancel.2.html) | x64 210 · i386 249 · g64 3 · arm 247 | 2.6 | documented | [io_cancel](./net-ipc/io_cancel.md) | —full |
| SC-io_destroy | [io_destroy](https://man7.org/linux/man-pages/man2/io_destroy.2.html) | x64 207 · i386 246 · g64 1 · arm 244 | 2.6 | documented | [io_destroy](./net-ipc/io_destroy.md) | —full |
| SC-io_getevents | [io_getevents](https://man7.org/linux/man-pages/man2/io_getevents.2.html) | x64 208 · i386 247 · g64 4 · arm 245 | 2.6 | documented | [io_getevents](./net-ipc/io_getevents.md) | —full |
| SC-io_pgetevents | io_pgetevents | x64 333 · i386 385 · g64 292 · arm 399 | 4.18 | documented | [io_pgetevents](./net-ipc/io_pgetevents.md) | —full |
| SC-io_pgetevents_time64 | io_pgetevents_time64 | x64 — · i386 416 · g64 — · arm 416 | — | researched | [io_pgetevents_time64](./net-ipc/io_pgetevents.md) | —time64 |
| SC-io_setup | [io_setup](https://man7.org/linux/man-pages/man2/io_setup.2.html) | x64 206 · i386 245 · g64 0 · arm 243 | 2.6 | documented | [io_setup](./net-ipc/io_setup.md) | —full |
| SC-io_submit | [io_submit](https://man7.org/linux/man-pages/man2/io_submit.2.html) | x64 209 · i386 248 · g64 2 · arm 246 | 2.6 | documented | [io_submit](./net-ipc/io_submit.md) | —full |
| SC-io_uring_enter | io_uring_enter | x64 426 · i386 426 · g64 426 · arm 426 | 5.1 | documented | [io_uring_enter](./net-ipc/io_uring_enter.md) | —full |
| SC-io_uring_register | io_uring_register | x64 427 · i386 427 · g64 427 · arm 427 | 5.1 | documented | [io_uring_register](./net-ipc/io_uring_register.md) | —full |
| SC-io_uring_setup | io_uring_setup | x64 425 · i386 425 · g64 425 · arm 425 | 5.1 | documented | [io_uring_setup](./net-ipc/io_uring_setup.md) | —full |
| SC-ipc | [ipc](https://man7.org/linux/man-pages/man2/ipc.2.html) | x64 — · i386 117 · g64 — · arm — | 1.0 | documented | [ipc](./net-ipc/ipc.md) | —full |
| SC-listen | [listen](https://man7.org/linux/man-pages/man2/listen.2.html) | x64 50 · i386 363 · g64 201 · arm 284 | 2.0 | documented | [listen](./net-ipc/listen.md) | —full |
| SC-mq_getsetattr | [mq_getsetattr](https://man7.org/linux/man-pages/man2/mq_getsetattr.2.html) | x64 245 · i386 282 · g64 185 · arm 279 | 2.6.6 | documented | [mq_getsetattr](./net-ipc/mq_getsetattr.md) | —full |
| SC-mq_notify | [mq_notify](https://man7.org/linux/man-pages/man2/mq_notify.2.html) | x64 244 · i386 281 · g64 184 · arm 278 | 2.6.6 | documented | [mq_notify](./net-ipc/mq_notify.md) | —full |
| SC-mq_open | [mq_open](https://man7.org/linux/man-pages/man2/mq_open.2.html) | x64 240 · i386 277 · g64 180 · arm 274 | 2.6.6 | documented | [mq_open](./net-ipc/mq_open.md) | —full |
| SC-mq_timedreceive | [mq_timedreceive](https://man7.org/linux/man-pages/man2/mq_timedreceive.2.html) | x64 243 · i386 280 · g64 183 · arm 277 | 2.6.6 | documented | [mq_timedreceive](./net-ipc/mq_timedreceive.md) | —full |
| SC-mq_timedreceive_time64 | mq_timedreceive_time64 | x64 — · i386 419 · g64 — · arm 419 | — | researched | [mq_timedreceive_time64](./net-ipc/mq_timedreceive.md) | —time64 |
| SC-mq_timedsend | [mq_timedsend](https://man7.org/linux/man-pages/man2/mq_timedsend.2.html) | x64 242 · i386 279 · g64 182 · arm 276 | 2.6.6 | documented | [mq_timedsend](./net-ipc/mq_timedsend.md) | —full |
| SC-mq_timedsend_time64 | mq_timedsend_time64 | x64 — · i386 418 · g64 — · arm 418 | — | researched | [mq_timedsend_time64](./net-ipc/mq_timedsend.md) | —time64 |
| SC-mq_unlink | [mq_unlink](https://man7.org/linux/man-pages/man2/mq_unlink.2.html) | x64 241 · i386 278 · g64 181 · arm 275 | 2.6.6 | documented | [mq_unlink](./net-ipc/mq_unlink.md) | —full |
| SC-msgctl | [msgctl](https://man7.org/linux/man-pages/man2/msgctl.2.html) | x64 71 · i386 402 · g64 187 · arm 304 | 2.0 | documented | [msgctl](./net-ipc/msgctl.md) | —full |
| SC-msgget | [msgget](https://man7.org/linux/man-pages/man2/msgget.2.html) | x64 68 · i386 399 · g64 186 · arm 303 | 2.0 | documented | [msgget](./net-ipc/msgget.md) | —full |
| SC-msgrcv | [msgrcv](https://man7.org/linux/man-pages/man2/msgrcv.2.html) | x64 70 · i386 401 · g64 188 · arm 302 | 2.0 | documented | [msgrcv](./net-ipc/msgop.md) | —full |
| SC-msgsnd | [msgsnd](https://man7.org/linux/man-pages/man2/msgsnd.2.html) | x64 69 · i386 400 · g64 189 · arm 301 | 2.0 | documented | [msgsnd](./net-ipc/msgop.md) | —full |
| SC-pipe | [pipe](https://man7.org/linux/man-pages/man2/pipe.2.html) | x64 22 · i386 42 · g64 — · arm 42 | 1.0 | documented | [pipe](./net-ipc/pipe.md) | —full |
| SC-pipe2 | [pipe2](https://man7.org/linux/man-pages/man2/pipe2.2.html) | x64 293 · i386 331 · g64 59 · arm 359 | 2.6.27 | documented | [pipe2](./net-ipc/pipe.md) | —full |
| SC-poll | [poll](https://man7.org/linux/man-pages/man2/poll.2.html) | x64 7 · i386 168 · g64 — · arm 168 | 2.0.36 | documented | [poll](./net-ipc/poll.md) | —full |
| SC-ppoll | [ppoll](https://man7.org/linux/man-pages/man2/ppoll.2.html) | x64 271 · i386 309 · g64 73 · arm 336 | 2.6.16 | documented | [ppoll](./net-ipc/poll.md) | —full |
| SC-ppoll_time64 | ppoll_time64 | x64 — · i386 414 · g64 — · arm 414 | — | researched | [ppoll_time64](./net-ipc/ppoll.md) | —time64 |
| SC-pselect6 | [pselect6](https://man7.org/linux/man-pages/man2/pselect6.2.html) | x64 270 · i386 308 · g64 72 · arm 335 | 2.6.16 | documented | [pselect6](./net-ipc/select.md) | —full |
| SC-pselect6_time64 | pselect6_time64 | x64 — · i386 413 · g64 — · arm 413 | — | researched | [pselect6_time64](./net-ipc/pselect6.md) | —time64 |
| SC-recv | [recv](https://man7.org/linux/man-pages/man2/recv.2.html) | x64 — · i386 — · g64 — · arm 291 | 2.0 | researched | [recv](./net-ipc/recv.md) | —brief |
| SC-recvfrom | [recvfrom](https://man7.org/linux/man-pages/man2/recvfrom.2.html) | x64 45 · i386 371 · g64 207 · arm 292 | 2.0 | documented | [recvfrom](./net-ipc/recv.md) | —full |
| SC-recvmmsg | [recvmmsg](https://man7.org/linux/man-pages/man2/recvmmsg.2.html) | x64 299 · i386 337 · g64 243 · arm 365 | 2.6.33 | documented | [recvmmsg](./net-ipc/recvmmsg.md) | —full |
| SC-recvmmsg_time64 | recvmmsg_time64 | x64 — · i386 417 · g64 — · arm 417 | — | researched | [recvmmsg_time64](./net-ipc/recvmmsg.md) | —time64 |
| SC-recvmsg | [recvmsg](https://man7.org/linux/man-pages/man2/recvmsg.2.html) | x64 47 · i386 372 · g64 212 · arm 297 | 2.0 | documented | [recvmsg](./net-ipc/recv.md) | —full |
| SC-select | [select](https://man7.org/linux/man-pages/man2/select.2.html) | x64 23 · i386 82 · g64 — · arm — | 1.0 | documented | [select](./net-ipc/select.md) | —full |
| SC-semctl | [semctl](https://man7.org/linux/man-pages/man2/semctl.2.html) | x64 66 · i386 394 · g64 191 · arm 300 | 2.0 | documented | [semctl](./net-ipc/semctl.md) | —full |
| SC-semget | [semget](https://man7.org/linux/man-pages/man2/semget.2.html) | x64 64 · i386 393 · g64 190 · arm 299 | 2.0 | documented | [semget](./net-ipc/semget.md) | —full |
| SC-semop | [semop](https://man7.org/linux/man-pages/man2/semop.2.html) | x64 65 · i386 — · g64 193 · arm 298 | 2.0 | documented | [semop](./net-ipc/semop.md) | —full |
| SC-semtimedop | [semtimedop](https://man7.org/linux/man-pages/man2/semtimedop.2.html) | x64 220 · i386 — · g64 192 · arm 312 | 2.6 | documented | [semtimedop](./net-ipc/semop.md) | —full |
| SC-semtimedop_time64 | semtimedop_time64 | x64 — · i386 420 · g64 — · arm 420 | — | researched | [semtimedop_time64](./net-ipc/semtimedop.md) | —time64 |
| SC-send | [send](https://man7.org/linux/man-pages/man2/send.2.html) | x64 — · i386 — · g64 — · arm 289 | 2.0 | researched | [send](./net-ipc/send.md) | —brief |
| SC-sendmmsg | [sendmmsg](https://man7.org/linux/man-pages/man2/sendmmsg.2.html) | x64 307 · i386 345 · g64 269 · arm 374 | 3.0 | documented | [sendmmsg](./net-ipc/sendmmsg.md) | —full |
| SC-sendmsg | [sendmsg](https://man7.org/linux/man-pages/man2/sendmsg.2.html) | x64 46 · i386 370 · g64 211 · arm 296 | 2.0 | documented | [sendmsg](./net-ipc/send.md) | —full |
| SC-sendto | [sendto](https://man7.org/linux/man-pages/man2/sendto.2.html) | x64 44 · i386 369 · g64 206 · arm 290 | 2.0 | documented | [sendto](./net-ipc/send.md) | —full |
| SC-setdomainname | [setdomainname](https://man7.org/linux/man-pages/man2/setdomainname.2.html) | x64 171 · i386 121 · g64 162 · arm 121 | 1.0 | researched | [setdomainname](./net-ipc/getdomainname.md) | —brief |
| SC-sethostname | [sethostname](https://man7.org/linux/man-pages/man2/sethostname.2.html) | x64 170 · i386 74 · g64 161 · arm 74 | 1.0 | researched | [sethostname](./net-ipc/gethostname.md) | —brief |
| SC-setsockopt | [setsockopt](https://man7.org/linux/man-pages/man2/setsockopt.2.html) | x64 54 · i386 366 · g64 208 · arm 294 | 2.0 | documented | [setsockopt](./net-ipc/getsockopt.md) | —full |
| SC-shmat | [shmat](https://man7.org/linux/man-pages/man2/shmat.2.html) | x64 30 · i386 397 · g64 196 · arm 305 | 2.0 | documented | [shmat](./net-ipc/shmop.md) | —full |
| SC-shmctl | [shmctl](https://man7.org/linux/man-pages/man2/shmctl.2.html) | x64 31 · i386 396 · g64 195 · arm 308 | 2.0 | documented | [shmctl](./net-ipc/shmctl.md) | —full |
| SC-shmdt | [shmdt](https://man7.org/linux/man-pages/man2/shmdt.2.html) | x64 67 · i386 398 · g64 197 · arm 306 | 2.0 | documented | [shmdt](./net-ipc/shmop.md) | —full |
| SC-shmget | [shmget](https://man7.org/linux/man-pages/man2/shmget.2.html) | x64 29 · i386 395 · g64 194 · arm 307 | 2.0 | documented | [shmget](./net-ipc/shmget.md) | —full |
| SC-shutdown | [shutdown](https://man7.org/linux/man-pages/man2/shutdown.2.html) | x64 48 · i386 373 · g64 210 · arm 293 | 2.0 | documented | [shutdown](./net-ipc/shutdown.md) | —full |
| SC-signalfd | [signalfd](https://man7.org/linux/man-pages/man2/signalfd.2.html) | x64 282 · i386 321 · g64 — · arm 349 | 2.6.22 | documented | [signalfd](./net-ipc/signalfd.md) | —full |
| SC-signalfd4 | [signalfd4](https://man7.org/linux/man-pages/man2/signalfd4.2.html) | x64 289 · i386 327 · g64 74 · arm 355 | 2.6.27 | documented | [signalfd4](./net-ipc/signalfd.md) | —full |
| SC-socket | [socket](https://man7.org/linux/man-pages/man2/socket.2.html) | x64 41 · i386 359 · g64 198 · arm 281 | 2.0 | documented | [socket](./net-ipc/socket.md) | —full |
| SC-socketcall | [socketcall](https://man7.org/linux/man-pages/man2/socketcall.2.html) | x64 — · i386 102 · g64 — · arm — | 1.0 | documented | [socketcall](./net-ipc/socketcall.md) | —full |
| SC-socketpair | [socketpair](https://man7.org/linux/man-pages/man2/socketpair.2.html) | x64 53 · i386 360 · g64 199 · arm 288 | 2.0 | documented | [socketpair](./net-ipc/socketpair.md) | —full |
| SC-timerfd_create | [timerfd_create](https://man7.org/linux/man-pages/man2/timerfd_create.2.html) | x64 283 · i386 322 · g64 85 · arm 350 | 2.6.25 | documented | [timerfd_create](./net-ipc/timerfd_create.md) | —full |
| SC-timerfd_gettime | [timerfd_gettime](https://man7.org/linux/man-pages/man2/timerfd_gettime.2.html) | x64 287 · i386 326 · g64 87 · arm 354 | 2.6.25 | documented | [timerfd_gettime](./net-ipc/timerfd_create.md) | —full |
| SC-timerfd_gettime64 | timerfd_gettime64 | x64 — · i386 410 · g64 — · arm 410 | — | researched | [timerfd_gettime64](./net-ipc/timerfd_gettime.md) | —time64 |
| SC-timerfd_settime | [timerfd_settime](https://man7.org/linux/man-pages/man2/timerfd_settime.2.html) | x64 286 · i386 325 · g64 86 · arm 353 | 2.6.25 | documented | [timerfd_settime](./net-ipc/timerfd_create.md) | —full |
| SC-timerfd_settime64 | timerfd_settime64 | x64 — · i386 411 · g64 — · arm 411 | — | researched | [timerfd_settime64](./net-ipc/timerfd_settime.md) | —time64 |

Total classified rows: 535. Unclassified: 0.

## Aliases, compat names and shared implementation paths

The rows above deliberately include historic and compat names so that coverage is not
inflated or silently dropped. Cross-cutting notes:

- **Name vs wrapper vs implementation.** `socketcall` (i386) multiplexes the socket
  family behind one number; x86_64/arm64 have direct numbers. `open` on arm64 is a libc
  wrapper over `openat`. `stat`/`lstat`/`fstat` exist on x86_64 as direct calls (removed
  in newer kernels for i386) but arm64 only has `newfstatat`. The kernel implementation
  name (`sys_read` → `__x64_sys_read` → `ksys_read`) is unrelated to the public name.
- **`*64` and `__NR3264_*` pairs** (`pread64`, `truncate64`, `statfs64`, …) exist
  because 32-bit architectures need explicit 64-bit offsets; 64-bit architectures reuse
  the base call (the asm-generic table expands `__NR3264_*` accordingly).
- **time32 vs time64** variants (`clock_gettime` vs `clock_gettime64`, `time32` abi
  rows in `scripts/syscall.tbl`) exist for 32-bit architectures facing the 2038 problem.
- **Removed and never-everywhere calls** (`_sysctl`, `uselib`, `create_module`,
  `query_module`, `vm86`, `modify_ldt`, old `sigaction`/`signal`, `epoll_ctl_old`,
  `nis_*` helpers) are kept in the ledger with their status instead of being dropped;
  several remain architecture-gated (x86 `vm86`, x86 `modify_ldt`).
- **Shared implementation paths** (documented in chapters, not extra rows):
  `wait4`/`waitpid` (libc wrapper), `dup2`/`dup3`, `pipe`/`pipe2`,
  `epoll_wait`/`epoll_pwait*`, `stat`/`newfstatat`, `getdents`/`getdents64`,
  `sigaction`/`rt_sigaction`, and the whole socket family on 32-bit via `socketcall`.

The `Since` column carries a small set of overrides verified during wave-1
documentation by kernel tag probes (noted in the chapter entries):
`cachestat` 6.5, `map_shadow_stack` 6.6, `mseal` 6.10,
`set_mempolicy_home_node` 5.17, `pivot_root` 2.3.41, `futex_wait`/
`futex_wake`/`futex_requeue` 6.14. Where the man-pages table and an
individual man page disagree (e.g. `mbind` 2.6.6 vs 2.6.7, `pkey_*` 4.8
vs 4.9), the chapters cite both readings.

## Unclassified names (triage queue)

The generator placed every inventoried name in a category; anything listed here was
added to the sources after the category map was written and must be triaged into a
chapter before its documentation starts.
