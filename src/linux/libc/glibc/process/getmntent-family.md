# `getmntent` / `getmntent_r` / `setmntent` / `endmntent` / `addmntent` / `hasmntopt` - glibc

> Split from the chapter *glibc: System Management* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `mntent.h` (struct line 51, functions lines 62-90; `getmntent_r` under `__USE_MISC` at line 71; getmntent.3 shows `#include <stdio.h>` + `#include <mntent.h>`) |
| Standards | SunOS 4.1.3 origin, non-reentrant set; `getmntent_r` is glibc (HP-UX has an int-returning variant) (getmntent.3) |
| Exported | `getmntent@@GLIBC_2.2.5` (T), `getmntent_r@@GLIBC_2.2.5` (W), `setmntent@@GLIBC_2.2.5` (W), `endmntent@@GLIBC_2.2.5` (W), `addmntent@@GLIBC_2.2.5` (W), `hasmntopt@@GLIBC_2.2.5` (W) (nm, host glibc 2.41) |
| Thread-safety | getmntent MT-Unsafe `race:mntentbuf locale`; setmntent/endmntent/hasmntopt MT-Safe; addmntent MT-Safe `race:stream locale`; getmntent_r MT-Safe locale (getmntent.3 ATTRIBUTES) |
| Ledger ID | GLIBC-getmntent, GLIBC-getmntent_r, GLIBC-setmntent, GLIBC-endmntent, GLIBC-addmntent, GLIBC-hasmntopt |

## Declaration and gates

```c
#include <stdio.h>
#include <mntent.h>

FILE *setmntent(const char *file, const char *mode);   /* mntent.h:64 */
struct mntent *getmntent(FILE *stream);                /* mntent.h:69 */
int addmntent(FILE *stream, const struct mntent *mnt); /* mntent.h:81 */
int endmntent(FILE *stream);                           /* mntent.h:85 */
char *hasmntopt(const struct mntent *mnt, const char *opt); /* :89 */

#ifdef __USE_MISC   /* mntent.h:71-77 */
struct mntent *getmntent_r(FILE *stream, struct mntent *result,
                           char *buffer, int bufsize);
#endif
```

`struct mntent` (mntent.h lines 51-59): `mnt_fsname`, `mnt_dir`,
`mnt_type`, `mnt_opts`, `mnt_freq` (dump frequency), `mnt_passno`
(fsck pass). Constants: `MNTTYPE_*`, `MNTOPT_*` (mntent.h lines 34-45).

## Semantics

The family parses `fstab(5)`-style lines from `/etc/fstab` and the
mounted-filesystems file `/etc/mtab` (getmntent.3; `_PATH_MNTTAB` /
`_PATH_MOUNTED`, paths.h lines 54-55 -- and on this host `/etc/mtab` is
a symlink to `/proc/self/mounts`). `setmntent` opens like `fopen`;
`getmntent` reads and breaks out the next line into a **static** struct
reused every call; `endmntent` closes (always returning 1); `addmntent`
appends an entry; `hasmntopt` substring-scans `mnt_opts` for an option,
returning a pointer into it. `getmntent_r` is the reentrant form with a
caller buffer (the reentrancy `__USE_MISC` gate lives only in the
header, not in older ports).

## Gotchas and portability

- The static buffer makes `getmntent` useless in threads -- use
  `getmntent_r` (or serialize); `feof`/`ferror` distinguish EOF from
  error since the NULL return conflates them (mntent.h comment).
- Close with `endmntent`, not `fclose` (getmntent.3) -- glibc's
  `endmntent` also flushes pending output.
- `mnt_freq`/`mnt_passno` are meaning-bearing for dump/fsck only.
- musl 1.2.5: all six present (`include/mntent.h` lines 32-37),
  same semantics, static `getmntent`.

## References

- man3: `getmntent.3` (covers the whole family; `setmntent.3` etc. are `.so` links)
- headers: `/usr/include/mntent.h` (lines 19-95), `/usr/include/paths.h` (lines 54-55)
- symbols: `nm -D --with-symbol-versions libc.so.6`
