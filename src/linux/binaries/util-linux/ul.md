# ul — translate nroff-style underlining for your terminal

## Overview

`ul` reads files (or standard input) containing **overstruck text** — the `_` + backspace convention that `nroff` and other classical formatters use to mean "underline this" — and rewrites it as real underline sequences for the terminal named by `$TERM`, looked up in the terminfo database. On a terminal that cannot underline, the emphasis is silently dropped. It ships in the Debian `bsdextrautils` package (upstream: util-linux, BSD heritage) at `/usr/bin/ul`.

You reach for `ul` in a pipeline after `nroff -man` (or old troff/nroff filters, `catman`-style page renderers) when you want human-readable, properly underlined output on a modern terminal — e.g. rendering an unformatted man page source on a machine without the usual pipeline. It is often confused with its pipeline siblings `col` (fixes vertical/semicursor motion from troff), `colcrt` (renders the same overstrikes for "CRT/line-printer" style output with dashes instead of terminal underline codes), and `colrm` (column removal — no relation beyond naming). `ul` answers a single question: *how do I underline on *this* terminal?*

| Field | Value |
| --- | --- |
| Package | bsdextrautils (Debian bookworm; upstream util-linux) |
| Man section | 1 |
| Path | /usr/bin/ul |
| First appeared | 3BSD (Berkeley, circa 1979) for the zoo of nroff-era terminals |
| Standards | none; BSD lineage, terminfo(5) conventions |

## Synopsis

```
ul [options] [file ...]
```

Main one-line forms:

```
nroff -man foo.1 | ul                 # underline per $TERM
nroff -man foo.1 | ul -t vt100        # force a terminal type
nroff -man foo.1 | ul -i              # dashes on a separate line instead
nroff -man foo.1 | ul -c | colcrt     # colcrt-compatible sequences
ul -t xterm < rendered.txt            # read from a file, write to stdout
```

## How It Works

### The input convention: overstrike

Line printers and early CRTs could not underline, so formatters underlined by **overstriking**: print the character, emit a backspace, print `_`:

```
nroff writes:    w   o   r   BS  _   l   d   BS  _
meaning:         w   o   r   l   d        ("world" underlined)
```

The same trick produced bold (`c` `BS` `c`), which is why `ul` also has to cope with backspaces and tabs while it filters. `ul` walks the stream, tracks which cells of each output position are marked for underlining, and when the marked characters are finally emitted, wraps the marked run in the terminal's "start underline / end underline" sequences.

```
input stream   :  "wor" BS "_" "ld" BS "_"
                          │ tracked as underline cells
output ($TERM):  "wor" <smul> "ld" <rmul>      e.g. ESC [ 4 m ... ESC [ 24 m
```

### Terminfo lookup

The terminal type comes from `$TERM` unless `-t` overrides it. `ul` consults the terminfo database (the `smul`/`rmul` capabilities) for the exact byte sequences of that terminal. If the terminal has no underline capability, the emphasis is simply discarded — output stays readable, which is precisely the historical contract: one formatted stream, many kinds of terminals.

```bash
$ TERM=vt100 nroff -man ./foo.1 | ul | less -R
# underlined headings rendered with vt100 escape codes
```

### Where ul sits in the classic pipeline

Historic document rendering was a chain of single-purpose filters, each fixing one class of device-independence artifacts left by troff/nroff:

```
troff -Tuv source.roff      device-independent escape stream
   │
   ▼
ul        ← horizontal overstrikes  -> terminal underline codes (this page)
   │
   ▼
col       ← reverse/half-line motion, char overlap -> clean char grid
   │
   ▼
less/lpr  consumer (screen or paper)
```

nroff output for terminal targets usually needs only `ul`; troff output aimed at typesetters needs `col` as well. Knowing which artifact each filter owns is the historical-systems interview answer: `ul` owns *underlining*, `col` owns *vertical motion*, `colcrt` owns *underline simulation for underline-less devices*.

### The terminfo capabilities involved

For the chosen terminal, `ul` reads two capabilities from the terminfo database:

```
smul   "start underline mode"   e.g. \E[4m   (ANSI/xterm)
rmul   "end underline mode"     e.g. \E[24m
```

If either capability is absent (the terminal genuinely cannot underline) the markers are dropped. That single lookup is the whole "magic": `ul` is a terminfo-driven state machine, not a formatter. You can pre-flight any terminal type by checking its capabilities with `infocmp <type> | grep -E 'smul|rmul'`.

### Overstrike mechanics, precisely

The input idiom and its pitfalls, worth knowing when cleaning legacy corpora:

```
ch BS _      underline the character 'ch'        (nroff underline)
ch BS ch     bold 'ch'                           (ul passes it through)
BS _         underline the *previous* position   (delayed-move trick)
```

Because a backspace can retroactively mark positions on the current output line, `ul` buffers one line's worth of cells and decides at end-of-line (or when the mark run closes) which stretches get `smul`/`rmul` wrapping. Tabs and carriage returns complicate the mapping, which is why the tool existed as a dedicated filter instead of a `sed` one-liner.

### Dash mode and colcrt mode

When the destination is not a smart terminal (a line printer, a plain file, `colcrt`), terminal escape codes are the wrong currency:

- `-i` (`--indicated`) replaces underline sequences by a **dash placed on a separate line** under the indicated text — the form a printer can reproduce.
- `-c` (`--colcrt`) translates underlining into sequences that `colcrt`-style filters know how to process downstream.

Both exist so `ul` can sit in the classic chain `nroff | ul | col`/`colcrt` depending on whether the consumer is a screen or paper.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-t, --terminal <type>` | Override the terminal type from `$TERM`. |
| `-i, --indicated` | Indicate underlining with dashes on a separate line instead of terminal sequences. |
| `-c, --colcrt` | Emit underlining as `colcrt`-compatible sequences. |
| `-h, -V` | Help / version. |

Notes:

- `-t` accepts any name present in the terminfo database; unknown names make `ul` fail rather than guess.
- With no `-t`, `ul` obeys `$TERM` — inside `cron`/CI that variable may be unset or `dumb`, both of which change the output (see gotchas).

## Usage Patterns

```bash
# Render an unformatted man page source with real underlines
nroff -man ./ping.1.src | ul | less -R
```

```bash
# Force a specific terminal type regardless of your environment
nroff -man ./foo.1 | ul -t xterm | less -R
```

```bash
# Produce printable output: dashes under the underlined words
nroff -man ./foo.1 | ul -i > out.txt
```

```bash
# Feed a colcrt-style postprocessor downstream
nroff -man ./foo.1 | ul -c | colcrt - | lpr
```

```bash
# Inspect the raw overstrike structure of old documents first
cat ./old.doc | cat -v | less        # ^H marks the backspaces ul will translate
```

```bash
# Same pipeline, but keep bold overstrikes too (ul leaves them alone-ish;
# use col to clean remaining motion)
nroff -man ./foo.1 | ul | col -bx | less
```

```bash
# Check what your TERM would do before piping a large document
echo "$TERM"; ul -t "$TERM" </dev/null && echo terminal ok
```

```bash
# Convert an ancient README that uses _word_ overstriking
printf 'wor\b_ld\b_ yes\n' | ul
```

```bash
# Render a directory full of unformatted page sources for review
for p in ./man-src/*.1; do echo "== $p"; nroff -man "$p" | ul -t xterm; done | less -R
```

```bash
# Strip underlines entirely for a plain-text archive copy
nroff -man ./foo.1 | ul -t dumb > foo.txt
```

```bash
# Prove ul is terminfo-driven: same input, two terminals
printf 'x\b_y\b_z\b_\n' | ul -t vt100 | cat -v   # vt100 codes (ESC[4m ...)
printf 'x\b_y\b_z\b_\n' | ul -t dumb | cat -v    # plain letters, no codes
```

```bash
# Keep the audit trail: compare overstrike input with translated output
cat -v ./legacy.doc | head -5; ul -t xterm < ./legacy.doc | cat -v | head -5
```

```bash
# Feed old roff output through the full classic chain
nroff -ms ./report.ms | ul -t xterm | col -bx | less -R
```

## Nuances and Gotchas

- **`$TERM` dependency.** `ul` renders for *one* terminal type; in scripts run from cron/ssh-without-tty, `$TERM` may be `dumb` or unset, and underline capabilities may be missing — output silently loses all emphasis. Pass `-t` explicitly when the consumer is known.
- **It is not a magic formatter.** `ul` only understands the overstrike/backspace idiom. If your input contains troff vertical motion or column output, you still need `col`/`colcrt` — `ul` composes with them rather than replacing them.
- **No-underline terminals drop emphasis silently.** That is by design (it was the whole point in 1979) but is a surprise for people piping `ul` output into JSON-ish processing: the marked text is unchanged, only the markers vanish.
- **Package split confusion.** On modern Debian, `ul` lives in `bsdextrautils` (it was in `bsdmainutils` in older releases), so minimal containers may lack it even though `util-linux` is installed.
- **Portability.** BSD/macOS ship a `ul` with the same flags; util-linux inherited it. BusyBox does not provide it. Do not rely on `-c`/`-i` behavior differences across the two lineages when scripting.
- **Exit status is rarely checked.** In pipelines `ul`'s failure (unknown terminal type, unreadable file) does not stop downstream filters — `set -o pipefail` in bash is your friend.
- **Dumb terminals are the neutral filter.** `ul -t dumb` (or any type without `smul`) is a legitimate way to *remove* overstrike markers from a stream entirely — sometimes exactly what you want before indexing or diffing legacy text.
- **Bold is not ul's job.** Character-backspace-character overstrikes (bold) pass through untranslated; the terminal re-rendering may stack or smear them. For a full overstrike cleanup, `col -b` (delete backspaces, keep last char) or `colcrt` is the companion.
- **Locale-blind by design.** `ul` predates UTF-8; it works on bytes and columns. Multibyte input usually survives because the underlying characters pass untouched, but column-position assumptions in weird legacy files can shift.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Input processed successfully. |
| nonzero | Unreadable file, or unknown terminal type from `-t`/`$TERM`. |

## Related Commands

- [`col`](./col.md) — postprocesses the other troff artifacts (vertical motion, backspaces) after `ul`.
- [`colcrt`](./colcrt.md) — the printer/CRT-oriented sibling that renders overstrikes with dashes.
- [`more`](./more.md) — the classic pager historically chained behind `ul`-style filters.
- [`../../reference/man-pages.md`](../../reference/man-pages.md) — how man pages are formatted and rendered.
- [`./overview.md`](./overview.md) — util-linux collection hub.

## Interview Questions

### Q: What input convention does `ul` exist to translate?

The nroff-era overstrike idiom: an underline is encoded as the character, then a backspace, then `_` (bold as character-backspace-character). `ul` re-encodes those runs using the terminfo underline sequences for the current terminal, or as dashes when asked (`-i`/`-c`).

### Q: Why would a modern person still use `ul`?

Two cases survive: rendering unformatted man page sources (`nroff -man x.1 | ul | less -R`) on systems where the standard renderer chain is missing, and cleaning old document corpora whose only markup is overstriking. It is a small, predictable text filter, which makes it useful in archival pipelines.

### Q: You pipe `nroff -man foo.1 | ul` in a cron job and the output has no underlines at all. Why?

`cron` runs with `$TERM` unset or `dumb`, and `ul` consults terminfo for the terminal's underline capability; with no capability it drops the emphasis by design. Fix by passing an explicit type (`ul -t xterm`) or rendering to dash style (`-i`) when the consumer is a file.

### Q: How do `ul`, `col` and `colcrt` divide the work in a troff pipeline?

`ul` converts horizontal overstriking into terminal underline codes (or dashes); `col` resolves reverse linefeeds/half-line motion and overlapping character output into a plain character grid; `colcrt` simulates underlining for devices that cannot underline at all. They are composable filters, each owning one artifact class of the formatter's output.

### Q: What happens on a terminal that genuinely cannot underline?

`ul` ignores the underlining and emits the plain characters — output remains fully readable, just not emphasized. This graceful degradation was the tool's original raison d'être: one nroff stream serving dozens of incompatible terminals and printers.

### Q: Why is `ul` a separate program instead of a feature of `col` or the pager?

Unix pipeline philosophy: each filter owns one transformation so they compose for any consumer. `ul` needs terminfo lookups and line-cell buffering that `col`'s character-grid model does not; keeping them separate lets you underline for a terminal without `col`'s vertical-motion cleanup (nroff case), or clean motion without any underline (plain troff dumps). The same modularity is why `colcrt` exists for underline-less hardcopy — three tools, three artifacts, any order the problem requires.

### Q: What would you reach for today to view a legacy overstruck document?

The same `ul` in a pipeline (it still ships), or `col -b`/`colcrt` when the target is plain text. If the corpus is large and one-off, converting once (`nroff input | ul -t dumb > clean.txt`) and keeping the clean copy beats re-translating on every read; keep the original as the archival artifact since the overstrike form is the most faithful representation of the source.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdextrautils/ul.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
