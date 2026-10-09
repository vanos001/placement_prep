# Linux Userland Binaries — Part Overview

Every Linux system, from a laptop to a hyperscaler fleet to a two-megabyte
container image, is operated through a few hundred small binaries in
`/usr/bin` and `/usr/sbin`. They predate the kernel's reputation, outlive
distros, and outlast frameworks — and interviews probe them constantly
because they are the shared vocabulary of every Unix-like platform. This
part covers the core collections one binary at a time: what ships in each
package, what each binary actually does, the flags that matter, the gotchas
that break production scripts, and the questions interviewers actually ask.

## How This Part Is Organized

Collections follow the upstream packaging the binaries really come from —
the same names `uutils` uses for its Rust rewrites — so what you learn here
maps directly onto package managers, container base images, and minimal
distros. Each collection has an overview page with its inventory and shared
conventions, then one page per binary.

| Collection | Binaries | Start here |
|---|---|---|
| [GNU Coreutils](./coreutils/overview.md) | 104 | file ops, then pipelines |
| [util-linux](./util-linux/overview.md) | ~95 | mount, lsblk, fdisk |
| [shadow (account tools)](./shadow/overview.md) | 24 | useradd, passwd |
| [login (session tools)](./login/overview.md) | 7 | login, nologin |
| [procps](./procps/overview.md) | 17 | ps, top, free |
| [findutils](./findutils/overview.md) | 2 + deep pages | locate, updatedb |
| [diffutils](./diffutils/overview.md) | 4 | diff, cmp |
| [grep](./grep/overview.md) | hub | → deep page |
| [GNU sed](./sed/overview.md) | hub | → deep page |
| [Gawk](./gawk/overview.md) | hub | → deep page |
| [GNU tar](./tar.md) | 1 | the archiver |
| [ACL tools](./acl/overview.md) | 3 | setfacl, getfacl |
| [hostname](./hostname.md) | 1 | hostname + variants |
| [bsdutils](./bsdutils/overview.md) | 7 | logger, script, wall |
| [BusyBox](./busybox.md) | 1 + applet matrix | the multi-call binary |
| [uutils](./uutils/overview.md) | 1 | the Rust rewrite landscape |

Coverage note: `find`, `xargs`, `grep`, `sed`, and `awk` already have deep
dedicated pages in the shell track — [find](../shell/find.md),
[xargs](../shell/xargs.md), [grep](../shell/grep.md), and
[sed + awk](../shell/sed-awk.md) — and remain the canonical treatment; the
collection hubs here link into them and add package-level context rather
than repeating usage coverage.

## Why Packaging Matters

Debian splits these upstream projects into binary packages along
operational lines, and knowing the split is genuinely practical: a minimal
container that has `coreutils` still lacks `mount(8)` and `fdisk(8)` (they
live in separate packages), `locate` is not part of `findutils` on modern
Debian (it is `plocate`), and `logger`/`wall`/`script` ship in `bsdutils`
even though upstream calls them util-linux. When an interviewer asks "how
would you debug X in a stripped-down container," the answer often starts
with "first check the binary is even installed" — this part tells you which
package to reach for.

## Standards and Lineage

The collections mix three traditions. POSIX utilities (`ls`, `ps`, `kill`,
`sh`) behave comparably everywhere POSIX is implemented and are specified
down to option grammar and exit codes. GNU tools extend POSIX with long
options and richer semantics and are the default on every major Linux
distro. BSD-heritage tools (`wall`, `write`, `script`, `cal`) migrated into
Linux packaging from 4BSD and are named accordingly. Each page's facts
table and Nuances section state where a binary sits in that landscape, so
portability traps — the classic GNU-vs-BSD flag drift — are called out
where you will meet them.

## Conventions Used Across Pages

- Every binary page starts with an Overview facts table (package, man
  section, path, lineage, standards), then a man-style Synopsis, mechanics,
  the options that matter, usage patterns, nuances and gotchas, exit
  status, related commands, interview questions, and references.
- References carry the verified online man page, the source browser, and
  the project page; no page invents URLs.
- Cross-links are heavy by design: shared concepts are explained once on
  the most relevant page and linked from siblings. If two binaries share a
  man page (like `pgrep`/`pkill`), each still gets its own page with its
  own angle, linked both ways.
- Related book material: the shell track
  ([bash](../shell/bash.md), [POSIX shell](../shell/posix-shell.md),
  [regex](../shell/regex.md)), the admin track
  ([permissions](../admin/permissions.md),
  [users & groups](../admin/users-groups.md),
  [process management](../admin/process-management.md)), and
  [Linux Internals](../internals.md) provide the depth behind syscall
  behavior these pages reference.

## Interview Questions

### Q: A minimal container has `sh` but no `ls`. What shipped, and what do you reach for?

BusyBox-style images replace the whole userland with one multi-call binary
that changes behavior based on `argv[0]` or its first argument — see
[BusyBox](./busybox.md). Debugging steps: check `/proc/1/exe`, try
`busybox ls`, and know that applet availability depends on build config.
The broader point: "Linux commands" are packages, and thin images install
subsets — coreutils alone is ~15 MB of binaries and usually present, while
util-linux's storage tools often are not.

### Q: What does POSIX actually guarantee you about these tools?

Option syntax (`-abc` clustering, `--` end-of-options), operand ordering,
diagnostics on stderr, and exit-status conventions — not long options,
not GNU extensions like `sort -h`. Scripts that must survive Alpine,
macOS, and enterprise Unix stick to the POSIX core and test on each
platform. Collections here flag POSIX membership per binary so the
portable subset is visible at a glance.

### Q: Why does the same binary appear in multiple packages or collections?

Upstream project, Debian binary package, and logical collection are three
different axes. `login(1)` is upstream util-linux, ships in Debian's
`login` package, and belongs in this part's login collection; `logger(1)`
is the same upstream but ships in `bsdutils`. The pages cross-link rather
than duplicate — the same discipline you should apply when several teams
own overlapping tooling.

### Q: Rust rewrites are replacing these tools — does memorizing flags still matter?

Yes, because compatibility is the explicit goal: uutils passes the GNU
test suite for the commands marked "ready" and deliberately reproduces
GNU semantics, quirks included. The migration risk concentrates in
edge-case flag drift and in the long tail — exactly the nuances these
pages document. See [uutils Coreutils Overview](./uutils/overview.md)
for the per-collection status.

## References

- [POSIX 2018 spec — Shell & Utilities](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [man7.org — Linux man-pages project](https://man7.org/linux/man-pages/)
- [uutils project](https://uutils.org/)
