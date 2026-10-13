# kexec_load(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | kexec_load 246 / 283 / 104 / 347; kexec_file_load 320 / - / 294 / 401 (per-call table below) |
| Since (kernel) | kexec_load 2.6.13; kexec_file_load 3.17 (man VERSIONS; hub grouped row shows 3.17) |
| Man page | man2/kexec_load.2 (kexec_file_load.2 is documented inside it; local cache, dated 2021-03-22) |
| glibc wrapper | None: glibc provides no wrappers, necessitating syscall(2); no kexec symbol in libc (nm -D on glibc 2.41) |
| Aliases covered | kexec_file_load |
| Ledger ID | SC-kexec_load, SC-kexec_file_load |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| kexec_load | 246 | 283 | 104 | 347 | 2.6.13 |
| kexec_file_load | 320 | - | 294 | 401 | 3.17 |

## Purpose

kexec_load() loads a new kernel image into memory where reboot(2) (or a panic) can later execute it, bypassing firmware. The image is described by up to 16 kexec_segment entries (user buffer buf/bufsz copied to page-aligned physical address mem/memsz, excess zeroed). kexec_file_load() (3.17) is the fd-based form: the kernel comes from kernel_fd, the initrd from initrd_fd, and the new command line from a NUL-terminated cmdline buffer; it exists so systems can restrict kexec to signed kernels.

## Synopsis

```c
long kexec_load(unsigned long entry, unsigned long nr_segments,
                struct kexec_segment *segments, unsigned long flags);
long kexec_file_load(int kernel_fd, int initrd_fd,
                     unsigned long cmdline_len, const char *cmdline,
                     unsigned long flags);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| entry | Physical entry address in the loaded kernel image (kexec_load only) |
| nr_segments / segments | Up to KEXEC_SEGMENT_MAX (16) segments; bufsz <= memsz; mem/memsz multiples of the page size |
| flags (kexec_load) | KEXEC_ON_CRASH (2.6.13: load into the crashkernel-reserved region for panic boots; targets are validated), KEXEC_PRESERVE_CONTEXT (2.6.27, CONFIG_KEXEC_JUMP); high 16 bits (mask 0xffff0000) carry the target architecture (KEXEC_ARCH_DEFAULT, KEXEC_ARCH_386, KEXEC_ARCH_X86_64, ...) |
| flags (kexec_file_load) | KEXEC_FILE_UNLOAD, KEXEC_FILE_ON_CRASH, KEXEC_FILE_NO_INITRAMFS (initrd_fd ignored) |

kexec_load() requires CONFIG_KEXEC; kexec_file_load() requires CONFIG_KEXEC_FILE.

## Return value and errors

Returns 0 on success; -1 with errno: EADDRNOTAVAIL (crash-region violation or unaligned mem/memsz), EBADF, EBUSY (crash kernel already loaded or in use), EINVAL (bad flags, bufsz > memsz, > 16 segments, overlapping targets, cmdline not NUL-terminated, empty file), ENOEXEC (kernel_fd not loadable; the man page notes bzImage/x86 constraints), ENOMEM, EPERM (no CAP_SYS_BOOT).

## Flags and constants

struct kexec_segment is {void *buf; size_t bufsz; void *mem; size_t memsz} (man page); constants live in <linux/kexec.h>.

## Security and notes

- EPERM names the gate: CAP_SYS_BOOT. A caller with it effectively controls what code runs after the next reboot, which is why lockdown-enabled kernels restrict kexec further (see the book's [secure boot page](../../security/secure-boot.md)).
- The crash-kernel region is advertised in /proc/iomem as "Crash kernel".

## References

- man2/kexec_load.2 in the cached man-pages tree.
- [Syscalls ledger](../ledger.md) rows SC-kexec_load, SC-kexec_file_load.
- Siblings: [reboot](reboot.md) (execution trigger); [Domain hub](overview.md).
