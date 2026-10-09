# sha224sum — Compute and verify SHA-224 digests (truncated SHA-256)

## Overview

`sha224sum` prints a 224-bit SHA-224 digest of each input file (or stdin) and verifies saved digest lists with `-c`. SHA-224 is not its own algorithm: it is SHA-256 with a different initialization vector and the output truncated from 256 to 224 bits (28 bytes, 56 hex characters). The tool exists so the coreutils checksum family covers every NIST digest size, but in practice it is the least-used member — most operational tooling standardizes on [`sha256sum`](./sha256sum.md) for the same security with a more familiar footprint.

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/sha224sum`. SHA-224 was added to the SHA-2 standard shortly after SHA-256 itself (FIPS 180 series) specifically to give TLS suites a 224-bit option, and coreutils grew the matching tool later than the md5/sha1/sha256/sha512 quartet. Not POSIX.

Reach for `sha224sum` when an external specification pins it: certain TLS-adjacent certificates, some smart-card and HSM ecosystems, and a handful of vendor manifests specify SHA-224. If nothing pins it, prefer SHA-256 — same cost, wider adoption, one less tool to explain. Everything about the output format, `-c` protocol and flags is identical to [`md5sum`](./md5sum.md); this page covers only what differs.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/sha224sum` |
| First appeared / lineage | SHA-224 (NIST FIPS 180 change notice, early 2000s); added to GNU coreutils later than the md5/sha1/sha256/sha512 quartet |
| Standards | Not POSIX; algorithm standardized by NIST FIPS 180 series |

## Synopsis

```
sha224sum [OPTION]... [FILE]...
```

```bash
sha224sum file                   # print 56-hex digest of file
sha224sum -c sums.sha224         # verify files against a digest list
sha224sum --tag file             # BSD-style tagged output
sha224sum -z -c sums0.sha224     # verify NUL-delimited checksum list
```

No `FILE` (or `FILE` `-`) means standard input. The manifest line format — digest, two-character separator, filename — and all check-mode reporting match [`md5sum`](./md5sum.md); `-c` also accepts BSD-tagged `SHA224 (file) = digest` lines.

## How It Works

### A truncated SHA-256, mechanically

SHA-224 is SHA-256 run with alternate initial chaining values (dropping the first eight bits of SHA-256's IV wording) and the final 256-bit state truncated to its first 224 bits. Two consequences matter operationally:

1. **Speed is identical to SHA-256.** The compression function, block size (512 bits) and round count are unchanged. There is no performance argument either way — the choice is purely about digest length and compatibility.
2. **A SHA-224 digest reveals nothing about the matching SHA-256 digest.** Truncation of the *output* is safe because the alternate IV already diverges the computation; you cannot compute one from the other without re-hashing the file.

Truncation in general is a standard way to buy collision resistance: a truncated n-bit hash has ~2^(n/2) collision cost and ~2^n preimage cost. At 224 bits, collision resistance (~2^112 work) remains far beyond any realistic adversary — the same security class as SHA-512/224-style constructions — so SHA-224 is *not* weak; it is merely niche.

### The precise construction

"SHA-256 with a different IV and a shortened output" nails the mechanics — the exact recipe per FIPS 180-4:

- **IV**: SHA-256 initializes `h0..h7` from the first 32 bits of the fractional parts of the square roots of the first eight primes (2, 3, 5, 7, 11, 13, 17, 19). SHA-224 instead uses the *ninth through sixteenth* primes (23, 29, 31, 37, 41, 43, 47, 53) — a completely different starting state, not a mutation of SHA-256's.
- **Truncation**: after the final block, the eight-word state is serialized as `h0..h6` only — the eighth word `h7` is discarded. 7 × 32 bits = 224 bits = 56 hex characters.
- **Everything else is SHA-256's engine**: 512-bit blocks, 64 rounds over eight 32-bit words, the same message-schedule expansion and round constants, the same padding with a 64-bit length field.

The SHA-2 family, in one table:

```
Member     Block     Words   Rounds   Output             Truncation
SHA-224    512 bit   8×32    64       224 bit (56 hex)   7 of 8 words, alt IV
SHA-256    512 bit   8×32    64       256 bit (64 hex)   none
SHA-384    1024 bit  8×64    80       384 bit (96 hex)   6 of 8 words, alt IV
SHA-512    1024 bit  8×64    80       512 bit (128 hex)  none
```

This is why the independence point above holds: the alternate IV means SHA-224's state diverges from SHA-256's at the very first compression call — the two digests are unrelated functions over shared machinery, deliberately so that neither width can be derived from the other.

### Digest-size trade-offs: who picks 224?

A 224-bit digest puts collision work at 2^112 and preimage at 2^224. NIST's security-strength tables map 112 bits to the legacy triple-DES symmetric class, so the pairing logic was: give protocols standardized on 112-bit-equivalent cryptography a matching hash. In practice SHA-224 gets chosen when:

- A **fixed protocol field or certificate profile** pins the width — some smart-card, payment-card and HSM ecosystems did exactly that.
- **Signature encodings** were sized for a narrower digest (ECDSA over P-224-class curves) and the hash should not exceed what the curve can actually sign.
- **Bandwidth/storage budgets** on embedded links treat every byte of an authentication tag as cost; 4 bytes saved per record across millions of records is real money.

What nobody chooses SHA-224 for is shell-side file manifests — there, [`sha256sum`](./sha256sum.md) costs nothing extra and interoperates with everything.

A naming trap before leaving the topic: FIPS 180-4 also defines **SHA-512/224** — the SHA-512 engine (1024-bit blocks, 64-bit words) with its own computed IV, output truncated to 224 bits. Same output size, different internals, and on 64-bit CPUs the SHA-512/224 route is *faster* than SHA-224. Coreutils exposes no separate binary for it; `sha224sum` is always the 32-bit-word construction.

### Same family, same protocol

Everything demonstrated in [`md5sum`](./md5sum.md) — the `digest␣␣filename` line, the `*` binary-mode marker, escaped filenames with the leading `\`, `-z` NUL records, `--tag`, and the full `-c` reporting flow (`OK`/`FAILED`/`FAILED open or read`, stderr `WARNING:` summary, exit 0/1) — applies here verbatim, with the digest field 56 characters wide:

```bash
$ echo hi | sha224sum
0689e590864cee67b037c8f4c390a75a192bb01160cc9c21374afb12  -
$ printf 'hello\n' > f1.txt && sha224sum f1.txt > f1.sha224
$ cat f1.sha224
2d6d67d91d0badcdd06cbbba1fe11538a68a37ec9c2e26457ceff12b  f1.txt
$ sha224sum -c f1.sha224
f1.txt: OK
```

The uniformity is deliberate: one verification protocol, one option set, five digest widths. Scripts that generalize over the family (parameterize the tool name, keep the flags) work unchanged.

### Verification behavior, worked

One corrupted file in a tree — verified output and exit code:

```bash
$ sha224sum f1.txt f2.txt > base.sha224
$ printf 'tampered\n' >> f2.txt
$ sha224sum -c base.sha224
f1.txt: OK
f2.txt: FAILED
sha224sum: WARNING: 1 computed checksum did NOT match
$ echo $?
1
```

The shape is the family contract at 56-hex width: per-file verdicts on stdout, the `WARNING:` aggregate on stderr, exit 1. In the family loop shown under Usage Patterns this exact transcript repeats for every member; only the digest column changes.

### Manifest-format interplay

The 56-hex digest field changes nothing about the format machinery — but two cross-tool facts are worth grounding:

- **`cksum` overlaps in recent coreutils.** The modern `cksum -a` option multiplexes digest algorithms with the same tagged output grammar:

```bash
$ cksum -a sha224 f1.txt
SHA224 (f1.txt) = 2d6d67d91d0badcdd06cbbba1fe11538a68a37ec9c2e26457ceff12b
$ sha224sum --tag f1.txt
SHA224 (f1.txt) = 2d6d67d91d0badcdd06cbbba1fe11538a68a37ec9c2e26457ceff12b
```

  Same digest, same tagged line — `sha224sum -c` happily verifies a manifest produced by `cksum -a sha224`, and vice versa. The value of `cksum -a` is one binary covering crc, md5, the SHA-2/SHA-3 widths and BLAKE2b; the value of `sha224sum` is that it exists everywhere, not just on recent coreutils.
- **Field-width parsers break; separator parsers don't.** Scripts assuming 32- or 64-hex digests misread 56-char lines. Parsing on the two-character mode separator (or `awk '{print $1}'`) is width-agnostic — the family-correct habit.

## Options That Matter

| Option | Effect |
|---|---|
| `-b`, `--binary` | `*` binary-mode separator on output lines |
| `-t`, `--text` | Space text-mode separator (the default on GNU) |
| `--tag` | Emit BSD-style `SHA224 (file) = digest` lines |
| `-c`, `--check` | Verify a digest manifest instead of hashing |
| `--quiet` / `--status` | Suppress `OK` lines / suppress all output (exit code only) |
| `--strict` / `-w` | Treat malformed manifest lines as errors / as warnings |
| `--ignore-missing` | Skip absent files during verification |
| `-z`, `--zero` | NUL-terminate records (input and output) |

All semantics identical to [`md5sum`](./md5sum.md); refer there for the edge cases.

## Usage Patterns

```bash
# Check a manifest whose specification (vendor, HSM tooling) mandates SHA-224
sha224sum -c --quiet firmware.sha224
```

```bash
# Generate that manifest in a NUL-safe, relocatable (relative-path) way
find . -type f -print0 | sort -z | xargs -0 sha224sum > MANIFEST.sha224
```

```bash
# Confirm the byte-exactness lesson: newline changes everything
printf 'payload' | sha224sum
echo 'payload'   | sha224sum
```

```bash
# Cross-verify the same file's SHA-224 against an OpenSSL-tagged line
echo 'SHA224 (key.pem) = 7f9a...' | sha224sum -c -
```

```bash
# Prove truncation doesn't leak the sibling digest — recompute both
sha224sum big.bin; sha256sum big.bin
```

```bash
# Silent nightly gate over a tree
sha224sum -c --status MANIFEST.sha224 || page_oncall
```

```bash
# Prove cksum and sha224sum are interchangeable before standardizing on either
diff <(cksum -a sha224 --untagged f1.txt) <(sha224sum f1.txt) && echo 'interchangeable'
```

```bash
# Family-generic manifest generator: the tool name is the only variable
for tool in md5sum sha1sum sha224sum sha256sum sha384sum sha512sum; do
  find . -type f -print0 | sort -z | xargs -0 "$tool" > "MANIFEST.${tool%sum}"
done
```

```bash
# Width-agnostic digest extraction — works for 32-, 40-, 56-, 64-, 96-, 128-hex alike
awk '{print $1}' MANIFEST.sha224
```

## Nuances and Gotchas

- **Niche by ecosystem, not by weakness.** Security at 224 bits is ample; the problem is that almost no publishing pipeline emits SHA-224 manifests, so you will mostly encounter it inside embedded/certificate tooling. Standardizing on [`sha256sum`](./sha256sum.md) avoids a second format for no gain.
- **No speed difference vs SHA-256.** Same 512-bit block machinery. If someone claims SHA-224 is "faster because shorter output", they are confusing digest truncation with cheaper computation — the compression work is identical.
- **Manifest format quirks are inherited wholesale.** Relative-path sensitivity, escaped filenames, CRLF-transferred manifests failing to parse, `--strict` granularity — all covered in [`md5sum`](./md5sum.md). They trip people identically here.
- **`sha224sum` vs `openssl dgst -sha224`.** Same digest; different output syntax (OpenSSL prints `SHA2-224(file)= digest` style depending on version). `-c` parses tagged lines, but round-tripping through OpenSSL output is where format surprises live — generate and verify with the same tool when possible.
- **busybox ships the big four only.** Minimal images typically provide md5sum/sha1sum/sha256sum/sha512sum applets; `sha224sum` may be absent. Rescue scripts should not depend on it.
- **SHA-224 ≠ SHA-512/224.** Same output width, different engines (32-bit-word SHA-256 machinery vs 64-bit-word SHA-512 machinery with a computed IV). A spec that says "SHA-512/224" is not satisfiable with this binary — confusing the two in a design review is a red flag.
- **The cksum overlap cuts both ways.** `cksum -a sha224` makes a separate binary feel redundant on recent coreutils, but minimal and older images ship `sha224sum` without the multiplexed `cksum` — portability arguments favor the dedicated tool, feature arguments favor `cksum`.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Digests printed, or every checked file passed |
| 1 | Any checked file failed (`FAILED` / `FAILED open or read`), malformed line under `--strict`, or an open/read error while hashing |

Identical family behavior under `--status`, `--quiet`, `-w`; see [`md5sum`](./md5sum.md) for worked examples of each combination.

## Related Commands

- [`sha256sum`](./sha256sum.md) — the full-width sibling; same speed, wider ecosystem support.
- [`md5sum`](./md5sum.md) — anchor page for the manifest format and `-c` protocol shared by the family.
- [`sha384sum`](./sha384sum.md) — the other truncated family member (from SHA-512 instead of SHA-256).
- [`sha512sum`](./sha512sum.md) — 64-bit-word sibling with different performance profile.
- [`sha1sum`](./sha1sum.md) — the collision-broken middle sibling this tool is not related to, but always confused with.
- [`b2sum`](./b2sum.md) — variable-length digests via `-l`; the modern way to "pick your width".
- [`cksum`](./cksum.md) — `-a sha224` reproduces this digest in recent coreutils, tagged grammar identical.
- [`sum`](./sum.md) — legacy BSD/SysV checksums; the family's pre-cryptographic past.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: Is SHA-224 a weaker hash than SHA-256?

No — it is SHA-256 with a different initial state and the output shortened to 224 bits. Collision work grows with half the output length (2^112 here, still infeasible) and preimage work with the full length. It exists for protocol ecosystems that standardized on the width (some TLS suites historically, certain certificate and HSM environments). Operationally it is *less* convenient, not less secure.

### Q: Given a file's SHA-224 digest, can you derive its SHA-256 digest? Why or why not?

No. Although the two share a compression function, SHA-224 starts from a different IV and truncates a different (diverged) final state. There is no algebraic path from one output to the other; you re-hash the input. The question tests whether a candidate understands that truncated hashes are not prefixes of the full hash's output stream in any exploitable sense.

### Q: When would you genuinely choose `sha224sum` over `sha256sum`?

Only when an external contract mandates the 224-bit width — a certificate profile, a vendor manifest, an HSM or smart-card pipeline that pins the digest. The tool then matters as an interoperability shim. Absent such a constraint, SHA-256 wins on ecosystem familiarity, available hardware acceleration (SHA-NI), and the fact that every reference manifest you will meet uses it.

### Q: Your verification script loops over `md5sum|sha1sum|sha224sum|sha256sum` with the same flags. Why does that work, and what breaks it?

It works because coreutils deliberately cloned the interface: identical output-line grammar, identical `-c` semantics, identical flag set and exit codes, so one generic wrapper suffices. It breaks on busybox (subset options, possibly missing `sha224sum`), on manifests from non-coreutils producers whose tagged lines differ, and if the script assumes digest length (parsing fixed widths like 32/40/56/64 hex chars instead of splitting on the separator).

### Q: SHA-224 and SHA-512/224 both output 224 bits. Which would you pick for a 64-bit-only fleet, and what must you give up?

SHA-512/224: its engine is the SHA-512 machinery — 1024-bit blocks of 64-bit word operations — which processes roughly twice the bits per round-cycle as the 32-bit-word SHA-256 engine SHA-224 uses, so it is typically faster on 64-bit cores. What you give up is tooling: coreutils exposes no `sha512/224sum`-style binary, so the digest must come from `openssl dgst` or a library, and its manifest would not interoperate with the coreutils family's `-c` protocol. The trade is exactly the sha256sum-vs-sha512sum performance story, cut down to a 224-bit output.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sha224sum.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
