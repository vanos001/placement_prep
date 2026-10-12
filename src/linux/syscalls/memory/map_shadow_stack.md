# map_shadow_stack(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 453 / 453 / 453 / 453 (hub) |
| Since (kernel) | 6.6 (hub; worklog 1-b tag-probed absent 6.5 / present 6.6) |
| Man page | none (no man2/map_shadow_stack.2 in the cached tree or on man7.org; documented from arch/x86/kernel/shstk.c -- source-limited on prose) |
| glibc wrapper | no dedicated wrapper; glibc 2.39 NEWS: "Sync with Linux kernel 6.6 shadow stack interface. The --enable-cet configure option is only supported on x86-64." (the 2.42 section of the cached NEWS snapshot carries no shadow-stack item; worklog 1-b's "2.42 quote" is not reproducible in this snapshot -- gap noted) |
| Aliases covered | none |
| Ledger ID | SC-map_shadow_stack |

## Purpose

map_shadow_stack() is the x86-64-only syscall (worklog 1-b: x86-64 only)
that allocates a shadow-stack mapping: guard-page-framed memory of the
architecturally enforced shadow stack used by Intel CET SHSTK. Unlike a
plain mmap(2) ([mmap](mmap.md)), a successful allocation ends with a
restore-token word written at the top of the new shadow stack, so the
region can be used with the RSTORSSP instruction for stack switches
(jmp_buf, vDSO swapcontext-style flows). The syscall exists because the
kernel must compute and place the token; userspace cannot safely write
the shadow stack itself.

## Synopsis

```c
#include <linux/mman.h>  /* SHADOW_STACK_SET_TOKEN */
long map_shadow_stack(unsigned long addr, unsigned long size,
                      unsigned int flags);
```

No glibc declaration; invoked via syscall(2).

## Arguments and behavior

`addr` is the requested base; 0 lets the kernel choose. A nonzero addr
below 4 GiB fails with `ERANGE` (kernel constant check `addr < SZ_4G`).
`size` is rounded up to page size. `flags` may be 0 or
`SHADOW_STACK_SET_TOKEN` (1 << 0, value verified in installed
/usr/include/x86_64-linux-gnu/bits/mman.h); any other bit fails with
`EINVAL`. With the token flag, `size < 8` fails with `ENOSPC` because
there is no room for a token; `PAGE_ALIGN` overflow fails with
`EOVERFLOW`. The allocation happens only when the CPU supports user
shadow stacks: otherwise `EOPNOTSUPP` (X86_FEATURE_USER_SHSTK check).

## Return value and errors

Returns the mapped address on success; a negated error on failure
(raw syscall convention, no glibc wrapper to translate it): `EOPNOTSUPP`
(feature off), `EINVAL` (bad flags), `ENOSPC` (too small for token),
`ERANGE` (addr below 4 GiB), `EOVERFLOW` (size overflow). Deeper
alloc_shstk failure paths are not documented in any man page and are
marked unverified here (worklog 1-b).

## Flags and constants

| Flag | Value | Note |
|---|---|---|
| SHADOW_STACK_SET_TOKEN | 0x1 | write a restore token at the top of the new stack |

`MAP_ABOVE4G` (0x80) is the related internal mapping hint in
arch/x86 uapi mman.h.

## Security and notes

- x86-64 only; CONFIG_X86_USER_SHADOW_STACK gates the implementation
  (arch/x86/kernel/shstk.c).
- Worklog 1-b verified since 6.6 by tag probing (absent v6.5, present
  v6.6); glibc integration is sourced only to the NEWS quote above.
- Tokens are what make a shadow stack switchable; an mmap'd region
  without a token cannot be entered with RSTORSSP.

## References

- Kernel source: source-cache/fetched/master-arch-x86-kernel-shstk.c
  (SYSCALL_DEFINE3(map_shadow_stack)).
- Flag value: /usr/include/x86_64-linux-gnu/bits/mman.h (0x1).
- glibc NEWS: source-cache/glibc-sparse/NEWS (Version 2.39 section).
- Numbers/Since: hub [overview](overview.md); worklog Task 1-b.
