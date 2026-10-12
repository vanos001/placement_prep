# Java: Exit Status, Signals, and Process Lifecycle

**ID range:** LG-JA-001 … LG-JA-005 — **Version scope:** JDK 21 (LTS) API docs (docs.oracle.com, retrieved 2026-10) plus the `java` command manual for JDK 21; version-dependent items are flagged (ProcessHandle/onExit are Java 9+). Claims are separated into *specification/documented API behavior* and *HotSpot/reference-implementation behavior* — the latter is explicitly marked, because several exit-status details are deliberately unspecified by the platform docs.

The JVM is a managed runtime hosted in an OS process. Java code never touches exit statuses or signals directly: the platform defines a *shutdown sequence* (hooks), a process API (`ProcessBuilder`/`Process`/`ProcessHandle`), and nothing else. Everything below the JVM's abstractions is implementation behavior.

---

## 1. Syntax and Semantics of Termination (LG-JA-001)

### 1.1 The JVM shutdown sequence — normative definition

The authoritative text is the *Shutdown Sequence* section of [`java.lang.Runtime`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html). The JVM initiates the shutdown sequence in response to exactly three documented events:

1. "when the number of live non-daemon threads drops to zero for the first time" (the JNI note explains that for embedded JVMs, `DestroyJavaVM` is "responsible for initiating the shutdown sequence when the number of live non-daemon threads first drops to zero");
2. "when the `Runtime.exit` or `System.exit` method is called for the first time; or"
3. "when some external event occurs, such as an interrupt or a signal is received from the operating system."

Then, quoted:

> "At the beginning of the shutdown sequence, the registered shutdown hooks are started in some unspecified order. They run concurrently with any daemon or non-daemon threads that were alive at the beginning of the shutdown sequence."

> "After the shutdown sequence has begun, registration and de-registration of shutdown hooks with `addShutdownHook` and `removeShutdownHook` is prohibited." (Violations throw `IllegalStateException`; the same hook registered twice throws `IllegalArgumentException`.)

> "The shutdown sequence finishes when all shutdown hooks have terminated. At this point, the Java Virtual Machine terminates."

And when the JVM terminates:

> "all threads are immediately prevented from executing any further Java code. This includes shutdown hooks as well as daemon and non-daemon threads. This means, for example, that: threads' current methods do not complete normally or abruptly; **finally clauses are not executed**; **uncaught exception handlers are not run**; and **resources opened with try-with-resources are not closed**."

If a hook never terminates ("for example, because of an infinite loop"), "the shutdown sequence will never finish" — only `Runtime.halt` can then end the process.

### 1.2 The explicit exits

**`System.exit(int)`** ([docs](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/System.html#exit(int))):

> "Initiates the shutdown sequence of the Java Virtual Machine. Unless the security manager denies exiting, this method initiates the shutdown sequence (if it is not already initiated) and then blocks indefinitely. This method neither returns nor throws an exception; that is, it does not complete either normally or abruptly. The argument serves as a status code. By convention, a nonzero status code indicates abnormal termination."

Effective equivalence documented in the Javadoc: `System.exit(n)` ≡ `Runtime.getRuntime().exit(n)`. With a security manager present, `checkExit` is consulted (throws `SecurityException` if denied). Note the modern reality: security managers are being phased out (deprecated for removal since JDK 17), but the JDK 21 Javadoc still specifies the check, so it is quoted here.

**`Runtime.exit(int)`** — same contract; additionally documented: "Successful invocations of this method are serialized such that only one invocation initiates the shutdown sequence and terminates the VM with the given status code. All other invocations will perform no action and block indefinitely." And a trap: "Because a successful invocation of this method blocks indefinitely, if it is invoked from a shutdown hook, it will prevent that shutdown hook from terminating. Consequently, this will prevent the shutdown sequence from finishing." (`System.exit` inside a hook therefore deadlocks the shutdown — use `halt` to actually stop.)

**`Runtime.halt(int)`** ([docs](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html#halt(int))):

> "Immediately terminates the Java Virtual Machine. If the security manager denies exiting, throws SecurityException. Otherwise, termination of the Java Virtual Machine is unconditional and immediate. This method does not initiate the shutdown sequence, nor does it wait for the shutdown sequence to finish if it is already in progress."

`halt` is the Java counterpart of `_exit`: no hooks, no finalizers, no flushing — the OS process ends with the given status.

### 1.3 Shutdown hooks

**`Runtime.addShutdownHook(Thread hook)`** ([docs](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html#addShutdownHook(java.lang.Thread))):

> "A shutdown hook is simply an initialized but unstarted thread. Shutdown hooks are started at the beginning of the shutdown sequence. Registration and de-registration of shutdown hooks is disallowed once the shutdown sequence has begun."

> "Uncaught exceptions are handled in shutdown hooks just as in any other thread, as specified in `Thread.UncaughtExceptionHandler`. After the uncaught exception handler has completed, the shutdown hook is considered to have terminated and is not treated differently from a hook that has terminated without having thrown an uncaught exception."

The API Note states the threading contract:

> "Shutdown hooks run at a delicate time in the life cycle of a virtual machine and should therefore be coded defensively. They should, in particular, be written to be thread-safe and to avoid deadlocks insofar as possible. They should also not rely blindly upon services that may have registered their own shutdown hooks and therefore may be in the process of shutting down. … Shutdown hooks should also finish their work quickly."

Hook ordering is **unspecified** — never depend on hook A running before hook B. Hooks may be removed before shutdown begins via `removeShutdownHook` (returns `true` if it had been registered and was removed).

**What triggers hooks:** normal completion (non-daemon threads exhausted), `System.exit`/`Runtime.exit`, and — the JVM's signal story — SIGINT/SIGTERM/SIGHUP on POSIX systems, via handlers the JVM installs itself. Verified from the `java` command manual ([java.html, `-Xrs`](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html)):

> "The JVM catches signals to implement shutdown hooks for unexpected termination. The JVM uses SIGHUP, SIGINT, and SIGTERM to initiate the running of shutdown hooks."

With `-Xrs` (reduce signals), the manual states: "the signal masks for SIGINT, SIGTERM, SIGHUP, and SIGQUIT aren't changed by the JVM, and signal handlers for these signals aren't installed" — so with `-Xrs` those signals kill the JVM with the kernel's default action and hooks do **not** run.

### 1.4 Uncaught exceptions and the implicit exit

- A thread whose `run`/`main` throws propagates through `Thread.getUncaughtExceptionHandler()`: thread-specific handler → thread group override → `Thread.setDefaultUncaughtExceptionHandler` ([docs](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html#setDefaultUncaughtExceptionHandler(java.lang.Thread.UncaughtExceptionHandler))). With nothing installed, the reference implementation prints the stack trace to `System.err` and the thread dies.
- "The thread dies; the JVM lives": if other non-daemon threads remain, the JVM keeps running — per the JLS 12.8 exit rule (program exits when all non-daemon threads terminate) and the `Runtime` shutdown-sequence text.
- **Exit status when `main` throws:** the platform docs do not specify a status. Observed reference-implementation behavior (HotSpot + `java` launcher): the launcher exits with **1**. Mark this as *implementation behavior, not a specification guarantee*; the JLS specifies *when* a program exits, never *with what code* (only "by convention, a nonzero status code indicates abnormal termination" in the `exit` docs).
- Exit status on normal completion (all non-daemon threads end): not specified by the docs; observed reference behavior is **0**. Same caveat.

### 1.5 Daemon vs non-daemon threads

Daemon threads (`Thread.setDaemon(true)`) never block the shutdown sequence: "when the number of live non-daemon threads drops to zero" the sequence begins — daemons are then simply cut off at termination time (no `finally`, no uncaught handlers)..daemon-ness must be set before `Thread.start()`.

### 1.6 Finalization

Finalization (object `finalize()`, `Runtime.runFinalization()`) is deprecated: JEP 421 (JDK 18) — "Deprecate Finalization for Removal"; the JDK 21 Javadoc marks `runFinalization` "Deprecated, for removal: This API element is subject to removal in a future version." At shutdown the JVM performs no finalization guarantee for objects; `finalize()` must never be relied on for process-lifetime cleanup. The replacement for resource lifetime is try-with-resources / `AutoCloseable` (which, note, is also *not* run at JVM termination per §1.1), and for post-mortem cleanup, `java.lang.ref.Cleaner`.

### 1.7 The JLS view: what makes a program exit

The Java Language Specification (referenced normatively from the `Runtime` class doc, "See Also: Java Language Specification 12.8 Program Exit") defines *when*, never *with what status*:

- A program terminates all activity when (1) all non-daemon threads terminate, or (2) some thread invokes `Runtime.exit`/`System.exit`.
- The specification says nothing about the exit status in case (1) — there is no API to choose it, and no documented value. If your application needs a specific status on the "threads just ended" path, it must call `System.exit(n)` explicitly before the last non-daemon thread dies.
- This is why "exit code of a Java program" has exactly two spec-level sources: the argument to `exit`/`halt`, and (unspecified) whatever the implementation does for the implicit paths.

### 1.8 Worked shutdown example

```java
public class Shutdown {
    public static void main(String[] args) {
        Runtime rt = Runtime.getRuntime();
        Thread hook = new Thread(() ->
            System.out.println("cleanup: closing resources"));
        rt.addShutdownHook(hook);          // registered, not started
        // rt.addShutdownHook(hook);       // IllegalArgumentException (same hook, compared with ==)
        System.out.println("working");
        System.exit(3);                    // initiates shutdown sequence
        // unreachable: exit() neither returns nor throws
    }
}
// Console:
// working
// cleanup: closing resources
// $ echo $?   -> 3
```

Under `kill -TERM` (no `-Xrs`), the same hook runs before the process disappears; under `-Xrs`, the kernel default applies and the hook never runs.

### 1.9 Termination-path table (Linux, reference implementation marked where applicable)

| Termination path | Exit status seen by parent | Status class |
|---|---|---|
| `main` returns / last non-daemon thread ends, hooks run | 0 | implementation behavior (not spec'd) |
| `System.exit(7)` / `Runtime.exit(7)` — hooks complete | 7 | documented ("status code") |
| `Runtime.halt(9)` | 9 | documented |
| Uncaught exception from `main`, no handler | 1 + stack trace on stderr | implementation behavior (launcher) |
| SIGTERM/SIGINT/SIGHUP with hooks installed | hooks run, then JVM exits; observed status **143** (128+15) for SIGTERM on Linux | implementation behavior (HotSpot) — not in the JDK docs |
| SIGTERM/SIGINT/SIGHUP with `-Xrs` | default action: killed by signal; shell `$?` = 128+N | documented (`java` manual) + OS semantics |
| `kill -KILL` (SIGKILL) | killed by signal 9; shell `$?` = 137 | OS behavior |
| Hook deadlock (hook calls `System.exit`) | shutdown never finishes; process must be `halt`ed or signaled | documented |

---

## 2. Standard-Library and Runtime API Inventory (LG-JA-002)

All signatures verified against the JDK 21 Javadoc pages cited in the ledger. The documented *supported* way to react to signals is shutdown hooks only — there is no public signal-handling API. (`sun.misc.Signal` was never a supported API; today's `jdk.internal.misc.Signal` is not accessible — see §4.4.)

### Termination

| API | Verified signature | Key semantics |
|---|---|---|
| `System.exit` | `public static void exit(int status)` | Initiates shutdown sequence; blocks indefinitely; never returns/throws (modulo `SecurityException`); nonzero = abnormal by convention |
| `Runtime.exit` | `public void exit(int status)` | As above; serialized; self-deadlock if called from a hook |
| `Runtime.halt` | `public void halt(int status)` | Immediate termination; no hooks; no shutdown sequence |
| `Runtime.addShutdownHook` | `public void addShutdownHook(Thread hook)` | Throws `IllegalArgumentException` (duplicate/running/run), `IllegalStateException` (sequence begun), `SecurityException` |
| `Runtime.removeShutdownHook` | `public boolean removeShutdownHook(Thread hook)` | `false` if not registered; `IllegalStateException` after sequence begun |
| `Thread.setDefaultUncaughtExceptionHandler` | `public static void setDefaultUncaughtExceptionHandler(Thread.UncaughtExceptionHandler ueh)` | Consulted last (thread → group → default); `null` removes |

### Process creation and control

| API | Verified signature | Key semantics |
|---|---|---|
| `ProcessBuilder.command` | `ProcessBuilder command(List<String> command)` / `command(String... command)` | "This method does not make a copy of the command list"; validity not checked here |
| `ProcessBuilder.directory` | `ProcessBuilder directory(File directory)` | `null` = inherit current working dir (`user.dir`) |
| `ProcessBuilder.environment` | `Map<String,String> environment()` | "initialized to a copy of the current process environment"; map edits go to the child; independent per builder; no null keys/values |
| `ProcessBuilder.redirectInput/Output/Error` | `ProcessBuilder redirectX(ProcessBuilder.Redirect r)` (+ `File` and path convenience overloads) | `Redirect.PIPE` (default), `Redirect.INHERIT`, `Redirect.READ`, `Redirect.WRITE`, `Redirect.appendTo`; non-PIPE ⇒ corresponding `Process` stream returns null |
| `ProcessBuilder.inheritIO` | `ProcessBuilder inheritIO()` | All three streams inherited from parent |
| `ProcessBuilder.redirectErrorStream` | `ProcessBuilder redirectErrorStream(boolean)` | Merge stderr into stdout (stderr stream then null) |
| `ProcessBuilder.start` | `Process start() throws IOException` | Validates command; throws `IOException` subclass on failure; `UnsupportedOperationException` if OS can't spawn; later builder edits don't affect the started process |
| `ProcessBuilder.startPipeline` | `static List<Process> startPipeline(List<ProcessBuilder> builders)` | Pipe each process's output into the next |
| `Process.getInputStream` | `abstract InputStream getInputStream()` | Connected to child stdout; **null if redirected** |
| `Process.getErrorStream` | `abstract InputStream getErrorStream()` | Connected to child stderr; null if redirected/merged |
| `Process.getOutputStream` | `abstract OutputStream getOutputStream()` | Connected to child stdin; null if `redirectInput` set |
| `Process.waitFor` | `int waitFor() throws InterruptedException` | Blocks until exit; returns exit value |
| `Process.waitFor` | `boolean waitFor(long timeout, TimeUnit unit) throws InterruptedException` | `true` if exited, `false` if time elapsed; default impl "polls the exitValue"; the child keeps running on timeout |
| `Process.exitValue` | `int exitValue()` | Throws `IllegalThreadStateException` if still running |
| `Process.destroy` | `void destroy()` | "Kills the process. Whether the process … is normally terminated or not is implementation dependent" — on POSIX this sends SIGTERM |
| `Process.destroyForcibly` | `Process destroyForcibly()` | Forcible kill — on POSIX SIGKILL; "isAlive() may return true for a brief period" after |
| `Process.isAlive` | `boolean isAlive()` | `true` until terminated |
| `Process.pid` | `long pid()` (9+) | Native process id |
| `Process.onExit` | `CompletableFuture<Process> onExit()` (9+) | Completes on termination regardless of status; "Cancelling the CompletableFuture does not affect the Process" |
| `Process.toHandle` | `ProcessHandle toHandle()` (9+) | Throws `UnsupportedOperationException` on bare `Process` subclasses |
| `ProcessHandle.of` | `static Optional<ProcessHandle> of(long pid)` | Handle for an existing OS process |
| `ProcessHandle.current` | `static ProcessHandle current()` | This process |
| `ProcessHandle.pid` | `long pid()` | Native pid |
| `ProcessHandle.info` | `Info info()` | Snapshot (command, args, start time, user) — availability platform-dependent |
| `ProcessHandle.children` | `Stream<ProcessHandle> children()` | Direct children snapshot |
| `ProcessHandle.descendants` | `Stream<ProcessHandle> descendants()` | "children of the process plus the descendants of those children, recursively" |
| `ProcessHandle.allProcesses` | `static Stream<ProcessHandle> allProcesses()` | Snapshot of all visible processes |
| `ProcessHandle.onExit` | `CompletableFuture<ProcessHandle> onExit()` | Completes when the process terminates |
| `ProcessHandle.destroy / destroyForcibly` | `boolean destroy()` / `ProcessHandle destroyForcibly()` | As `Process` counterparts; OS access controls may prevent the kill |

`Process` also offers Java 17+ character-stream bridges (`inputReader()`, `outputWriter()`, `errorReader()`), documented with the warning that "The BufferedReader may have buffered input from the input stream" — mixing byte and char APIs on the same stream can strand bytes in the buffer.

### 2.1 `Runtime.exec` variants (legacy surface, for completeness)

The `Runtime` class documents the full legacy process-creation family:

```text
Process exec(String command)                       // deprecated: tokenizes on whitespace
Process exec(String[] cmdarray)
Process exec(String[] cmdarray, String[] envp)
Process exec(String[] cmdarray, String[] envp, File dir)
Process exec(String command, String[] envp)        // deprecated
Process exec(String command, String[] envp, File dir) // deprecated
```

The `String[]` overloads are not deprecated; they delegate to the `ProcessBuilder` machinery internally and return `Process` objects with the same semantics as §5. The environment argument replaces the child's environment entirely (`null` inherits). Prefer `ProcessBuilder`: it exposes redirections, working directory, and `startPipeline`, which `Runtime.exec` cannot express.

---

## 3. Process Lifecycle and Termination (LG-JA-003)

**Creation.** The `java` launcher creates the JVM, initializes signal handlers (unless `-Xrs`), and invokes `main` on a non-daemon thread. Embedded JVMs (`JNI_CreateJavaVM`) follow the same shutdown rules via `DestroyJavaVM`.

**Normal termination.** `main` returns → the main thread dies. The shutdown sequence begins only when *all* non-daemon threads have died (or `System.exit` was called): hooks run (unspecified order), then the JVM terminates with the status from `exit` (0 for the thread-exhaustion path, reference implementation).

**Explicit termination.** `System.exit(status)` for orderly exit with a chosen status; `Runtime.halt(status)` to skip everything.

**Abnormal termination.** Uncaught exception from `main` → launcher exits 1 (implementation behavior). Signal → hooks run first (JVM-installed handlers), then the process exits; with `-Xrs` or SIGKILL the kernel terminates the process directly. Note that in the signal-triggered case the *status* the parent observes is again not covered by the specification — see the table in §1.7.

**Process vs thread vs child.** `Thread.stop` is long gone; you cannot terminate another thread safely — cooperative interruption (`Thread.interrupt`) is the model, and at JVM termination all threads just stop. Child processes are OS processes controlled through `Process`/`ProcessHandle`; they are unaffected by JVM termination unless you kill them yourself (hooks are the sanctioned place).

---

## 4. Signals and OS Interaction (LG-JA-004)

### 4.1 What the JVM installs

On Linux the HotSpot JVM installs handlers for **SIGHUP, SIGINT, SIGTERM** to run shutdown hooks (verified `java` manual quote in §1.3) and handles additional signals internally (e.g. SIGQUIT for thread dumps — the manual ties `-Xrs`'s "signal masks … aren't changed" list to SIGHUP/SIGINT/SIGTERM/SIGQUIT). When such a signal arrives, the documented behavior is: the shutdown sequence begins, hooks run, JVM terminates. The exit status is *not* specified in the JDK documentation; on Linux HotSpot the observed result is 128+signal (e.g. 143 after SIGTERM) once hooks complete — **implementation behavior, stated as such**.

### 4.2 The supported API surface: hooks only

The platform deliberately exposes no public signal API. The `java` manual's `-Xrs` description frames signal handling as JVM-internal; the supported way to observe SIGINT/SIGTERM/SIGHUP is `Runtime.addShutdownHook`. Consequences:

- You cannot distinguish *which* signal triggered the shutdown from public API (no signal number is passed to hooks).
- You cannot ignore or re-dispose arbitrary signals from supported Java code.
- Uncatchable signals (SIGKILL, SIGSTOP) bypass hooks entirely (kernel semantics).

### 4.3 `-Xrs` and embedding

`-Xrs` ("reduce signals") is documented as the answer for embedders: "Applications embedding the JVM frequently need to trap signals such as SIGINT or SIGTERM, which can lead to interference with the JVM signal handlers." With `-Xrs`, the JVM neither installs handlers for nor masks SIGHUP/SIGINT/SIGTERM/SIGQUIT — signals keep their kernel defaults, and shutdown hooks for unexpected termination no longer run. `System.exit`-initiated shutdown still works normally (hooks still run for that path).

### 4.4 Non-public signal APIs (limitation, documented as such)

`sun.misc.Signal` (historic) was never supported and is inaccessible under the module system; `jdk.internal.misc.Signal` remains internal (`jdk.unsupported`-adjacent, not exported API). Any program doing more than hooks with signals is using non-portable internals — mark such code as relying on implementation behavior. **No supported public signal API exists in JDK 21** — this is a documented platform limitation, not a gap in this chapter.

### 4.5 Threads, masking, async-safety

Java exposes no `sigprocmask`/`sigwait` equivalents; masking is JVM-internal. Handler → application communication is impossible in the POSIX sense; the sanctioned pattern is: hook thread performs ordinary (Java-level, thread-safe) cleanup. Hook code runs on its own hook thread — it is *not* a POSIX async-signal-safe context, but it *is* a fragile shutdown context (other services may already be dead; see the API Note in §1.3).

### 4.6 The Windows parallel (design symmetry, for orientation)

The `java` manual documents the same hook mechanism on Windows via console events: "the JVM watches for console control events … the JVM registers a console control handler that begins shutdown-hook processing and returns TRUE for CTRL_C_EVENT, CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, and CTRL_SHUTDOWN_EVENT. The JVM uses a similar mechanism to implement the feature of dumping thread stacks … The JVM uses CTRL_BREAK_EVENT to perform thread dumps." With `-Xrs` on Windows, "the JVM doesn't install any console control handler." The design point for a Linux reader: in every case the JVM mediates OS asynchronous termination into the single supported callback (hooks) or into nothing (`-Xrs`).

---

## 5. Subprocess and Child-Process Management (LG-JA-005)

### 5.1 Creation

```java
Process p = new ProcessBuilder("ls", "-l", dir)   // argument array — no shell
        .directory(workDir)
        .redirectErrorStream(true)
        .start();
```

`start()` performs the platform `fork`/`exec` equivalent with the builder's command (argument list — no shell involved, so no quoting/injection layer exists at all), `directory()`, and `environment()`. Documented failure modes throw `IOException` subclasses ("The operating system program file was not found. / Access to the program file was denied. / The working directory does not exist. / Invalid character in command argument, such as NUL."). `startPipeline` builds shell-free pipelines:

```java
List<Process> pipeline = ProcessBuilder.startPipeline(List.of(
        new ProcessBuilder("cat", "access.log"),
        new ProcessBuilder("grep", "404"),
        new ProcessBuilder("wc", "-l")));
Process last = pipeline.get(pipeline.size() - 1);
try (BufferedReader r = last.inputReader()) {   // Java 17+ reader API
    System.out.println("404 lines: " + r.readLine());
}
```

`Runtime` also exposes the legacy `exec` family. The `exec(String)` overload is deprecated in JDK 21 with the documented rationale: "This method is error-prone and should not be used, the corresponding method `exec(String[])` or `ProcessBuilder` should be used instead" — string tokenization silently corrupts arguments containing spaces. Prefer `ProcessBuilder` throughout.

### 5.2 Streams and the documented deadlock hazard

The `Process` class doc, quoted verbatim:

> "By default, the created process does not have its own terminal or console. All its standard I/O (i.e. stdin, stdout, stderr) operations will be redirected to the parent process, where they can be accessed via the streams obtained using the methods getOutputStream(), getInputStream(), and getErrorStream(). … Because some native platforms only provide limited buffer size for standard input and output streams, failure to promptly write the input stream or read the output stream of the process may cause the process to block, or even deadlock."

Concretely: with `Redirect.PIPE` (default), failing to drain stdout while the child writes more than the pipe buffer ⇒ child blocks in `write(2)`; failing to read your own `getInputStream` while also reading stderr separately is the classic two-pipe deadlock — drain both (two threads, or `redirectErrorStream(true)` to merge, or redirect to files).

`Redirect` subtypes and their meaning (all documented in `ProcessBuilder.Redirect`):

| Redirect | Child-side effect | Parent-side stream |
|---|---|---|
| `Redirect.PIPE` (default) | connected to a pipe | `getInputStream()`/`getErrorStream()`/`getOutputStream()` return live streams |
| `Redirect.INHERIT` | inherits parent's stdio | corresponding `Process` stream returns `null` |
| `Redirect.from(File)` (READ) | child's stdin read from file | `getOutputStream()` returns `null` |
| `Redirect.to(File)` (WRITE) | child's stdout written to file (truncate) | `getInputStream()` returns `null` |
| `Redirect.appendTo(File)` | appended | `getInputStream()` returns `null` |

### 5.3 Waiting, polling, termination, status

```java
Process p = pb.start();
if (!p.waitFor(30, TimeUnit.SECONDS)) {      // false = still running
    p.destroy();                              // SIGTERM on POSIX
    if (!p.waitFor(5, TimeUnit.SECONDS)) {
        p.destroyForcibly().waitFor();        // SIGKILL on POSIX
    }
    throw new TimeoutException("child hung");
}
int code = p.exitValue();                     // legal only after termination
```

- `waitFor()` / `waitFor(timeout, unit)`: interruption while waiting throws `InterruptedException` (the wait ends; the child keeps running).
- `exitValue()` throws `IllegalThreadStateException` if the process has not terminated.
- `destroy()` sends SIGTERM on POSIX ("normal termination allows the process to shut down cleanly" — the Javadoc phrase; whether it is graceful is implementation dependent, and `supportsNormalTermination()` reports which your platform does).
- `destroyForcibly()` sends SIGKILL on POSIX; `isAlive()` "may return true for a brief period" afterward (documented API note).
- `onExit()` (Java 9+) returns `CompletableFuture<Process>`; composition example documented in the API notes: `p.onExit().thenApply(...)` for asynchronous waits without a blocked thread.
- `ProcessHandle.Info` gives post-hoc diagnostics (availability platform-dependent): `info.command()`, `info.arguments()`, `info.startInstant()`, `info.user()` — all `Optional`-returning snapshots, not live data.
- `ProcessHandle.allProcesses()` + `info()` is the documented snapshot API for "what is running" — the platform-level answer before reaching for `ps`.

```java
Process p = new ProcessBuilder("long-job").start();
p.onExit().thenRun(() -> System.out.println("done, code=" + p.exitValue()));
// ... other work runs concurrently ...
```

### 5.4 Exit-status representation, signal death (verification result)

The JDK 21 `Process.exitValue`/`waitFor` docs say only: "the exit value of the process … By convention, the value 0 indicates normal termination." **No JDK documentation defines the value returned when the child was killed by a signal.** Verification result:

- Observed reference-implementation behavior on Linux (HotSpot `java.lang.ProcessImpl` reading the raw `waitpid` status): a child killed by signal N is reported as **128+N** (e.g. 143 for SIGTERM, 137 for SIGKILL).
- This is **implementation behavior** — do not write code that depends on it; treat any non-zero/abnormal result portably and use `ProcessHandle.Info`/platform checks if signal-death diagnostics matter. (Contrast: Python's `subprocess` *does* document `-N`; Node.js *does* document `(code, signal)` nullability — Java is the outlier with neither.)

### 5.5 ProcessHandle: trees, trees of zombies, cleanup

```java
// Documented use of descendants: kill a whole tree
ProcessHandle tree = ProcessHandle.of(pid).orElseThrow();
tree.descendants().forEach(ProcessHandle::destroy);  // SIGTERM the subtree
tree.destroy();                                       // then the root
```

`descendants()` is a *snapshot* ("processes are created and terminate asynchronously … no guarantee that a process is alive"); destroying each handle individually races with process creation — the JDK docs stop short of promising atomic tree kills, so a robust implementation re-checks `isAlive()`/`onExit()`. A `Process`/`ProcessHandle` is not a resource you must close: "The process is not killed when there are no more references to the Process object, but rather the process continues executing asynchronously" (`Process` class doc). Zombies on Linux: a child that exited but was never `waitFor`ed stays a zombie; `onExit()`/`waitFor()` reaps. Orphans: children of a dead JVM are re-parented to init — the JVM's exit does not kill them (hooks are your only chance).

### 5.6 Sync vs async, timeouts, cancellation

- Sync style: `waitFor(timeout)` loop or `onExit().get(timeout)`; async style: `onExit().thenRun(...)` — both documented.
- There is no built-in child timeout that kills automatically (unlike Python's `subprocess.run(timeout=…)`); you compose `waitFor` + `destroy` as in §5.3.
- Interruption of a thread blocked in `waitFor` is the cancellation mechanism; it does not affect the child.

---

## 6. Concurrency and Resource Semantics (LG-JA-006)

**Threads and the shutdown sequence.** New threads may be created and started *during* shutdown ("creating and starting new threads is permitted" — `Runtime` docs) and run concurrently with hooks; only termination stops everything. Starting a hook thread yourself before shutdown makes the behavior "unspecified" (documented).

**fd ownership.** Each `Process` owns pipe fds; the JDK closes the parent-side pipe ends appropriately per redirection (non-PIPE redirections make the corresponding stream return `null`). Streams obtained from `Process` should be closed by the reader/writer; because each is buffered ("It is a good idea for the returned input stream to be buffered" — implementation notes), mixing `InputStream` and reader APIs loses data (documented API note, §2).

**Races.** `environment()` returns a live map — mutating it while `start()` reads is a data race; configure builders before `start()`. `command(List)` stores the caller's list by reference ("does not make a copy") — the same hazard. `descendants()`-based tree kills race with child creation (§5.5). `exitValue` vs `waitFor` misuse throws rather than racing.

**Deadlocks.** Undrained child output (§5.2); `System.exit` from a shutdown hook (§1.2); hooks using services that have their own hooks (§1.3); large `waitFor` with unredirected stderr on two-pipe setups.

**Leaks.** A never-waited child becomes a zombie; a `ProcessBuilder` reused after `start()` starts a *new* identical process (documented: `start()` "can be invoked repeatedly") — accidental double-spawn is a classic leak of work, not of fds.

### 6.1 Misconceptions

- **"`System.exit` kills the JVM immediately."** It starts a *sequence*: hooks run first, possibly forever. Only `halt` is immediate.
- **"Hooks run in registration order."** "Some unspecified order" — documented.
- **"`finally` blocks always run."** At JVM termination they explicitly do not (documented list in §1.1). try-with-resources neither.
- **"`System.exit` from a shutdown hook is a clean way to stop hooks."** It deadlocks the shutdown sequence (documented). Use `halt`.
- **"`Process.destroy` always kills."** "Whether the process … is normally terminated or not is implementation dependent" — a stubborn child may need `destroyForcibly()`; the documented API note even warns `isAlive()` can still be `true` briefly afterwards.
- **"`waitFor` timeout kills the child."** The timeout variant returns `false` and leaves the child running — killing is your job.
- **"Java exit codes are portable across signal deaths."** The signal-death encoding is not documented at all (§5.4).

---

### Coverage ledger

Statuses: `documented` = verified against the cited JDK 21 source with signature and semantics recorded; `source-limited` = a named primary source was unreachable or silent.

| API | Canonical signature | Status | Reference |
|---|---|---|---|
| LG-JA-001 `System.exit` | `public static void exit(int status)` | documented | [System.html#exit(int)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/System.html#exit(int)) |
| LG-JA-001 `Runtime.exit` | `public void exit(int status)` | documented | [Runtime.html#exit(int)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html#exit(int)) |
| LG-JA-001 `Runtime.halt` | `public void halt(int status)` | documented | [Runtime.html#halt(int)](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html#halt(int)) |
| LG-JA-001 `addShutdownHook`/`removeShutdownHook` | `public void addShutdownHook(Thread hook)` / `public boolean removeShutdownHook(Thread hook)` | documented | [Runtime.html#addShutdownHook](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html#addShutdownHook(java.lang.Thread)) |
| LG-JA-001 shutdown-sequence trigger/termination rules | (§1.1, quoted) | documented | [Runtime.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html) |
| LG-JA-001 uncaught-exception handler chain | `Thread.setDefaultUncaughtExceptionHandler(Thread.UncaughtExceptionHandler)` | documented | [Thread.html#setDefaultUncaughtExceptionHandler](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html#setDefaultUncaughtExceptionHandler(java.lang.Thread.UncaughtExceptionHandler)) |
| LG-JA-001 exit code for `main` uncaught exception | — | source-limited (not specified in JLS/Javadoc; reference launcher behavior 1 stated as implementation behavior) | [Runtime.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html); JLS 12.8 via Runtime docs |
| LG-JA-001 finalization deprecation | JEP 421 (JDK 18) | documented | [JEP 421](https://openjdk.org/jeps/421) |
| LG-JA-002 `ProcessBuilder` full surface | command/directory/environment/redirect*/inheritIO/redirectErrorStream/start/startPipeline | documented | [ProcessBuilder.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ProcessBuilder.html) |
| LG-JA-002 `Process` full surface | waitFor×2/exitValue/destroy/destroyForcibly/isAlive/pid/onExit/toHandle/streams | documented | [Process.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Process.html) |
| LG-JA-002 `ProcessHandle` full surface | of/current/pid/info/children/descendants/allProcesses/onExit/destroy | documented | [ProcessHandle.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ProcessHandle.html) |
| LG-JA-002 stream-deadlock warning | (§5.2, quoted verbatim) | documented | [Process.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Process.html) |
| LG-JA-003 lifecycle & termination paths | (§1.7 table) | documented (impl-behavior rows marked) | as above |
| LG-JA-004 signal triggers for hooks (SIGHUP/SIGINT/SIGTERM) | — | documented | [java.html −Xrs](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) |
| LG-JA-004 `-Xrs` behavior | (§4.3, quoted) | documented | [java.html −Xrs](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) |
| LG-JA-004 public signal API | — | source-limited (documented limitation: no public API; sun.misc.Signal removed/unsupported, jdk.internal.misc.Signal internal) | [java.html](https://docs.oracle.com/en/java/javase/21/docs/specs/man/java.html) |
| LG-JA-004 JVM exit status after signal-triggered shutdown | observed 128+N on Linux HotSpot | source-limited (unspecified in JDK docs; stated as implementation behavior) | [Process.html](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Process.html) (absence verified) |
| LG-JA-005 exit-status representation on signal death (`waitFor`/`exitValue`) | — | source-limited (JDK docs silent; observed 128+N on Linux, marked implementation behavior) | [Process.html#exitValue](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Process.html#exitValue()) |
| LG-JA-005/006 concurrency, fd, buffering semantics | (§6) | documented | as above |

**Counts:** inventoried 19 rows; documented 15 (including rows marked as implementation behavior where a documented fact exists); remaining 0; source-limited 4 (all four are documented *limitations* of the platform docs — the behaviors are stated explicitly and marked implementation-specific rather than left silent).

## Related Topics

- [Python](python.md) — `subprocess` −N convention vs Java's undocumented signal-death encoding; `atexit` vs shutdown hooks.
- [Node.js](nodejs.md) — `'exit' (code, signal)` events vs `Process.waitFor`; `process.exit` vs `Runtime.halt`.
- [OCaml](ocaml.md) — `Unix.process_status` (WEXITED/WSIGNALED) as the explicit status model Java omits.
- [Signals overview](../signals/index.md) — what SIGHUP/SIGINT/SIGTERM defaults mean below the JVM.
- [Exit status conventions](../exit-status/index.md) — 128+N and the shell's view of JVM terminations.
- [Interface ledger](../interfaces/index.md) — `waitpid`, `kill`, `pipe` under `ProcessBuilder`.

## References

1. *Class System*, Java SE 21 & JDK 21 API Specification, docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/System.html (retrieved 2026-10).
2. *Class Runtime* (Shutdown Sequence, exit, halt, addShutdownHook), Java SE 21 & JDK 21, docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html (retrieved 2026-10).
3. *Class Process*, Java SE 21 & JDK 21, docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Process.html (retrieved 2026-10).
4. *Class ProcessBuilder*, Java SE 21 & JDK 21, docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ProcessBuilder.html (retrieved 2026-10).
5. *Class ProcessHandle*, Java SE 21 & JDK 21, docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ProcessHandle.html (retrieved 2026-10).
6. *Class Thread* (UncaughtExceptionHandler), Java SE 21 & JDK 21, docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html (retrieved 2026-10).
7. *java command reference — `-Xrs`*, JDK 21 specification docs, docs.oracle.com/en/java/javase/21/docs/specs/man/java.html (retrieved 2026-10).
8. *JEP 421: Deprecate Finalization for Removal*, OpenJDK, openjdk.org/jeps/421 (retrieved 2026-10).
