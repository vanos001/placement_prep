# musl API Coverage Ledger

## Overview

musl does not maintain a separate "documented API" list: every prototype in
its public headers is exported from `libc.so` (and its math/dynamic-loader
companions), and functions not in headers are implementation detail. The
inventory below is therefore parsed from the **musl 1.2.5 public headers**
(`include/` and its subsystem subdirectories), which is the authoritative
exported surface, grouped by the header that declares each function.

The delta sections compare this set with the glibc 2.41 set recorded in the
[glibc ledger](./ledger-glibc.md) (documented functions ∪ exported symbols).
Differences at the *set level* are start points, not verdicts: a name can be
present in both with different semantics, and glibc-only names often have a
musl equivalent under another name or in a non-libc library. The
[musl catalog page](./musl-catalog.md) discusses the important deltas.

**Status vocabulary** (defined in the [encyclopedia overview](../interface-encyclopedia.md)):
`not-started` → inventoried only · `researched` → sources read ·
`documented` → full entry · `source-limited` → fewer sources than standard.

## Ledger (by declaring header)

### `acct.h` (1)

| `acct` |
|---|

### `aio.h` (8)

| `aio_cancel` | `aio_error` | `aio_fsync` | `aio_read` | `aio_return` | `aio_suspend` | `aio_write` | `lio_listio` |
|---|---|---|---|---|---|---|---|

### `alloca.h` (1)

| `alloca` |
|---|

### `auxv.h` (1)

| `getauxval` |
|---|

### `cachectl.h` (3)

| `_flush_cache` | `cachectl` | `cacheflush` |
|---|---|---|

### `complex.h` (66)

| `cabs` | `cabsf` | `cabsl` | `cacos` | `cacosf` | `cacosh` | `cacoshf` | `cacoshl` |
|---|---|---|---|---|---|---|---|
| `cacosl` | `carg` | `cargf` | `cargl` | `casin` | `casinf` | `casinh` | `casinhf` |
|---|---|---|---|---|---|---|---|
| `casinhl` | `casinl` | `catan` | `catanf` | `catanh` | `catanhf` | `catanhl` | `catanl` |
|---|---|---|---|---|---|---|---|
| `ccos` | `ccosf` | `ccosh` | `ccoshf` | `ccoshl` | `ccosl` | `cexp` | `cexpf` |
|---|---|---|---|---|---|---|---|
| `cexpl` | `cimag` | `cimagf` | `cimagl` | `clog` | `clogf` | `clogl` | `conj` |
|---|---|---|---|---|---|---|---|
| `conjf` | `conjl` | `cpow` | `cpowf` | `cpowl` | `cproj` | `cprojf` | `cprojl` |
|---|---|---|---|---|---|---|---|
| `creal` | `crealf` | `creall` | `csin` | `csinf` | `csinh` | `csinhf` | `csinhl` |
|---|---|---|---|---|---|---|---|
| `csinl` | `csqrt` | `csqrtf` | `csqrtl` | `ctan` | `ctanf` | `ctanh` | `ctanhf` |
|---|---|---|---|---|---|---|---|
| `ctanhl` | `ctanl` |
|---|---|

### `crypt.h` (2)

| `crypt` | `crypt_r` |
|---|---|

### `ctype.h` (29)

| `isalnum` | `isalpha` | `isalpha_l` | `isascii` | `isblank` | `isblank_l` | `iscntrl` | `iscntrl_l` |
|---|---|---|---|---|---|---|---|
| `isdigit` | `isdigit_l` | `isgraph` | `isgraph_l` | `islower` | `islower_l` | `isprint` | `isprint_l` |
|---|---|---|---|---|---|---|---|
| `ispunct` | `ispunct_l` | `isspace` | `isspace_l` | `isupper` | `isupper_l` | `isxdigit` | `isxdigit_l` |
|---|---|---|---|---|---|---|---|
| `toascii` | `tolower` | `tolower_l` | `toupper` | `toupper_l` |
|---|---|---|---|---|

### `dirent.h` (13)

| `alphasort` | `closedir` | `dirfd` | `fdopendir` | `getdents` | `opendir` | `readdir` | `readdir_r` |
|---|---|---|---|---|---|---|---|
| `rewinddir` | `scandir` | `seekdir` | `telldir` | `versionsort` |
|---|---|---|---|---|

### `dlfcn.h` (6)

| `dladdr` | `dlclose` | `dlerror` | `dlinfo` | `dlopen` | `dlsym` |
|---|---|---|---|---|---|

### `epoll.h` (5)

| `epoll_create` | `epoll_create1` | `epoll_ctl` | `epoll_pwait` | `epoll_wait` |
|---|---|---|---|---|

### `err.h` (8)

| `err` | `errx` | `verr` | `verrx` | `vwarn` | `vwarnx` | `warn` | `warnx` |
|---|---|---|---|---|---|---|---|

### `ether.h` (7)

| `ether_aton` | `ether_aton_r` | `ether_hostton` | `ether_line` | `ether_ntoa` | `ether_ntoa_r` | `ether_ntohost` |
|---|---|---|---|---|---|---|

### `eventfd.h` (3)

| `eventfd` | `eventfd_read` | `eventfd_write` |
|---|---|---|

### `fanotify.h` (2)

| `fanotify_init` | `fanotify_mark` |
|---|---|

### `fcntl.h` (15)

| `creat` | `fallocate` | `fcntl` | `lockf` | `name_to_handle_at` | `open` | `open_by_handle_at` | `openat` |
|---|---|---|---|---|---|---|---|
| `posix_fadvise` | `posix_fallocate` | `readahead` | `splice` | `sync_file_range` | `tee` | `vmsplice` |
|---|---|---|---|---|---|---|

### `fenv.h` (11)

| `feclearexcept` | `fegetenv` | `fegetexceptflag` | `fegetround` | `feholdexcept` | `feraiseexcept` | `fesetenv` | `fesetexceptflag` |
|---|---|---|---|---|---|---|---|
| `fesetround` | `fetestexcept` | `feupdateenv` |
|---|---|---|

### `file.h` (1)

| `flock` |
|---|

### `fmtmsg.h` (1)

| `fmtmsg` |
|---|

### `fnmatch.h` (1)

| `fnmatch` |
|---|

### `fsuid.h` (2)

| `setfsgid` | `setfsuid` |
|---|---|

### `ftw.h` (2)

| `ftw` | `nftw` |
|---|---|

### `getopt.h` (3)

| `getopt` | `getopt_long` | `getopt_long_only` |
|---|---|---|

### `glob.h` (2)

| `glob` | `globfree` |
|---|---|

### `grp.h` (12)

| `endgrent` | `fgetgrent` | `getgrent` | `getgrgid` | `getgrgid_r` | `getgrnam` | `getgrnam_r` | `getgrouplist` |
|---|---|---|---|---|---|---|---|
| `initgroups` | `putgrent` | `setgrent` | `setgroups` |
|---|---|---|---|

### `iconv.h` (3)

| `iconv` | `iconv_close` | `iconv_open` |
|---|---|---|

### `if.h` (4)

| `if_freenameindex` | `if_indextoname` | `if_nameindex` | `if_nametoindex` |
|---|---|---|---|

### `ifaddrs.h` (2)

| `freeifaddrs` | `getifaddrs` |
|---|---|

### `inet.h` (13)

| `htonl` | `htons` | `inet_addr` | `inet_aton` | `inet_lnaof` | `inet_makeaddr` | `inet_netof` | `inet_network` |
|---|---|---|---|---|---|---|---|
| `inet_ntoa` | `inet_ntop` | `inet_pton` | `ntohl` | `ntohs` |
|---|---|---|---|---|

### `inotify.h` (4)

| `inotify_add_watch` | `inotify_init` | `inotify_init1` | `inotify_rm_watch` |
|---|---|---|---|

### `inttypes.h` (6)

| `imaxabs` | `imaxdiv` | `strtoimax` | `strtoumax` | `wcstoimax` | `wcstoumax` |
|---|---|---|---|---|---|

### `io.h` (2)

| `ioperm` | `iopl` |
|---|---|

### `ipc.h` (1)

| `ftok` |
|---|

### `klog.h` (1)

| `klogctl` |
|---|

### `langinfo.h` (2)

| `nl_langinfo` | `nl_langinfo_l` |
|---|---|

### `libgen.h` (2)

| `basename` | `dirname` |
|---|---|

### `libintl.h` (9)

| `bind_textdomain_codeset` | `bindtextdomain` | `dcgettext` | `dcngettext` | `dgettext` | `dngettext` | `gettext` | `ngettext` |
|---|---|---|---|---|---|---|---|
| `textdomain` |
|---|

### `link.h` (2)

| `dl_iterate_phdr` | `ElfW` |
|---|---|

### `locale.h` (6)

| `duplocale` | `freelocale` | `localeconv` | `newlocale` | `setlocale` | `uselocale` |
|---|---|---|---|---|---|

### `malloc.h` (7)

| `calloc` | `free` | `malloc` | `malloc_usable_size` | `memalign` | `realloc` | `valloc` |
|---|---|---|---|---|---|---|

### `math.h` (202)

| `acosf` | `acosh` | `acoshf` | `acoshl` | `acosl` | `asin` | `asinf` | `asinh` |
|---|---|---|---|---|---|---|---|
| `asinhf` | `asinhl` | `asinl` | `atan` | `atan2` | `atan2f` | `atan2l` | `atanf` |
|---|---|---|---|---|---|---|---|
| `atanh` | `atanhf` | `atanhl` | `atanl` | `cbrt` | `cbrtf` | `cbrtl` | `ceil` |
|---|---|---|---|---|---|---|---|
| `ceilf` | `ceill` | `copysign` | `copysignf` | `copysignl` | `cos` | `cosf` | `cosh` |
|---|---|---|---|---|---|---|---|
| `coshf` | `coshl` | `cosl` | `drem` | `dremf` | `erf` | `erfc` | `erfcf` |
|---|---|---|---|---|---|---|---|
| `erfcl` | `erff` | `erfl` | `exp` | `exp10` | `exp10f` | `exp10l` | `exp2` |
|---|---|---|---|---|---|---|---|
| `exp2f` | `exp2l` | `expf` | `expl` | `expm1` | `expm1f` | `expm1l` | `fabs` |
|---|---|---|---|---|---|---|---|
| `fabsf` | `fabsl` | `fdim` | `fdimf` | `fdiml` | `finite` | `finitef` | `floor` |
|---|---|---|---|---|---|---|---|
| `floorf` | `floorl` | `fma` | `fmaf` | `fmal` | `fmax` | `fmaxf` | `fmaxl` |
|---|---|---|---|---|---|---|---|
| `fmin` | `fminf` | `fminl` | `fmod` | `fmodf` | `fmodl` | `frexp` | `frexpf` |
|---|---|---|---|---|---|---|---|
| `frexpl` | `hypot` | `hypotf` | `hypotl` | `ilogb` | `ilogbf` | `ilogbl` | `j0` |
|---|---|---|---|---|---|---|---|
| `j0f` | `j1` | `j1f` | `jn` | `jnf` | `ldexp` | `ldexpf` | `ldexpl` |
|---|---|---|---|---|---|---|---|
| `lgamma` | `lgamma_r` | `lgammaf` | `lgammaf_r` | `lgammal` | `lgammal_r` | `llrint` | `llrintf` |
|---|---|---|---|---|---|---|---|
| `llrintl` | `llround` | `llroundf` | `llroundl` | `log` | `log10` | `log10f` | `log10l` |
|---|---|---|---|---|---|---|---|
| `log1p` | `log1pf` | `log1pl` | `log2` | `log2f` | `log2l` | `logb` | `logbf` |
|---|---|---|---|---|---|---|---|
| `logbl` | `logf` | `logl` | `lrint` | `lrintf` | `lrintl` | `lround` | `lroundf` |
|---|---|---|---|---|---|---|---|
| `lroundl` | `modf` | `modff` | `modfl` | `nan` | `nanf` | `nanl` | `nearbyint` |
|---|---|---|---|---|---|---|---|
| `nearbyintf` | `nearbyintl` | `nextafter` | `nextafterf` | `nextafterl` | `nexttoward` | `nexttowardf` | `nexttowardl` |
|---|---|---|---|---|---|---|---|
| `pow` | `pow10` | `pow10f` | `pow10l` | `powf` | `powl` | `remainder` | `remainderf` |
|---|---|---|---|---|---|---|---|
| `remainderl` | `remquo` | `remquof` | `remquol` | `rint` | `rintf` | `rintl` | `round` |
|---|---|---|---|---|---|---|---|
| `roundf` | `roundl` | `scalb` | `scalbf` | `scalbln` | `scalblnf` | `scalblnl` | `scalbn` |
|---|---|---|---|---|---|---|---|
| `scalbnf` | `scalbnl` | `significand` | `significandf` | `sin` | `sincos` | `sincosf` | `sincosl` |
|---|---|---|---|---|---|---|---|
| `sinf` | `sinh` | `sinhf` | `sinhl` | `sinl` | `sqrt` | `sqrtf` | `sqrtl` |
|---|---|---|---|---|---|---|---|
| `tan` | `tanf` | `tanh` | `tanhf` | `tanhl` | `tanl` | `tgamma` | `tgammaf` |
|---|---|---|---|---|---|---|---|
| `tgammal` | `trunc` | `truncf` | `truncl` | `y0` | `y0f` | `y1` | `y1f` |
|---|---|---|---|---|---|---|---|
| `yn` | `ynf` |
|---|---|

### `membarrier.h` (1)

| `membarrier` |
|---|

### `mman.h` (17)

| `madvise` | `memfd_create` | `mincore` | `mlock` | `mlock2` | `mlockall` | `mmap` | `mprotect` |
|---|---|---|---|---|---|---|---|
| `mremap` | `msync` | `munlock` | `munlockall` | `munmap` | `posix_madvise` | `remap_file_pages` | `shm_open` |
|---|---|---|---|---|---|---|---|
| `shm_unlink` |
|---|

### `mntent.h` (6)

| `addmntent` | `endmntent` | `getmntent` | `getmntent_r` | `hasmntopt` | `setmntent` |
|---|---|---|---|---|---|

### `monetary.h` (2)

| `strfmon` | `strfmon_l` |
|---|---|

### `mount.h` (3)

| `mount` | `umount` | `umount2` |
|---|---|---|

### `mqueue.h` (10)

| `mq_close` | `mq_getattr` | `mq_notify` | `mq_open` | `mq_receive` | `mq_send` | `mq_setattr` | `mq_timedreceive` |
|---|---|---|---|---|---|---|---|
| `mq_timedsend` | `mq_unlink` |
|---|---|

### `msg.h` (4)

| `msgctl` | `msgget` | `msgrcv` | `msgsnd` |
|---|---|---|---|

### `nameser.h` (8)

| `ns_get16` | `ns_get32` | `ns_initparse` | `ns_name_uncompress` | `ns_parserr` | `ns_put16` | `ns_put32` | `ns_skiprr` |
|---|---|---|---|---|---|---|---|

### `netdb.h` (32)

| `endhostent` | `endnetent` | `endprotoent` | `endservent` | `freeaddrinfo` | `gai_strerror` | `getaddrinfo` | `gethostbyaddr` |
|---|---|---|---|---|---|---|---|
| `gethostbyaddr_r` | `gethostbyname` | `gethostbyname2` | `gethostbyname2_r` | `gethostbyname_r` | `gethostent` | `getnameinfo` | `getnetbyaddr` |
|---|---|---|---|---|---|---|---|
| `getnetbyname` | `getnetent` | `getprotobyname` | `getprotobynumber` | `getprotoent` | `getservbyname` | `getservbyname_r` | `getservbyport` |
|---|---|---|---|---|---|---|---|
| `getservbyport_r` | `getservent` | `herror` | `hstrerror` | `sethostent` | `setnetent` | `setprotoent` | `setservent` |
|---|---|---|---|---|---|---|---|

### `nl_types.h` (3)

| `catclose` | `catgets` | `catopen` |
|---|---|---|

### `personality.h` (1)

| `personality` |
|---|

### `poll.h` (2)

| `poll` | `ppoll` |
|---|---|

### `prctl.h` (1)

| `prctl` |
|---|

### `pthread.h` (108)

| `_pthread_cleanup_pop` | `_pthread_cleanup_push` | `pthread_atfork` | `pthread_attr_destroy` | `pthread_attr_getdetachstate` | `pthread_attr_getguardsize` | `pthread_attr_getinheritsched` | `pthread_attr_getschedparam` |
|---|---|---|---|---|---|---|---|
| `pthread_attr_getschedpolicy` | `pthread_attr_getscope` | `pthread_attr_getstack` | `pthread_attr_getstacksize` | `pthread_attr_init` | `pthread_attr_setdetachstate` | `pthread_attr_setguardsize` | `pthread_attr_setinheritsched` |
|---|---|---|---|---|---|---|---|
| `pthread_attr_setschedparam` | `pthread_attr_setschedpolicy` | `pthread_attr_setscope` | `pthread_attr_setstack` | `pthread_attr_setstacksize` | `pthread_barrier_destroy` | `pthread_barrier_init` | `pthread_barrier_wait` |
|---|---|---|---|---|---|---|---|
| `pthread_barrierattr_destroy` | `pthread_barrierattr_getpshared` | `pthread_barrierattr_init` | `pthread_barrierattr_setpshared` | `pthread_cancel` | `pthread_cond_broadcast` | `pthread_cond_destroy` | `pthread_cond_init` |
|---|---|---|---|---|---|---|---|
| `pthread_cond_signal` | `pthread_cond_timedwait` | `pthread_cond_wait` | `pthread_condattr_destroy` | `pthread_condattr_getclock` | `pthread_condattr_getpshared` | `pthread_condattr_init` | `pthread_condattr_setclock` |
|---|---|---|---|---|---|---|---|
| `pthread_condattr_setpshared` | `pthread_create` | `pthread_detach` | `pthread_equal` | `pthread_exit` | `pthread_getaffinity_np` | `pthread_getattr_default_np` | `pthread_getattr_np` |
|---|---|---|---|---|---|---|---|
| `pthread_getconcurrency` | `pthread_getcpuclockid` | `pthread_getname_np` | `pthread_getschedparam` | `pthread_getspecific` | `pthread_join` | `pthread_key_create` | `pthread_key_delete` |
|---|---|---|---|---|---|---|---|
| `pthread_mutex_consistent` | `pthread_mutex_destroy` | `pthread_mutex_getprioceiling` | `pthread_mutex_init` | `pthread_mutex_lock` | `pthread_mutex_setprioceiling` | `pthread_mutex_timedlock` | `pthread_mutex_trylock` |
|---|---|---|---|---|---|---|---|
| `pthread_mutex_unlock` | `pthread_mutexattr_destroy` | `pthread_mutexattr_getprioceiling` | `pthread_mutexattr_getprotocol` | `pthread_mutexattr_getpshared` | `pthread_mutexattr_getrobust` | `pthread_mutexattr_gettype` | `pthread_mutexattr_init` |
|---|---|---|---|---|---|---|---|
| `pthread_mutexattr_setprioceiling` | `pthread_mutexattr_setprotocol` | `pthread_mutexattr_setpshared` | `pthread_mutexattr_setrobust` | `pthread_mutexattr_settype` | `pthread_once` | `pthread_rwlock_destroy` | `pthread_rwlock_init` |
|---|---|---|---|---|---|---|---|
| `pthread_rwlock_rdlock` | `pthread_rwlock_timedrdlock` | `pthread_rwlock_timedwrlock` | `pthread_rwlock_tryrdlock` | `pthread_rwlock_trywrlock` | `pthread_rwlock_unlock` | `pthread_rwlock_wrlock` | `pthread_rwlockattr_destroy` |
|---|---|---|---|---|---|---|---|
| `pthread_rwlockattr_getpshared` | `pthread_rwlockattr_init` | `pthread_rwlockattr_setpshared` | `pthread_setaffinity_np` | `pthread_setattr_default_np` | `pthread_setcancelstate` | `pthread_setcanceltype` | `pthread_setconcurrency` |
|---|---|---|---|---|---|---|---|
| `pthread_setname_np` | `pthread_setschedparam` | `pthread_setschedprio` | `pthread_setspecific` | `pthread_spin_destroy` | `pthread_spin_init` | `pthread_spin_lock` | `pthread_spin_trylock` |
|---|---|---|---|---|---|---|---|
| `pthread_spin_unlock` | `pthread_testcancel` | `pthread_timedjoin_np` | `pthread_tryjoin_np` |
|---|---|---|---|

### `ptrace.h` (1)

| `ptrace` |
|---|

### `pty.h` (2)

| `forkpty` | `openpty` |
|---|---|

### `pwd.h` (9)

| `endpwent` | `fgetpwent` | `getpwent` | `getpwnam` | `getpwnam_r` | `getpwuid` | `getpwuid_r` | `putpwent` |
|---|---|---|---|---|---|---|---|
| `setpwent` |
|---|

### `quota.h` (1)

| `quotactl` |
|---|

### `random.h` (1)

| `getrandom` |
|---|

### `reboot.h` (1)

| `reboot` |
|---|

### `regex.h` (4)

| `regcomp` | `regerror` | `regexec` | `regfree` |
|---|---|---|---|

### `resolv.h` (9)

| `dn_comp` | `dn_expand` | `dn_skipname` | `res_init` | `res_mkquery` | `res_query` | `res_querydomain` | `res_search` |
|---|---|---|---|---|---|---|---|
| `res_send` |
|---|

### `resource.h` (6)

| `getpriority` | `getrlimit` | `getrusage` | `prlimit` | `setpriority` | `setrlimit` |
|---|---|---|---|---|---|

### `sched.h` (17)

| `clone` | `memcmp` | `memcpy` | `memset` | `sched_get_priority_max` | `sched_get_priority_min` | `sched_getaffinity` | `sched_getcpu` |
|---|---|---|---|---|---|---|---|
| `sched_getparam` | `sched_getscheduler` | `sched_rr_get_interval` | `sched_setaffinity` | `sched_setparam` | `sched_setscheduler` | `sched_yield` | `setns` |
|---|---|---|---|---|---|---|---|
| `unshare` |
|---|

### `search.h` (15)

| `hcreate` | `hcreate_r` | `hdestroy` | `hdestroy_r` | `hsearch` | `hsearch_r` | `insque` | `lfind` |
|---|---|---|---|---|---|---|---|
| `lsearch` | `remque` | `tdelete` | `tdestroy` | `tfind` | `tsearch` | `twalk` |
|---|---|---|---|---|---|---|

### `select.h` (2)

| `pselect` | `select` |
|---|---|

### `sem.h` (4)

| `semctl` | `semget` | `semop` | `semtimedop` |
|---|---|---|---|

### `semaphore.h` (10)

| `sem_close` | `sem_destroy` | `sem_getvalue` | `sem_init` | `sem_open` | `sem_post` | `sem_timedwait` | `sem_trywait` |
|---|---|---|---|---|---|---|---|
| `sem_unlink` | `sem_wait` |
|---|---|

### `sendfile.h` (1)

| `sendfile` |
|---|

### `setjmp.h` (6)

| `_longjmp` | `_setjmp` | `longjmp` | `setjmp` | `siglongjmp` | `sigsetjmp` |
|---|---|---|---|---|---|

### `shadow.h` (10)

| `endspent` | `fgetspent` | `getspent` | `getspnam` | `getspnam_r` | `lckpwdf` | `putspent` | `setspent` |
|---|---|---|---|---|---|---|---|
| `sgetspent` | `ulckpwdf` |
|---|---|

### `shm.h` (4)

| `shmat` | `shmctl` | `shmdt` | `shmget` |
|---|---|---|---|

### `signal.h` (30)

| `kill` | `killpg` | `psiginfo` | `psignal` | `pthread_kill` | `pthread_sigmask` | `raise` | `sigaction` |
|---|---|---|---|---|---|---|---|
| `sigaddset` | `sigaltstack` | `sigandset` | `sigdelset` | `sigemptyset` | `sigfillset` | `sighold` | `sigignore` |
|---|---|---|---|---|---|---|---|
| `siginterrupt` | `sigisemptyset` | `sigismember` | `sigorset` | `sigpause` | `sigpending` | `sigprocmask` | `sigqueue` |
|---|---|---|---|---|---|---|---|
| `sigrelse` | `sigsuspend` | `sigtimedwait` | `sigwait` | `sigwaitinfo` | `void` |
|---|---|---|---|---|---|

### `signalfd.h` (1)

| `signalfd` |
|---|

### `socket.h` (21)

| `accept` | `accept4` | `bind` | `connect` | `getpeername` | `getsockname` | `getsockopt` | `listen` |
|---|---|---|---|---|---|---|---|
| `recv` | `recvfrom` | `recvmmsg` | `recvmsg` | `send` | `sendmmsg` | `sendmsg` | `sendto` |
|---|---|---|---|---|---|---|---|
| `setsockopt` | `shutdown` | `sockatmark` | `socket` | `socketpair` |
|---|---|---|---|---|

### `spawn.h` (23)

| `posix_spawn` | `posix_spawn_file_actions_addchdir_np` | `posix_spawn_file_actions_addclose` | `posix_spawn_file_actions_adddup2` | `posix_spawn_file_actions_addfchdir_np` | `posix_spawn_file_actions_addopen` | `posix_spawn_file_actions_destroy` | `posix_spawn_file_actions_init` |
|---|---|---|---|---|---|---|---|
| `posix_spawnattr_destroy` | `posix_spawnattr_getflags` | `posix_spawnattr_getpgroup` | `posix_spawnattr_getschedparam` | `posix_spawnattr_getschedpolicy` | `posix_spawnattr_getsigdefault` | `posix_spawnattr_getsigmask` | `posix_spawnattr_init` |
|---|---|---|---|---|---|---|---|
| `posix_spawnattr_setflags` | `posix_spawnattr_setpgroup` | `posix_spawnattr_setschedparam` | `posix_spawnattr_setschedpolicy` | `posix_spawnattr_setsigdefault` | `posix_spawnattr_setsigmask` | `posix_spawnp` |
|---|---|---|---|---|---|---|

### `stat.h` (18)

| `chmod` | `fchmod` | `fchmodat` | `fstat` | `fstatat` | `futimens` | `lchmod` | `lstat` |
|---|---|---|---|---|---|---|---|
| `mkdir` | `mkdirat` | `mkfifo` | `mkfifoat` | `mknod` | `mknodat` | `stat` | `statx` |
|---|---|---|---|---|---|---|---|
| `umask` | `utimensat` |
|---|---|

### `statfs.h` (2)

| `fstatfs` | `statfs` |
|---|---|

### `statvfs.h` (3)

| `fstatvfs` | `statvfs` | `unsigned` |
|---|---|---|

### `stdio.h` (88)

| `asprintf` | `clearerr` | `clearerr_unlocked` | `ctermid` | `cuserid` | `dprintf` | `fclose` | `fdopen` |
|---|---|---|---|---|---|---|---|
| `feof` | `feof_unlocked` | `ferror` | `ferror_unlocked` | `fflush` | `fflush_unlocked` | `fgetc` | `fgetc_unlocked` |
|---|---|---|---|---|---|---|---|
| `fgetln` | `fgetpos` | `fgets` | `fgets_unlocked` | `fileno` | `fileno_unlocked` | `flockfile` | `fmemopen` |
|---|---|---|---|---|---|---|---|
| `fopen` | `fopencookie` | `fprintf` | `fputc` | `fputc_unlocked` | `fputs` | `fputs_unlocked` | `fread` |
|---|---|---|---|---|---|---|---|
| `fread_unlocked` | `freopen` | `fscanf` | `fseek` | `fseeko` | `fsetpos` | `ftell` | `ftello` |
|---|---|---|---|---|---|---|---|
| `ftrylockfile` | `funlockfile` | `fwrite` | `fwrite_unlocked` | `getc` | `getc_unlocked` | `getchar` | `getchar_unlocked` |
|---|---|---|---|---|---|---|---|
| `getdelim` | `getline` | `gets` | `getw` | `open_memstream` | `pclose` | `perror` | `popen` |
|---|---|---|---|---|---|---|---|
| `printf` | `putc` | `putc_unlocked` | `putchar` | `putchar_unlocked` | `puts` | `putw` | `remove` |
|---|---|---|---|---|---|---|---|
| `rename` | `renameat` | `rewind` | `scanf` | `setbuf` | `setbuffer` | `setlinebuf` | `setvbuf` |
|---|---|---|---|---|---|---|---|
| `snprintf` | `sprintf` | `sscanf` | `tempnam` | `tmpfile` | `tmpnam` | `ungetc` | `vasprintf` |
|---|---|---|---|---|---|---|---|
| `vdprintf` | `vfprintf` | `vfscanf` | `vprintf` | `vscanf` | `vsnprintf` | `vsprintf` | `vsscanf` |
|---|---|---|---|---|---|---|---|

### `stdio_ext.h` (1)

| `_flushlbf` |
|---|

### `stdlib.h` (80)

| `_Exit` | `a64l` | `abort` | `abs` | `aligned_alloc` | `at_quick_exit` | `atexit` | `atof` |
|---|---|---|---|---|---|---|---|
| `atoi` | `atol` | `atoll` | `bsearch` | `clearenv` | `div` | `drand48` | `ecvt` |
|---|---|---|---|---|---|---|---|
| `erand48` | `exit` | `fcvt` | `gcvt` | `getenv` | `getloadavg` | `getsubopt` | `grantpt` |
|---|---|---|---|---|---|---|---|
| `initstate` | `jrand48` | `l64a` | `labs` | `lcong48` | `ldiv` | `llabs` | `lldiv` |
|---|---|---|---|---|---|---|---|
| `lrand48` | `mblen` | `mbstowcs` | `mbtowc` | `mkdtemp` | `mkostemp` | `mkostemps` | `mkstemp` |
|---|---|---|---|---|---|---|---|
| `mkstemps` | `mktemp` | `mrand48` | `nrand48` | `posix_memalign` | `posix_openpt` | `ptsname` | `ptsname_r` |
|---|---|---|---|---|---|---|---|
| `putenv` | `qsort` | `qsort_r` | `quick_exit` | `rand` | `rand_r` | `random` | `reallocarray` |
|---|---|---|---|---|---|---|---|
| `realpath` | `secure_getenv` | `seed48` | `setenv` | `setkey` | `setstate` | `srand` | `srand48` |
|---|---|---|---|---|---|---|---|
| `srandom` | `strtod` | `strtod_l` | `strtof` | `strtof_l` | `strtol` | `strtold` | `strtold_l` |
|---|---|---|---|---|---|---|---|
| `strtoll` | `strtoul` | `strtoull` | `system` | `unlockpt` | `unsetenv` | `wcstombs` | `wctomb` |
|---|---|---|---|---|---|---|---|

### `string.h` (41)

| `explicit_bzero` | `memccpy` | `memchr` | `memmem` | `memmove` | `mempcpy` | `memrchr` | `stpcpy` |
|---|---|---|---|---|---|---|---|
| `stpncpy` | `strcasestr` | `strcat` | `strchr` | `strchrnul` | `strcmp` | `strcoll` | `strcoll_l` |
|---|---|---|---|---|---|---|---|
| `strcpy` | `strcspn` | `strdup` | `strerror` | `strerror_l` | `strerror_r` | `strlcat` | `strlcpy` |
|---|---|---|---|---|---|---|---|
| `strlen` | `strncat` | `strncmp` | `strncpy` | `strndup` | `strnlen` | `strpbrk` | `strrchr` |
|---|---|---|---|---|---|---|---|
| `strsep` | `strsignal` | `strspn` | `strstr` | `strtok` | `strtok_r` | `strverscmp` | `strxfrm` |
|---|---|---|---|---|---|---|---|
| `strxfrm_l` |
|---|

### `strings.h` (12)

| `bcmp` | `bcopy` | `bzero` | `ffs` | `ffsl` | `ffsll` | `index` | `rindex` |
|---|---|---|---|---|---|---|---|
| `strcasecmp` | `strcasecmp_l` | `strncasecmp` | `strncasecmp_l` |
|---|---|---|---|

### `stropts.h` (2)

| `ioctl` | `isastream` |
|---|---|

### `swap.h` (2)

| `swapoff` | `swapon` |
|---|---|

### `sysinfo.h` (5)

| `get_avphys_pages` | `get_nprocs` | `get_nprocs_conf` | `get_phys_pages` | `sysinfo` |
|---|---|---|---|---|

### `syslog.h` (5)

| `closelog` | `openlog` | `setlogmask` | `syslog` | `vsyslog` |
|---|---|---|---|---|

### `termios.h` (15)

| `cfgetispeed` | `cfgetospeed` | `cfmakeraw` | `cfsetispeed` | `cfsetospeed` | `cfsetspeed` | `tcdrain` | `tcflow` |
|---|---|---|---|---|---|---|---|
| `tcflush` | `tcgetattr` | `tcgetsid` | `tcgetwinsize` | `tcsendbreak` | `tcsetattr` | `tcsetwinsize` |
|---|---|---|---|---|---|---|

### `threads.h` (25)

| `call_once` | `cnd_broadcast` | `cnd_destroy` | `cnd_init` | `cnd_signal` | `cnd_timedwait` | `cnd_wait` | `mtx_destroy` |
|---|---|---|---|---|---|---|---|
| `mtx_init` | `mtx_lock` | `mtx_timedlock` | `mtx_trylock` | `mtx_unlock` | `thrd_create` | `thrd_current` | `thrd_detach` |
|---|---|---|---|---|---|---|---|
| `thrd_equal` | `thrd_exit` | `thrd_join` | `thrd_sleep` | `thrd_yield` | `tss_create` | `tss_delete` | `tss_get` |
|---|---|---|---|---|---|---|---|
| `tss_set` |
|---|

### `time.h` (40)

| `adjtime` | `asctime` | `asctime_r` | `clock` | `clock_getcpuclockid` | `clock_getres` | `clock_gettime` | `clock_nanosleep` |
|---|---|---|---|---|---|---|---|
| `clock_settime` | `ctime` | `ctime_r` | `difftime` | `futimes` | `futimesat` | `getdate` | `getitimer` |
|---|---|---|---|---|---|---|---|
| `gettimeofday` | `gmtime` | `gmtime_r` | `localtime` | `localtime_r` | `lutimes` | `mktime` | `nanosleep` |
|---|---|---|---|---|---|---|---|
| `setitimer` | `settimeofday` | `stime` | `strftime` | `strftime_l` | `strptime` | `time` | `timegm` |
|---|---|---|---|---|---|---|---|
| `timer_create` | `timer_delete` | `timer_getoverrun` | `timer_gettime` | `timer_settime` | `timespec_get` | `tzset` | `utimes` |
|---|---|---|---|---|---|---|---|

### `timeb.h` (1)

| `ftime` |
|---|

### `timerfd.h` (3)

| `timerfd_create` | `timerfd_gettime` | `timerfd_settime` |
|---|---|---|

### `times.h` (1)

| `times` |
|---|

### `timex.h` (2)

| `adjtimex` | `clock_adjtime` |
|---|---|

### `uchar.h` (4)

| `c16rtomb` | `c32rtomb` | `mbrtoc16` | `mbrtoc32` |
|---|---|---|---|

### `ucontext.h` (4)

| `getcontext` | `makecontext` | `setcontext` | `swapcontext` |
|---|---|---|---|

### `uio.h` (8)

| `preadv` | `preadv2` | `process_vm_readv` | `process_vm_writev` | `pwritev` | `pwritev2` | `readv` | `writev` |
|---|---|---|---|---|---|---|---|

### `ulimit.h` (1)

| `ulimit` |
|---|

### `unistd.h` (114)

| `_exit` | `_Fork` | `access` | `alarm` | `brk` | `chdir` | `chown` | `chroot` |
|---|---|---|---|---|---|---|---|
| `close` | `confstr` | `copy_file_range` | `daemon` | `dup` | `dup2` | `dup3` | `eaccess` |
|---|---|---|---|---|---|---|---|
| `encrypt` | `endusershell` | `euidaccess` | `execl` | `execle` | `execlp` | `execv` | `execve` |
|---|---|---|---|---|---|---|---|
| `execvp` | `execvpe` | `faccessat` | `fchdir` | `fchown` | `fchownat` | `fdatasync` | `fexecve` |
|---|---|---|---|---|---|---|---|
| `fork` | `fpathconf` | `fsync` | `ftruncate` | `get_current_dir_name` | `getcwd` | `getdomainname` | `getdtablesize` |
|---|---|---|---|---|---|---|---|
| `getegid` | `getentropy` | `geteuid` | `getgid` | `getgroups` | `gethostid` | `gethostname` | `getlogin` |
|---|---|---|---|---|---|---|---|
| `getlogin_r` | `getpagesize` | `getpass` | `getpgid` | `getpgrp` | `getpid` | `getppid` | `getresgid` |
|---|---|---|---|---|---|---|---|
| `getresuid` | `getsid` | `gettid` | `getuid` | `getusershell` | `isatty` | `issetugid` | `lchown` |
|---|---|---|---|---|---|---|---|
| `link` | `linkat` | `lseek` | `nice` | `pathconf` | `pause` | `pipe` | `pipe2` |
|---|---|---|---|---|---|---|---|
| `posix_close` | `pread` | `pwrite` | `read` | `readlink` | `readlinkat` | `rmdir` | `sbrk` |
|---|---|---|---|---|---|---|---|
| `setdomainname` | `setegid` | `seteuid` | `setgid` | `sethostname` | `setpgid` | `setpgrp` | `setregid` |
|---|---|---|---|---|---|---|---|
| `setresgid` | `setresuid` | `setreuid` | `setsid` | `setuid` | `setusershell` | `sleep` | `swab` |
|---|---|---|---|---|---|---|---|
| `symlink` | `symlinkat` | `sync` | `syncfs` | `syscall` | `sysconf` | `tcgetpgrp` | `tcsetpgrp` |
|---|---|---|---|---|---|---|---|
| `truncate` | `ttyname` | `ttyname_r` | `ualarm` | `unlink` | `unlinkat` | `usleep` | `vfork` |
|---|---|---|---|---|---|---|---|
| `vhangup` | `write` |
|---|---|

### `utime.h` (1)

| `utime` |
|---|

### `utmp.h` (9)

| `endutent` | `getutent` | `getutid` | `getutline` | `login_tty` | `pututline` | `setutent` | `updwtmp` |
|---|---|---|---|---|---|---|---|
| `utmpname` |
|---|

### `utmpx.h` (8)

| `endutxent` | `getutxent` | `getutxid` | `getutxline` | `pututxline` | `setutxent` | `updwtmpx` | `utmpxname` |
|---|---|---|---|---|---|---|---|

### `utsname.h` (1)

| `uname` |
|---|

### `wait.h` (5)

| `wait` | `wait3` | `wait4` | `waitid` | `waitpid` |
|---|---|---|---|---|

### `wchar.h` (100)

| `btowc` | `fgetwc` | `fgetwc_unlocked` | `fgetws` | `fgetws_unlocked` | `fputwc` | `fputwc_unlocked` | `fputws` |
|---|---|---|---|---|---|---|---|
| `fputws_unlocked` | `fwide` | `fwprintf` | `fwscanf` | `getwc` | `getwc_unlocked` | `getwchar` | `getwchar_unlocked` |
|---|---|---|---|---|---|---|---|
| `iswalnum` | `iswalpha` | `iswblank` | `iswcntrl` | `iswctype` | `iswdigit` | `iswgraph` | `iswlower` |
|---|---|---|---|---|---|---|---|
| `iswprint` | `iswpunct` | `iswspace` | `iswupper` | `iswxdigit` | `mbrlen` | `mbrtowc` | `mbsinit` |
|---|---|---|---|---|---|---|---|
| `mbsnrtowcs` | `mbsrtowcs` | `open_wmemstream` | `putwc` | `putwc_unlocked` | `putwchar` | `putwchar_unlocked` | `swprintf` |
|---|---|---|---|---|---|---|---|
| `swscanf` | `towlower` | `towupper` | `ungetwc` | `vfwprintf` | `vfwscanf` | `vswprintf` | `vswscanf` |
|---|---|---|---|---|---|---|---|
| `vwprintf` | `vwscanf` | `wcpcpy` | `wcpncpy` | `wcrtomb` | `wcscasecmp` | `wcscasecmp_l` | `wcscat` |
|---|---|---|---|---|---|---|---|
| `wcschr` | `wcscmp` | `wcscoll` | `wcscoll_l` | `wcscpy` | `wcscspn` | `wcsdup` | `wcsftime` |
|---|---|---|---|---|---|---|---|
| `wcsftime_l` | `wcslen` | `wcsncasecmp` | `wcsncasecmp_l` | `wcsncat` | `wcsncmp` | `wcsncpy` | `wcsnlen` |
|---|---|---|---|---|---|---|---|
| `wcsnrtombs` | `wcspbrk` | `wcsrchr` | `wcsrtombs` | `wcsspn` | `wcsstr` | `wcstod` | `wcstof` |
|---|---|---|---|---|---|---|---|
| `wcstok` | `wcstol` | `wcstold` | `wcstoll` | `wcstoul` | `wcstoull` | `wcswcs` | `wcswidth` |
|---|---|---|---|---|---|---|---|
| `wcsxfrm` | `wcsxfrm_l` | `wctob` | `wctype` | `wcwidth` | `wmemchr` | `wmemcmp` | `wmemcpy` |
|---|---|---|---|---|---|---|---|
| `wmemmove` | `wmemset` | `wprintf` | `wscanf` |
|---|---|---|---|

### `wctype.h` (20)

| `iswalnum_l` | `iswalpha_l` | `iswblank_l` | `iswcntrl_l` | `iswctype_l` | `iswdigit_l` | `iswgraph_l` | `iswlower_l` |
|---|---|---|---|---|---|---|---|
| `iswprint_l` | `iswpunct_l` | `iswspace_l` | `iswupper_l` | `iswxdigit_l` | `towctrans` | `towctrans_l` | `towlower_l` |
|---|---|---|---|---|---|---|---|
| `towupper_l` | `wctrans` | `wctrans_l` | `wctype_l` |
|---|---|---|---|

### `wordexp.h` (2)

| `wordexp` | `wordfree` |
|---|---|

### `xattr.h` (12)

| `fgetxattr` | `flistxattr` | `fremovexattr` | `fsetxattr` | `getxattr` | `lgetxattr` | `listxattr` | `llistxattr` |
|---|---|---|---|---|---|---|---|
| `lremovexattr` | `lsetxattr` | `removexattr` | `setxattr` |
|---|---|---|---|

musl functions inventoried: 1482.

## Set deltas vs glibc 2.41

### In musl 1.2.5 headers, not in the glibc 2.41 set

Names below exist in musl's headers but matched neither glibc's documented
functions nor its exported dynamic symbols. Verify per name before citing:
some are reserved-namespace spellings that glibc also provides but exports
only as `__`-prefixed internal aliases (excluded from the glibc set by
policy), and some are musl-added functions.

- `ElfW`
- `_flush_cache`
- `at_quick_exit`
- `cachectl`
- `cacheflush`
- `fgetln`
- `getdents`
- `issetugid`
- `membarrier`
- `posix_close`
- `res_init`
- `tcgetwinsize`
- `tcsetwinsize`
- `unsigned`
- `void`

### In the glibc 2.41 set, not in musl 1.2.5 headers

This list is long because it includes GNU extensions, error-reporting and
stdio helpers, XSI leftovers, and symbol-versioned compat names. It is
reproduced in full (sorted) so that coverage claims can be checked
mechanically; the [musl catalog](./musl-catalog.md) discusses the families
that matter in practice.

- `DTTOIF`
- `IFTODT`
- `_IO_2_1_stderr_`
- `_IO_2_1_stdin_`
- `_IO_2_1_stdout_`
- `_IO_adjust_column`
- `_IO_adjust_wcolumn`
- `_IO_default_doallocate`
- `_IO_default_finish`
- `_IO_default_pbackfail`
- `_IO_default_uflow`
- `_IO_default_xsgetn`
- `_IO_default_xsputn`
- `_IO_do_write`
- `_IO_doallocbuf`
- `_IO_enable_locks`
- `_IO_fclose`
- `_IO_fdopen`
- `_IO_feof`
- `_IO_ferror`
- `_IO_fflush`
- `_IO_fgetpos`
- `_IO_fgetpos64`
- `_IO_fgets`
- `_IO_file_attach`
- `_IO_file_close`
- `_IO_file_close_it`
- `_IO_file_doallocate`
- `_IO_file_finish`
- `_IO_file_fopen`
- `_IO_file_init`
- `_IO_file_jumps`
- `_IO_file_open`
- `_IO_file_overflow`
- `_IO_file_read`
- `_IO_file_seek`
- `_IO_file_seekoff`
- `_IO_file_setbuf`
- `_IO_file_stat`
- `_IO_file_sync`
- `_IO_file_underflow`
- `_IO_file_write`
- `_IO_file_xsputn`
- `_IO_flockfile`
- `_IO_flush_all`
- `_IO_flush_all_linebuffered`
- `_IO_fopen`
- `_IO_fprintf`
- `_IO_fputs`
- `_IO_fread`
- `_IO_free_backup_area`
- `_IO_free_wbackup_area`
- `_IO_fsetpos`
- `_IO_fsetpos64`
- `_IO_ftell`
- `_IO_ftrylockfile`
- `_IO_funlockfile`
- `_IO_fwrite`
- `_IO_getc`
- `_IO_getline`
- `_IO_getline_info`
- `_IO_gets`
- `_IO_init`
- `_IO_init_marker`
- `_IO_init_wmarker`
- `_IO_iter_begin`
- `_IO_iter_end`
- `_IO_iter_file`
- `_IO_iter_next`
- `_IO_least_wmarker`
- `_IO_link_in`
- `_IO_list_all`
- `_IO_list_lock`
- `_IO_list_resetlock`
- `_IO_list_unlock`
- `_IO_marker_delta`
- `_IO_marker_difference`
- `_IO_padn`
- `_IO_peekc_locked`
- `_IO_popen`
- `_IO_printf`
- `_IO_proc_close`
- `_IO_proc_open`
- `_IO_putc`
- `_IO_puts`
- `_IO_remove_marker`
- `_IO_seekmark`
- `_IO_seekoff`
- `_IO_seekpos`
- `_IO_seekwmark`
- `_IO_setb`
- `_IO_setbuffer`
- `_IO_setvbuf`
- `_IO_sgetn`
- `_IO_sprintf`
- `_IO_sputbackc`
- `_IO_sputbackwc`
- `_IO_sscanf`
- `_IO_str_init_readonly`
- `_IO_str_init_static`
- `_IO_str_overflow`
- `_IO_str_pbackfail`
- `_IO_str_seekoff`
- `_IO_str_underflow`
- `_IO_sungetc`
- `_IO_sungetwc`
- `_IO_switch_to_get_mode`
- `_IO_switch_to_main_wget_area`
- `_IO_switch_to_wbackup_area`
- `_IO_switch_to_wget_mode`
- `_IO_un_link`
- `_IO_ungetc`
- `_IO_unsave_markers`
- `_IO_unsave_wmarkers`
- `_IO_vfprintf`
- `_IO_vfscanf`
- `_IO_vsprintf`
- `_IO_wdefault_doallocate`
- `_IO_wdefault_finish`
- `_IO_wdefault_pbackfail`
- `_IO_wdefault_uflow`
- `_IO_wdefault_xsgetn`
- `_IO_wdefault_xsputn`
- `_IO_wdo_write`
- `_IO_wdoallocbuf`
- `_IO_wfile_jumps`
- `_IO_wfile_overflow`
- `_IO_wfile_seekoff`
- `_IO_wfile_sync`
- `_IO_wfile_underflow`
- `_IO_wfile_xsputn`
- `_IO_wmarker_delta`
- `_IO_wsetb`
- `_LIB_VERSION`
- `__fbufsize`
- `__flbf`
- `__fpending`
- `__fpurge`
- `__freadable`
- `__freading`
- `__fsetlocking`
- `__fwritable`
- `__fwriting`
- `__ppc_get_timebase`
- `__ppc_get_timebase_freq`
- `__ppc_mdoio`
- `__ppc_mdoom`
- `__ppc_set_ppr_low`
- `__ppc_set_ppr_med`
- `__ppc_set_ppr_med_high`
- `__ppc_set_ppr_med_low`
- `__ppc_set_ppr_very_low`
- `__ppc_yield`
- `__riscv_flush_icache`
- `__x86_get_cpuid_feature_leaf`
- `_authenticate`
- `_dl_find_object`
- `_dl_mcount_wrapper`
- `_dl_mcount_wrapper_check`
- `_gethtbyaddr`
- `_gethtbyname`
- `_gethtbyname2`
- `_gethtent`
- `_getlong`
- `_getshort`
- `_itoa_lower_digits`
- `_libc_intl_domainname`
- `_mcleanup`
- `_mcount`
- `_nl_default_dirname`
- `_nl_domain_bindings`
- `_nl_msg_cat_cntr`
- `_nss_dns_getcanonname_r`
- `_nss_dns_gethostbyaddr2_r`
- `_nss_dns_gethostbyaddr_r`
- `_nss_dns_gethostbyname2_r`
- `_nss_dns_gethostbyname3_r`
- `_nss_dns_gethostbyname4_r`
- `_nss_dns_gethostbyname_r`
- `_nss_dns_getnetbyaddr_r`
- `_nss_dns_getnetbyname_r`
- `_nss_files_endaliasent`
- `_nss_files_endetherent`
- `_nss_files_endgrent`
- `_nss_files_endhostent`
- `_nss_files_endnetent`
- `_nss_files_endnetgrent`
- `_nss_files_endprotoent`
- `_nss_files_endpwent`
- `_nss_files_endrpcent`
- `_nss_files_endservent`
- `_nss_files_endsgent`
- `_nss_files_endspent`
- `_nss_files_getaliasbyname_r`
- `_nss_files_getaliasent_r`
- `_nss_files_getetherent_r`
- `_nss_files_getgrent_r`
- `_nss_files_getgrgid_r`
- `_nss_files_getgrnam_r`
- `_nss_files_gethostbyaddr_r`
- `_nss_files_gethostbyname2_r`
- `_nss_files_gethostbyname3_r`
- `_nss_files_gethostbyname4_r`
- `_nss_files_gethostbyname_r`
- `_nss_files_gethostent_r`
- `_nss_files_gethostton_r`
- `_nss_files_getnetbyaddr_r`
- `_nss_files_getnetbyname_r`
- `_nss_files_getnetent_r`
- `_nss_files_getnetgrent_r`
- `_nss_files_getntohost_r`
- `_nss_files_getprotobyname_r`
- `_nss_files_getprotobynumber_r`
- `_nss_files_getprotoent_r`
- `_nss_files_getpwent_r`
- `_nss_files_getpwnam_r`
- `_nss_files_getpwuid_r`
- `_nss_files_getrpcbyname_r`
- `_nss_files_getrpcbynumber_r`
- `_nss_files_getrpcent_r`
- `_nss_files_getservbyname_r`
- `_nss_files_getservbyport_r`
- `_nss_files_getservent_r`
- `_nss_files_getsgent_r`
- `_nss_files_getsgnam_r`
- `_nss_files_getspent_r`
- `_nss_files_getspnam_r`
- `_nss_files_init`
- `_nss_files_initgroups_dyn`
- `_nss_files_parse_etherent`
- `_nss_files_parse_grent`
- `_nss_files_parse_netent`
- `_nss_files_parse_protoent`
- `_nss_files_parse_pwent`
- `_nss_files_parse_rpcent`
- `_nss_files_parse_servent`
- `_nss_files_parse_sgent`
- `_nss_files_parse_spent`
- `_nss_files_setaliasent`
- `_nss_files_setetherent`
- `_nss_files_setgrent`
- `_nss_files_sethostent`
- `_nss_files_setnetent`
- `_nss_files_setnetgrent`
- `_nss_files_setprotoent`
- `_nss_files_setpwent`
- `_nss_files_setrpcent`
- `_nss_files_setservent`
- `_nss_files_setsgent`
- `_nss_files_setspent`
- `_nss_netgroup_parseline`
- `_null_auth`
- `_obstack`
- `_obstack_allocated_p`
- `_obstack_begin`
- `_obstack_begin_1`
- `_obstack_free`
- `_obstack_memory_used`
- `_obstack_newchunk`
- `_pthread_cleanup_pop_restore`
- `_pthread_cleanup_push_defer`
- `_res`
- `_res_hconf`
- `_res_opcodes`
- `_rpc_dtablesize`
- `_seterr_reply`
- `_sethtent`
- `_sys_errlist`
- `_sys_nerr`
- `_sys_siglist`
- `_thread_db___nptl_last_event`
- `_thread_db___nptl_nthreads`
- `_thread_db___nptl_rtld_global`
- `_thread_db___pthread_keys`
- `_thread_db_const_thread_area`
- `_thread_db_dtv_dtv`
- `_thread_db_dtv_slotinfo_gen`
- `_thread_db_dtv_slotinfo_list_len`
- `_thread_db_dtv_slotinfo_list_next`
- `_thread_db_dtv_slotinfo_list_slotinfo`
- `_thread_db_dtv_slotinfo_map`
- `_thread_db_dtv_t_counter`
- `_thread_db_dtv_t_pointer_val`
- `_thread_db_link_map_l_tls_modid`
- `_thread_db_link_map_l_tls_offset`
- `_thread_db_list_t_next`
- `_thread_db_list_t_prev`
- `_thread_db_pthread_cancelhandling`
- `_thread_db_pthread_dtvp`
- `_thread_db_pthread_eventbuf`
- `_thread_db_pthread_eventbuf_eventmask`
- `_thread_db_pthread_eventbuf_eventmask_event_bits`
- `_thread_db_pthread_key_data_data`
- `_thread_db_pthread_key_data_level2_data`
- `_thread_db_pthread_key_data_seq`
- `_thread_db_pthread_key_struct_destr`
- `_thread_db_pthread_key_struct_seq`
- `_thread_db_pthread_list`
- `_thread_db_pthread_nextevent`
- `_thread_db_pthread_report_events`
- `_thread_db_pthread_schedparam_sched_priority`
- `_thread_db_pthread_schedpolicy`
- `_thread_db_pthread_specific`
- `_thread_db_pthread_start_routine`
- `_thread_db_pthread_tid`
- `_thread_db_rtld_global__dl_stack_used`
- `_thread_db_rtld_global__dl_stack_user`
- `_thread_db_rtld_global__dl_tls_dtv_slotinfo_list`
- `_thread_db_sizeof_dtv_slotinfo`
- `_thread_db_sizeof_dtv_slotinfo_list`
- `_thread_db_sizeof_list_t`
- `_thread_db_sizeof_pthread`
- `_thread_db_sizeof_pthread_key_data`
- `_thread_db_sizeof_pthread_key_data_level2`
- `_thread_db_sizeof_pthread_key_struct`
- `_thread_db_sizeof_td_eventbuf_t`
- `_thread_db_sizeof_td_thr_events_t`
- `_thread_db_td_eventbuf_t_eventdata`
- `_thread_db_td_eventbuf_t_eventnum`
- `_thread_db_td_thr_events_t_event_bits`
- `_tolower`
- `_toupper`
- `acos`
- `acosf128`
- `acosf32`
- `acosf32x`
- `acosf64`
- `acosf64x`
- `acosfN`
- `acosfNx`
- `acoshf128`
- `acoshf32`
- `acoshf32x`
- `acoshf64`
- `acoshf64x`
- `acoshfN`
- `acoshfNx`
- `acospi`
- `acospif`
- `acospif128`
- `acospif32`
- `acospif32x`
- `acospif64`
- `acospif64x`
- `acospifN`
- `acospifNx`
- `acospil`
- `addseverity`
- `advance`
- `aio_cancel64`
- `aio_error64`
- `aio_fsync64`
- `aio_init`
- `aio_read64`
- `aio_return64`
- `aio_suspend64`
- `aio_write64`
- `alphasort64`
- `arc4random`
- `arc4random_buf`
- `arc4random_uniform`
- `arch_prctl`
- `argp_err_exit_status`
- `argp_error`
- `argp_failure`
- `argp_help`
- `argp_parse`
- `argp_program_bug_address`
- `argp_program_version`
- `argp_program_version_hook`
- `argp_state_help`
- `argp_usage`
- `argz_add`
- `argz_add_sep`
- `argz_append`
- `argz_count`
- `argz_create`
- `argz_create_sep`
- `argz_delete`
- `argz_extract`
- `argz_insert`
- `argz_next`
- `argz_replace`
- `argz_stringify`
- `asinf128`
- `asinf32`
- `asinf32x`
- `asinf64`
- `asinf64x`
- `asinfN`
- `asinfNx`
- `asinhf128`
- `asinhf32`
- `asinhf32x`
- `asinhf64`
- `asinhf64x`
- `asinhfN`
- `asinhfNx`
- `asinpi`
- `asinpif`
- `asinpif128`
- `asinpif32`
- `asinpif32x`
- `asinpif64`
- `asinpif64x`
- `asinpifN`
- `asinpifNx`
- `asinpil`
- `atan2f128`
- `atan2f32`
- `atan2f32x`
- `atan2f64`
- `atan2f64x`
- `atan2fN`
- `atan2fNx`
- `atan2pi`
- `atan2pif`
- `atan2pif128`
- `atan2pif32`
- `atan2pif32x`
- `atan2pif64`
- `atan2pif64x`
- `atan2pifN`
- `atan2pifNx`
- `atan2pil`
- `atanf128`
- `atanf32`
- `atanf32x`
- `atanf64`
- `atanf64x`
- `atanfN`
- `atanfNx`
- `atanhf128`
- `atanhf32`
- `atanhf32x`
- `atanhf64`
- `atanhf64x`
- `atanhfN`
- `atanhfNx`
- `atanpi`
- `atanpif`
- `atanpif128`
- `atanpif32`
- `atanpif32x`
- `atanpif64`
- `atanpif64x`
- `atanpifN`
- `atanpifNx`
- `atanpil`
- `authdes_create`
- `authdes_getucred`
- `authdes_pk_create`
- `authnone_create`
- `authunix_create`
- `authunix_create_default`
- `backtrace`
- `backtrace_symbols`
- `backtrace_symbols_fd`
- `bdflush`
- `bindresvport`
- `bsd_signal`
- `c8rtomb`
- `cabsf128`
- `cabsf32`
- `cabsf32x`
- `cabsf64`
- `cabsf64x`
- `cabsfN`
- `cabsfNx`
- `cacosf128`
- `cacosf32`
- `cacosf32x`
- `cacosf64`
- `cacosf64x`
- `cacosfN`
- `cacosfNx`
- `cacoshf128`
- `cacoshf32`
- `cacoshf32x`
- `cacoshf64`
- `cacoshf64x`
- `cacoshfN`
- `cacoshfNx`
- `callrpc`
- `canonicalize`
- `canonicalize_file_name`
- `canonicalizef`
- `canonicalizef128`
- `canonicalizef32`
- `canonicalizef32x`
- `canonicalizef64`
- `canonicalizef64x`
- `canonicalizefN`
- `canonicalizefNx`
- `canonicalizel`
- `capget`
- `capset`
- `cargf128`
- `cargf32`
- `cargf32x`
- `cargf64`
- `cargf64x`
- `cargfN`
- `cargfNx`
- `casinf128`
- `casinf32`
- `casinf32x`
- `casinf64`
- `casinf64x`
- `casinfN`
- `casinfNx`
- `casinhf128`
- `casinhf32`
- `casinhf32x`
- `casinhf64`
- `casinhf64x`
- `casinhfN`
- `casinhfNx`
- `catanf128`
- `catanf32`
- `catanf32x`
- `catanf64`
- `catanf64x`
- `catanfN`
- `catanfNx`
- `catanhf128`
- `catanhf32`
- `catanhf32x`
- `catanhf64`
- `catanhf64x`
- `catanhfN`
- `catanhfNx`
- `cbc_crypt`
- `cbrtf128`
- `cbrtf32`
- `cbrtf32x`
- `cbrtf64`
- `cbrtf64x`
- `cbrtfN`
- `cbrtfNx`
- `ccosf128`
- `ccosf32`
- `ccosf32x`
- `ccosf64`
- `ccosf64x`
- `ccosfN`
- `ccosfNx`
- `ccoshf128`
- `ccoshf32`
- `ccoshf32x`
- `ccoshf64`
- `ccoshf64x`
- `ccoshfN`
- `ccoshfNx`
- `ceilf128`
- `ceilf32`
- `ceilf32x`
- `ceilf64`
- `ceilf64x`
- `ceilfN`
- `ceilfNx`
- `cexpf128`
- `cexpf32`
- `cexpf32x`
- `cexpf64`
- `cexpf64x`
- `cexpfN`
- `cexpfNx`
- `cfgetibaud`
- `cfgetobaud`
- `cfree`
- `cfsetbaud`
- `cfsetibaud`
- `cfsetobaud`
- `chflags`
- `cimagf128`
- `cimagf32`
- `cimagf32x`
- `cimagf64`
- `cimagf64x`
- `cimagfN`
- `cimagfNx`
- `clnt_broadcast`
- `clnt_create`
- `clnt_pcreateerror`
- `clnt_perrno`
- `clnt_perror`
- `clnt_spcreateerror`
- `clnt_sperrno`
- `clnt_sperror`
- `clntraw_create`
- `clnttcp_create`
- `clntudp_bufcreate`
- `clntudp_create`
- `clntunix_create`
- `clog10`
- `clog10f`
- `clog10f128`
- `clog10f32`
- `clog10f32x`
- `clog10f64`
- `clog10f64x`
- `clog10fN`
- `clog10fNx`
- `clog10l`
- `clogf128`
- `clogf32`
- `clogf32x`
- `clogf64`
- `clogf64x`
- `clogfN`
- `clogfNx`
- `close_range`
- `closefrom`
- `compoundn`
- `compoundnf`
- `compoundnfN`
- `compoundnfNx`
- `compoundnl`
- `conjf128`
- `conjf32`
- `conjf32x`
- `conjf64`
- `conjf64x`
- `conjfN`
- `conjfNx`
- `copysignf128`
- `copysignf32`
- `copysignf32x`
- `copysignf64`
- `copysignf64x`
- `copysignfN`
- `copysignfNx`
- `cosf128`
- `cosf32`
- `cosf32x`
- `cosf64`
- `cosf64x`
- `cosfN`
- `cosfNx`
- `coshf128`
- `coshf32`
- `coshf32x`
- `coshf64`
- `coshf64x`
- `coshfN`
- `coshfNx`
- `cospi`
- `cospif`
- `cospif128`
- `cospif32`
- `cospif32x`
- `cospif64`
- `cospif64x`
- `cospifN`
- `cospifNx`
- `cospil`
- `cpowf128`
- `cpowf32`
- `cpowf32x`
- `cpowf64`
- `cpowf64x`
- `cpowfN`
- `cpowfNx`
- `cprojf128`
- `cprojf32`
- `cprojf32x`
- `cprojf64`
- `cprojf64x`
- `cprojfN`
- `cprojfNx`
- `crealf128`
- `crealf32`
- `crealf32x`
- `crealf64`
- `crealf64x`
- `crealfN`
- `crealfNx`
- `creat64`
- `create_module`
- `crypt_checksalt`
- `crypt_gensalt`
- `crypt_gensalt_r`
- `crypt_gensalt_ra`
- `crypt_gensalt_rn`
- `crypt_preferred_method`
- `crypt_ra`
- `crypt_rn`
- `csinf128`
- `csinf32`
- `csinf32x`
- `csinf64`
- `csinf64x`
- `csinfN`
- `csinfNx`
- `csinhf128`
- `csinhf32`
- `csinhf32x`
- `csinhf64`
- `csinhf64x`
- `csinhfN`
- `csinhfNx`
- `csqrtf128`
- `csqrtf32`
- `csqrtf32x`
- `csqrtf64`
- `csqrtf64x`
- `csqrtfN`
- `csqrtfNx`
- `ctanf128`
- `ctanf32`
- `ctanf32x`
- `ctanf64`
- `ctanf64x`
- `ctanfN`
- `ctanfNx`
- `ctanhf128`
- `ctanhf32`
- `ctanhf32x`
- `ctanhf64`
- `ctanhf64x`
- `ctanhfN`
- `ctanhfNx`
- `daddl`
- `ddivl`
- `delete_module`
- `des_setparity`
- `dfmal`
- `dladdr1`
- `dlmopen`
- `dlvsym`
- `dmull`
- `drand48_r`
- `dreml`
- `dsqrtl`
- `dsubl`
- `dysize`
- `ecb_crypt`
- `ecvt_r`
- `encrypt_r`
- `endaliasent`
- `endfsent`
- `endnetgrent`
- `endrpcent`
- `endsgent`
- `endttyent`
- `envz_add`
- `envz_entry`
- `envz_get`
- `envz_merge`
- `envz_remove`
- `envz_strip`
- `epoll_pwait2`
- `erand48_r`
- `erfcf128`
- `erfcf32`
- `erfcf32x`
- `erfcf64`
- `erfcf64x`
- `erfcfN`
- `erfcfNx`
- `erff128`
- `erff32`
- `erff32x`
- `erff64`
- `erff64x`
- `erffN`
- `erffNx`
- `errno`
- `error`
- `error_at_line`
- `error_message_count`
- `error_one_per_line`
- `error_print_progname`
- `execveat`
- `exp10f128`
- `exp10f32`
- `exp10f32x`
- `exp10f64`
- `exp10f64x`
- `exp10fN`
- `exp10fNx`
- `exp10m1`
- `exp10m1f`
- `exp10m1f128`
- `exp10m1f32`
- `exp10m1f32x`
- `exp10m1f64`
- `exp10m1f64x`
- `exp10m1fN`
- `exp10m1fNx`
- `exp10m1l`
- `exp2f128`
- `exp2f32`
- `exp2f32x`
- `exp2f64`
- `exp2f64x`
- `exp2fN`
- `exp2fNx`
- `exp2m1`
- `exp2m1f`
- `exp2m1f128`
- `exp2m1f32`
- `exp2m1f32x`
- `exp2m1f64`
- `exp2m1f64x`
- `exp2m1fN`
- `exp2m1fNx`
- `exp2m1l`
- `expf128`
- `expf32`
- `expf32x`
- `expf64`
- `expf64x`
- `expfN`
- `expfNx`
- `expm1f128`
- `expm1f32`
- `expm1f32x`
- `expm1f64`
- `expm1f64x`
- `expm1fN`
- `expm1fNx`
- `f32addf128`
- `f32addf32x`
- `f32addf64`
- `f32addf64x`
- `f32divf128`
- `f32divf32x`
- `f32divf64`
- `f32divf64x`
- `f32fmaf128`
- `f32fmaf32x`
- `f32fmaf64`
- `f32fmaf64x`
- `f32mulf128`
- `f32mulf32x`
- `f32mulf64`
- `f32mulf64x`
- `f32sqrtf128`
- `f32sqrtf32x`
- `f32sqrtf64`
- `f32sqrtf64x`
- `f32subf128`
- `f32subf32x`
- `f32subf64`
- `f32subf64x`
- `f32xaddf128`
- `f32xaddf64`
- `f32xaddf64x`
- `f32xdivf128`
- `f32xdivf64`
- `f32xdivf64x`
- `f32xfmaf128`
- `f32xfmaf64`
- `f32xfmaf64x`
- `f32xmulf128`
- `f32xmulf64`
- `f32xmulf64x`
- `f32xsqrtf128`
- `f32xsqrtf64`
- `f32xsqrtf64x`
- `f32xsubf128`
- `f32xsubf64`
- `f32xsubf64x`
- `f64addf128`
- `f64addf64x`
- `f64divf128`
- `f64divf64x`
- `f64fmaf128`
- `f64fmaf64x`
- `f64mulf128`
- `f64mulf64x`
- `f64sqrtf128`
- `f64sqrtf64x`
- `f64subf128`
- `f64subf64x`
- `f64xaddf128`
- `f64xdivf128`
- `f64xfmaf128`
- `f64xmulf128`
- `f64xsqrtf128`
- `f64xsubf128`
- `fMaddfN`
- `fMaddfNx`
- `fMdivfN`
- `fMdivfNx`
- `fMfmafN`
- `fMfmafNx`
- `fMmulfN`
- `fMmulfNx`
- `fMsqrtfN`
- `fMsqrtfNx`
- `fMsubfN`
- `fMsubfNx`
- `fMxaddfN`
- `fMxaddfNx`
- `fMxdivfN`
- `fMxdivfNx`
- `fMxfmafN`
- `fMxfmafNx`
- `fMxmulfN`
- `fMxmulfNx`
- `fMxsqrtfN`
- `fMxsqrtfNx`
- `fMxsubfN`
- `fMxsubfNx`
- `fabsf128`
- `fabsf32`
- `fabsf32x`
- `fabsf64`
- `fabsf64x`
- `fabsfN`
- `fabsfNx`
- `fadd`
- `faddl`
- `fallocate64`
- `fattach`
- `fchflags`
- `fcloseall`
- `fcntl64`
- `fcrypt`
- `fcvt_r`
- `fdetach`
- `fdimf128`
- `fdimf32`
- `fdimf32x`
- `fdimf64`
- `fdimf64x`
- `fdimfN`
- `fdimfNx`
- `fdiv`
- `fdivl`
- `fedisableexcept`
- `feenableexcept`
- `fegetexcept`
- `fegetmode`
- `fesetexcept`
- `fesetmode`
- `fetestexceptflag`
- `ffma`
- `ffmal`
- `fgetgrent_r`
- `fgetpos64`
- `fgetpwent_r`
- `fgetsgent`
- `fgetsgent_r`
- `fgetspent_r`
- `finitel`
- `floorf128`
- `floorf32`
- `floorf32x`
- `floorf64`
- `floorf64x`
- `floorfN`
- `floorfNx`
- `fmaf128`
- `fmaf32`
- `fmaf32x`
- `fmaf64`
- `fmaf64x`
- `fmafN`
- `fmafNx`
- `fmaxf128`
- `fmaxf32`
- `fmaxf32x`
- `fmaxf64`
- `fmaxf64x`
- `fmaxfN`
- `fmaxfNx`
- `fmaximum`
- `fmaximum_mag`
- `fmaximum_mag_num`
- `fmaximum_mag_numf`
- `fmaximum_mag_numf128`
- `fmaximum_mag_numf32`
- `fmaximum_mag_numf32x`
- `fmaximum_mag_numf64`
- `fmaximum_mag_numf64x`
- `fmaximum_mag_numfN`
- `fmaximum_mag_numfNx`
- `fmaximum_mag_numl`
- `fmaximum_magf`
- `fmaximum_magf128`
- `fmaximum_magf32`
- `fmaximum_magf32x`
- `fmaximum_magf64`
- `fmaximum_magf64x`
- `fmaximum_magfN`
- `fmaximum_magfNx`
- `fmaximum_magl`
- `fmaximum_num`
- `fmaximum_numf`
- `fmaximum_numf128`
- `fmaximum_numf32`
- `fmaximum_numf32x`
- `fmaximum_numf64`
- `fmaximum_numf64x`
- `fmaximum_numfN`
- `fmaximum_numfNx`
- `fmaximum_numl`
- `fmaximumf`
- `fmaximumf128`
- `fmaximumf32`
- `fmaximumf32x`
- `fmaximumf64`
- `fmaximumf64x`
- `fmaximumfN`
- `fmaximumfNx`
- `fmaximuml`
- `fmaxmag`
- `fmaxmagf`
- `fmaxmagf128`
- `fmaxmagf32`
- `fmaxmagf32x`
- `fmaxmagf64`
- `fmaxmagf64x`
- `fmaxmagfN`
- `fmaxmagfNx`
- `fmaxmagl`
- `fminf128`
- `fminf32`
- `fminf32x`
- `fminf64`
- `fminf64x`
- `fminfN`
- `fminfNx`
- `fminimum`
- `fminimum_mag`
- `fminimum_mag_num`
- `fminimum_mag_numf`
- `fminimum_mag_numf128`
- `fminimum_mag_numf32`
- `fminimum_mag_numf32x`
- `fminimum_mag_numf64`
- `fminimum_mag_numf64x`
- `fminimum_mag_numfN`
- `fminimum_mag_numfNx`
- `fminimum_mag_numl`
- `fminimum_magf`
- `fminimum_magf128`
- `fminimum_magf32`
- `fminimum_magf32x`
- `fminimum_magf64`
- `fminimum_magf64x`
- `fminimum_magfN`
- `fminimum_magfNx`
- `fminimum_magl`
- `fminimum_num`
- `fminimum_numf`
- `fminimum_numf128`
- `fminimum_numf32`
- `fminimum_numf32x`
- `fminimum_numf64`
- `fminimum_numf64x`
- `fminimum_numfN`
- `fminimum_numfNx`
- `fminimum_numl`
- `fminimumf`
- `fminimumf128`
- `fminimumf32`
- `fminimumf32x`
- `fminimumf64`
- `fminimumf64x`
- `fminimumfN`
- `fminimumfNx`
- `fminimuml`
- `fminmag`
- `fminmagf`
- `fminmagf128`
- `fminmagf32`
- `fminmagf32x`
- `fminmagf64`
- `fminmagf64x`
- `fminmagfN`
- `fminmagfNx`
- `fminmagl`
- `fmodf128`
- `fmodf32`
- `fmodf32x`
- `fmodf64`
- `fmodf64x`
- `fmodfN`
- `fmodfNx`
- `fmul`
- `fmull`
- `fopen64`
- `free_aligned_sized`
- `free_sized`
- `freopen64`
- `frexpf128`
- `frexpf32`
- `frexpf32x`
- `frexpf64`
- `frexpf64x`
- `frexpfN`
- `frexpfNx`
- `fromfp`
- `fromfpf`
- `fromfpf128`
- `fromfpf32`
- `fromfpf32x`
- `fromfpf64`
- `fromfpf64x`
- `fromfpfN`
- `fromfpfNx`
- `fromfpl`
- `fromfpx`
- `fromfpxf`
- `fromfpxf128`
- `fromfpxf32`
- `fromfpxf32x`
- `fromfpxf64`
- `fromfpxf64x`
- `fromfpxfN`
- `fromfpxfNx`
- `fromfpxl`
- `fsconfig`
- `fseeko64`
- `fsetpos64`
- `fsmount`
- `fsopen`
- `fspick`
- `fsqrt`
- `fsqrtl`
- `fstat64`
- `fstatat64`
- `fstatfs64`
- `fstatvfs64`
- `fsub`
- `fsubl`
- `ftello64`
- `ftruncate64`
- `fts64_children`
- `fts64_close`
- `fts64_open`
- `fts64_read`
- `fts64_set`
- `fts_children`
- `fts_close`
- `fts_open`
- `fts_read`
- `fts_set`
- `ftw64`
- `gai_cancel`
- `gai_error`
- `gai_suspend`
- `gamma`
- `gammaf`
- `gammal`
- `get_kernel_syms`
- `get_myaddress`
- `getaddrinfo_a`
- `getaliasbyname`
- `getaliasbyname_r`
- `getaliasent`
- `getaliasent_r`
- `getcpu`
- `getdate_err`
- `getdate_r`
- `getdents64`
- `getdirentries`
- `getdirentries64`
- `getfsent`
- `getfsfile`
- `getfsspec`
- `getgrent_r`
- `gethostent_r`
- `getipv4sourcefilter`
- `getmsg`
- `getnetbyaddr_r`
- `getnetbyname_r`
- `getnetent_r`
- `getnetgrent`
- `getnetgrent_r`
- `getnetname`
- `getpayload`
- `getpayloadf`
- `getpayloadf128`
- `getpayloadf32`
- `getpayloadf32x`
- `getpayloadf64`
- `getpayloadf64x`
- `getpayloadfN`
- `getpayloadfNx`
- `getpayloadl`
- `getpmsg`
- `getprotobyname_r`
- `getprotobynumber_r`
- `getprotoent_r`
- `getpt`
- `getpublickey`
- `getpw`
- `getpwent_r`
- `getrlimit64`
- `getrpcbyname`
- `getrpcbyname_r`
- `getrpcbynumber`
- `getrpcbynumber_r`
- `getrpcent`
- `getrpcent_r`
- `getrpcport`
- `getsecretkey`
- `getservent_r`
- `getsgent`
- `getsgent_r`
- `getsgnam`
- `getsgnam_r`
- `getsourcefilter`
- `getspent_r`
- `getttyent`
- `getttynam`
- `getumask`
- `getutent_r`
- `getutid_r`
- `getutline_r`
- `getutmp`
- `getutmpx`
- `getwd`
- `glob64`
- `glob_pattern_p`
- `globfree64`
- `gnu_dev_major`
- `gnu_dev_makedev`
- `gnu_dev_minor`
- `gnu_get_libc_release`
- `gnu_get_libc_version`
- `group_member`
- `gsignal`
- `gtty`
- `h_errlist`
- `h_nerr`
- `host2netname`
- `hypotf128`
- `hypotf32`
- `hypotf32x`
- `hypotf64`
- `hypotf64x`
- `hypotfN`
- `hypotfNx`
- `ilogbf128`
- `ilogbf32`
- `ilogbf32x`
- `ilogbf64`
- `ilogbf64x`
- `ilogbfN`
- `ilogbfNx`
- `inet6_opt_append`
- `inet6_opt_find`
- `inet6_opt_finish`
- `inet6_opt_get_val`
- `inet6_opt_init`
- `inet6_opt_next`
- `inet6_opt_set_val`
- `inet6_option_alloc`
- `inet6_option_append`
- `inet6_option_find`
- `inet6_option_init`
- `inet6_option_next`
- `inet6_option_space`
- `inet6_rth_add`
- `inet6_rth_getaddr`
- `inet6_rth_init`
- `inet6_rth_reverse`
- `inet6_rth_segments`
- `inet6_rth_space`
- `inet_net_ntop`
- `inet_net_pton`
- `inet_neta`
- `inet_nsap_addr`
- `inet_nsap_ntoa`
- `init_module`
- `initstate_r`
- `innetgr`
- `iruserok`
- `iruserok_af`
- `isalnum_l`
- `isctype`
- `isfdtype`
- `isinf`
- `isinff`
- `isinfl`
- `isnan`
- `isnanf`
- `isnanl`
- `j0f128`
- `j0f32`
- `j0f32x`
- `j0f64`
- `j0f64x`
- `j0fN`
- `j0fNx`
- `j0l`
- `j1f128`
- `j1f32`
- `j1f32x`
- `j1f64`
- `j1f64x`
- `j1fN`
- `j1fNx`
- `j1l`
- `jnf128`
- `jnf32`
- `jnf32x`
- `jnf64`
- `jnf64x`
- `jnfN`
- `jnfNx`
- `jnl`
- `jrand48_r`
- `key_decryptsession`
- `key_decryptsession_pk`
- `key_encryptsession`
- `key_encryptsession_pk`
- `key_gendes`
- `key_get_conv`
- `key_secretkey_is_set`
- `key_setnet`
- `key_setsecret`
- `lcong48_r`
- `ldexpf128`
- `ldexpf32`
- `ldexpf32x`
- `ldexpf64`
- `ldexpf64x`
- `ldexpfN`
- `ldexpfNx`
- `lgammaf128`
- `lgammaf128_r`
- `lgammaf32`
- `lgammaf32_r`
- `lgammaf32x`
- `lgammaf32x_r`
- `lgammaf64`
- `lgammaf64_r`
- `lgammaf64x`
- `lgammaf64x_r`
- `lgammafN`
- `lgammafN_r`
- `lgammafNx`
- `lgammafNx_r`
- `lio_listio64`
- `llogb`
- `llogbf`
- `llogbf128`
- `llogbf32`
- `llogbf32x`
- `llogbf64`
- `llogbf64x`
- `llogbfN`
- `llogbfNx`
- `llogbl`
- `llrintf128`
- `llrintf32`
- `llrintf32x`
- `llrintf64`
- `llrintf64x`
- `llrintfN`
- `llrintfNx`
- `llroundf128`
- `llroundf32`
- `llroundf32x`
- `llroundf64`
- `llroundf64x`
- `llroundfN`
- `llroundfNx`
- `llseek`
- `loc1`
- `loc2`
- `lockf64`
- `locs`
- `log10f128`
- `log10f32`
- `log10f32x`
- `log10f64`
- `log10f64x`
- `log10fN`
- `log10fNx`
- `log10p1`
- `log10p1f`
- `log10p1f128`
- `log10p1f32`
- `log10p1f32x`
- `log10p1f64`
- `log10p1f64x`
- `log10p1fN`
- `log10p1fNx`
- `log10p1l`
- `log1pf128`
- `log1pf32`
- `log1pf32x`
- `log1pf64`
- `log1pf64x`
- `log1pfN`
- `log1pfNx`
- `log2f128`
- `log2f32`
- `log2f32x`
- `log2f64`
- `log2f64x`
- `log2fN`
- `log2fNx`
- `log2p1`
- `log2p1f`
- `log2p1f128`
- `log2p1f32`
- `log2p1f32x`
- `log2p1f64`
- `log2p1f64x`
- `log2p1fN`
- `log2p1fNx`
- `log2p1l`
- `logbf128`
- `logbf32`
- `logbf32x`
- `logbf64`
- `logbf64x`
- `logbfN`
- `logbfNx`
- `logf128`
- `logf32`
- `logf32x`
- `logf64`
- `logf64x`
- `logfN`
- `logfNx`
- `login`
- `logout`
- `logp1`
- `logp1f`
- `logp1f128`
- `logp1f32`
- `logp1f32x`
- `logp1f64`
- `logp1f64x`
- `logp1fN`
- `logp1fNx`
- `logp1l`
- `logwtmp`
- `lrand48_r`
- `lrintf128`
- `lrintf32`
- `lrintf32x`
- `lrintf64`
- `lrintf64x`
- `lrintfN`
- `lrintfNx`
- `lroundf128`
- `lroundf32`
- `lroundf32x`
- `lroundf64`
- `lroundf64x`
- `lroundfN`
- `lroundfNx`
- `lseek64`
- `lstat64`
- `mallinfo`
- `mallinfo2`
- `malloc_info`
- `malloc_stats`
- `malloc_trim`
- `mallopt`
- `mallwatch`
- `matherr`
- `mbrtoc8`
- `mcheck`
- `mcheck_check_all`
- `mcheck_pedantic`
- `mcount`
- `memalignment`
- `memfrob`
- `memset_explicit`
- `mkostemp64`
- `mkostemps64`
- `mkstemp64`
- `mkstemps64`
- `mmap64`
- `modff128`
- `modff32`
- `modff32x`
- `modff64`
- `modff64x`
- `modffN`
- `modffNx`
- `modify_ldt`
- `moncontrol`
- `monstartup`
- `mount_setattr`
- `move_mount`
- `mprobe`
- `mrand48_r`
- `mseal`
- `mtrace`
- `muntrace`
- `nanf128`
- `nanf32`
- `nanf32x`
- `nanf64`
- `nanf64x`
- `nanfN`
- `nanfNx`
- `nearbyintf128`
- `nearbyintf32`
- `nearbyintf32x`
- `nearbyintf64`
- `nearbyintf64x`
- `nearbyintfN`
- `nearbyintfNx`
- `netname2host`
- `netname2user`
- `nextafterf128`
- `nextafterf32`
- `nextafterf32x`
- `nextafterf64`
- `nextafterf64x`
- `nextafterfN`
- `nextafterfNx`
- `nextdown`
- `nextdownf`
- `nextdownf128`
- `nextdownf32`
- `nextdownf32x`
- `nextdownf64`
- `nextdownf64x`
- `nextdownfN`
- `nextdownfNx`
- `nextdownl`
- `nextup`
- `nextupf`
- `nextupf128`
- `nextupf32`
- `nextupf32x`
- `nextupf64`
- `nextupf64x`
- `nextupfN`
- `nextupfNx`
- `nextupl`
- `nfsservctl`
- `nftw64`
- `nis_add`
- `nis_add_entry`
- `nis_addmember`
- `nis_checkpoint`
- `nis_clone_directory`
- `nis_clone_object`
- `nis_clone_result`
- `nis_creategroup`
- `nis_destroy_object`
- `nis_destroygroup`
- `nis_dir_cmp`
- `nis_domain_of`
- `nis_domain_of_r`
- `nis_first_entry`
- `nis_free_directory`
- `nis_free_object`
- `nis_free_request`
- `nis_freenames`
- `nis_freeresult`
- `nis_freeservlist`
- `nis_freetags`
- `nis_getnames`
- `nis_getservlist`
- `nis_ismember`
- `nis_leaf_of`
- `nis_leaf_of_r`
- `nis_lerror`
- `nis_list`
- `nis_local_directory`
- `nis_local_group`
- `nis_local_host`
- `nis_local_principal`
- `nis_lookup`
- `nis_mkdir`
- `nis_modify`
- `nis_modify_entry`
- `nis_name_of`
- `nis_name_of_r`
- `nis_next_entry`
- `nis_perror`
- `nis_ping`
- `nis_print_directory`
- `nis_print_entry`
- `nis_print_group`
- `nis_print_group_entry`
- `nis_print_link`
- `nis_print_object`
- `nis_print_result`
- `nis_print_rights`
- `nis_print_table`
- `nis_read_obj`
- `nis_remove`
- `nis_remove_entry`
- `nis_removemember`
- `nis_rmdir`
- `nis_servstate`
- `nis_sperrno`
- `nis_sperror`
- `nis_sperror_r`
- `nis_stats`
- `nis_verifygroup`
- `nis_write_obj`
- `nrand48_r`
- `ns_datetosecs`
- `ns_format_ttl`
- `ns_makecanon`
- `ns_msg_getflag`
- `ns_name_compress`
- `ns_name_ntol`
- `ns_name_ntop`
- `ns_name_pack`
- `ns_name_pton`
- `ns_name_rollback`
- `ns_name_skip`
- `ns_name_unpack`
- `ns_parse_ttl`
- `ns_samedomain`
- `ns_samename`
- `ns_sprintrr`
- `ns_sprintrrf`
- `ns_subdomain`
- `ntp_adjtime`
- `ntp_gettime`
- `ntp_gettimex`
- `obstack_1grow`
- `obstack_1grow_fast`
- `obstack_alloc`
- `obstack_alloc_failed_handler`
- `obstack_base`
- `obstack_blank`
- `obstack_blank_fast`
- `obstack_copy`
- `obstack_copy0`
- `obstack_exit_failure`
- `obstack_finish`
- `obstack_free`
- `obstack_grow`
- `obstack_grow0`
- `obstack_init`
- `obstack_int_grow`
- `obstack_int_grow_fast`
- `obstack_next_free`
- `obstack_object_size`
- `obstack_printf`
- `obstack_ptr_grow`
- `obstack_ptr_grow_fast`
- `obstack_room`
- `obstack_vprintf`
- `on_exit`
- `open64`
- `open_tree`
- `openat2`
- `openat64`
- `optarg`
- `opterr`
- `optind`
- `optopt`
- `parse_printf_format`
- `passwd2des`
- `pidfd_getfd`
- `pidfd_getpid`
- `pidfd_open`
- `pidfd_send_signal`
- `pidfd_spawn`
- `pidfd_spawnp`
- `pivot_root`
- `pkey_alloc`
- `pkey_free`
- `pkey_get`
- `pkey_mprotect`
- `pkey_set`
- `pmap_getmaps`
- `pmap_getport`
- `pmap_rmtcall`
- `pmap_set`
- `pmap_unset`
- `posix_fadvise64`
- `posix_fallocate64`
- `posix_spawn_file_actions_addclosefrom_np`
- `posix_spawn_file_actions_addtcsetpgrp_np`
- `posix_spawnattr_getcgroup_np`
- `posix_spawnattr_setcgroup_np`
- `powf128`
- `powf32`
- `powf32x`
- `powf64`
- `powf64x`
- `powfN`
- `powfNx`
- `pown`
- `pownf`
- `pownfN`
- `pownfNx`
- `pownl`
- `powr`
- `powrf`
- `powrfN`
- `powrfNx`
- `powrl`
- `pread64`
- `preadv64`
- `preadv64v2`
- `printf_size`
- `printf_size_info`
- `prlimit64`
- `process_madvise`
- `process_mrelease`
- `profil`
- `pthread_attr_getaffinity_np`
- `pthread_attr_getsigmask_np`
- `pthread_attr_getstackaddr`
- `pthread_attr_setaffinity_np`
- `pthread_attr_setsigmask_np`
- `pthread_attr_setstackaddr`
- `pthread_clockjoin_np`
- `pthread_cond_clockwait`
- `pthread_gettid_np`
- `pthread_kill_other_threads_np`
- `pthread_mutex_clocklock`
- `pthread_mutex_consistent_np`
- `pthread_mutexattr_getkind_np`
- `pthread_mutexattr_getrobust_np`
- `pthread_mutexattr_setkind_np`
- `pthread_mutexattr_setrobust_np`
- `pthread_rwlock_clockrdlock`
- `pthread_rwlock_clockwrlock`
- `pthread_rwlockattr_getkind_np`
- `pthread_rwlockattr_setkind_np`
- `pthread_self`
- `pthread_sigqueue`
- `pthread_yield`
- `putmsg`
- `putpmsg`
- `putsgent`
- `pvalloc`
- `pwrite64`
- `pwritev64`
- `pwritev64v2`
- `qecvt`
- `qecvt_r`
- `qfcvt`
- `qfcvt_r`
- `qgcvt`
- `query_module`
- `random_r`
- `rawmemchr`
- `rcmd`
- `rcmd_af`
- `re_comp`
- `re_compile_fastmap`
- `re_compile_pattern`
- `re_exec`
- `re_match`
- `re_match_2`
- `re_max_failures`
- `re_search`
- `re_search_2`
- `re_set_registers`
- `re_set_syntax`
- `re_syntax_options`
- `readColdStartFile`
- `readdir64`
- `readdir64_r`
- `register_printf_function`
- `register_printf_modifier`
- `register_printf_specifier`
- `register_printf_type`
- `registerrpc`
- `remainderf128`
- `remainderf32`
- `remainderf32x`
- `remainderf64`
- `remainderf64x`
- `remainderfN`
- `remainderfNx`
- `remquof128`
- `remquof32`
- `remquof32x`
- `remquof64`
- `remquof64x`
- `renameat2`
- `res_dnok`
- `res_gethostbyaddr`
- `res_gethostbyname`
- `res_gethostbyname2`
- `res_hnok`
- `res_mailok`
- `res_nmkquery`
- `res_nquery`
- `res_nquerydomain`
- `res_nsearch`
- `res_nsend`
- `res_ownok`
- `res_send_setqhook`
- `res_send_setrhook`
- `revoke`
- `rexec`
- `rexec_af`
- `rexecoptions`
- `rintf128`
- `rintf32`
- `rintf32x`
- `rintf64`
- `rintf64x`
- `rintfN`
- `rintfNx`
- `rootn`
- `rootnf`
- `rootnfN`
- `rootnfNx`
- `rootnl`
- `roundeven`
- `roundevenf`
- `roundevenf128`
- `roundevenf32`
- `roundevenf32x`
- `roundevenf64`
- `roundevenf64x`
- `roundevenfN`
- `roundevenfNx`
- `roundevenl`
- `roundf128`
- `roundf32`
- `roundf32x`
- `roundf64`
- `roundf64x`
- `roundfN`
- `roundfNx`
- `rpc_createerr`
- `rpmatch`
- `rresvport`
- `rresvport_af`
- `rsqrt`
- `rsqrtf`
- `rsqrtfN`
- `rsqrtfNx`
- `rsqrtl`
- `rtime`
- `ruserok`
- `ruserok_af`
- `ruserpass`
- `scalbl`
- `scalblnf128`
- `scalblnf32`
- `scalblnf32x`
- `scalblnf64`
- `scalblnf64x`
- `scalblnfN`
- `scalblnfNx`
- `scalbnf128`
- `scalbnf32`
- `scalbnf32x`
- `scalbnf64`
- `scalbnf64x`
- `scalbnfN`
- `scalbnfNx`
- `scandir64`
- `scandirat`
- `scandirat64`
- `sched_getattr`
- `sched_setattr`
- `seed48_r`
- `sem_clockwait`
- `sendfile64`
- `setaliasent`
- `setfsent`
- `sethostid`
- `setipv4sourcefilter`
- `setkey_r`
- `setlogin`
- `setnetgrent`
- `setpayload`
- `setpayloadf`
- `setpayloadf128`
- `setpayloadf32`
- `setpayloadf32x`
- `setpayloadf64`
- `setpayloadf64x`
- `setpayloadfN`
- `setpayloadfNx`
- `setpayloadl`
- `setpayloadsig`
- `setpayloadsigf`
- `setpayloadsigf128`
- `setpayloadsigf32`
- `setpayloadsigf32x`
- `setpayloadsigf64`
- `setpayloadsigf64x`
- `setpayloadsigfN`
- `setpayloadsigfNx`
- `setpayloadsigl`
- `setrlimit64`
- `setrpcent`
- `setsgent`
- `setsourcefilter`
- `setstate_r`
- `setttyent`
- `sgetsgent`
- `sgetsgent_r`
- `sgetspent_r`
- `sigabbrev_np`
- `sigblock`
- `sigdescr_np`
- `siggetmask`
- `signal`
- `signbit`
- `significandl`
- `sigreturn`
- `sigset`
- `sigsetmask`
- `sigstack`
- `sigvec`
- `sincosf128`
- `sincosf32`
- `sincosf32x`
- `sincosf64`
- `sincosf64x`
- `sincosfN`
- `sincosfNx`
- `sinf128`
- `sinf32`
- `sinf32x`
- `sinf64`
- `sinf64x`
- `sinfN`
- `sinfNx`
- `sinhf128`
- `sinhf32`
- `sinhf32x`
- `sinhf64`
- `sinhf64x`
- `sinhfN`
- `sinhfNx`
- `sinpi`
- `sinpif`
- `sinpif128`
- `sinpif32`
- `sinpif32x`
- `sinpif64`
- `sinpif64x`
- `sinpifN`
- `sinpifNx`
- `sinpil`
- `sprofil`
- `sqrtf128`
- `sqrtf32`
- `sqrtf32x`
- `sqrtf64`
- `sqrtf64x`
- `sqrtfN`
- `sqrtfNx`
- `srand48_r`
- `srandom_r`
- `ssignal`
- `sstk`
- `stat64`
- `statfs64`
- `statvfs64`
- `stdc_bit_ceil_uc`
- `stdc_bit_ceil_ui`
- `stdc_bit_ceil_ul`
- `stdc_bit_ceil_ull`
- `stdc_bit_ceil_us`
- `stdc_bit_floor_uc`
- `stdc_bit_floor_ui`
- `stdc_bit_floor_ul`
- `stdc_bit_floor_ull`
- `stdc_bit_floor_us`
- `stdc_bit_width_uc`
- `stdc_bit_width_ui`
- `stdc_bit_width_ul`
- `stdc_bit_width_ull`
- `stdc_bit_width_us`
- `stdc_count_ones_uc`
- `stdc_count_ones_ui`
- `stdc_count_ones_ul`
- `stdc_count_ones_ull`
- `stdc_count_ones_us`
- `stdc_count_zeros_uc`
- `stdc_count_zeros_ui`
- `stdc_count_zeros_ul`
- `stdc_count_zeros_ull`
- `stdc_count_zeros_us`
- `stdc_first_leading_one_uc`
- `stdc_first_leading_one_ui`
- `stdc_first_leading_one_ul`
- `stdc_first_leading_one_ull`
- `stdc_first_leading_one_us`
- `stdc_first_leading_zero_uc`
- `stdc_first_leading_zero_ui`
- `stdc_first_leading_zero_ul`
- `stdc_first_leading_zero_ull`
- `stdc_first_leading_zero_us`
- `stdc_first_trailing_one_uc`
- `stdc_first_trailing_one_ui`
- `stdc_first_trailing_one_ul`
- `stdc_first_trailing_one_ull`
- `stdc_first_trailing_one_us`
- `stdc_first_trailing_zero_uc`
- `stdc_first_trailing_zero_ui`
- `stdc_first_trailing_zero_ul`
- `stdc_first_trailing_zero_ull`
- `stdc_first_trailing_zero_us`
- `stdc_has_single_bit_uc`
- `stdc_has_single_bit_ui`
- `stdc_has_single_bit_ul`
- `stdc_has_single_bit_ull`
- `stdc_has_single_bit_us`
- `stdc_leading_ones_uc`
- `stdc_leading_ones_ui`
- `stdc_leading_ones_ul`
- `stdc_leading_ones_ull`
- `stdc_leading_ones_us`
- `stdc_leading_zeros_uc`
- `stdc_leading_zeros_ui`
- `stdc_leading_zeros_ul`
- `stdc_leading_zeros_ull`
- `stdc_leading_zeros_us`
- `stdc_trailing_ones_uc`
- `stdc_trailing_ones_ui`
- `stdc_trailing_ones_ul`
- `stdc_trailing_ones_ull`
- `stdc_trailing_ones_us`
- `stdc_trailing_zeros_uc`
- `stdc_trailing_zeros_ui`
- `stdc_trailing_zeros_ul`
- `stdc_trailing_zeros_ull`
- `stdc_trailing_zeros_us`
- `stderr`
- `stdin`
- `stdout`
- `step`
- `strerrordesc_np`
- `strerrorname_np`
- `strfromd`
- `strfromf`
- `strfromf128`
- `strfromf32`
- `strfromf32x`
- `strfromf64`
- `strfromf64x`
- `strfromfN`
- `strfromfNx`
- `strfroml`
- `strfry`
- `strptime_l`
- `strtof128`
- `strtof128_l`
- `strtof32`
- `strtof32_l`
- `strtof32x`
- `strtof32x_l`
- `strtof64`
- `strtof64_l`
- `strtof64x`
- `strtof64x_l`
- `strtofN`
- `strtofNx`
- `strtol_l`
- `strtoll_l`
- `strtoq`
- `strtoul_l`
- `strtoull_l`
- `strtouq`
- `stty`
- `svc_exit`
- `svc_fdset`
- `svc_getreq`
- `svc_getreq_common`
- `svc_getreq_poll`
- `svc_getreqset`
- `svc_max_pollfd`
- `svc_pollfd`
- `svc_register`
- `svc_run`
- `svc_sendreply`
- `svc_unregister`
- `svcauthdes_stats`
- `svcerr_auth`
- `svcerr_decode`
- `svcerr_noproc`
- `svcerr_noprog`
- `svcerr_progvers`
- `svcerr_systemerr`
- `svcerr_weakauth`
- `svcfd_create`
- `svcraw_create`
- `svctcp_create`
- `svcudp_bufcreate`
- `svcudp_create`
- `svcudp_enablecache`
- `svcunix_create`
- `svcunixfd_create`
- `sys_errlist`
- `sys_nerr`
- `sys_sigabbrev`
- `sys_siglist`
- `sysctl`
- `sysv_signal`
- `tanf128`
- `tanf32`
- `tanf32x`
- `tanf64`
- `tanf64x`
- `tanfN`
- `tanfNx`
- `tanhf128`
- `tanhf32`
- `tanhf32x`
- `tanhf64`
- `tanhf64x`
- `tanhfN`
- `tanhfNx`
- `tanpi`
- `tanpif`
- `tanpif128`
- `tanpif32`
- `tanpif32x`
- `tanpif64`
- `tanpif64x`
- `tanpifN`
- `tanpifNx`
- `tanpil`
- `tgammaf128`
- `tgammaf32`
- `tgammaf32x`
- `tgammaf64`
- `tgammaf64x`
- `tgammafN`
- `tgammafNx`
- `tgkill`
- `timelocal`
- `timespec_getres`
- `tmpfile64`
- `tmpnam_r`
- `totalorder`
- `totalorderf`
- `totalorderf128`
- `totalorderf32`
- `totalorderf32x`
- `totalorderf64`
- `totalorderf64x`
- `totalorderfN`
- `totalorderfNx`
- `totalorderl`
- `totalordermag`
- `totalordermagf`
- `totalordermagf128`
- `totalordermagf32`
- `totalordermagf32x`
- `totalordermagf64`
- `totalordermagf64x`
- `totalordermagfN`
- `totalordermagfNx`
- `totalordermagl`
- `tr_break`
- `truncate64`
- `truncf128`
- `truncf32`
- `truncf32x`
- `truncf64`
- `truncf64x`
- `truncfN`
- `truncfNx`
- `ttyslot`
- `twalk_r`
- `uabs`
- `ufromfp`
- `ufromfpf`
- `ufromfpf128`
- `ufromfpf32`
- `ufromfpf32x`
- `ufromfpf64`
- `ufromfpf64x`
- `ufromfpfN`
- `ufromfpfNx`
- `ufromfpl`
- `ufromfpx`
- `ufromfpxf`
- `ufromfpxf128`
- `ufromfpxf32`
- `ufromfpxf32x`
- `ufromfpxf64`
- `ufromfpxf64x`
- `ufromfpxfN`
- `ufromfpxfNx`
- `ufromfpxl`
- `ulabs`
- `ullabs`
- `umaxabs`
- `uselib`
- `user2netname`
- `ustat`
- `versionsort64`
- `vlimit`
- `vtimes`
- `wcschrnul`
- `wcslcat`
- `wcslcpy`
- `wcstod_l`
- `wcstof128`
- `wcstof128_l`
- `wcstof32`
- `wcstof32_l`
- `wcstof32x`
- `wcstof32x_l`
- `wcstof64`
- `wcstof64_l`
- `wcstof64x`
- `wcstof64x_l`
- `wcstofN`
- `wcstofNx`
- `wcstof_l`
- `wcstol_l`
- `wcstold_l`
- `wcstoll_l`
- `wcstoq`
- `wcstoul_l`
- `wcstoull_l`
- `wcstouq`
- `wmempcpy`
- `writeColdStartFile`
- `xcrypt`
- `xcrypt_gensalt`
- `xcrypt_gensalt_r`
- `xcrypt_r`
- `xdecrypt`
- `xdr_accepted_reply`
- `xdr_array`
- `xdr_authdes_cred`
- `xdr_authdes_verf`
- `xdr_authunix_parms`
- `xdr_bool`
- `xdr_bytes`
- `xdr_callhdr`
- `xdr_callmsg`
- `xdr_cback_data`
- `xdr_char`
- `xdr_cryptkeyarg`
- `xdr_cryptkeyarg2`
- `xdr_cryptkeyres`
- `xdr_des_block`
- `xdr_domainname`
- `xdr_double`
- `xdr_enum`
- `xdr_float`
- `xdr_free`
- `xdr_getcredres`
- `xdr_hyper`
- `xdr_int`
- `xdr_int16_t`
- `xdr_int32_t`
- `xdr_int64_t`
- `xdr_int8_t`
- `xdr_key_netstarg`
- `xdr_key_netstres`
- `xdr_keybuf`
- `xdr_keydat`
- `xdr_keystatus`
- `xdr_long`
- `xdr_longlong_t`
- `xdr_mapname`
- `xdr_netnamestr`
- `xdr_netobj`
- `xdr_obj_p`
- `xdr_opaque`
- `xdr_opaque_auth`
- `xdr_peername`
- `xdr_pmap`
- `xdr_pmaplist`
- `xdr_pointer`
- `xdr_quad_t`
- `xdr_reference`
- `xdr_rejected_reply`
- `xdr_replymsg`
- `xdr_rmtcall_args`
- `xdr_rmtcallres`
- `xdr_short`
- `xdr_sizeof`
- `xdr_string`
- `xdr_u_char`
- `xdr_u_hyper`
- `xdr_u_int`
- `xdr_u_long`
- `xdr_u_longlong_t`
- `xdr_u_quad_t`
- `xdr_u_short`
- `xdr_uint16_t`
- `xdr_uint32_t`
- `xdr_uint64_t`
- `xdr_uint8_t`
- `xdr_union`
- `xdr_unixcred`
- `xdr_valdat`
- `xdr_vector`
- `xdr_void`
- `xdr_wrapstring`
- `xdr_yp_buf`
- `xdr_ypall`
- `xdr_ypbind_binding`
- `xdr_ypbind_resp`
- `xdr_ypbind_resptype`
- `xdr_ypbind_setdom`
- `xdr_ypdelete_args`
- `xdr_ypmap_parms`
- `xdr_ypmaplist`
- `xdr_yppush_status`
- `xdr_yppushresp_xfr`
- `xdr_ypreq_key`
- `xdr_ypreq_nokey`
- `xdr_ypreq_xfr`
- `xdr_ypresp_all`
- `xdr_ypresp_key_val`
- `xdr_ypresp_maplist`
- `xdr_ypresp_master`
- `xdr_ypresp_order`
- `xdr_ypresp_val`
- `xdr_ypresp_xfr`
- `xdr_ypstat`
- `xdr_ypupdate_args`
- `xdr_ypxfrstat`
- `xdrmem_create`
- `xdrrec_create`
- `xdrrec_endofrecord`
- `xdrrec_eof`
- `xdrrec_skiprecord`
- `xdrstdio_create`
- `xencrypt`
- `xprt_register`
- `xprt_unregister`
- `y0f128`
- `y0f32`
- `y0f32x`
- `y0f64`
- `y0f64x`
- `y0fN`
- `y0fNx`
- `y0l`
- `y1f128`
- `y1f32`
- `y1f32x`
- `y1f64`
- `y1f64x`
- `y1fN`
- `y1fNx`
- `y1l`
- `ynf128`
- `ynf32`
- `ynf32x`
- `ynf64`
- `ynf64x`
- `ynfN`
- `ynfNx`
- `ynl`
- `yp_all`
- `yp_bind`
- `yp_first`
- `yp_get_default_domain`
- `yp_maplist`
- `yp_master`
- `yp_match`
- `yp_next`
- `yp_order`
- `yp_unbind`
- `yp_update`
- `ypbinderr_string`
- `yperr_string`
- `ypprot_err`
