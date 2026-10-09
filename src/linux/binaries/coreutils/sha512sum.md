# sha512sum — Compute and verify SHA-512 digests

## Overview

`sha512sum` prints a 512-bit SHA-512 digest of each input file (or stdin) and, with `-c`, verifies files against a saved digest list. It is the widest member of the coreutils SHA-2 set and the performance counterweight to [`sha256sum`](./sha256sum.md): built on 64-bit word arithmetic, it frequently outruns SHA-256 in software on 64-bit CPUs — yet it lacks the dedicated hardware acceleration that SHA-256 enjoys, so the "which is faster" answer is genuinely machine-dependent.

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/sha512sum`. SHA-512 was published by NIST as part of FIPS 180-2 (2002) alongside SHA-256; the coreutils tool arrived with the SHA-2 generation. Not POSIX, but present on every mainstream Linux system (including busybox) and BSDs. Output format, `-c` protocol and flags are exactly the family interface documented in [`md5sum`](./md5sum.md); only the digest — 128 hex characters — differs.

Reach for `sha512sum` when hashing large files on 64-bit hardware without SHA-NI (bulk backups, VM images, nightly tree snapshots), when a specification demands the 512-bit width (some signing pipelines, some compliance frameworks), or when generating long-lived high-margin fingerprints. Note the password-hashing namesake: `/etc/shadow`'s `$6$` hashes are SHA-512-based *crypt* — a salted, deliberately slow derivation, not `sha512sum` output; the similarity in name is a classic interview trap.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/sha512sum` |
| First appeared / lineage | SHA-512 (NIST FIPS 180-2, 2002); coreutils tool of the SHA-2 generation |
| Standards | Not POSIX; algorithm standardized by NIST FIPS 180 series |

## Synopsis

```
sha512sum [OPTION]... [FILE]...
```

```bash
sha512sum file                   # print 128-hex digest of file
sha512sum -c sums.sha512         # verify files against a digest list
sha512sum --tag file             # BSD-style tagged output
sha512sum -z -c sums0.sha512     # verify NUL-delimited checksum list
```

No `FILE` (or `FILE` `-`) reads standard input. Manifest line grammar and check-mode reporting match [`md5sum`](./md5sum.md); `-c` also accepts BSD-tagged `SHA512 (file) = digest` lines.

## How It Works

### 64-bit words change the economics

SHA-512's block is twice SHA-256's: 1024 bits per block, mixed through 80 rounds over **eight 64-bit words** (SHA-256: 64 rounds over eight 32-bit words). Three consequences follow:

1. **More bits per operation on 64-bit CPUs.** Adds, rotates and shifts cost the same instruction count whether the word is 32 or 64 bits, so SHA-512 chews through roughly twice the input per round-cycle. On a modern x86-64 core without SHA extensions, software SHA-512 typically reaches ~2 GB/s where software SHA-256 sits near ~1 GB/s — often the fastest *secure software-only* option in the family.
2. **Half the block iterations for the same file.** A 1 GiB input is 2^20 SHA-512 blocks but 2^21 SHA-256 blocks. Compression dominates runtime; the wider block wins.
3. **No hardware acceleration — for now.** Intel/AMD's SHA-NI and ARMv8 crypto extensions accelerate SHA-256 only. On such fleets SHA-256 pulls decisively ahead (multi-GB/s with a handful of cycles per round), inverting the software ranking. The x86-64 vector-SHA-512 story has only arrived piecemeal via newer extensions; assume software-only on older fleets.

The practical decision table:

```
                        SHA-NI / ARM crypto?    choice
64-bit CPU, no accel        no                  sha512sum (usually)
modern x86/ARM w/ accel     yes                 sha256sum (usually)
32-bit CPU                  -                   sha256sum (64-bit ops costly)
                            → benchmark on your fleet; I/O may dominate anyway
```

For most operational jobs — backups over gigabit or slower links, verifying a tree from spinning disk — the disk is the bottleneck and either tool is free.

### One block, end to end

The complete SHA-512 pipeline for one message:

```
 message                pad: 0x80, zeros, 128-bit big-endian bit length
   │                    ─────────────────────────────────────────────
   ▼                          1024-bit block
 split into 16×64-bit words W[0..15]
   ▼
 expand to 80:  σ0 = ROTR¹⊕ROTR⁸⊕SHR⁷   σ1 = ROTR¹⁹⊕ROTR⁶¹⊕SHR⁶
                W[t] = σ1(W[t-2]) + W[t-7] + σ0(W[t-15]) + W[t-16]
   ▼
 80 rounds over eight 64-bit registers (a..h):
   T1 = h + Σ1(e) + Ch(e,f,g) + K[t] + W[t]
   T2 = Σ0(a) + Maj(a,b,c)       Σ1 = ROTR¹⁴⊕ROTR¹⁸⊕ROTR⁴¹
   h←g  g←f  f←e  e←d+T1         Σ0 = ROTR²⁸⊕ROTR³⁴⊕ROTR³⁹
   c←b  b←a  a←T1+T2             Ch/Maj as in SHA-256
   ▼
 add the round output into the 512-bit chaining state
   ▼
 after the last block: serialize big-endian → 64 bytes → 128 hex chars
```

- **Constants**: the 80 round constants `K[t]` are the first 64 bits of the fractional parts of the *cube roots* of the first 80 primes — a "nothing up my sleeve" table in the same spirit as the square-root-derived IV.
- **128-bit length field**: the 64-bit family pads the message length into 128 bits (SHA-256 uses 64). Pure headroom today, but SHA-512's padding is unambiguous for any input that will ever exist.
- **80 rounds vs SHA-256's 64**, at twice the state width: preimage resistance is 2^512 against SHA-256's 2^256; collision resistance stays birthday-bound at 2^256 for both.

### The hardware question, sharpened

SHA-256's speed crown on modern x86 comes from the SHA extensions (SHA-NI): a handful of added instructions that collapse each round's mixing into near-single-cycle work, shipping in mainstream Intel and AMD cores since roughly the mid-2010s. SHA-512 got no x86 equivalent — which is why the software ranking inverts wherever SHA-NI is present. Two refinements to the simple story:

- **ARM is not symmetric.** ARMv8's base crypto extensions accelerate SHA-256 (and SHA-1); SHA-512 support (FEAT_SHA512) exists only as an optional ARMv8.2 addition that many cores omit. On x86 the gap is structural.
- **Vectorized software narrows, not closes, the gap.** AVX2/AVX-512 SHA-512 implementations recover some throughput, which is why the delta differs between a plain build and an optimized library — one more argument for benchmarking the exact binaries you deploy.

### Check mode

Family protocol from [`md5sum`](./md5sum.md): parse lines, recompute, report `file: OK` / `file: FAILED`, missing files as `FAILED open or read`, stderr `WARNING:` summary, exit 0/1; `--quiet`, `--status`, `--strict`, `-w`, `--ignore-missing` all behave identically. Live round trip:

```bash
$ printf 'hello\n' > f1.txt
$ sha512sum f1.txt > f1.sha512
$ cat f1.sha512
e7c22b994c59d9cf2b48e549b1e24666636045930d3da7c1acb299d...
$ sha512sum -c f1.sha512
f1.txt: OK
```

(The 128-hex digest is too wide for a page column — trust the tool, not the typography.)

### Checksum-file workflows, worked

The full failure surface, with verified outputs:

```bash
$ printf 'hello\n' > present.txt
$ sha512sum present.txt > m.sha512
$ echo "0000...0000  absent.txt" >> m.sha512   # 128 zeros: entry for a missing file
$ sha512sum -c m.sha512
present.txt: OK
absent.txt: FAILED open or read
sha512sum: absent.txt: No such file or directory
sha512sum: WARNING: 1 listed file could not be read
```

(The first two lines are stdout; the `sha512sum:` lines are stderr — in a terminal they interleave.) A missing file is a *read* failure, not a digest mismatch, and the aggregate travels on stderr in the `WARNING:` line — the part cron jobs should capture. The modifiers slice the report three ways:

```bash
$ sha512sum -c --ignore-missing m.sha512
present.txt: OK                       # absent.txt silently skipped, exit 0
$ sha512sum -c --quiet m.sha512
absent.txt: FAILED open or read       # only failures reported, exit 1
$ sha512sum -c --status m.sha512      # nothing at all; the exit code is the report
```

`--ignore-missing` suits partial restores; `--quiet` suits human eyes over large trees; `--status` suits automation that signals humans itself. Add `--strict` (malformed manifest lines become fatal) for the rarest and most dangerous failure — a corrupted *manifest* — because without it a mangled line is skipped with a warning while the rest still verify.

### Where SHA-512 shows up outside this binary

- **`/etc/shadow` `$6$`** — SHA-512-crypt: thousands of salted iterations via `crypt(3)`, deliberately slow. Not `sha512sum`; never compare the two.
- **`/var/lib/dpkg/info/*.md5sums`** uses MD5, but several distro signing pipelines and ISO manifests publish SHA-512 alongside SHA-256.
- **`--tag` output** reads `SHA512 (file) = digest`, parseable by family `-c`.

## Options That Matter

| Option | Effect |
|---|---|
| `-b`, `--binary` | `*` binary-mode separator on output lines |
| `-t`, `--text` | Space text-mode separator (the default on GNU) |
| `--tag` | Emit BSD-style `SHA512 (file) = digest` lines |
| `-c`, `--check` | Verify a digest manifest instead of hashing |
| `--quiet` | During check, suppress `OK` lines; failures still print |
| `--status` | During check, print nothing; exit code only |
| `--strict` | Malformed manifest lines are fatal (nonzero exit) |
| `-w`, `--warn` | Warn (not fail) on malformed manifest lines |
| `--ignore-missing` | Skip manifest entries whose files are absent |
| `-z`, `--zero` | NUL-terminate records; pairs with `find -print0`/`xargs -0` |

Semantics identical across the family — per-flag walkthroughs in [`md5sum`](./md5sum.md).

## Usage Patterns

```bash
# Baseline a VM image directory before nightly tamper checks
sha512sum /var/lib/libvirt/images/*.qcow2 > images.sha512
```

```bash
# Verify on restore — the whole point of the baseline
sha512sum -c --quiet images.sha512
```

```bash
# Tree-wide manifest, sorted and NUL-safe, relative paths for portability
cd /data && find . -type f -print0 | sort -z | xargs -0 sha512sum > MANIFEST.sha512
```

```bash
# Speed test your fleet before standardizing on an algorithm
time sha256sum 10G.img; time sha512sum 10G.img
```

```bash
# Exact-string hashing without the newline echo adds
printf '%s' "$secret" | sha512sum | cut -d' ' -f1
```

```bash
# ...and the trap: same content, different digest, because of the newline
echo "$secret" | sha512sum
```

```bash
# Bulk deduplication of large media files by content
sha512sum *.mkv | sort | awk 'seen[$1]++ {print "dup:", $2}'
```

```bash
# Verify only what survived a partial restore
sha512sum -c --ignore-missing MANIFEST.sha512
```

```bash
# Cron-friendly gate: silent, exit-code driven, stderr logged
sha512sum -c --status MANIFEST.sha512 2>>/var/log/integrity.log || page_oncall
```

```bash
# --tag round trip: the BSD grammar verifies through -c like any other
sha512sum --tag vm.qcow2 > vm.tag && sha512sum -c vm.tag
```

```bash
# What changed in /etc since the baseline? re-hash and diff the manifests
sha512sum $(find /etc -type f | sort) > /tmp/etc-now.sha512
diff /tmp/etc-baseline.sha512 /tmp/etc-now.sha512
```

```bash
# Many-core tree inventories: parallelize across files, then restore order
find . -type f -print0 | xargs -0 -P "$(nproc)" -n 32 sha512sum | LC_ALL=C sort -k2 > MANIFEST.sha512
```

```bash
# Verify on a second host: ship the manifest, not the trust
scp -q MANIFEST.sha512 backup:/tmp/ && ssh backup 'sha512sum -c /tmp/MANIFEST.sha512 --quiet'
```

## Nuances and Gotchas

- **`sha512sum` ≠ SHA-512-crypt (`$6$`).** The former is a plain file digest; the latter is a salted, iterated password KDF in `/etc/shadow`. Confusing them in an answer signals textbook-only knowledge; the crypt form's iterations exist precisely to defeat the GPU attacks a bare digest invites.
- **The speed ranking is hardware-conditional.** Software-only 64-bit: SHA-512 usually wins. SHA-NI present: SHA-256 usually wins, sometimes by 2-3x. 32-bit platforms: SHA-512 pays a penalty emulating 64-bit ops. Benchmark, don't recite.
- **Digest width is operational, not just cosmetic.** 128 hex characters overflow fixed-column scripts, `awk '{print $1}'` still works but `cut -c1-64`-style parsing does not, and some ticket systems mangle long lines. Generate with the default format and parse on the separator, never on column positions.
- **Family manifest quirks apply.** Relative-path resolution from the working directory, `\`-escaped filenames, CRLF transfer corruption, `--strict` granularity — all documented in [`md5sum`](./md5sum.md).
- **busybox supports the core only.** `-c` and `-b` exist; `--tag`, `--status`, `--strict`, `--ignore-missing` do not. Keep embedded scripts to the core flags.
- **`$6$` is itself becoming history.** Recent Debian releases default to yescrypt (`$y$` prefix) for new accounts, moving past SHA-512-crypt; the interview point survives unchanged — none of those shadow formats are `sha512sum` output.
- **Parallel hashing must come from the file level.** One `sha512sum` process is single-threaded; the `-P` pattern above interleaves complete lines from concurrent processes, so `LC_ALL=C sort -k2` afterwards is mandatory before diffing manifests.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Digests printed successfully, or every checked file passed |
| 1 | Any checked file `FAILED` / `FAILED open or read`, malformed manifest line under `--strict`, or open/read error while hashing |

`--status` keeps codes and drops output; `--quiet` keeps failures and drops `OK`; `-w` downgrades malformed-line complaints. Family-identical — worked combinations in [`md5sum`](./md5sum.md).

## Related Commands

- [`sha256sum`](./sha256sum.md) — the everyday workhorse and the hardware-accelerated rival.
- [`sha384sum`](./sha384sum.md) — truncated SHA-512; identical speed, protocol-sized output.
- [`md5sum`](./md5sum.md) — anchor page: shared manifest format, `-c` protocol, flag semantics.
- [`sha1sum`](./sha1sum.md) — collision-broken predecessor; context for the SHA-2 generation.
- [`b2sum`](./b2sum.md) — BLAKE2: 64-bit-internal too, tunable length, keyed mode.
- [`wc`](./wc.md) — the other byte-stream measurer; pairs in one-pass inventory pipelines.
- [`sha224sum`](./sha224sum.md) — the 32-bit-family truncated twin; same protocol, opposite word width.
- [`cksum`](./cksum.md) — multiplexed checksums (`-a sha512` reproduces this digest in recent coreutils).
- [`sum`](./sum.md) — legacy BSD/SysV checksum applets; the family's historical starting point.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: Why can SHA-512 be faster than SHA-256 even though it computes more output?

Because the work is per 1024-bit block over 64-bit words: a 64-bit CPU executes the same instructions but moves twice the bits per word operation, and a given file needs half as many block iterations. Output width is a serialization detail, not compute. The exception is hardware: SHA-NI accelerates SHA-256 only, flipping the ranking on modern fleets — so the real answer is "software vs accelerated workloads differ; measure".

### Q: Explain the difference between `sha512sum /etc/shadow`-style digests and the `$6$` entries in `/etc/shadow`.

`sha512sum` computes a fast, unsalted digest over exact bytes — ideal for integrity, terrible for passwords because identical passwords hash identically and GPUs compute it at billions per second. `$6$` is SHA-512-crypt: a salted, thousands-of-iterations KDF built *on* SHA-512, deliberately slow and unique per user. Same primitive, opposite design goals; an interviewer uses this to separate "knows the names" from "knows the constructions".

### Q: You must hash 50 TB nightly and verify. Which SHA-2 tool do you pick, and what else dominates the decision?

Benchmark SHA-256 vs SHA-512 on the actual storage first: if reads run at 500 MB/s, the CPU is idle either way and the choice is moot; on fast NVMe with SHA-NI, SHA-256 wins; on NVMe without SHA-NI, SHA-512 usually wins. Then the real constraints: manifest portability (relative paths, sorted, NUL-safe generation), `--quiet`/`--status` for reporting, and whether verification can run incrementally (`--ignore-missing`, per-directory manifests) instead of one monolithic re-scan.

### Q: What breaks if a script parses checksum lines with `cut -c1-64`?

It assumes SHA-256 width. Family manifests carry 32 (MD5), 40 (SHA-1), 56, 64, 96 or 128 hex characters — column-based parsing fails everywhere except its home tool. Parse on the separator instead: the digest is the first whitespace-run-delimited field (`awk '{print $1}'`), the filename is everything after the two-character mode marker. The escape-marker `\` prefix for exotic filenames is the further reason column math and manifests don't mix.

### Q: Why do the coreutils checksum tools share one binary interface — and what does that buy you operationally?

Coreutils deliberately cloned md5sum's grammar across the family: same line format, same `-c` protocol, same flags and exit codes. The payoff: one wrapper script parameterized by tool name verifies any manifest; one mental model spans algorithm migrations; and failure modes learned once (missing files, malformed lines, `--status` semantics) transfer everywhere. It also makes algorithm upgrades mechanical — swap the binary name, re-hash, keep the harness.

### Q: Why 1024-bit blocks for SHA-512 rather than SHA-256's 512 — what does the wider block actually buy?

Throughput per compression call: block size is the amount of message consumed per chain step, so a 1024-bit block halves the number of sequential compression invocations for the same file — the critical path gets shorter, not just the work spread wider. With 64-bit words, each of those steps also moves twice the payload per instruction. The costs are memory (eight 64-bit registers, an 80-entry expanded schedule of 64-bit words) and poor efficiency on 32-bit or constrained hardware, which is exactly why NIST kept both families in FIPS 180: SHA-256 for embedded breadth, SHA-512 for 64-bit servers.

### Q: A vendor quotes 2.5 GB/s SHA-512 and 1.8 GB/s SHA-256 for an appliance. What do you ask before believing the ranking?

Whether the SHA-256 figure used SHA-NI — if the appliance has the extensions and still loses to software SHA-512, the implementation is suspect, because SHA-NI SHA-256 should lead on any mid-2010s-or-newer x86 core. Whether both numbers come from the same binary and I/O path (`openssl speed` and coreutils measure differently, and disk can bottleneck before either algorithm does). And which CPU generation your own fleet runs versus the vendor's test bed. The honest procedure is one command on one representative machine: `time sha512sum 10G.img; time sha256sum 10G.img` over the real bytes.

### Q: Where does SHA-512/256 fit — why truncate SHA-512 to 256 bits instead of using SHA-256?

Purely as an engine swap: SHA-512/256 runs the 1024-bit, 64-bit-word machinery, so on 64-bit CPUs without SHA-NI it typically outruns SHA-256 while producing the same 256-bit output, and its computed IV makes it a domain-separated function rather than a prefix of SHA-512's stream. FIPS 180-4 defines it for environments that want exactly that trade. Coreutils ships no dedicated binary, so it comes from `openssl dgst` or a library — one more reason the shell conversation stays anchored on plain `sha512sum`.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sha512sum.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
