# `tmpfile` / `tmpnam` / `mkstemp` / `mkdtemp` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-tmpfile (group) |
| Header | `stdio.h` (`tmpfile`, `tmpnam`); `stdlib.h` (`mkstemp`, `mkdtemp`) |
| Provenance | ISO C (`tmpfile`, `tmpnam`); SVID (`tempnam`, `tmpnam_r`); BSD (`mkstemp`, `mkdtemp`; `mkdtemp` from OpenBSD, manual) |
| Status | documented |

**Semantics** -- `tmpfile()` creates an unnamed temporary binary file in
update mode (`"wb+"`), unlinked at close or program termination -- the
safe default. `mkstemp(template)` replaces the trailing `XXXXXX`, opens
the file `O_EXCL` (creation is race-free by construction, manual), mode
`0600`, and returns the fd; `mkdtemp(template)` creates mode-`0700`
directory and returns the name or `NULL` with `errno` (`EINVAL` for a
bad template). Templates are modified in place and must not be string
constants.

**tmpnam is unsafe** -- it only *generates* a name; between generating
and opening, another process can claim it, the classic symlink race the
manual warns about for `tmpnam`, `tmpnam_r`, `tempnam` and `mktemp`
(manual, *Temporary Files*). `tmpnam(NULL)` also returns a pointer to a
static buffer (non-reentrant). The manual's fix: use `tmpfile` or
`mkstemp`, or open generated names with `O_EXCL`. `tempnam(dir, prefix)`
honors `$TMPDIR`, `dir`, `P_tmpdir`, `/tmp` in that order and mallocs
its result; `L_tmpnam`/`TMP_MAX` bound `tmpnam` names.

**References** -- `man3/mkstemp.3`, `man3/tmpnam.3`; glibc manual
*Temporary Files*.
