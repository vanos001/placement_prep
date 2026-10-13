# Shells: Exit-Status Mechanics Compared (SH-012)

The [exit-status lifecycle](../exit-status/lifecycle.md) ends at the shell: the shell's
`wait`-equivalent produces `$?`, applies the `128+N` reporting convention, and decides what
"failure" means for automation. POSIX XCU Chapter 2 fixes the baseline (§2.8.2 exit status,
§2.9.2 pipelines, §2.9.3 lists, §2.11 signals/error handling), and each shell extends it
differently. This hub compares the three shells documented in this part —
[bash](./bash.md), [dash](./dash.md), [zsh](./zsh.md) — feature by feature, with version
notes, and links to the POSIX sections each row rests on.

## Portability matrix

| Feature | bash | dash | zsh | POSIX baseline |
|---------|------|------|-----|----------------|
| Pipeline status | Last command (XCU 2.9.2); `set -o pipefail` → rightmost non-zero (manual §3.2.3; disabled by default; version attribution 3.0 unverified — see bash.md) | Last command; **`set -o pipefail` documented in current dash (verified in 0.5.13.4 manual); absent from POSIX and older dash** | Last command; `setopt PIPE_FAIL` (manual, options) | Last command only; `!` negation (2.9.2) |
| Per-element pipeline statuses | `$PIPESTATUS` — uppercase, **0-indexed**, transient (reset by nearly every command; manual §5.2) | **None** — no array facility at all | `$pipestatus` — lowercase, **1-indexed** (0 under `KSH_ARRAYS`), `<Z>`: absent under sh/ksh emulation | None |
| `$?` semantics | "exit status of the most recently executed command" (§3.7.5) | "exit status of the most recent pipeline" (manual) | "exit status returned by the last command" (manual params) | "decimal exit status of the most recent pipeline" (2.5.2) |
| `wait -n` (wait for next job) | Yes (manual §7.2; version attribution 4.3 unverified — see bash.md) | **No** — verified: `Illegal option -n`, exit 2 | **No** — not in the documented builtin; `wait` takes jobspecs/PIDs, no-arg waits for all | Not in POSIX |
| `trap ERR` / failure trap | Yes — `ERR` sigspec, exemptions mirror `errexit` (manual §4.1) | **No** — POSIX sigspecs only (`0`/`EXIT` + signals) | Yes, as `ZERR` (after each non-zero command); `ERR` is an alias | Not in POSIX (extension) |
| `trap DEBUG` / `trap RETURN` | Yes — before every simple command; after functions/`.`-scripts | **No** | Yes — `DEBUG` (before/after per `DEBUG_BEFORE_CMD`), `RETURN` via `TRAPRETURN`/`trap` | Not in POSIX |
| `TRAPxxx` *function* traps | No (builtin only) | No | Yes — `TRAPINT(){}` etc.; own function environment; return-status semantics (zero = handled) | Not in POSIX |
| `EXIT` trap scope | Shell exit only | Shell *normal* exit only ("not via an unhandled signal") | Shell exit **and** function-body exit when set inside a function | `0`/`EXIT` on shell exit (2.11-adjacent) |
| Trap survival in subshells | Trapped (non-ignored) signals reset on subshell creation; ignored-on-entry sticky (non-interactive) | Same (manual: "resets trapped (but not ignored) signals to the default"; ignored-on-entry sticky) | **`ZERR` and `DEBUG` traps are kept** within subshells; other traps reset (manual, builtins) | Traps inherited; behavior of specific sigspecs not fixed (2.11) |
| Async `SIGINT`/`SIGQUIT` ignore (job control off) | Yes — applied to the async subshell itself (verified: `kill -INT` on it is a no-op) | POSIX 2.11 wording; verified: an async *compound* subshell died on `SIGINT` (rc 130) — boundary differs from bash | Yes per manual (Jobs & Signals) — plus the shell always ignores `SIGQUIT` | Commands in an async list inherit `SIG_IGN` for INT/QUIT (2.11) |
| `errexit` (`-e`) family | `set -e`; exemptions list (§4.3.1); **default: `-e` cleared inside command substitution** | `set -e` per POSIX wording; **`-e` inherited into command substitutions (verified)** | `ERR_EXIT`; ignores contexts + **whole function body when called in `&&`/`||`/condition**; extra "complex command" rule; not disabled interactively | 2.8.1 error consequences; `-e` semantics in `set(1posix)` |
| `errexit` into `$( )` knob | `shopt -s inherit_errexit` (on under POSIX mode; version attribution 4.4 unverified — see bash.md) | n/a (always inherits — verified) | No documented equivalent | Not specified |
| Job control in scripts | Monitor off by default; no job notifications; SIGTTIN/SIGTTOU stops unreported | Same | Same; monitor-mode `CHLD` trap fires per completed job (manual) | `set -m` exists; scripts normally run with it off |
| Trapped-signal timing | Deferred until foreground command completes; `wait` returns >128 then trap runs (§3.7.6) | Same (POSIX 2.11 literal) | Same baseline; `TRAPNAL` return status steers continue/interrupt | 2.11, verbatim |

**Version notes and honesty markers.** All "verified" entries above come from the manuals
fetched for this chapter and/or executed reproductions (bash 5.2.37, dash 0.5.13.4 in the
research sandbox; zsh claims are manual-sourced — see each page). Three version attributions
commonly recited could **not** be verified because bash's NEWS/changelog was unreachable
from the sandbox: `pipefail` = bash 3.0, `wait -n` = bash 4.3, `inherit_errexit` = bash 4.4;
the features themselves are verified present in the current manual (bash.md marks each
inline). Similarly, dash's `pipefail` is verified in the 0.5.13.4 manual; the introduction
release is not verified here.

## Reading guide

- **[bash.md](./bash.md)** (SH-001–SH-006) — pipeline/pipefail, `PIPESTATUS`, substitution and
  subshell propagation, the full trap surface, `wait`/`wait -n`/jobs, `set -e`+`ERR`+`inherit_errexit`.
- **[dash.md](./dash.md)** (SH-007–SH-008) — the POSIX-strict baseline: last-command pipelines,
  current-dash pipefail, no status array, `wait -n` absent, POSIX-only traps, async-signal
  boundary differences.
- **[zsh.md](./zsh.md)** (SH-009–SH-011) — `PIPE_FAIL` + lowercase 1-indexed `pipestatus`,
  `TRAPNAL` functions and their return-status semantics, subshell-keeping `ZERR`/`DEBUG`
  traps, `ERR_EXIT`'s documented deviations, `wait` with jobspecs.

## POSIX anchors

- §2.8.2 — 127 / 126 / >128 / "full eight bits of exit status" — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_08_02>
- §2.9.2 — pipeline exit status — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_09_02>
- §2.9.3 — AND-OR lists, async lists — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_09_03>
- §2.11 — signals and error handling (async `SIG_IGN`, trap deferral, `wait` >128) — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html#tag_18_11>

## Related Topics

- [The life of an exit status](../exit-status/lifecycle.md) — the kernel/wait layer all three shells project
- [Conventions and their limits](../exit-status/conventions.md) — what 126/127/128+N can and cannot prove
- [kill(2), raise(3), kill utility](../interfaces/kill-raise.md) — the signal-sending front doors
- [Signal masks](../interfaces/signal-masks.md) — blocking vs ignoring, from the C side
- [Standard signals](../signals/standard-signals.md) — dispositions and `Core` actions
- [Service managers](../service-managers/index.md) and [containers](../containers/index.md) — the consumers of shell-reported statuses
- The book's general shell chapters: [bash](../../shell/bash.md), [zsh](../../shell/zsh.md), [posix-shell](../../shell/posix-shell.md)

## References

- POSIX.1-2017 XCU Chapter 2 (Shell Command Language) — The Open Group — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html>
- Bash Reference Manual (Bash-5.2) — Free Software Foundation / Chet Ramey mirror — <https://www.gnu.org/software/bash/manual/bash.html> (canonical; fetched via <https://tiswww.case.edu/php/chet/bash/bashref.html>)
- dash(1), 0.5.13.4-1 render — Debian Almquist SHell — <https://man.archlinux.org/man/dash.1.en>; upstream: <http://gondor.apana.org.au/~herbert/dash/>
- zsh manual (Parameters, Options, Jobs & Signals, Shell Builtin Commands) — zsh project — <https://zsh.sourceforge.io/Doc/Release/>; documentation sources: <https://github.com/zsh-users/zsh/tree/master/Doc/Zsh>
- bash(1), zshparam(1), zshmisc(1) renders — distribution man pages — <https://man.archlinux.org/man/bash.1.en>, <https://man.archlinux.org/man/zshparam.1.en>, <https://man.archlinux.org/man/zshmisc.1.en>
