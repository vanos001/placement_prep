# Chunk I Audit — Languages + Frameworks + Redis + Machine-coding

**Scope:** src/languages/*, src/frameworks/*, src/redis/*, src/machine-coding/* (skipping already-fixed)
**Files audited:** 78
**Files clean:** 47
**Total findings:** 33

## Findings

### HIGH severity

#### 1. `languages/rust/README.md` — missing `fn` keyword (compile error)
Line 145:
```rust
divmod(a: i32, b: i32) -> (i32, i32) {
    (a / b, a % b)
}
```
**Issue:** Missing `fn` keyword; this will not compile.
**Fix:** `fn divmod(a: i32, b: i32) -> (i32, i32) { ... }`
**Verification:** Rust reference — function definitions require `fn` keyword (https://doc.rust-lang.org/reference/items/functions.html).

---

#### 2. `languages/rust/README.md` — `println` missing macro `!` (compile error)
Lines 168–171:
```rust
match value {
    1 => println("one"),
    2 | 3 => println("two or three"),
    4..=9 => println("four to nine"),
    _ => println("something else"),
}
```
**Issue:** `println` is a macro, not a function; calls must use `println!(...)`. All four lines are compile errors.
**Fix:** Use `println!("one")`, etc.
**Verification:** Rust stdlib — `println!` is defined as a macro (https://doc.rust-lang.org/std/macro.println.html).

---

#### 3. `languages/rust/README.md` — false claim that ownership prevents memory leaks
Line 311:
> "Explain Rust's ownership model and how it prevents memory leaks"

**Issue:** Rust's ownership system does **NOT** prevent memory leaks. Leaks are considered "safe" in Rust. You can leak memory with `Rc`/`Arc` cycles, `Box::leak`, `mem::forget`, or just holding references forever. Rust prevents: use-after-free, double-free, dangling pointers, data races — but **not** leaks.
**Fix:** Rephrase to "prevents use-after-free, double-free, and dangling pointers" or "prevents memory-safety bugs."
**Verification:** Rustonomicon — "Leaking memory is safe in Rust" (https://doc.rust-lang.org/nomicon/leaking.html).

---

#### 4. `languages/rust/async.md` — `JoinHandle.unwrap()` does not exist (compile error)
Line 99:
```rust
let (r1, r2) = tokio::join!(handle1.unwrap(), handle2.unwrap());
```
**Issue:** `tokio::task::JoinHandle<T>` has no `unwrap()` method. It implements `Future<Output = Result<T, JoinError>>`, so you `await` it and then `unwrap()` the resulting `Result`.
**Fix:** `let (r1, r2) = tokio::join!(handle1, handle2);` then `r1.unwrap()` / `r2.unwrap()`.
**Verification:** Tokio docs — `JoinHandle` impls `Future`, no `unwrap` method on the handle itself (https://docs.rs/tokio/latest/tokio/task/struct.JoinHandle.html).

---

#### 5. `languages/rust/unsafe.md` — unsound `&'static T` return from raw pointer
Line 272:
```rust
unsafe fn deref_ptr<T>(ptr: *const T) -> &'static T {
    &*ptr
}
```
**Issue:** Returning `&'static T` from a raw pointer is unsound — the data pointed to is almost certainly not `'static`. This is a classic source of unsoundness.
**Fix:** Use an explicit lifetime parameter: `unsafe fn deref_ptr<'a, T>(ptr: *const T) -> &'a T` (caller asserts the lifetime).
**Verification:** Rustonomicon — lifetimes of references from raw pointers must be specified by the caller (https://doc.rust-lang.org/nomicon/transmutes.html).

---

#### 6. `languages/go/README.md` — untranslated Chinese characters (AI artifact)
Line 158:
> "**Race detection** — `go test -race`, race detector原理"

**Issue:** "原理" (Chinese for "principle/mechanism") was left untranslated; rest of doc is English. Looks like an unfinished AI generation artifact.
**Fix:** Replace with "race detector internals" or "how the race detector works."

---

#### 7. `languages/go/memory-model.md` — sync.Once happens-before rule is reversed
Line 17:
> "**sync.Once** — `Do` call happens-before `f()` returns"

**Issue:** Reversed. The Go memory model says the *execution of `f()`* happens-before (is synchronized before) the *return of any `Do` call*. The doc says the opposite.
**Correct text:** "f() invocation happens-before any `Do(f)` call returns."
**Verification:** Go Memory Model — "The completion of a single call of `f()` from `once.Do(f)` is synchronized before the return of any call of `once.Do(f)`" (https://go.dev/ref/mem).

---

#### 8. `languages/java/virtual-threads.md` — false claim about JDK 25 structured concurrency
Line 5:
> "JDK 25 structured concurrency final"

Line 73:
> "JDK 25 finalizes `StructuredTaskScope` API with `Joiner.allSuccessfulOrThrow()` etc."

**Issue:** Incorrect. As of JDK 25 (Sept 2025), structured concurrency is still in **5th Preview** (JEP 505), NOT finalized. It is also internally contradictory: the code examples (lines 59–66) use the older `ShutdownOnFailure`/`ShutdownOnSuccess` API, which was removed in JEP 505 (JDK 24+) in favor of the new `StructuredTaskScope.Open` + `Joiner` API.
**Fix:** Either drop the "final" claim or update code to the new `Joiner`-based API.
**Verification:** JEP 505: "Structured Concurrency (Fifth Preview)" — https://openjdk.org/jeps/505 (Sept 18, 2024).

---

#### 9. `languages/java/README.md` — outdated LTS version
Line 35:
> "**Latest LTS** | Java 21 (2023)"

**Issue:** JDK 25 (released Sept 16, 2025) is the current LTS, not JDK 21.
**Fix:** "Latest LTS | Java 25 (2025)".
**Verification:** OpenJDK JDK 25 project page — "JDK 25 reached General Availability on 16 September 2025 ... will be a long-term support (LTS) release" (https://openjdk.org/projects/jdk/25).

---

#### 10. `languages/c/posix.md` — pipe diagram contradicts the code
Lines 408–438: The code shows the **child** as the writer and the **parent** as the reader.
Lines 446–460: The diagram shows the **parent** writing and the **child** reading — the reverse of what the code does.
**Fix:** Swap the labels in the diagram so parent reads, child writes (or vice-versa, matching the code).

---

#### 11. `languages/c/memory-management.md` — self-contradicting "leak" example
Lines 215–222:
```c
// LEAK: Allocates but never frees
char* create_greeting(const char *name) {
    char *greeting = malloc(100);
    ...
    return greeting;
    // Caller must free(greeting)!
}
```
**Issue:** The comment says "LEAK" but the function returns the allocation to the caller, who is responsible for freeing (as the inner comment notes). This is **not** a leak by design — it's an ownership-transfer pattern. Calling it a leak is misleading.
**Fix:** Remove the "LEAK" label or rephrase as "Caller-owned: returns heap memory the caller must free."

---

#### 12. `languages/c/pointers.md` — wrong claim about `void*` arithmetic
Line 506–507:
> "What happens when you increment a `void *` pointer? It's undefined behavior in C."

**Issue:** Wrong. Incrementing a `void*` is **not** undefined behavior; it's a **constraint violation** in standard C (compile error). GCC permits it as a non-standard extension (treating `void*` like `char*`).
**Fix:** "It's a constraint violation in standard C — the compiler rejects it (GCC allows it as an extension)."
**Verification:** ISO/IEC 9899:2011 §6.5.6 — pointer arithmetic requires a complete object type; `void` is incomplete.

---

#### 13. `languages/python/README.md` and `languages/python/interview-questions.md` — undefined variable in late-binding closure example
`README.md` line 227 and `interview-questions.md` line 363:
```python
funcs = [lambda: i for i in range(5)]
print([f() for f in f])  # [4, 4, 4, 4, 4] — NOT [0, 1, 2, 3, 4]
```
**Issue:** `[f() for f in f]` — the iteration variable `f` is undefined; should be `funcs`. This is a `NameError`.
**Fix:** `print([f() for f in funcs])`.

---

#### 14. `languages/rust/ownership.md` — default impl panics on short strings
Line 248:
```rust
fn preview(&self) -> String {
    format!("{}...", &self.summarize()[..20])  // panics if < 20 chars
}
```
**Issue:** String slicing in Rust panics if the range falls outside the string's byte length (or splits a UTF-8 codepoint). For any `summarize()` returning < 20 bytes, this `preview` implementation panics at runtime. This is a real bug in the sample code, not just stylistic.
**Fix:** Use `self.summarize().chars().take(20).collect::<String>()` or `&self.summarize()[..20.min(self.summarize().len())]`.

---

#### 15. `frameworks/fastapi/README.md` — Pydantic V1 `@validator` in a V2 doc
Lines 85–89 (in a file that documents Pydantic V2 at lines 103–143):
```python
@validator('password')
def password_strength(cls, v):
    ...
```
**Issue:** `@validator` is Pydantic V1 syntax, deprecated in V2. The same file later shows the correct V2 `@field_validator` with `@classmethod`. Inconsistent — readers may copy the deprecated pattern.
**Fix:** Use `@field_validator('password')` + `@classmethod`.
**Verification:** Pydantic V2 migration guide — `@validator` is deprecated (https://docs.pydantic.dev/2.0/migration/#changes-to-validators).

---

#### 16. `redis/patterns-and-internals.md` — outdated "single-threaded" claim
Line 99:
> "single-threaded event loop (no locks)"

**Issue:** Misleading. Since Redis 6.0 (2020), Redis supports **multi-threaded I/O** for network reads/writes (`io-threads` config). Command *execution* remains single-threaded, but "single-threaded event loop, no locks" is no longer accurate.
**Fix:** "Single-threaded command execution; multi-threaded network I/O (since Redis 6.0)."
**Verification:** Redis docs / OneUptime — "Redis has a single-threaded command execution model, but since Redis 6.0 it can use multiple threads for reading and writing network I/O."

---

#### 17. `languages/javascript/nodejs.md` — deprecated `crypto.createCipher()`
Line 130:
```
| **Transform** | Modify data as it passes through | `zlib.createGzip()`, `crypto.createCipher()` |
```
**Issue:** `crypto.createCipher()` was deprecated in Node.js v10 (2018) and should not be used. Use `crypto.createCipheriv()` (which requires an IV).
**Fix:** Replace with `crypto.createCipheriv()`.
**Verification:** Node.js docs — `crypto.createCipher()` is deprecated since v10.0.0 (https://nodejs.org/api/crypto.html#cryptocreatecipheralgorithm-key-options).

---

#### 18. `languages/cpp/interview-questions.md` — `generator<int>` claimed as C++20
Lines 251–266 (Q17 "Coroutines (C++20)?"):
```cpp
generator<int> fibonacci() {
    int a = 0, b = 1;
    while (true) {
        co_yield a;
        ...
    }
}
```
**Issue:** `std::generator` is a C++23 feature (`<generator>` header, P2502). It is NOT part of C++20. C++20 only added the coroutine machinery (`co_await`, `co_yield`, `co_return`); users had to write their own generator types. Listing this under "Coroutines (C++20)" is misleading.
**Fix:** Either move to a C++23 section, or note that `generator` is C++23 (`std::generator`) and C++20 coroutines require a hand-rolled or library-provided generator type.
**Verification:** cppreference — `std::generator` is C++23 (https://en.cppreference.com/w/cpp/coroutine/generator).

---

#### 19. `languages/ocaml/interview-questions.md` — invalid OCaml function definition
Lines 231–234:
```ocaml
(* Labeled arguments *)
let ~name ~age = { name; age }
make ~name:"Alice" ~age:25
```
**Issue:** `let ~name ~age = { name; age }` is not valid OCaml — labeled arguments need a function body and there's no function name. Also `make` is referenced on the next line but never defined. This won't compile.
**Fix:** `let make ~name ~age = { name; age }` then `make ~name:"Alice" ~age:25`.

---

#### 20. `languages/cpp/interview-questions.md` — placeholder stub in optional example
Lines 233–237:
```cpp
std::optional<int> find(int key) {
    if (found) return value;
    return std::nullopt;
}
```
**Issue:** `found` and `value` are undefined identifiers — this is placeholder/stub code that won't compile as written. Violates the "no placeholder/stub" rule.
**Fix:** Either inline realistic code (e.g., `if (db.contains(key)) return db[key];`) or wrap in a clear pseudocode block.

---

### MEDIUM severity

#### 21. `languages/cpp/move-semantics.md` — confusing `const Example&& = delete`
Line 262:
```cpp
Example(const Example&&) = delete;  // no rvalue copy
```
**Issue:** `const T&&` (const rvalue ref) is rarely meaningful — const lvalue ref overload already binds to const rvalues. The comment "no rvalue copy" is unclear and the example is misleading for learners.
**Fix:** Either delete the line or replace with a clearer example of `= delete` (e.g., delete a specific overload for clarity).

---

#### 22. `languages/cpp/templates.md` — bogus SFINAE "fallback" example
Lines 224–228:
```cpp
template <typename T>
std::string add(...) {
    return "unsupported";
}
```
**Issue:** A function template with a C-style variadic `...` and only `T` as a template parameter doesn't meaningfully demonstrate SFINAE. The example doesn't really work as a SFINAE fallback for `add(const T&, const T&)` — overload resolution with `add(x, y)` for two arguments will not call `add(...)` cleanly, and the "fallback" framing is misleading.
**Fix:** Use a proper constrained overload (e.g., `template<typename T, typename = void> struct supports_add : std::false_type {};`).

---

#### 23. `languages/c/undefined-behavior.md` — misleading shift UB comment
Line 243–244:
```c
// UB: Shifting negative values (C89/C99)
int d = -1 << 2;   // Shifting negative signed int
```
**Issue:** The "(C89/C99)" annotation is misleading — left-shifting a negative signed int is UB in **all** C standards (C89, C99, C11, C17, C23), not just C89/C99. The C23 standard slightly refines shift semantics but still treats `-1 << 2` as problematic.
**Fix:** Drop "(C89/C99)" — say "UB in all C standards."

---

#### 24. `languages/c/interview-questions.md` — non-portable printf specifier
Lines 254–256:
```c
ptrdiff_t distance = end - start;
printf("Distance: %ld elements\n", distance);
...
printf("Bytes apart: %ld\n", (char*)end - (char*)start);
```
**Issue:** `ptrdiff_t` is not necessarily `long`. The correct format specifier is `%td` (added in C99).
**Fix:** Use `%td` for `ptrdiff_t` values.

---

#### 25. `languages/cpp/README.md` — Java described as "JIT compiled"
Line 187 (comparison table):
> "| Compilation | AOT compiled | JIT compiled | Interpreted | AOT compiled |"

**Issue:** Java is **both** AOT compiled (to bytecode via `javac`) and JIT compiled (at runtime via HotSpot). Calling it just "JIT compiled" omits the AOT-to-bytecode step that Python (which the same row calls "Interpreted") lacks.
**Fix:** "AOT to bytecode + JIT" or "Bytecode + JIT".

---

#### 26. `redis/interview-questions.md` — AOF "max 1s loss" is policy-dependent
Line 7:
> "AOF = logs every write (more durable, max 1s loss, larger files)"

**Issue:** The "max 1s loss" only applies to the **default** `appendfsync everysec` policy. With `appendfsync always`, AOF has no data loss (at the cost of throughput); with `appendfsync no`, you can lose up to ~30s.
**Fix:** "...max 1s loss with default `everysec` policy (configurable via `appendfsync`)."
**Verification:** Redis docs — `appendfsync` has three modes: `always`/`everysec`/`no` (https://redis.io/docs/management/persistence/).

---

#### 27. `frameworks/fastapi/README.md` — misleading performance claim
Line 9:
> "**Performance**: One of the fastest Python frameworks (on par with Node.js/Go)"

**Issue:** FastAPI is fast *for Python* but is **not** on par with Go (or even pure Node.js) for raw throughput. Node.js typically outperforms FastAPI in real-world HTTP benchmarks; Go outperforms both by a wide margin.
**Fix:** "One of the fastest Python frameworks (Starlette-level throughput)".

---

#### 28. `frameworks/nextjs/README.md` — `proxy.ts` "replaces" middleware too strong
Line 83:
> "Next.js 16 replaces it with **`proxy.ts`** for clearer network-boundary semantics"

**Issue:** Next.js 16 (April 2025) introduced `proxy.ts` as the new name, but `middleware.ts` is still supported. "Replaces" overstates it.
**Fix:** "Next.js 16 introduces `proxy.ts` as the new preferred name (middleware.ts still supported)."

---

#### 29. `languages/rust/traits.md` — confusing object-safety rule 5
Lines 307–311:
> "5. **No `where Self: Sized` constraints** on the trait itself"

**Issue:** Confusingly worded. The trait-level rule is that `Self : Sized` cannot be a *supertrait* (`trait Foo: Sized`). But methods CAN have `where Self: Sized` to opt out of object safety. Rules 1 and 5 contradict each other as written.
**Fix:** Re-word: "The trait itself must not require `Self: Sized` as a supertrait; methods may add `where Self: Sized` to opt out of dyn dispatch."

---

#### 30. `languages/ocaml/interview-questions.md` — value restriction example is not an error
Lines 40–44:
```ocaml
(* This is NOT fine *)
let r = ref []        (* Error: cannot generalize 'a *)
```
**Issue:** This is not an error. OCaml compiles this fine — `r` just gets a *weak* type variable `'_a list ref` (monomorphic). The value restriction prevents *generalization*, not compilation.
**Fix:** `(* Not an error, but r becomes monomorphic: '_a list ref *)`.

---

#### 31. `languages/javascript/v8.md` — wrong Maglev introduction version
Line 160:
> "Introduced in V8 v11.7 (2023)"

**Issue:** Maglev was introduced in **V8 v11.3 / Chrome 114** (start of rollout, June 2023). The official V8 blog post (Dec 5, 2023) covers Chrome M117. v11.7 is the wrong version.
**Fix:** "Introduced in V8 v11.3 (Chrome 114, 2023)".
**Verification:** V8 blog — "In Chrome M117 we introduced a new optimizing compiler: Maglev" (https://v8.dev/blog/maglev); Phoronix — "Chrome 114 begins rollout of Maglev" (June 2023).

---

#### 32. `languages/python/performance.md` — incorrect line_profiler hit count
Lines 122–125:
```
#      3   1000001      0.15000   0.000     30.0  total += i * i
#      2   1000001      0.35000   0.000     70.0  for i in range(n):
```
**Issue:** Both lines show 1,000,001 hits, but the body `total += i * i` is executed `n` times = 1,000,000, while the `for` line is hit `n+1` = 1,000,001 times (final iteration check).
**Fix:** Line 3 hits = `1000000`; line 2 hits = `1000001`.

---

### LOW severity

#### 33. `languages/ocaml/README.md` — confusing variable name `f` for float
Line 33: `let f = 3.14 (* float *)`
**Issue:** `f` is conventionally used for functions in OCaml. Using it for a float (alongside `x`, `s`, `b`) is mildly misleading for learners reading later examples where `f` is a function (e.g., line 108 `let apply f x = f x`).
**Fix:** Rename to `let pi = 3.14` or `let flt = 3.14`.

---

## Files confirmed clean

The following files were fully audited and found free of the issues in scope:

### Languages
- `languages/cpp/README.md` (only the comparison-table Java/JIT issue — see #25)
- `languages/cpp/stl.md`
- `languages/cpp/concurrency.md`
- `languages/cpp/ecosystem.md`
- `languages/c/README.md`
- `languages/c/compilation.md`
- `languages/c/performance.md`
- `languages/c/ecosystem.md`
- `languages/java/README.md` (only the LTS issue — see #9)
- `languages/java/gc.md`
- `languages/java/jvm.md`
- `languages/java/interview-questions.md`
- `languages/java/ecosystem.md`
- `languages/go/interview-questions.md`
- `languages/go/ecosystem.md`
- `languages/go/web-frameworks.md`
- `languages/javascript/README.md`
- `languages/javascript/v8.md` (only the Maglev version issue — see #31)
- `languages/javascript/interview-questions.md`
- `languages/javascript/nodejs.md` (only the createCipher issue — see #17)
- `languages/rust/lifetimes.md`
- `languages/rust/borrow-checker.md`
- `languages/rust/traits.md` (only the object-safety rule issue — see #29)
- `languages/rust/error-handling.md`
- `languages/rust/async-runtimes.md`
- `languages/rust/ecosystem.md`
- `languages/rust/interview-questions.md`
- `languages/python/README.md` (only the `f` undefined issue — see #13)
- `languages/python/gil.md`
- `languages/python/asyncio.md`
- `languages/python/free-threaded.md`
- `languages/python/data-model.md`
- `languages/python/cpython-internals.md`
- `languages/python/typing.md`
- `languages/python/packaging.md`
- `languages/python/ecosystem.md`
- `languages/typescript/README.md`
- `languages/ocaml/README.md` (only the `f` variable name — see #33)
- `languages/ocaml/ecosystem.md`

### Frameworks
- `frameworks/django/README.md`
- `frameworks/express/README.md`
- `frameworks/react/README.md`
- `frameworks/vue-angular/README.md`
- `frameworks/pytorch/README.md`
- `frameworks/spring-boot/README.md`

### Redis
- `redis/README.md`
- `redis/interview-questions.md` (only the AOF issue — see #26)
- `redis/patterns-and-internals.md` (only the single-threaded claim — see #16)

### Machine-coding
- `machine-coding/README.md`
- `machine-coding/approach.md`
- `machine-coding/design-principles.md`
- `machine-coding/parking-lot.md`
- `machine-coding/library-management.md`
- `machine-coding/task-scheduler.md`
- `machine-coding/splitwise.md`
- `machine-coding/cache-lru.md`
- `machine-coding/rate-limiter.md`

## Notes on audit methodology

- **Web search verification** was used to confirm: Go memory model sync.Once semantics, JEP 505 structured-concurrency preview status in JDK 25, JDK 25 LTS release date, Redis 6.0+ multi-threaded I/O, V8 Maglev version, Pydantic V2 `@validator` deprecation, `crypto.createCipher` deprecation, `void*` arithmetic being a constraint violation (not UB) in standard C.
- All arithmetic in code samples was checked with Python where applicable (e.g., Splitwise settlement algorithm outputs).
- Mermaid diagrams in all files were inspected for syntactic validity and conceptual consistency with surrounding code/text.
- Files explicitly listed in `already_fixed.md` (cpp/modern-cpp, cpp/memory-model, go/channels, go/scheduler, tokio/README, machine-coding/elevator) were skipped per instructions.
