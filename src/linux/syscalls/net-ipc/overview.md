# net-ipc syscalls — function index

This hub indexes the per-function pages of the `net-ipc` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable — the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 · i386 · g64 · arm) | Since | Status |
|---|---|---|---|---|
| [select](select.md) | `_newselect`, `pselect6`, `select` | x64 — · i386 142 · g64 — · arm 142 | 2.0 | researched |
| [accept](accept.md) | `accept`, `accept4` | x64 43 · i386 — · g64 202 · arm 285 | 2.0 | documented |
| [bind](bind.md) | `bind` | x64 49 · i386 361 · g64 200 · arm 282 | 2.0 | documented |
| [connect](connect.md) | `connect` | x64 42 · i386 362 · g64 203 · arm 283 | 2.0 | documented |
| [epoll_create](epoll_create.md) | `epoll_create`, `epoll_create1` | x64 213 · i386 254 · g64 — · arm 250 | 2.6 | documented |
| [epoll_ctl](epoll_ctl.md) | `epoll_ctl` | x64 233 · i386 255 · g64 21 · arm 251 | 2.6 | documented |
| [epoll_ctl_old](epoll_ctl_old.md) | `epoll_ctl_old` | x64 214 · i386 — · g64 — · arm — | — | researched |
| [epoll_wait](epoll_wait.md) | `epoll_pwait`, `epoll_pwait2`, `epoll_wait` | x64 281 · i386 319 · g64 22 · arm 346 | 2.6.19 | documented |
| [epoll_wait_old](epoll_wait_old.md) | `epoll_wait_old` | x64 215 · i386 — · g64 — · arm — | — | researched |
| [eventfd](eventfd.md) | `eventfd`, `eventfd2` | x64 284 · i386 323 · g64 — · arm 351 | 2.6.22 | documented |
| [getdomainname](getdomainname.md) | `getdomainname`, `setdomainname` | x64 — · i386 — · g64 — · arm — | 2.2 | researched |
| [gethostname](gethostname.md) | `gethostname`, `sethostname` | x64 — · i386 — · g64 — · arm — | 2.0 | researched |
| [getpeername](getpeername.md) | `getpeername` | x64 52 · i386 368 · g64 205 · arm 287 | 2.0 | documented |
| [getsockname](getsockname.md) | `getsockname` | x64 51 · i386 367 · g64 204 · arm 286 | 2.0 | documented |
| [getsockopt](getsockopt.md) | `getsockopt`, `setsockopt` | x64 55 · i386 365 · g64 209 · arm 295 | 2.0 | documented |
| [io_cancel](io_cancel.md) | `io_cancel` | x64 210 · i386 249 · g64 3 · arm 247 | 2.6 | documented |
| [io_destroy](io_destroy.md) | `io_destroy` | x64 207 · i386 246 · g64 1 · arm 244 | 2.6 | documented |
| [io_getevents](io_getevents.md) | `io_getevents` | x64 208 · i386 247 · g64 4 · arm 245 | 2.6 | documented |
| [io_pgetevents](io_pgetevents.md) | `io_pgetevents`, `io_pgetevents_time64` | x64 333 · i386 385 · g64 292 · arm 399 | 4.18 | documented |
| [io_setup](io_setup.md) | `io_setup` | x64 206 · i386 245 · g64 0 · arm 243 | 2.6 | documented |
| [io_submit](io_submit.md) | `io_submit` | x64 209 · i386 248 · g64 2 · arm 246 | 2.6 | documented |
| [io_uring_enter](io_uring_enter.md) | `io_uring_enter` | x64 426 · i386 426 · g64 426 · arm 426 | 5.1 | documented |
| [io_uring_register](io_uring_register.md) | `io_uring_register` | x64 427 · i386 427 · g64 427 · arm 427 | 5.1 | documented |
| [io_uring_setup](io_uring_setup.md) | `io_uring_setup` | x64 425 · i386 425 · g64 425 · arm 425 | 5.1 | documented |
| [ipc](ipc.md) | `ipc` | x64 — · i386 117 · g64 — · arm — | 1.0 | documented |
| [listen](listen.md) | `listen` | x64 50 · i386 363 · g64 201 · arm 284 | 2.0 | documented |
| [mq_getsetattr](mq_getsetattr.md) | `mq_getsetattr` | x64 245 · i386 282 · g64 185 · arm 279 | 2.6.6 | documented |
| [mq_notify](mq_notify.md) | `mq_notify` | x64 244 · i386 281 · g64 184 · arm 278 | 2.6.6 | documented |
| [mq_open](mq_open.md) | `mq_open` | x64 240 · i386 277 · g64 180 · arm 274 | 2.6.6 | documented |
| [mq_timedreceive](mq_timedreceive.md) | `mq_timedreceive`, `mq_timedreceive_time64` | x64 243 · i386 280 · g64 183 · arm 277 | 2.6.6 | documented |
| [mq_timedsend](mq_timedsend.md) | `mq_timedsend`, `mq_timedsend_time64` | x64 242 · i386 279 · g64 182 · arm 276 | 2.6.6 | documented |
| [mq_unlink](mq_unlink.md) | `mq_unlink` | x64 241 · i386 278 · g64 181 · arm 275 | 2.6.6 | documented |
| [msgctl](msgctl.md) | `msgctl` | x64 71 · i386 402 · g64 187 · arm 304 | 2.0 | documented |
| [msgget](msgget.md) | `msgget` | x64 68 · i386 399 · g64 186 · arm 303 | 2.0 | documented |
| [msgop](msgop.md) | `msgrcv`, `msgsnd` | x64 70 · i386 401 · g64 188 · arm 302 | 2.0 | documented |
| [pipe](pipe.md) | `pipe`, `pipe2` | x64 22 · i386 42 · g64 — · arm 42 | 1.0 | documented |
| [poll](poll.md) | `poll`, `ppoll` | x64 7 · i386 168 · g64 — · arm 168 | 2.0.36 | documented |
| [ppoll](ppoll.md) | `ppoll_time64` | x64 — · i386 414 · g64 — · arm 414 | — | researched |
| [pselect6](pselect6.md) | `pselect6_time64` | x64 — · i386 413 · g64 — · arm 413 | — | researched |
| [recv](recv.md) | `recv`, `recvfrom`, `recvmsg` | x64 — · i386 — · g64 — · arm 291 | 2.0 | researched |
| [recvmmsg](recvmmsg.md) | `recvmmsg`, `recvmmsg_time64` | x64 299 · i386 337 · g64 243 · arm 365 | 2.6.33 | documented |
| [semctl](semctl.md) | `semctl` | x64 66 · i386 394 · g64 191 · arm 300 | 2.0 | documented |
| [semget](semget.md) | `semget` | x64 64 · i386 393 · g64 190 · arm 299 | 2.0 | documented |
| [semop](semop.md) | `semop`, `semtimedop` | x64 65 · i386 — · g64 193 · arm 298 | 2.0 | documented |
| [semtimedop](semtimedop.md) | `semtimedop_time64` | x64 — · i386 420 · g64 — · arm 420 | — | researched |
| [send](send.md) | `send`, `sendmsg`, `sendto` | x64 — · i386 — · g64 — · arm 289 | 2.0 | researched |
| [sendmmsg](sendmmsg.md) | `sendmmsg` | x64 307 · i386 345 · g64 269 · arm 374 | 3.0 | documented |
| [shmop](shmop.md) | `shmat`, `shmdt` | x64 30 · i386 397 · g64 196 · arm 305 | 2.0 | documented |
| [shmctl](shmctl.md) | `shmctl` | x64 31 · i386 396 · g64 195 · arm 308 | 2.0 | documented |
| [shmget](shmget.md) | `shmget` | x64 29 · i386 395 · g64 194 · arm 307 | 2.0 | documented |
| [shutdown](shutdown.md) | `shutdown` | x64 48 · i386 373 · g64 210 · arm 293 | 2.0 | documented |
| [signalfd](signalfd.md) | `signalfd`, `signalfd4` | x64 282 · i386 321 · g64 — · arm 349 | 2.6.22 | documented |
| [socket](socket.md) | `socket` | x64 41 · i386 359 · g64 198 · arm 281 | 2.0 | documented |
| [socketcall](socketcall.md) | `socketcall` | x64 — · i386 102 · g64 — · arm — | 1.0 | documented |
| [socketpair](socketpair.md) | `socketpair` | x64 53 · i386 360 · g64 199 · arm 288 | 2.0 | documented |
| [timerfd_create](timerfd_create.md) | `timerfd_create`, `timerfd_gettime`, `timerfd_settime` | x64 283 · i386 322 · g64 85 · arm 350 | 2.6.25 | documented |
| [timerfd_gettime](timerfd_gettime.md) | `timerfd_gettime64` | x64 — · i386 410 · g64 — · arm 410 | — | researched |
| [timerfd_settime](timerfd_settime.md) | `timerfd_settime64` | x64 — · i386 411 · g64 — · arm 411 | — | researched |
