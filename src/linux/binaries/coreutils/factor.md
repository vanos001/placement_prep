# factor — print the prime factors of integers

## Overview

`factor` prints the prime factorization of each integer given on the command
line or standard input: `factor 60` prints `60: 2 2 3 5`. It handles
arbitrarily large integers (GNU builds link GMP when available), so the
practical limit is CPU time, not overflow. A number appears in the output
exactly once as itself when prime — `factor 97` prints `97: 97` — which
makes factor the classic "is this prime?" oracle in scripts.

Debian ships it in `coreutils` at `/usr/bin/factor`. It is one of the few
coreutils tools with no file, stream, or system role — a pure number-theory
utility in the same section as [`false`](./false.md) — inherited from the
BSD games heritage. It is not POSIX-standardized.

Practical uses are modest but real: primality checks in one-liners,
teaching demonstrations, generating prime lists (`factor $(seq ...) |
awk`), and breaking down sizes or counts during debugging. The interesting
engineering story — which is what interviews probe — is the algorithmic
progression from naive trial division to the Pollard rho/Pollard p−1
combination modern coreutils uses for large inputs.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/factor` on modern Debian/Ubuntu |
| First appeared / lineage | 5th/6th Edition UNIX (`/usr/games/factor` in BSD heritage); GNU version integrated into coreutils |
| Standards | Not POSIX-standardized; GNU and BSD extension |

## Synopsis

```
factor [NUMBER]...
factor OPTION
```

Main forms:

```bash
factor 60              # -> 60: 2 2 3 5
factor 97              # -> 97: 97    (prime: single factor, itself)
factor 12 18           # one output line per input
seq 2 30 | factor      # stdin mode: one number per line (or whitespace-separated)
```

## How It Works

### Output format

Each input produces one line: the number, a colon, then its prime factors
in ascending order with multiplicity:

```bash
$ factor 60
60: 2 2 3 5
$ factor 1234567890
1234567890: 2 3 3 5 3607 3803
$ factor 97
97: 97
$ factor 1
1:
$ factor 0
0:
```

Trivial cases: `1:` and `0:` print with no factors; negative numbers and
non-integers are rejected (a leading `-` looks like an option and fails the
option parser — `factor -- -5` also errors since there is no `--` for
operands here; pass negatives as... you can't: factor accepts non-negative
integers only).

### Algorithm progression

The command is a small case study in number-theory engineering:

1. **Trial division** (the historical implementation): divide by 2, then
   odd numbers up to `sqrt(n)`. Perfectly fine for 64-bit inputs with small
   factors; hopeless for `n = p·q` with both primes ~10^9+ — sqrt is 10^4.5,
   still fast — but for a 30-digit semiprime it would outlive the universe.
2. **Wheel + small-prime sieving**: modern coreutils first strips factors
   below a fixed bound (tens of thousands) cheaply, so everyday inputs are
   fully factored by trial division almost instantly.
3. **Probable-prime test**: what remains is checked with strong
   pseudoprime tests (Miller–Rabin-style bases) so composites are not
   declared prime.
4. **Pollard rho (Brent variant)**: splits composites in expected
   `O(n^(1/4))` per split — the workhorse that made 15–18 digit factors
   routine.
5. **Pollard p−1**: catches factors `p` where `p−1` is smooth, covering
   rho's worst cases.

Recursion splits the number until only primes remain. With GMP the same
pipeline runs on arbitrary precision, but there is no magic: a 2048-bit
RSA modulus is as hard for factor as for any tool — its security *depends*
on that.

```
     n ──► strip small primes (trial/wheel) ──► leftover
             │ fully factored                     │
             ▼                                    ▼
        print factors                 probable-prime test
                                            │           │
                                          prime       composite
                                            │           │
                                          print      Pollard rho / p−1
                                                    split, recurse ◄─┐
                                                                     │
                                                    back to probable-prime
```

### Primality test idiom

`factor` prints a lone number exactly when the input is prime:

```bash
$ factor 1000003
1000003: 1000003          # prime
$ factor 1000005
1000005: 3 5 66667        # composite
```

### Stdin mode

Without arguments, factor reads whitespace-separated numbers from stdin —
one output line per number — which is what makes the seq pipeline natural:

```bash
$ seq 1 10 | factor
1:
2: 2
3: 3
4: 2 2
...
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `--help` / `--version` | As usual |

There are no algorithm-selection flags; the implementation decides. (The
separate GNU `factor` from the *GMP-enabled* build differs from the
non-GMP build only in input range, not behavior.)

## Usage Patterns

```bash
# Is this number prime? (single factor = prime)
f=$(factor 2147483647); [ "$(echo $f | awk '{print NF}')" = 2 ] && echo prime
```

```bash
# Simpler primality check: output has exactly "N: N"
[ "$(factor 97)" = "97: 97" ] && echo prime
```

```bash
# List primes up to 100 via the seq pipeline
seq 2 100 | factor | awk 'NF==2{print $2}'
```

```bash
# Prime counting: how many primes below 10000?
seq 2 10000 | factor | awk 'NF==2' | wc -l
```

```bash
# Factor a file size to plan square-ish grid layouts
size=$(stat -c %s data.bin); factor "$size"
```

```bash
# Verify a multiplication puzzle by hand in CI
factor $((2 * 3 * 5 * 7))     # -> 210: 2 3 5 7
```

```bash
# Batch-factor numbers from a column of a CSV
cut -d, -f3 values.csv | factor
```

```bash
# Teaching: gcd via factorizations of two numbers
factor 48; factor 18          # common factors: 2 * 3 -> gcd 6
```

```bash
# Stress-ish demo: factor a Mersenne-flavored composite
factor $((2**61 - 1))         # prime (2305843009213693951: itself)
```

## Nuances and Gotchas

- **Negative inputs don't exist here.** `factor -5` is parsed as an option
  and fails with `invalid option`; there is no `--` escape that turns it
  into a number. Only non-negative integers are accepted.
- **`factor 0` and `factor 1` print `0:` / `1:`** — valid lines with no
  factors. Scripts counting fields (`NF`) must expect 1 field, not an
  error, for these inputs.
- **Performance cliff is real, not academic:** 64-bit worst cases
  (semiprimes of two ~32-bit primes) are fast with rho, but inputs beyond
  ~2^70 with two large prime factors can take minutes to days. GMP-enabled
  builds go further, but RSA-class numbers are out of reach by design.
- **Output multiplicity matters:** `60: 2 2 3 5` — two 2s. Scripts doing
  `sort -u` on factors or multiplying output back must account for
  multiplicity (`product of output == input` is the correctness invariant).
- **Stdin mode splits on any whitespace**, so `echo 12 18 | factor` gives
  two lines — convenient, but a CSV with spaces in the wrong column will
  silently produce unexpected factorizations of fragments.
- **Not POSIX, not on minimal systems:** busybox has `factor` only in some
  configurations; alpine images may lack it. Fallback: a 10-line shell/awk
  trial-division loop for small inputs.
- **No option to print *distinct* primes or exponents** — the format is
  frozen for compatibility; post-process with `uniq -c` for exponent form.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | All numbers factored and printed |
| nonzero | Unparseable input, invalid option, or value out of range |

`factor 99999999999999999999999999999999999999999999999999999` on a
non-GMP build reports an out-of-range error rather than a wrong answer —
the correct failure mode.

## Related Commands

- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- [`expr`](./expr.md) — the other coreutils numeric-operations tool (arithmetic expressions vs factorization)
- `seq` — feeds the prime-listing pipeline (coreutils; no separate page in this batch)

## Interview Questions

### Q: How can `factor` serve as a primality test, and what output pattern do you test for?

A prime's factorization is the number itself, so `factor N` prints exactly
`N: N` — one line, two fields, both equal. Compare the whole line or check
`NF == 2` after splitting. This is exact (no probabilistic false positive
*visible* to the user) and fast for 64-bit inputs thanks to the
small-prime strip + probable-prime test in modern implementations. For
scripting, `[ "$(factor N)" = "N: N" ]` is the cleanest spelling.

### Q: Describe the algorithmic layers modern GNU factor uses for a large composite, and why trial division alone is insufficient.

Modern factor first strips primes below a modest bound with trial division
(wheel), which settles nearly all everyday inputs. The leftover composite
is confirmed composite via strong probable-prime (Miller–Rabin-style)
testing, then split with Pollard rho (Brent's cycle-detection variant,
expected O(n^(1/4)) per split) with Pollard p−1 as a complement for
smooth `p−1` factors; splitting recurses until only primes remain. Trial
division alone is O(sqrt(n)) — fine at 10^9, astronomical at 10^18 — while
rho's n^(1/4) behavior is what makes 15+-digit factors tractable.

### Q: Write a one-liner that prints all primes below 1000 and explain each stage.

`seq 2 999 | factor | awk 'NF==2{print $2}'`. `seq` emits the candidate
range one per line; factor reads stdin and prints `n: p1 p2 ...` per line;
awk keeps lines with exactly two fields — the number and a single factor,
i.e. primes — and prints the second field. Composite lines have three or
more fields (e.g. `12: 2 2 3`) and are filtered out. Each stage is
streaming, so memory stays constant regardless of range size.

### Q: Why is factor's existence relevant to discussions of RSA security, and what does that say about running it on an RSA modulus?

RSA's hardness assumption is precisely that factoring the modulus is
infeasible; factor embodies that problem directly. Running
`factor <2048-bit modulus>` is safe to attempt and will not finish in any
human timescale — the tool will grind trial division/rho without progress.
The pedagogical point: algorithmic progress (trial division → rho →
number-field sieve research) is why key sizes grew from 512 to 2048+ bits,
and factor's own history mirrors the small end of that curve.

### Q: What happens with `factor 0`, `factor 1`, and a negative input, and why do these corner cases matter in scripts?

`factor 0` prints `0:` and `factor 1` prints `1:` — success status, zero
factors — so field-counting logic sees one field where a naive script
expects "at least the number plus one factor". A negative argument never
reaches the math: `-5` is consumed by the option parser (`invalid option`)
and the command fails. Scripts must therefore (a) treat 0/1 as valid
factor-free inputs, (b) validate non-negativity upstream, and (c) not rely
on `--` to protect negative operands.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/factor.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
