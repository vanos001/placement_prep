# signal-time syscalls - function index

This hub indexes the per-function pages of the `signal-time` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable -- the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 / i386 / g64 / arm) | Since | Status |
|---|---|---|---|---|
| [clock_adjtime](clock_adjtime.md) | `adjtimex` x64 159 | i386 124 | g64 171 | arm 124, `clock_adjtime` x64 305 | i386 343 | g64 266 | arm 372, `clock_adjtime64` x64 -- | i386 405 | g64 -- | arm 405 | - | 1.0 | documented |
| [alarm](alarm.md) | `alarm` x64 37 | i386 27 | g64 -- | arm -- | - | 1.0 | documented |
| [clock_getres](clock_getres.md) | `clock_getres` x64 229 | i386 266 | g64 114 | arm 264, `clock_getres_time64` x64 -- | i386 406 | g64 -- | arm 406, `clock_gettime` x64 228 | i386 265 | g64 113 | arm 263, `clock_gettime64` x64 -- | i386 403 | g64 -- | arm 403, `clock_settime` x64 227 | i386 264 | g64 112 | arm 262, `clock_settime64` x64 -- | i386 404 | g64 -- | arm 404 | - | 2.6 | documented |
| [clock_nanosleep](clock_nanosleep.md) | `clock_nanosleep` x64 230 | i386 267 | g64 115 | arm 265, `clock_nanosleep_time64` x64 -- | i386 407 | g64 -- | arm 407, `nanosleep` x64 35 | i386 162 | g64 101 | arm 162 | - | 2.6 | documented |
| [setitimer](setitimer.md) | `getitimer` x64 36 | i386 105 | g64 102 | arm 105, `setitimer` x64 38 | i386 104 | g64 103 | arm 104 | - | 1.0 | documented |
| [gettimeofday](gettimeofday.md) | `gettimeofday` x64 96 | i386 78 | g64 169 | arm 78, `settimeofday` x64 164 | i386 79 | g64 170 | arm 79 | - | 1.0 | documented |
| [kill](kill.md) | `kill` x64 62 | i386 37 | g64 129 | arm 37 | - | 1.0 | documented |
| [pause](pause.md) | `pause` x64 34 | i386 29 | g64 -- | arm 29 | - | 1.0 | documented |
| [restart_syscall](restart_syscall.md) | `restart_syscall` x64 219 | i386 0 | g64 128 | arm 0 | - | 2.6 | documented |
| [rt_sigaction](rt_sigaction.md) | `rt_sigaction` x64 13 | i386 174 | g64 134 | arm 174, `sigaction` x64 -- | i386 67 | g64 -- | arm 67, `signal` x64 -- | i386 48 | g64 -- | arm -- | - | 2.2 | documented |
| [sigpending](sigpending.md) | `rt_sigpending` x64 127 | i386 176 | g64 136 | arm 176, `sigpending` x64 -- | i386 73 | g64 -- | arm 73 | - | 2.2 | documented |
| [rt_sigprocmask](rt_sigprocmask.md) | `rt_sigprocmask` x64 14 | i386 175 | g64 135 | arm 175, `sigprocmask` x64 -- | i386 126 | g64 -- | arm 126 | - | 2.2 | documented |
| [rt_sigqueueinfo](rt_sigqueueinfo.md) | `rt_sigqueueinfo` x64 129 | i386 178 | g64 138 | arm 178, `rt_tgsigqueueinfo` x64 297 | i386 335 | g64 240 | arm 363 | - | 2.2 | documented |
| [sigreturn](sigreturn.md) | `rt_sigreturn` x64 15 | i386 173 | g64 139 | arm 173, `sigreturn` x64 -- | i386 119 | g64 -- | arm 119 | - | 2.2 | documented |
| [rt_sigsuspend](rt_sigsuspend.md) | `rt_sigsuspend` x64 130 | i386 179 | g64 133 | arm 179, `sigsuspend` x64 -- | i386 72 | g64 -- | arm 72 | - | 2.2 | researched |
| [sigtimedwait](sigtimedwait.md) | `rt_sigtimedwait` x64 128 | i386 177 | g64 137 | arm 177 | - | 2.2 | documented |
| [rt_sigtimedwait_time64](rt_sigtimedwait_time64.md) | `rt_sigtimedwait_time64` x64 -- | i386 421 | g64 -- | arm 421 | - | -- | researched |
| [sgetmask](sgetmask.md) | `sgetmask` x64 -- | i386 68 | g64 -- | arm --, `ssetmask` x64 -- | i386 69 | g64 -- | arm -- | - | 1.0 | researched |
| [sigaltstack](sigaltstack.md) | `sigaltstack` x64 131 | i386 186 | g64 132 | arm 186 | - | 2.2 | documented |
| [stime](stime.md) | `stime` x64 -- | i386 25 | g64 -- | arm -- | - | 1.0 | source-limited |
| [tkill](tkill.md) | `tgkill` x64 234 | i386 270 | g64 131 | arm 268, `tkill` x64 200 | i386 238 | g64 130 | arm 238 | - | 2.6 | documented |
| [time](time.md) | `time` x64 201 | i386 13 | g64 -- | arm -- | - | 1.0 | documented |
| [timer_create](timer_create.md) | `timer_create` x64 222 | i386 259 | g64 107 | arm 257, `timer_delete` x64 226 | i386 263 | g64 111 | arm 261, `timer_getoverrun` x64 225 | i386 262 | g64 109 | arm 260, `timer_gettime` x64 224 | i386 261 | g64 108 | arm 259, `timer_gettime64` x64 -- | i386 408 | g64 -- | arm 408, `timer_settime` x64 223 | i386 260 | g64 110 | arm 258, `timer_settime64` x64 -- | i386 409 | g64 -- | arm 409 | - | 2.6 | documented |
| [times](times.md) | `times` x64 100 | i386 43 | g64 153 | arm 43 | - | 1.0 | documented |
