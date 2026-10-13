# `gethostid` / `sethostid` - glibc

> Split from the chapter *glibc: System Management* into the per-function
> layout; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `unistd.h` (`sethostid` line 924 under `__USE_MISC`; `gethostid` line 1002 under `__USE_MISC` or `__USE_XOPEN_EXTENDED`) -- both gates in one `#if` at line 998 |
| Standards | 4.2BSD, dropped in 4.4BSD; SVr4 has `gethostid` but not `sethostid` (gethostid.3 CONFORMING TO) |
| Exported | `gethostid@@GLIBC_2.2.5` (T), `sethostid@@GLIBC_2.2.5` (T) (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES table in gethostid.3; file-backed in glibc |
| Ledger ID | GLIBC-gethostid, GLIBC-sethostid |

## Declaration and gates

```c
#include <unistd.h>

int sethostid(long id);   /* unistd.h:924, __USE_MISC */
long gethostid(void);     /* unistd.h:1002, __USE_MISC || __USE_XOPEN_EXTENDED */
```

Man-page gates: `gethostid` needs `_DEFAULT_SOURCE || _XOPEN_SOURCE >= 500`
(since glibc 2.20); `sethostid` needs `_DEFAULT_SOURCE` since 2.21.

## Semantics

Both manage a 32-bit identifier meant to be unique for the machine --
historically resembling the host's IPv4 address, which is why it "usually
never needs to be set" (gethostid.3). In the glibc implementation the
value is stored in the file `/etc/hostid` (written by `sethostid`, which
is restricted to the superuser; before glibc 2.2 the file was
`/var/adm/hostid`). If `gethostid` cannot open that file it falls back to
heuristics: take `gethostname`, resolve it with `gethostbyname_r` to an
IPv4 address, and bit-twiddle that into a 32-bit value -- explicitly
documented as possibly non-unique (gethostid.3 NOTES). The manual keeps a
matching description (sysinfo.texi, *Host Identification*, functions at
lines 178-210). There is no syscall here at all: both are pure library
file/lookup operations.

## Gotchas and portability

- Cloud/VM images cloned from one template share the same `/etc/hostid`;
  the fallback path can return the *same* value for unrelated hosts whose
  hostname resolves to the same address, so never use it as a unique
  license or instance key without checking the file exists.
- `sethostid` writes `/etc/hostid` -- in a read-only root or a sandbox
  this fails with errno from the file operation (no separate man ERRORS
  list for it).
- The identifier is `long` in the prototype but only 32 bits meaningful
  (gethostid.3).
- musl 1.2.5: `gethostid` present (`include/unistd.h` line 144);
  **`sethostid` is absent** from the header and the tree -- a glibc-only
  writer.

## References

- man3: `gethostid.3` (covers `sethostid`; no man2 pages)
- glibc manual: `sysinfo.texi`, node *Host Identification*
- headers: `/usr/include/unistd.h` (lines 921-924, 1000-1002)
- symbols: `nm -D --with-symbol-versions libc.so.6`
