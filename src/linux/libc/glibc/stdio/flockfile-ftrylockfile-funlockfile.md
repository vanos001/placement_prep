# `flockfile` / `ftrylockfile` / `funlockfile` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-flockfile (group) |
| Header | `stdio.h` |
| Provenance | POSIX (stdio locking); glibc extras in `stdio_ext.h` |
| Status | documented |

**Signature** -- `void flockfile(FILE *stream);` `int ftrylockfile(FILE
*stream);` `void funlockfile(FILE *stream);`

**Semantics** -- acquire, try-acquire, and release a stream's internal
lock. The lock is *recursive* and tracks its owner: nested acquisitions
in one thread are counted, and exactly as many `funlockfile` calls are
needed to release it (manual, *Streams and Threads*). While held, no
other thread can lock the stream explicitly or implicitly. Typical use:
make a multi-call sequence (prompt + read, `fputs` + `fprintf`) atomic,
and wrap hot `_unlocked` loops:

```c
flockfile(fp);
while (cond)
   putc_unlocked(ch++, fp);
funlockfile(fp);
```

`ftrylockfile` returns `0` on success, nonzero when another thread holds
the lock; ignoring its result makes the paired `funlockfile` undefined.
glibc additionally offers `__fsetlocking` (`stdio_ext.h`) with
`FSETLOCKING_INTERNAL` / `FSETLOCKING_BYCALLER` / `FSETLOCKING_QUERY` to
switch implicit locking off stream-wide -- aimed at code that manages
locking itself. The `_unlocked` function set (POSIX: `getc_unlocked`,
`getchar_unlocked`, `putc_unlocked`, `putchar_unlocked`,
`fflush_unlocked`, `fgetc_unlocked`, `fputc_unlocked`; glibc adds
`feof_unlocked`, `ferror_unlocked`, `clearerr_unlocked`,
`fileno_unlocked`, `fgets_unlocked`, `fputs_unlocked`, `fread_unlocked`,
`fwrite_unlocked`) skips the implicit lock and is the documented fast
path -- historically these revived the pre-threads macro speed of
`getc`/`putc`.
