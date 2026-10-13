# uutils — GNU userland, rewritten in Rust (collection hub)

## Overview

uutils is an umbrella project re-implementing the classic Unix/GNU userland in
Rust — MIT-licensed, cross-platform, and organized into one sub-project per
upstream collection: `coreutils`, `findutils`, `diffutils`, `grep`, `sed`,
`awk`, `tar`, `acl`, `hostname`, `login`, `shadow`, `bsdutils`, `procps`,
`util-linux`. The scale is real: the coreutils sub-project alone mirrors the
~100-binary GNU package this book covers one page at a time. This book part
uses those same collection names, deliberately: what you learn per-binary
here maps onto both the GNU originals that ship today and the Rust
implementations taking over incrementally. The hub page carries what the
collections share — maturity status, compatibility strategy, how to try the
tools — while behavior itself lives on the per-binary pages, starting with
[GNU Coreutils](../coreutils/overview.md).

Two framing facts prevent most misunderstandings. First, uutils' goal is
*compatibility*, not reinvention: the GNU coreutils test suite is the
explicit target, GNU quirks included. Second, adoption is per-collection and
per-tool, not a flag day: your box can be running uutils `ls` while
everything else is still GNU, and most scripts would never notice — the
differences live in the long tail this book documents per flag.

The part overview is at [Linux Userland Binaries](../overview.md); this page
is the family map for where the Rust rewrites stand.

Positioning helps too: uutils is not an embedded minimal userland — that
niche belongs to BusyBox, with its size-first CONFIG_ trimming — and it is
not a POSIX-only portability layer either. It is a full-featured, Rust-native
replacement aiming at *the exact behavior* of the GNU tools most of the
industry already runs, which is why compatibility evidence matters more here
than feature lists.

## Why a Rewrite Matters

The uutils.org pitch rests on three legs, all verifiable rather than
aspirational:

- **Memory safety.** These tools run as root, parse hostile filenames, and
  process untrusted input; the C implementations behind GNU userland carry a
  long history of CVEs in exactly the bug class (buffer overflows,
  use-after-free) that Rust's ownership model removes by construction.
  Rewriting in Rust does not make the tools correct, but it removes an entire
  category of security incidents from consideration.
- **Cross-platform.** One codebase builds on Linux, macOS, Windows, and the
  BSDs, so the same `ls -l` means the same thing in CI on all of them. That
  is a real operational difference from GNU coreutils, whose behavior you
  otherwise triangulate against BSD userland drift — the same flag-drift
  problem this book documents for BusyBox, but on macOS and Windows.
- **Licensing.** GNU coreutils is GPL-3.0-or-later; uutils coreutils is MIT.
  Stated neutrally: the GPL requires source disclosure and license
  preservation when you distribute modified binaries, while MIT permits
  integration into proprietary products with attribution. Nothing about
  either license changes how the tools behave day to day; the choice matters
  to vendors embedding a userland in products with different obligations, and
  to distributions weighing ecosystem effects of the switch. The uutils
  project treats the license as an enabler of adoption, not as an argument
  against GNU's — both continue to exist and interoperate.

On adoption, uutils.org reports that Ubuntu 25.10 ships uutils coreutils as
the default coreutils implementation — the first major distribution to make
that default, per uutils.org at time of writing. Whatever one predicts about
the trajectory, the compatibility-first strategy is what made a mainstream
default plausible: a distro can switch because the tools promise GNU
behavior, quirks included.

What the Ubuntu default does **not** mean: it is not a signal that every
collection is ready to swap — the family table shows sed and util-linux far
earlier on the curve — and it is not a removal of the GNU userland. Both
stacks coexist on one image without conflict, and minimal images frequently
keep GNU exactly because the long tail is documented, battle-tested
behavior.

## The Project Family

uutils is not one project but a family, and maturity varies wildly across it —
which is why per-collection status is the unit of analysis, not "uutils" as a
blob. The table below maps the collections covered by this book part to their
uutils counterparts, with the maturity labels as shown on uutils.org at time
of writing:

| Collection in this part | uutils project | Status on uutils.org |
|---|---|---|
| GNU Coreutils | `coreutils` | ready |
| findutils | `findutils` | beta |
| diffutils | `diffutils` | beta |
| grep | `grep` | beta |
| shadow (account tools) | `shadow` | beta |
| GNU sed | `sed` | alpha |
| Gawk | `awk` | in progress |
| GNU tar | `tar` | in progress |
| ACL tools | `acl` | in progress |
| hostname | `hostname` | in progress |
| login (session tools) | `login` | in progress |
| bsdutils | `bsdutils` | in progress |
| procps | `procps` | in progress |
| util-linux | `util-linux` | in progress |

Read the labels as uutils.org's own self-assessment, captured at time of
writing — they move release to release, and the live per-utility status pages
on uutils.org are the citable source, not this table. The safe interview
position: "coreutils is the mature one; everything around it is earlier on
the curve, with sed the earliest." Note also what the labels do *not* say:
they describe implementation and compatibility progress, not a promise that
any distro ships a given collection.

Two naming notes prevent confusion. The uutils project names in the middle
column are upstream project names, which line up with this book's collection
names but only loosely with Debian binary packages: uutils `shadow` targets
the upstream shadow suite, whose account tools Debian splits into its
`passwd` and `login` packages. And the statuses are per *collection*, not
per binary — a collection can be beta overall while specific utilities in it
are effectively complete.

The ordering itself is informative. coreutils reached ready first because it
is the largest, most-exercised surface — more users, more bug reports, and
the GNU test suite to lean on. The text-heavy oddballs lag for structural
reasons: sed and awk are state machines with locale-sensitive parsing where
the spec's edge cases are the product, and util-linux/procps wrap kernel
interfaces with distro-specific quirks. When an interviewer asks "how far
along is the rewrite?", answering per collection with a reason is what
separates a real answer from a headline.

## Compatibility Strategy

The strategy is unusually disciplined for a rewrite, and it is worth
understanding because interview questions about "rewrite risk" are really
questions about this section.

**The GNU test suite is the target.** uutils runs the upstream GNU coreutils
test suite against its implementations and tracks per-utility results. This
is the right oracle: the goal is to reproduce GNU behavior — including
decades of accumulated edge-case decisions, exit codes, and error messages —
not to design a cleaner spec. A rewrite that passed only its own tests could
drift anywhere; one judged by the GNU suite is anchored to the observable
behavior millions of scripts depend on.

**Differential fuzzing covers what the suite cannot.** Test suites encode
known edge cases; generated argument sets explore unknown ones. The project
documents differential fuzzing that runs the same command line through both
implementations and compares stdout, stderr, and exit status (and, for
file-rewriting tools, the resulting file trees). Mismatches become bug
reports or explicit compatibility decisions — the mechanism by which "rare
flag behaves differently" gets found *before* a user's cron job finds it.

The differential technique is not reserved for the project's own CI — it
scales down to a one-liner on any box with both implementations, and it is
the single most practical habit this page teaches:

```bash
# your own differential check on real invocations, no fuzzing infra needed
$ /usr/bin/ls -la --color=never /etc > /tmp/gnu.out
$ coreutils ls -la --color=never /etc > /tmp/uu.out
$ diff /tmp/gnu.out /tmp/uu.out && echo IDENTICAL
IDENTICAL
```

Mismatches on your own corpus are exactly the drift that matters to *you*;
fuzzing generalizes the search, but the corpus is what you can act on before
a cutover decision.

**Drift concentrates where testing is weakest.** The residual differences
cluster predictably: rare and combined flags (the long tail nobody exercises
daily), locale collation and character-class behavior under non-`C` locales,
and i18n/encoding edge cases. The happy path — the flags in every tutorial —
is the most-fuzzed surface and effectively indistinguishable. The practical
consequence for scripts: if you stay on the exercised core, the switch is
boring; the risk budget is spent exactly where this book's Nuances sections
point. See the per-binary pages for concrete drift classes:
[sort](../coreutils/sort.md) for locale collation, [ls](../coreutils/ls.md)
for quoting, [test](../coreutils/test.md) for exit-code semantics.

## Trying It

There is no `apt install uutils` on Debian bookworm — the archive does not
carry it — so the path is a Rust toolchain (rustup, or your distro's `rustc`
plus `cargo` is enough) and crates.io:

```bash
# install from crates.io (pulls the whole workspace)
$ cargo install coreutils

# multi-call dispatch: the applet name is the first argument
$ coreutils ls --help
$ coreutils seq 1 3
1
2
3

# where it landed, and that it does NOT shadow the system tools
$ which coreutils
~/.cargo/bin/coreutils
$ ls --version | head -1        # still GNU coreutils
ls (GNU coreutils) 9.7
```

Details worth knowing before you rely on it:

- The binary is named `coreutils` (the project's tools were historically
  invoked as `uutils`); the crate on crates.io is `coreutils`.
- Installing creates **no applet symlinks** — your `/usr/bin/ls` stays GNU
  until you deliberately build a symlink farm to the new binary. The
  multi-call dispatch itself works exactly like BusyBox's: `argv[0]` lookup
  or first-argument form. That is the safest default for a
  compatibility-sensitive tool: opt-in replacement, trivially reversible.
- A symlink farm for testing is a one-liner per applet; in CI, prefer
  invoking `coreutils <applet>` explicitly so the GNU and Rust runs are
  distinguishable in logs.
- Per-applet crates (below) can also be pulled into a Rust project directly,
  which is how the tools get embedded elsewhere.
- Building from a source checkout (`cargo build --release`) yields the same
  binary plus the ability to pin a commit — useful when you need a fix that
  has not reached crates.io yet; the workspace carries the tests, so
  `cargo test` runs the compatibility checks locally.
- In CI logs, `coreutils --version` identifies the build you are testing
  against — cheap insurance against comparing runs of different builds.

## The Crate Ecosystem

Structurally, the project is a Cargo workspace: one crate per utility
(`uu_ls`, `uu_cp`, `uu_sort`, ...), a shared `uucore` crate providing the
common scaffolding (option-parsing idioms, human-readable size formatting,
platform shims that make Windows behavior sane), and a thin top-level
`coreutils` binary that is little more than an argv[0] dispatch table over
those crates. Each `uu_*` crate is published to crates.io in its own right,
so an application can embed exactly one utility — a packaging granularity
the C original never had. The sibling collections (findutils, diffutils, the
rest of the family table) mirror this layout, which is why the maturity
table reads as one coherent project rather than fourteen unrelated ports.

## Conventions Shared Across the Family

The collections are separate projects, but they behave like one family
because they share scaffolding:

- **Dispatch** — every collection binary is multi-call: applet name as the
  first argument or `argv[0]` via a symlink farm, the same mechanism BusyBox
  uses and documents on [its page](../busybox.md).
- **Exit codes and error text** aim at the GNU originals, because scripts
  branch on both; divergence here counts as a bug in the uutils model.
- **No implicit takeover** — installing a collection never rewrites PATH;
  replacement is opt-in per symlink, reversible by deleting it.
- **Per-crate granularity** — any single utility can be embedded in a larger
  Rust program without carrying the rest of the collection.
- **Locale sensitivity** mirrors the GNU originals — the same `LC_ALL`
  discipline this book's coreutils pages teach applies unchanged.

## What This Means for the Per-Binary Pages

The per-binary pages in this part — [ls](../coreutils/ls.md),
[cp](../coreutils/cp.md), [sort](../coreutils/sort.md), [df](../coreutils/df.md),
[du](../coreutils/du.md), [stat](../coreutils/stat.md) and the rest of the
[coreutils collection](../coreutils/overview.md) — describe GNU behavior.
That is not a limitation; it is the point: GNU semantics are the
compatibility target the rewrites aim at, so GNU-first documentation remains
correct as the userland transitions underneath it. Where uutils-specific
drift exists today, it lives in the rare-flag/locale long tail — the same
places GNU-vs-BSD drift lives — and the migration-risk analysis in the
interview section is how you reason about it operationally.

## Interview Questions

### Q: Your distribution announces it is switching GNU coreutils to uutils. Walk through your migration-risk analysis.

Start with the evidence: which utilities are marked ready, and what are their
GNU test-suite pass rates — that is the parity baseline. Then localize the
risk: production scripts' flag usage against the rare-flag/locale long tail
where drift concentrates; anything exercising exotic combinations deserves a
canary. Run your own differential checks on a corpus of real invocations
(same argv through both binaries, diff stdout/stderr/exit code) before
cutover, keep the old userland one rollback away, and monitor for exit-code
or formatting changes in cron/systemd jobs. The strong answer treats it as a
compatibility-testing exercise, not a faith-based upgrade.

### Q: MIT versus GPL — what actually changes when a userland is MIT-licensed?

Factually: GPL-3.0 requires that distributed binaries ship with source and
that modifications stay under the GPL; MIT permits redistribution and
proprietary integration with attribution and no source obligation. For an
end user typing `ls`, nothing changes. For a vendor embedding the userland in
a shipped product, the MIT path removes license-compliance work; for a
distribution, the license is mostly irrelevant to behavior but relevant to
ecosystem effects — which is why the honest answer states the mechanics and
stops short of "therefore better". Know what each license requires, and you
can answer for either side.

### Q: Why does uutils run the GNU test suite instead of only its own tests?

Because the compatibility target is GNU behavior, and the GNU suite *is*
that behavior, written down: decades of edge-case decisions, exit codes, and
error-message formats that scripts silently depend on. A rewrite judged only
by its own tests is free to drift anywhere its authors didn't think about —
the suite is the external anchor. The complement is differential fuzzing,
because a test suite only covers cases someone imagined. Suite for known
edge cases, fuzzing for unknown ones, per-utility status tracking for
progress: that three-layer strategy is the model answer.

### Q: The uutils `coreutils` binary doesn't replace `/usr/bin/ls` when installed. Why is that the right default, and when would you flip it?

Because an implicit PATH takeover of core system tools by an early-maturity
rewrite would be the least testable upgrade imaginable — silent, global, and
hard to attribute when something breaks. Opt-in dispatch (`coreutils ls`) or
an explicit symlink farm keeps the change visible and reversible, exactly
like BusyBox's `--install`. You flip it deliberately: in a dedicated test
container, a CI image pinned for parity experiments, or once your org has
run its differential corpus clean — never as a side effect of installing a
package.

### Q: Does the Rust rewrite change performance characteristics?

It can, and the project does not claim parity there — behavioral
compatibility is the goal, not cycle-for-cycle equivalence. In practice most
userland cost is process spawn plus I/O, which the rewrite does not change;
hot loops inside one invocation (sorting a large file, for instance) can
differ in either direction. The operational advice is the same as for any
implementation change: benchmark the specific workload if it matters. The
test suite pins behavior contracts, not nanoseconds.

## References

- [uutils project](https://uutils.org/)
- [Source — GitHub](https://github.com/uutils/coreutils)
- [POSIX 2018 spec — Shell & Utilities](https://pubs.opengroup.org/onlinepubs/9699919799/)
