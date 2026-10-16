# Language Chapters: Exit Statuses and Signals per Runtime

This part documents how each of the eight languages — C, C++, Python, Go,
Java, Rust, Node.js, and OCaml — creates processes, terminates, handles
signals, and reports exit status, at the exit/signal slice of each runtime.
Every chapter follows the same six-area structure (syntax and semantics;
standard-library/runtime API inventory; process lifecycle and termination;
signals and OS interaction; subprocess and child-process management;
concurrency and resource semantics), so any two chapters can be read side
by side. Requirements are tracked as `LG-*` rows in the part's unified
ledger: [Coverage Ledger — Process Exit & Signals](../../process-exit-signal-coverage.md).

## Contents

| Page | Ledger IDs | What it covers |
|---|---|---|
| [C](./c.md) | LG-C-001..006 | `main`/`exit`/`_Exit`/`abort`/`atexit`/`quick_exit`, C11/C23 deltas, `signal`/`sigaction` + handler UB list, fork/exec/wait/`posix_spawn`, pthread + stdio hazards, API inventory with verified signatures |
| [C++](./cpp.md) | LG-CPP-001..006 | the C substrate plus `std::exit`/`std::terminate`, static destruction order, exceptions vs termination paths, RAII cleanup guarantees, `std::system` |
| [Python](./python.md) | LG-PY-001..006 | `sys.exit`/`SystemExit`/`os._exit`, `atexit` ordering, interpreter shutdown, `signal` module limitations, `subprocess` (pipes, timeouts, returncode), CPython-specific behavior |
| [Go](./go.md) | LG-GO-001..005 | `os.Exit` vs return from `main`, deferred calls, `log.Fatal`, panic/recover, `os/exec` (`Cmd`, `ProcessState`, `ExitCode`), signal notification with `os/signal` |
| [Java](./java.md) | LG-JA-001..005 | JVM shutdown sequence, `System.exit` vs `Runtime.halt`, shutdown hooks, uncaught exceptions, `ProcessBuilder`/`ProcessHandle`, `waitFor`/`destroyForcibly`, stream-deadlock avoidance |
| [Rust](./rust.md) | LG-RU-001..005 | return from `main`, `std::process::exit`/`abort`, panic unwind vs `panic=abort`, destructor (drop) guarantees, `std::process::Command`/`Child`/`ExitStatus`, `std::os::unix::process` |
| [Node.js](./nodejs.md) | LG-NO-001..005 | event-loop completion vs `process.exit`, `process.exitCode`, signal events, `node:child_process` (`spawn`/`exec`/`execFile`/`fork`), `code` vs `signal` semantics, uncaught exceptions |
| [OCaml](./ocaml.md) | LG-OC-001..006 | `Stdlib.exit`/`at_exit`, runtime shutdown, `Sys`/`Unix` signal handling, `Unix.fork`/`execv*`/`wait`/`process_status`, `open_process_*` pipe management |
| [Cross-Language Comparison](./comparison.md) | XC-001..009 | one table per lifecycle dimension: what a returned status means, which cleanup runs on which path, how child statuses decode, per-runtime panic/abort codes (130, 101, 2), and where the runtimes disagree with POSIX expectations |

## How this part relates to the Section G deep dive

The sibling part [Process & Runtime Semantics by
Language](../../../languages/process-runtime/index.md) (`PL-*` ledger IDs) is
the **full-depth** documentation project for the same eight languages —
six mandatory coverage areas per language, version-verified against the
current language/runtime releases, with per-language coverage ledgers. The
chapters here are the exit/signal-scoped slice (`LG-*` IDs); where the two
parts overlap, the Section G chapters are the source of record for current
version baselines, and the chapters here remain the faster per-runtime
exit-code decoder. Neither part duplicates the other's ledger.

## Reading order

- First: [Cross-Language Comparison](./comparison.md) — the map of where
  the eight runtimes agree and diverge.
- Then: the chapter for the runtime you are debugging, plus
  [Common Status Values](../troubleshooting/common-status-values.md) to
  decode the number you actually observed.
- OS substrate beneath every call in this part: [Signals](../signals/index.md)
  and [Interfaces](../interfaces/index.md); the applied procedure is in
  [Operational Troubleshooting](../troubleshooting/index.md).

## Related Topics

- [Section G deep dive: Process & Runtime Semantics by Language](../../../languages/process-runtime/index.md)
- [Unified coverage ledger](../../process-exit-signal-coverage.md)
- [Troubleshooting index](../troubleshooting/index.md) ·
  [Containers index](../containers/index.md) ·
  [Service managers index](../service-managers/index.md)

## References

Primary sources (language specifications, official runtime documentation,
POSIX.1-2024, Linux man-pages) are cited per claim inside each chapter and
consolidated in each chapter's trailing `References` section; the
requirement-to-source mapping lives in the
[unified coverage ledger](../../process-exit-signal-coverage.md).
