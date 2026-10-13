# add_key(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | add_key: x64 248 / i386 286 / arm64-generic 217 / arm32 309; request_key: x64 249 / i386 287 / arm64-generic 218 / arm32 310; keyctl: x64 250 / i386 288 / arm64-generic 219 / arm32 311 |
| Since (kernel) | 2.6.10 for add_key / request_key / keyctl core operations (man VERSIONS); later keyctl operations have their own dates (table below) |
| Man page | man2/add_key.2, man2/request_key.2, man2/keyctl.2 (cached, 2021-08-27); overview in keyrings(7) |
| glibc wrapper | None -- glibc does not wrap the keyring syscalls; wrappers live in `libkeyutils` (`<keyutils.h>`, link with `-lkeyutils`) |
| Aliases covered | `request_key` (SC-request_key), `keyctl` (SC-keyctl) -- the keyring API trio shares this page |
| Ledger ID | SC-add_key |

## Purpose

The kernel key retention service stores security tokens (kerberos tickets,
encryption keys, module signatures) with per-user quotas and permission
bits. The API is three syscalls: `add_key()` creates or updates a key and
links it into a keyring; `request_key()` finds a key by type+description,
optionally triggering a `/sbin/request-key` user-space upcall to construct
it; `keyctl()` is the control multiplexer (read, revoke, link, search,
instantiate, timeout, and more).

## Synopsis

    /* no glibc wrapper: use libkeyutils or syscall(2) */
    long add_key(const char *type, const char *description,
                 const void *payload, size_t plen, key_serial_t keyring);

    key_serial_t request_key(const char *type, const char *description,
                             const char *callout_info, key_serial_t dest_keyring);

    long keyctl(int operation, ...);

## Arguments and behavior

`add_key()`: `type` is a registered key type -- `keyring` (payload NULL),
`user` (arbitrary blob up to 32,767 bytes, kernel memory), `logon` (since
3.3, never readable from user space, description needs a `service:` prefix)
or `big_key` (since 3.13, up to 1 MiB, large payloads spliced to encrypted
tmpfs). If a matching type+description key already exists in the
destination keyring, the type may update it in place; otherwise the new key
displaces the old link. `description` is limited to 4096 bytes, `type` to
32. Destination `keyring` is a serial number or a special ID: `KEY_SPEC_THREAD_KEYRING`
(-1), `KEY_SPEC_PROCESS_KEYRING` (-2), `KEY_SPEC_SESSION_KEYRING` (-3),
`KEY_SPEC_USER_KEYRING` (-4), `KEY_SPEC_USER_SESSION_KEYRING` (-5),
`KEY_SPEC_GROUP_KEYRING` (-6, defunct), `KEY_SPEC_REQKEY_AUTH_KEY` (-7),
`KEY_SPEC_REQUESTOR_KEYRING` (-8) (values from `<linux/keyctl.h>`).
`request_key()` searches thread -> process -> session keyrings breadth-first
(search permission required); a miss with non-NULL `callout_info` forks the
`/sbin/request-key` helper with an authorization key of type
`.request_key_auth`; a miss with NULL `callout_info` fails `ENOKEY`.
`keyctl()` operations (numbered constants in `<linux/keyctl.h>`): 0
`KEYCTL_GET_KEYRING_ID`, 1 `JOIN_SESSION_KEYRING`, 2 `UPDATE`, 3 `REVOKE`,
4 `CHOWN`, 5 `SETPERM`, 6 `DESCRIBE`, 7 `CLEAR`, 8 `LINK`, 9 `UNLINK`,
10 `SEARCH`, 11 `READ`, 12 `INSTANTIATE`, 13 `NEGATE` (all 2.6.10),
14 `SET_REQKEY_KEYRING` (2.6.13), 15 `SET_TIMEOUT`,
16 `ASSUME_AUTHORITY` (2.6.16), 17 `GET_SECURITY` (2.6.26),
18 `SESSION_TO_PARENT` (2.6.32), 19 `REJECT`, 20 `INSTANTIATE_IOV`
(2.6.39), 21 `INVALIDATE` (3.5), 22 `GET_PERSISTENT` (3.13),
23 `DH_COMPUTE` (4.7), 29 `RESTRICT_KEYRING` (4.12); 24-28
`KEYCTL_PKEY_*` (public-key ops), 30 `MOVE`, 31 `CAPABILITIES`,
32 `WATCH_KEY` exist in the installed header without a pinned kernel date
in our sources.

## Return value and errors

`add_key()` returns the new key's serial; `keyctl()` returns an
operation-dependent nonnegative value. Common errors: `EACCES` (keyring not
writable / no search permission), `EDQUOT` (per-user key quota exceeded),
`EFAULT`, `EINVAL` (type/description length; bad payload; unprefixed
`logon` description), `EKEYEXPIRED`, `EKEYREVOKED`, `ENOKEY` (keyring or
key missing), `ENOMEM`, `EPERM` (type or keyring description starting with
a period -- reserved).

## Flags and constants

| Constant | Value | Meaning |
|---|---|---|
| `KEY_SPEC_THREAD_KEYRING` | -1 | Caller's thread keyring |
| `KEY_SPEC_PROCESS_KEYRING` | -2 | Caller's process keyring |
| `KEY_SPEC_SESSION_KEYRING` | -3 | Caller's session keyring |
| `KEY_SPEC_USER_KEYRING` | -4 | UID keyring |
| `KEY_SPEC_USER_SESSION_KEYRING` | -5 | UID session keyring |
| `KEY_SPEC_GROUP_KEYRING` | -6 | GID keyring (legacy/defunct) |
| `KEY_SPEC_REQKEY_AUTH_KEY` | -7 | Assumed request_key authorization key |
| `KEY_SPEC_REQUESTOR_KEYRING` | -8 | request_key destination in upcalled helper |

## Security and notes

Key permissions are four 8-bit masks (only six bits used per mask) for the
possessor, user, group and other categories, granting `view`, `read`,
`write`, `search`, `link` and `setattr`; `KEYCTL_SETPERM` changes the mask,
and without `CAP_SYS_ADMIN` a caller may change permissions only on keys it
owns (fsuid match) -- keyctl.2. Session
keyrings are attached at login by `pam_keyinit` (request_key.2 comment).
`/proc/keys` lists a user's keys with state flags, permission mask, UID/GID,
type and description; it also displays the expiry countdown set by
`KEYCTL_SET_TIMEOUT` and shows invalidated keys with an `i` flag until
garbage collection (keyctl.2). `KEYCTL_DH_COMPUTE` (4.7) implements
Diffie-Hellman over `user`-type keys with optional KDF. Related process
credentials: [setuid](../process/setuid.md)-family pages.

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/add_key.2`,
  `request_key.2`, `keyctl.2`
- Online: https://man7.org/linux/man-pages/man2/add_key.2.html
- Constants: `/usr/include/linux/keyctl.h` (KEY_SPEC_*, KEYCTL_* values)
- Kernel tables: `source-cache/kernel/syscall_64.tbl` (248, 249, 250)
