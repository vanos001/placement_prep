# bpf(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 321 / 357 / 280 / 386 (cached kernel tables; hub agrees) |
| Since (kernel) | 3.18 (man VERSIONS; hub agrees) |
| Man page | man2/bpf.2 (local cache, dated 2021-03-22); current man7.org copy fetched this session also lacks CAP_BPF, so the 5.8 capability split is kernel-source sourced (below) |
| glibc wrapper | None: declared only in <linux/bpf.h>, use syscall(2); no bpf* symbol in libc (nm -D on glibc 2.41) |
| Aliases covered | none |
| Ledger ID | SC-bpf |

## Purpose

bpf() is the single multiplexed, fd-based entry point for extended BPF: one syscall, a cmd selector, a size-checked zero-filled union bpf_attr. Programs are statically verified before load and cannot harm the kernel; maps are generic key/value stores shared between programs and user space; fds to both transfer across dup(2), fork(2), and UNIX sockets, and an object lives until its last fd closes. The book's BPF pages cover the ecosystem: the [eBPF overview](../../kernel/networking/ebpf.md) and, as plain text, kernel/bpf-verifier.md, tracing/ebpf-verifier.md, and security/bpf-lsm.md.

## Synopsis

```c
#include <linux/bpf.h>
int bpf(int cmd, union bpf_attr *attr, unsigned int size);
```

## Arguments and behavior

Commands documented in the cached man page, with values from the installed <linux/bpf.h> enum:

| Command | Value | Meaning |
|---|---|---|
| BPF_MAP_CREATE | 0 | Create a map; returns an fd with close-on-exec already set |
| BPF_MAP_LOOKUP_ELEM | 1 | Fetch an element's value by key |
| BPF_MAP_UPDATE_ELEM | 2 | Create or update a key/value pair |
| BPF_MAP_DELETE_ELEM | 3 | Delete an element by key |
| BPF_MAP_GET_NEXT_KEY | 4 | Iterate keys |
| BPF_PROG_LOAD | 5 | Verify and load a program; returns an fd with close-on-exec set |

The installed header continues the enum through BPF_TOKEN_CREATE (36): BPF_OBJ_PIN 6, BPF_OBJ_GET 7, BPF_PROG_ATTACH/DETACH 8/9, BPF_PROG_TEST_RUN 10, an ID/FD_BY_ID/GET_INFO_BY_FD group, BPF_BTF_LOAD 18, BPF_MAP_LOOKUP_AND_DELETE_ELEM 21, the *_BATCH ops 24-27, BPF_LINK_CREATE 28, and more. These are header-sourced; no man page documents them and since-versions are unverified (flagged, not invented).

## Return value and errors

Returns the new map/program fd for MAP_CREATE/PROG_LOAD and 0 for other commands; -1 with errno: E2BIG (program too large, max_entries hit), EACCES (verifier rejection; retry with log_level 1), EBADF, EFAULT, EINVAL (unknown cmd, bad attributes, nonzero unused union fields), ENOENT (missing key), ENOMEM, EPERM (privilege, see below).

## Flags and constants

union bpf_attr carries per-command anonymous structs (map creation; element ops; program load fields); zero-fill it -- EINVAL follows if fields unused by the command are nonzero.

## Security and notes

- Before 4.4 every command needed CAP_SYS_ADMIN; from 4.4 unprivileged users may load BPF_PROG_TYPE_SOCKET_FILTER programs and maps with a reduced helper set; /proc/sys/kernel/unprivileged_bpf_disabled (write 1) blocks that.
- CAP_BPF (39) exists since kernel 5.8 (probed: absent v5.7, present v5.8), splitting BPF administration off CAP_SYS_ADMIN; tracing programs need CAP_PERFMON plus CAP_BPF, networking ones CAP_NET_ADMIN plus CAP_BPF (v5.8 capability.h comment). No man page mentions CAP_BPF; this paragraph is kernel-source sourced.
- The JIT is off by default before 4.15; CONFIG_BPF_JIT_ALWAYS_ON (4.15) forces it on as a Spectre mitigation.

## References

- man2/bpf.2 in the cached man-pages tree; current man7.org copy (source-cache/fetched/bpf.2.current.txt).
- Headers: /usr/include/linux/bpf.h (command enum, union bpf_attr); v5.8 include/uapi/linux/capability.h (CAP_BPF, source-cache/fetched).
- [Syscalls ledger](../ledger.md) row SC-bpf; [Domain hub](overview.md).
