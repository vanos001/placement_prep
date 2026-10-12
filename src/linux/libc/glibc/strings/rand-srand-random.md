# `rand` / `srand` / `rand_r` / `random` / `srandom` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | ISO C (`rand`, `srand`); POSIX.1-1995, marked obsolete in POSIX.1-2008 (`rand_r`); XSI/4.3BSD (`random`, `srandom`, `initstate`, `setstate`) |
| Exported | `rand@@GLIBC_2.2.5`, `srand@@GLIBC_2.2.5` (weak), `rand_r@@GLIBC_2.2.5`, `random@@GLIBC_2.2.5` (weak), `srandom@@GLIBC_2.2.5` (weak), `initstate@@GLIBC_2.2.5`, `setstate@@GLIBC_2.2.5`, `random_r@@GLIBC_2.2.5` (weak), `srandom_r@@GLIBC_2.2.5` (weak), `arc4random@@GLIBC_2.36` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe per ATTRIBUTES, but the sequence state is process-global (`rand(3)`, `random(3)`) |
| Ledger ID | GLIBC-rand, GLIBC-srand, GLIBC-rand_r, GLIBC-random, GLIBC-srandom, GLIBC-initstate, GLIBC-setstate |

## Declaration and gates

```c
#include <stdlib.h>

int  rand(void);
void srand(unsigned int seed);
int  rand_r(unsigned int *seedp);          /* _POSIX_C_SOURCE >= 199506L */

long random(void);                          /* _DEFAULT_SOURCE / XSI family */
void srandom(unsigned int seed);
char *initstate(unsigned int seed, char *statebuf, size_t statelen);
char *setstate(char *statebuf);
```

`RAND_MAX` is `2147483647` on glibc (`/usr/include/stdlib.h` line 87), the
largest 32-bit signed int; other libcs may define as little as 32767
(manual `math.texi` *ISO Random*). Gates: `random` family under
`__USE_MISC || __USE_XOPEN_EXTENDED` (`stdlib.h` lines 513-535),
`rand_r` under `__USE_POSIX199506` (lines 577-580).

## Semantics

`rand` returns the next pseudo-random integer in [0, RAND_MAX]; `srand`
re-seeds the sequence, and an unseeded program behaves as if
`srand(1)` had been called (`rand(3)`). In glibc `rand` just calls
`random` and `srand` aliases `srandom` (manual *ISO Random* source
comments: "Just calls random", "Alias to srandom"). `random` uses a
nonlinear additive feedback generator with a default 31-entry table,
range [0, 2^31 - 1], period about `16 * (2^31 - 1)` (`random(3)`).
`initstate` installs a caller-supplied state array (8 to 256 bytes;
optimal sizes 8, 32, 64, 128, 256) and returns the previous state;
`setstate` swaps state arrays (`random(3)`, manual *BSD Random*).

## Gotchas and portability

- Sequences are libc-specific: "the same seed, used in different C
  libraries or on different CPU types, will give you different random
  numbers" (manual *Pseudo-Random Numbers*). Never store or compare
  `rand()` streams across implementations; musl's `rand` is a different
  64-bit LCG entirely (`musl src/prng/rand.c`:
  `seed = 6364136223846793005ULL*seed + 1; return seed>>33;`).
- Not for cryptography or security: predictable state, shared process-wide.
  glibc 2.36 added the OpenBSD-derived `arc4random` family for that
  (NEWS under *Version 2.36*; nm `arc4random@@GLIBC_2.36`).
- Reproducibility in threads: global state makes `rand`/`random`
  unusable for per-thread reproducible streams; POSIX added `rand_r`,
  which the glibc manual calls "badly designed and unsuitable for serious
  work" because all state fits in an `unsigned int` (manual *ISO Random*),
  and POSIX.1-2008 marks it obsolete (`rand(3)` CONFORMING TO). The GNU
  `random_r` family (`struct random_data`) is the reentrant alternative.
- `initstate` bug: POSIX says return `NULL` on error, glibc sets `errno`
  but does not return `NULL` (`random(3)` BUGS).
- musl 1.2.5's `random` reimplements the BSD lagged Fibonacci with a fixed
  31-word state under a lock (`musl src/prng/random.c`); its `rand_r`
  is a tempered LCG (`src/prng/rand_r.c`).

## References

- glibc manual: `math.texi`, nodes *Pseudo-Random Numbers*, *ISO Random*,
  *BSD Random*
- man3: `rand(3)` (covers `srand`, `rand_r`), `random(3)` (covers
  `srandom`, `initstate`, `setstate`)
- header: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
