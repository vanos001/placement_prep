# sched-misc syscalls - function index

This hub indexes the per-function pages of the `sched-misc` domain in the [System Call Encyclopedia](../overview.md). Each row links to the page documenting that syscall (or man-page family); the Status column is merged from the [coverage ledger](../ledger.md). Names listed in one row share a family page: roff `.so` aliases in man-pages, plus documented time64 twins and the 6.7 futex2 operations, which their base entries document inline.

Status vocabulary: `documented` (full per-page entry), `researched` (brief entry, facts sourced), `source-limited` (no primary source reachable -- the entry names the gap), `not-started` (row inventoried in the ledger, documentation not begun).

| Page | Calls covered | Numbers (x64 / i386 / g64 / arm) | Since | Status |
|---|---|---|---|---|
| [sysctl](sysctl.md) | `_sysctl` x64 156 | i386 149 | g64 -- | arm 149 | - | 2.0 | documented |
| [unimplemented](unimplemented.md) | `afs_syscall` x64 183 | i386 137 | g64 -- | arm --, `break` x64 -- | i386 17 | g64 -- | arm --, `getpmsg` x64 181 | i386 188 | g64 -- | arm --, `gtty` x64 -- | i386 32 | g64 -- | arm --, `lock` x64 -- | i386 53 | g64 -- | arm --, `mpx` x64 -- | i386 56 | g64 -- | arm --, `prof` x64 -- | i386 44 | g64 -- | arm --, `putpmsg` x64 182 | i386 189 | g64 -- | arm --, `security` x64 185 | i386 -- | g64 -- | arm --, `stty` x64 -- | i386 31 | g64 -- | arm --, `tuxcall` x64 184 | i386 -- | g64 -- | arm --, `vserver` x64 236 | i386 273 | g64 -- | arm 313 | - | -- | documented |
| [alloc_hugepages](alloc_hugepages.md) | `alloc_hugepages` x64 -- | i386 -- | g64 -- | arm --, `free_hugepages` x64 -- | i386 -- | g64 -- | arm -- | - | 2.5.36 | documented |
| [arc_gettls](arc_gettls.md) | `arc_gettls` x64 -- | i386 -- | g64 -- | arm -- | - | 3.9 | source-limited |
| [arc_settls](arc_settls.md) | `arc_settls` x64 -- | i386 -- | g64 -- | arm -- | - | 3.9 | source-limited |
| [arc_usr_cmpxchg](arc_usr_cmpxchg.md) | `arc_usr_cmpxchg` x64 -- | i386 -- | g64 -- | arm -- | - | 4.9 | source-limited |
| [atomic_barrier](atomic_barrier.md) | `atomic_barrier` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.34 | source-limited |
| [atomic_cmpxchg_32](atomic_cmpxchg_32.md) | `atomic_cmpxchg_32` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.34 | source-limited |
| [bdflush](bdflush.md) | `bdflush` x64 -- | i386 134 | g64 -- | arm 134 | - | 1.2 | documented |
| [bpf](bpf.md) | `bpf` x64 321 | i386 357 | g64 280 | arm 386 | - | 3.18 | documented |
| [breakpoint](breakpoint.md) | `breakpoint` x64 -- | i386 -- | g64 -- | arm -- | - | 2.2 | source-limited |
| [cacheflush](cacheflush.md) | `cacheflush` x64 -- | i386 -- | g64 -- | arm -- | - | 1.2 | documented |
| [create_module](create_module.md) | `create_module` x64 174 | i386 127 | g64 -- | arm -- | - | 1.0 | documented |
| [delete_module](delete_module.md) | `delete_module` x64 176 | i386 129 | g64 106 | arm 129, `finit_module` x64 313 | i386 350 | g64 273 | arm 379, `init_module` x64 175 | i386 128 | g64 105 | arm 128 | - | 1.0 | documented |
| [ftime](ftime.md) | `ftime` x64 -- | i386 35 | g64 -- | arm -- | - | -- | source-limited |
| [get_kernel_syms](get_kernel_syms.md) | `get_kernel_syms` x64 177 | i386 130 | g64 -- | arm -- | - | 1.0 | documented |
| [set_thread_area](set_thread_area.md) | `get_thread_area` x64 211 | i386 244 | g64 -- | arm --, `set_thread_area` x64 205 | i386 243 | g64 -- | arm -- | - | 2.6 | researched |
| [get_tls](get_tls.md) | `get_tls` x64 -- | i386 -- | g64 -- | arm -- | - | 4.15 | source-limited |
| [getcpu](getcpu.md) | `getcpu` x64 309 | i386 318 | g64 168 | arm 345 | - | 2.6.19 | documented |
| [getdtablesize](getdtablesize.md) | `getdtablesize` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | documented |
| [getpagesize](getpagesize.md) | `getpagesize` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | documented |
| [getpriority](getpriority.md) | `getpriority` x64 140 | i386 96 | g64 141 | arm 96, `nice` x64 -- | i386 34 | g64 -- | arm 34, `setpriority` x64 141 | i386 97 | g64 140 | arm 97 | - | 1.0 | documented |
| [getrandom](getrandom.md) | `getrandom` x64 318 | i386 355 | g64 278 | arm 384 | - | 3.17 | documented |
| [getunwind](getunwind.md) | `getunwind` x64 -- | i386 -- | g64 -- | arm -- | - | 2.4.8 | documented |
| [getxgid](getxgid.md) | `getxgid` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | source-limited |
| [getxpid](getxpid.md) | `getxpid` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | source-limited |
| [getxuid](getxuid.md) | `getxuid` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | source-limited |
| [idle](idle.md) | `idle` x64 -- | i386 112 | g64 -- | arm -- | - | -- | documented |
| [ioperm](ioperm.md) | `ioperm` x64 173 | i386 101 | g64 -- | arm -- | - | 1.0 | researched |
| [iopl](iopl.md) | `iopl` x64 172 | i386 110 | g64 -- | arm -- | - | 1.0 | researched |
| [ioprio_get](ioprio_get.md) | `ioprio_get` x64 252 | i386 290 | g64 31 | arm 315, `ioprio_set` x64 251 | i386 289 | g64 30 | arm 314 | - | 2.6.13 | documented |
| [kcmp](kcmp.md) | `kcmp` x64 312 | i386 349 | g64 272 | arm 378 | - | 3.5 | documented |
| [kern_features](kern_features.md) | `kern_features` x64 -- | i386 -- | g64 -- | arm -- | - | 3.7 | source-limited |
| [kexec_load](kexec_load.md) | `kexec_file_load` x64 320 | i386 -- | g64 294 | arm 401, `kexec_load` x64 246 | i386 283 | g64 104 | arm 347 | - | 3.17 | documented |
| [landlock_create_ruleset](landlock_create_ruleset.md) | `landlock_add_rule` x64 445 | i386 445 | g64 445 | arm 445, `landlock_create_ruleset` x64 444 | i386 444 | g64 444 | arm 444, `landlock_restrict_self` x64 446 | i386 446 | g64 446 | arm 446 | - | 5.13 | documented |
| [lookup_dcookie](lookup_dcookie.md) | `lookup_dcookie` x64 212 | i386 253 | g64 18 | arm 249 | - | 2.6 | documented |
| [lsm_get_self_attr](lsm_get_self_attr.md) | `lsm_get_self_attr` x64 459 | i386 459 | g64 459 | arm 459, `lsm_list_modules` x64 461 | i386 461 | g64 461 | arm 461, `lsm_set_self_attr` x64 460 | i386 460 | g64 460 | arm 460 | - | -- | documented |
| [memory_ordering](memory_ordering.md) | `memory_ordering` x64 -- | i386 -- | g64 -- | arm -- | - | 2.2 | source-limited |
| [modify_ldt](modify_ldt.md) | `modify_ldt` x64 154 | i386 123 | g64 -- | arm -- | - | 1.0 | documented |
| [nfsservctl](nfsservctl.md) | `nfsservctl` x64 180 | i386 169 | g64 42 | arm 169 | - | 2.2 | documented |
| [old_adjtimex](old_adjtimex.md) | `old_adjtimex` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | source-limited |
| [old_getrlimit](old_getrlimit.md) | `old_getrlimit` x64 -- | i386 -- | g64 -- | arm -- | - | 2.4 | source-limited |
| [stat](stat.md) | `oldfstat` x64 -- | i386 28 | g64 -- | arm --, `oldlstat` x64 -- | i386 84 | g64 -- | arm --, `oldstat` x64 -- | i386 18 | g64 -- | arm -- | - | 1.0 | source-limited |
| [uname](uname.md) | `oldolduname` x64 -- | i386 59 | g64 -- | arm --, `olduname` x64 -- | i386 109 | g64 -- | arm -- | - | 1.0 | source-limited |
| [umount2](umount2.md) | `oldumount` x64 -- | i386 -- | g64 -- | arm -- | - | 2.4.116 | source-limited |
| [or1k_atomic](or1k_atomic.md) | `or1k_atomic` x64 -- | i386 -- | g64 -- | arm -- | - | 3.1 | source-limited |
| [pciconfig_read](pciconfig_read.md) | `pciconfig_iobase` x64 -- | i386 -- | g64 -- | arm 271, `pciconfig_read` x64 -- | i386 -- | g64 -- | arm 272, `pciconfig_write` x64 -- | i386 -- | g64 -- | arm 273 | - | 2.2.15 | documented |
| [perf_event_open](perf_event_open.md) | `perf_event_open` x64 298 | i386 336 | g64 241 | arm 364 | - | 2.6.31 | documented |
| [perfctr](perfctr.md) | `perfctr` x64 -- | i386 -- | g64 -- | arm -- | - | 2.2 | source-limited |
| [perfmonctl](perfmonctl.md) | `perfmonctl` x64 -- | i386 -- | g64 -- | arm -- | - | 2.4 | documented |
| [profil](profil.md) | `profil` x64 -- | i386 98 | g64 -- | arm -- | - | -- | source-limited |
| [query_module](query_module.md) | `query_module` x64 178 | i386 167 | g64 -- | arm -- | - | 2.2 | documented |
| [reboot](reboot.md) | `reboot` x64 169 | i386 88 | g64 142 | arm 88 | - | 1.0 | documented |
| [riscv_flush_icache](riscv_flush_icache.md) | `riscv_flush_icache` x64 -- | i386 -- | g64 -- | arm -- | - | 4.15 | source-limited |
| [rtas](rtas.md) | `rtas` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.2 | source-limited |
| [s390_guarded_storage](s390_guarded_storage.md) | `s390_guarded_storage` x64 -- | i386 -- | g64 -- | arm -- | - | 4.12 | documented |
| [s390_pci_mmio_write](s390_pci_mmio_write.md) | `s390_pci_mmio_read` x64 -- | i386 -- | g64 -- | arm --, `s390_pci_mmio_write` x64 -- | i386 -- | g64 -- | arm -- | - | 3.19 | documented |
| [s390_runtime_instr](s390_runtime_instr.md) | `s390_runtime_instr` x64 -- | i386 -- | g64 -- | arm -- | - | 3.7 | documented |
| [s390_sthyi](s390_sthyi.md) | `s390_sthyi` x64 -- | i386 -- | g64 -- | arm -- | - | 4.15 | documented |
| [sched_setaffinity](sched_setaffinity.md) | `sched_get_affinity` x64 -- | i386 -- | g64 -- | arm --, `sched_getaffinity` x64 204 | i386 242 | g64 123 | arm 242, `sched_set_affinity` x64 -- | i386 -- | g64 -- | arm --, `sched_setaffinity` x64 203 | i386 241 | g64 122 | arm 241 | - | 2.6 | documented |
| [sched_get_priority_max](sched_get_priority_max.md) | `sched_get_priority_max` x64 146 | i386 159 | g64 125 | arm 159, `sched_get_priority_min` x64 147 | i386 160 | g64 126 | arm 160, `sched_rr_get_interval` x64 148 | i386 161 | g64 127 | arm 161, `sched_rr_get_interval_time64` x64 -- | i386 423 | g64 -- | arm 423 | - | 2.0 | documented |
| [sched_setattr](sched_setattr.md) | `sched_getattr` x64 315 | i386 352 | g64 275 | arm 381, `sched_setattr` x64 314 | i386 351 | g64 274 | arm 380 | - | 3.14 | documented |
| [sched_setscheduler](sched_setscheduler.md) | `sched_getparam` x64 143 | i386 155 | g64 121 | arm 155, `sched_getscheduler` x64 145 | i386 157 | g64 120 | arm 157, `sched_setparam` x64 142 | i386 154 | g64 118 | arm 154, `sched_setscheduler` x64 144 | i386 156 | g64 119 | arm 156 | - | 2.0 | documented |
| [sched_yield](sched_yield.md) | `sched_yield` x64 24 | i386 158 | g64 124 | arm 158 | - | 2.0 | documented |
| [seccomp](seccomp.md) | `seccomp` x64 317 | i386 354 | g64 277 | arm 383 | - | 3.17 | documented |
| [set_tls](set_tls.md) | `set_tls` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.11 | source-limited |
| [sethae](sethae.md) | `sethae` x64 -- | i386 -- | g64 -- | arm -- | - | 2.0 | source-limited |
| [setup](setup.md) | `setup` x64 -- | i386 -- | g64 -- | arm -- | - | 1.0 | documented |
| [spill](spill.md) | `spill` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.13 | source-limited |
| [spu_create](spu_create.md) | `spu_create` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.16 | documented |
| [spu_run](spu_run.md) | `spu_run` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.16 | documented |
| [subpage_prot](subpage_prot.md) | `subpage_prot` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.25 | documented |
| [swapcontext](swapcontext.md) | `swapcontext` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.3 | source-limited |
| [switch_endian](switch_endian.md) | `switch_endian` x64 -- | i386 -- | g64 -- | arm -- | - | 4.1 | source-limited |
| [sys_debug_setcontext](sys_debug_setcontext.md) | `sys_debug_setcontext` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.11 | source-limited |
| [syscall](syscall.md) | `syscall` x64 -- | i386 -- | g64 -- | arm -- | - | 1.0 | researched |
| [sysfs](sysfs.md) | `sysfs` x64 139 | i386 135 | g64 -- | arm 135 | - | 1.2 | documented |
| [sysinfo](sysinfo.md) | `sysinfo` x64 99 | i386 116 | g64 179 | arm 116 | - | 1.0 | documented |
| [syslog](syslog.md) | `syslog` x64 103 | i386 103 | g64 116 | arm 103 | - | 1.0 | documented |
| [sysmips](sysmips.md) | `sysmips` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.0 | source-limited |
| [ulimit](ulimit.md) | `ulimit` x64 -- | i386 58 | g64 -- | arm -- | - | -- | source-limited |
| [uprobe](uprobe.md) | `uprobe` x64 336 | i386 -- | g64 -- | arm -- | - | -- | source-limited |
| [uretprobe](uretprobe.md) | `uretprobe` x64 335 | i386 -- | g64 -- | arm -- | - | -- | source-limited |
| [uselib](uselib.md) | `uselib` x64 134 | i386 86 | g64 -- | arm 86 | - | 1.0 | documented |
| [usr26](usr26.md) | `usr26` x64 -- | i386 -- | g64 -- | arm -- | - | 2.4.8.1 | source-limited |
| [usr32](usr32.md) | `usr32` x64 -- | i386 -- | g64 -- | arm -- | - | 2.4.8.1 | source-limited |
| [ustat](ustat.md) | `ustat` x64 136 | i386 62 | g64 -- | arm 62 | - | 1.0 | documented |
| [utrap_install](utrap_install.md) | `utrap_install` x64 -- | i386 -- | g64 -- | arm -- | - | 2.2 | source-limited |
| [vhangup](vhangup.md) | `vhangup` x64 153 | i386 111 | g64 58 | arm 111 | - | 1.0 | researched |
| [vm86](vm86.md) | `vm86` x64 -- | i386 166 | g64 -- | arm --, `vm86old` x64 -- | i386 113 | g64 -- | arm -- | - | 2.0.28 | documented |
| [xtensa](xtensa.md) | `xtensa` x64 -- | i386 -- | g64 -- | arm -- | - | 2.6.13 | source-limited |
