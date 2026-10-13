# scriptlive — re-run a recorded typescript's commands in a fresh shell

## Overview

`scriptlive` executes a recorded terminal session again — not as a video, but as *commands*. It takes the timing file and the stdin log that `script(1)` produced with `--log-timing` plus `--log-in`/`--log-io`, and feeds the recorded input into a newly created pseudoterminal running your `$SHELL`, paced by the recorded rhythm. It ships in the `bsdutils` package at `/usr/bin/scriptlive` (upstream util-linux; a modern addition to the script family, 2017-era).

The critical distinction: `scriptreplay(1)` re-**displays** the output stream and runs nothing; `scriptlive` re-**executes** the input stream and displays little. That makes it the tool for re-running recorded interactive workflows — environment setup sequences, REPL demos, guided installations — and also makes it the most dangerous member of the family, because a typescript is arbitrary code. It is often confused with `scriptreplay` (the display-only sibling) and with `bash` replaying history (`history` re-runs shell lines without timing or pty semantics; `scriptlive` re-drives *keystrokes*, including what a full-screen app would have received).

| Field | Value |
| --- | --- |
| Package | bsdutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/scriptlive |
| First appeared | util-linux script-family addition (2017 era) |
| Standards | — (util-linux specific) |

## Synopsis

```
scriptlive [options] <timingfile> <typescript>
```

The positional `typescript` is the *input* log. The same files can be passed with options:

```
scriptlive -t session.time -I session.in     # options form (recommended in scripts)
scriptlive -T session.time -B session.io     # input+output merged recording
scriptlive -t session.time -I session.in -d 5 -m 2   # faster, capped pauses
```

## How It Works

### What it needs from the recording

A `scriptlive`-able recording is a pair of files:

```
script -T session.time --log-in session.in      (record: timing + input)
          │
          ▼
scriptlive -t session.time -I session.in        (replay: execute the input)
```

The timing file must contain `I` entries (input bursts) — which only exist if `script` was recording input. A session recorded without `--log-in`/`--log-io` has nothing for `scriptlive` to feed; that failure is discovered at replay time, so check the timing file for `I` lines first. The input log contains what was typed, including non-echoed secrets (password prompts) — the same security caveat as the recording side.

Verified end-to-end with a recorded three-line session (`echo replayed-marker`, `echo second-line`, `exit`), the replay looked like:

```
>>> scriptlive: Starting your typescript execution by /bin/bash.
z@host:/tmp/sctest$ replayed-marker
z@host:/tmp/sctest$ second-line
z@host:/tmp/sctest$ exit

>>> scriptlive: done.
```

The `>>>` lines are scriptlive's own; between them, a fresh `/bin/bash` (from `$SHELL`) received the recorded keystrokes on its pty. With `-E never` the typed commands themselves are not echoed into the replay — you see their *effects*.

### A complete worked example (all artifacts real)

Recording — note the input stream produces `I` timing entries:

```
$ script -q -T t4.log -I in4.log -O o4.log -c 'bash --noprofile --norc' < input.txt
$ head -9 t4.log
H 0.000000 START_TIME 2026-10-09 16:41:16+00:00
H 0.000000 SHELL /bin/bash
H 0.000000 COMMAND bash --noprofile --norc
H 0.000000 TIMING_LOG t4.log
H 0.000000 OUTPUT_LOG o4.log
H 0.000000 INPUT_LOG in4.log
I 0.000053 43          ← the typed bytes: scriptlive's payload
O 0.260220 158         ← the display: scriptreplay's payload
```

The input log carries the session header/footer around the typed lines (`Script started on …` / `Script done …`) — that is normal; scriptlive consumes the file through the timing indices, so the banner bytes are skipped, but if you `cat` such a log into a shell by hand those header lines would execute as garbage.

Replay (captured output):

```
$ scriptlive -t t4.log -I in4.log -E never
>>> scriptlive: Starting your typescript execution by /bin/bash.
z@host:/tmp/sctest$ replayed-marker
z@host:/tmp/sctest$ second-line
z@host:/tmp/sctest$ exit

>>> scriptlive: done.
```

### Execution environment: a new pty, today's machine

The commands run in a **newly created pseudoterminal** with the user's shell — not in the recorded machine, directory, or data state. The replay is a *re-execution*, so every command acts on whatever exists *now*: files have changed, environments differ, and destructive commands are just as destructive as when typed. This is the whole point and the whole risk.

The man page's warning is explicit and worth internalizing: the typescript may contain arbitrary commands, and the recommended pre-flight is to inspect it with the display-only sibling first:

```bash
scriptreplay --stream in --log-in session.in    # or --log-io; shows ONLY the input stream
```

### Pacing: divisor and maxdelay

Input is delivered with the recorded inter-burst delays. `-d/--divisor NUM` divides all delays (2 = twice as fast, 0.1 = ten times slower); `-m/--maxdelay NUM` caps any single gap at NUM seconds — the pragmatic fix for recordings where you went to lunch mid-session. Unlike `scriptreplay`, there are no interactive speed keys; pacing is fixed at startup.

### Echo control

`-E auto|always|never` controls the ECHO flag of the replay pty. The default is `auto` (echo enabled), and the man page notes this default may change — scripts that need stable behavior should pass `-E` explicitly. The choice affects what you *see* during the replay, not what gets executed.

### What the replayed shell inherits

The fresh pty gets the *current* process environment: scriptlive's working directory, its environment variables, and `$SHELL` (or `-c CMD`) decide the interpreter — **not** anything recorded. If the recorded session assumed a specific checkout directory or environment, `cd` into it and export the needed variables before launching scriptlive, because the replay starts exactly where you invoke it. Within the replay session, recorded `cd`/`export` commands do take effect for subsequent commands — the state accumulates inside that one shell, exactly as a live session would.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-t, --timing FILE` | timing file (positional alternative: first operand) |
| `-T, --log-timing FILE` | alias of `-t`, mirrors script's option spelling |
| `-I, --log-in FILE` | stdin log from `script --log-in` (the commands to re-run) |
| `-B, --log-io FILE` | merged in+out log from `script --log-io` |
| `-c, --command CMD` | run CMD instead of an interactive shell in the replay pty |
| `-E, --echo WHEN` | replay-pty echo: auto / always / never |
| `-d, --divisor NUM` | divide recorded delays (float; >1 faster, <1 slower) |
| `-m, --maxdelay NUM` | cap any single delay at NUM seconds |

There is no `--summary`, no stream selection, and no output-file options: scriptlive produces a live session, not a file.

## Usage Patterns

```bash
# Record a workflow you intend to replay (timing + input, output optional)
script -T setup.time --log-in setup.in --log-out setup.out
```

```bash
# MANDATORY pre-flight: view the input stream before executing it
scriptreplay --stream in --log-in setup.in
```

```bash
# Re-run the recorded setup, five times faster, pauses capped at 2 s
scriptlive -t setup.time -I setup.in -d 5 -m 2
```

```bash
# Replay into a specific shell instead of $SHELL
scriptlive -t setup.time -I setup.in -c /bin/bash --noprofile --norc 2>/dev/null || \
scriptlive -t setup.time -I setup.in
```

```bash
# Check the recording is scriptlive-compatible before running it
rg '^I ' setup.time | head -3    # I entries must exist
```

```bash
# Demo a REPL-based workflow (psql, python, redis-cli) at natural speed
scriptlive -t repl.time -I repl.in
```

```bash
# Slow a too-fast recording down for a live demo (0.5 = half speed)
scriptlive -t demo.time -I demo.in -d 0.5
```

```bash
# Set the stage explicitly: the replay inherits THIS cwd and environment
cd /srv/app && source .venv/bin/activate && \
  scriptlive -t setup.time -I setup.in
```

```bash
# Compatibility probe: same bytes, different shell — see what breaks
scriptlive -t setup.time -I setup.in -c 'sh'   # then with bash for comparison
```

```bash
# Keep the replay non-chatty: no echoing of the injected keystrokes
scriptlive -t setup.time -I setup.in -E never
```

```bash
# Compatibility check: does the timing file carry input entries at all?
head -20 setup.time | grep '^I ' || echo "no input recorded — scriptlive has nothing to run"
```

```bash
# Replay a risky recording inside a throwaway container instead of your host
docker run --rm -it -v "$PWD":/rec debian bash -c \
  'scriptlive -t /rec/setup.time -I /rec/setup.in'
```

## Nuances and Gotchas

- **It executes whatever the log contains — as *you*, now.** A typescript that once ran `rm -rf /tmp/old` will run it again, today, against whatever is currently there. Verify with `scriptreplay --stream in` before every scriptlive run; never scriptlive recordings from untrusted sources (a malicious "demo log" is a shell prompt you didn't notice).
- **No input log, no replay.** Recordings made without `--log-in`/`--log-io` carry only `O`-stream timing; scriptlive has nothing to feed. The recording and replay flags must match (`-I` ↔ `--log-in`, `-B` ↔ `--log-io`).
- **State drift is silent.** The recorded session ran against yesterday's checkout; the replay runs against today's. Commands succeed/fail differently without any error — treat scriptlive as a workflow accelerator, not a reproducibility guarantee. For reproducibility, wrap the steps in a real script and version it.
- **Secrets in the input log.** Passwords typed at non-echoing prompts are in the stdin log in plaintext (the same warning as `script --log-in`). scriptlive doesn't create this problem; it re-raises it every replay.
- **Timing is real time.** Without `-d`/`-m` a recording that idled ten minutes replays for ten minutes. Always pair `-m` with any human-recorded session.
- **`-E never` changes what you see, not what runs.** With echo disabled you watch effects only; output still appears (it comes from the programs), but the injected keystrokes don't. Debugging a misbehaving replay is easier with `-E always`.
- **Interactive full-screen apps re-drive.** If the recording contains a `vim` or `htop` session, the recorded keystrokes drive those programs again — impressive in demos, confusing if the terminal size differs (redraws misalign). Replay in a similarly sized terminal.
- **No interactive speed control.** Unlike `scriptreplay` (Space/Up/Down), pacing is fixed by `-d`/`-m` at start; to adjust mid-run, stop it (Ctrl-C — which also kills the replayed shell) and restart with new values.
- **Interrupting is not resumable.** Ctrl-C aborts the injected stream; re-running starts the recording from the beginning. Long replays should be split at the recording layer (several short script sessions) rather than fast-forwarded.
- **`-c` changes the target shell, not the safety model.** `scriptlive -c busybox sh` executes the same recorded bytes under a different interpreter; syntax differences can turn a benign-looking log into errors — or, worse, into different commands than you reviewed. Review in the same shell you will replay with.
- **Environment inheritance is silent.** A replay launched from a different directory or with different `PATH` runs the *same bytes* against different surroundings — recorded `./script.sh` may resolve to something else entirely. Anchor cwd/venv/env before starting, and prefer absolute paths in sessions you intend to replay.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Replay finished (the replayed shell exited) |
| >0 | Setup error: missing/unreadable timing or input log, bad option |

Note that failures *inside* replayed commands do not fail scriptlive — it faithfully types them into the shell and moves on, exactly like a human would.

## Related Commands

- [`./script.md`](./script.md) — the recorder; `--log-timing` + `--log-in` output is scriptlive's required input.
- [`./scriptreplay.md`](./scriptreplay.md) — the display-only sibling; use `--stream in` as scriptlive's safety check.
- [`./overview.md`](./overview.md) — the bsdutils collection hub and packaging rationale.
- [`../../admin/systemd.md`](../../admin/systemd.md) — when "re-run recorded steps" should really be a systemd unit instead.

## Interview Questions

### Q: What is the difference between scriptreplay and scriptlive?

`scriptreplay` re-displays: it reads the output log and the timing file and repaints the recorded session at the recorded rhythm; no commands run, so it is safe on untrusted material. `scriptlive` re-executes: it reads the timing file and the *input* log and feeds those keystrokes into a fresh pty running your shell, so everything recorded actually happens again — against today's filesystem and data. Different input files (output log vs input log), different risk classes, complementary uses (safe review vs real re-run).

### Q: What must a recording contain for scriptlive to work, and how do you check?

The timing file must include `I` (input) entries and you must supply the input log that `script --log-in` (or `--log-io`) wrote. A recording made without input logging has no commands to replay. Check with `rg '^I ' session.time` on an advanced-format timing file, and always review the input itself first via `scriptreplay --stream in --log-in session.in` — the man page recommends exactly this before executing.

### Q: Why is scriptlive considered dangerous, and what workflow makes it acceptable?

Because its input is a shell session: executing a typescript is executing arbitrary code with your privileges, against the current machine state rather than the recorded one. Acceptable use means: recordings only from trusted sources, a mandatory `scriptreplay --stream in` review step, no secrets typed during recording (they land in plaintext in the input log), and replays run in scoped environments (containers, scratch accounts) when the recording is at all uncertain.

### Q: A recorded setup session includes a ten-minute thinking pause and typed passwords. How do you make it replayable?

Fix both at the recording layer ideally: re-record without typing secrets (do authentication steps outside the recorded flow). For the existing recording, cap the pause with `-m` (e.g. `-m 2` limits any gap to two seconds) and optionally speed everything with `-d 5`; the password bytes will still be in the input log, so restrict the file and treat it as a credential, or trim the sensitive range out of the log before replaying.

### Q: How does `-E never` change a replay, and when would you want it?

It disables ECHO on the replay pseudoterminal, so the injected keystrokes are not echoed — you see prompts and program output but not the commands being "typed". That produces cleaner output for demos and logs; the downside is harder debugging of the replay itself. `-E always` echoes every keystroke, which is what you want when verifying that the right bytes arrive at the right moments.

### Q: When is scriptlive the right tool versus just writing a shell script?

When the value is in the *interactive choreography* — REPL sessions, TUI-driven tools, commands that need a real pty and human-paced confirmations — and re-driving it faithfully is cheaper than reverse-engineering a script. If the steps are non-interactive, a versioned script with proper error handling beats a timing-driven replay in every dimension: no drift, no secrets, no pty dependence.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdutils/scriptlive.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
