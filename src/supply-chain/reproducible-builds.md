# Reproducible and Hermetic Builds

Two builds of the same source, run on two different machines, should produce
the same bytes. Most builds do not. This page covers the discipline that
closes that gap: what breaks determinism, how the ecosystem standardized
around `SOURCE_DATE_EPOCH`, what Debian learned from rebuilding its archive,
why hermeticity beats determinism as a goal, and how independent rebuilders
turn "the vendor says so" into a checkable claim. For a survey of build
systems and caching, see [Build Systems](./build-systems.md); for the
pipeline-security framing, see
[Supply Chain Security, Advanced](../security/advanced/supply-chain-advanced.md).

## The Definition, Precisely

The [reproducible-builds.org definition](https://reproducible-builds.org/docs/definition/)
is worth quoting nearly in full:

> A build is reproducible if given the same source code, build environment and
> build instructions, any party can recreate bit-by-bit identical copies of
> all specified artifacts.

Three subtleties hide in that sentence. Verification is **bit-by-bit
comparison**, conventionally by cryptographic hash. The *relevant attributes*
of environment, instructions, and source are **defined by the authors or
distributors** -- a distributor may declare CPU microarchitecture part of the
identity, or irrelevant. *Artifacts* means primary outputs, not build logs.

As an identity statement, a build is a function evaluated twice:

```text
      build instructions + toolchain
                   |
  sources ------->|                +--> artifact A  --+
                   |   environment  |                  |-- equal?
  sources ------->|                +--> artifact B  --+
  H(sources, env, instructions) fully determines output bytes
```

If a build *reads* an environment attribute that no one declared as part of
the identity, the equation silently breaks.

## A Taxonomy of Nondeterminism

The reproducible-builds.org docs organize the leaks into a
[Managing variance](https://reproducible-builds.org/docs/) taxonomy --
timestamps, timezones, locales, archive metadata, output ordering, randomness,
build path. The common pattern: the toolchain reads something that is not a
declared input and writes it into the output bytes.

| Leak class | Mechanism | Where the bytes change | Standard fix |
|---|---|---|---|
| Wall-clock time | `__DATE__`, `__TIME__`, build stamping | Header blocks, PE/ELF notes | `SOURCE_DATE_EPOCH` |
| Timezone/locale | Localized date formatting, sort order | Docs, generated string tables | `TZ=UTC`, `LC_ALL=C` |
| File ordering | Filesystem enumeration order | Archive member order, symbol tables | Sort inputs canonically |
| Archive metadata | mtime/uid/gid fields in tar, zip, gzip | Whole-container/image hashes | Normalize headers, `gzip -n` |
| Build path | Compiler embeds `__FILE__`, DWARF `DW_AT_comp_dir` | Debug info, panic messages | Prefix map (`-ffile-prefix-map`) |
| Randomness | Hash-seed ordering, generated UUIDs | Iteration order in output | Seed deterministically |
| Toolchain drift | Different compiler versions/flags in path | Everything | Pin toolchain by hash |

The toolchain cases deserve a closer look because they are the least obvious:

- **Path embedding.** A file compiled as `/home/alice/build/src/util.c` bakes
  that string into DWARF debug info; Bob's machine compiles it from
  `/home/bob/ci/src/util.c`. Same program, different bytes. The proposed
  `BUILD_PATH_PREFIX_MAP` spec (still work-in-progress) targets this;
  meanwhile compilers grew `-ffile-prefix-map`.
- **Archive ordering.** `ar` and `tar` historically wrote members in
  filesystem order, so hash-ordered ext4 and insertion-ordered tmpfs produce
  archives with identical members but different byte layout -- and hashes.
- **Trailing metadata.** `gzip` records filename and mtime; `zip` records
  per-member timestamps; Python bytecode caches embed source mtime and size.
  One changed byte changes the artifact hash, and every image digest above it.

## SOURCE_DATE_EPOCH

The ecosystem's one big standardization win is
[`SOURCE_DATE_EPOCH`](https://reproducible-builds.org/docs/source-date-epoch/):
a Unix timestamp in seconds, interpreted as UTC, that timestamp-aware tools
treat as "now". Distributions typically set it to the latest source
modification time (the commit date is popular). Tools that honor it -- GNU
`tar`, `gzip`, compilers' `__DATE__`, doc generators -- then produce
timestamp fields that are a function of the source tree, not of the machine.

Two properties make the convention work. It is **opt-in per tool** -- a tool
that ignores it keeps leaking wall-clock time, which is how you hunt
remaining offenders: rebuild twice, diff, find the differing bytes. And it
is **part of the declared identity**: the distributor picks the epoch.

## Debian: the Rebuild-Everything Programme

The modern reproducibility push is largely a Debian story: beginning in 2013,
contributors rebuilt the archive and filed bugs for every package whose two
builds differed. That grew into continuous infrastructure that rebuilds
packages across architectures and toolchain perturbations and publishes
per-package status (see the
[Debian ReproducibleBuilds wiki](https://wiki.debian.org/ReproducibleBuilds));
the binary-diffing tool `diffoscope` ([diffoscope.org](https://diffoscope.org/))
came out of that effort.

The headline result, from the project's
[success stories page](https://reproducible-builds.org/success-stories/):
the essential and required package sets became 100% reproducible in the
Debian bookworm release on amd64 and arm64. The wider archive sits below
that, and the live numbers move with every toolchain change -- precisely why
this is continuous rebuilding rather than a one-off audit. Arch Linux runs a
similar [public rebuilder](https://reproducible.archlinux.org/).

## Hermeticity: Stronger than Determinism

Determinism says: *given an environment, the output is a function of it.*
Hermeticity says: *the environment contains nothing you did not declare.*
A deterministic build on a polluted host is still polluted -- reproducibly.

- A **deterministic, non-hermetic** build: the same laptop always produces
  the same binary, but the binary embeds whatever happens to be in
  `/usr/include` and `$HOME` that day. Rebuild elsewhere and it diverges.
- A **hermetic** build: toolchain and inputs are materialized by hash into an
  isolated workspace; the host's `/usr` is simply not visible. Nix and Guix
  are the canonical implementations -- builds run against a content-addressed
  store ([how Nix works](https://nixos.org/guides/how-nix-works.html)) with no
  implicit host access -- and Bazel applies the same idea per action
  ([Bazel and the Build Graph](./bazel-build-graphs.md)).

Hermeticity gives determinism *by construction* when the pinned toolchain is
itself deterministic, plus two things determinism cannot: **portability** and
**correct caching** -- a cache key computed from declared inputs is only
complete if no undeclared inputs exist. The cost is discipline: every input
must be declared.

## Verification: Rebuilders and Assurance Builds

Reproducibility pays off when a *third party* rebuilds and compares:
publish (source, environment description, instructions), let anyone
re-execute, compare hashes.

- **Distributions.** Debian's and Arch's continuous rebuilders are permanent
  audits of the archive rather than release gates; NixOS reported an
  independent, bit-for-bit identical rebuild of its minimal installation
  image -- a large, multi-toolchain dependency chain.
- **Bitcoin Core.** The release process, documented in
  [`doc/guix.md`](https://github.com/bitcoin/bitcoin/blob/master/doc/guix.md),
  builds release binaries inside GNU Guix, which pins the toolchain, so
  anyone can re-execute the build and compare bytes with the published ones.
  Attestations accumulate in a signatures repository
  ([bitcoin-core/guix.sigs](https://github.com/bitcoin-core/guix.sigs)) -- a
  crowd-sourced, continuously-run rebuilder for a binary strangers are
  expected to execute. Tor Browser and Tails (whose 3.3 ISO was among the
  first reproducible distro images) sit on the same success-stories page.

The security logic is the point. Signing proves "these bytes came from the
key holder" -- not that they correspond to the source. The SolarWinds
compromise (2020) exploited exactly that gap: a validly signed, officially
delivered update whose build pipeline had been tampered with. Reproducible
builds with independent rebuilders attack that step: tampering changes the
output bytes, and anyone can detect the mismatch. (It does not address
Thompson's deeper "trusting trust" compiler attack; that needs bootstrappable
builds -- see [Software Supply Chain Security](./software-supply-chain.md).)

## Demonstration: Watching Nondeterminism Leak, then Disappear

The script builds the same three-file "project" two ways. The naive build
stamps wall-clock time into the artifact and walks the input tree in
enumeration order (simulating two machines whose filesystems list files
differently); the reproducible build pins `SOURCE_DATE_EPOCH` and sorts
inputs canonically.

```python
import hashlib
import time

SOURCES_A = {"app.c":  b"int main(void) { return helper(); }",
             "util.c": b"int helper(void) { return 42; }",
             "lib.h":  b"int helper(void);"}
# machine B lists the same directory in a different order (fs-dependent)
SOURCES_B = {"lib.h":  b"int helper(void);",
             "app.c":  b"int main(void) { return helper(); }",
             "util.c": b"int helper(void) { return 42; }"}

def naive_build(tree):
    """Legacy toolchain: wall-clock stamp + directory enumeration order."""
    out = bytearray()
    out += b"built-at=" + str(time.time_ns()).encode() + b"\n"
    for name in tree:                      # enumeration order, not sorted
        out += ("obj " + name + "\n").encode() + tree[name] + b"\n"
    return bytes(out)

def reproducible_build(tree, source_date_epoch):
    """Pinned epoch + canonical input order => environment cancels out."""
    out = bytearray()
    for name in sorted(tree):              # canonical order
        out += ("obj " + name + "\n").encode() + tree[name] + b"\n"
    out += b"source-date-epoch=" + str(source_date_epoch).encode() + b"\n"
    return bytes(out)

def sha(b):
    return hashlib.sha256(b).hexdigest()

a1 = naive_build(SOURCES_A)
time.sleep(0.003)                          # 3 ms of real time passes
a2 = naive_build(SOURCES_B)                # same sources, other fs order
b1 = reproducible_build(SOURCES_A, 946684800)   # 2000-01-01T00:00:00Z
b2 = reproducible_build(SOURCES_B, 946684800)
b3 = reproducible_build(SOURCES_A, 946684801)   # 1 s later

print("NAIVE toolchain (build time + fs order leak into bytes)")
print("  builder A digest:", sha(a1)[:32])
print("  builder B digest:", sha(a2)[:32])
print("  bit-identical?  ", a1 == a2)
print()
print("REPRODUCIBLE build (SOURCE_DATE_EPOCH + sorted inputs)")
print("  builder X digest:", sha(b1)[:32])
print("  builder Y digest:", sha(b2)[:32])
print("  bit-identical?  ", b1 == b2)
print()
print("the epoch is part of the declared identity:")
print("  shift epoch by 1 s -> bytes change:", b1 != b3)
```

Output from one run (Python 3.12). The two naive digests differ -- with
*different values* on every invocation -- while the reproducible digest
`1197c1b391cbfde48511780bf18baa6d` never moves:

```text
NAIVE toolchain (build time + fs order leak into bytes)
  builder A digest: e6830a3c5db74bb10ea8265bd9035e57
  builder B digest: 0a970b40cdfec47ce2d51adb50a99947
  bit-identical?   False

REPRODUCIBLE build (SOURCE_DATE_EPOCH + sorted inputs)
  builder X digest: 1197c1b391cbfde48511780bf18baa6d
  builder Y digest: 1197c1b391cbfde48511780bf18baa6d
  bit-identical?   True

the epoch is part of the declared identity:
  shift epoch by 1 s -> bytes change: True
```

Reproducibility does not mean "the bytes never change" -- the bytes are a
function of *declared* inputs, and changing the declared epoch is a source
change: no implicit inputs, ever.

## Failure Modes in Practice

Teams adopting reproducible builds reliably hit the same walls:

- **Partial coverage.** "Ninety-five percent reproducible" is misleading: the
  differing 5% are exactly the packages worth auditing, so keep status visible
  (Debian's tracker exists for this reason).
- **Declared-but-impure inputs.** Pinning "the Docker image tagged latest" is
  not pinning; environment identities must be content-addressed (image
  digests, store paths, lockfile hashes), not named.
- **The network as input.** A build that fetches anything at build time has
  an undeclared input unless the fetch is hash-verified (Nix fixed-output
  derivations, vendored checksums); generators are toolchains too, so an
  untracked protoc leaks into artifacts like an untracked gcc.
- **No independent verifier.** If CI is the only place binaries are built,
  nobody ever checks them; rebuilding must be documented and exercised
  (Bitcoin Core's signature repos are the health check), or the property rots.

## References

1. [reproducible-builds.org -- Definitions](https://reproducible-builds.org/docs/definition/) -- the normative definition quoted above.
2. [reproducible-builds.org -- Documentation index](https://reproducible-builds.org/docs/) -- the variance taxonomy (timestamps, locales, build path, archive metadata, randomness) and `BUILD_PATH_PREFIX_MAP` status.
3. [reproducible-builds.org -- SOURCE_DATE_EPOCH](https://reproducible-builds.org/docs/source-date-epoch/) -- the epoch convention spec.
4. [reproducible-builds.org -- Success stories](https://reproducible-builds.org/success-stories/) -- Debian bookworm essential+required at 100%, NixOS image rebuild, Tor, Tails, coreboot.
5. [Bitcoin Core -- `doc/guix.md`](https://github.com/bitcoin/bitcoin/blob/master/doc/guix.md) -- Guix-pinned assurance builds; attestations in [bitcoin-core/guix.sigs](https://github.com/bitcoin-core/guix.sigs).
