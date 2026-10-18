# "GC languages can't leak"

## Overview

This page examines the claim that garbage collection solved memory leaks.
Garbage collectors automate one thing precisely: reclaiming objects that are
*unreachable*. Leaks in GC'd languages are objects that remain reachable but
are never used again — a problem the collector is designed not to touch. Add
off-heap/native memory and classloader lifetime, and a "GC language" offers
at least three leak classes the collector cannot see. This page states the
claim fairly, shows a five-line leak that grows without bound, and covers
how such leaks are diagnosed with heap dumps and retention paths.

## The Claim, Stated Fairly

The strongest common form of the claim is: "Java, Go, and Python reclaim
memory automatically, so a program written in them cannot leak memory; the
class of bugs that made C programs slow down and die does not exist here."
Stated this way, the claim is not a caricature; it is what early Java-era
marketing and a generation of course material implied, and what engineers
reasonably conclude from never having called `free()`.

The claim deserves its fairness because the kernel is real. Garbage
collection genuinely eliminates the manual-management bug classes: the
forgotten free, the double free, the dangling pointer, the allocation whose
owner nobody remembers. Those are real, painful, and largely gone. The
question is whether "the collector frees unreachable objects" honestly
compresses to "programs cannot leak".

## Verdict

**False.** A leak is unbounded growth of memory the program no longer uses —
and the standard counterexample is five lines: a static, put-only map. The
collector is functioning perfectly while the process dies; reachability, not
collection, is the leak's currency.

## Why People Believe It

The kernel of truth is threefold. First, the collector's guarantee is
genuine: any object with no path from the roots is eventually reclaimed, so
the C-style leak — memory that is allocated, lost, and never freeable —
cannot happen. Second, the experience base agrees: most application code in
GC'd languages runs for months without a leak, because most object
lifetimes are stack-like and end when the frame returns. Third, the
replacement of `malloc`/`free` removed the *visible* mechanics, so nothing
in the code reminds anyone that object lifetime is still a design decision.

What disappears in compression is the word *unreachable*. The collector's
contract is about paths from roots, not about usefulness. A map that grows
forever, a listener registered a million times, a native buffer masked by a
tiny wrapper object, a classloader pinned by one forgotten thread — all
perfectly reachable, all perfectly collectible-never.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "GC prevents leaks" | GC reclaims unreachable objects; leaks are *reachable* objects that are never used again |
| "Memory is managed" | The heap is managed; native memory, direct buffers, and memory-mapped regions are not in the heap and not in the histogram |
| "The runtime handles lifetime" | The runtime handles *reclamation*; you still design *lifetime* policy — who holds what, for how long |
| "Caches are free" | An unbounded cache is an unbounded retention structure; "cache" and "leak" differ only by a bound |
| "OOM means heap full" | Containers kill on *total* memory (cgroup limit); a process can be OOMKilled with a mostly-empty heap |

The correct sentence: "GC removes manual reclamation, not lifetime design.
Memory leaks when reachable-but-useless objects (or off-heap allocations
masked by reachable wrappers) accumulate without bound."

## Where It Breaks

**The five-line leak.** The canonical unbounded leak in any GC language:

```java
static final Map<String, byte[]> SESSION_CACHE = new HashMap<>();

static void login(String userId, byte[] session) {
    SESSION_CACHE.put(userId, session);  // put-only: no eviction, no TTL, no bound
}
```

Do the arithmetic: 100,000 logins per day at 64 KiB of retained session
payload each is 6.4 GB of live data per day — about 6.0 GiB. On an 8 GiB
heap, the map alone exhausts it in roughly 1.3 days (reasoning arithmetic,
not a benchmark). Before that, the GC does exactly what it is supposed to:
as the heap fills it collects everything collectible, pauses stretch, and
finally the collector gives up and throws `OutOfMemoryError` — with a heap
whose live set is *legitimately* reachable all the way from the static
root. The Python equivalent is a module-global dict with the same put-only
shape; refcounting will never save it, because every entry has a referee.

**Listener and callback registration.** Every `registerListener` call
without a matching unregister adds a path from a long-lived object
(the event bus) to a short-lived one (the widget, the request handler, the
Activity context). Android's classic leaked-`Activity` bug is exactly this:
one static field holding a Context pins the entire view hierarchy and its
bitmaps. Ten thousand registrations at, say, 50 KiB of retained view tree
is 500 MB of "garbage" the collector will never collect — reachable means
collectible-never.

**Off-heap and native memory.** A `DirectByteBuffer` in Java allocates
*outside* the heap; the native block is released only when the small heap
wrapper is collected (or via explicit deallocation). A service churning
direct buffers shows a flat heap histogram while native RSS climbs — until
the container's cgroup limit ends the process with an `OOMKilled`, not an
`OutOfMemoryError`, and the heap dump shows nothing. The same class covers
native caches embedded in libraries and any `malloc`'d region referenced
only through JNI. The claim's blind spot is total here: the "managed
runtime" never managed this memory in the first place.

**Classloader leaks.** In application servers and hot-reload environments,
redeploying a web app creates a new classloader per deployment. If anything
from the old deployment survives — a static cache in one of its classes, a
thread the app started and never stopped, a driver registered in a
shared registry — the old *classloader* stays reachable, and with it every
class, static field, and interned object of that deployment. Fifty retained
deployments at ~50 MB of classes and statics each is ~2.5 GB of untouchable
memory (reasoning arithmetic), presenting as `Metaspace`/`OutOfMemoryError:
Metaspace` after the Nth redeploy. One retained object per deployment is
enough; leaks per redeploy are the bug class, not leaks per request.

**Diagnosing: retention paths, not histograms.** The method that works:
capture a heap dump (`jcmd <pid> GC.heap_dump`, or a dump triggered at OOM),
then in an analyzer (Eclipse Memory Analyzer and similar) open the
*dominator tree* and ask for the *path to GC roots* of the biggest
retainers — the shortest reference chain keeping the object alive. The
retention path answers the only question that matters: "who is holding
it?" For Python: `tracemalloc` snapshot diffs localize the allocation site,
`gc.get_referrers()` lists who references a suspect object, and reference
graphing tools (objgraph) draw the chain. Two dumps taken minutes apart,
diffed by dominator size, turn "memory grows" into "this map, held by this
static, grown by this call site."

## Practical Implications

- Bound every cache by construction: size limits with eviction, TTLs, or
  weak references (`WeakHashMap`-style keys, Python's `weakref`) where the
  lifetime should be tied to the client.
- Register and unregister symmetrically; treat "add listener" without a
  removal path as a review-blocking defect in long-lived processes.
- Watch RSS and cgroup memory, not just the heap histogram; in containers,
  size the limit for heap *plus* native plus metaspace, or the kernel will
  enforce the budget for you at the worst moment.
- On `OutOfMemoryError` or OOMKill, reach for heap dumps and retention
  paths before changing `-Xmx`; growing the heap buys days and hides the
  unbounded structure.
- In hot-reload environments, redeploy-stability-test: after N redeploys,
  classes from old deployments must be collectible; a leak here grows per
  deploy, not per request.
- Say "the GC frees unreachable objects" — not "the GC prevents leaks" —
  in design reviews; the second sentence has shipped many first leaks.

## Interview Questions

### Show me a memory leak in Java or Python, in a few lines, and explain why the GC cannot fix it.

A static, put-only map (`static Map<K,V>` with only `put`, or a
module-global dict): entries stay reachable from a root forever, so the
collector's contract — reclaim unreachable objects — never applies.
Arithmetic makes it concrete: 100,000 entries/day at 64 KiB each is ~6 GiB
of live data per day on an 8 GiB heap. The fix is a bound: eviction, TTL,
or weak references.

### A containerized Java service's RSS grows daily, but the heap histogram is flat and Full GCs are rare. What do you investigate?

Off-heap growth: direct `ByteBuffer`s (released only when heap wrappers are
collected), native library caches, metaspace/classloader retention (hot
redeploys), thread stacks, and memory-mapped files. Tools: `NativeMemoryTracking`
in the JVM, RSS versus heap dashboards, two heap dumps diffed by dominator
size, and the cgroup memory accounting — the container kills on total RSS,
not on heap occupancy.

### What is a classloader leak, and why can one static field break an application server's redeploys?

A surviving reference from an old deployment (static field, spawned thread,
registered driver) pins that deployment's classloader; the classloader
references all its classes, which reference their statics. Retained memory
then grows per redeploy until `Metaspace` is exhausted. The fix is
lifecycle discipline: stop threads, deregister drivers/listeners, and avoid
static caches in reloadable code.

## Key Takeaways

- GC automates reclamation of *unreachable* objects; leaks are
  *reachable* objects that are dead by intent — the collector is the wrong
  tool by design.
- The five-line put-only map is the canonical leak; "cache without a bound"
  and "leak" are the same structure with different marketing.
- Off-heap/native memory and classloader retention are leak classes the
  heap-based mental model cannot even see; containers kill on total RSS.
- Diagnosis is a reference-graph problem: heap dump, dominator tree, path
  to GC roots — or `tracemalloc`/`gc.get_referrers()` in Python.
- The honest sentence is "GC languages remove manual *freeing*, not
  lifetime *design*"; the design task survives in every managed runtime.

## Cross-References

- [Follow-up Tree: Garbage Collection](../followup-tree/garbage-collection.md)
  — the GC escalation chain this claim claims to end
- [Connection Atlas: GC & Memory Management](../connection-atlas/gc-memory-management.md)
  — how collector mechanics shape the retention behavior above
- [Java Runtime](../../languages/process-runtime/java.md) — heap, native
  memory, and classloading in the JVM
- [Python GIL](../../languages/python/gil.md) — the same runtime's
  refcounting-plus-cycle-GC memory story
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- Python Software Foundation. *gc — Garbage collector interface* and
  *tracemalloc* documentation — cycle collection, snapshot diffs.
  <https://docs.python.org/3/library/gc.html>
  <https://docs.python.org/3/library/tracemalloc.html>
- Python Software Foundation. *weakref — Weak references*.
  <https://docs.python.org/3/library/weakref.html>
- Oracle. *java.lang.ref package* API documentation — reference semantics
  under which direct-buffer natives are released.
  <https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/lang/ref/package-summary.html>
- B. Goetz, T. Peierls, J. Bloch, J. Bowbeer, D. Holmes, and D. Lea.
  *Java Concurrency in Practice*. Addison-Wesley, 2006 — lifetime and
  ownership discipline in managed runtimes, cited by title.
- Eclipse Memory Analyzer (MAT) — dominator tree and "path to GC roots"
  retention analysis, cited by name.
