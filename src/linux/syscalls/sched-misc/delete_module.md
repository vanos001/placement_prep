# delete_module(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | delete_module 176 / 129 / 106 / 129; init_module 175 / 128 / 105 / 128; finit_module 313 / 350 / 273 / 379 (per-call table below) |
| Since (kernel) | delete_module/init_module 1.0 (hub); finit_module 3.8 (man VERSIONS); hub grouped row shows delete_module's 1.0 |
| Man page | man2/delete_module.2 and man2/init_module.2 (finit_module.2 is documented inside init_module.2; local cache, dated 2021-03-22) |
| glibc wrapper | No declarations in glibc headers; glibc exported the ABI historically -- nm -D on glibc 2.41 still shows delete_module@@GLIBC_2.2.5 and init_module@@GLIBC_2.2.5 (but the man page says no wrapper, use syscall(2)); no finit_module symbol |
| Aliases covered | init_module, finit_module |
| Ledger ID | SC-delete_module, SC-init_module, SC-finit_module |

Numbers by call, from [the ledger](../ledger.md) and cross-checked against the cached kernel tables:

| Call | x64 | i386 | g64 | arm32 | Since |
|---|---|---|---|---|---|
| delete_module | 176 | 129 | 106 | 129 | 1.0 |
| init_module | 175 | 128 | 105 | 128 | 1.0 |
| finit_module | 313 | 350 | 273 | 379 | 3.8 |

## Purpose

init_module() loads an ELF kernel-module image into kernel space, relocates symbols, applies module parameters from a space-delimited param_values string, and runs the module's init function. finit_module() (3.8) is the fd-based form: it reads the image from fd, which lets signed-module verification key off the file location instead of a memory buffer. delete_module() removes the module named by name, running its exit function first; removal fails while other modules depend on it or, depending on flags, while its reference count is nonzero.

## Synopsis

```c
int init_module(void *module_image, unsigned long len,
                const char *param_values);
int finit_module(int fd, const char *param_values, int flags);
int delete_module(const char *name, int flags);
```

## Arguments and behavior

| Call | Arguments |
|---|---|
| init_module | module_image/len: ELF image built for the running kernel; param_values: name=value specs parsed by the kernel |
| finit_module | fd open for reading; param_values as above; flags: MODULE_INIT_IGNORE_MODVERSIONS and MODULE_INIT_IGNORE_VERMAGIC bypass the build-time safety checks (needs CONFIG_MODULE_FORCE_LOAD, else ENOEXEC) |
| delete_module | name; flags O_NONBLOCK (return EWOULDBLOCK if the reference count is nonzero) and O_TRUNC (unload regardless of reference count; bypasses the init-without-exit refusal; taints the kernel TAINT_FORCED_RMMOD) |

Without O_NONBLOCK the caller sleeps uninterruptibly (TASK_UNINTERRUPTIBLE) until the count reaches zero -- the man page flags this as undesirable and likely to become mandatory to avoid.

## Return value and errors

Returns 0 on success; -1 with errno: EBUSY (module not live; init-without-exit without O_TRUNC; symbol-resolution timeout), EFAULT, ENOENT (no such module), EPERM (lacking CAP_SYS_MODULE, or /proc/sys/kernel/modules_disabled set), EWOULDBLOCK (dependents, or O_NONBLOCK with busy module); init_module adds EEXIST/EINVAL/ENOEXEC, finit_module adds EBADF/EFBIG/EINVAL/ENOEXEC, and both report EBADMSG/ENOKEY (3.7) for signature problems (ENOKEY only under CONFIG_MODULE_SIG_FORCE, otherwise taint).

## Flags and constants

MODULE_INIT_IGNORE_MODVERSIONS and MODULE_INIT_IGNORE_VERMAGIC are defined in <linux/module.h>; O_NONBLOCK/O_TRUNC are reused from <fcntl.h> values.

## Security and notes

- All three calls require CAP_SYS_MODULE in the initial user namespace sense ("This system call requires privilege"); modules_disabled=1 is the hard kill switch for both loading and unloading.
- In Linux 2.4 and earlier the interfaces differed (single-argument delete_module; caller-relocated init_module images); kmod/libmodprobe map O_TRUNC to force and O_NONBLOCK to nowait.

## References

- man2/delete_module.2, man2/init_module.2 in the cached man-pages tree.
- [Syscalls ledger](../ledger.md) rows SC-delete_module, SC-init_module, SC-finit_module.
- [Domain hub](overview.md) for status and sibling pages.
