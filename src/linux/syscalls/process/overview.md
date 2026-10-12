# process syscalls - function index

This hub indexes the per-function pages of the `process` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable -- the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 / i386 / g64 / arm) | Since | Status |
|---|---|---|---|---|
| [acct](acct.md) | `acct` x64 163 | i386 51 | g64 89 | arm 51 | - | 1.0 | researched |
| [arch_prctl](arch_prctl.md) | `arch_prctl` x64 158 | i386 384 | g64 -- | arm -- | - | 2.6 | researched |
| [capget](capget.md) | `capget` x64 125 | i386 184 | g64 90 | arm 184, `capset` x64 126 | i386 185 | g64 91 | arm 185 | - | 2.2 | documented |
| [chown](chown.md) | `chown32` x64 -- | i386 212 | g64 -- | arm 212, `fchown32` x64 -- | i386 207 | g64 -- | arm 207, `lchown32` x64 -- | i386 198 | g64 -- | arm 198 | - | 2.4 | not-started |
| [clone](clone.md) | `clone` x64 56 | i386 120 | g64 220 | arm 120, `clone2` x64 -- | i386 -- | g64 -- | arm --, `clone3` x64 435 | i386 435 | g64 435 | arm 435 | - | 1.0 | documented |
| [execv](execv.md) | `execv` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | not-started |
| [execve](execve.md) | `execve` x64 59 | i386 11 | g64 221 | arm 11 | - | 1.0 | documented |
| [execveat](execveat.md) | `execveat` x64 322 | i386 358 | g64 281 | arm 387 | - | 3.19 | documented |
| [_exit](_exit.md) | `exit` x64 60 | i386 1 | g64 93 | arm 1, `exit_group` x64 231 | i386 252 | g64 94 | arm 248 | - | 1.0 | documented |
| [fork](fork.md) | `fork` x64 57 | i386 2 | g64 -- | arm 2 | - | 1.0 | documented |
| [futex](futex.md) | `futex` x64 202 | i386 240 | g64 98 | arm 240, `futex_requeue` x64 456 | i386 456 | g64 456 | arm 456, `futex_time64` x64 -- | i386 422 | g64 -- | arm 422, `futex_wait` x64 455 | i386 455 | g64 455 | arm 455, `futex_waitv` x64 449 | i386 449 | g64 449 | arm 449, `futex_wake` x64 454 | i386 454 | g64 454 | arm 454 | - | 2.6 | documented |
| [get_robust_list](get_robust_list.md) | `get_robust_list` x64 274 | i386 312 | g64 100 | arm 339, `set_robust_list` x64 273 | i386 311 | g64 99 | arm 338 | - | 2.6.17 | researched |
| [getgid](getgid.md) | `getegid` x64 108 | i386 50 | g64 177 | arm 50, `getgid` x64 104 | i386 47 | g64 176 | arm 47, `getgid32` x64 -- | i386 200 | g64 -- | arm 200 | - | 1.0 | documented |
| [getegid](getegid.md) | `getegid32` x64 -- | i386 202 | g64 -- | arm 202 | - | 2.4 | documented |
| [getuid](getuid.md) | `geteuid` x64 107 | i386 49 | g64 175 | arm 49, `getuid` x64 102 | i386 24 | g64 174 | arm 24, `getuid32` x64 -- | i386 199 | g64 -- | arm 199 | - | 1.0 | documented |
| [geteuid](geteuid.md) | `geteuid32` x64 -- | i386 201 | g64 -- | arm 201 | - | 2.4 | documented |
| [getgroups](getgroups.md) | `getgroups` x64 115 | i386 80 | g64 158 | arm 80, `getgroups32` x64 -- | i386 205 | g64 -- | arm 205, `setgroups` x64 116 | i386 81 | g64 159 | arm 81 | - | 1.0 | documented |
| [setpgid](setpgid.md) | `getpgid` x64 121 | i386 132 | g64 155 | arm 132, `getpgrp` x64 111 | i386 65 | g64 -- | arm 65, `setpgid` x64 109 | i386 57 | g64 154 | arm 57, `setpgrp` x64 -- | i386 -- | g64 -- | arm -- | - | 1.0 | documented |
| [getpid](getpid.md) | `getpid` x64 39 | i386 20 | g64 172 | arm 20, `getppid` x64 110 | i386 64 | g64 173 | arm 64, `gettid` x64 186 | i386 224 | g64 178 | arm 224 | - | 1.0 | researched |
| [getresuid](getresuid.md) | `getresgid` x64 120 | i386 171 | g64 150 | arm 171, `getresuid` x64 118 | i386 165 | g64 148 | arm 165, `getresuid32` x64 -- | i386 209 | g64 -- | arm 209 | - | 2.2 | documented |
| [getresgid](getresgid.md) | `getresgid32` x64 -- | i386 211 | g64 -- | arm 211 | - | 2.4 | documented |
| [getrlimit](getrlimit.md) | `getrlimit` x64 97 | i386 76 | g64 -- | arm --, `prlimit64` x64 302 | i386 340 | g64 261 | arm 369, `setrlimit` x64 160 | i386 75 | g64 -- | arm 75, `ugetrlimit` x64 -- | i386 191 | g64 -- | arm 191 | - | 1.0 | not-started |
| [getrusage](getrusage.md) | `getrusage` x64 98 | i386 77 | g64 165 | arm 77 | - | 1.0 | not-started |
| [getsid](getsid.md) | `getsid` x64 124 | i386 147 | g64 156 | arm 147 | - | 2.0 | documented |
| [personality](personality.md) | `personality` x64 135 | i386 136 | g64 92 | arm 136 | - | 1.2 | not-started |
| [pidfd_getfd](pidfd_getfd.md) | `pidfd_getfd` x64 438 | i386 438 | g64 438 | arm 438 | - | 5.6 | documented |
| [pidfd_open](pidfd_open.md) | `pidfd_open` x64 434 | i386 434 | g64 434 | arm 434 | - | 5.3 | documented |
| [pidfd_send_signal](pidfd_send_signal.md) | `pidfd_send_signal` x64 424 | i386 424 | g64 424 | arm 424 | - | 5.1 | documented |
| [prctl](prctl.md) | `prctl` x64 157 | i386 172 | g64 167 | arm 172 | - | 2.2 | documented |
| [process_madvise](process_madvise.md) | `process_madvise` x64 440 | i386 440 | g64 440 | arm 440 | - | 5.10 | documented |
| [process_mrelease](process_mrelease.md) | `process_mrelease` x64 448 | i386 448 | g64 448 | arm 448 | - | -- | source-limited |
| [ptrace](ptrace.md) | `ptrace` x64 101 | i386 26 | g64 117 | arm 26 | - | 1.0 | researched |
| [rseq](rseq.md) | `rseq` x64 334 | i386 386 | g64 293 | arm 398 | - | 4.18 | source-limited |
| [rseq_slice_yield](rseq_slice_yield.md) | `rseq_slice_yield` x64 471 | i386 471 | g64 471 | arm 471 | - | -- | source-limited |
| [set_tid_address](set_tid_address.md) | `set_tid_address` x64 218 | i386 258 | g64 96 | arm 256 | - | 2.6 | documented |
| [setfsgid](setfsgid.md) | `setfsgid` x64 123 | i386 139 | g64 152 | arm 139, `setfsgid32` x64 -- | i386 216 | g64 -- | arm 216 | - | 1.2 | documented |
| [setfsuid](setfsuid.md) | `setfsuid` x64 122 | i386 138 | g64 151 | arm 138, `setfsuid32` x64 -- | i386 215 | g64 -- | arm 215 | - | 1.2 | documented |
| [setgid](setgid.md) | `setgid` x64 106 | i386 46 | g64 144 | arm 46, `setgid32` x64 -- | i386 214 | g64 -- | arm 214 | - | 1.0 | documented |
| [setgroups](setgroups.md) | `setgroups32` x64 -- | i386 206 | g64 -- | arm 206 | - | 2.4 | documented |
| [setreuid](setreuid.md) | `setregid` x64 114 | i386 71 | g64 143 | arm 71, `setreuid` x64 113 | i386 70 | g64 145 | arm 70, `setreuid32` x64 -- | i386 203 | g64 -- | arm 203 | - | 1.0 | documented |
| [setregid](setregid.md) | `setregid32` x64 -- | i386 204 | g64 -- | arm 204 | - | 2.4 | documented |
| [setresuid](setresuid.md) | `setresgid` x64 119 | i386 170 | g64 149 | arm 170, `setresuid` x64 117 | i386 164 | g64 147 | arm 164, `setresuid32` x64 -- | i386 208 | g64 -- | arm 208 | - | 2.2 | documented |
| [setresgid](setresgid.md) | `setresgid32` x64 -- | i386 210 | g64 -- | arm 210 | - | 2.4 | documented |
| [setsid](setsid.md) | `setsid` x64 112 | i386 66 | g64 157 | arm 66 | - | 1.0 | documented |
| [setuid](setuid.md) | `setuid` x64 105 | i386 23 | g64 146 | arm 23, `setuid32` x64 -- | i386 213 | g64 -- | arm 213 | - | 1.0 | documented |
| [uname](uname.md) | `uname` x64 63 | i386 122 | g64 160 | arm 122 | - | 1.0 | documented |
| [vfork](vfork.md) | `vfork` x64 58 | i386 190 | g64 -- | arm 190 | - | 2.2 | documented |
| [wait4](wait4.md) | `wait4` x64 61 | i386 114 | g64 260 | arm 114, `waitpid` x64 -- | i386 7 | g64 -- | arm -- | - | 1.0 | documented |
| [wait](wait.md) | `waitid` x64 247 | i386 284 | g64 95 | arm 280 | - | 2.6.10 | documented |
