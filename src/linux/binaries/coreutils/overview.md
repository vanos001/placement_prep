# GNU Coreutils — Collection Overview

The GNU Core Utilities — always "coreutils" — is the package that makes a
Linux system feel like Linux. Its 104 binaries cover file operations, text
processing, checksums, and the small shell-facing tools that scripts lean on
every minute. This collection gives each binary its own page: synopsis in
man-page style, mechanics, the options that matter, gotchas, and interview
questions. An Overview facts table on every page anchors the basics; this
page carries what the binaries share.

## Why One Page Per Binary

Two binaries that look similar are usually separated by a real behavioral
boundary — `cp` and `mv` differ in inode bookkeeping, not just a rename
syscall; `head -n -5` and `tail -n +5` look symmetric but parse differently.
Interview questions exploit exactly those boundaries, so this collection
keeps each tool's semantics on its own page and uses cross-links for shared
concepts. The checksum family is the clearest example: `md5sum` explains the
coreutils checksum-file format once, and `sha256sum` links to it instead of
restating it.

## Lineage

Coreutils descends from the Unix userland of the 1970s, was assembled as the
GNU "fileutils", "textutils", and "sh-utils" packages through the 1980s and
1990s, and merged into one package in 2002. It has shipped as the default
userland on every major GNU/Linux distribution since. Debian's `coreutils`
package (bookworm ships the 9.1 series; current upstream is the 9.x line)
installs everything under `/usr/bin` — the historical `/bin` split collapsed
with the usrmerge. Today the package is unusually stable: interfaces added
decades ago are still supported, and new options arrive slowly and
conservatively, which is exactly why mastery pays off across every distro
you will ever touch.

The Rust rewrite project uutils is re-implementing this package command by
command and is already being adopted by Ubuntu — see
[uutils Coreutils Overview](../uutils/overview.md) for the compatibility
picture. Its per-command status page is the fastest way to check whether a
portability concern applies to you.

## Standards Position

| Layer | What it fixes | Examples in this collection |
|---|---|---|
| POSIX 2018 | Syntax, options, exit codes for ~100 utilities | `ls`, `cp`, `sort`, `tr`, `test` |
| GNU extensions | Everything POSIX leaves open: long options, `-h` sizes, deeper formats | `sort -h -V`, `du --apparent-size`, `date -d` |
| GNU-only tools | Utilities POSIX does not define | `numfmt`, `shuf`, `stdbuf`, `timeout`, `runcon` |

The rule of thumb: when a page's Nuances section mentions portability, the
GNU behavior described is what you get on Debian/Ubuntu/RHEL/Fedora; the BSDs
and BusyBox often implement the POSIX subset plus their own divergences. When
a script must survive those platforms, prefer the POSIX core and test.

## The Inventory

### File operations (24)

| Binary | One-liner | Page |
|---|---|---|
| `cp` | Copy files and directories | [cp](./cp.md) |
| `dd` | Block-level copy and convert | [dd](./dd.md) |
| `install` | Copy with mode/owner/timestamp control | [install](./install.md) |
| `ln` | Create hard and symbolic links | [ln](./ln.md) |
| `ls` | List directory contents | [ls](./ls.md) |
| `dir` | `ls` equivalent with different defaults | [dir](./dir.md) |
| `vdir` | `ls -l` equivalent | [vdir](./vdir.md) |
| `dircolors` | Generate LS_COLORS setup | [dircolors](./dircolors.md) |
| `mkdir` | Create directories | [mkdir](./mkdir.md) |
| `mkfifo` | Create named pipes | [mkfifo](./mkfifo.md) |
| `mknod` | Create device and FIFO nodes | [mknod](./mknod.md) |
| `mktemp` | Create secure temporary files/dirs | [mktemp](./mktemp.md) |
| `mv` | Move/rename files | [mv](./mv.md) |
| `realpath` | Resolve canonical paths | [realpath](./realpath.md) |
| `rm` | Remove files and trees | [rm](./rm.md) |
| `rmdir` | Remove empty directories | [rmdir](./rmdir.md) |
| `shred` | Overwrite in place before delete | [shred](./shred.md) |
| `sync` | Flush page cache to disk | [sync](./sync.md) |
| `touch` | Create/retimestamp files | [touch](./touch.md) |
| `truncate` | Resize to a length | [truncate](./truncate.md) |
| `stat` | File/inode status detail | [stat](./stat.md) |
| `df` | Filesystem capacity | [df](./df.md) |
| `du` | Directory disk usage | [du](./du.md) |
| `chcon` | Change SELinux file context | [chcon](./chcon.md) |

### Ownership and metadata

| Binary | One-liner | Page |
|---|---|---|
| `chgrp` | Change group ownership | [chgrp](./chgrp.md) |
| `chmod` | Change permission bits | [chmod](./chmod.md) |
| `chown` | Change user/group ownership | [chown](./chown.md) |

### Text processing (39)

| Binary | One-liner | Page |
|---|---|---|
| `base32` | RFC 4648 base-32 codec | [base32](./base32.md) |
| `base64` | RFC 4648 base-64 codec | [base64](./base64.md) |
| `basenc` | Unified encoder (base16/32/64url/z85) | [basenc](./basenc.md) |
| `cat` | Concatenate and print | [cat](./cat.md) |
| `cksum` | CRC32 and newer checksums | [cksum](./cksum.md) |
| `comm` | Compare two sorted files line-wise | [comm](./comm.md) |
| `csplit` | Split by context/regex | [csplit](./csplit.md) |
| `cut` | Slice fields/bytes/columns | [cut](./cut.md) |
| `expand` | Tabs to spaces | [expand](./expand.md) |
| `fmt` | Reflow paragraphs | [fmt](./fmt.md) |
| `fold` | Wrap fixed width | [fold](./fold.md) |
| `head` | First lines/bytes | [head](./head.md) |
| `tail` | Last lines/bytes, follow mode | [tail](./tail.md) |
| `join` | Relational join on a field | [join](./join.md) |
| `nl` | Number lines with styles | [nl](./nl.md) |
| `numfmt` | Human-readable number conversion | [numfmt](./numfmt.md) |
| `od` | Octal/byte-level dump | [od](./od.md) |
| `paste` | Merge lines column-wise | [paste](./paste.md) |
| `pr` | Paginate for printing | [pr](./pr.md) |
| `ptx` | Permuted index | [ptx](./ptx.md) |
| `shuf` | Random permutation | [shuf](./shuf.md) |
| `sort` | Sort lines (keys, numeric, version) | [sort](./sort.md) |
| `split` | Split into chunks | [split](./split.md) |
| `tac` | Reverse lines | [tac](./tac.md) |
| `tee` | Tap a pipeline | [tee](./tee.md) |
| `tr` | Translate/delete characters | [tr](./tr.md) |
| `tsort` | Topological sort | [tsort](./tsort.md) |
| `unexpand` | Spaces to tabs | [unexpand](./unexpand.md) |
| `uniq` | Collapse/report repeated lines | [uniq](./uniq.md) |
| `wc` | Count lines/words/bytes | [wc](./wc.md) |

### Checksums (9)

| Binary | One-liner | Page |
|---|---|---|
| `md5sum` | MD5 checksums (format anchor) | [md5sum](./md5sum.md) |
| `sha1sum` | SHA-1 checksums | [sha1sum](./sha1sum.md) |
| `sha224sum` | SHA-224 checksums | [sha224sum](./sha224sum.md) |
| `sha256sum` | SHA-256 checksums | [sha256sum](./sha256sum.md) |
| `sha384sum` | SHA-384 checksums | [sha384sum](./sha384sum.md) |
| `sha512sum` | SHA-512 checksums | [sha512sum](./sha512sum.md) |
| `b2sum` | BLAKE2 checksums | [b2sum](./b2sum.md) |
| `sum` | Legacy BSD/SysV checksums | [sum](./sum.md) |
| `printenv` | Print environment variables | [printenv](./printenv.md) |

### Shell and system (32)

| Binary | One-liner | Page |
|---|---|---|
| `arch` | Print machine architecture | [arch](./arch.md) |
| `basename` | Strip directory/suffix | [basename](./basename.md) |
| `chroot` | Run in a new root | [chroot](./chroot.md) |
| `date` | Print/convert dates | [date](./date.md) |
| `dirname` | Strip last component | [dirname](./dirname.md) |
| `echo` | Print arguments | [echo](./echo.md) |
| `env` | Run with modified environment | [env](./env.md) |
| `expr` | Evaluate expressions (legacy) | [expr](./expr.md) |
| `factor` | Prime factorization | [factor](./factor.md) |
| `false` | Exit 1 | [false](./false.md) |
| `groups` | Print group memberships | [groups](./groups.md) |
| `hostid` | Print numeric host id | [hostid](./hostid.md) |
| `id` | Print uid/gid identity | [id](./id.md) |
| `link` | link(2) wrapper | [link](./link.md) |
| `logname` | Login name from utmp | [logname](./logname.md) |
| `nice` | Run at adjusted niceness | [nice](./nice.md) |
| `nohup` | Immune to SIGHUP | [nohup](./nohup.md) |
| `nproc` | CPU count | [nproc](./nproc.md) |
| `pathchk` | Check path portability | [pathchk](./pathchk.md) |
| `pinky` | Lightweight finger | [pinky](./pinky.md) |
| `printf` | Format and print data | [printf](./printf.md) |
| `pwd` | Print working directory | [pwd](./pwd.md) |
| `readlink` | Resolve symlink targets | [readlink](./readlink.md) |
| `runcon` | Run in a security context | [runcon](./runcon.md) |
| `seq` | Print number sequences | [seq](./seq.md) |
| `sleep` | Delay for an interval | [sleep](./sleep.md) |
| `stdbuf` | Adjust stdio buffering | [stdbuf](./stdbuf.md) |
| `stty` | Terminal line discipline | [stty](./stty.md) |
| `test` | File/condition checks (`[`) | [test](./test.md) |
| `timeout` | Run with a time limit | [timeout](./timeout.md) |
| `true` | Exit 0 | [true](./true.md) |
| `tty` | Print terminal name | [tty](./tty.md) |
| `uname` | Kernel/system info | [uname](./uname.md) |
| `unlink` | unlink(2) wrapper | [unlink](./unlink.md) |
| `users` | Current login names | [users](./users.md) |
| `who` | Who is logged in | [who](./who.md) |
| `whoami` | Effective username | [whoami](./whoami.md) |
| `yes` | Repeat a string forever | [yes](./yes.md) |

## Shared Conventions Worth Knowing Once

Every page assumes these; knowing them once saves repetition.

- **Long options**: GNU coreutils accepts `--long-name` and unique prefixes;
  `--` ends option parsing, which is why `touch -- "$file"` is the safe
  pattern for hostile filenames.
- **Exit codes**: 0 success, 1 minor failure (per-file errors keep going),
  2 serious trouble (bad invocation, missing operand). Tools that verify
  (`test`, `cmp`, `sort -c`) use 1 to mean "check failed", not "crashed".
- **`--help` / `--version`**: consistent across the package and the basis of
  most of this book's flag tables.
- **`-` and `/dev/stdin`**: most text tools read stdin on `-`; `dd` and
  `cat` also accept `/dev/stdin`, which matters for process substitution.
- **Locale**: collation and character classes change behavior under
  non-`C` locales — the `sort` and `tr` pages show concrete traps and the
  `LC_ALL=C` fix.
- **Signal discipline**: text filters die on SIGPIPE (exit 143) unless they
  opt out; `tail -f`, `tee -p`, and `timeout --preserve-status` each handle
  this differently — covered on their pages.

## Reading Order For Interview Prep

1. Flagships first: [ls](./ls.md), [cp](./cp.md), [mv](./mv.md),
   [rm](./rm.md), [chmod](./chmod.md), [chown](./chown.md),
   [sort](./sort.md), [df](./df.md), [du](./du.md), [stat](./stat.md).
2. Pipeline tools: [cut](./cut.md), [tr](./tr.md), [head](./head.md),
   [tail](./tail.md), [tee](./tee.md), [uniq](./uniq.md),
   [wc](./wc.md), [od](./od.md).
3. Scripting load-bearers: [test](./test.md), [printf](./printf.md),
   [env](./env.md), [mktemp](./mktemp.md), [timeout](./timeout.md),
   [date](./date.md).
4. The rest is breadth — skim One-liners above and target gaps.

Text-search siblings that are NOT coreutils live in the shell collection:
[find](../../shell/find.md), [grep](../../shell/grep.md),
[sed and awk](../../shell/sed-awk.md), and
[xargs](../../shell/xargs.md) have their own deep pages there.

## Interview Questions

### Q: Why does `sort -u` not replace `sort | uniq`?

They agree on output but differ in semantics and cost. `sort -u` dedupes on
the full line only by default, while `uniq -c` and friends operate on
adjacent duplicates with field-skipping options (`-f`, `-s`, `-w`) that
`sort -u` cannot express; and `sort | uniq -c | sort -rn` builds histograms
you cannot get from `-u`. With GNU sort's parallel and external-merge
machinery a single `sort -u` is usually faster for plain dedup, which is
precisely the trade-off interviewers want you to articulate.

### Q: What do exit codes 0, 1, and 2 mean across coreutils?

0 is success; 1 is a minor failure where per-file work continued (a file
disappeared mid-`du`, a checksum mismatch with `md5sum -c`); 2 is serious
trouble such as a bad invocation or missing operand. Verification tools
reuse 1 to mean "the check itself failed" — `test`/`[` returns 1 for a
false condition — so shell code must treat 1 as data, not as an error.

### Q: Why do scripts write `touch -- "$file"` and `rm -- "$file"`?

A filename like `-f` would otherwise parse as an option. `--` ends option
parsing for every coreutils tool, making the argument list unambiguous. The
same pattern protects `cp`, `mv`, and `sort` pipelines fed by hostile or
machine-generated names.

### Q: Where does the userland end and the shell begin?

Coreutils binaries are external programs; the shell builtin set (`cd`,
`export`, `[[`, `$(( ))`) is not part of coreutils. That is why
`/usr/bin/echo` and the bash builtin `echo` differ in details like `-e`, and
why `printf` is the portable choice — the same tension is covered on the
[echo](./echo.md) and [printf](./printf.md) pages.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page index(1,8) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/)
- [POSIX 2018 spec — Shell & Utilities](https://pubs.opengroup.org/onlinepubs/9699919799/)
