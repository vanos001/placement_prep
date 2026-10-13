# `S_ISDIR` / `makedev` / `major` / `minor` (3) - glibc

> Per-function page for the mode-inspection macros and device-number helpers
> that accompany `struct stat`; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. These are
> macros/functions, not syscalls: nothing here leaves the library.

| Field | Value |
|---|---|
| Header | `sys/stat.h` (`S_IS*`, `S_IF*`, `S_TYPEIS*`); `dirent.h` (`DT_*`, `IFTODT`, `DTTOIF`); `sys/sysmacros.h` (`major`, `minor`, `makedev`) |
| Standards | POSIX (`S_ISDIR`, `S_ISCHR`, `S_ISBLK`, `S_ISREG`, `S_ISFIFO`, `S_TYPEIS*`), GNU (`S_ISLNK`, `S_ISSOCK`), BSD (`S_IFMT` mask, `S_IF*` codes, `DT_*`, `IFTODT`/`DTTOIF`), BSD/SysV (`makedev` family) |
| Exported | `gnu_dev_major@@GLIBC_2.3.3`, `gnu_dev_minor@@GLIBC_2.3.3`, `gnu_dev_makedev@@GLIBC_2.3.3` (nm, host glibc 2.41); the `S_IS*`/`S_IF*`/`DT_*` names are macros and export no symbols |
| Thread-safety | All macros are pure; the `gnu_dev_*` helpers are MT-Safe/AS-Safe/AC-Safe by construction (single arithmetic expressions in `sys/sysmacros.h`) |
| Ledger ID | GLIBC-gnu_dev_makedev (triage row; the S_IS* predicates have no ledger rows, they are macros) |

## Declaration and gates

```c
#include <sys/stat.h>

int S_ISDIR(mode_t m);   /* directory */
int S_ISCHR(mode_t m);   /* char device */   int S_ISBLK(mode_t m);
int S_ISREG(mode_t m);   /* regular file */  int S_ISFIFO(mode_t m);
int S_ISLNK(mode_t m);   /* symlink, GNU */  int S_ISSOCK(mode_t m);
/* BSD alternate form: (m & S_IFMT) == S_IFDIR / S_IFCHR / ... */
int S_TYPEISMQ(struct stat *s);  /* POSIX.1b objects; on Linux these
int S_TYPEISSEM(struct stat *s); /* three always evaluate to zero */
int S_TYPEISSHM(struct stat *s); /* (bits/stat.h: st_mode - st_mode) */

#include <sys/sysmacros.h>
dev_t makedev(unsigned int maj, unsigned int min);
unsigned int major(dev_t dev);
unsigned int minor(dev_t dev);   /* macros over gnu_dev_* */
```

## Semantics

`st_mode` packs the file-type code and the permission bits; the predicate
macros test the type code of a mode value `m`, and the BSD-style form masks
with `S_IFMT` first (manual, *Testing File Type*). `d_type` in
`struct dirent` carries the same information as `DT_*` constants, with
`IFTODT`/`DTTOIF` converting between `d_type` values and `st_mode` bits
(manual, *Directory Entries*). `makedev` combines major and minor IDs into a
`dev_t` for `mknod`, and `major`/`minor` decompose `st_dev`/`st_rdev` again
(man3 `makedev.3`).

## Gotchas and portability

- `DT_UNKNOWN` is a legal `d_type` on filesystems without type support;
  only `d_name` is portable across POSIX systems (manual).
- The POSIX.1b predicates take a `struct stat *`, not a mode; on this host
  their definitions force zero (`bits/stat.h`), matching Linux's treatment
  of mqueues/semaphores/shm as ordinary filesystem objects.
- glibc keeps the device-number macros in `sys/sysmacros.h`; the historical
  `sys/types.h` placement is not what this header layout guarantees.
- musl 1.2.5: `include/sys/sysmacros.h` defines `major`/`minor`/`makedev`
  as pure bit-shift macros, with no exported helper symbols.

## References

- glibc manual: `filesys.texi`, nodes *Testing File Type*, *Directory
  Entries*, *Attribute Meanings* (st_rdev context)
- man3: `makedev.3`; man2 `stat.2` (st_mode layout)
- headers: `/usr/include/x86_64-linux-gnu/sys/stat.h`, `dirent.h`,
  `sys/sysmacros.h`, `bits/stat.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
