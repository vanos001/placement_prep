# `DTTOIF` / `IFTODT` (3) - glibc

> Split from the chapter *glibc: File System Interface* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `dirent.h` (both; under `__USE_MISC`) |
| Standards | No standard; BSD `d_type` convention carried into Linux |
| Exported | None -- preprocessor macros, no nm symbols (nm negative check, host glibc 2.41) |
| Thread-safety | Not applicable: pure arithmetic macros, expand in place |
| Ledger ID | GLIBC-DTTOIF, GLIBC-IFTODT |

## Declaration and gates

```c
#include <dirent.h>   /* DT_* enum + macros under __USE_MISC */

# define IFTODT(mode)   (((mode) & 0170000) >> 12)
# define DTTOIF(dirtype) ((dirtype) << 12)
```

Both macros sit at the end of the `DT_*` enum block guarded by
`#ifdef __USE_MISC` (`/usr/include/dirent.h` line 95; macros at lines
120-121; the enum `DT_UNKNOWN` 0, `DT_FIFO` 1, `DT_CHR` 2, `DT_DIR` 4,
`DT_BLK` 6, `DT_REG` 8, `DT_LNK` 10, `DT_SOCK` 12, `DT_WHT` 14 spans
lines 96-117). The kernel uapi equivalent lives in
`linux/libc-compat.h`-driven `dirent.h`; glibc deliberately keeps its
own copy out of the uapi headers it ships.

## Semantics

The macros convert between the `st_mode` file-type nibble used by the
`stat` family (`S_IFMT` class bits, `S_IFDIR`, `S_IFREG`, ...) and the
`DT_*` constants carried in `d_type` by `readdir(3)` and the raw
`getdents64` interface: `IFTODT` masks out everything but `S_IFMT`
(`0170000`) and shifts right by 12; `DTTOIF` shifts back (`getdents.2`
documents the `DT_*` set). They are the glue that lets one code path
switch on file type whether it came from `stat` or from a directory
scan.

## Gotchas and portability

- `DT_UNKNOWN` (0) maps through `DTTOIF` to 0, which is no `S_IF*`
  value: filesystems are not obliged to return a type, so the
  conversion is only meaningful after a `DT_UNKNOWN` check
  (`readdir(3)`, `getdents.2`).
- The mapping is defined only for the type bits; permission bits fed
  to `IFTODT` are ignored by design (`& 0170000`), but feeding a
  `DT_*` value >= 16 to `DTTOIF` produces garbage silently.
- musl 1.2.5 defines the same two macros ungated
  (`include/dirent.h` lines 50-51), so code relying on the
  `__USE_MISC` gate breaks there in the opposite direction.
- Sibling coverage: `S_IS*` type-test macros in
  [test-file-types-macros.md](test-file-types-macros.md);
  the raw buffer walk in [getdents64.md](getdents64.md).

## References

- headers: `/usr/include/dirent.h` lines 95-122
- man2: `getdents.2` (`DT_*` values; `d_type` filesystem support),
  `inode(7)` (S_IFMT classes, via the cached man-pages set)
- symbols: none (macro-only; `nm -D libc.so.6` negative check)
