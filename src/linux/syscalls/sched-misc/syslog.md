# syslog(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 103 / 103 / 116 / 103 (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 (hub/ledger); command 9 since 2.4.10 and command 10 since 2.6.6 per the man page |
| Man page | man2/syslog.2 (local cache, dated 2021-03-22; klogctl is documented on the same page) |
| glibc wrapper | The glibc wrapper is named `klogctl()` and is declared in `<sys/klog.h>`; symbol klogctl@@GLIBC_2.2.5 (nm -D). It is NOT syslog(3), which talks to syslogd(8). Installed glibc 2.41 sys/klog.h declares only klogctl -- the SYSLOG_ACTION_* names are not exported by glibc (the man page says the symbolic names are defined in the kernel source but not exported to user space) |
| Aliases covered | klogctl (glibc name) |
| Ledger ID | SC-syslog |

## Purpose

The kernel `syslog()` system call controls the kernel `printk()` ring buffer and
the console log level. It is a different animal from the C library function
syslog(3) of the same name, which sends messages to syslogd(8) -- hence the
glibc wrapper name klogctl() (man page). `dmesg(1)` is the usual front end.

## Synopsis

    #include <sys/klog.h>        /* klogctl; SYSLOG_ACTION_* not in glibc 2.41 */
    int klogctl(int type, char *bufp, int len);
    /* raw: syscall(SYS_syslog, type, bufp, len) */

## Arguments and behavior

| Type | Name (kernel source; not exported) | Action |
|---|---|---|
| 0 | `SYSLOG_ACTION_CLOSE` | Close the log; currently a NOP |
| 1 | `SYSLOG_ACTION_OPEN` | Open the log; currently a NOP |
| 2 | `SYSLOG_ACTION_READ` | Blocking read; bytes then vanish from the buffer; this is what reading `/proc/kmsg` executes |
| 3 | `SYSLOG_ACTION_READ_ALL` | Read the last `len` bytes, nondestructively; not more than what was written since the last clear |
| 4 | `SYSLOG_ACTION_READ_CLEAR` | Like 3, then also clear |
| 5 | `SYSLOG_ACTION_CLEAR` | Clear: only sets the bookkeeping variable behind commands 3 and 4; no effect on 2 or 9 |
| 6 | `SYSLOG_ACTION_CONSOLE_OFF` | Save `console_loglevel`, set it to the minimum; before 2.6.32 it simply set the minimum |
| 7 | `SYSLOG_ACTION_CONSOLE_ON` | Restore the level saved by 6; before 2.6.32 set to the default |
| 8 | `SYSLOG_ACTION_CONSOLE_LEVEL` | Set `console_loglevel` to `len`, which must be 1..8; silently clamped up to the minimum |
| 9 | `SYSLOG_ACTION_SIZE_UNREAD` (2.4.10) | Bytes currently available to command 2 |
| 10 | `SYSLOG_ACTION_SIZE_BUFFER` (2.6.6) | Total size of the log buffer |

The buffer length `LOG_BUF_LEN` was 4096 in early kernels, 8192 from 1.3.54,
16384 from 2.1.113, and a config option (`CONFIG_LOG_BUF_SHIFT`, arch-dependent
default) since 2.4.23/2.6 (man page).

## Return value and errors

Types 2, 3, 4: number of bytes read; 9: unread bytes; 10: buffer size; all
others: 0 on success. On error -1 with `errno`: `EINVAL` (bad `type`; NULL
`buf` or negative `len` for 2/3/4; level outside 1..8 for type 8), `ENOSYS`
(kernel built without `CONFIG_PRINTK`), `EPERM` (changing the level or clearing
without privilege), `ERESTARTSYS` (interrupted; visible only under a trace).

## Flags and constants

printk log levels (man page): `KERN_EMERG` 0, `KERN_ALERT` 1, `KERN_CRIT` 2,
`KERN_ERR` 3, `KERN_WARNING` 4, `KERN_NOTICE` 5, `KERN_INFO` 6, `KERN_DEBUG` 7.
A printk message reaches the console only if its level is lower than
`console_loglevel`. `/proc/sys/kernel/printk` exposes four values:
`console_loglevel`, `default_message_loglevel`, `minimum_console_loglevel`,
`default_console_loglevel`.

## Security and notes

All commands except 3 and 10 require privilege: `CAP_SYS_ADMIN` before Linux
2.6.37; since 2.6.37 either `CAP_SYSLOG` or `CAP_SYS_ADMIN` (man page).
Commands 3 and 10 are unprivileged only if `/proc/sys/kernel/dmesg_restrict`
is 0 (since 2.6.37).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/syslog.2`
- Header: installed glibc `/usr/include/sys/klog.h` (klogctl declaration)
- Online: https://man7.org/linux/man-pages/man2/syslog.2.html
