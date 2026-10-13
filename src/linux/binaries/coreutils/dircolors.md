# dircolors — generate the LS_COLORS environment variable

## Overview

`dircolors` does not color anything itself. It is a small translator: it takes a color database (the built-in one, or one you supply as a file in the classic `/etc/DIR_COLORS` format) and emits shell commands that set the `LS_COLORS` environment variable — the palette that GNU `ls` (and siblings `dir` and `vdir`, plus `--color`-aware tools like some `grep` builds) consult when colorizing directory listings. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/dircolors`.

The eval idiom `eval "$(dircolors -b)"` in a shell startup file is the whole contract: `dircolors` outputs an assignment plus an `export`, so it must go through `eval` rather than command substitution alone. `LS_COLORS` is a GNU convention, but an influential one — FreeBSD's `ls` reads it too, while macOS's BSD `ls` uses the incompatible `LSCOLORS` format instead.

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/dircolors |
| First appeared | GNU fileutils, mid-1990s (as the `LS_COLORS` database generator) |
| Standards | None — GNU extension; `LS_COLORS` is a widely imitated de-facto convention |

## Synopsis

```
dircolors [OPTION]... [FILE]
```

Common one-line forms:

```
dircolors -b                 # Bourne-shell output (bash, zsh, ...) — the default
dircolors -c                 # C-shell output (csh, tcsh)
dircolors -p                 # print the built-in database in DIR_COLORS format
dircolors -b ~/.dircolors    # compile a custom database file
```

## How It Works

### The colorization pipeline

```
~/.dircolors (or /etc/DIR_COLORS, or nothing = built-in database)
        │
        ▼
   dircolors -b FILE
        │  emits:   LS_COLORS='di=01;34:ln=01;36:*.tar=01;31:...';
        │           export LS_COLORS
        ▼
   eval "..."          ← assignment + export both take effect
        │
        ▼
   LS_COLORS in the environment of the shell
        │
        ▼
   ls --color=auto ──── for each entry: stat it, pick a key
        │               (file-type code first, then glob patterns),
        ▼               wrap the name in the corresponding SGR sequence
   ANSI escapes on the terminal
```

### LS_COLORS grammar

The value of `LS_COLORS` is a colon-separated list of `KEY=VALUE` pairs. Verified from a real run (`TERM=xterm-256color dircolors -b`):

```
LS_COLORS='rs=0:di=01;34:ln=01;36:pi=40;33:so=01;35:bd=40;33;01:
           cd=40;33;01:or=40;31;01:su=37;41:sg=30;43:tw=30;42:
           ow=34;42:ex=01;32:*.tar=01;31:*.jpg=01;35:...';
```

- **Two-letter type codes** select by file type: `di` directory, `ln` symlink, `pi` FIFO, `so` socket, `bd`/`cd` block/char device, `ex` executable, `fi` regular file, `or` orphaned symlink, `mi` missing target, `su`/`sg` setuid/setgid, `tw`/`ow`/`st` sticky+world-writable / other-writable / sticky, `mh` multi-hardlink, `do` door, `ca` capability, `rs` reset.
- **Glob keys** such as `*.tar=01;31` match file names and are checked after the type codes — a compressed archive gets the archive color, not the plain-file color.
- **Values are SGR parameters**: the numbers `ls` puts between `ESC[` and `m`. `01;34` = bold blue; `38;5;196` and `38;2;255;0;0` work on 256-color/truecolor terminals. An empty value means no special treatment.
- **Special value `target`** for `ln`: color a symlink according to the type of its target rather than as a link.

The type codes in one view (values shown are the built-in defaults):

| Code | Meaning | Default |
| --- | --- | --- |
| `di` | directory | `01;34` |
| `ln` | symbolic link (`target` = color by target type) | `01;36` |
| `pi` / `so` / `do` | FIFO / socket / door | `40;33` / `01;35` / `01;35` |
| `bd` / `cd` | block / character device | `40;33;01` |
| `ex` | executable by a permission bit | `01;32` |
| `fi` / `rs` | regular file / reset | `00` / `0` |
| `su` / `sg` | setuid / setgid | `37;41` / `30;43` |
| `tw` / `ow` / `st` | sticky+world-writable / other-writable / sticky | `30;42` / `34;42` / `37;44` |
| `or` / `mi` | orphaned symlink / missing target | `40;31;01` / `00` |
| `mh` / `ca` | multi-hardlink file / capability file | `00` / `00` |

### The database file format

`dircolors -p` prints the built-in database — 245 lines on this system — in the same format a custom file uses:

```
DIR 01;34 # directory
LINK 01;36 # symbolic link. (If you set this to 'target' instead of a
           # numerical value, the color is determined by the target...)
FIFO 40;33 # pipe
ORPHAN 40;31;01 # symlink to nonexistent file
EXEC 01;32
.jpg 01;35        # image formats
.tar 01;31        # archive formats
```

Rules: `#` starts a comment; keyword lines use the long uppercase names (`DIR`, `LINK`, `FIFO`, `SOCK`, `BLK`, `CHR`, `ORPHAN`, `SETUID`, `SETGID`, `STICKY`, `OTHER_WRITABLE`, `EXEC`, `NORMAL`, ...); suffix lines like `.jpg 01;35` become `*.jpg` glob entries; `TERM xterm-256color` (and `COLORTERM`) lines gate which terminal types a following section applies to; the legacy Slackware keywords `COLOR`, `OPTIONS`, and `EIGHTBIT` are recognized but ignored.

### Why eval, and where the file lives

`dircolors` never sets anything in your environment — it prints shell code. Because the output is two statements (`LS_COLORS='...';` and `export LS_COLORS`), plain command substitution would only echo them; `eval` executes them. Debian's stock `/etc/skel/.bashrc` shows the canonical pattern, including the optional custom database:

```bash
# /etc/skel/.bashrc (Debian), verbatim
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
fi
```

Note the Debian convention: an optional per-user `~/.dircolors`. The famous `/etc/DIR_COLORS` path is a Slackware/Red-Hat convention — Debian ships no such file; nothing reads a database implicitly, the file argument must be passed to `dircolors` explicitly.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-b`, `--sh`, `--bourne-shell` | Emit Bourne-shell code (assignment + export) — the default |
| `-c`, `--csh`, `--c-shell` | Emit C-shell code (`setenv LS_COLORS ...`) for csh/tcsh |
| `-p`, `--print-database` | Print the built-in database in DIR_COLORS format; ignores FILE |
| `--print-ls-colors` | Print the resolved entries, colors displayed, one per line |
| `FILE` (operand) | Read colors from this database file instead of the built-in one |

## Usage Patterns

```bash
# The standard startup-file idiom: import the default palette
eval "$(dircolors -b)"
```

```bash
# Debian skeleton-file pattern: use ~/.dircolors if present
test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
```

```bash
# Start from the stock database, then edit
dircolors -p > ~/.dircolors && "$EDITOR" ~/.dircolors
```

```bash
# Inspect what the built-in database assigns to file types
dircolors -p | sed -n '/^DIR/p;/^EXEC/p;/^ORPHAN/p'
```

```bash
# See the full resolved palette, rendered in color, one entry per line
dircolors --print-ls-colors | head -20
```

```bash
# One-off tint without a database file: append to the existing variable
LS_COLORS="$LS_COLORS:di=01;33" ls --color=auto
```

```bash
# Highlight your own extension (logs in flashing-free bright yellow)
printf '%s\n' '.log 01;33' > ~/.dircolors
dircolors -b ~/.dircolors   # check the generated LS_COLORS first
```

```bash
# csh/tcsh users get C-shell syntax
dircolors -c ~/.dircolors   # emits: setenv LS_COLORS '...'
```

```bash
# Verify what ls actually emits for a directory entry
LS_COLORS='di=01;35' ls --color=always -d /tmp | cat -v
# ^[[01;35m/tmp^[[0m
```

```bash
# Per-terminal palettes inside one database file
#   TERM screen-256color
#   DIR 00;36
#   TERM xterm-256color
#   DIR 01;34
```

```bash
# Diagnose "why is my directory not red?" — see what ls resolves for one entry
LS_COLORS='di=01;31' ls --color=always -d /tmp | cat -v
```

```bash
# Ship a project-specific palette in a repo without touching ~/.dircolors
eval "$(dircolors -b contrib/repo-ls-colors)"
```

## Nuances and Gotchas

- **dircolors colors nothing, ls decides everything.** The variable is only consulted by programs that opt in (`ls --color`, `dir --color`, `vdir --color`, and look-alikes). Without `--color=auto`/`always`, `LS_COLORS` is inert. It does not affect `find`, `tree`, or your terminal's own palette.
- **`eval` is mandatory, and the dialect must match the shell.** Piping `dircolors -c` output into bash, or evaluating the `-b` output in csh, breaks. The output is literally code — treat database edits the way you treat shell edits.
- **Glob keys match names, not types.** `*.tar` matches any name ending in `.tar` (after type codes like `di`/`ex` are checked). A directory named `backups.tar` still colors as a directory: type codes win over globs.
- **Empty palette is valid.** When `$TERM` is unknown, plain `dircolors -b` prints `LS_COLORS='';` — an empty variable. `ls` then falls back to its compiled-in defaults, not to monochrome.
- **Parsing color output is a bug factory.** ANSI codes leak into logs, greps, and git blobs when `--color=always` output is redirected. Colors are presentation-only; strip with `sed 's/\x1b\[[0-9;]*m//g'` if you inherit polluted text.
- **Portability.** `dircolors` itself is GNU-only; macOS/BSD users get `LSCOLORS` (different format) on macOS, while FreeBSD's `ls` does honor `LS_COLORS`. BusyBox `ls` understands a small subset. Scripts should treat the variable as a convenience, never a dependency.
- **Terminal gating.** A database can deliver different palettes per `TERM`/`COLORTERM` value; if your custom colors "don't apply", check whether a `TERM` line above your entries excluded your terminal.
- **`NORMAL` is the fallback, not a reset.** `NORMAL` (key `fi`) colors ordinary files; it does not undo other entries. The `rs` (`RESET`) code is what `ls` emits after each colored name to stop the attributes from bleeding into following text.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Database read and shell code emitted |
| 1 | Failure — e.g. the FILE operand cannot be read (`dircolors: /nonexistent: No such file or directory`) |

## Related Commands

- [`ls`](./ls.md) — the consumer: `--color` maps entries through `LS_COLORS`.
- [`dir`](./dir.md) — columnar sibling; `--color` behavior identical.
- [`vdir`](./vdir.md) — long-format sibling; same palette.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [bash](../../shell/bash.md) — where the `eval "$(dircolors -b)"` idiom lives (startup files, aliases).
- [env](./env.md) — inspecting the environment where `LS_COLORS` ends up.
- [man pages](../../reference/man-pages.md) — the full option list and format notes.

## Interview Questions

### Q: What is the format of LS_COLORS and what are its two kinds of keys?

A colon-separated list of `KEY=VALUE` pairs where values are SGR parameter lists (e.g. `01;34` for bold blue). The two kinds of keys are two-letter file-type codes (`di` directory, `ln` symlink, `ex` executable, `or` orphan, `su` setuid, ...) and glob patterns against file names (`*.tar=01;31`). Type codes are checked first, so a directory named `x.tar` still gets the directory color; `ln=target` is a special value that colors symlinks by their target's type.

### Q: Why does the canonical idiom use eval rather than just running dircolors?

`dircolors` outputs two shell statements — an assignment of the whole palette to `LS_COLORS` and an `export LS_COLORS` — rather than modifying its caller's environment (a child process cannot). Command substitution alone would print the code; `eval "$(dircolors -b)"` executes it in the current shell. The `-c` variant emits `setenv` for C shells, so the flag must match the shell you're in.

### Q: How do you add a custom color for your project's extension, end to end?

Seed from the stock database (`dircolors -p > ~/.dircolors`), add a line like `.conf.d 01;33` (suffix entries become `*.conf.d` globs), and load it in `~/.bashrc` with `eval "$(dircolors -b ~/.dircolors)"`. Verify with `dircolors --print-ls-colors` or by running `ls --color=always -d <file> | cat -v` to see the raw SGR wrapping. Watch for `TERM` gating lines in the file — entries only apply to terminals matched above them.

### Q: Where does /etc/DIR_COLORS fit in, and what does Debian do instead?

`/etc/DIR_COLORS` is a Slackware/Red-Hat convention: a system-wide database that their startup scripts pass to `dircolors`. Nothing in `dircolors` or `ls` reads it implicitly — it only matters because someone wrote `eval "$(dircolors -b /etc/DIR_COLORS)"`. Debian ships no such file; its `/etc/skel/.bashrc` instead checks for a per-user `~/.dircolors` and otherwise falls back to `dircolors -b` with the compiled-in database.

### Q: A colleague pipes `ls --color=always` into grep and gets matches that "look right but act wrong". What happened?

The grep matches include ANSI escape sequences embedded in the text, so the match works visually but downstream tools see `\x1b[01;34metc\x1b[0m` instead of `etc` — comparisons, sorting, and parsing all break. Root cause: `--color=always` forces escapes regardless of output type; the fix is `--color=auto` (escapes only on a tty) or stripping them with `sed 's/\x1b\[[0-9;]*m//g'`. It's a reminder that `LS_COLORS` is presentation metadata and must never become part of a data pipeline.

### Q: Is LS_COLORS standardized? What do non-GNU ls implementations do?

No — it's a GNU coreutils convention, not a POSIX feature. The format was widely imitated: FreeBSD's `ls` honors `LS_COLORS`, while macOS's BSD `ls` uses its own `LSCOLORS` variable with a compact one-letter format (a completely different scheme). BusyBox `ls` supports a small subset. So scripts can rely on `ls --color=auto` behavior on GNU systems but should not assume any of the palette machinery exists elsewhere.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/dircolors.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
