# sha384sum — Compute and verify SHA-384 digests (truncated SHA-512)

## Overview

`sha384sum` prints a 384-bit SHA-384 digest of each input file (or stdin) and verifies saved digest lists with `-c`. SHA-384 is SHA-512 with a different initialization vector and the 512-bit output truncated to 384 bits (48 bytes, 96 hex characters) — the SHA-512-side twin of [`sha224sum`](./sha224sum.md) on the SHA-256 side. Like SHA-224, it exists mainly because protocol ecosystems standardized on the width: TLS 1.2 cipher suites, the TLS 1.3 signature repertoire, and a number of certificate and HSM profiles pin SHA-384.

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/sha384sum`. SHA-384 was defined alongside SHA-512 in the NIST FIPS 180 series; coreutils gained the tool in the same later wave as `sha224sum`. Not POSIX. Output format, `-c` protocol and flags are exactly the family interface from [`md5sum`](./md5sum.md); this page covers only the differences.

In day-to-day shell work `sha384sum` is rare — [`sha256sum`](./sha256sum.md) owns that space and [`sha512sum`](./sha512sum.md) the "wide digest" space. Where you *will* meet SHA-384 is in TLS handshakes (`TLS_AES_256_GCM_SHA384`), JWT/signature algorithms (`ES384`, `RS384`), and compliance-driven manifests. Knowing the tool means you can verify those artifacts from the shell instead of eyeballing hex from a library dump.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/sha384sum` |
| First appeared / lineage | SHA-384 (NIST FIPS 180 series, alongside SHA-512); added to GNU coreutils in the later SHA-2 wave |
| Standards | Not POSIX; algorithm standardized by NIST FIPS 180 series |

## Synopsis

```
sha384sum [OPTION]... [FILE]...
```

```bash
sha384sum file                   # print 96-hex digest of file
sha384sum -c sums.sha384         # verify files against a digest list
sha384sum --tag file             # BSD-style tagged output
sha384sum -z -c sums0.sha384     # verify NUL-delimited checksum list
```

No `FILE` (or `FILE` `-`) reads standard input. Manifest line grammar and check-mode reporting match [`md5sum`](./md5sum.md); `-c` also accepts BSD-tagged `SHA384 (file) = digest` lines.

## How It Works

### Truncated SHA-512, mechanically

SHA-384 runs the full SHA-512 compression function — 1024-bit blocks, 80 rounds of 64-bit-word mixing — but seeds the chaining state with alternate IV values and serializes only the first six of the eight final state words (384 of 512 bits). Operational consequences:

1. **Speed equals SHA-512.** Identical block size and round count; truncation is free. On 64-bit CPUs this is the SHA-2 *speed tier*, often faster than SHA-256 without SHA-NI — see [`sha512sum`](./sha512sum.md).
2. **No algebraic relationship to SHA-512 output.** The alternate IV diverges the computation; one digest cannot be derived from the other. Re-hash to get the sibling.
3. **Security margin stays high after truncation.** Collision work grows as half the output width: 384 bits → ~2^192, preimage ~2^384. Nothing about "truncated" means "weakened" at this scale; it means "protocol-sized".

### The precise construction

FIPS 180-4's recipe for SHA-384:

- **IV**: the first 64 bits of the fractional parts of the square roots of the *ninth through sixteenth* primes (23, 29, 31, 37, 41, 43, 47, 53) — exactly the primes SHA-224 uses, sampled 64 bits deep instead of 32. The family symmetry is literal: SHA-384's IV words are SHA-224's IV words concatenated in pairs (`c1059ed8` opens the first word of both).
- **Truncation**: the final eight-word state is serialized as `h0..h5` only — two words (128 bits) discarded. 6 × 64 bits = 384 bits = 96 hex characters.
- **Engine**: SHA-512's, unchanged — 1024-bit blocks, 80 rounds over eight 64-bit words, a 16-word message schedule expanded to 80 entries via `σ0 = ROTR¹⊕ROTR⁸⊕SHR⁷` and `σ1 = ROTR¹⁹⊕ROTR⁶¹⊕SHR⁶`, and a 128-bit length field in the padding (the 32-bit SHA-2 family uses 64 bits).

The SHA-2 family, in one table:

```
Member     Block     Words   Rounds   Output             Truncation
SHA-224    512 bit   8×32    64       224 bit (56 hex)   7 of 8 words, alt IV
SHA-256    512 bit   8×32    64       256 bit (64 hex)   none
SHA-384    1024 bit  8×64    80       384 bit (96 hex)   6 of 8 words, alt IV
SHA-512    1024 bit  8×64    80       512 bit (128 hex)  none
```

### 64-bit internals vs the 32-bit family

Every SHA-384 round is the same instruction mix as SHA-256's — add, rotate, xor, choose/majority — just over 64-bit operands. On a 64-bit CPU the operand width is free, so SHA-384 eats 1024-bit blocks at roughly SHA-256's per-round cost and usually wins in pure software. Three caveats keep the story honest:

- **Hardware flips the ranking.** x86 SHA-NI (mid-2010s Intel/AMD onward) accelerates SHA-256 only; ARMv8's base crypto extensions likewise. Some ARMv8.2+ cores optionally add SHA-512 instructions (FEAT_SHA512), but they are rare enough to treat as absent in capacity planning.
- **32-bit platforms pay double** for every 64-bit operation, making SHA-384 the wrong choice there.
- **Truncation is free but not a discount.** You pay for 80 rounds of 512-bit-engine work regardless of how many output words you serialize — SHA-384's speed is SHA-512's, full stop.

### The TLS heritage, concretely

TLS 1.3's flagship suite is literally named for the pairing: `TLS_AES_256_GCM_SHA384` — AES-256 for the record layer, SHA-384 for the transcript hash. TLS 1.2's `*_SHA384` MAC suites and the `RS384`/`ES384`/`PS384` families in JOSE/JWT carry the same choice. The pattern to internalize: whenever a protocol negotiates AES-256-class strength, it tends to reach for a 384-bit hash to keep the margin proportionate. That is the *entire* operational niche of SHA-384 — and the reason a systems engineer meets it in certificates, `openssl s_client` output, and JWT headers long before meeting the coreutils binary.

Watch the width appear on your own machine:

```bash
# Mint a self-signed certificate signed with SHA-384, then inspect it
openssl req -x509 -newkey rsa:2048 -nodes -keyout k.pem -out c.pem -days 1 \
  -sha384 -subj '/CN=example' 2>/dev/null
openssl x509 -in c.pem -noout -text | grep 'Signature Algorithm'
#     Signature Algorithm: sha384WithRSAEncryption      # tbsCertificate
#   Signature Algorithm: sha384WithRSAEncryption        # outer signature
```

Two lines, because an X.509 certificate records the algorithm both in the signed body (tbsCertificate) and in the outer signature wrapper — a verifier checks that they agree. Public web certificates show the same field; when CAs abandoned SHA-1, the replacements visible in `openssl x509 -text` were overwhelmingly sha256WithRSAEncryption and ecdsa-with-SHA256, with sha384/ecdsa-with-SHA384 at the top security tier.

### Same family, same protocol

Everything from [`md5sum`](./md5sum.md) applies verbatim — the `digest␣␣filename` line, `*` binary marker, `\`-escaped filenames, `-z` NUL records, `--tag`, and the `-c` flow (`OK`/`FAILED`/`FAILED open or read`, stderr `WARNING:` summary, exit 0/1) — with a 96-character digest field:

```bash
$ echo hi | sha384sum
4284b5694ca6c0d2cf4789a0b95ac8025c818de52304364be7cd2981b2d2edc685b322277ec25819962413d8c9b2c1f5  -
$ printf 'hello\n' > f1.txt && sha384sum f1.txt > f1.sha384
$ sha384sum -c f1.sha384
f1.txt: OK
```

### Where you meet SHA-384 in practice

Concrete sightings, all verifiable from a shell with OpenSSL installed:

```bash
# Certificate signature algorithms read ecdsa-with-SHA384 / sha384WithRSAEncryption
openssl x509 -in server.crt -noout -text | grep 'Signature Algorithm'

# The digest itself, OpenSSL grammar — same bytes sha384sum computes
$ openssl dgst -sha384 f1.txt
SHA2-384(f1.txt)= 1d0f284efe3edea4b9ca3bd514fa134b17eae361ccc7a1eefeff801b9bd6604e01f21f6bf249ef030599f0c218f2ba8c

# Same digest, coreutils grammar — the hex fields are identical
$ sha384sum f1.txt
1d0f284efe3edea4b9ca3bd514fa134b17eae361ccc7a1eefeff801b9bd6604e01f21f6bf249ef030599f0c218f2ba8c  f1.txt
```

The OpenSSL spelling differs (`SHA2-384(file)= ` with no space before the equals sign) — enough to break naive parsers expecting the coreutils two-space separator; one more reason to round-trip within a single toolchain. Beyond TLS: JOSE/JWT token algorithms `ES384`/`RS384`/`PS384`, HMAC-SHA-384 in webhook signing schemes, and FIPS-driven manifests that pair the digest with AES-256 at the 192-bit security class.

## Options That Matter

| Option | Effect |
|---|---|
| `-b`, `--binary` | `*` binary-mode separator on output lines |
| `-t`, `--text` | Space text-mode separator (the default on GNU) |
| `--tag` | Emit BSD-style `SHA384 (file) = digest` lines |
| `-c`, `--check` | Verify a digest manifest instead of hashing |
| `--quiet` / `--status` | Suppress `OK` lines / suppress all check output |
| `--strict` / `-w` | Malformed manifest lines fatal / merely warned |
| `--ignore-missing` | Skip absent files during verification |
| `-z`, `--zero` | NUL-terminate records; pairs with `find -print0`/`xargs -0` |

All semantics identical to [`md5sum`](./md5sum.md); refer there for edge cases.

## Usage Patterns

```bash
# Verify a compliance-driven manifest that mandates SHA-384
sha384sum -c --quiet baseline.sha384
```

```bash
# Generate such a manifest, NUL-safe and relocatable
find . -type f -print0 | sort -z | xargs -0 sha384sum > MANIFEST.sha384
```

```bash
# Confirm the newline lesson on this width
printf 'payload' | sha384sum
echo 'payload'   | sha384sum
```

```bash
# Cross-check a certificate against a tagged digest from an OpenSSL workflow
echo 'SHA384 (server.crt) = 6b1e...' | sha384sum -c -
```

```bash
# Benchmark intuition: SHA-384 runs at SHA-512 speed (64-bit words)
time sha384sum big.img; time sha256sum big.img
```

```bash
# Silent verification gate in a cron-driven integrity job
sha384sum -c --status MANIFEST.sha384 || logger -t integrity 'drift detected'
```

```bash
# Confirm OpenSSL and coreutils agree on digest bytes, not just format
# (-r = coreutils-compatible reversed output)
diff <(openssl dgst -sha384 -r f1.txt | cut -d' ' -f1) \
     <(sha384sum f1.txt | cut -d' ' -f1) && echo 'same digest'
```

```bash
# Family-generic generation: the tool name is the only variable
for tool in sha224sum sha256sum sha384sum sha512sum; do
  find . -type f -print0 | sort -z | xargs -0 "$tool" > "MANIFEST.${tool%sum}"
done
```

```bash
# Width-agnostic parsing on the separator, never on columns (96 hex chars!)
awk '{print length($1), $2}' MANIFEST.sha384 | sort -u
```

## Nuances and Gotchas

- **Rare in shell land, everywhere in protocol land.** If you found a `.sha384` manifest, it almost certainly came from a TLS/PKI/compliance pipeline rather than a sysadmin habit. Don't "normalize" it to SHA-256 — the width is usually contractual.
- **Performance is SHA-512's, not SHA-256's.** Same 1024-bit-block engine. On 64-bit CPUs without SHA-NI it can outpace SHA-256; with SHA-NI the ranking flips. Measure on your fleet — see [`sha512sum`](./sha512sum.md).
- **Family quirks inherited wholesale.** Relative-path sensitivity of manifests, escaped filenames, CRLF-corrupted manifests, `--strict` granularity — all as in [`md5sum`](./md5sum.md).
- **`sha384sum` vs `openssl dgst -sha384`.** Same digest, different output syntax; `-c` parses tagged lines, but mixing producers and verifiers across toolchains invites format drift. Round-trip within one tool when you can.
- **Not in busybox's default set.** Minimal images ship the big four checksum applets; `sha384sum` may be missing exactly where compliance tooling needs it — plan static binaries for rescue environments.
- **`SHA-384` vs `SHA-512/256` naming confusion.** FIPS 180-4's SHA-512/256 is a *different* 256-bit-output construction (SHA-512 engine, computed IV) — not "SHA-384 with more words chopped off". Protocol names rarely say which one they mean; read the spec, not the width.
- **OpenSSL grammar drift.** Depending on version, `openssl dgst -sha384` spells the digest name `SHA2-384` or `SHA384`, with variable spacing around `=`. Never parse OpenSSL output with coreutils column assumptions — the digest *bytes* agree, only the envelope differs.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Digests printed, or every checked file passed |
| 1 | Any checked file `FAILED` / `FAILED open or read`, malformed line under `--strict`, or an open/read error while hashing |

Identical family behavior under `--status`, `--quiet`, `-w`; worked examples in [`md5sum`](./md5sum.md).

## Related Commands

- [`sha512sum`](./sha512sum.md) — the full-width engine SHA-384 truncates; performance twin.
- [`sha256sum`](./sha256sum.md) — the everyday workhorse; default choice absent a protocol contract.
- [`sha224sum`](./sha224sum.md) — the SHA-256-side truncated twin; same niche logic, other ecosystem.
- [`md5sum`](./md5sum.md) — anchor page for the family's manifest format and `-c` protocol.
- [`sha1sum`](./sha1sum.md) — collision-broken sibling; migration source, never a destination.
- [`b2sum`](./b2sum.md) — variable-length digests via `-l`; the flexible alternative to fixed truncations.
- [`cksum`](./cksum.md) — `-a sha384` reproduces this digest in recent coreutils, tagged grammar identical.
- [`sum`](./sum.md) — legacy BSD/SysV checksums; the family's pre-cryptographic past.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: Why would a protocol pick SHA-384 rather than full SHA-512?

Proportionality and convention: a 384-bit digest pairs cleanly with 256-bit symmetric keys (the SHA-384/`TLS_AES_256_GCM_SHA384` convention), keeping hash and cipher security classes aligned without carrying unused width. Truncation also slightly shrinks signatures and transcript state. Mathematically SHA-384 inherits SHA-512's engine with ~2^192 collision resistance — far beyond need — so the choice is protocol ergonomics, not strength.

### Q: Is SHA-384 faster or slower than SHA-256, and why does the answer depend on the CPU?

The algorithm itself is SHA-512's: 1024-bit blocks of 64-bit-word operations, so on 64-bit CPUs without dedicated SHA hardware it processes more bits per instruction and often beats SHA-256. But SHA-256 has hardware support (Intel/AMD SHA-NI, ARMv8 crypto extensions) while SHA-384/SHA-512 do not — so on SHA-NI-equipped fleets SHA-256 wins decisively. Correct engineering answer: benchmark on the target hardware; see [`sha512sum`](./sha512sum.md) for the same trade at full width.

### Q: You find a file whose SHA-384 digest matches its SHA-512 digest in the first 96 hex chars. What does that tell you?

Effectively nothing unusual — but *not* because SHA-384 is a prefix of SHA-512's output. Truncated family members start from different IVs, so their state diverges from round one; a leading match that long would be an astronomical coincidence (2^-384), meaning you're looking at a mislabeled or fabricated value. The question tests whether candidates believe the "truncated = prefix" myth.

### Q: Your compliance framework demands SHA-384 manifests for backups. What operational traps follow from the tool family?

Traps are the family's, at 96-hex width: manifests must be generated from the backup root so relative paths survive restore-side verification; long line widths break naive column-parsing scripts and `cut -c` assumptions; CRLF transfer corrupts manifest parsing; and `--strict` is required if a corrupted manifest itself must alarm rather than silently verify nothing. Pair with `--status` for cron and keep stderr for the `WARNING:` summaries.

### Q: Why does SHA-384's IV use the same primes as SHA-224's, and what design principle does that illustrate?

Both truncated members needed a starting state independent of their full-width siblings, and NIST reused one derivation: fractional parts of square roots of the ninth through sixteenth primes, sampled 32 bits deep for SHA-224 and 64 bits deep for SHA-384. The principle is **domain separation**: the alternate IV guarantees SHA-384 and SHA-512 diverge from the first compression call, so no algebraic shortcut relates their outputs even though the engine is identical. It is the same idea as BLAKE2's digest-length parameter or SHA-512/256's computed IV — make every output width its own function, not a prefix of another.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sha384sum.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
