# Troubleshooting: Exit Statuses, Signals, and Process Death in Practice

This chapter is the applied layer of the process-exit-signal part: given an
observed exit status or termination signal, determine what actually
happened — with evidence, not folklore. It assumes the conceptual
foundations from [../signals/index.md](../signals/index.md),
[../interfaces/index.md](../interfaces/index.md), and the language chapters
summarized in [../languages/comparison.md](../languages/comparison.md)
(XC-001..XC-009).

## Contents

| Page | IDs | What it covers |
|---|---|---|
| [Common status values](./common-status-values.md) | TR-001..TR-008 | The deep decode table: 0, 1, 2, 126, 127, 128+N, 130, 137, 139, 143, 152/153, sysexits 64–78; SIGTERM vs SIGKILL and shutdown races; segfaults and core dumps (`core_pattern`, systemd-coredump, `coredumpctl`); OOM kills and rlimits (`oom_score_adj`, cgroup `memory.events`); failed exec (ENOENT/EACCES attribution); pipeline/wrapper status attribution; service-manager and container layers; ignored/masked signal inheritance across `execve` |
| [Decision tree](./decision-tree.md) | TR-009 | Status + evidence → plausible causes → confirmatory checks; mermaid flowchart + text procedure + worked examples tied to the container drills |

## The method in one paragraph

An exit status is an *observation*. The kernel guarantees only the
wait-status encoding and the 8-bit truncation; 126/127 are POSIX shell
contracts; 128+N is a shell convention over the "> 128" POSIX rule; the
sysexits 64–78 band is a BSD-derived convention that exists on Linux but is
not a Linux standard. Everything else — Go's panic-2, Rust's panic-101,
Java's launcher-1, CPython's 130 — is per-runtime documentation. Therefore:
decode first (signal band? exec failure? runtime code?), then demand
confirming evidence for every plausible cause (`State.OOMKilled`,
`memory.events` `oom_kill`, dmesg, `coredumpctl`, strace on `execve`,
`SigIgn`/`SigCgt` masks) before naming it. [Common status
values](./common-status-values.md) is the reference;
[the decision tree](./decision-tree.md) is the procedure.

## Where each layer's view lives

- Supervisors rewrite context around the same status: systemd's
  `code=killed, status=15/TERM` lines, restart decisions, and
  `SuccessExitStatus` — [../service-managers/index.md](../service-managers/index.md)
  (SM-001..SM-013).
- Containers add layer codes (125/126/127), `OOMKilled`, grace-period
  escalations, and PID-1 signal absorption —
  [../containers/index.md](../containers/index.md) (CT-001..CT-011), with
  six end-to-end drills in
  [../containers/troubleshooting-scenarios.md](../containers/troubleshooting-scenarios.md).
- Per-language exit semantics (which code means "panic" where): the eight
  language chapters, cross-compared in
  [../languages/comparison.md](../languages/comparison.md).

## Related Topics

- [Signals overview](../signals/index.md) ·
  [Standard signals](../signals/standard-signals.md) ·
  [kill/raise](../interfaces/kill-raise.md) ·
  [signal masks](../interfaces/signal-masks.md) ·
  [async-signal-safety](../interfaces/async-signal-safety.md)
- [Service managers index](../service-managers/index.md) ·
  [Containers index](../containers/index.md)
- The `exit-status/` chapter of this part owns the status lifecycle and
  full convention map; `shells/` owns the shell layer that produces
  126/127/128+N.

## References

- Referenced primary sources (POSIX XCU 2.8, man 7 `signal`, man 5 `core`,
  `sysexits.h(3head)`, `getrlimit(2)`, `proc_pid_oom_score_adj(5)`, kernel
  cgroup-v2, Docker/Kubernetes docs) are listed per claim on the two pages
  above; the master list is at the end of
  [./common-status-values.md](./common-status-values.md).
