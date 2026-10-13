# Exit-Status Conventions and Their Limits (EX-010 — EX-012)

An exit status is one unsigned byte delivered by the mechanisms of
[lifecycle.md](./lifecycle.md). Everything *above* that byte — "127 means not found", "137
means OOM-killed" — is a convention adopted by some community of software, enforced by
nothing. This page catalogues the common conventions, classifies the strength of each
guarantee, and collects the additional evidence needed before an integer may be treated as a
root cause.

## EX-010 — The common status table, classified

**Guarantee classes used below:** *POSIX guarantee* = required by POSIX.1-2017 XCU 2.8.2
("If a command is not found, the exit status shall be 127. If the command name is found, but
it is not an executable utility, the exit status shall be 126"); *shell convention* =
documented in shell manuals but not standardized; *tool-specific* = one program's documented
contract; *kernel artifact* = a property of the 16-bit wait status escaping through the
shell layer.

| Status | Conventional meaning | Guarantee class | Additional evidence required before treating as root cause |
|--------|----------------------|-----------------|-------------------------------------------------------------|
| `0` | Success | POSIX (zero = success across XCU 2.8.2 and every shell manual) | None — but see EX-011: `exit(256)` also yields 0. |
| `1` | "Generic" failure; catch-all | Convention (POSIX fixes only `EXIT_FAILURE` ≥ non-zero in C, not a specific value) | Read the program's own stderr/diagnostics; almost any code chooses 1. |
| `2` | Shell **builtin misuse** ("All builtins return an exit status of 2 to indicate incorrect usage" — bash manual §Exit Status); also "serious trouble" for grep/diff/ls (tool-specific) | Shell convention + tool-specific | Check whether a *builtin* misfired (bash) vs the tool's own manual row. |
| `126` | Command found but **not executable** | POSIX guarantee (2.8.2) | Inspect permissions/ACL/mount noexec bit; check for wrapper scripts; `ls -l` + `file` on the resolved path. |
| `127` | Command **not found** | POSIX guarantee (2.8.2) | PATH/wrapper analysis: `command -v`, `type -a`, shell hash (`hash -r`), PATH differences between environments. |
| `128+N` | Shell reports death-by-signal-N as `128+N` (bash manual: "When a command terminates on a fatal signal whose number is N, Bash uses the value 128+N"; POSIX 2.8.2 only requires ">128") | Shell convention on a kernel artifact | Determine *who sent signal N* and why (EX-011); the shell cannot tell a signal death from a program that chose that code. |
| `130` | `128+2` — died by **SIGINT** (typically Ctrl-C at a terminal) | Shell convention (instance of 128+N) | Was it a human, a timeout implementation, or a sibling process? Check `stty`/tty association, CI runner logs. |
| `137` | `128+9` — died by **SIGKILL** (frequently the OOM killer or a runtime's kill-after-timeout) | Shell convention (instance of 128+N) | OOM/runtimes: `dmesg`/`journalctl -k` for oom-kill lines, cgroup `memory.events` (`oom_kill`), container runtime metadata (`OOMKilled` flag), process-manager timeout policy. SIGKILL leaves no handler-side trace by design. |
| `139` | `128+11` — died by **SIGSEGV** | Shell convention (instance of 128+N) | Core dump (if produced — see lifecycle EX-006), `coredumpctl`, `dmesg` segfault lines with the faulting IP/library; then map to the binary's build ID. |
| `141` | `128+13` — died by **SIGPIPE** (classic: `yes | head`) | Shell convention (instance of 128+N) | Usually benign pipeline closure; in daemons, look for missing `SIG_IGN` on SIGPIPE + `EPIPE` handling. |
| `143` | `128+15` — died by **SIGTERM** (typically a supervisor stopping the service) | Shell convention (instance of 128+N) | Which manager sent TERM and on what timeout (systemd `TimeoutStopSec=`, orchestrator grace periods — see [service-managers](../service-managers/index.md), [containers](../containers/index.md)). |
| `124` | `timeout(1)` "command timed out" — "if COMMAND times out, and `--preserve-status` is not specified" (timeout(1) Exit status section, verified; the same page reserves 125 for `timeout` itself failing and passes 126/127 through) | Tool-specific (GNU coreutils `timeout`) | Distinguish from 128+N deaths the tool may deliver itself; check the tool's manual row. |

The `>128` rows deserve the standing caveat: the range is reserved by POSIX 2.8.2's RATIONALE
("A command was interrupted by a signal") *for reporting*, but nothing prevents a program
from `exit(137)` of its own free will — verified: `dash -c 'exit 137'` reports 137 exactly
like a SIGKILL death. The 16-bit wait status does distinguish the two (signal in bits 0–6
vs code in bits 8–15, per [lifecycle EX-004](./lifecycle.md#ex-004--the-exact-16-bit-wait-status-layout-linux));
the shell-visible 8-bit integer does not.

### Tool-specific codes: verified rows

- **GNU grep** (grep(1), EXIT STATUS): "Normally the exit status is 0 if a line is selected,
  1 if no lines were selected, and 2 if an error occurred. However, if the `-q` or `--quiet`
  or `--silent` is used and a line is selected, the exit status is 0 even if an error
  occurred." That last clause — quiet mode *masks* errors — is a miniature of this whole page.
- **GNU diff** (diff(1)): "Exit status is 0 if inputs are the same, 1 if different, 2 if
  trouble." Note 1 is a *successful* answer ("they differ"), not a failure — scripts that
  treat any non-zero as failure break on diff-based checks.
- **GNU ls** (coreutils manual, "ls invocation"): `0` success; `1` minor problems (e.g.,
  failure to access a file not named on the command line); `2` serious trouble (invalid
  option, failure to access a command-line argument, directory loop). Verified against the
  official `coreutils.texi` source.
- **curl** (curl(1) "EXIT CODES" section): a documented numeric range — sample rows verified
  from the man page: `0` success; `1` unsupported protocol; `2` failed to initialize;
  `3` URL malformed; `6` could not resolve host; `7` failed to connect; `22` HTTP ≥400
  *only with `--fail`*; `26` read error; `28` operation timed out; `47` too many redirects;
  `60` peer certificate cannot be authenticated; `63` maximum file size exceeded. curl's
  codes are dense and version-documented — always grep the man page of the installed
  version rather than relying on folklore. (The everything.curl.dev "Exit codes" chapter
  moved; the canonical list lives in `man curl`.)

## EX-011 — Why one integer cannot establish cause

Four independent mechanisms make the exit status *suggestive but never conclusive*:

1. **Codes are chosen by programmers, not assigned by the system.** Nothing validates that
   `1` means the same thing across two tools, or even across two versions of one tool.
   A tool's manual is the only source for its own codes (grep/diff/ls/curl rows above).
2. **`128+N` is a reporting convention, not an execution mark.** A process that decides to
   `exit(137)` — or `exit(143)`, or `exit(130)` — produces the same shell-visible integer as
   a SIGKILL/SIGTERM/SIGINT death. The wait status kernel-side keeps the distinction
   ([lifecycle EX-004](./lifecycle.md)); the shell layer, and therefore your CI log, does not.
3. **Runtimes and wrappers transform statuses.** Verified examples:
   - CPython exits **1** on an unhandled exception (regardless of exception type) and 130 on
     SIGINT-as-Ctrl-C — the Python signal your process died from is invisible in `1`
     (see [languages/python](../languages/python.md)).
   - The JVM exits 1 for an uncaught exception in `main`; the exit status on signal death is
     not documented API behavior ([languages/java](../languages/java.md)).
   - Shell wrappers shift everything: `sh -c 'cmd ...'` reports the *inner* command's status,
     but an entrypoint chain like `sh -c "prepare && exec cmd"` can also fail in `prepare`
     with an unrelated code; `su`, `nohup`, `setsid`, and `timeout` each add their own
     conventions (e.g. GNU `timeout` exits **124** on its own timeout, and the signaled
     child's status only with `--preserve-status`).
   - Container runtimes report their *own* codes for their own failures — Docker reserves
     **125** for "docker run itself failed" and passes 126/127 through from the container's
     shell ([containers/docker](../containers/docker.md)).
4. **Truncation collides.** `exit(256)` reports 0; `exit(300)` and `exit(44)` are
   indistinguishable forever ([lifecycle EX-005](./lifecycle.md#ex-005--truncation-to-8-bits-what-is-lost-and-where)).
   A "success" can literally be a mis-encoded large failure code.

### Evidence checklist by suspicion

| You see | Treat as root cause only after |
|---------|-------------------------------|
| `137` | OOM evidence: `journalctl -k`/`dmesg` oom-kill lines, cgroup v2 `memory.events: oom_kill`, runtime API flag (`State.OOMKilled`), or a supervisor's kill policy (timeout → SIGKILL). If none: suspect a self-chosen `exit(137)`. |
| `139` | Core file / `coredumpctl list`, `dmesg` `segfault` line (faulting library + offset), or debugger run; remember `RLIMIT_CORE=0` suppresses dumps silently (lifecycle EX-006). |
| `127` | PATH/wrapper analysis: `command -v cmd`, `type -a cmd`, PATH as seen *inside* the failing environment (CI jobs, cron, containers all have different PATHs), shell hash staleness. |
| `126` | `ls -l`, mount flags (`noexec`), shebang validity — a bad interpreter also surfaces as 126 on some systems and "No such file or directory" messages for the *interpreter*. |
| `130`/`143` | Who sent the signal: interactive terminal, `timeout`, systemd stop, orchestrator eviction. Check the supervisor's logs and grace-period settings before blaming the process. |
| `1` | Nothing beyond the program's stderr — `1` is the universal "some failure" and carries no specific information. |

The general rule: **an exit status is a hypothesis generator, not a verdict.** Pair it with
stderr, journal/kernel logs, and the consuming system's metadata before writing the incident
report.

## EX-012 — Who consumes these conventions

- **Shells** are the primary producers of the 128+N/126/127 conventions and the primary
  consumers of 0/non-zero for `&&`, `||`, `if`, and `set -e`-style automation. The
  per-shell mechanics (and their differences!) live in [shells/](../shells/index.md).
- **GNU coreutils** document per-tool contracts (ls/grep/diff rows above) that scripts lean
  on; grep's `-q` masking behavior is a documented, deliberate trap.
- **Service managers** map exit statuses to restart decisions: systemd classifies clean vs
  abnormal and lets you extend success/restart-prevention sets (`SuccessExitStatus=`,
  `RestartPreventExitStatus=`), and its Process Exit Codes tables (LSB/BSD ranges) are
  themselves a conventions catalogue — see
  [service-managers/systemd](../service-managers/systemd.md) and the comparison hub
  [service-managers/index](../service-managers/index.md).
- **Container runtimes and orchestrators** consume the same conventions at the boundary:
  Docker's 125/126/127 runtime codes and `docker events` translation of signal deaths
  (SIGTERM → `exitCode=143`), Kubernetes surfacing `exitCode` + `reason` (e.g. `OOMKilled`,
  `Error`) in container states and steering `restartPolicy`/CrashLoopBackOff from them —
  see [containers/docker](../containers/docker.md) and
  [containers/kubernetes](../containers/kubernetes.md).
- **Troubleshooting playbooks** compile the evidence checklists into runbooks; the
  cross-reference of status values for incidents is maintained in
  [troubleshooting/common-status-values](../troubleshooting/common-status-values.md).

## Related Topics

- [The life of an exit status](./lifecycle.md) — the kernel/wait/shell mechanics underneath every row above
- [Shell exit-status mechanics](../shells/index.md) — pipefail, PIPESTATUS, traps: how shells *produce* these values
- [Service managers](../service-managers/index.md) — exit-code-driven restart decisions
- [Containers](../containers/index.md) — runtime codes 125/126/127 and orchestrator status handling
- [Common status values (troubleshooting)](../troubleshooting/common-status-values.md) — incident-side catalogue
- [curl](../../../networks/tools/curl.md) — curl usage page in this book
- [Python](../languages/python.md), [Java](../languages/java.md) — runtime exit-status transformation examples

## References

- POSIX.1-2017 XCU Chapter 2, §2.8 "Exit Status and Errors" (incl. 2.8.2 and RATIONALE table reserving 126/127/>128) — The Open Group — <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html>
- Bash Reference Manual, §3.7.5 "Exit Status" (128+N, 126/127, builtin usage → 2) — Free Software Foundation / Chet Ramey — <https://www.gnu.org/software/bash/manual/bash.html>
- GNU grep manual / grep(1) EXIT STATUS — GNU Project (man page render) — <https://man.archlinux.org/man/grep.1.en>
- GNU diffutils diff(1) — GNU Project (man page render) — <https://man.archlinux.org/man/diff.1.en>
- GNU coreutils manual, "ls invocation" Exit status — GNU Project (doc source `doc/coreutils.texi`) — <https://github.com/coreutils/coreutils/blob/master/doc/coreutils.texi>
- curl(1) man page, "EXIT CODES" — curl project — <https://curl.se/docs/manpage.html>
- `timeout(1)` exit statuses (124/125/126/127) — GNU coreutils (man page render) — <https://man.archlinux.org/man/timeout.1.en>
- `wait(2)` (kernel-side status semantics underpinning 128+N) — Linux man-pages project — <https://man7.org/linux/man-pages/man2/wait.2.html>
