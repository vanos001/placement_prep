# Troubleshooting by Exit Status: Common Values and Their Evidence

An exit status is an *observation*, not a diagnosis. The only parts of the
status byte that the OS guarantees are the kernel's wait-status encoding
(exited vs. signaled vs. stopped, man 2 `wait`) and the 8-bit truncation of
the value the process passed to `exit` (man 2 `_exit`: `status & 0xFF`).
Everything else — which value means what — is a convention maintained by
shells, runtimes, service managers, and container runtimes. Three labels
are used throughout: **guarantee** (kernel/POSIX specifies it — XCU 2.8.2:
"If a command is not found, the exit status shall be 127. If the command
name is found, but it is not an executable utility, the exit status shall
be 126"; a command "terminated because it received a signal shall be
reported as greater than 128"), **convention** (shells and runtimes agree,
nothing forces compliance — 0 = success, 128+N = signal N, sysexits 64–78),
and **impl** (one implementation's documented-or-observed behavior — Java's
launcher exit 1, CPython's 130, Rust's 101).

---

## TR-001 The common status values, decoded

| Status | Typical meaning | Guarantee vs convention | First confirming evidence |
|---|---|---|---|
| `0` | success | convention for arbitrary programs (POSIX defines 0 = success *for shell utilities*) | the program's own docs/logs; absence of error output |
| `1` | generic failure; catch-all error | convention | program stderr; for Java/Python/Node: uncaught-exception traceback is the real cause |
| `2` | shell: reserved for builtin misuse; Go: unrecovered panic; OCaml: uncaught exception; grep: serious error | convention / **documented** per runtime | Go: stack dump on stderr; OCaml: `Fatal error: exception …` line |
| `126` | command found but not executable | **POSIX** (2.8.2) + shells | `sh -c 'cmd'; echo $?`, wrapper stderr; strace `execve` → `EACCES` |
| `127` | command not found | **POSIX** (2.8.2) + shells | missing file/PATH problem; strace `execve` → `ENOENT`; OCaml `Unix.system` documents `WEXITED 127` |
| `128+N` | killed by signal N | POSIX: "> 128" is the standard; exact `128+N` arithmetic is the **shell** formula (bash; Node docs state the same rule) | decode N; then signal-specific checks below |
| `130` (=128+2) | SIGINT — user interrupt (or a runtime re-raising it) | 128+N convention; the *re-raise* path in CPython is **impl** | was Ctrl-C involved? journal/session logs |
| `137` (=128+9) | SIGKILL — OOM killer, `docker stop` escalation, manual `kill -9`, cgroup kill | convention | **not proof of OOM** — check `State.OOMKilled`, dmesg, cgroup `memory.events` (TR-004) |
| `139` (=128+11) | SIGSEGV — invalid memory access | convention | dmesg `segfault` line; core dump / `coredumpctl` (TR-003) |
| `143` (=128+15) | SIGTERM — polite termination request honored (or ignored → escalated later) | convention | service manager logs ("Main process exited, code=killed, status=15/TERM"); who sent it (TR-002/TR-007) |
| `152` (=128+24) | SIGXCPU — CPU-time rlimit exceeded | convention over a documented signal (`getrlimit(2)`): SIGXCPU at the soft limit, repeated, then SIGKILL at the hard limit | `ulimit -t`, systemd `CPUQuota`, `prlimit --pid` |
| `153` (=128+25) | SIGXFSZ — file-size rlimit exceeded | convention over a documented signal (`getrlimit(2)` writes get SIGXFSZ past `RLIMIT_FSIZE`) | `ulimit -f`, application log for write() failures |

Signal numbers used above (SIGINT=2, SIGKILL=9, SIGSEGV=11, SIGTERM=15,
SIGXCPU=24, SIGXFSZ=25) are from man 7 `signal` (x86-64/ARM column).

### The sysexits range: 64–78 (BSD-derived, not a Linux standard)

`<sysexits.h>` defines `EX_OK`(0), `EX__BASE`(64), and the error band
`EX_USAGE`(64), `EX_DATAERR`(65), `EX_NOINPUT`(66), `EX_NOUSER`(67),
`EX_NOHOST`(68), `EX_UNAVAILABLE`(69), `EX_SOFTWARE`(70), `EX_OSERR`(71),
`EX_OSFILE`(72), `EX_CANTCREAT`(73), `EX_IOERR`(74), `EX_TEMPFAIL`(75),
`EX_PROTOCOL`(76), `EX_NOPERM`(77), `EX_CONFIG`(78). Verification result:
man7.org now ships `sysexits.h(3head)` (man-pages 6.19), whose STANDARDS
section says simply "BSD" and whose HISTORY traces it to 4.0BSD's sendmail.
The header **exists on Linux** (glibc ships it; Python's `os` module
exports the `EX_*` constants "and can be used with `_exit()`, although they
are not required" — os docs, quoted in [../languages/python.md](../languages/python.md) §1.3),
but **usage is a BSD-derived convention, not a Linux standard**: no kernel
or shell mechanism interprets 64–78 specially, so the band means "ask the
program's documentation" — with `EX_TEMPFAIL` (75) as a de-facto
retry-me contract with MTAs and job schedulers.

Worked decode, annotated:

```console
$ ./check-queue; echo $?
137
$ # 137 > 128  -> died by signal (POSIX rule). 137-128 = 9 = SIGKILL.
$ # SIGKILL cannot be caught/blocked (man 7 signal) -> sender was the
$ # kernel (OOM/cgroup) or an external kill. Which one? -> TR-004 checks.
```

Sources: POSIX.1 XCU 2.8.2 (pubs.opengroup.org, quoted); man 7 `signal`
(numbers table, SIGKILL/SIGSTOP uncatchable); man 2 `_exit`/`wait`;
bash `128+n` formula (GNU Bash Reference Manual, *Exit Status* — gnu.org
was unreachable from this environment; the formula is additionally
documented in Node's process docs "exit codes" section and observable in
any shell — marked convention); `sysexits.h(3head)`
(https://man7.org/linux/man-pages/man3/sysexits.h.3head.html — fetched,
man-pages 6.19).

---

## TR-002 SIGTERM vs SIGKILL, and the shutdown race

**SIGTERM (15)** is the polite request: catchable, blockable, ignorable. A
process may convert it into a clean shutdown — which is exactly why a 143
does not tell you whether cleanup ran or whether the process died
mid-flight. **SIGKILL (9)** is uncatchable and unignorable (man 7
`signal`): when you see 137 the process had no chance to run any handler —
no `atexit`, no shutdown hooks, no `finally`, no `'exit'` event.

The canonical shutdown race: the supervisor sends SIGTERM, your handler
starts a multi-second cleanup, the supervisor's patience expires (systemd
`TimeoutStopSec` default 90s per
[../service-managers/systemd.md](../service-managers/systemd.md); `docker
stop` default 10s per [../containers/docker.md](../containers/docker.md);
Kubernetes `terminationGracePeriodSeconds` default 30s per
[../containers/kubernetes.md](../containers/kubernetes.md)), and SIGKILL
arrives mid-cleanup — the parent observes **137**, not 143: the grace
period, not the handler, decided the status.

Confirming evidence for "which signal, who sent it, when":

- `journalctl -u myservice` — systemd logs the escalation ("Sending
  SIGTERM…", later "Killing process … (myservice) with signal SIGKILL") and
  the final line `Main process exited, code=killed, status=9/KILL`.
- `docker inspect <c> --format '{{json .State}}'` — `ExitCode`,
  `OOMKilled`, `FinishedAt`; `docker events` shows `signal=15` then
  `exitCode=143` (drill in
  [../containers/troubleshooting-scenarios.md](../containers/troubleshooting-scenarios.md)).
- `strace -f -e trace=kill,tgkill -p <pid>` on a reproducing process shows
  the sender's pid (the first field).
- If 137 appears *without* a stop/timeout: suspect the OOM killer before
  concluding "someone ran kill -9" — TR-004.

Two more race patterns: the **TERM-then-exit race** (the process exits
between the parent's `kill()` and `wait()`; a signal sent in that window
can hit a reused PID — Node's `subprocess.kill` documents this verbatim,
nodejs.md §5.6) and **double-escalation** (a wrapper that ignores SIGTERM
per TR-008 forces the supervisor into SIGKILL; group-kill via
`kill(-pgid)`/`process_group`/`setsid` fixes delivery, not statuses).

---

## TR-003 Segfaults (139) and core dumps

Default action for SIGSEGV is "core" (man 7 `signal`). The shell reports
139; the kernel additionally tries to write a core file — *if and only if*
all of these allow it (conditions from man 5 `core`, verified):

- `RLIMIT_CORE` (soft core limit) is not 0 — `ulimit -c` / `prlimit`;
- `/proc/sys/kernel/core_pattern` points to a writable location (or a pipe
  program); an empty `core_pattern` + `core_uses_pid=0` means the core is
  silently dropped;
- for privileged/suid processes, `fs.suid_dumpable` must permit it;
- the same conditions apply to SIGABRT (134) crashes — `assert()` failures
  and Go/Rust/Python `abort()` paths land here too.

Evidence chain for a segfault:

```console
$ dmesg | tail -1
[ 1234.567] myapp[8123]: segfault at 10 ip 000055... sp 00007f... error 4 in libfoo.so.1.2[5555...]
$ cat /proc/sys/kernel/core_pattern
|/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %e
$ coredumpctl list | tail -3            # systemd-coredump recorded it
$ coredumpctl dump <pid> -o core        # extract; then gdb ./myapp core
```

`coredumpctl` exists only where systemd-coredump is the `core_pattern`
handler (the pipe line above is quoted verbatim in `core(5)`'s systemd
section); on non-systemd hosts read `core_pattern` literally as a path
with `%p`/`%e` templates. In the dmesg line, `error 4` encodes the fault
type and `in libfoo.so` names the mapping — the fastest library
attribution available.

Sources: man 5 `core` (fetched: RLIMIT_CORE, core_pattern, core_uses_pid,
systemd-coredump pipe, coredumpctl examples); man 7 `signal` (default
"core" action).

---

## TR-004 OOM kills and resource limits

**The kernel OOM killer** picks a victim when memory is exhausted and sends
SIGKILL — so the *status* is the same 137 a human `kill -9` produces. Never
report "OOM" from the status alone; confirm with, in ascending strength:

1. `/proc/<pid>/oom_score_adj` (since Linux 2.6.36) — the badness
   adjustment you (or a manager) set; heuristic scores run 0–1000
   (proc_pid_oom_score_adj(5), verified). Docker exposes the knob as
   `--oom-score-adj` (-1000..1000, verified in the engine run docs).
2. `dmesg`/`journalctl -k` — the kernel prints the kill decision and the
   "Out of memory: Killed process …" line with the victim's uid/oom_score.
3. cgroup v2 counters — `memory.events`: the `oom_kill` counter increments
   for every kill in that cgroup, and `oom_group_kill` when
   `memory.oom.group` caused the whole group to be killed (kernel cgroup-v2
   admin docs, verified). Reading it costs nothing and survives log
   rotation: `cat /sys/fs/cgroup/.../memory.events`.
4. Container runtimes surface the same fact: Docker
   `State.OOMKilled == true` (Engine API; see
   [../containers/docker.md](../containers/docker.md)); Kubernetes shows
   `Last State: Terminated, Reason: OOMKilled, Exit Code: 137` in
   `kubectl describe pod` ([../containers/kubernetes.md](../containers/kubernetes.md)).

**Memory rlimits and other limits produce *different* signals/statuses:**

| Limit exceeded | What happens (getrlimit(2)/setrlimit) | Observable status |
|---|---|---|
| `RLIMIT_CPU` soft | SIGXCPU (24) — repeated once per second until terminated or the hard limit is hit | 152 (=128+24); then SIGKILL (137) if it keeps running |
| `RLIMIT_CPU` hard | SIGKILL | 137 |
| `RLIMIT_FSIZE` | SIGXFSZ (25) on writes past the limit (a handler that returns gets `EFBIG` on retry) | 153 (=128+25) |
| `RLIMIT_CORE = 0` | no core dump on SIGSEGV/SIGABRT — status unchanged, evidence gone | 139/134 with *no* coredump (TR-003) |
| `RLIMIT_NPROC` / `RLIMIT_NOFILE` | no signal — the syscall fails (`EAGAIN`/`EMFILE`) | ordinary nonzero exit chosen by the program, or language exception |

So "137" is SIGKILL, "152/153" are rlimit signals, and a program that
crashes in `malloc` under memory pressure may show any nonzero status —
classify by evidence, not by proximity to 137.

Sources: man 2 `getrlimit` (fetched: SIGXCPU soft/hard semantics, SIGXFSZ);
man 5 `proc_pid_oom_score_adj` (fetched: badness 0–1000, since 2.6.36);
kernel cgroup-v2 admin guide (memory.events `oom_kill`/`oom_group_kill`,
`memory.oom.group` — fetched); docs.docker.com engine run (`--oom-score-adj`
— fetched); man 7 `signal` (numbers 24/25); man 5 `core` (RLIMIT_CORE=0).

---

## TR-005 Failed exec: 126 vs 127, and what wrappers do to it

`execve(2)` returns only on failure. The two statuses are standardized at
the shell level (POSIX XCU 2.8.2, quoted in TR-001): **127 = not found**
(`ENOENT`), **126 = found but not executable** (`EACCES`, or a directory).

Attribution through layers:

```console
$ /opt/app/bin/server; echo $?        # direct: bash prints "bash: ...: Permission denied"
126
$ sh -c '/opt/app/bin/server'; echo $?
126
$ docker run myimg /etc; echo $?      # docker's own contract (docs): 126 cannot be invoked
126
$ docker run myimg nosuchbin; echo $? # 127 cannot be found
127
```

Per-language exec-failure surfaces: **Docker** adds its own layer code —
125 = the *daemon* failed (usually not your program's fault), 126/127 =
the contained command (docs.docker.com engine run "Exit Status",
verified); **Go** classifies at `Start` (`LookPath` → `ErrNotFound` as an
error value, not a child status, go.md §5.1); **Python** raises before
forking (`Popen(["missing"])` → `FileNotFoundError`; via a shell you get
`returncode 127`); **Node** emits `'error'` (ENOENT) and `'exit'` "may or
may not fire" (nodejs.md §5.4); **Java** throws `IOException` subclasses
(ProcessBuilder docs, java.md §5.1); **OCaml's `Unix.system` returns
`WEXITED 127`** when *the shell* couldn't be executed (Unix docs, ocaml.md
§5.3) — a 127 that attributes to the shell, not your command. Wrappers can
mask the distinction: `exec /opt/app/bin/server` preserves 126/127, while
a child-running wrapper that `exit 0`s its success path does not (TR-006).

Confirming evidence: run the failing command under
`strace -f -e trace=execve` and read the errno (`ENOENT` → 127-class,
`EACCES` → 126-class); check `ls -l` for the mode bit and the shebang
(a missing interpreter in `#!` also surfaces as ENOENT — 127), and `echo
$PATH` in the *exact* environment the wrapper used.

---

## TR-006 Pipeline, wrapper, and subprocess attribution

`$?` is only ever the **last** command in a pipeline. Three failure modes
routinely misattributed:

1. **Pipeline loss**: `long_job | tee log` fails but `$?` is `tee`'s 0.
   Evidence/fix: bash's `PIPESTATUS` array or `set -o pipefail` — both
   **bash extensions**, not POSIX (dash has neither).
2. **Wrapper swallowing**: a wrapper ending with a cleanup command
   (`rm -f $lock`) overwrites the program's status. Capture `st=$?`
   immediately and `exit $st`; bash makes a killed child's 128+N visible
   as `$?`, and re-exiting with that value preserves the convention.
3. **Subshell/`sh -c` layers**: each `sh -c` adds one attribution hop —
   the shell uses 126/127 for its own failures (POSIX), 2 for builtin
   misuse, and otherwise propagates the child's status or 128+N. A status
   that looks impossible (2 from a program that never returns 2) usually
   came from a shell layer — exactly why Node's docs mark code 2
   "reserved by Bash for builtin misuse" (process docs).

Attribution toolbox: `ps -o pid,ppid,pgid,cmd` and `pstree` to see who
spawns whom; `strace -f -e trace=execve,clone,exit_group` to watch the
actual `execve` chain and each `exit_group` code; `journalctl _PID=<pid>`
or `journalctl _COMM=<name>` for the unit's view. In programs, the
sibling-language chapter [../languages/comparison.md](../languages/comparison.md)
(XC-006) explains why the same death is `-15` to Python, `(null,'SIGTERM')`
to Node, `139`-style 128+N to Java, and a `WSIGNALED 15` variant to OCaml —
multi-language fleets must normalize before comparing.

---

## TR-007 Service managers and containers: where the status is recorded

The same status travels with different metadata depending on who supervised
the process — this chapter's sibling pages own those layers:

- **systemd**: `systemctl status`/`journalctl` report `code=exited,
  status=N` vs `code=killed, status=15/TERM`; `SuccessExitStatus`/
  `RestartPreventExitStatus` decide whether your convention-0-only exit
  triggers a restart; `Restart=`, start-limit and kill-escalation knobs —
  [../service-managers/systemd.md](../service-managers/systemd.md)
  (SM-001..SM-005). OpenRC's supervise-daemon/start-stop-daemon, runit's
  `./finish $1/$2` (exitcode-or-−1, low wait-status byte), and s6's
  `finish` args + exit-125 permanent-failure contract are the other
  managers' analogues — [../service-managers/openrc.md](../service-managers/openrc.md),
  [../service-managers/runit.md](../service-managers/runit.md),
  [../service-managers/s6.md](../service-managers/s6.md).
- **Docker**: `docker inspect .State.{Status,ExitCode,OOMKilled,Error}`,
  `docker events`, the 125/126/127 layer codes, `--restart` policies and
  stop-timeout escalation — [../containers/docker.md](../containers/docker.md)
  (CT-003..CT-005).
- **Kubernetes**: `kubectl describe pod` `Last State: Terminated, Exit
  Code`, `Reason` (OOMKilled/Error), `terminationMessagePath`, restart
  policy and CrashLoopBackOff timing —
  [../containers/kubernetes.md](../containers/kubernetes.md)
  (CT-006..CT-008). Six evidence-first drills (137-after-deploy, ignored
  SIGTERM, grace-period exhaustion, 143/137/139 triage, zombie
  accumulation, CrashLoopBackOff exit 1) are worked step-by-step in
  [../containers/troubleshooting-scenarios.md](../containers/troubleshooting-scenarios.md) (CT-011).
- Cross-cutting warning: **PID 1 in containers absorbs signals and child
  reaping differently** — a `sh -c` entrypoint makes SIGTERM a no-op unless
  trapped, so the runtime's SIGKILL escalation (137) becomes the *expected*
  outcome; see [../containers/pid1-signals.md](../containers/pid1-signals.md)
  (CT-001/CT-002) before blaming the application.

---

## TR-008 Masked, ignored, and inherited signal dispositions

Two kernel rules decide most "my handler never ran" mysteries — both from
man 7 `signal` (verified quotes):

1. **Across `execve`:** "the dispositions of handled signals are reset to
   the default; the dispositions of ignored signals are left unchanged."
   I.e. `SIG_IGN` **survives exec**, handlers do not. A parent that set
   `SIGTERM` to `SIG_IGN` (e.g. `nohup`-style code, a job runner) leaves
   every child *ignoring* SIGTERM — the child's own SIGTERM handler never
   gets installed *because the child never installs one*, and even ones
   that do are fine, but runtimes that rely on the default action (see 2)
   inherit the ignore instead.
2. **The signal mask is preserved across `execve`** (man 7 `signal`;
   `sigprocmask(2)`), and the pending set likewise. A child that starts
   with SIGTERM/SIGCHLD blocked stays blocked until it unblocks.

Consequences with statuses:

- **Inherited SIG_IGN → graceless stops.** A supervisor's timeout then
  produces SIGKILL (137) because the ignored SIGTERM caused no reaction.
  Python's `subprocess` documents the countermeasure: `restore_signals=True`
  (default) restores `SIG_IGN`'d signals (SIGPIPE, SIGXFZ [sic], SIGXFSZ
  per the docs' list) to `SIG_DFL` before exec (python.md §5.1); Go
  documents the mirror fact — `os/exec` children "will inherit the modified
  signal mask" of the runtime (go.md §4.3); `nohup(1)` exploits the
  survival rule deliberately.
- **Inherited blocked mask → delayed or lost signals.** A service that
  inherits SIGTERM blocked will not react even with a handler installed
  until it unblocks — the supervisor sees a timeout, then 137. Evidence:
  `cat /proc/<pid>/status` → `SigBlk`/`SigIgn`/`SigCgt` masks (bit
  positions = signal numbers), or `sigprocmask` via `strace`.
- **Runtime defaults that mimic ignores.** CPython ignores SIGPIPE (so
  `BrokenPipeError` surfaces instead of silent death, python.md §4.3);
  Node *removes* default SIGINT/SIGTERM behavior the moment you register a
  listener (nodejs.md §4.1) — a listener that forgets to exit converts
  SIGTERM into a no-op, so `docker stop` escalates to SIGKILL and the
  status you get is 137, not 143.
- **SIGKILL/SIGSTOP cannot be masked, caught, or ignored** by anyone (man 7
  `signal`) — a 137 is always terminal and unhandled, in all eight
  languages ([../languages/comparison.md](../languages/comparison.md) XC-004).

Diagnostic one-liners:

```console
$ grep -E 'SigBlk|SigIgn|SigCgt' /proc/$(pgrep -f mydaemon)/status
SigBlk: 0000000000000000        # blocked mask: none
SigIgn: 0000000000000006        # bits 1,2 (SIGHUP,SIGINT) ignored  <- inherited?
SigCgt: 0000000180000000        # caught: 35,36 ...
```

Sources: man 7 `signal` (execve disposition + mask rules, fetched);
`sigprocmask(2)`; python.md/nodejs.md/go.md as cited; `nohup(1)`.

---

## Related Topics

- Comparison grounding: [Cross-language comparison](../languages/comparison.md)
  (XC-001..XC-009 — which runtime produced which status).
- Kernel interface details: [kill/raise](../interfaces/kill-raise.md) ·
  [signal masks](../interfaces/signal-masks.md) ·
  [sigaction/signal](../interfaces/sigaction-signal.md) ·
  [async-signal-safety](../interfaces/async-signal-safety.md) ·
  [tgkill](../interfaces/tgkill.md)
- Signal reference: [Standard signals](../signals/standard-signals.md) ·
  [Real-time signals](../signals/real-time-signals.md)
- Supervision layers: [Service managers](../service-managers/index.md) ·
  [Containers](../containers/index.md) ·
  [Container troubleshooting drills](../containers/troubleshooting-scenarios.md) ·
  [PID 1 and signals](../containers/pid1-signals.md)
- Next step for a live incident: [Decision tree (TR-009)](./decision-tree.md).
- The `exit-status/` chapter of this part covers the status lifecycle and
  the full 0–255 convention map; `shells/` covers the shell layer that
  manufactures 126/127/128+N.

## References

- POSIX.1-2017 XCU §2.8 (Exit Status and Errors; 2.8.2 quotes) —
  https://pubs.opengroup.org/onlinepubs/9699919799/
- Linux man-pages (man7.org, fetched 2026-10): `signal(7)` (execve rules,
  default actions, signal numbers 2/9/11/15/24/25), `core(5)` (core_pattern,
  RLIMIT_CORE conditions, systemd-coredump, coredumpctl), `getrlimit(2)`
  (RLIMIT_CPU→SIGXCPU, RLIMIT_FSIZE→SIGXFSZ), `proc_pid_oom_score_adj(5)`
  (badness 0–1000, since 2.6.36), `wait(2)`, `_exit(2)` (`status & 0xFF`),
  `sigprocmask(2)` — https://man7.org/linux/man-pages/
- `sysexits.h(3head)` (man-pages 6.19; STANDARDS: BSD; HISTORY: 4.0BSD) —
  https://man7.org/linux/man-pages/man3/sysexits.h.3head.html
- Kernel cgroup v2 admin guide (`memory.events`: `oom_kill`,
  `oom_group_kill`; `memory.oom.group`) —
  https://docs.kernel.org/admin-guide/cgroup-v2.html
- Docker "Exit status" (125/126/127) and `--oom-score-adj` —
  https://docs.docker.com/engine/containers/run/ ; Engine API
  `ContainerState.OOMKilled` as verified in
  [../containers/docker.md](../containers/docker.md)
- GNU Bash Reference Manual, *Exit Status* (128+n formula) —
  https://www.gnu.org/software/bash/manual/ (gnu.org unreachable from this
  environment; the >128 POSIX rule was verified directly, and the exact
  128+n arithmetic is corroborated by Node's documented "Signal Exits"
  rule — https://nodejs.org/docs/latest-v22.x/api/process.html#exit-codes)
- Python 3 `os` module (`EX_*` constants, `restore_signals`) —
  https://docs.python.org/3/library/os.html
- Supervisor semantics verified in the sibling pages:
  [systemd](../service-managers/systemd.md),
  [runit](../service-managers/runit.md) (`./finish` args),
  [s6](../service-managers/s6.md) (exit-125 contract)
