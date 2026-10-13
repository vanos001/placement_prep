# Java: Language Semantics, Standard Library, Process APIs, and Subprocesses

**Declared scope** (all sources retrieved **2026-10-13**): Java SE **25** — the current
Oracle JDK **LTS** (GA 2025-09). The Oracle docs portal serves both *Java SE 25 & JDK 25*
and *Java SE 26* API specifications (checked 2026-10-13); every signature below was
verified against the **JDK 25** Javadoc at `docs.oracle.com/en/java/javase/25/docs/api/...`.
Language rules cite the **JLS, SE 25** (`docs.oracle.com/javase/specs/jls/se25/`). The
implementation substrate is the **HotSpot/OpenJDK reference implementation on Linux**
(source spot-checks from the `jdk-25+36` GA tag, `github.com/openjdk/jdk`); POSIX deltas
are labeled; Windows appears only briefly.

**Layer labels:** [JLS] = normative language rule (JLS SE 25) · [JDK documented] =
normative API rule (JDK 25 Javadoc / `java` command manual / JEP) · [HotSpot
implementation] = reference-implementation behavior, **not** a portability guarantee ·
[Linux/POSIX] = OS-level behavior · [Windows delta] = Windows divergence (brief).

**Reading map.** §1 language semantics; §2 verified API inventory; §3 JVM
startup/termination; §4 signals; §5 subprocesses; §6 concurrency and resources. The
exit/signal-scoped sibling [Java: Exit Status, Signals, and Process
Lifecycle](../../linux/process-exit-signal/languages/java.md) owns the deep
termination-status tables (LG-JA-*); this chapter covers the whole six-area surface and
cross-links rather than re-derives. Cross-language subprocess comparisons live in
[go.md](./go.md) and [python.md](./python.md); the part hub is [index.md](./index.md).
Deeper JVM material out of scope here: [JVM internals](../java/jvm.md), [JVM memory
model](../java/jvm-memory-model.md), [virtual threads](../java/virtual-threads.md).

---

## 1. Syntax and Semantics

### 1.1 Declarations in one paragraph

Statically typed, class-based, garbage-collected; every value is a primitive
(`byte short int long float double char boolean`) or an object reference. Classes,
interfaces (with `default` methods), enums (fixed instances, implicitly `final`), and
records (`record R(int a, int b)`; JEP 395, *Delivered, Release 16*) are declared in
packages; `sealed` types (JEP 409, *Delivered, Release 17*) restrict implementations.
Records derive accessors/`equals`/`hashCode`/`toString` and behave like hand-written
final classes — nothing below treats them specially. Fields have default values
(`0`, `false`, `null`) until initialized; locals must be definitely assigned [JLS §4.12.5].

### 1.2 Methods and overload resolution (the part that bites)

Overload resolution [JLS §15.12.2] proceeds in **three phases**, taking the first phase
with an applicable method: (1) *strict* — no boxing, no varargs; (2) *loose* —
boxing/unboxing allowed; (3) *variable arity*. Within a phase, the *most specific*
method wins. The normative rationale: phase 1 "guarantees that any calls that were
valid … before Java SE 5.0" keep resolving identically [JLS §15.12.2].

```java
static void f(int x)      { System.out.println("int"); }
static void f(long x)     { System.out.println("long"); }
static void f(Integer x)  { System.out.println("Integer"); }
public static void main(String[] args) {
    f(1);        // Expected: int     — phase 1 (exact int); never boxes
    f((char) 1); // Expected: int     — widening char->int beats boxing char->Integer
    f(Integer.valueOf(1)); // Expected: int — unboxing is phase 2; int remains most specific
}
```

Hazards: an `f(Object)` overload changes what a bare `null` selects (most specific
reference type); boxing-phase changes can silently alter behavior across compiler
releases; overload *choice* is static — no dispatch on arguments.

### 1.3 Checked vs unchecked exceptions — the exact compile-time rule

[JLS §11.1.3], verbatim: "The unchecked exception classes are the run-time exception
classes and the error classes" — the *run-time exception classes* are "`RuntimeException`
and all its subclasses", the *error classes* "`Error` and all its subclasses". "The
checked exception classes are all exception classes other than the unchecked exception
classes. That is, the checked exception classes are `Throwable` and all its subclasses
other than `RuntimeException` and its subclasses and `Error` and its subclasses."

Compile-time consequences [JLS §11.2]:

- A `throw` of checked `E`, or a call whose target declares `throws E`, makes `E` a
  *possible result* of the statement. It is a **compile-time error** if the enclosing
  method/constructor can throw `E` and `E` is neither caught (by a handler for `E` or a
  supertype) nor declared in the `throws` clause.
- Unchecked classes are exempt everywhere; `Throwable`/`Exception` (non-runtime) are
  checked.
- `catch (E e)` for a checked `E` that cannot be thrown by the `try` block is a
  compile-time error ("exception `E` is never thrown in the corresponding try block"),
  *unless* `E` is `Exception`/`Throwable` or unchecked.
- Overrides may only narrow `throws`; reflective instantiation wraps checked failures.

```java
import java.io.IOException;
class CheckDemo {
    // void a() { throw new IOException(); }   // compile error: unreported exception
    void b() throws IOException { throw new IOException("io"); }
    void c() { try { b(); } catch (IOException e) { /* required: checked */ } }
    void d() { throw new IllegalStateException("unchecked"); } // no throws needed
    // void e() { try { } catch (IOException x) { } } // compile error: never thrown in try
}
```

Expected: `c()`/`d()` compile; the commented lines fail exactly as stated [JLS §11.2].

### 1.4 try / catch / finally — the abrupt-completion algebra

Every block *completes normally* or *abruptly with a reason* (thrown value, `return`
value, `break`/`continue` to label) [JLS §14.20.2]. The exact rules: if the `try` (or a
selected `catch`) completes abruptly for reason `R` and `finally` completes abruptly for
reason `S`, "the try statement completes abruptly for reason `S` (and reason `R` is
discarded and forgotten)". So a `return`/`throw` in `finally` silently swallows any
exception in flight and overrides `try`/`catch` return values:

```java
static int f() {
    try { throw new RuntimeException("boom"); }
    finally { return 42; }          // exception "discarded and forgotten"
}
// Expected: f() == 42; the RuntimeException never escapes.

static int g() {
    int x = 1;
    try { return x; }               // return value captured here…
    finally { x = 99; }             // …then finally runs
}
// Expected: g() == 1 — finally executes, but the returned value was already fixed.
```

"finally always runs" is a misconception at process level (§3.5); at statement level it
runs *before the completion propagates* — `System.exit`, `halt`, or an infinite loop in
`finally` prevents whatever followed.

### 1.5 try-with-resources and suppressed exceptions

[JLS §14.20.3]: resources are closed "in the reverse order from which they were
initialized"; a resource is closed only if it initialized **non-null**; "an exception
from the closing of one resource does not prevent the closing of other resources. Such
an exception is suppressed if an exception was thrown previously by an initializer, the
try block, or the closing of a resource." Since SE 25 a resource may be an existing
`final`/effectively-final variable (`VariableAccess`) or an unnamed variable `_`.
Suppressed exceptions are retrievable [JDK documented, verified
`public final Throwable[] getSuppressed()`]:

```java
class R implements AutoCloseable {
    final String name; R(String n) { name = n; }
    public void close() { System.out.println("close " + name); throw new IllegalStateException(name); }
}
static void demo() throws Exception {
    try (R a = new R("A"); R b = new R("B")) { throw new RuntimeException("body"); }
}
// Expected: "close B" then "close A" (reverse order); the RuntimeException("body")
// propagates; e.getSuppressed() == [IllegalStateException B, IllegalStateException A].
```

[JLS §14.20.3.1] translates the statement into nested try-catch-finally with a
`#primaryExc` slot; `close()` failures are attached via `addSuppressed`.
`AutoCloseable.close()` is documented as not required to be idempotent, but "implementers
are strongly encouraged to make their `close` methods idempotent" [JDK documented].

### 1.6 Autoboxing / unboxing edges

- Boxing uses `Integer.valueOf`; the cache guarantees **object identity** for `-128..127`
  (source-verified `Integer.java`, `jdk-25+36`: `static final int low = -128;` with
  `-XX:AutoBoxCacheMax=<size>` raising the bound; `valueOf` "will always cache values in
  the range -128 to 127, inclusive, and may cache other values outside of this range").

  ```java
  Integer a = 127, b = 127, c = 128, d = 128;
  System.out.println(a == b);   // Expected: true   (cached, same object)
  System.out.println(c == d);   // Expected: false  (distinct objects)
  ```

- Unboxing `null` throws `NullPointerException` [JLS §5.1.8]. The boxed conditional trap
  [JLS §15.25.2]: in `cond ? boxedExpr : intExpr` the type is `int`, so a null
  `boxedExpr` NPEs even when the `int` branch would be chosen.
- `==` on boxed numerics compares references — use `equals` or unbox explicitly.
- `i += 1` on `Integer i` unboxes, adds, reboxes (the box object is replaced).

### 1.7 Static initializers and class initialization order

[JLS §12.4.1]: class/interface `T` is initialized immediately before the first occurrence
of any of: creating an instance of `T`; invoking a static method declared by `T`;
assigning a static field declared by `T`; using a non-constant static field declared by
`T`; certain reflective calls. "When a class is initialized, its superclasses are
initialized (if they have not been previously initialized), as well as any superinterfaces
that declare any default methods." Interface initialization does **not** initialize
superinterfaces; a static-field reference initializes only the class "that actually
declares it, even though it might be referred to through the name of a subclass."
Initializers run in **textual order** [JLS §12.4.2] under the JVM's per-class init lock —
one thread initializes while others block (cyclic `<clinit>` can deadlock); an exception
in `<clinit>` becomes `ExceptionInInitializerError`, then `NoClassDefFoundError` on
subsequent use [JVMS behavior].

```java
class InitOrder {
    static int A = trace("A", 1);
    static { System.out.println("static block 1"); }
    static int B = trace("B", 2);
    static String trace(String n, int v) { System.out.println("init " + n); return "" + v; }
    public static void main(String[] args) { System.out.println(B); }
}
// Expected: init A / static block 1 / init B / 2  — textual order, before main's body.
```

### 1.8 Object lifecycle: finalization vs Cleaner (verified current status)

- `Object.finalize()` — [JDK documented, JDK 25 Javadoc, verified]:
  `@Deprecated(since="9", forRemoval=true)`, `protected void finalize() throws Throwable`,
  "Finalization is deprecated and subject to removal in a future release." **As of JDK 25
  it is still present and may still run**: "This method will remain in place until
  finalizers have been removed from most existing code."
- JEP 421 (*Deprecate Finalization for Removal*) — [JDK documented] *Delivered, Release
  18*: "Finalization remains enabled by default for now, but can be disabled to
  facilitate early testing. In a future release it will be disabled by default, and in a
  later release it will be removed." `Runtime.runFinalization()` is marked
  "Deprecated, for removal" in JDK 25 (verified); `--finalization=disabled` (JEP 421)
  makes `finalize()` never run.
- Recommended replacements [JDK documented, `Object.finalize`]: "`Use Cleaner and
  PhantomReference as safer ways to release resources when an object becomes
  unreachable. Alternatively, add a close method … and implement AutoCloseable to enable
  use of the try-with-resources statement.`"
- `java.lang.ref.Cleaner` [JDK documented, verified]: `public static Cleaner create()`
  ("creates a daemon thread to process the phantom reachable objects and to invoke
  cleaning actions"); `public Cleanable register(Object obj, Runnable action)` — action
  runs at most once when `obj` becomes phantom-reachable, unless `Cleanable.clean()` ran
  first.

**Misconceptions:** "GC guarantees finalize" — no: no promptness guarantee, may never
run, never a shutdown cleanup mechanism (§3.5). "Cleaner replaces finalize 1:1" — the
action must not capture the registered object (that keeps it reachable forever).

### 1.9 Normal vs exceptional termination of methods and threads

A method completes normally or abruptly; exception causes are exactly [JLS §11.1.2]: a
`throw` statement, an enabled failing `assert`, a JVM-detected abnormal condition
(divide by zero, linkage failure), or asynchronous VM stop. A thread terminates when its
`run` completes normally, or "completes abruptly and the relevant uncaught exception
handler completes normally or abruptly" [JLS §12.8]. Thread-level abrupt completion never
propagates to other threads — it is funneled into the uncaught-exception chain (§3.6);
process termination is a separate mechanism (§3).

### 1.10 In-scope unspecified / implementation-defined areas

- Exit status on implicit paths (main returns; uncaught exception in main): not
  specified by JLS or Javadoc; [HotSpot implementation] launcher exits 0 and 1
  (sibling chapter LG-JA-001).
- Exit status after a signal-triggered shutdown: JDK docs silent; [HotSpot
  implementation] 128+signal (§4.1).
- Value reported for a **signal-killed child** by `waitFor`/`exitValue`: JDK docs
  silent; [HotSpot implementation] 128+signal from source (§5.7).
- Which native threads pump child pipes: implementation detail, no API surface
  ([HotSpot implementation]).
- `Thread.setDaemon` "behavior … when the thread has terminated is not specified" [JDK
  documented]; `ProcessBuilder.environment()` modification support is
  "system-dependent" [JDK documented].

### 1.11 Version deltas affecting in-scope semantics

| Change | Since | In-scope effect |
|---|---|---|
| Records (JEP 395) / sealed types (JEP 409) | 16 / 17 | data carriers / restricted hierarchies |
| `Process.onExit`, `ProcessHandle`, `pid` | 9 | async process API (§5) |
| `ProcessBuilder.Redirect.DISCARD` | 9 | output → OS null file |
| `Process.inputReader/outputWriter/errorReader` | 17 | char bridges with buffered-input caveat |
| Virtual threads (JEP 444) | 21 | `Thread.ofVirtual()`; daemon by construction (§6.6) |
| `synchronized` no longer pins virtual threads (JEP 491) | 24 | monitor blocking parks instead of capturing carriers |
| `Process.waitFor(Duration)` | **24** | third `waitFor` overload (verified `Since: 24`) |
| Compact source files + instance main (JEP 512) | **25** | flexible `main` launch protocol **final** (§3.1) |
| Finalization deprecated for removal (JEP 421) | 18; still present in 25 | §1.8 |

### 1.12 Misconceptions (language level)

"finally always runs" (§1.4/§3.5) · "GC guarantees finalize" (§1.8) · "int overflow
throws" (silent wraparound) · "default methods initialize superinterfaces" (they do not,
[JLS §12.4.1]) · "checked exceptions are a runtime mechanism" (compile-time checking
only, [JLS §11.2]).

---

## 2. Standard-Library and Runtime API Inventory

All signatures **verified against the JDK 25 Javadoc** (retrieved 2026-10-13); canonical
forms copied from the Javadoc method summaries. `@since` noted where post-1.0.

### 2.1 Termination surface (`java.lang`)

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `System.exit` | `public static void exit(int status)` | "Initiates the shutdown sequence … and then blocks indefinitely. This method neither returns nor throws"; nonzero = abnormal by convention | [System.html#exit](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/System.html#exit(int)) |
| `Runtime.exit` | `public void exit(int status)` | Same sequence; "Successful invocations … are serialized"; **calling it from a hook prevents the shutdown from finishing** (documented) | [Runtime.html#exit](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html#exit(int)) |
| `Runtime.halt` | `public void halt(int status)` | "Immediately terminates … unconditional and immediate. … does not initiate the shutdown sequence" | [Runtime.html#halt](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html#halt(int)) |
| `Runtime.addShutdownHook` | `public void addShutdownHook(Thread hook)` | Registers unstarted thread; `IllegalArgumentException` (duplicate/running hook), `IllegalStateException` once sequence begun | [Runtime.html#addShutdownHook](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html#addShutdownHook(java.lang.Thread)) |
| `Runtime.removeShutdownHook` | `public boolean removeShutdownHook(Thread hook)` | `false` if not registered; `IllegalStateException` once sequence begun | [Runtime.html#removeShutdownHook](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html#removeShutdownHook(java.lang.Thread)) |
| `Runtime.getRuntime` | `public static Runtime getRuntime()` | Singleton accessor | [Runtime.html#getRuntime](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html#getRuntime()) |
| `Runtime.runFinalization` | `public void runFinalization()` | `@Deprecated(forRemoval=true)` — "Finalization has been deprecated for removal" | [Runtime.html#runFinalization](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html#runFinalization()) |

### 2.2 Thread surface in scope (`java.lang.Thread`, verified)

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `Thread.start` | `public void start()` | "Schedules this thread to begin execution"; `IllegalThreadStateException` if already started | [Thread.html#start](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#start()) |
| `Thread.join` | `public final void join(long millis) throws InterruptedException` (+ `join()`, `join(long,int)`) | Waits for death; interruptible | [Thread.html#join](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#join()) |
| `Thread.interrupt` | `public void interrupt()` | wait/sleep/join-blocked → status cleared + `InterruptedException`; `InterruptibleChannel` I/O → channel closed + `ClosedByInterruptException`; else status set | [Thread.html#interrupt](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#interrupt()) |
| `Thread.setDaemon` | `public final void setDaemon(boolean on)` | "must be invoked before the thread is started"; virtual threads are **always daemon**, cannot be made non-daemon | [Thread.html#setDaemon](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#setDaemon(boolean)) |
| `Thread.setUncaughtExceptionHandler` | `public void setUncaughtExceptionHandler(Thread.UncaughtExceptionHandler ueh)` | Per-thread handler | [Thread.html#setUncaughtExceptionHandler](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#setUncaughtExceptionHandler(java.lang.Thread.UncaughtExceptionHandler)) |
| `Thread.setDefaultUncaughtExceptionHandler` | `public static void setDefaultUncaughtExceptionHandler(Thread.UncaughtExceptionHandler ueh)` | Consulted after thread-specific handler and ThreadGroup | [Thread.html#setDefaultUncaughtExceptionHandler](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#setDefaultUncaughtExceptionHandler(java.lang.Thread.UncaughtExceptionHandler)) |
| `Thread.getUncaughtExceptionHandler` | `public Thread.UncaughtExceptionHandler getUncaughtExceptionHandler()` | "If this thread has not had an uncaught exception handler explicitly set then this thread's ThreadGroup object is returned" | [Thread.html#getUncaughtExceptionHandler](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#getUncaughtExceptionHandler()) |
| `Thread.UncaughtExceptionHandler` | `void uncaughtException(Thread t, Throwable e)` | Functional interface; "If a thread has not had its UncaughtExceptionHandler explicitly set, then its ThreadGroup object acts as its UncaughtExceptionHandler" and may forward to the default handler | [Thread.UncaughtExceptionHandler.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.UncaughtExceptionHandler.html) |
| `Thread.ofVirtual` / `isVirtual` | `public static Thread.Builder.OfVirtual ofVirtual()` / `public final boolean isVirtual()` | Virtual-thread builder / predicate (21) | [Thread.html#ofVirtual](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html#ofVirtual()) |

### 2.3 ProcessBuilder (verified, JDK 25)

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| ctor | `public ProcessBuilder(List<String> command)` | "does not make a copy of the command list. Subsequent updates to the list will be reflected"; validity not checked here | [ProcessBuilder.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ProcessBuilder.html) |
| ctor | `public ProcessBuilder(String... command)` | Convenience varargs ctor | as above |
| `command` | `public ProcessBuilder command(List<String> command)` / `public ProcessBuilder command(String... command)` | Sets program+args; getter `command()` returns the live list | as above |
| `directory` | `public ProcessBuilder directory(File directory)` | Working dir; `null` = inherit current (`user.dir`) | as above |
| `environment` | `public Map<String,String> environment()` | "initialized to a copy of the current process environment"; modifications visible to `start()`ed children; builders independent; no null keys/values; system-dependent modification support | as above |
| `redirectInput` | `public ProcessBuilder redirectInput(ProcessBuilder.Redirect source)` (+ `redirectInput(File)`) | Sets stdin source; getter `redirectInput()` | as above |
| `redirectOutput` | `public ProcessBuilder redirectOutput(ProcessBuilder.Redirect destination)` (+ `redirectOutput(File)`) | Sets stdout destination | as above |
| `redirectError` | `public ProcessBuilder redirectError(ProcessBuilder.Redirect destination)` (+ `redirectError(File)`) | Sets stderr destination | as above |
| `redirectErrorStream` | `public ProcessBuilder redirectErrorStream(boolean redirectErrorStream)` | Merges stderr into stdout; the stderr stream then returns `null` | as above |
| `inheritIO` | `public ProcessBuilder inheritIO()` | All three std streams → same as current Java process | as above |
| `start` | `public Process start() throws IOException` | Spawns; `IOException` subclass on exec failure (program not found / access denied / bad dir / NUL in argument) | as above |
| `startPipeline` | `public static List<Process> startPipeline(List<ProcessBuilder> builders)` | Starts each builder, piping stdout→stdin of the next | as above |

### 2.4 `Redirect` (`ProcessBuilder.Redirect`, verified)

| API | Canonical signature | Semantics | Reference |
|---|---|---|---|
| `Redirect.PIPE` | `public static final ProcessBuilder.Redirect PIPE` | Default; child stream ↔ pipe; live `Process` streams | [Redirect.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ProcessBuilder.Redirect.html) |
| `Redirect.INHERIT` | `public static final ProcessBuilder.Redirect INHERIT` | Child inherits parent stdio; corresponding `Process` stream returns `null` | as above |
| `Redirect.DISCARD` | `public static final ProcessBuilder.Redirect DISCARD` (@since 9) | "output will be discarded … by writing to an operating system specific 'null file'"; `type()==WRITE` | as above |
| `Redirect.from` / `to` / `appendTo` | `public static ProcessBuilder.Redirect from(File file)` / `to(File file)` / `appendTo(File file)` | `type()` = READ / WRITE ("previous contents will be discarded") / APPEND_TO | as above |
| `type` / `file` | `public abstract ProcessBuilder.Redirect.Type type()` / `public File file()` | Discriminator / associated file or `null` | as above |

### 2.5 `Process` (abstract class, verified, JDK 25)

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `getInputStream` | `public abstract InputStream getInputStream()` | Child stdout; `null` if redirected away (INHERIT/WRITE/APPEND_TO/DISCARD or merged) | [Process.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Process.html) |
| `getErrorStream` | `public abstract InputStream getErrorStream()` | Child stderr; `null` if redirected/merged | as above |
| `getOutputStream` | `public abstract OutputStream getOutputStream()` | Child stdin; `null` if stdin redirected | as above |
| `waitFor` | `public abstract int waitFor() throws InterruptedException` | Blocks until exit; returns exit value | as above |
| `waitFor` | `public boolean waitFor(long timeout, TimeUnit unit) throws InterruptedException` | `true`=exited, `false`=timeout; default impl "polls the exitValue"; **child not killed on timeout** | as above |
| `waitFor` | `public boolean waitFor(Duration duration) throws InterruptedException` | **@since 24**; NPE on null duration | as above |
| `exitValue` | `public abstract int exitValue()` | `IllegalThreadStateException` if not terminated | as above |
| `destroy` | `public abstract void destroy()` | "Kills the process. Whether the process … is normally terminated or not is implementation dependent"; no action if not alive | as above |
| `destroyForcibly` | `public Process destroyForcibly()` | Forcible kill; API Note: "isAlive() may return true for a brief period" after | as above |
| `isAlive` | `public boolean isAlive()` | `true` until terminated | as above |
| `pid` / `toHandle` | `public long pid()` / `public ProcessHandle toHandle()` | @since 9; `toHandle` may throw `UnsupportedOperationException` on bare `Process` subclasses | as above |
| `onExit` | `public CompletableFuture<Process> onExit()` | @since 9; completed on termination regardless of status; "Cancelling the CompletableFuture does not affect the Process" | as above |
| `info` / `children` / `descendants` | `public ProcessHandle.Info info()` / `public Stream<ProcessHandle> children()` / `public Stream<ProcessHandle> descendants()` | @since 9; delegations to `toHandle()` | as above |
| `supportsNormalTermination` | `public boolean supportsNormalTermination()` | `true` if `destroy()` normally terminates | as above |
| `inputReader` / `outputWriter` / `errorReader` | `final BufferedReader inputReader()` / `final BufferedWriter outputWriter()` / `final BufferedReader errorReader()` | @since 17; documented caution: reader may hold buffered bytes | as above |

Class-documentation contract, verbatim [JDK documented, `Process`]: "Because some native
platforms only provide limited buffer size for standard input and output streams, failure
to promptly write the input stream or read the output stream of the process may cause the
process to block, or even deadlock." And: "There is no requirement that the process
represented by a `Process` object execute asynchronously or concurrently with respect to
the Java process that owns the `Process` object."

### 2.6 `ProcessHandle` and `ProcessHandle.Info` (verified, JDK 25)

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `ProcessHandle.current` / `of` | `public static ProcessHandle current()` / `public static Optional<ProcessHandle> of(long pid)` | This process / handle for existing pid (empty if none) | [ProcessHandle.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ProcessHandle.html) |
| `pid` / `parent` | `public long pid()` / `public Optional<ProcessHandle> parent()` | Native pid / parent snapshot (empty if none) | as above |
| `children` / `descendants` | `public Stream<ProcessHandle> children()` / `public Stream<ProcessHandle> descendants()` | "a snapshot of the current direct children" / direct children + recursive descendants (snapshot) | as above |
| `allProcesses` | `public static Stream<ProcessHandle> allProcesses()` | Snapshot of all visible processes | as above |
| `info` | `public ProcessHandle.Info info()` | Snapshot; availability platform-dependent | as above |
| `onExit` | `public CompletableFuture<ProcessHandle> onExit()` | Completed on termination | as above |
| `destroy` / `destroyForcibly` | `public boolean destroy()` / `public boolean destroyForcibly()` | "Requests the process to be killed"; `false` on failure (e.g. permission) | as above |
| `isAlive` / `supportsNormalTermination` / `compareTo` / `equals` | `public boolean isAlive()` / `public boolean supportsNormalTermination()` / `public int compareTo(ProcessHandle other)` / `public boolean equals(Object other)` | equals: same implementation + same system process | as above |
| `Info.command` / `arguments` | `Optional<String> command()` / `Optional<String[]> arguments()` | Executable pathname / arguments (may be unavailable) | [ProcessHandle.Info.html](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ProcessHandle.Info.html) |
| `Info.commandLine` | `Optional<String> commandLine()` | command + arguments joined ("may be truncated" on some platforms) | as above |
| `Info.startInstant` / `totalCpuDuration` / `user` | `Optional<Instant> startInstant()` / `Optional<Duration> totalCpuDuration()` / `Optional<String> user()` | Start time / accumulated CPU / owner | as above |

### 2.7 Concurrency / cleanup surfaces (verified)

| API | Canonical signature | Semantics / notes | Reference |
|---|---|---|---|
| `CompletableFuture.allOf` | `public static CompletableFuture<Void> allOf(CompletableFuture<?>... cfs)` | Completed when all complete; any exceptional completion → `CompletionException` with that cause | [CompletableFuture.html#allOf](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/CompletableFuture.html#allOf(java.util.concurrent.CompletableFuture...)) |
| `CompletableFuture.get` / `join` | `public T get() throws InterruptedException, ExecutionException` / `public T join()` | Checked vs unchecked completion | [CompletableFuture.html#get](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/CompletableFuture.html#get()) |
| `Cleaner.create` / `register` | `public static Cleaner create()` / `public Cleanable register(Object obj, Runnable action)` | Daemon cleaning thread / at-most-once phantom-reachability action | [Cleaner.html#register](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ref/Cleaner.html#register(java.lang.Object,java.lang.Runnable)) |
| `Throwable.getSuppressed` | `public final Throwable[] getSuppressed()` | Suppressed exceptions from try-with-resources | [Throwable.html#getSuppressed](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Throwable.html#getSuppressed()) |

### 2.8 `Runtime.exec` (legacy, for completeness)

`Runtime.exec(String)` and the `envp` overloads are `@Deprecated` in JDK 25 — "This
method is error-prone and should not be used, the corresponding method `exec(String[])`
or `ProcessBuilder` should be used instead" (the `String` form tokenizes on whitespace).
The `String[]` overloads delegate to the same machinery as `ProcessBuilder.start()` and
return `Process` objects with identical semantics, but cannot express redirections or
`startPipeline`. Prefer `ProcessBuilder` (§5).

---

## 3. Process Creation and Termination

### 3.1 JVM startup and the `main` rules

The `java` launcher "starts a Java application … by starting the Java Virtual Machine
(JVM), loading the specified class, and calling that class's `main()` method"; the
classic protocol: "The method must be declared public and static, it must not return any
value, and it must accept a String array as a parameter" — `public static void main(String[] args)` [JDK documented, `java` command manual].

**Flexible main is final in JDK 25** — JEP 512 (*Compact Source Files and Instance Main
Methods*), status *Closed / Delivered, Release 25* (verified). The launch protocol
selects, for the specified class, in order [JEP 512]: (1) a `main` with a `String[]`
parameter (chosen even if a no-arg candidate exists); (2) otherwise a no-arg `main`
(static); (3) otherwise an **instance main method** — the class "must have a
non-private no-args constructor and then invokes the chosen main method of the resulting
instance". A *compact source file* (implicitly declared class) "must have a launchable
main method; if it does not, a compile-time error occurs". In source-file mode (`java
Foo.java`) the first top-level class must still declare "an entry `main` method", and
compile errors make "the launcher exit with a non-zero exit code" [JDK documented].

Startup order relevant here: JVM initializes → main class resolved → class
initialization (§1.7) → `main` runs on a **non-daemon** thread.

### 3.2 Return from `main`

`main` returning simply ends the main thread. The JVM does **not** exit until "all of
its non-daemon threads have terminated" [JLS §12.8]; then the shutdown sequence runs
(hooks) and the JVM terminates. The **status code** on this path is not specified by JLS
or Javadoc; [HotSpot implementation] observed exit status **0** (sibling chapter §1.7).
To choose a status on the natural-exit path, call `System.exit(n)` before the last
non-daemon thread dies.

### 3.3 `System.exit(status)` / `Runtime.exit(status)` — the full documented sequence

[JDK documented, `Runtime` class description]: the shutdown sequence initiates on
(1) "when the number of live non-daemon threads drops to zero for the first time";
(2) "when the `Runtime.exit` or `System.exit` method is called for the first time"; or
(3) "when some external event occurs, such as an interrupt or a signal is received from
the operating system." Then: "At the beginning of the shutdown sequence, the registered
shutdown hooks are **started in some unspecified order**. They run concurrently with any
daemon or non-daemon threads that were alive at the beginning of the shutdown sequence."
"After the shutdown sequence has begun, registration and de-registration of shutdown
hooks … is prohibited" (`IllegalStateException`); creating and starting *ordinary* new
threads during shutdown is permitted. "The shutdown sequence finishes when all shutdown
hooks have terminated. At this point, the Java Virtual Machine terminates." A hook that
never terminates ("for example, because of an infinite loop") means "the shutdown
sequence will never finish" — only `halt` or an external kill ends it. **When the JVM
terminates**: "all threads are immediately prevented from executing any further Java
code … threads' current methods do not complete normally or abruptly; **finally clauses
are not executed**; **uncaught exception handlers are not run**; and **resources opened
with try-with-resources are not closed**."

`System.exit(n)` ≡ `Runtime.getRuntime().exit(n)` (the "conventional and convenient
means", per the Javadoc). `Runtime.exit` specifics: invocations are serialized; all but
the first "perform no action and block indefinitely"; and — the documented trap — "if it
is invoked from a shutdown hook, it will prevent that shutdown hook from terminating.
Consequently, this will prevent the shutdown sequence from finishing." Use `halt` *from*
a hook that must stop.

```java
public class ExitDemo {
    public static void main(String[] args) {
        Runtime.getRuntime().addShutdownHook(new Thread(() ->
            System.out.println("hook: flushing logs")));
        System.out.println("work");
        System.exit(3);      // hooks run, then JVM terminates with 3
        // unreachable: exit() neither returns nor throws
    }
}
// Expected stdout: "work", then "hook: flushing logs";  $ echo $?  -> 3
```

### 3.4 `Runtime.halt(status)`

"Immediately terminates the Java Virtual Machine … termination is unconditional and
immediate. This method does not initiate the shutdown sequence, nor does it wait for the
shutdown sequence to finish if it is already in progress" [JDK documented]. No hooks, no
flushes, no `finally` — the OS process ends with the given status. The only sanctioned
way out of a stuck shutdown sequence, and the counterpart of `_exit(2)` [Linux/POSIX].

### 3.5 Shutdown hooks — the complete documented rules

From `Runtime.addShutdownHook` / class description [JDK documented]:

- A hook is "simply an initialized but unstarted thread", started at the beginning of
  the shutdown sequence, in unspecified order.
- Uncaught exceptions in hooks "are handled in shutdown hooks just as in any other
  thread, as specified in `Thread.UncaughtExceptionHandler`. After the uncaught exception
  handler has completed, the shutdown hook is considered to have terminated and is not
  treated differently from a hook that has terminated without having thrown an uncaught
  exception." A throwing hook **does not block or fail the shutdown** — but its
  incomplete cleanup is your bug.
- API Note (key clauses verbatim): "Shutdown hooks … should therefore be coded
  defensively. They should, in particular, be written to be **thread-safe** and to avoid
  deadlocks insofar as possible. They should also not rely blindly upon services that may
  have registered their own shutdown hooks and therefore may be in the process of
  shutting down. … Shutdown hooks should also finish their work quickly."
- Same hook registered twice → `IllegalArgumentException`; starting the hook thread
  yourself before shutdown → documented as unspecified behavior.
- Daemons never *prevent* shutdown; at JVM termination they are cut off like everyone
  else (no `finally`, no uncaught handlers).
- **Not a finalizer substitute**: at termination try-with-resources close and
  `finalize()` do not run (§3.3, §1.8) — hooks are the only guaranteed application
  callback on JVM exit paths (except `halt`/SIGKILL, §3.8).

### 3.6 Uncaught exceptions

The handler chain [JDK documented, `Thread.UncaughtExceptionHandler`]: "When a thread is
about to terminate due to an uncaught exception the Java Virtual Machine will query the
thread for its `UncaughtExceptionHandler` using `Thread.getUncaughtExceptionHandler()`
and will invoke the handler's `uncaughtException` method." `getUncaughtExceptionHandler`
returns the thread-specific handler or "this thread's `ThreadGroup` object"; the
ThreadGroup "can forward the invocation to the default uncaught exception handler"
(`Thread.getDefaultUncaughtExceptionHandler`). Default behavior (nothing installed): the
reference implementation prints the stack trace to `System.err` and the thread dies
[HotSpot implementation].

- **Thread death ≠ process death**: if other non-daemon threads remain, the JVM keeps
  running [JLS §12.8]. The documented pattern for "any thread's death is fatal": call
  `System.exit` yourself from the installed handler.
- **Uncaught exception in `main`**: main thread dies; if it was the last non-daemon
  thread, the shutdown sequence runs and the JVM exits. Status: not specified;
  [HotSpot implementation] launcher exits **1** with the trace on stderr (sibling
  chapter table).
- In a **shutdown hook** the same chain applies and the hook then counts as terminated
  (§3.5).

```java
public class UEDemo {
    public static void main(String[] args) throws Exception {
        Thread.setDefaultUncaughtExceptionHandler((t, e) -> {
            System.err.println("fatal in " + t.getName());
            System.exit(70);                  // convert thread death into a chosen status
        });
        new Thread(() -> { throw new IllegalStateException("worker died"); }, "w").start();
        Thread.sleep(200);
        System.out.println("reached only if the handler did not exit");
    }
}
// Expected stderr: "fatal in w";  $ echo $?  -> 70
```

### 3.7 Current process vs thread vs child process

**Thread** termination (`run` ends, honored interrupt, uncaught exception) never by
itself ends the process unless it was the last non-daemon thread (§3.6). The **current
process** ends only through the JLS §12.8 doors: all non-daemon threads ended (+hooks);
`System.exit`/`Runtime.exit` (+hooks); `Runtime.halt` (no hooks); or an external event
"recognized … as requesting termination" (signal — hooks if the JVM mediates it, §4) —
plus the undocumented door SIGKILL (kernel action, no Java code runs). A **child
process** (§5) is an OS process outside the JVM: JVM termination does not kill children —
they are re-parented (to init/systemd on Linux) and keep running; killing them on the way
out is the application's job in a hook.

### 3.8 Per-path termination table (what actually runs)

| Path | Hooks? | `finally` / TWR close? | Finalizers / Cleaner? | Status parent sees | Layer |
|---|---|---|---|---|---|
| `main` returns, last non-daemon ends | yes (unspecified order) | yes, during normal execution | not guaranteed (GC-dependent) | 0 (impl.) | [JDK documented] + [HotSpot implementation] |
| `System.exit(7)` / `Runtime.exit(7)` | yes | no — threads frozen after hooks | no | 7 (truncated, §3.9) | [JDK documented] |
| `Runtime.halt(9)` | **no** | no | no | 9 | [JDK documented] |
| Uncaught exception in `main` (last non-daemon) | yes | no | no | 1 (impl.) + stderr trace | [HotSpot implementation] |
| SIGTERM/SIGINT/SIGHUP (no `-Xrs`) | yes — JVM-installed handlers start the sequence | no | no | 128+N observed, e.g. 143 (impl.) | [JDK documented] trigger / [HotSpot implementation] status |
| SIGTERM/… with `-Xrs` | no — handlers not installed | no | no | killed by signal; shell sees 128+N | [JDK documented] (`java` manual) |
| SIGKILL | no — kernel action, no Java code runs | no | no | 137 = 128+9 | [Linux/POSIX] |
| Hook deadlock (hook calls `System.exit`) | sequence never finishes | — | — | must `halt` or kill | [JDK documented] |

### 3.9 Exit-status range and truncation

`System.exit(int)` takes the full Java `int`, but what a parent can observe is
OS-scoped: on Linux/POSIX, `exit(3)` — "the **least significant byte** of status (i.e.,
`status & 0xFF`) is returned to the parent" [Linux/POSIX, man-pages exit(3)]. So
`System.exit(256)` is observed as **0**, `System.exit(300)` as **44**; portable status
codes are 0..255. The JDK documentation does not document the truncation — it is OS
behavior on every supported Unix. Signal deaths are encoded by the kernel as `128+N` in
the shell view; Java's own child-status reporting mirrors that only by implementation
choice (§5.7).

---

## 4. Signals and OS Interaction

### 4.1 The documented surface: shutdown hooks only

There is **no public JVM API** for registering POSIX signal handlers — a documented
platform limitation, not a gap. The `java` manual [JDK documented]: "The JVM catches
signals to implement shutdown hooks for unexpected termination. The JVM uses **SIGHUP,
SIGINT, and SIGTERM** to initiate the running of shutdown hooks." Consequences: hooks
cannot tell *which* signal triggered them (no signal number is delivered); arbitrary
signals cannot be ignored or re-bound from supported Java code; SIGKILL/SIGSTOP are
uncatchable by any process and bypass Java entirely. Signal-triggered shutdown goes
through the same hook sequence as `System.exit` (§3.3); the final status is [HotSpot
implementation] 128+N (sibling chapter verifies 143 for SIGTERM).

### 4.2 `sun.misc.Signal` — the internal API (labeled)

Not part of the published SE API specification (the JDK 25 published module docs do not
include it; the class lives in the `jdk.unsupported` module). Verified from the
`jdk-25+36` source (`src/jdk.unsupported/share/classes/sun/misc/Signal.java`):
`public static synchronized SignalHandler handle(Signal sig, SignalHandler handler) throws IllegalArgumentException`
and `public static void raise(Signal sig) throws IllegalArgumentException`. Documented
constraints (class Javadoc, verbatim): "Java code cannot register a handler for signals
that are already used by the Java VM implementation. The `Signal.handle` function raises
an `IllegalArgumentException` if such an attempt is made." And: "the special C signal
handler **creates a new thread** (at priority `Thread.MAX_PRIORITY`) to run the
registered Java signal handler. The C signal handler immediately returns." So even this
internal API dispatches handlers **asynchronously on a fresh thread** — Java never runs
code in the POSIX signal-handling context. `handle` delegates to
`jdk.internal.misc.Signal`. Status: internal, unsupported, may change without notice —
relying on it is implementation behavior [HotSpot implementation].

### 4.3 `-Xrs` — the exact documented behavior

[JDK documented, `java` manual, verified]: "Reduces the use of operating system signals
by the JVM." Non-Windows: "When `-Xrs` is used, the signal masks for SIGINT, SIGTERM,
SIGHUP, and SIGQUIT **aren't changed by the JVM**, and **signal handlers for these
signals aren't installed**." Documented consequences: "Non-Windows: **SIGQUIT thread
dumps aren't available**. Windows: Ctrl+Break thread dumps aren't available." And: "User
code is responsible for causing shutdown hooks to run, for example, by calling
`System.exit()` when the JVM is to be terminated." So under `-Xrs`: SIGHUP/SIGINT/SIGTERM
take the kernel default action (terminate) — hooks do **not** run;
`System.exit`-initiated shutdown still runs hooks normally. Embedders that must own
SIGINT/SIGTERM install `-Xrs` by design.

### 4.4 Runtime internals (labeled, non-API)

- **SIGQUIT → thread dump** on HotSpot: documented only *negatively* via `-Xrs`
  ("SIGQUIT thread dumps aren't available") plus the manual's grouping of SIGQUIT with
  the JVM-handled signals [HotSpot implementation].
- **libjsig / signal chaining**: the JVM ships a signal-chaining interposer so JNI
  libraries that install handlers coexist with JVM handlers. The dedicated Oracle
  Troubleshooting-Guide page was not reachable at retrieval time — **source-limited**
  (ledger PL-JV-062); treat details as implementation behavior and keep JNI handlers out
  of JVM-owned signals (SIGHUP/SIGINT/SIGTERM/SIGQUIT).
- **Hooks + OOM + halt**: `OutOfMemoryError` is an `Error` (unchecked, §1.3); throwing it
  does not initiate any documented shutdown path — the JVM continues unless your uncaught
  handler exits. Under memory pressure, hook threads that allocate may fail *during*
  shutdown; the documented API Note ("coded defensively … thread-safe … avoid
  deadlocks") is the only normative guidance. A stuck sequence is ended only by `halt`
  (§3.4) or an external SIGKILL [Linux/POSIX].

### 4.5 POSIX vs Windows deltas (brief)

[Windows delta, JDK documented]: "the JVM watches for console control events … registers
a console control handler that begins shutdown-hook processing and returns TRUE for
**CTRL_C_EVENT, CTRL_CLOSE_EVENT, CTRL_LOGOFF_EVENT, and CTRL_SHUTDOWN_EVENT**. The JVM
uses a similar mechanism … **CTRL_BREAK_EVENT to perform thread dumps**." With `-Xrs` on
Windows "the JVM doesn't install any console control handler." CTRL_CLOSE_EVENT (console
window closed) gives a bounded grace period to run hooks — unlike POSIX SIGTERM there is
no second default-killing signal; treat hook latency on Windows as best-effort. POSIX
specifics (signal masks, handler dispatch on a dedicated internal thread, `128+N` status
encoding) are [Linux/POSIX]/[HotSpot implementation] throughout this chapter.

---

## 5. Subprocess and Child-Process Management

### 5.1 Creation: `ProcessBuilder` — argument list, never a shell

```java
Process p = new ProcessBuilder("ls", "-l", dir)  // argv array — no shell, no quoting layer
        .directory(workDir)                       // child cwd; null = inherit
        .start();
```

`start()` spawns with the builder's current command list, directory, and environment.
Failure is `IOException`-typed and documented: "The operating system program file was not
found. / Access to the program file was denied. / The working directory does not exist. /
Invalid character in command argument, such as NUL." [JDK documented]. Because the API
passes an **argv array** there is no shell-injection surface at the Java level — the risk
returns only if you deliberately run `sh -c "…"`. **Pipelines** without a shell:
`ProcessBuilder.startPipeline(List.of(b1, b2, b3))` wires each process's stdout to the
next process's stdin [JDK documented]. **Reuse hazard**: a builder is a configuration
object — `start()` twice spawns two children; mutating the stored command list or the
`environment()` map after `start()` affects only future `start()` calls (the child
inherits a snapshot at spawn) [JDK documented].

### 5.2 Streams and the documented pipe-buffer deadlock

Defaults: all three std streams are `Redirect.PIPE`; the parent gets `getOutputStream()`
(child's stdin), `getInputStream()` (child's stdout), `getErrorStream()` (child's
stderr). The `Process` class Javadoc caution (§2.5) is the normative deadlock warning.
The classic **two-pipe deadlock** — worked example:

```java
// BROKEN: child writes > pipe-buffer bytes to stderr while parent blocks on stdout read.
Process p = new ProcessBuilder("verbose-tool", "--big").start();
String out;
try (var in = p.getInputStream()) {
    out = new String(in.readAllBytes());     // blocks until stdout EOF
}
String err;
try (var e = p.getErrorStream()) {           // stderr never drained meanwhile
    err = new String(e.readAllBytes());
}
// Expected (bug): if verbose-tool writes ~1MB to stderr before its first stdout byte,
// the child blocks in write(2) on the full stderr pipe, never reaches stdout EOF,
// and readAllBytes() blocks forever => parent and child deadlocked.

// FIXED — choose one:
//  (a) merge: new ProcessBuilder("verbose-tool","--big").redirectErrorStream(true).start();
//  (b) drain concurrently: read stderr on another thread (or via CompletableFuture)
//  (c) redirect: redirectError(Redirect.to(errFile)) / Redirect.DISCARD / INHERIT
```

Drain rule: with PIPE redirections, *every* connected stream must be drained while the
child runs, or the child can fill its pipe buffer (Linux default 64 KiB per pipe
[Linux/POSIX]) and block. `redirectErrorStream(true)` merges stderr into stdout (the
stderr getter then returns `null`); file/DISCARD/INHERIT redirections make the
corresponding `Process` stream return `null` — nothing to drain.

### 5.3 Waiting, polling, and status retrieval

```java
Process p = pb.start();
if (!p.waitFor(30, TimeUnit.SECONDS)) {   // false = still running; CHILD NOT KILLED
    p.destroy();                          // SIGTERM on POSIX [HotSpot implementation]
    if (!p.waitFor(5, TimeUnit.SECONDS)) {
        p.destroyForcibly().waitFor();    // SIGKILL on POSIX; waitFor() reaps + gets status
    }
    throw new java.util.concurrent.TimeoutException("child hung");
}
int code = p.exitValue();                 // legal only after termination
```

- `waitFor()` — returns the exit value; interruption throws `InterruptedException` and
  leaves the child untouched [JDK documented].
- `waitFor(timeout, unit)` / `waitFor(Duration)` (@since 24) — `true` if exited, `false`
  on timeout; the default implementation "polls the exitValue" and concrete
  implementations are "strongly encouraged to override" [JDK documented]; **a timeout
  kills nothing** — the documented kill-after-timeout pattern is above (there is no
  Python-style one-shot `run(timeout=…)`).
- `exitValue()` — polls without blocking; `IllegalThreadStateException` if still running
  [JDK documented].
- `isAlive()` — `true` until terminated; after `destroyForcibly()` "may return true for
  a brief period" [JDK documented API Note] — a documented destroy-then-observe race.

### 5.4 `destroy` / `destroyForcibly` — what they actually send

The JDK documentation says only "kills the process"; whether termination is "normal"
(clean shutdown) or forcible "is implementation dependent", and
`supportsNormalTermination()` reports which your platform does [JDK documented]. On
Unix, verified from the `jdk-25+36` source (`ProcessHandleImpl_unix.c`):

```c
int sig = (force == JNI_TRUE) ? SIGKILL : SIGTERM;   // destroy0 body
return (kill(pid, sig) < 0) ? JNI_FALSE : JNI_TRUE;
```

So `destroy()` → **SIGTERM**, `destroyForcibly()` → **SIGKILL** [HotSpot
implementation, source-verified], gated by a **start-time check** — the kill happens
only if the recorded start time still matches ("The process is signaled only if its
start time matches the known start time", `ProcessHandleImpl`) — a guard against **pid
reuse** [HotSpot implementation]. `ProcessHandle.destroy` returns `boolean` (false on
failure, e.g. permission denied); `Process.destroy` returns nothing. A child that
ignores SIGTERM needs `destroyForcibly()`; a **zombie** (exited, not reaped) is reaped
by `waitFor()`/`onExit()` [Linux/POSIX].

### 5.5 `Process.onExit()` — asynchronous process management

```java
Process p = new ProcessBuilder("long-job").start();
p.onExit().thenAccept(done -> System.out.println("code=" + done.exitValue()));
// ... main thread does other work; no thread is blocked in waitFor

// wait with timeout WITHOUT a blocked thread:
Process done = p.onExit().get(30, TimeUnit.SECONDS);   // TimeoutException if too slow

// run several children concurrently and wait for all:
List<Process> ps = cmds.stream().map(c -> new ProcessBuilder(c).start()).toList();
CompletableFuture.allOf(ps.stream().map(Process::onExit).toArray(CompletableFuture<?>[]::new))
                 .join();                              // all exited (any status)
```

`onExit()` (both `Process` and `ProcessHandle`, @since 9) returns
`CompletableFuture<Process>` "completed regardless of the exit status of the process";
"Cancelling the CompletableFuture does not affect the Process" [JDK documented].
`allOf` [JDK documented]: completes when all complete; an exceptional completion
anywhere makes it complete exceptionally with a `CompletionException` cause — for
process futures (which complete normally even on nonzero exit) this only triggers on
your own chained stages. `get()` throws checked `InterruptedException`/
`ExecutionException`; `join()` throws unchecked `CompletionException` (§2.7).

### 5.6 `ProcessHandle` — trees, info, and descendants

```java
// Kill a whole subtree (documented snapshot semantics — beware races):
ProcessHandle root = ProcessHandle.of(pid).orElseThrow();
root.descendants().forEach(ProcessHandle::destroy);   // SIGTERM the subtree...
root.destroy();                                        // ...then the root

// Diagnostics (all Optional — availability platform-dependent):
ProcessHandle.Info i = ProcessHandle.current().info();
System.out.println(i.command().orElse("?") + " started " + i.startInstant().orElse(null));
```

`children()`/`descendants()` are **snapshots**: "processes are created and terminate
asynchronously … no guarantee that a process is alive" [JDK documented]. A child that
itself spawned grandchildren is still *reported* via `descendants()` (recursive), but
whether an exited intermediate child's orphans remain discoverable is
platform-dependent [JDK documented; on Linux discovered via `/proc` parent links,
[HotSpot implementation]]. The same start-time guard protects `destroy` from killing a
recycled pid (§5.4). There is no atomic tree-kill — the snapshot can race with child
creation; a robust implementation re-checks `isAlive()`/`onExit()`.

### 5.7 Exit-status representation of a signal-killed child (verification result)

[JDK documented] `exitValue`/`waitFor` say only: "the exit value of the process … By
convention, the value 0 indicates normal termination." **No JDK documentation defines
the value for a signal-killed child.** Verified from the `jdk-25+36` source
(`ProcessHandleImpl_unix.c`):

```c
/* The child exited because of a signal.
 * The best value to return is 0x80 + signal number,
 * because that is what all Unix shells do, and because
 * it allows callers to distinguish between process exit and
 * process death by signal. */
#define WTERMSIG_RETURN(status) (WTERMSIG(status) + 0x80)
```

[HotSpot implementation, source-verified]: a child killed by signal N is reported as
**128+N** (143 after SIGTERM, 137 after SIGKILL); `WIFEXITED` cases return
`WEXITSTATUS`. This is implementation behavior — the sibling chapter (LG-JA-005) reaches
the same conclusion; portable code should treat any nonzero value as "abnormal" and use
`Info`/platform checks for signal-death diagnostics.

### 5.8 Interruption, virtual threads, and the pump threads

Interrupting a thread blocked in any `waitFor` throws `InterruptedException` and does
not affect the child [JDK documented]. [HotSpot implementation, source-verified]
`ProcessImpl.waitFor()` parks on a `j.u.c` lock (`lock.lock(); condition.await()`), not
an object monitor — so a **virtual thread** waiting in `waitFor()` unmounts normally and
does **not** pin its carrier; and since JEP 491 (JDK 24) even `synchronized`-based
blocking no longer pins [JDK documented, JEP 491 *Delivered, Release 24*]. Blocking on
`Process` *streams* (pipe reads) in virtual threads is likewise handled by the
implementation's poll-based I/O [HotSpot implementation]. Which native threads pump the
pipes is an implementation detail with no API surface [HotSpot implementation].

### 5.9 Platform deltas (brief)

[Linux/POSIX]: spawn via the `posix_spawn`/`vfork`/`clone` family (choice is an
implementation detail), `pipe(2)` buffers (~64 KiB), SIGTERM/SIGKILL for destroy,
zombies until reaped, pid reuse guarded by start time. [Windows delta]: no SIGTERM —
`destroy()` maps to a terminate-style operation (check
`supportsNormalTermination()`), pipe/fd semantics differ, and `Redirect.DISCARD` writes
to the OS null file on both platforms [JDK documented; platform mapping = [HotSpot
implementation]].

---

## 6. Concurrency and Resource Semantics

### 6.1 Thread essentials in scope

`start()` schedules the thread; starting twice throws `IllegalThreadStateException` [JDK
documented]; calling `run()` directly is ordinary method invocation. `join()` blocks
until death, `throws InterruptedException`. `interrupt()` is cooperative: for
`Object.wait`/`Thread.sleep`/`join` — status cleared, `InterruptedException`; for
`InterruptibleChannel` I/O — channel closed + `ClosedByInterruptException`; for
`Selector` — wakeup; otherwise the status flag is set and the target must poll
`isInterrupted()` [JDK documented, verified text §2.2]. `setDaemon(true)` must precede
`start()`; virtual threads are always daemon and cannot be made non-daemon [JDK
documented]. Daemon threads never prevent the shutdown sequence; they are frozen
mid-flight at termination (§3.3). Thread death ≠ process death (§3.6).

### 6.2 Executors and waiting for processes

Prefer `CompletableFuture.onExit` chains (§5.5) to parking threads: `ExecutorService` +
`allOf(onExit futures)` scales to many children; a platform-pool task blocked in
`waitFor()` occupies a carrier — with virtual threads submit
`p.onExit().thenRun(...)` instead. Shutdown interplay: executor threads are ordinary
non-daemon threads by default and **keep the JVM alive** unless the executor is shut
down (`shutdown()`) or its threads are daemons — the common cause of "my Java program
hangs after main returns".

### 6.3 Synchronization essentials (as they bear on hooks and callbacks)

- Shutdown hooks run **concurrently** in unspecified order (§3.3) — shared state needs
  `synchronized`, `volatile`, or `j.u.c` atomics; the API Note mandates thread-safe
  hooks [JDK documented].
- `onExit` dependent actions run on the JDK's process machinery threads by default
  [HotSpot implementation] — hand them to your own executor
  (`thenRunAsync(action, executor)`) when they must not run there.
- Visibility at shutdown: daemon threads may still be *running concurrently with hooks*
  (§3.3) — writes from them are visible to hooks only with proper happens-before edges
  (see [jvm-memory-model.md](../java/jvm-memory-model.md)); do not assume ambient
  daemons finished their work.

### 6.4 fd/handle ownership of `Process` streams

Documented lifecycle [JDK documented, `Process` class description, verbatim]: streams
remain usable "until there are no longer any references to the `Process` or the input,
error, and output streams or readers, or they have been closed"; "The process is not
killed when there are no more references to the `Process` object, but rather the process
continues executing asynchronously"; and — the leak protection — "The process
implementation closes file descriptors and handles for streams that are no longer
referenced to prevent leaking operating system resources. Processes that have terminated
or been terminated are monitored and their resources released." Practical contract:
dropping a `Process` does **not** kill the child; unreferenced streams are eventually
closed by the implementation — but with many long-lived children, close streams you stop
using and `destroy` children you no longer need; relying on GC timing for fd budgets is
[HotSpot implementation] behavior. There are **no finalizers on `Process`** — cleanup is
the implementation's monitoring plus your explicit close/destroy (§6.5).

### 6.5 Buffering and GC interaction

The byte streams from `Process` are buffered wrappers in the reference implementation
[HotSpot implementation]; wrap with `BufferedReader`/`BufferedInputStream` for
throughput. The @since-17 char bridges carry the documented caveat that "The
`BufferedReader` may have buffered input from the input stream" — mixing byte and char
APIs on one stream can strand bytes in a buffer [JDK documented]. `System.out` is a
`PrintStream`; **nothing in the documented shutdown sequence flushes streams** — flush
explicitly before `System.exit` or in hooks; `halt` and SIGKILL lose unflushed data
(§3.8). Finalization is deprecated-for-removal and never guaranteed (§1.8); the
sanctioned post-mortem hook for *your* wrappers is `java.lang.ref.Cleaner` (§2.7) — e.g.
a cleaning action that warns about an un-destroyed child — with the same rule that
Cleaner actions are **not** guaranteed to run at JVM termination (§3.8).

### 6.6 Deadlocks (full inventory)

| Deadlock | Mechanism | Cure |
|---|---|---|
| Two-pipe stdout/stderr | child fills unread stderr pipe while parent blocks on stdout (§5.2) | `redirectErrorStream(true)`, concurrent drains, redirect to files |
| Stdin overfeed | parent writes child's stdin past its buffer; child not reading | write in a separate thread; close `getOutputStream()` to signal EOF |
| Undrained output + `waitFor` | `waitFor()` blocks; child blocks on full pipe | drain (concurrently) before/while waiting |
| Hook deadlock | hook calls `System.exit`/`Runtime.exit` → blocks forever (§3.3) | `Runtime.halt` from the hook; keep hooks minimal |
| Hook ↔ service deadlock | hook waits on a service whose own hook has not run (unspecified order) | API Note: "not rely blindly upon services that may have registered their own shutdown hooks" |
| Class-init deadlock | cyclic `<clinit>` (§1.7) | restructure static state |

### 6.7 Races and leaks

**Races:** (1) `destroy()` then `exitValue()`/`isAlive()` — the child may still be
dying; documented for `destroyForcibly` ("isAlive may return true for a brief period")
and generally for SIGTERM delivery [JDK documented]/[Linux/POSIX]; pattern:
`p.destroyForcibly().waitFor()` or `p.onExit().get()`. (2) `environment()`/`command(List)`
mutation racing `start()` — the map/list is live; configure fully before `start()`
(§5.1). (3) `descendants()`-based tree kills race with process creation — snapshots, not
transactions (§5.6). (4) Hook-order race — two hooks assuming each other's cleanup ran;
forbidden by the unspecified-order rule (§3.5).

**Leaks:** (1) **Zombies** [Linux/POSIX] — exited children never waited/reaped
accumulate as `<defunct>`; `waitFor()`/`onExit()` reaps; a JVM that spawns many
short-lived children but never waits leaks zombie PIDs. (2) **Unclosed streams** — the
implementation closes unreferenced ones eventually (§6.4); explicit close keeps fd
pressure bounded. (3) **`ThreadLocal` in pooled threads** — hook threads are fresh
threads each shutdown, but pooled carrier threads outlive tasks; `ThreadLocal`s left set
leak values across tasks (JEP 444 guidance on thread-local "expensive resource per
task" idioms [JDK documented]). (4) **Double-spawn** — reusing a builder by accident
starts a second identical child (§5.1) — a work leak, not an fd leak.

### 6.8 Runtime scheduling effects (virtual threads, brief)

Virtual threads (JEP 444, delivered 21) unmount on blocking j.u.c/IO operations.
In-scope consequences: (a) `waitFor()` in the reference implementation parks on j.u.c
locks — safe on virtual threads, no pinning (§5.8); (b) `synchronized` pinning existed
in 21 but JEP 491 (24) removed it — blocking inside monitors now parks instead of
capturing the carrier [JDK documented]; (c) `java.io` classes were reworked to avoid
pinning [JDK documented, JEP 444]; (d) prefer `onExit` callbacks to thousands of parked
platform threads when supervising large child fleets (§6.2). Deeper treatment:
[virtual-threads.md](../java/virtual-threads.md).

### 6.9 Misconceptions (process/concurrency level)

"`System.exit` kills immediately" — it starts a sequence hooks can stall forever (§3.3);
only `halt` is immediate. "Hooks run in registration order" — unspecified (§3.5).
"`waitFor(timeout)` kills the child" — it returns `false` and leaves it running (§5.3).
"`Process.destroy` always kills" — SIGTERM may be ignored; escalate to
`destroyForcibly` (§5.4). "Dropping the `Process` object kills the child" — documented
to the contrary (§6.4). "The JVM exits when main throws" — only when the last non-daemon
thread ends; stray non-daemon threads keep it alive (§3.6, §6.2).

---

## Coverage ledger

The authoritative, per-claim ledger for this chapter is
[ledger-java.md](./ledger-java.md) (schema G4, IDs `PL-JV-001`…). **Declared row count:
80 rows** — §1 semantics: PL-JV-001–013; §2 API inventory: PL-JV-014–045; §3 process
creation/termination: PL-JV-046–056; §4 signals/OS: PL-JV-057–063; §5 subprocesses:
PL-JV-064–074; §6 concurrency/resources: PL-JV-075–080. Rollup: **Inventoried 80 /
Documented 78 / Remaining 0 / Source-limited 2** (PL-JV-062: signal-chaining/libjsig
documentation unreachable; PL-JV-073: JDK API docs silent on signal-death encoding —
value stated as source-verified implementation behavior).

## Related Topics

- [Java: Exit Status, Signals, and Process Lifecycle](../../linux/process-exit-signal/languages/java.md)
  — the exit/signal-scoped chapter (LG-JA-*); termination-status tables live there.
- [Go](./go.md) — `exec.Cmd`/`WaitDelay` model vs `ProcessBuilder`; `os.Exit` vs
  `System.exit`/`halt`.
- [Python](./python.md) — `subprocess.run(timeout=…)` kills vs `waitFor` does not;
  `-N` status convention vs Java's undocumented 128+N.
- [Part hub](./index.md) — Section G scope and ledger schema.
- [JVM internals](../java/jvm.md) — class loading/JIT beneath these semantics.
- [JVM memory model](../java/jvm-memory-model.md) — happens-before for hook visibility
  (§6.3).
- [Virtual threads](../java/virtual-threads.md) — pinning details behind §5.8/§6.8.

## References

*API specification (all retrieved 2026-10-13; Java SE 25 & JDK 25):*

1. `java.lang.Runtime` (shutdown sequence, exit, halt, hooks): https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html
2. `java.lang.System` (`exit`): https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/System.html
3. `java.lang.Object` (`finalize` status): https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Object.html
4. `java.lang.Thread` (+ `UncaughtExceptionHandler`): https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html
5. `java.lang.ProcessBuilder` (+ `Redirect`): https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ProcessBuilder.html
6. `java.lang.Process`: https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Process.html
7. `java.lang.ProcessHandle` (+ `Info`): https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ProcessHandle.html
8. `java.util.concurrent.CompletableFuture`: https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/CompletableFuture.html
9. `java.lang.Throwable` (suppression): https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Throwable.html
10. `java.lang.ref.Cleaner`: https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ref/Cleaner.html

*Specifications and command reference (retrieved 2026-10-13):*

11. JLS SE 25 — §5.1.7/5.1.8 (boxing/unboxing), §11 (exceptions), §12.4 (class
    initialization), §12.8 (program exit), §14.20.2 (try-finally), §14.20.3
    (try-with-resources), §15.12.2 (overload resolution), §15.25 (conditional
    expressions): https://docs.oracle.com/javase/specs/jls/se25/html/
12. `java` command manual (main rules, `-Xrs`, console control events):
    https://docs.oracle.com/en/java/javase/25/docs/specs/man/java.html

*JEPs (retrieved 2026-10-13):*

13. JEP 421 — Deprecate Finalization for Removal (Release 18): https://openjdk.org/jeps/421
14. JEP 444 — Virtual Threads (Release 21): https://openjdk.org/jeps/444
15. JEP 491 — Synchronize Virtual Threads without Pinning (Release 24): https://openjdk.org/jeps/491
16. JEP 512 — Compact Source Files and Instance Main Methods (Release 25): https://openjdk.org/jeps/512
17. JEP 395 — Records (Release 16); JEP 409 — Sealed Classes (Release 17): https://openjdk.org/jeps/395 , https://openjdk.org/jeps/409

*OpenJDK `jdk-25+36` source spot-checks (retrieved 2026-10-13):*

18. `src/java.base/unix/classes/java/lang/ProcessImpl.java` (waitFor on j.u.c locks);
    `src/java.base/share/classes/java/lang/ProcessHandleImpl.java` (`destroyProcess`
    + start-time guard); `src/java.base/unix/native/libjava/ProcessHandleImpl_unix.c`
    (`SIGKILL : SIGTERM`; `0x80 + signal` exit encoding);
    `src/jdk.unsupported/share/classes/sun/misc/Signal.java`;
    `src/java.base/share/classes/java/lang/Integer.java` (IntegerCache) —
    https://github.com/openjdk/jdk/tree/jdk-25%2B36

*POSIX/OS layer (retrieved 2026-10-13):*

19. man-pages exit(3) — 8-bit status truncation: https://man7.org/linux/man-pages/man3/exit.3.html
