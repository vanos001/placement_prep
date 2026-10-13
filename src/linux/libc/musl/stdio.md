# musl: stdio

| Field | Value |
|---|---|
| musl version | 1.2.5 (WHATSNEW) |
| Key source files | `src/internal/stdio_impl.h`, `src/stdio/*.c` (incl. `stderr.c`, `stdout.c`, `__stdio_exit.c`, `__stdio_write.c`, `fmemopen.c`, `setvbuf.c`) |
| glibc counterpart pages | [fopen/fdopen/freopen/fclose](../glibc/stdio/fopen-fdopen-freopen-fclose.md), [setvbuf/setbuf family](../glibc/stdio/setvbuf-setbuf-setbuffer-setlinebuf.md), [fflush](../glibc/stdio/fflush.md), [printf family](../glibc/stdio/printf-printf-fprintf-dprintf-sprintf-snprintf-asprintf.md), [stream extensions](../glibc/stdio/stream-extensions-one-line-notes.md) |
| Ledger | MUSL-family-stdio / MUSL-family-stdio_ext rows; ledger-musl.md header families `stdio.h` (88), `stdio_ext.h` (1; parse artifact, 14 declared) |

## Implementation notes

The FILE object is `struct _IO_FILE` in `src/internal/stdio_impl.h`: read/write
cursor pairs (`rpos/rend`, `wpos/wbase`, `wend`), mode flags (`F_NORD`, `F_NOWR`,
`F_SVB`, `F_APP`), a per-stream `lock` word, and function pointers for
read/write/seek/close. `feof`, `ferror`, `getc_unlocked`, `putc_unlocked` are
macros over those fields. Streams live on the ofl list; `__stdio_exit()`
(`src/stdio/__stdio_exit.c`) walks it at exit, flushing pending output and
repositioning read streams. `stderr` is constructed with `buf_size = 0` and
`lbf = -1`, i.e. unbuffered by construction (`src/stdio/stderr.c`); `stdout`
keeps `lbf = '\n'` and `__stdout_write` demotes it to full buffering when the
fd is not a tty (`src/stdio/__stdout_write.c`). Flushes go out as a single
`writev` of buffer plus pending argument (`src/stdio/__stdio_write.c`).

## Deltas vs glibc (verified)

- Private struct: musl's `_IO_FILE` is its own ~30-field layout; glibc's is the
  libio `_IO_FILE` chain with exported `_IO_2_1_std*` objects (nm on libc.so.6).
- `%as` scanf: musl parses `a` as the C float conversion and implements only the
  C11 `m` allocation modifier (`src/stdio/vfscanf.c`); glibc treats `%as` as
  allocating. Code using `%as` misparses under musl.
- `setvbuf` reserves UNGET (8) bytes of a caller buffer and silently ignores
  undersized buffers (`src/stdio/setvbuf.c`).
- `fmemopen`/`open_memstream`/`open_wmemstream`/`fopencookie` all exist
  (`include/stdio.h`, `src/stdio/fmemopen.c`); no auto-wide behavior beyond
  what `fwide`/wide ops provide (no source for a wider claim; unverified).
- 1.2.5 WHATSNEW: `snprintf` no longer fails on `n > INT_MAX`.

## Porting notes

Take the address of `stdout`/`stderr`, rely on glibc's `_IO_` struct fields,
or use `%as` scanf and musl breaks. Buffers passed to `setvbuf` must leave
UNGET headroom. Symbol-versioned stdio references have no musl counterpart;
see the dynamic-loader page.
