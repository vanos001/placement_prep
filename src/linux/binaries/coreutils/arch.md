# arch — print machine hardware architecture

## Overview

`arch` prints a single token naming the machine hardware architecture — on this
class of machine, `x86_64`. It takes no options other than `--help` and
`--version`, reads nothing from its environment, and produces exactly one line
of output. Functionally it is a strict alias for `uname -m`: both call the
`uname(2)` system call and print the `machine` field.

The binary ships in the Debian `coreutils` package alongside `uname` itself —
in fact both are built from the same source file (`uname.c` in the coreutils
tree), which is why their output can never drift apart. On modern Debian and
Ubuntu systems with merged `/usr` it lives at `/usr/bin/arch`.

You reach for `arch` in shell scripts that need to pick architecture-specific
artifacts: which tarball to download, which plugin directory to use, which
libexec path to compile against. Its value over `uname -m` is purely
ergonomic — a shorter command with a more specific name — and reviewers of
portable scripts often prefer `uname -m` precisely because `arch` does not
exist everywhere (macOS and the BSDs historically ship it, but some minimal
containers and busybox-only systems do not).

Do not confuse `arch` with `dpkg --print-architecture`: the former prints the
kernel's hardware name (`x86_64`), the latter Debian's package-architecture
name (`amd64`). The two vocabularies overlap but are not interchangeable.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/arch` on modern Debian/Ubuntu |
| First appeared / lineage | BSD lineage (4.3BSD-era alias for `uname -m`); folded into GNU coreutils in the 5.x/6.x era |
| Standards | Not POSIX-standardized; GNU coreutils and BSDs only |

## Synopsis

```
arch [OPTION]...
```

There is exactly one form. The command accepts no operands at all:

```bash
arch                    # print e.g. x86_64
arch --help             # usage text
arch --version          # coreutils version banner
arch x86_64             # error: extra operand 'x86_64'
```

## How It Works

`arch` performs a single `uname(2)` syscall and prints the `machine` member of
the returned `utsname` struct, followed by a newline. Nothing else influences
the output: no environment variable, no configuration file, no argument.

```bash
$ arch
x86_64
$ uname -m
x86_64
$ arch | cmp - <(uname -m) && echo identical
identical
```

### What the output actually reports

The `machine` field describes **the running kernel**, not the userland and
not the CPU silicon. This distinction produces the classic surprises:

| Situation | `arch` output | Why |
| --- | --- | --- |
| 64-bit kernel, 64-bit userland (typical) | `x86_64` | straightforward |
| 64-bit kernel running a 32-bit i386 chroot/container | `x86_64` | kernel is still 64-bit |
| 64-bit ARM CPU (Cortex-A76 etc.) with 32-bit kernel | `armv7l` | kernel reports 32-bit ARM |
| 64-bit ARM kernel running 32-bit armhf userland | `aarch64` | kernel is 64-bit |
| 32-bit i686 kernel on a modern x86_64 CPU | `i686` | kernel chose 32-bit mode |

So `arch` answers "what kind of kernel is running", which is usually the right
question when the script is about to *execute* something (you need binaries
that match the kernel ABI), but the wrong question when the script is about to
*link* something (that depends on the compiler target).

### Common values

| `arch` output | Where you see it | Debian pkg-arch |
| --- | --- | --- |
| `x86_64` | Intel/AMD 64-bit | `amd64` |
| `i686` | legacy 32-bit x86 | `i386` |
| `aarch64` | 64-bit ARM (AWS Graviton, Raspberry Pi 4/5 w/ 64-bit OS, Apple Silicon VMs) | `arm64` |
| `armv7l` | 32-bit ARM hard-float (older Pi, many SBCs) | `armhf` |
| `ppc64le` | POWER little-endian | `ppc64el` |
| `s390x` | IBM Z mainframes | `s390x` |
| `riscv64` | RISC-V 64-bit | `riscv64` |

Note the two vocabularies: `arch`/`uname -m` use the kernel naming, Debian
packaging uses its own set. `x86_64` vs `amd64` is the most frequent mismatch
in hand-written install scripts.

### Why packaging scripts use it

Download-based installers (node, go, rust toolchains, container images)
branch on architecture to pick the artifact name:

```bash
case "$(arch)" in
  x86_64)  TARBALL_ARCH="x64"   ;;
  aarch64) TARBALL_ARCH="arm64" ;;
  armv7l)  TARBALL_ARCH="armv7" ;;
  *) echo "unsupported architecture: $(arch)" >&2; exit 1 ;;
esac
```

Vendors name their artifacts differently (`x64`, `amd64`, `x86_64`, `x86-64`
are all in circulation), so the mapping table inside the `case` is
unavoidable. `arch` merely supplies the kernel-side token that starts the
mapping.

## Options That Matter

`arch` has no functional options — a deliberate property worth stating in an
interview when asked to compare it with `uname`.

| Option | Effect |
| --- | --- |
| `--help` | Print usage and exit 0 |
| `--version` | Print coreutils version and exit 0 |

Any other argument is rejected with `arch: extra operand` and exit status 1.

## Usage Patterns

```bash
# Simple gate: refuse to install on non-64-bit
[ "$(arch)" = "x86_64" ] || { echo "need x86_64"; exit 1; }
```

```bash
# Pick the right Go toolchain tarball
curl -LO "https://go.dev/dl/go1.22.linux-$(arch).tar.gz"
```

```bash
# Normalize kernel arch to Debian package arch
case $(arch) in
  x86_64)  deb=amd64  ;; aarch64) deb=arm64 ;;
  armv7l)  deb=armhf  ;; i686)    deb=i386  ;;
esac
```

```bash
# Log the architecture in a CI runner banner
echo "runner: $(hostname) arch=$(arch) kernel=$(uname -r)"
```

```bash
# Verify a downloaded binary matches the host before executing it
file ./tool | grep -q "$(arch)" || echo "binary may not run here"
```

```bash
# Compare host arch to the container arch you are about to emulate
[ "$(arch)" = "$(docker exec myctr arch)" ] && echo "native" || echo "emulated"
```

```bash
# Choose a compiler -march flag in a build script
case $(arch) in x86_64) CFLAGS="-march=x86-64-v2";; aarch64) CFLAGS="-march=armv8-a";; esac
```

```bash
# Assert the whole fleet is homogeneous before a rolling deploy
for h in $(cat hosts.txt); do printf '%s %s\n' "$h" "$(ssh "$h" arch)"; done | sort -k2 -u
```

## Nuances and Gotchas

- **Not POSIX.** `arch` is a GNU/BSD convenience. POSIX-standardized scripts
  use `uname -m`. BusyBox builds may omit `arch` entirely, so alpine-based
  containers can fail with "arch: not found" while `uname -m` works.
- **It reports the kernel, not the userland.** A 32-bit container on an
  x86_64 host still prints `x86_64`. Scripts that use `arch` to pick *library*
  paths inside a multiarch chroot will pick the wrong one; inspect the
  compiler or `file` the binary instead.
- **`armv7l` vs `aarch64` is a kernel decision.** The same 64-bit-capable
  board can report either depending on which kernel image was booted. Any
  script that treats `armv7l` as "CPU is 32-bit" is wrong.
- **Debian names differ.** `x86_64` → package arch `amd64`, `aarch64` →
  `arm64`, `armv7l` → `armhf`, `ppc64le` → `ppc64el`. Inside Debian packaging
  use `dpkg --print-architecture`, not `arch`.
- **`i686` vs `i386` vs `i486`.** Older kernels report various iX86 values;
  never string-match a single one — glob `i?86` if you must match 32-bit x86.
- **Output is one line with trailing newline.** Piping into tools that expect
  no newline (rare) needs `tr -d '\n'`; command substitution strips it
  naturally.
- **No options means no future flags to learn** — but also no way to ask for
  e.g. the Debian name or CPU endianness; that is `uname`'s job (`-p`, `-i`).

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Machine name written successfully |
| nonzero | Write failed (e.g. broken pipe with `pipefail`) or bad option/operand given |

`arch | head -c 0` under `set -o pipefail` can surface the write error — the
same behavior as `true`-style coreutils writers.

## Related Commands

- [`overview`](./overview.md) — collection hub: index of all userland binary pages
- `uname -m` — the POSIX-spelled twin of `arch`; same output, no coreutils page in this collection
- `dpkg --print-architecture` — Debian package-architecture name (not part of coreutils; no page here)

The coreutils siblings below share the "report a fact about the running
system" theme:

- [`false`](./false.md) — the degenerate "report a fact" command: exits 1, always
- [`hostid`](./hostid.md) — another dormant system-identity reporting command
- [`id`](./id.md) — reports identity of a user rather than of the machine

## Interview Questions

### Q: What does `arch` print on an Apple M1 laptop running a Docker Linux aarch64 container?

`aarch64`. Inside the Linux container the kernel is a 64-bit ARM kernel, so
the `machine` field of `uname(2)` is `aarch64`. On macOS itself the command
would not be GNU `arch`; the container boundary is what makes the question
well-defined. If the image were an emulated amd64 image (qemu), the *emulated*
kernel would report `x86_64`, which is why `arch` inside a container answers
"what will run here", not "what hardware is this".

### Q: A script does `[ "$(arch)" = "x86_64" ]` and fails inside a 32-bit i386 Debian chroot on an otherwise 64-bit host. Why, and what is the fix?

Because `arch` consults the kernel, and the kernel is still 64-bit — the
chroot changes the root filesystem and the ABI of new processes, not the
`utsname` struct. There is no fix via `arch`; the script must test what it
actually cares about, e.g. the linker flavor (`file /bin/ls`) or the
`DEB_HOST_ARCH` dpkg variable, since the chroot's *userland* is i386 even
though the kernel is not.

### Q: Why do many maintainers reject `arch` in favor of `uname -m` in portable scripts?

`uname -m` is defined by POSIX and exists on every Unix-like system including
busybox-only environments, while `arch` is absent from some of those (and on
macOS it had different historical behavior before returning to `uname -m`
semantics). Since the outputs are provably identical wherever both exist,
using the more portable spelling costs nothing and removes a dependency.

### Q: What is the relationship between the source files of `arch` and `uname` in the GNU coreutils tree?

They are one program: `uname.c` builds both binaries, and the code path for
`arch` is the `uname -m` code path. This is a deliberate design so the two can
never disagree, similar to how several coreutils tools are built from shared
sources. An interviewer is probing whether you know `arch` is a thin alias,
not an independent implementation.

### Q: Name two architectures where the kernel token and the Debian package architecture have non-obvious names.

`x86_64` maps to Debian `amd64` (a historical choice from when AMD defined the
64-bit extension), and `ppc64le` maps to `ppc64el` (Debian abbreviates the
"little endian" suffix). Also `armv7l` → `armhf` is non-obvious since the
package name encodes the hard-float ABI rather than the machine token.
Scripts that translate naively break on exactly these.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/arch.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
