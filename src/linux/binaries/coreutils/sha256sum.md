# sha256sum — Compute and verify SHA-256 digests

## Overview

`sha256sum` prints a 256-bit SHA-256 digest of each input file (or stdin) and, with `-c`, verifies files against a saved digest list. It is the workhorse of the coreutils checksum family and the default integrity primitive of modern Linux operations: distribution ISO checksums, container image digests, package manifests, reproducible-build attestations, file-integrity monitoring baselines. When documentation says "checksum" without naming an algorithm in the 2020s, it means SHA-256.

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/sha256sum`. SHA-256 was designed by the NSA and published by NIST as FIPS 180-2 (2002); the tool joined coreutils with the SHA-2 generation. Not POSIX, but universal on Linux (including busybox), BSDs, and available everywhere via `shasum -a 256` or OpenSSL. Output format, `-c` protocol and flags are exactly the family interface documented in [`md5sum`](./md5sum.md); only the digest (64 hex characters) differs.

Reach for `sha256sum` as your default. Reach for [`sha512sum`](./sha512sum.md) when hashing huge files on 64-bit CPUs without hardware acceleration, or [`b2sum`](./b2sum.md) when you need speed plus tunable/keyed output. Reach away from MD5/SHA-1 (`./md5sum.md`, `./sha1sum.md`) whenever an adversary is in the threat model.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/sha256sum` |
| First appeared / lineage | SHA-256 (NIST FIPS 180-2, 2002); coreutils tool of the SHA-2 generation |
| Standards | Not POSIX; algorithm standardized by NIST FIPS 180 series |

## Synopsis

```
sha256sum [OPTION]... [FILE]...
```

```bash
sha256sum file.iso               # print 64-hex digest of file.iso
sha256sum -c SHA256SUMS          # verify files against a digest manifest
sha256sum --tag file.iso         # BSD-style tagged output
sha256sum -z -c sums0.sha256     # verify NUL-delimited checksum list
```

No `FILE` (or `FILE` `-`) reads standard input. The manifest line grammar — digest, two-character separator (space or `*`), filename — is the family format from [`md5sum`](./md5sum.md); `-c` also accepts BSD-tagged `SHA256 (file) = digest` lines.

## How It Works

### The algorithm in one paragraph

SHA-256 is a Merkle–Damgård hash over 512-bit blocks with a 256-bit chaining state of eight 32-bit words: 64 rounds per block of add/rotate/xor/choose/majority mixing driven by a fixed 64-word schedule, then the state serializes big-endian into 32 bytes — 64 hex characters. Unlike MD5 and SHA-1, no practical collision is known for SHA-256; collision resistance is expected at ~2^128 work and preimage at ~2^256, both safely beyond any projected adversary. It is also the SHA-2 member with dedicated CPU support: Intel/AMD SHA-NI instructions (and ARMv8 crypto extensions) accelerate exactly SHA-256's round function, which is why it is often the *fastest* secure choice in containers and VMs despite being a 32-bit-word design.

### The container-image digest connection

A container image reference pins content by digest, and that digest is a SHA-256 over the image's content-addressable layer blobs:

```
docker pull nginx:1.25
   │  registry resolves tag ──► manifest (a JSON document)
   ▼
manifest digest: sha256:4c0fdaa8b6341bfdeca5f1ec0f4a3d5c1a1a3a7b...   ← SHA-256 of the manifest bytes
   │
   ├─ layer blob  sha256:9d1a2c...   ← SHA-256 of each compressed layer tar
   └─ layer blob  sha256:650de6...
```

Every `sha256:` prefix you see in `docker images --digests`, `podman image inspect`, OCI descriptors, or a Dockerfile `FROM nginx@sha256:...` is the same primitive `sha256sum` computes — just computed over exact blobs by the registry client. Two operational habits follow:

1. `FROM image@sha256:digest` gives bit-reproducible pulls; the digest is verified by the engine the same way `sha256sum -c` verifies a manifest.
2. The digest of a *rebuilt* image changes even when the source didn't (timestamps, toolchain drift) — which is exactly why reproducible-build effort exists (below).

### Check mode

The `-c` flow is the family protocol from [`md5sum`](./md5sum.md): parse lines, recompute, print `file: OK` / `file: FAILED`, missing files as `FAILED open or read`, stderr `WARNING:` summary, exit 0 all-good / 1 any-failure. Modifiers `--quiet`, `--status`, `--strict`, `-w`, `--ignore-missing` behave identically. A real round trip:

```bash
$ printf 'hello\n' > f1.txt
$ sha256sum f1.txt > SHA256SUMS
$ cat SHA256SUMS
5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03  f1.txt
$ sha256sum -c SHA256SUMS
f1.txt: OK
$ printf 'tampered\n' > f1.txt
$ sha256sum -c SHA256SUMS
f1.txt: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

Distribution manifests — the `SHA256SUMS` next to ISO downloads, or Debian/Alpine package index checksums — are exactly this format, which is why scripts can verify them with one command and no parsing.

### Determinism and reproducible builds

A digest is only useful for attestation if the hashed bytes themselves are deterministic. Random access timestamps don't matter (they're metadata, not content), but embedded timestamps, gzip headers, build paths and file ordering inside archives do. The standard recipe for a stable tree digest:

```bash
# Content-deterministic tarball: fixed mtimes, fixed owner, sorted names, no pax headers
tar --sort=name --mtime='UTC 1970-01-01' --owner=0 --group=0 --numeric-owner \
    --format=ustar -cf - src/ | sha256sum
```

Build systems (Bazel, Nix, GNU make with checksum sources) and release pipelines rely on this discipline: hash canonicalized content, then the digest becomes a portable, comparable attestation token.

## Options That Matter

| Option | Effect |
|---|---|
| `-b`, `--binary` | `*` binary-mode separator on output lines (compat syntax on GNU) |
| `-t`, `--text` | Space text-mode separator (the default) |
| `--tag` | Emit BSD-style `SHA256 (file) = digest` lines |
| `-c`, `--check` | Verify a digest manifest instead of hashing |
| `--quiet` | During check, suppress `OK` lines; failures still print |
| `--status` | During check, print nothing; exit code is the only signal |
| `--strict` | Malformed manifest lines are fatal (nonzero exit) |
| `-w`, `--warn` | Warn (not fail) on malformed manifest lines |
| `--ignore-missing` | Skip manifest entries whose files are absent |
| `-z`, `--zero` | NUL-terminate records; pairs with `find -print0` / `xargs -0` |

Semantics identical across the family — see [`md5sum`](./md5sum.md) for per-flag walkthroughs and the escaped-filename rules.

## Usage Patterns

```bash
# Verify a downloaded ISO against the distribution's published checksums
sha256sum -c debian-CD-1.sha256 2>&1 | grep -v ': OK$'
```

```bash
# Pin a container base image bit-for-bit in a Dockerfile
# FROM debian:bookworm@sha256:<digest>
docker pull debian:bookworm && docker image inspect --format '{{.RepoDigests}}' debian
```

```bash
# Build a relocatable manifest for a tree (relative paths, sorted, NUL-safe)
cd /srv/app && find . -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
```

```bash
# Nightly integrity gate over that tree
cd /srv/app && sha256sum -c --quiet SHA256SUMS || echo 'config drift!'
```

```bash
# Hash a string exactly (no newline) — the version you usually want for tokens
printf '%s' "$token" | sha256sum | cut -d' ' -f1
```

```bash
# Digest of the same string WITH newline — different value, common bug source
echo "$token" | sha256sum | cut -d' ' -f1
```

```bash
# Feed only specific files (quoting handled by shell) into one manifest
sha256sum /etc/{passwd,group,shadow} > baseline.sha256
```

```bash
# Verify only files present in a partially checked-out release
sha256sum -c --ignore-missing SHA256SUMS
```

```bash
# Content-addressed dedup across directories
sha256sum dir1/* dir2/* | sort | awk 'seen[$1]++ {print $2}'
```

```bash
# Pipeline-friendly: keep only the digest itself for comparison in scripts
sha256sum image.raw | awk '{print $1}'
```

## Nuances and Gotchas

- **The newline tax.** `echo x | sha256sum` and `printf 'x' | sha256sum` differ. When comparing against a published digest for a string, reproduce the byte stream exactly. Most "hash doesn't match" support tickets are this.
- **Digest of the archive vs digest of its contents.** A `.tar.gz` digest covers the compressed bytes (gzip embeds a timestamp unless `gzip -n` is used); unpacked trees have no single canonical digest. Always be explicit about *what bytes* are being attested.
- **Rebuilt images change digest.** `FROM image@sha256:...` pins the registry bytes, not the source. CI caches and registry re-uploads can leave the same tag pointing at a different digest — query `RepoDigests` rather than trusting the tag.
- **Manifest paths are as-written.** Relative paths verify only from the right working directory; absolute paths make the manifest machine-bound. Filenames with newlines need the `\`-escape format or `-z` records — mechanics in [`md5sum`](./md5sum.md).
- **SHA-NI changes the performance ranking.** With hardware acceleration (most post-2016 x86, ARMv8 crypto extensions), SHA-256 outruns software-only rivals including BLAKE2 in many cases. Benchmark on your target fleet before picking "the fast one" — see [`sha512sum`](./sha512sum.md) for the 64-bit-words counterpoint.
- **`--status` still writes the stderr WARNING.** Silencing stdout is not silencing diagnostics; capture `2>/dev/null` only when you truly want the error invisible, or log stderr intentionally.
- **`sha256sum` vs `openssl dgst -sha256`.** Same digest, different output syntax (`<digest> <file>` vs `SHA2-256(file)= <digest>`); `-c` parses tagged lines but round-tripping across tools invites format drift.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Digests printed successfully, or every checked file passed |
| 1 | Any checked file `FAILED` / `FAILED open or read`, malformed manifest line under `--strict`, or open/read error while hashing |

`--status` keeps codes and drops output; `--quiet` drops `OK` lines; `-w` downgrades malformed-line complaints to warnings. Family-identical — worked combinations in [`md5sum`](./md5sum.md).

## Related Commands

- [`md5sum`](./md5sum.md) — anchor page: the shared manifest format, `-c` protocol and flag semantics.
- [`sha512sum`](./sha512sum.md) — 64-bit-word sibling; often faster on 64-bit CPUs without SHA-NI.
- [`sha1sum`](./sha1sum.md) — collision-broken predecessor; the migration source for most SHA-256 usage.
- [`sha224sum`](./sha224sum.md) — truncated SHA-256; same speed, niche ecosystem role.
- [`sha384sum`](./sha384sum.md) — truncated SHA-512; TLS heritage.
- [`b2sum`](./b2sum.md) — BLAKE2; tunable length and keyed mode when you outgrow plain SHA-256.
- [`wc`](./wc.md) — the other stream-measuring tool; commonly paired in one-pass inventory pipelines.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: Why is SHA-256 the default everywhere instead of the "stronger" SHA-512?

Digest strength is not the constraint — both are far beyond feasible attack. SHA-256 won on ecosystem momentum, 128-bit security margin considered ample, and hardware acceleration: SHA-NI makes it dramatically faster on modern CPUs. SHA-512's wider words can make it faster on 64-bit CPUs *without* acceleration, which is why the choice is workload- and fleet-dependent, but the default needs the fastest hardware-assisted, most-widely-supported option — that's SHA-256.

### Q: `docker pull debian@sha256:<digest>` — what exactly does the engine verify, and how does it relate to `sha256sum -c`?

The digest is SHA-256 over the image manifest bytes (the JSON listing layers). The engine pulls the manifest, hashes the received bytes, compares to the pinned digest — the same recompute-and-compare loop as `-c` — then verifies each referenced layer blob against its own `sha256:` descriptor. So one pinned digest transitively pins the whole image: content-addressing composes. `sha256sum -c` is the same protocol with a flat file list instead of a JSON graph.

### Q: Your CI builds "the same" artifact twice and `sha256sum` differs. Name four likely causes.

Embedded timestamps (zip/gzip headers, ELF build IDs), nondeterministic file ordering inside archives (tar without `--sort=name`), absolute build paths embedded by the toolchain, and environment-dependent codegen (different CPU flags, different compiler versions). The fixes are the reproducible-build canon: `gzip -n` or fixed mtimes, sorted/timestamp-normalized tarballs, `-ffile-prefix-map`, and pinned toolchains. The digest is honest — the *bytes* were genuinely different.

### Q: A vendor publishes only MD5 checksums. What's your verification posture?

Treat it as corruption detection, not tamper resistance. Accidental damage in transit is caught by any digest, so `md5sum -c` still has value. For tamper resistance you need an authenticated channel: fetch the manifest over TLS from the vendor's own host, or better their GPG-signed release file, and migrate your records to SHA-256. If the vendor offers no stronger channel, the checksum adds convenience, not security — worth stating explicitly in your threat model.

### Q: Why does a truncated hash (say SHA-256 cut to 128 bits) give only 64-bit collision resistance?

The birthday bound: among n-bit digests, a collision appears after roughly 2^(n/2) tries because any two inputs can match, not one against a fixed target. 128-bit output → ~2^64 collision work, which is within reach of organized attackers. Truncated-by-construction designs like SHA-224/SHA-384 also change the IV so the outputs aren't simple prefixes, but the security math of length vs birthday cost is the same — the reason short digest formats in URLs (git short SHAs are the everyday example) are fine for *naming*, never for *verification*.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sha256sum.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
