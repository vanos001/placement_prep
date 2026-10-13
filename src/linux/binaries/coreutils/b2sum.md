# b2sum — Compute and verify BLAKE2 digests

## Overview

`b2sum` prints a BLAKE2 digest of each input file (or stdin) and verifies saved digest lists with `-c`. BLAKE2 (RFC 7693) is the modern entry of the coreutils checksum family: designed for software speed — faster than MD5 on 64-bit CPUs while offering at least SHA-3-grade security — and parameterized, so the digest length is an option (`-l`) rather than a separate binary. Where the SHA family answers "pick a width, spawn a tool", BLAKE2 answers "one tool, choose 8-512 bits".

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/b2sum`, having joined coreutils in the 8.2x-era releases (early 2010s). Not POSIX, and less universally present than the SHA tools: busybox does not ship it, older enterprise images may not have it. Its lineage: BLAKE was a finalist in the SHA-3 competition; BLAKE2 is its tuned successor by Aumasson, Neves, Wilcox-O'Hearn and Winner-Pursey — the same competition that produced Keccak/SHA-3.

Reach for `b2sum` when you control both ends of the pipeline and want the fastest software hash with a tunable digest, or when a project (e.g. some backup tools, borg-style dedup designs, WireGuard-adjacent tooling, PyPI's blake2 usage) specifies it. Reach for [`sha256sum`](./sha256sum.md) when interoperability with published checksum lists matters — the ecosystem default — or when SHA-NI hardware makes SHA-256 the actual speed winner (see [`sha512sum`](./sha512sum.md) for that hardware story).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/b2sum` |
| First appeared / lineage | BLAKE2 (RFC 7693, 2013), successor of SHA-3 finalist BLAKE; added to GNU coreutils in the 8.2x era |
| Standards | Not POSIX; algorithm specified by RFC 7693 |

## Synopsis

```
b2sum [OPTION]... [FILE]...
```

```bash
b2sum file                       # print 128-hex BLAKE2b-512 digest
b2sum -l 256 file                # 64-hex digest: BLAKE2b-256 width
b2sum -c sums.b2                 # verify files against a digest list
b2sum -l 256 --tag file          # tagged output at a custom width
```

No `FILE` (or `FILE` `-`) reads standard input. Default digest is full BLAKE2b: 512 bits, 128 hex characters. Manifest line grammar and `-c` reporting follow the family interface from [`md5sum`](./md5sum.md).

## How It Works

### BLAKE2 in one paragraph

BLAKE2 is an ARX design (add-rotate-xor over a small state, in 64-bit words for BLAKE2b) structured as a wide-pipe Merkle–Damgård-ish permutation: 128-byte blocks, twelve rounds (reduced from BLAKE-512's sixteen by dropping nothing security-relevant — the simplification is itself a design point), with the message schedule drawn from fixed permutations. "Wide pipe" means the internal state is much larger than the output, and the finalization simply takes as many state bytes as the requested digest — which is exactly why `-l` exists and why truncation here is principled rather than an afterthought.

The speed claim comes from what it *omits*: no per-round table lookups, fewer rounds than its SHA-3-finalist ancestor, and a layout friendly to SIMD and 64-bit registers. Software BLAKE2b commonly beats MD5 itself on modern cores — the rare case of "more secure and faster than the broken one".

### The HAIFA frame and the parameter block

BLAKE2 is a HAIFA construction — a Merkle–Damgård refinement in which every compression call also receives a *block counter* and metadata. Two design elements follow, and both are visible in the tool's behavior:

- **The counter kills length extension.** SHA-2 digests famously permit the "resume the chain" trick against `HASH(secret || message)` layouts. BLAKE2 mixes the block index into every compression call and gates the final block with a flag, so a captured state cannot be extended into a longer valid message. That is why RFC 7693 can bless keyed BLAKE2 as a MAC without an HMAC wrapper.
- **The parameter block makes variants official.** The initial state (the IV, eight 64-bit words = 64 bytes) is XORed with a 64-byte parameter block:

```
 bytes 0-7    digest_length | key_length | fanout | depth | leaf_length
 bytes 8-15   node_offset (tree mode)
 bytes 16-31  node_depth, inner_length, reserved
 bytes 32-63  salt (16) + personalization (16)
```

Plain `b2sum` fixes everything except the digest length: `key_length=0`, `fanout=1`, `depth=1` (strictly sequential), all optional fields zero. That is also why `-l 256` is *not* "hash at 512 bits, then chop": the length is part of the initial state, making each width its own well-defined function (BLAKE2b-256, BLAKE2b-384, …) — the principled answer to the same problem SHA-224/SHA-384 solve with alternate IVs.

### One tool, many widths: `-l`

The headline difference from the SHA siblings:

```bash
$ echo hi | b2sum
7ea59e7a000ec003846b6607dfd5f9217b681dc1a81b0789b464c3995105d93083f7f0a86fca01a1bed27e9f9303ae58d01746e3b20443480bea56198e65bfc5  -
$ echo hi | b2sum -l 256
de9543b2ae1b2b87434a730727db17f5ac8b8c020b84a5cb8c5fbcc1423443ba  -
$ echo hi | b2sum -l 128
d34d45c68b57eca5c771e244c320c794  -
```

`-l/--length=BITS` accepts 8..512 in multiples of 8 (BLAKE2b's range); anything else fails loudly:

```bash
$ b2sum -l 100 f2.txt
b2sum: invalid length: '100'
b2sum: length is not a multiple of 8
```

In check mode the length is *inferred per line* from the digest width, so mixed-width manifests verify without flags:

```bash
$ b2sum -l 128 f2.txt > f2.b128
$ b2sum -l 128 -c f2.b128
f2.txt: OK
$ b2sum -c f2.b128          # no -l needed: width read from the line
f2.txt: OK
```

The inference is authoritative in check mode: passing `-l` alongside `-c` does not force a width — each line's digest length wins. A manifest mixing 128- and 512-bit lines verifies in one pass:

```bash
$ b2sum -l 128 f2.txt > mixed.b2 && b2sum f2.txt >> mixed.b2
$ b2sum -l 128 -c mixed.b2      # the -l is inert here
f2.txt: OK
f2.txt: OK
```

Convenient for migrations and width upgrades — but it also means the manifest, not your flags, decides what "verified" means (a gotcha covered below).

### Keyed mode: part of the design, partly outside coreutils

BLAKE2's signature feature is a **keyed mode** — a built-in MAC construction where a secret key is absorbed first, giving HMAC-like authentication without a separate HMAC layer. The RFC 7693 algorithm and the reference `b2sum` implementation expose it; the *coreutils* binary intentionally exposes only the unkeyed hash plus `-l`. Consequences for practice:

- `b2sum` output in coreutils is a plain digest — suitable for integrity manifests exactly like the SHA family's.
- If a specification calls for keyed BLAKE2 (secret-suffix file authentication), that is done through libraries or the reference tooling, not through this binary. Knowing the distinction is itself a standard interview probe.
- The related BLAKE2 constructions (BLAKE2bp/b, parallel variants, and the KDF mode BLAKE2s/BLAKE2X) are likewise library-side; coreutils ships the plain BLAKE2b tool.

Verify the absence locally — the help text is the contract:

```bash
$ b2sum --help
Usage: b2sum [OPTION]... [FILE]...
  -b, --binary          read in binary mode
  -c, --check           read checksums from the FILEs and check them
  -l, --length=BITS     digest length in bits; ...
  ...
```

(Truncated; the full option list contains no key-material flag in recent GNU coreutils, 9.x era.) Mechanically, RFC 7693's keyed mode sets `key_length` in the parameter block and absorbs the key zero-padded to a full 128-byte block *before* the message — the counter-and-flag construction then supplies what HMAC's outer layer would. From a shell, the HMAC-grade equivalent today is `openssl dgst -sha256 -hmac "$key"` or a library call; there is no flag to add.

### Tree mode lives in the spec, not in this tool

BLAKE2's parameter block includes fanout, depth, node-offset and inner-length fields precisely to support *tree hashing* — digesting disjoint chunks in parallel and combining their digests. The coreutils binary never sets them: it pins fanout=1, depth=1, the strictly sequential mode, so a single invocation is inherently single-threaded per file. Consequences:

- Large-file throughput scales with one core; there is no `-j` and no chunking.
- Parallelism must come *between* files: run several `b2sum` processes (`xargs -P`), or hash chunks yourself and hash the digests — a DIY Merkle tree.
- The designs that do this natively (BLAKE2bp/BLAKE2sp in the reference implementation, BLAKE3's binary tree) are library tools, not this applet.

```bash
# The only parallelism b2sum offers: across files. Sort afterwards to restore order.
find . -type f -print0 | xargs -0 -P "$(nproc)" -n 64 b2sum | LC_ALL=C sort -k2 > MANIFEST.b2
```

### Check mode and the family protocol

`-c` behaves as in [`md5sum`](./md5sum.md): parse, recompute, `file: OK` / `file: FAILED` / `FAILED open or read`, stderr `WARNING:` summary, exit 0/1, with `--quiet`, `--status`, `--strict`, `-w`, `--ignore-missing` semantics unchanged. The one family extension here: `-z` output ends lines with NUL and **disables filename escaping** (NUL can't appear in a name, so escaping is unnecessary and would only confuse consumers).

## Options That Matter

| Option | Effect |
|---|---|
| `-l`, `--length=BITS` | Digest length, multiple of 8, ≤ 512 (default 512); width inferred from lines in `-c` mode |
| `-c`, `--check` | Verify a digest manifest instead of hashing |
| `--tag` | BSD-style tagged lines: `BLAKE2b (file) = digest`, or `BLAKE2b-<bits> (file) = digest` with `-l` |
| `-b`, `--binary` | `*` binary-mode separator on output lines |
| `-t`, `--text` | Space text-mode separator (the default on GNU) |
| `--quiet` / `--status` | Suppress `OK` lines / suppress all check output |
| `--strict` / `-w` | Malformed manifest lines fatal / merely warned |
| `--ignore-missing` | Skip absent files during verification |
| `-z`, `--zero` | NUL-terminate records; disables filename escaping (unlike SHA tools) |

## Usage Patterns

```bash
# Default full-width digest — the drop-in family usage
b2sum backup.tar.zst
```

```bash
# SHA-256-width digest when a downstream schema reserves 64 hex chars
b2sum -l 256 artifact.bin
```

```bash
# Short 128-bit digests for quick local tree comparison (NOT for adversarial use)
find src -type f -print0 | sort -z | xargs -0 b2sum -l 128 > quick.b128
```

```bash
# Verify that manifest; width comes from the lines themselves
b2sum -c quick.b128
```

```bash
# NUL-safe tree manifest with the widest digest, relocatable via relative paths
cd /data && find . -type f -print0 | sort -z | xargs -0 b2sum -z > MANIFEST.b2
```

```bash
# Nightly silent gate
b2sum -c --status MANIFEST.b2 || echo 'drift detected'
```

```bash
# The newline lesson, BLAKE2 edition
printf 'payload' | b2sum -l 128
echo 'payload'   | b2sum -l 128
```

```bash
# Compare algorithm speed on your fleet before choosing
time b2sum 10G.img; time sha256sum 10G.img; time sha512sum 10G.img
```

```bash
# Tagged output for tooling that expects the BSD-style grammar
b2sum --tag -l 256 app.bin
```

```bash
# Recent coreutils also exposes BLAKE2b through cksum -a (same digest, tagged grammar)
cksum -a blake2b -l 256 artifact.bin
# BLAKE2b-256 (artifact.bin) = <64-hex digest>   # identical to b2sum --tag -l 256
```

```bash
# Cross-check the two tools agree byte-for-byte on a given width
diff <(b2sum -l 256 artifact.bin | cut -d' ' -f1) \
     <(cksum -a blake2b -l 256 --untagged artifact.bin | cut -d' ' -f1) && echo same
```

## Nuances and Gotchas

- **`-l` short digests shrink collision resistance.** Birthday math: a 128-bit digest has ~2^64 collision work. Fine for dedup/caching/local comparison; never for anything an attacker can feed. Choose width by threat model, not by aesthetics.
- **Keyed mode is not in coreutils b2sum.** The algorithm supports it (RFC 7693), the reference implementation exposes it, the coreutils binary does not. Promising "keyed b2sum" in a design doc will fail at implementation time.
- **Portability gap.** busybox lacks b2sum; minimal containers and old LTS images may too. Anything shipped to heterogeneous fleets needs a SHA fallback or a bundled static binary.
- **`-z` disables filename escaping.** In the SHA tools, `-z` and `\`-escaping coexist; here NUL records replace escaping entirely. Scripts parsing b2sum `-z` output must not expect `\n`-escapes — the difference is in the man page, and in interviews.
- **Width inference makes manifests self-describing.** Good for migration, but it also means a truncated digest line *verifies at its own width* — a manifest someone "shortened" by hand still passes. Treat manifest integrity as a channel problem (sign it), not a format problem.
- **No SHA-NI, but SIMD-friendly.** BLAKE2's speed on modern x86 comes from software design (and AVX2/AVX-512 vectorization in optimized builds); it can still lose to SHA-NI-backed SHA-256. Benchmark per fleet — see [`sha512sum`](./sha512sum.md) for the same caveat.
- **Not FIPS-approved.** NIST never standardized BLAKE2 — SHA-2/SHA-3 own the compliance world. In FIPS-140 environments b2sum output is off the menu regardless of its technical merits; that, more than speed, explains its niche.
- **Parallel `xargs -P` output is unordered.** Concurrent processes interleave complete lines — digest and filename stay atomic per line, but sort afterwards (`LC_ALL=C`) before diffing manifests.
- **`cksum -a blake2b` duplication cuts both ways.** One binary covering every digest feels like a replacement, but minimal and older images ship `b2sum` without the multiplexed `cksum` — portability favors the dedicated tool, feature breadth favors `cksum`.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Digests printed, or every checked file passed |
| 1 | Any checked file `FAILED` / `FAILED open or read`, malformed manifest line under `--strict`, invalid `-l` value, or open/read error while hashing |

Same `--status`/`--quiet`/`-w` behavior as the family — worked combinations in [`md5sum`](./md5sum.md).

## Related Commands

- [`sha512sum`](./sha512sum.md) — the same 64-bit-internal width class, fixed 512-bit output; the performance comparison partner.
- [`sha256sum`](./sha256sum.md) — ecosystem default; where interoperability outranks tunability.
- [`md5sum`](./md5sum.md) — anchor page for the family's manifest format and `-c` protocol.
- [`sha224sum`](./sha224sum.md) / [`sha384sum`](./sha384sum.md) — the fixed truncated widths b2sum generalizes via `-l`.
- [`sha1sum`](./sha1sum.md) — the broken middle child; historical context for why BLAKE2 exists.
- [`cksum`](./cksum.md) — recent coreutils multiplexer; `-a blake2b` computes the same digest (honoring `-l` widths).
- [`sum`](./sum.md) — legacy BSD/SysV checksum applets; the pre-MD5 history of this family.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: What does `-l` change in b2sum, and what are the security implications of a short value?

It selects the digest length in bits (8-512, multiples of 8) by truncating BLAKE2b's wide internal state at finalization. Security follows birthday bounds: n-bit digest ≈ 2^(n/2) collision work. `-l 128` therefore matches MD5's collision *size* — but with an unbroken function — acceptable for non-adversarial dedup, insufficient against chosen-input adversaries. In check mode the width is inferred per line, so mixed-width manifests work without flags.

### Q: BLAKE2 is faster than MD5 in software and unbroken — why does sha256sum still dominate?

Ecosystem and hardware. Every published checksum list, package index, and container digest speaks SHA-256, and SHA-NI makes SHA-256 hardware-accelerated on most modern CPUs, where it can outrun even BLAKE2. b2sum wins in closed pipelines that control both ends, need tunable or keyed digests, or run on hardware without SHA extensions. Defaulting to the most-interoperable, hardware-assisted option is the conservative operational call.

### Q: Where does BLAKE2's design lineage come from, and what did the designers deliberately drop?

From BLAKE, a SHA-3 competition finalist built around a ChaCha-like permutation; after Keccak won SHA-3, the BLAKE team shipped BLAKE2 as a faster, tightened successor. They kept the security core and removed the parts that only existed to mimic SHA-2's constant-time guarantees in hardware-hostile environments — fewer rounds, no table lookups — yielding software speed above MD5 with SHA-3-class margins. It's the rare case where "newer" means "simpler and faster" without weakening.

### Q: A teammate proposes "keyed BLAKE2 via b2sum" for authenticating nightly dumps. What's wrong at the tooling level?

Coreutils b2sum implements only unkeyed hashing plus `-l`; keyed mode lives in the RFC and in the reference implementation/libraries, not in this binary. The right moves: implement keyed BLAKE2 (or HMAC-SHA-256) through a library in the backup tool itself, or authenticate the digest file with a signature (`gpg --detach-sign`). The question checks whether a candidate confuses an algorithm's features with a specific binary's feature set.

### Q: How does b2sum's `-l` relate to how SHA-224 and SHA-384 achieve their widths?

Same goal, different mechanism. The SHA family bakes each truncated width in as a distinct standard: SHA-224/SHA-384 run their engine with alternate IVs and serialize a shortened state, so a separate binary exists per width. BLAKE2 instead carries the digest length in its parameter block, XORed into the initial state at startup — one algorithm, any width from 8 to 512 bits, one binary. The BLAKE2 approach is cleaner for tooling (its check mode even infers width per line); the SHA approach is what compliance ecosystems standardized on. The insight to land: both are domain-separation strategies, not "hash then chop".

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/b2sum.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
