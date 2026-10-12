# `setfsent` / `endfsent` / `getfsent` / `getfsfile` / `getfsspec` - glibc

> Split from the chapter *glibc: System Management* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `fstab.h` (path constants lines 48-55, struct lines 57-66, functions lines 71-75 -- no feature-test gate) |
| Standards | 4.3BSD heritage (header is BSD-licensed, "@(#)fstab.h 8.1 (Berkeley) 6/2/93"); "not in POSIX.1" (getfsent.3 CONFORMING TO) |
| Exported | `setfsent@@GLIBC_2.2.5` (T), `endfsent@@GLIBC_2.2.5` (T), `getfsent@@GLIBC_2.2.5` (T), `getfsfile@@GLIBC_2.2.5` (T), `getfsspec@@GLIBC_2.2.5` (T) (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:fsent` (setfsent/endfsent), `race:fsent locale` (readers) (getfsent.3 ATTRIBUTES) |
| Ledger ID | GLIBC-setfsent, GLIBC-endfsent, GLIBC-getfsent, GLIBC-getfsfile, GLIBC-getfsspec |

## Declaration and gates

```c
#include <fstab.h>

#define _PATH_FSTAB "/etc/fstab"    /* fstab.h:48 */
#define FSTAB_RO "ro"               /* FSTAB_RW/RQ/RO/SW/XX, lines 51-55 */

struct fstab {                      /* fstab.h:57-66 */
    char *fs_spec;        /* block special device name */
    char *fs_file;        /* mount point */
    char *fs_vfstype;     /* filesystem type */
    char *fs_mntops;      /* mount options */
    const char *fs_type;  /* one FSTAB_* extracted from fs_mntops */
    int fs_freq;          /* dump frequency, days */
    int fs_passno;        /* parallel-fsck pass number */
};

int setfsent(void);
struct fstab *getfsent(void);
void endfsent(void);
struct fstab *getfsspec(const char *special_file);
struct fstab *getfsfile(const char *mount_point);
```

## Semantics

The family reads `/etc/fstab` into `struct fstab` records (getfsent.3).
`setfsent` opens the file when required and rewinds it; `getfsent`
parses the next line; `endfsent` closes it; `getfsspec`/`getfsfile`
position-scan for an entry whose `fs_spec` (device) or `fs_file` (mount
point) matches. On success the readers return a `struct fstab *` and
`setfsent` returns 1; on failure or EOF they return NULL and 0
(getfsent.3 RETURN VALUE). The returned pointer is to static storage
overwritten by the next call -- the same model as `getmntent`. `fs_type`
holds one of the five strings "rw", "rq", "ro", "sw", "xx" extracted
from `fs_mntops` (fstab.h lines 51-55, getfsent.3).

## Gotchas and portability

- Legacy interface: prefer the `mntent` family (same file, active
  maintenance); fstab.h's own comment lists its consumers as the
  dump/mount/umount/swapon/fsck/df tooling of another era.
- Static storage: not thread-safe (`race:fsent`), and each call
  invalidates the previous result.
- The BSD `fs_type` semantics ("rq" = quotas etc.) survive in glibc, but
  Linux fstab files commonly use `mntops`-style options; treat `fs_type`
  as best-effort.
- HP-UX has same-named functions over a different `struct checklist`
  (getfsent.3 CONFORMING TO).
- musl 1.2.5: **absent** -- no `fstab.h` in `include/`, no symbols in the
  tree; glibc/BSD-only.

## References

- man3: `getfsent.3` (covers all five; `setfsent.3`, `endfsent.3` are `.so` links)
- headers: `/usr/include/fstab.h` (lines 32-77)
- symbols: `nm -D --with-symbol-versions libc.so.6`
