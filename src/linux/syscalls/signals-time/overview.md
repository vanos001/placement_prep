# signal-time syscalls — function index

This hub indexes the per-function pages of the `signal-time` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable — the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 · i386 · g64 · arm) | Since | Status |
|---|---|---|---|---|
| [adjtimex](adjtimex.md) | `adjtimex`, `clock_adjtime` | x64 159 · i386 124 · g64 171 · arm 124 | 1.0 | documented |
| [alarm](alarm.md) | `alarm` | x64 37 · i386 27 · g64 — · arm — | 1.0 | documented |
| [clock_adjtime](clock_adjtime.md) | `clock_adjtime64` | x64 — · i386 405 · g64 — · arm 405 | — | researched |
| [clock_getres](clock_getres.md) | `clock_getres`, `clock_getres_time64`, `clock_gettime`, `clock_gettime64`, `clock_settime`, `clock_settime64` | x64 229 · i386 266 · g64 114 · arm 264 | 2.6 | documented |
| [clock_nanosleep](clock_nanosleep.md) | `clock_nanosleep`, `clock_nanosleep_time64` | x64 230 · i386 267 · g64 115 · arm 265 | 2.6 | documented |
| [getitimer](getitimer.md) | `getitimer`, `setitimer` | x64 36 · i386 105 · g64 102 · arm 105 | 1.0 | documented |
| [gettimeofday](gettimeofday.md) | `gettimeofday`, `settimeofday` | x64 96 · i386 78 · g64 169 · arm 78 | 1.0 | documented |
| [kill](kill.md) | `kill` | x64 62 · i386 37 · g64 129 · arm 37 | 1.0 | documented |
| [nanosleep](nanosleep.md) | `nanosleep` | x64 35 · i386 162 · g64 101 · arm 162 | 2.0 | documented |
| [pause](pause.md) | `pause` | x64 34 · i386 29 · g64 — · arm 29 | 1.0 | documented |
| [restart_syscall](restart_syscall.md) | `restart_syscall` | x64 219 · i386 0 · g64 128 · arm 0 | 2.6 | documented |
| [sigaction](sigaction.md) | `rt_sigaction`, `sigaction` | x64 13 · i386 174 · g64 134 · arm 174 | 2.2 | documented |
| [sigpending](sigpending.md) | `rt_sigpending`, `sigpending` | x64 127 · i386 176 · g64 136 · arm 176 | 2.2 | documented |
| [sigprocmask](sigprocmask.md) | `rt_sigprocmask`, `sigprocmask` | x64 14 · i386 175 · g64 135 · arm 175 | 2.2 | documented |
| [rt_sigqueueinfo](rt_sigqueueinfo.md) | `rt_sigqueueinfo`, `rt_tgsigqueueinfo` | x64 129 · i386 178 · g64 138 · arm 178 | 2.2 | documented |
| [sigreturn](sigreturn.md) | `rt_sigreturn`, `sigreturn` | x64 15 · i386 173 · g64 139 · arm 173 | 2.2 | documented |
| [sigsuspend](sigsuspend.md) | `rt_sigsuspend`, `sigsuspend` | x64 130 · i386 179 · g64 133 · arm 179 | 2.2 | researched |
| [sigtimedwait](sigtimedwait.md) | `rt_sigtimedwait` | x64 128 · i386 177 · g64 137 · arm 177 | 2.2 | documented |
| [rt_sigtimedwait_time64](rt_sigtimedwait_time64.md) | `rt_sigtimedwait_time64` | x64 — · i386 421 · g64 — · arm 421 | — | researched |
| [sgetmask](sgetmask.md) | `sgetmask`, `ssetmask` | x64 — · i386 68 · g64 — · arm — | 1.0 | researched |
| [sigaltstack](sigaltstack.md) | `sigaltstack` | x64 131 · i386 186 · g64 132 · arm 186 | 2.2 | documented |
| [signal](signal.md) | `signal` | x64 — · i386 48 · g64 — · arm — | 1.0 | researched |
| [stime](stime.md) | `stime` | x64 — · i386 25 · g64 — · arm — | 1.0 | source-limited |
| [tkill](tkill.md) | `tgkill`, `tkill` | x64 234 · i386 270 · g64 131 · arm 268 | 2.6 | documented |
| [time](time.md) | `time` | x64 201 · i386 13 · g64 — · arm — | 1.0 | documented |
| [timer_create](timer_create.md) | `timer_create` | x64 222 · i386 259 · g64 107 · arm 257 | 2.6 | documented |
| [timer_delete](timer_delete.md) | `timer_delete` | x64 226 · i386 263 · g64 111 · arm 261 | 2.6 | documented |
| [timer_getoverrun](timer_getoverrun.md) | `timer_getoverrun` | x64 225 · i386 262 · g64 109 · arm 260 | 2.6 | documented |
| [timer_settime](timer_settime.md) | `timer_gettime`, `timer_gettime64`, `timer_settime`, `timer_settime64` | x64 224 · i386 261 · g64 108 · arm 259 | 2.6 | documented |
| [times](times.md) | `times` | x64 100 · i386 43 · g64 153 · arm 43 | 1.0 | documented |
