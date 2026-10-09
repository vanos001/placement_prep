# more — page through text one screenful at a time

## Overview

`more` is the original Unix pager: it prints a file (or stdin) to a terminal, stops after each screenful, and waits for a single-key command to continue, search, or give up. It ships in the `util-linux` package at `/usr/bin/more` and is present on essentially every Linux system because `util-linux` is an essential package — which is exactly why scripts and installers still fall back to it when fancier pagers may not exist.

`more` is often confused with `less`, its more capable sibling from the same niche (`less` supports backward scrolling, arbitrary movement, persistent search highlighting, and is Debian's default `PAGER` for `man`). `more` is also confused with `cat` in pipelines: when stdout is *not* a terminal, `more` degrades to a plain copy and never pauses. Reaching for `more` is mostly a "guaranteed available, dead simple" decision: interactive debugging on a minimal rescue system, predictable behavior in POSIX-portable scripts, and reading streams without loading them entirely into memory.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/more |
| First appeared | 3BSD (1979) |
| Standards | POSIX.1-2018 (`more`) |

## Synopsis

```
more [options] <file>...
```

Common one-line forms:

```
more /var/log/messages        # page a file, SPACE to advance, q to quit
more -s file                  # squeeze runs of blank lines
more +/ERROR logfile          # start at the first line matching ERROR
dmesg | more                  # page output of a pipe (stdin form)
```

## How It Works

### File selection and stdin

`more` pages each FILE operand in turn. With no operands it reads standard input. There are two very different runtime modes:

```
stdout is a terminal:  interactive pager; prompt per screenful; keys read from stdin (or /dev/tty)
stdout is a pipe/file: plain copy — behaves like cat, never pauses
```

```
$ seq 1 5 | more | head -2
1
2
$ echo "rc=$?"
rc=0
```

That degradation is deliberate (piped output must stay machine-readable) and is the most common `more` surprise: `somecmd | more` inside a non-interactive job simply prints everything.

If stdin is the data source and stdout is a terminal, `more` opens `/dev/tty` to read its single-key commands, so the pipe stays usable: `grep ... | more` still lets you press SPACE.

### The paging loop

`more` asks the terminal driver for the screen size (`TIOCGWINSZ`), falls back to the `LINES`/`TERM` environment or a compiled-in default, and reserves one line for the prompt. It then copies lines until the screen is full, shows a prompt, and blocks for one key:

```
┌───────────────────────────────┐
│ line 1                        │  screen area
│ ...                           │  (N-1 lines)
│ line N-1                      │
├───────────────────────────────┤
│ --More--(34%)                 │  prompt: name/percent per style
└───────────────────────────────┘
```

On Debian's util-linux `more` the prompt includes the percentage of the file already displayed; with `-d` it appends `[Press space to continue, 'q' to quit]`, and invalid keys produce help text instead of a bell — ideal for demos and for users who cannot remember the key map.

### Interactive commands

The single-key command set (from the current line, `k` is the last count prefix you typed):

```
h            help summary
SPACE / z    next screenful
<CR>         next line
d, ^D        scroll half a screen
s            skip forward k lines
f            skip forward k screenfuls
b, ^B        skip backward k screenfuls
/pattern     search forward for the k-th occurrence
n            repeat last search
'            return to the line where the last search started
=            print current line number
:f           print current file name and line number
:n / :p      next / previous file in the operand list
v            edit the current file at the current line via $EDITOR
!command     run a shell escape (uses $SHELL)
^L           redraw the screen
q, Q, ZZ     quit
.            repeat the previous command
```

There is no full-screen cursor movement, no scrolling within a screenful, and no regex variants of search — that is the line where `less` begins.

### Option processing and the MORE variable

Flags are processed left to right and *stick* for the rest of the run: `more -s -c file` squeezes blanks and repaints from the top for every page, not just the first. The `MORE` environment variable is prepended to the command line, so configuration set once in a profile shapes every invocation — including the ones other tools make on your behalf:

```
$ export MORE="-s -d"          # squeeze blanks, friendly prompt, everywhere
$ git log | more               # picks up BOTH flags without them on the line
```

Precedence, low to high: compiled-in defaults → `MORE` → explicit command-line flags. `PAGER=more` is a different layer — it only decides *which* pager a tool spawns; `MORE` then configures that pager.

### Environment

| Variable | Effect |
| --- | --- |
| `MORE` | Default flags applied before the command line (space separated; may include `+N` and `+/pattern`) |
| `TERM` | Terminal capability lookup; wrong values cause redraw/paint garbage |
| `SHELL` | Shell used by `!` escapes |
| `EDITOR` | Editor started by `v` (falls back to `vi`) |

## Options That Matter

| Option | Effect |
| --- | --- |
| `-d`, `--silent` | Friendly prompt + error help instead of bell |
| `-f`, `--logical` | Count logical lines, not wrapped screen lines (long lines count once) |
| `-l`, `--no-pause` | Do not pause after a form feed (`^L`) in the input |
| `-c`, `--print-over` | Paint from the top, clear line ends — no scroll |
| `-p`, `--clean-print` | Clear the whole screen, then print — no scroll |
| `-s`, `--squeeze` | Collapse runs of blank lines into one |
| `-u`, `--plain` | Suppress underlining/backspaces from nroff-era output |
| `-n N`, `-N` | Use N lines per screen instead of the detected size |
| `+N` | Start displaying at line N |
| `+/pattern` | Start displaying two lines before the first match |

Recent util-linux releases (the 2.40+ rewrite) add `-e`/`--exit-on-eof` and friends; Debian bookworm's `more(1)` documents the set above, so avoid depending on the newer flags in portable scripts.

## Usage Patterns

```bash
# Read a large log without a editor, squeezing nroff-style double spacing
more -s /var/log/daemon.log
```

```bash
# Jump straight to the interesting part of a huge file
more +/Traceback /tmp/build.log
```

```bash
# Demo-friendly paging for other users: help on every wrong key
more -d /etc/motd
```

```bash
# Page a live stream (stdin form); /dev/tty is used for commands
journalctl -u nginx | more
```

```bash
# Count a wrapped kernel dump as logical lines so percentages stay sane
dmesg | more -f
```

```bash
# Force 40-line screens on a small window
more -n 40 /usr/share/doc/bash/README.Debian
```

```bash
# A guaranteed pager for scripts that must run anywhere
export PAGER=more
man ls
```

```bash
# Start 100 lines into a file
more +100 /var/log/auth.log
```

```bash
# Inspect a file mid-pipeline without losing the data
ps auxww | more
```

```bash
# Prove the pipe behavior: identical to cat, no pause, no prompt
seq 1 100000 | more | wc -l
```

```bash
# Step through several files with :n / :p; :f shows where you are
more -d /var/log/syslog /var/log/auth.log
```

```bash
# Terminal with an unusual size (serial console): force the geometry
more -n 24 /etc/fstab
```

## Nuances and Gotchas

- **Pipe means "no paging".** `more` only pauses when stdout is a TTY. `cmd | more > out.txt` or a detached `more` in a cron job copies the whole input silently — a classic cause of "the script finished but scrolled everything away".
- **`more` is not `less`.** No backward search, no movement within a screen, no `-R` color handling. If you muscle-memory `?pattern` or `G`, you want `less`; `more` will just show the help screen or beep.
- **Wrapped lines inflate screen counts.** A 200-column line on an 80-column terminal occupies three screen lines. `-f` counts logical lines instead; this matters for `dmesg`, stack traces, and `%` accuracy.
- **`MORE` leaks into everything.** Like `LESS`, the `MORE` variable is applied to every `more` invocation, including inside other tools' code paths. A stray `MORE=-d` in your environment changes output that looks prompt-configured "by default".
- **Binary files are not detected.** `more` happily pushes control bytes to the terminal; `less` detects binary content and warns. Use `strings` or `xxd` for unknown files.
- **Form feeds pause.** Legacy nroff/`man` output containing `^L` makes `more` stop unexpectedly; `-l` suppresses that pause, `-c`/`-p` change the repaint style instead of scrolling.
- **POSIX defines `more` but not the extras.** POSIX.1-2018 standardizes the basic key set; `-d`, `-f`, `-s` details vary across BSD/GNU/busybox implementations. BusyBox `more` is a dramatically reduced clone (no search, no `-d` help text).
- **`v` spawns `$EDITOR` on the *file*, not the pipe.** It cannot work when reading stdin (no file to reopen), so it errors out there.
- **`ZZ` quits, `q` quits, but `^Z` may suspend.** Muscle memory from `less` can drop you to the shell via job control; on restricted shells (rescue images) the suspension does nothing and the session appears hung.
- **`:n`/`:p` step the *operand list*, not a directory.** `more *.log` expands the glob at shell time; new files created after the start are invisible, and reading stdin counts as one non-steppable "file".
- **`-s` changes what you read, not just how.** Squeezed blank lines are data loss if whitespace is meaningful (config files, poetry, patch context). Never pipe `more -s` output onward as a copy of the original.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success (all input displayed, normal `q` quit) |
| 1 | Error: operand cannot be opened, terminal setup failure, usage error |

## Related Commands

- [`less`](https://manpages.debian.org/bookworm/less/less.1.en.html) — the modern pager actually used by Debian's `man`; see also `../../reference/man-pages.md`.
- [`overview`](./overview.md) — hub page of the util-linux collection.
- [`dmesg`](./dmesg.md) — kernel ring buffer dump commonly piped through `more` on rescue systems.
- [`column`](./column.md) — frequently combined with pagers to reshape tabular output before display.

## Interview Questions

### Q: What does `more` do when its stdout is not a terminal, and why does that matter for scripts?

It copies input verbatim, like `cat`, and never prompts — paging is a TTY-only behavior. Scripts that call `more` "to be safe" therefore get full output into whatever stdout is, which can flood logs or block if the consumer expects paging. Conversely, the interactive mode reads commands from `/dev/tty`, so `cmd | more` still pages even though stdin carries the data.

### Q: Why would anyone still use `more` instead of `less`?

Availability and standards. `more` is POSIX-standardized and ships in essential `util-linux`, so it exists on rescue images, busybox-based initramfs environments (in reduced form), and minimal containers where `less` is not installed. For scripted or contractual environments that must be portable, `more`'s behavior is defined by POSIX, while `less` is not part of POSIX at all.

### Q: Explain the difference between screen lines and logical lines in `more`.

The pager's unit of progress is the screen line. A source line longer than the terminal width wraps onto several screen lines, so percentages and screenful boundaries shift unpredictably when viewing files with very long lines (kernel logs, JSON). `-f` switches accounting to logical lines, counting a wrapped line once. The same distinction appears in `wc -l` (counts newlines) versus rendered rows — interviewers use it to check whether you understand that terminal pagers and line-based tools measure differently.

### Q: A nightly cron job that "emails the tail of a log" via `more` produced a 2 GB email. What happened?

The job had no controlling terminal, so `more`'s TTY detection failed and it degenerated to `cat`, copying the whole log into the mail transport instead of one screenful. Fixes: use `head`/`tail` explicitly for machine consumers, or send stdout to a pager only when `[[ -t 1 ]]` shows a terminal. The deeper lesson: any tool with interactive-only behavior must be gated on TTY detection in automation.

### Q: What is the role of the `MORE` environment variable, and how does it interact with `PAGER`?

`PAGER` selects which pager a tool spawns; `MORE` configures util-linux `more` itself, and is prepended to that pager's arguments. They compose: `PAGER=more MORE=-s` means every `PAGER`-honoring program launches `more -s ...`. The same pattern exists as `LESS`/`LESSSECURE` for `less`, which is why pager behavior "changes with no command line" — the environment was set in a profile or a wrapper script. Debugging rule: `env | grep -iE 'pager|more|less'` before suspecting the pager binary.

### Q: How does `more` decide how many lines make a screenful?

It queries the terminal size via the `TIOCGWINSZ` ioctl; if that fails it falls back to `LINES`/`TERM`-derived values or a built-in default, and `-n N` overrides everything. One line is reserved for the status prompt. This is why resizing the window mid-session changes paging, and why `more` in an environment without a proper `TERM` misbehaves.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/more.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
