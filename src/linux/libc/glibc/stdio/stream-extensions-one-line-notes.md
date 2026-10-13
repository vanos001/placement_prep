# Stream extensions (one-line notes) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

Researched from the glibc manual, `stdio_ext(3)` and headers; no full
entries yet.

| Function(s) | Note |
|---|---|
| `fwide` | Set/query orientation (ISO C95, `wchar.h`); positive mode wide, negative narrow, 0 query; cannot re-orient an oriented stream (manual, *Streams and I18N*). |
| `wprintf` family (`fwprintf`, `swprintf`, `vwprintf`, `vfwprintf`, `vswprintf`) | Wide output; operates on the same streams; `swprintf` returns negative + `E2BIG` on overflow (GNU errno extension) unlike `snprintf`. |
| `wscanf` family (`fwscanf`, `swscanf`, `vwscanf`, `vfwscanf`, `vswscanf`) | Wide input mirrors `scanf`; wide-oriented streams only. |
| `fgetwc` / `fputwc` / `ungetwc` (+`_unlocked`, `getwc`, `getwchar`, `putwchar`, `fgetws`, `fputws`) | Wide character/string I/O; `WEOF` failure value; `_unlocked` wide variants are GNU. |
| `fmemopen` / `open_memstream` / `open_wmemstream` | Streams over memory: fixed buffer vs. grown malloc buffer whose pointer/size update at `fflush`/`fclose` (manual, *String Streams*); POSIX.1-2008; symbol `fmemopen` carries version `GLIBC_2.22` on installed glibc (reimplementation). |
| `fopencookie` | Custom streams via `cookie_io_functions_t` read/write/seek/close callbacks (manual, *Custom Streams*); GNU. |
| `__fbufsize`, `__flbf`, `__fpending`, `__fpurge`, `__freadable`, `__fwritable`, `__freading`, `__fwriting`, `__fsetlocking`, `_flushlbf` | Solaris-origin `stdio_ext.h` introspection: buffer size, line-buffered flag, pending output bytes, buffer discard, direction queries, locking mode, line-buffer flush (manual, *Streams and Threads* / *Flushing Buffers*). |
| `obstack_printf` / `obstack_vprintf` | `asprintf` variants allocating on an obstack (manual, *Dynamic Output*); GNU. |
| `parse_printf_format` / `printf_size` / `printf_size_info` | GNU template parsing and size-suffix conversions supporting custom `printf` handlers (manual, *Parsing a Template String*). |
| `register_printf_function` | Register custom conversion specifiers for the `printf` family (manual, *Customizing Printf*); glibc-specific, no ISO/POSIX counterpart -- treat as non-portable. |
| `fmtmsg` / `addseverity` | Strictly formatted messages to stderr/console with severity classes (manual, *Formatted Messages*); XSI origin. |
| `getw` / `putw` | SVID word I/O legacy, grouped above; no way to report a `-1` word via `getw`. |
