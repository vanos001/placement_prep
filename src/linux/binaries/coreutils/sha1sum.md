# sha1sum — Compute and verify SHA-1 message digests

## Overview

`sha1sum` prints a 160-bit SHA-1 digest of each input file (or stdin) and, with `-c`, verifies files against a saved digest list. It is the middle child of the coreutils checksum family: output format, flags, and exit codes are identical to [`md5sum`](./md5sum.md) — only the algorithm and the digest length (40 hex characters instead of 32) change.

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/sha1sum`. SHA-1 was designed by the US NSA and published by NIST as FIPS 180-1 in 1995; the tool entered GNU's userland with textutils and moved into coreutils with the rest of the checksum family. It is not POSIX, but it is present on every mainstream Linux system, on BSDs, and in busybox.

Reach for `sha1sum` today in exactly two situations: when a legacy artifact (old vendor manifest, older pipeline) demands it, or when you need a stronger-than-MD5 fingerprint in a context where collision resistance does not matter. For anything new, use [`sha256sum`](./sha256sum.md). The practical reason to still know SHA-1 deeply is archaeological and defensive: the world is full of SHA-1-based systems being retired, and interviews love the story of why.

It is often confused with `shasum` (the Perl implementation installed almost everywhere, which handles all SHA variants via `-a 1`), with `git hash-object` (SHA-1 underneath, but with header-prefix mangling), and with `openssl dgst -sha1` (same digest, OpenSSL output format).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/sha1sum` |
| First appeared / lineage | SHA-1 (NIST FIPS 180-1, 1995); tool from GNU textutils, merged into GNU coreutils |
| Standards | Not POSIX; algorithm standardized by NIST FIPS 180 series |

## Synopsis

```
sha1sum [OPTION]... [FILE]...
```

```bash
sha1sum file                     # print 40-hex digest of file
sha1sum -c sums.sha1             # verify files against a digest list
sha1sum --tag file               # BSD-style tagged output
sha1sum -z -c sums0.sha1         # verify NUL-delimited checksum list
```

With no `FILE`, or when `FILE` is `-`, standard input is read. The output line format — digest, two-character separator, filename — is byte-for-byte the format documented in [`./md5sum.md`](./md5sum.md); `-c` accepts both that format and BSD-tagged lines.

## How It Works

### From MD5 to SHA-1

SHA-1 shares its overall shape with MD5 — Merkle–Damgård padding, 512-bit blocks, a chaining state serialized as the final digest — but doubles the state: five 32-bit words instead of four, 80 mixing steps per block instead of 64, and a different round schedule with rotates instead of MD5's ad-hoc shifts. The output is five words big-endian serialized into 20 bytes, printed as 40 hex characters:

```bash
$ echo hi | sha1sum
55ca6286e3e4f4fba5d0448333fa99fc5a404a73  -
```

The bigger state and the more disciplined mixing are why SHA-1 resisted attack far longer than MD5 did: MD5 collisions fell in 2004, SHA-1's did not fall in practice until 2017. Speed is the trade: SHA-1 is noticeably slower than MD5 in software, and faster than neither, so it survives mostly where the digest itself is contractual, not cryptographic.

### Inside the 80-round compression function

The full pipeline, once per 512-bit block:

```
 message (any length)               512-bit block M
      │                                  │
      ├─ append 0x80                     ▼
      ├─ zero-fill to 56 bytes    ┌─────────────────────────────┐
      ├─ 64-bit big-endian        │ expand W[0..15] to W[0..79] │
      │  bit length               │ W[t]=ROTL¹(W[t-3]⊕W[t-8]    │
      ▼                           │       ⊕W[t-14]⊕W[t-16])     │
 pad to 512-bit boundary          └──────────────┬──────────────┘
      │                                          ▼
 state h0..h4  ◄── add ──── 80 rounds over (a,b,c,d,e)
 (160-bit chain)            in four 20-round groups
      ▼
 serialize big-endian → 20 bytes → 40 hex chars
```

Details worth being able to recite:

- **IV**: `h0..h4 = 67452301 EFCDAB89 98BADCFE 10325476 C3D2E1F0` — the first four words are exactly MD5's initial state, a visible fingerprint of the shared MD4 lineage.
- **Four round groups of twenty**, each with its own Boolean function over `b,c,d` (selection, parity, majority, parity) and its own additive constant: `0x5A827999`, `0x6ED9EBA1`, `0x8F1BBCDC`, `0xCA62C1D6` — the first 32 bits of the fractional parts of √2, √3, √5, √10.
- **Per round**: `temp = ROTL⁵(a) + f(group) + e + K + W[t]`, then the five registers shift one position with `c ← ROTL³⁰(b)`.
- **The cryptanalytic lever**: the schedule expansion rotates each new word in by a single bit, and every expanded word stays live for dozens of rounds — a regularity the 2005-era Wang-line differential attacks exploited to steer message differences through the rounds cheaply. SHA-2 and BLAKE2 both reworked their schedules specifically to break that regularity.

### The break, qualitatively

Two properties matter and they fail at different costs:

- **Collision resistance** — can you find *any* two different inputs with the same digest? Broken. Academic attacks since 2005 got steadily cheaper until 2017, when the "SHAttered" work demonstrated two real PDF files with identical SHA-1. The attack needed months of GPU/cloud computation, but it was a demonstration, not a theory — and the cost curve since has only gone down. Chosen-prefix collisions (adversary steers *both* inputs toward a shared digest) are the practically dangerous variant and are now within reach of well-funded attackers.
- **Preimage resistance** — given a digest, can you construct an input that hashes to it? Still infeasible for SHA-1. This is why old SHA-1 manifests still *detect accidental corruption* perfectly well.

Consequences in the wild: browser certificate authorities stopped issuing SHA-1 signatures in 2016-2017; NIST disallowed SHA-1 for signatures and mandated migration; Git moved to SHA-256 object hashing as an option (new repos / newer Git versions) precisely because of this history. A signature over a SHA-1 digest is only as strong as that digest's collision resistance, which is why the death of collision resistance kills signatures but not plain integrity checks.

### SHAttered and the chosen-prefix era

The 2017 SHAttered result (Google Research with CWI Amsterdam) made the threat concrete: two meaningfully different PDF files — thousands of words apart in their rendered content — sharing one SHA-1. In shell terms:

```bash
$ sha1sum shattered-1.pdf shattered-2.pdf
# <same digest>  shattered-1.pdf
# <same digest>  shattered-2.pdf    # identical SHA-1, different documents
```

(digests elided; the point is the equality). The attack was an *identical-prefix* collision — the two files share a common prefix and diverge inside a crafted ~128-byte region — and cost, by the team's own accounting, roughly 6,500 single-CPU years plus 110 single-GPU years of computation (≈2^63.1 hashes). Enormous, but a one-time demonstration that the cost curve bends toward the attacker.

Three years later the same community produced a practical *chosen-prefix* collision ("SHA-1 is a Shambles", 2020): the adversary picks two arbitrary starting contents and still steers them to a shared digest, at a GPU-rental cost the authors placed in the tens of thousands of dollars. Chosen-prefix is the variant that breaks signature workflows end to end — prepare a benign document and a malicious one, get the benign one signed, present the malicious one — and it is the reason ecosystems built on SHA-1 signatures treated 2020, not 2017, as the real deadline.

### Why Git moved away

Git's object IDs are SHA-1 over content plus a type/length header (see Nuances), which narrows but does not close the attack: an attacker who can mint chosen-prefix collisions can craft two objects a vulnerable Git would treat as identical. Git's interim defense was *hardened SHA-1* — counter-cryptanalysis that detects colliding inputs as they arrive and rejects them — and the long-term answer is a repository object format built on SHA-256, available in recent Git releases as an opt-in per-repository choice. The migration is deliberately slow because it invalidates every tool assuming 40-hex object names; the episode is a case study in how an ecosystem retires a broken hash without breaking itself.

### Check mode, in brief

`-c` works exactly as described in [`./md5sum.md`](./md5sum.md): parse lines, recompute, report `file: OK` / `file: FAILED`, missing files as `FAILED open or read`, one stderr `WARNING:` summary line, exit 0 or 1. The same `--quiet`, `--status`, `--strict`, `-w` and `--ignore-missing` modifiers apply with identical semantics — this uniformity across the family is the design win.

```bash
$ printf 'hello\n' > f1.txt
$ sha1sum f1.txt > f1.sha1
$ cat f1.sha1
f572d396fae9206628714fb2ce00f72e94f2258f  f1.txt
$ sha1sum -c f1.sha1
f1.txt: OK
```

### `-b`, `-t` and `--tag` in practice

```bash
$ printf 'hello\n' > f1.txt
$ sha1sum -b f1.txt
f572d396fae9206628714fb2ce00f72e94f2258f *f1.txt
$ sha1sum --tag f1.txt
SHA1 (f1.txt) = f572d396fae9206628714fb2ce00f72e94f2258f
```

`-b`/`-t` are heritage from systems where text and binary files differ (CRLF translation): the flag records the *mode marker* in the output — `*` versus a space — so `-c` can later re-apply the same mode. On GNU, both modes read identical bytes and produce identical digests, so the marker is bookkeeping, not semantics. The catch: on toolchains that *do* translate line endings, the same manifest can verify differently across platforms, which is why manifests crossing OS boundaries should be generated with `-b`.

`--tag` switches to the BSD grammar (`SHA1 (file) = digest`), which `-c` parses natively. Emitting both forms from one workflow costs nothing and lets each consumer pick — tagged lines survive round trips through tools that mangle the classic format's two-space separator.

### Performance notes

SHA-1 has no dedicated hardware acceleration on mainstream x86 (unlike SHA-256, which has the SHA-NI extensions, and SHA-512, which benefits from 64-bit arithmetic). Software SHA-1 runs at roughly 1-2 GB/s on modern cores — comfortably faster than any single disk, so I/O dominates in practice. If you find yourself caring about SHA-1 throughput, the correct fix is switching algorithms, not tuning.

## Options That Matter

| Option | Effect |
|---|---|
| `-b`, `--binary` | Mark output lines with the `*` binary-mode separator (no-op byte-wise on GNU) |
| `-t`, `--text` | Mark output lines with the space text-mode separator (the default) |
| `--tag` | Emit BSD-style `SHA1 (file) = digest` lines |
| `-c`, `--check` | Verify files listed in a digest manifest instead of hashing |
| `--quiet` | Suppress `OK` lines during check; keep failure reports |
| `--status` | Suppress all check output; exit code only |
| `--strict` | Improperly formatted manifest lines cause a nonzero exit |
| `-w`, `--warn` | Warn (but don't fail) on improperly formatted lines |
| `--ignore-missing` | Skip manifest entries whose files are absent |
| `-z`, `--zero` | NUL-terminate records; pairs with `find -print0`/`xargs -0` |

Every flag has exactly the same meaning as in [`md5sum`](./md5sum.md) and the other family members — see that page for the per-flag gotchas (path sensitivity of manifests, escaped filenames, `-z` mechanics).

## Usage Patterns

```bash
# Verify a legacy vendor manifest that predates SHA-256
sha1sum -c RELEASE-MD5SUMS.sha1 --quiet
```

```bash
# Generate the manifest matching that legacy format
find . -type f -print0 | sort -z | xargs -0 sha1sum > MANIFEST.sha1
```

```bash
# Same string, two transports: the newline is the difference
echo 'payload' | sha1sum
printf 'payload' | sha1sum
```

```bash
# Cross-check a file against a digest given in tagged format
echo 'SHA1 (app.jar) = 3a52ce780950d4fe955a8f1ae3c82d4fa1617d11' | sha1sum -c -
```

```bash
# Inventory a directory without blocking on huge files' I/O — digest as you copy
cp big.img /mnt/ && sha1sum big.img > big.img.sha1
```

```bash
# Scripted integrity gate: silent check, act on exit code
sha1sum -c --status manifest.sha1 || { echo 'integrity failure'; exit 1; }
```

```bash
# Compare two trees by digest only (run in each, then diff)
sha1sum $(find src -type f | sort) | sed 's|  .*/|  |' > /tmp/that-tree.sha1
```

```bash
# Find duplicate content among downloads by digest prefix
sha1sum *.iso | sort | uniq -w16 -D
```

```bash
# Baseline → change detection: re-hash and diff the manifests
sha1sum $(find . -type f | sort) > /tmp/before.sha1
# ...work, build, deploy...
sha1sum $(find . -type f | sort) > /tmp/after.sha1 && diff /tmp/before.sha1 /tmp/after.sha1
```

```bash
# Download-then-verify against a partial manifest, ignoring what was not fetched
sha1sum -c --quiet --ignore-missing MANIFEST.sha1
```

```bash
# Emit the BSD-tagged grammar and verify it straight back
sha1sum --tag app.tar.gz > app.tag && sha1sum -c app.tag
```

## Nuances and Gotchas

- **Do not use SHA-1 for anything collision-sensitive.** Signatures, certificates, deduplication of potentially adversarial content, file-integrity monitoring against attackers — all dead for SHA-1. Accidental-corruption checks are fine. The one-line interview answer: collision broken since 2017 (SHAttered), preimage still hard.
- **`shasum` vs `sha1sum`.** On many systems `shasum` is a Perl script, `sha1sum` is the C coreutils binary. Digests agree; output formats agree for the default mode; but option sets differ (`shasum -a 256` vs `sha256sum`) and scripts calling the wrong one break on minimal images that ship only coreutils.
- **Git interplay.** Git object IDs are SHA-1 over content *plus a type/size header*, so `sha1sum file` will not match `git hash-object file`. Interviewers probe exactly this confusion; the header (`blob <len>\0`) is the delta.
- **Manifests inherit all `md5sum -c` path quirks.** Relative paths are resolved from the current directory, filenames with newlines need the `\`-escape or `-z` treatment, and a manifest built over absolute paths only verifies in place. Details in [`./md5sum.md`](./md5sum.md).
- **busybox support is a subset.** `-c` and `-b` exist; `--tag`, `--status`, `--strict`, `--ignore-missing` do not. Keep embedded scripts to the core flags.
- **No upgrade path preserves digests.** SHA-1 and SHA-256 digests are unrelated — you cannot transform one manifest into the other without re-reading every file. Plan migrations as full re-hashing passes.
- **Identical-prefix vs chosen-prefix is the interview discriminator.** SHAttered (2017) needed a shared file prefix; the 2020 chosen-prefix work does not. Signatures, key material, and content-addressed stores fall to the chosen-prefix variant; "my ISO manifest still verifies" survives both — for now.
- **The x86 SHA extensions include SHA-1 instructions** (`SHA1RNDS4` et al.) that nobody ships performance paths on — dead algorithm, dead silicon. The software-only throughput picture stands; the pedantic exception makes a good aside.
- **Dedup built on SHA-1 is a live attack surface, not just legacy debt.** A storage system that accepts third-party uploads and deduplicates by SHA-1 lets an attacker deliberately plant or retrieve the wrong object; integrity-against-accidents is not the same property.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Digests printed successfully, or every checked file passed |
| 1 | Any checked file failed (`FAILED` / `FAILED open or read`), or an improperly formatted line with `--strict`, or an open/read error while hashing |

`--status` keeps the same codes with no output; `--warn` warns about malformed lines without failing. Family-identical semantics — see [`md5sum`](./md5sum.md) for the worked examples.

## Related Commands

- [`md5sum`](./md5sum.md) — anchor page: shared manifest format, `-c` protocol, and all flag semantics.
- [`sha256sum`](./sha256sum.md) — the standard replacement for SHA-1 in new designs.
- [`sha512sum`](./sha512sum.md) — wider sibling; often faster on 64-bit CPUs due to word width.
- [`sha224sum`](./sha224sum.md) — truncated SHA-256 variant, same tool family.
- [`sha384sum`](./sha384sum.md) — truncated SHA-512 variant, TLS heritage.
- [`b2sum`](./b2sum.md) — BLAKE2: modern fast alternative with variable-length output.
- [`cksum`](./cksum.md) — multiplexed checksum tool; `-a sha1` computes this same digest in recent coreutils.
- [`sum`](./sum.md) — the legacy BSD/SysV checksum applets; the family's pre-cryptographic ancestor.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: SHA-1 was "broken" in 2017 — yet `sha1sum -c` still catches corrupted downloads. Explain.

Two different security properties collapsed at different times. Collision resistance (finding any two inputs with equal digests) fell: SHAttered produced two distinct PDFs with the same SHA-1, which destroys digital signatures over SHA-1 because an attacker can prepare two documents, get the benign one signed, and swap in the malicious one. Preimage resistance (constructing input for a *given* digest) is unbroken, so recomputing a SHA-1 digest over a downloaded file still detects accidental corruption — the attacker can't steer the corruption to match your manifest unless they also control the manifest.

### Q: Why does `sha1sum file` disagree with `git hash-object file` for the same file?

Git doesn't hash raw content. It prepends `blob <size>` and a NUL byte, then applies SHA-1, so the input streams differ. This is by design — the header binds object type and length into the digest, preventing type-confusion substitutions. Same lesson as `echo` vs `printf` for `sha1sum` itself: identical *content* hashed over different *byte streams* yields different digests.

### Q: You inherit a build pipeline pinned to SHA-1 manifests. Walk through the migration.

Re-hash everything once into a SHA-256 manifest (`find -print0 | sort -z | xargs -0 sha256sum`) since digest formats don't convert; keep both manifests during a transition window so old and new nodes verify against their own format; switch the publisher first, then consumers, because `-c` on a missing-format manifest fails fast and loudly. Decide explicitly what the digest is protecting: if it guards against adversaries, the SHA-1 era must end even if operations are smooth, and the manifest distribution channel (TLS or signatures) matters as much as the algorithm.

### Q: Why did certificate authorities have to drop SHA-1 before Git did?

A CA signature is a collision-resistance bet: an attacker who can construct two certificates with equal SHA-1 can get the harmless one signed and present the malicious one as valid. Browsers accept certificates from *any* CA in the trust store, so one weak link poisons the whole web PKI — the cost of an attack is private, the payoff is universal. Git's SHA-1 usage, by contrast, is repository-internal: an attacker would need to inject a colliding object into *your* repo under your control, a far narrower attack surface, which bought Git a decade of grace before the SHA-256 transition.

### Q: What's the practical difference between `sha1sum` and `shasum`?

Both implement SHA-1 and emit the same coreutils-style output for default invocations, so manifests interop. `sha1sum` is the compiled C coreutils binary (guaranteed on any Debian/Ubuntu, no Perl runtime), `shasum` is a Perl script that also multiplexes the other SHA variants via `-a`. Scripts that must run on minimal containers or rescue environments should call the coreutils names; `shasum` belongs where its option superset is genuinely needed.

### Q: MD5 collapsed in 2004 and SHA-1 held until 2017 — what did the extra margin buy, structurally?

Design margin, concretely: five 32-bit state words instead of four, 80 rounds instead of 64, more rotation per step, and constants derived from square roots rather than MD5's arbitrary-looking table. The 2005-era differential attacks still worked in principle — because the message-schedule expansion kept MD4's single-rotate regularity — but the added rounds and state made every step of the attack orders of magnitude more expensive, stretching the practical break from "laptop" to "supercomputer fleet". The lesson: structure determines whether an attack class exists; dimensions (rounds, width) determine when it lands.

### Q: Name two uses of SHA-1 that remain defensible today, and two that are malpractice.

Defensible: legacy manifest verification where the digest guards against accidental corruption and the manifest travels over an authenticated channel; and inert fingerprints in closed, non-adversarial systems (cache keys, dedup of trusted content) where rewriting buys nothing. Malpractice: any signature or certificate path over SHA-1 — chosen-prefix collisions make the sign-benign/present-malicious swap practical — and dedup or content-addressed storage of third-party-submittable content, where an attacker can deliberately plant a colliding object.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sha1sum.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
