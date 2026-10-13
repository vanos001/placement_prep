# reboot(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 169 / 88 / 142 / 88 (cached kernel tables; hub agrees) |
| Since (kernel) | 1.0 (hub/ledger); per-command since values from the man page / headers given in the table below |
| Man page | man2/reboot.2 (local cache, dated 2021-03-22) |
| glibc wrapper | `reboot(int cmd)` declared in `<sys/reboot.h>` with the `RB_*` names; symbol reboot@@GLIBC_2.2.5 (nm -D on glibc 2.41). The raw call takes four arguments (man page) |
| Aliases covered | none |
| Ledger ID | SC-reboot |

## Purpose

`reboot()` reboots, halts, powers off, or suspends the system, toggles
Ctrl-Alt-Del (CAD) handling, or boots a kernel previously loaded with
kexec_load(2). Since Linux 3.4 it can also "reboot" a non-initial PID
namespace by killing its init process (man page).

## Synopsis

    #include <linux/reboot.h>   /* LINUX_REBOOT_* constants */
    int syscall(SYS_reboot, int magic, int magic2, int cmd, void *arg);
    /* or the 1-argument libc form */
    #include <sys/reboot.h>
    int reboot(int cmd);

## Arguments and behavior

The call fails with `EINVAL` unless `magic` is `LINUX_REBOOT_MAGIC1` (0xfee1dead)
and `magic2` is `LINUX_REBOOT_MAGIC2` (672274793) or, since 2.1.17 / 2.1.97 /
2.5.71 respectively, 85072278 / 369367448 / 537993216 (man page; values in
installed linux/reboot.h).

| Command | Value (linux/reboot.h) | glibc RB_* | Since | Effect |
|---|---|---|---|---|
| `LINUX_REBOOT_CMD_RESTART` | 0x01234567 | `RB_AUTOBOOT` | original | "Restarting system." then default restart |
| `LINUX_REBOOT_CMD_HALT` | 0xCDEF0123 | `RB_HALT_SYSTEM` | 1.1.76 | "System halted.", control to ROM monitor |
| `LINUX_REBOOT_CMD_CAD_ON` | 0x89ABCDEF | `RB_ENABLE_CAD` | original | CAD keystroke triggers RESTART immediately |
| `LINUX_REBOOT_CMD_CAD_OFF` | 0x00000000 | `RB_DISABLE_CAD` | original | CAD sends SIGINT to init instead |
| `LINUX_REBOOT_CMD_POWER_OFF` | 0x4321FEDC | `RB_POWER_OFF` | 2.1.30 | "Power down.", remove power |
| `LINUX_REBOOT_CMD_RESTART2` | 0xA1B2C3D4 | (none in glibc sys/reboot.h) | 2.1.30 | restart using the command string in `arg` |
| `LINUX_REBOOT_CMD_SW_SUSPEND` | 0xD000FCE2 | `RB_SW_SUSPEND` | 2.5.18 | suspend to disk; needs `CONFIG_HIBERNATION` |
| `LINUX_REBOOT_CMD_KEXEC` | 0x45584543 | `RB_KEXEC` | 2.6.13 | execute a kernel loaded via kexec_load(2); needs `CONFIG_KEXEC` |

Discrepancy to flag: the cached man page prints SW_SUSPEND as 0xd000fce1; both
installed headers (linux/reboot.h and glibc sys/reboot.h) give 0xD000FCE2.

## Return value and errors

The commands that stop or restart the system do not return. CAD_ON/CAD_OFF
return 0 on success. On failure -1 with `errno`: `EFAULT` (bad user data under
RESTART2), `EINVAL` (bad magic numbers or command), `EPERM` (insufficient
privilege).

## Flags and constants

None beyond the command table.

## Security and notes

The caller must have `CAP_SYS_BOOT` inside its user namespace (man ERRORS:
EPERM). RESTART/HALT/POWER_OFF without a preceding sync(2) lose data (man
page). Inside a non-initial PID namespace (since 3.4): RESTART/RESTART2
terminate the namespace's init and the parent's wait(2) reports SIGHUP;
POWER_OFF/HALT report SIGINT; other commands fail with `EINVAL`.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/reboot.2`
- Headers: installed `/usr/include/linux/reboot.h`, glibc `sys/reboot.h`
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (169), `syscall_32.tbl`
  (88), `syscall_generic.tbl` (142), `syscall_arm.tbl` (88)
- Online: https://man7.org/linux/man-pages/man2/reboot.2.html
