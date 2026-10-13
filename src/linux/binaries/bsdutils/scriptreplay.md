# scriptreplay — play back a typescript with its original timing

## Overview

`scriptreplay` replays a terminal session recorded by `script(1)`: it reads the timing file, waits out the recorded gaps, and pushes the recorded output to your terminal so the session unfolds exactly as it did live — same colors, same progress bars, same rhythm. Crucially, it **does not run any commands**; the man page states it plainly: the programs that were run when the typescript was recorded are not run again. That makes it the safe member of the script family — suitable for demos, documentation, and reviewing sessions from untrusted sources. It ships in the `bsdutils` package at `/usr/bin/scriptreplay` (upstream util-linux; lineage traces to Joey Hess's late-1990s Perl `scriptreplay`, modernized in C as the script family gained multi-stream logging).

It is often confused with `scriptlive(1)` — which re-*executes* the recorded *input* in a fresh shell and is the dangerous sibling — and with screen recorders: `scriptreplay` renders plain terminal data, so its fidelity depends on your terminal being type-compatible with the recording one.

| Field | Value |
| --- | --- |
| Package | bsdutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/scriptreplay |
| First appeared | Perl original (late 1990s); C util-linux implementation |
| Standards | — (util-linux specific) |

## Synopsis

```
scriptreplay [options] <timingfile> [<typescript> [<divisor>]]
```

Common one-line forms:

```
scriptreplay timing.tm typescript          # positional form (divisor third)
scriptreplay -t timing.tm -O out.log       # options form; matches script's logs
scriptreplay -t t.tm -O out.log -d 4       # 4x faster replay
scriptreplay -t t.tm -O out.log -m 1       # cap any pause at one second
scriptreplay --summary -t t.tm             # session metadata (advanced format only)
```

## How It Works

### Inputs and pacing

Two files drive the replay: the timing log (from `script -T`) and the content log (default name `typescript`, else `-O/--log-out`, `-I/--log-in`, or `-B/--log-io`). Each timing entry says "wait N seconds, then emit M bytes of stream S"; the replay loop is exactly that — sleep, emit, repeat:

```
script -T t.tm -O out.log   ──►   t.tm (timeline)  +  out.log (content)
                                            │                 │
                                            ▼                 ▼
                                   scriptreplay: for each entry
                                   sleep(elapsed / divisor) → write M bytes
```

Timing formats mirror `script`'s. The classic format is two fields per line, elapsed seconds and byte count (verified recording):

```
0.010113 10
0.391612 10
0.302062 4
```

The advanced multi-stream format (produced when input+output were logged) carries per-entry stream types and header metadata, which is what enables `--summary` and `-x/--stream` filtering:

```
H 0.000000 START_TIME 2026-10-09 16:40:39+00:00
H 0.000000 COMMAND printf "abc\n"; sleep 0.2; printf "def\n"
O 0.010117 5
O 0.191611 5
H 0.000000 DURATION 0.212092
H 0.000000 EXIT_CODE 0
```

### Speed control: divisor, maxdelay, and live keys

`-d/--divisor NUM` divides every recorded delay: 2 replays twice as fast, 0.1 ten times slower (the name is literal — timings are divided by it). It overrides the old positional third argument. `-m/--maxdelay NUM` clamps single gaps — the standard companion for human-recorded sessions with idle stretches. During playback you can steer interactively:

| Key | Effect |
| --- | --- |
| Space | toggle pause/resume |
| Up arrow | +10% playback speed |
| Down arrow | −10% playback speed |

These need a terminal on stdin; in CI they simply never fire.

### Stream selection and CR handling

For multi-stream (`--log-io`) recordings, `-x/--stream in|out|signal|info` restricts replay to one stream — most importantly `in`, the *typed* stream, which is the sanctioned way to inspect what `scriptlive` would execute before executing it. `-c/--cr-mode auto|never|always` handles carriage returns from logs: in `auto` (default), CRs in the *stdin* log are replaced with line breaks so a displayed input stream doesn't overwrite one line repeatedly.

### --summary

With an advanced-format timing file, `--summary` prints an overview of the recorded session (start time, command, duration, exit code — the `H` metadata) and exits, without any playback. Classic-format files don't qualify; re-record with input logging or `-m advanced` if you need it.

### Under the hood: a sleep-and-emit loop

The implementation is deliberately trivial: parse the timing file, then for each entry sleep the recorded (divided) delay and write the recorded byte count from the content file. No terminal state is saved or restored — the replay leaves your terminal exactly as the recorded bytes left it, which is why a misrendered session can leave colors or cursor modes behind and the standard remedy afterwards is `reset` (or `printf '\033[0m'` for colors only). The timing file itself is plain, diffable text with microsecond float precision — you can read it, filter it, even hand-edit gaps (scaled consistently, the replay follows).

### Fidelity limits

Replay is pure redisplay: escape sequences in the typescript are reinterpreted by *your* terminal. The man page warns the replay is only guaranteed on the same type of terminal it was recorded on — different sizes, terminal models, or emulators render cursor-addressing sequences differently, which is why screen-manipulating sessions (`vim`, `htop`) can look scrambled on replay even though the bytes are identical.

### A complete worked example (all artifacts real)

Record a three-step session and inspect both files before replaying:

```
$ script -q -T t2.log -O o2.log \
    -c 'printf "step-one\n"; sleep 0.4; printf "step-two\n"; sleep 0.3; printf "done\n"'
$ cat o2.log
Script started on 2026-10-09 16:59:07+00:00 [COMMAND="..." <not executed on terminal>]
step-one
step-two
done

Script done on 2026-10-09 16:59:08+00:00 [COMMAND_EXIT_CODE="0"]
$ cat t2.log
0.010095 10        ← "step-one\r\n" (pty adds the CR) 10 ms after start
0.391486 10        ← "step-two\r\n", 0.39 s later (the sleep 0.4)
0.301383 6         ← "done\r\n"
$ scriptreplay -t t2.log -O o2.log && echo "replay exit=$?"   # → replay exit=0
```

Note the byte counts count *pty* bytes: every line carries a `` the program never printed, and the replay reproduces even those. With an input+output recording the timing file gains `I`/`H` entries (see the [`script`](./script.md) page) and the same replay command works unchanged — scriptreplay simply ignores the `I` stream unless `-x in` selects it.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-t, --timing FILE` | timing file (replaces the positional timing argument) |
| `-T, --log-timing FILE` | alias of `-t`, mirrors script's spelling |
| `-O, --log-out FILE` | output/content log (default name: `typescript`) |
| `-I, --log-in FILE` | input log — for `-x in` inspection of typed material |
| `-B, --log-io FILE` | merged in+out log |
| `-s, --typescript FILE` | deprecated alias of `--log-out` |
| `-d, --divisor NUM` | divide all delays (float; >1 faster, <1 slower) |
| `-m, --maxdelay NUM` | cap any single delay at NUM seconds |
| `-x, --stream TYPE` | replay only `in`, `out`, `signal`, or `info` |
| `-c, --cr-mode MODE` | CR handling: auto / never / always |
| `--summary` | print session metadata (advanced format) and exit |

## Usage Patterns

```bash
# Record once, replay anywhere (the canonical pair)
script -T time.tm -O session.log
scriptreplay -t time.tm -O session.log
```

```bash
# Demo for a talk: 5x speed, no 30 s dead air
scriptreplay -t demo.time -O demo.log -d 5 -m 2
```

```bash
# CI artifact check: summarize what a job's recording contains
scriptreplay --summary -t build.time
```

```bash
# Safety review before scriptlive: show only what was typed
scriptreplay --stream in --log-in session.in
```

```bash
# Slow-motion teaching replay of a tricky procedure
scriptreplay -t t.tm -O o.log -d 0.5
```

```bash
# Watch only the output of a merged in/out recording
scriptreplay -t t.tm -B io.log -x out
```

```bash
# Old-style positional syntax still accepted (timing, typescript, divisor)
scriptreplay time.tm session.log 4
```

```bash
# Missing files fail loudly (verified)
scriptreplay -t missing.tm
# scriptreplay: cannot open missing.tm: No such file or directory   (exit 1)
```

```bash
# Review only the output of a merged in/out recording, ignoring typed noise
scriptreplay -t t.tm -B io.log -x out
```

```bash
# Steering playback live during a demo: Space pauses, Up/Down shift speed ±10%
scriptreplay -t demo.time -O demo.log       # run it in a real terminal to steer
```

```bash
# Turn a recorded session into reviewable text instead of a performance
col -bp < demo.log > demo.txt    # then read the cleaned typescript at your leisure
```

```bash
# Extract the typed commands of a merged recording as plain text
scriptreplay -x in --log-in session.in > typed-lines.txt   # what scriptlive would run
```

```bash
# After a misrendered replay, normalize the terminal again
scriptreplay -t t.tm -O o.log ; reset    # clear leftover colors/cursor modes
```

## Nuances and Gotchas

- **Display-only, by design and by contract.** Nothing is executed; you can replay material from an untrusted host without fear — the exact opposite of `scriptlive`. Don't "verify" a suspicious log by scriptlive-ing it after a scriptreplay glance; redisplay shows you bytes, not intent.
- **`-d` divides, not multiplies.** `-d 10` is ten *times faster*; newcomers expecting a speed multiplier set 0.1 and wonder why the demo crawls. The interactive Up/Down keys nudge the same factor by ±10%.
- **`--summary` needs the advanced format.** On a classic timing file it has nothing to read; re-record with input logging (`-I`/`-B`) or force `-m advanced` when recording.
- **`-x` only means something with multi-stream logs.** Selecting `--stream in` on a classic (output-only) recording yields nothing; the stream concept exists only where input was recorded.
- **Terminal mismatch garbles fancy sessions.** Same terminal type is a stated precondition; resize your window or change emulators and cursor-addressing replay misrenders. For durable documentation, prefer `col -b`-cleaned typescripts over replay-dependent artifacts.
- **Timing file and content file must belong together.** Mixing logs from different recordings plays plausible nonsense; pairing errors are silent because there is no checksum linking the two files.
- **Old-style syntax order matters.** Positional form is `timingfile typescript [divisor]`; `-t` replaces the *first* positional only. Mixing `-t file` with a positional typescript works, but readable scripts use the full options form.
- **Pause keys need a tty.** In non-interactive contexts the Space/Up/Down controls are inert; pacing must come from `-d`/`-m`.
- **`--cr-mode` only rescues the input stream.** The `auto` CR→newline substitution applies to the stdin log; output replays keep their raw CRs, which is correct — the terminal's cursor behavior is part of the show. Forcing `always` on an output stream breaks full-screen sessions that rely on CR rewrites.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Replay completed (or `--summary` printed) |
| 1 | Missing/unreadable timing or content file (verified message: `scriptreplay: cannot open missing.tm: No such file or directory`) |

Failures *inside* the recorded session don't affect scriptreplay's status — the recording is just data.

## Related Commands

- [`./script.md`](./script.md) — produces the timing and content logs this tool consumes.
- [`./scriptlive.md`](./scriptlive.md) — the execute-rather-than-display sibling; `scriptreplay --stream in` is its pre-flight check.
- [`./overview.md`](./overview.md) — the bsdutils collection hub and packaging rationale.

## Interview Questions

### Q: Why is scriptreplay safe on untrusted recordings while scriptlive is not?

Because scriptreplay only writes recorded bytes to your terminal — it is a redisplay loop over the timing file, executing nothing. scriptlive feeds the recorded *input* into a live shell, executing everything. The practical rule: review any recording with `scriptreplay --stream in --log-in ...` before ever letting `scriptlive` touch it; the same pair of files serves both tools.

### Q: How does the divisor work, and what's the difference from maxdelay?

The divisor divides every recorded delay, so `-d 4` finishes in a quarter of the original wall time and `-d 0.5` stretches the session to double length. `maxdelay` doesn't scale anything — it caps individual gaps, e.g. `-m 2` turns a three-minute idle into a two-second pause while leaving fast sequences untouched. Demos typically combine both: `-d 5 -m 2`.

### Q: What can you learn from `scriptreplay --summary`, and what does it require?

It reads the header metadata of an advanced-format timing file — start time, shell, recorded command, duration, exit code — and prints it without playback. It requires the multi-stream format, which `script` produces when input and output logging are combined (or `-m advanced` is forced). Classic-format timing files carry no metadata, so `--summary` has nothing to show for them.

### Q: A replayed vim session looks scrambled although the typescript "should" replay fine. Why?

Replay reinterprets the recorded escape sequences in *your* terminal. The man page's precondition — same type of terminal as the recording — is violated by a different size, terminal type, or emulator, and cursor-addressing sequences land wrong. The bytes are faithful; the rendering isn't. Screen-manipulating sessions replay reliably only on matching terminals; otherwise stick to cleaned typescripts or re-record.

### Q: What does scriptreplay guarantee about fidelity, and what doesn't it guarantee?

It guarantees the recorded bytes reach a terminal at the recorded relative times (scaled by divisor/maxdelay). It does not guarantee the *rendering* matches (terminal-type dependence), that the session's side effects exist (nothing ran), or that stream separation survives classic-format recordings (single stream only). Saying exactly this — "faithful bytes, faithful rhythm, no execution, conditional rendering" — is the complete answer.

### Q: Why does the timing file record byte counts rather than lines?

Because terminal output is not line-oriented: progress bars repaint in place with CRs, escape sequences arrive in bursts, and a single logical "update" may span many partial writes. Recording elapsed-time-plus-byte-count pairs lets the replay reproduce the stream at write granularity — the unit the original programs actually emitted — which is what makes in-place updates, spinners, and colors reappear correctly. Line-based timing would flatten exactly the behavior that makes replays look alive.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdutils/scriptreplay.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
