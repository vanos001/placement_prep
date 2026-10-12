# net-ipc syscalls - function index

This hub indexes the per-function pages of the `net-ipc` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable -- the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 / i386 / g64 / arm) | Since | Status |
|---|---|---|---|---|
| [select](select.md) | `_newselect` x64 -- | i386 142 | g64 -- | arm 142, `pselect6` x64 270 | i386 308 | g64 72 | arm 335, `pselect6_time64` x64 -- | i386 413 | g64 -- | arm 413, `select` x64 23 | i386 82 | g64 -- | arm -- | - | 2.0 | documented |
| [accept](accept.md) | `accept` x64 43 | i386 -- | g64 202 | arm 285, `accept4` x64 288 | i386 364 | g64 242 | arm 366 | - | 2.0 | documented |
| [bind](bind.md) | `bind` x64 49 | i386 361 | g64 200 | arm 282 | - | 2.0 | documented |
| [connect](connect.md) | `connect` x64 42 | i386 362 | g64 203 | arm 283 | - | 2.0 | documented |
| [epoll_create](epoll_create.md) | `epoll_create` x64 213 | i386 254 | g64 -- | arm 250, `epoll_create1` x64 291 | i386 329 | g64 20 | arm 357 | - | 2.6 | documented |
| [epoll_ctl](epoll_ctl.md) | `epoll_ctl` x64 233 | i386 255 | g64 21 | arm 251 | - | 2.6 | documented |
| [epoll_wait](epoll_wait.md) | `epoll_ctl_old` x64 214 | i386 -- | g64 -- | arm --, `epoll_pwait` x64 281 | i386 319 | g64 22 | arm 346, `epoll_pwait2` x64 441 | i386 441 | g64 441 | arm 441, `epoll_wait` x64 232 | i386 256 | g64 -- | arm 252, `epoll_wait_old` x64 215 | i386 -- | g64 -- | arm -- | - | -- | documented |
| [eventfd](eventfd.md) | `eventfd` x64 284 | i386 323 | g64 -- | arm 351, `eventfd2` x64 290 | i386 328 | g64 19 | arm 356 | - | 2.6.22 | documented |
| [getdomainname](getdomainname.md) | `getdomainname` x64 -- | i386 -- | g64 -- | arm --, `setdomainname` x64 171 | i386 121 | g64 162 | arm 121 | - | 2.2 | researched |
| [gethostname](gethostname.md) | `gethostname` x64 -- | i386 -- | g64 -- | arm --, `sethostname` x64 170 | i386 74 | g64 161 | arm 74 | - | 2.0 | researched |
| [getsockname](getsockname.md) | `getpeername` x64 52 | i386 368 | g64 205 | arm 287, `getsockname` x64 51 | i386 367 | g64 204 | arm 286 | - | 2.0 | documented |
| [setsockopt](setsockopt.md) | `getsockopt` x64 55 | i386 365 | g64 209 | arm 295, `setsockopt` x64 54 | i386 366 | g64 208 | arm 294 | - | 2.0 | documented |
| [io_setup](io_setup.md) | `io_cancel` x64 210 | i386 249 | g64 3 | arm 247, `io_destroy` x64 207 | i386 246 | g64 1 | arm 244, `io_getevents` x64 208 | i386 247 | g64 4 | arm 245, `io_pgetevents` x64 333 | i386 385 | g64 292 | arm 399, `io_pgetevents_time64` x64 -- | i386 416 | g64 -- | arm 416, `io_setup` x64 206 | i386 245 | g64 0 | arm 243, `io_submit` x64 209 | i386 248 | g64 2 | arm 246 | - | 2.6 | documented |
| [io_uring_setup](io_uring_setup.md) | `io_uring_enter` x64 426 | i386 426 | g64 426 | arm 426, `io_uring_register` x64 427 | i386 427 | g64 427 | arm 427, `io_uring_setup` x64 425 | i386 425 | g64 425 | arm 425 | - | 5.1 | documented |
| [ipc](ipc.md) | `ipc` x64 -- | i386 117 | g64 -- | arm -- | - | 1.0 | documented |
| [listen](listen.md) | `listen` x64 50 | i386 363 | g64 201 | arm 284 | - | 2.0 | documented |
| [mq_open](mq_open.md) | `mq_getsetattr` x64 245 | i386 282 | g64 185 | arm 279, `mq_notify` x64 244 | i386 281 | g64 184 | arm 278, `mq_open` x64 240 | i386 277 | g64 180 | arm 274, `mq_timedreceive` x64 243 | i386 280 | g64 183 | arm 277, `mq_timedreceive_time64` x64 -- | i386 419 | g64 -- | arm 419, `mq_timedsend` x64 242 | i386 279 | g64 182 | arm 276, `mq_timedsend_time64` x64 -- | i386 418 | g64 -- | arm 418, `mq_unlink` x64 241 | i386 278 | g64 181 | arm 275 | - | 2.6.6 | documented |
| [msgget](msgget.md) | `msgctl` x64 71 | i386 402 | g64 187 | arm 304, `msgget` x64 68 | i386 399 | g64 186 | arm 303, `msgrcv` x64 70 | i386 401 | g64 188 | arm 302, `msgsnd` x64 69 | i386 400 | g64 189 | arm 301 | - | 2.0 | documented |
| [pipe](pipe.md) | `pipe` x64 22 | i386 42 | g64 -- | arm 42, `pipe2` x64 293 | i386 331 | g64 59 | arm 359 | - | 1.0 | documented |
| [poll](poll.md) | `poll` x64 7 | i386 168 | g64 -- | arm 168, `ppoll` x64 271 | i386 309 | g64 73 | arm 336, `ppoll_time64` x64 -- | i386 414 | g64 -- | arm 414 | - | 2.0.36 | documented |
| [sendto](sendto.md) | `recv` x64 -- | i386 -- | g64 -- | arm 291, `recvfrom` x64 45 | i386 371 | g64 207 | arm 292, `send` x64 -- | i386 -- | g64 -- | arm 289, `sendto` x64 44 | i386 369 | g64 206 | arm 290 | - | 2.0 | documented |
| [sendmmsg](sendmmsg.md) | `recvmmsg` x64 299 | i386 337 | g64 243 | arm 365, `recvmmsg_time64` x64 -- | i386 417 | g64 -- | arm 417, `sendmmsg` x64 307 | i386 345 | g64 269 | arm 374 | - | 2.6.33 | documented |
| [sendmsg](sendmsg.md) | `recvmsg` x64 47 | i386 372 | g64 212 | arm 297, `sendmsg` x64 46 | i386 370 | g64 211 | arm 296 | - | 2.0 | documented |
| [semget](semget.md) | `semctl` x64 66 | i386 394 | g64 191 | arm 300, `semget` x64 64 | i386 393 | g64 190 | arm 299 | - | 2.0 | documented |
| [semop](semop.md) | `semop` x64 65 | i386 -- | g64 193 | arm 298, `semtimedop` x64 220 | i386 -- | g64 192 | arm 312, `semtimedop_time64` x64 -- | i386 420 | g64 -- | arm 420 | - | 2.0 | documented |
| [shmget](shmget.md) | `shmat` x64 30 | i386 397 | g64 196 | arm 305, `shmctl` x64 31 | i386 396 | g64 195 | arm 308, `shmdt` x64 67 | i386 398 | g64 197 | arm 306, `shmget` x64 29 | i386 395 | g64 194 | arm 307 | - | 2.0 | documented |
| [shutdown](shutdown.md) | `shutdown` x64 48 | i386 373 | g64 210 | arm 293 | - | 2.0 | documented |
| [signalfd](signalfd.md) | `signalfd` x64 282 | i386 321 | g64 -- | arm 349, `signalfd4` x64 289 | i386 327 | g64 74 | arm 355 | - | 2.6.22 | documented |
| [socket](socket.md) | `socket` x64 41 | i386 359 | g64 198 | arm 281, `socketpair` x64 53 | i386 360 | g64 199 | arm 288 | - | 2.0 | documented |
| [socketcall](socketcall.md) | `socketcall` x64 -- | i386 102 | g64 -- | arm -- | - | 1.0 | documented |
| [timerfd_create](timerfd_create.md) | `timerfd_create` x64 283 | i386 322 | g64 85 | arm 350, `timerfd_gettime` x64 287 | i386 326 | g64 87 | arm 354, `timerfd_settime` x64 286 | i386 325 | g64 86 | arm 353 | - | 2.6.25 | documented |
| [timerfd_settime](timerfd_settime.md) | `timerfd_gettime64` x64 -- | i386 410 | g64 -- | arm 410, `timerfd_settime64` x64 -- | i386 411 | g64 -- | arm 411 | - | -- | documented |
