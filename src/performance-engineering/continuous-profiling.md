# Continuous Profiling: Parca, Pyroscope, and Production Flame Graphs

Continuous profiling keeps a low-overhead sampler running against every production service at all
times, stores the resulting profiles as time-series data, and diffs them across deploys -- the
profiler stops being a tool you reach for and becomes a signal you own. Flame graph mechanics and
the ad-hoc tooling (`perf`, `async-profiler`, `py-spy`) live in [Flame Graphs](./flamegraph.md) and
[CPU Profiling](./cpu-profiling.md); this page is what changes when profiling never turns off.

## What Changes When the Profiler Never Turns Off

| Dimension | Ad-hoc profiling | Continuous profiling |
|---|---|---|
| When it runs | On demand, someone must decide to | Always on, scheduled and scraped |
| Question answered | "Why is this slow *right now*?" | "What got slower since the last deploy?" |
| Overhead tolerance | 999 Hz is fine for a 30-second capture | Budgeted below ~1-2% CPU, permanently |
| Data lifetime | Local file, usually discarded | Stored, indexed, retained, diffable |
| Coverage | The service someone remembered | Fleet-wide, including rarely-hit services |

Two failure classes justify the always-on mode: **slow regressions nobody profiles for** (a 4% CPU
burn across 4,000 pods never triggers a manual session but shows up instantly in a deploy diff), and
**rare profiles of scarce failures** (a leak that surfaces after five days needs labeled profiles
already collected).

## Instrumentation Modes: eBPF Agents vs. Language Agents

Every continuous profiler ships one of two collectors, and the trade is the same everywhere:

- **eBPF / kernel agent** (Parca Agent, the OpenTelemetry eBPF profiler): samples via `perf_event`
  timers and walks stacks in-kernel -- system-wide, zero application changes, native and kernel
  frames. Blind to JIT runtimes unless the runtime cooperates; needs frame pointers or DWARF.
- **Language agents / SDKs** (Go `runtime/pprof`, JVM JFR and async-profiler, Pyroscope SDKs,
  py-spy): hook the runtime. They see through JIT inlining and expose runtime-native profile types
  (allocations, mutex, block) no kernel sampler can see. Cost: per-language install work.

Because fleets are polyglot, real deployments run both. All paths converge on pprof -- a protobuf
schema (`profile.proto`) of samples, values, and labels -- feeding the same backend:

```text
  SDK push / agent scrape / OTel eBPF profiler   (all emit pprof)
        |
        v
  profiling backend: fold samples into stacked trees, attach labels
        |
        +---> profile store on object storage
        |     (Parca: FrostDB/Parquet; Pyroscope v2: direct writes)
        +---> query + diff UI (flame graphs, deploy diffs,
              per-type / per-label views)
```

The OTel profiling signal rides the same OTLP pipeline as traces and metrics, making the eBPF
collector a drop-in addition to an existing [OpenTelemetry deployment](../backend/observability/opentelemetry.md).

## The Overhead Budget

Overhead is dominated by stack unwinding, not by taking the sample. Budgets that hold up:

| Collector mode | Typical always-on setting | Dominant cost | Notes |
|---|---|---|---|
| eBPF CPU, frame pointers | 20-100 Hz per core | In-kernel stack walk | Cheap per sample; needs `-fno-omit-frame-pointer` builds |
| eBPF CPU, DWARF fallback | 20-50 Hz per core | Userspace DWARF unwind | Kilobytes of stack copies per sample; rate must drop |
| Go runtime CPU | 100 Hz per process | Runtime signal handler | Built in, negligible to enable |
| JVM (JFR method sampling) | ~100 Hz (10 ms period) | Safepoint-free stack walk | async-profiler goes higher via perf_events |
| Go heap (allocs) | 1 sample per ~512 KiB | Sampled, not traced | `MemProfileRate` default 512 KiB |

Two rules interviewers probe for. First, the **sample rate is bounded by unwind cost, not event
cost**: the timer tick is free, walking a 100-frame stack is not -- hence always-on rates an order
of magnitude below ad-hoc rates. Second, **allocation profiles are sampled on purpose**: Go records
roughly one allocation per 512 KiB and scales counts up, so alloc profiles show *relative* volume
per stack, never exact bytes.

## Profile Types: What Each One Answers

pprof models every profile the same way -- samples, value(s), labels -- but the types answer
different questions:

| Profile type | Question it answers | Usual source | Common gotcha |
|---|---|---|---|
| cpu | Where is CPU burned? | perf_event/eBPF or runtime timer | Blind to blocked time entirely |
| allocs (alloc_space/objects) | What allocates the most? | Runtime heap sampling | Sampled counts, scaled estimates |
| inuse (inuse_space/objects) | What is live right now? Leaks? | Runtime heap profile | GC timing skews the window |
| mutex | Where do threads wait on locks? | Runtime mutex profiling | Often disabled by default in Go |
| block | Where do threads block on sync primitives? | Runtime block profiling | Rate-limited; biased toward hot paths |
| off-cpu / wall | Where does wall-clock go? | eBPF sched_switch tracing | Includes intentional sleeps; noisy |

The runtime-exposed types (mutex, block, allocs) are exactly the ones an eBPF agent cannot see -- the
cleanest answer to "why not just eBPF everything?": eBPF owns cpu and off-cpu; the runtime owns
allocation and lock internals.

## Diff Profiling Across Deploys

The core workflow is a loop: tag every profile with the deploy identity (git SHA, version label),
keep the history, and compare equal-length windows across the deploy boundary. The demo rebuilds the
call tree from two folded snapshots -- the format flame graphs render from -- computes leaf
self-time, draws ASCII flame bars, and flags regressions over threshold:

```python
# Folded snapshots for deploy N-1 and N: stack -> sample count.
# N-1: 43 samples of one pod at 100 Hz. N: 42 after a release that
# regressed encode, dropped v1_join, added a new cache path.
BEFORE = {
    "main;handle;encode;json.dumps": 14,
    "main;handle;db.query;net.recv": 9,
    "main;handle;gc.collect": 8,
    "main;handle;auth;pbkdf2": 7,
    "main;handle;v1_join;sort": 5,
}
AFTER = {
    "main;handle;encode;json.dumps": 21,
    "main;handle;db.query;net.recv": 8,
    "main;handle;gc.collect": 6,
    "main;handle;cache;deser": 4,     # new leaf, no baseline
    "main;handle;auth;pbkdf2": 3,
}


def leaf_self_times(folded):
    """Folded stacks -> {(frames...): self samples}."""
    root, leaves = {}, {}
    for stack, n in folded.items():
        node = root
        for frame in stack.split(";"):
            node = node.setdefault(frame, {})
        node[None] = node.get(None, 0) + n          # None = self-time slot
    todo = [(root, ())]
    while todo:
        node, path = todo.pop()
        for frame, sub in node.items():
            if frame is None:
                continue
            leaves[path + (frame,)] = sub.get(None, 0)
            todo.append((sub, path + (frame,)))
    return leaves


def top_bars(folded, width=36):
    leaves = leaf_self_times(folded)
    total = sum(leaves.values()) or 1
    for path, n in sorted(leaves.items(), key=lambda kv: -kv[1])[:5]:
        print("%3d  %-36s  %s" % (n, "#" * round(width * n / total),
                                  ";".join(path[-2:])))


print("== deploy N-1 (before): self-time, top 5 leaves ==")
top_bars(BEFORE)
print("\n== deploy N (after): self-time, top 5 leaves ==")
top_bars(AFTER)
print("\n== regressions (>= +50% and >= +2 samples) ==")
b, a = leaf_self_times(BEFORE), leaf_self_times(AFTER)
for s in sorted(set(b) | set(a), key=lambda s: -(a.get(s, 0) - b.get(s, 0))):
    delta = a.get(s, 0) - b.get(s, 0)
    if delta >= 2 and (b.get(s, 0) == 0 or delta / b.get(s, 0) >= 0.5):
        print("  %s  %d -> %d samples (+%d)"
              % (";".join(s), b.get(s, 0), a.get(s, 0), delta))
```

Output (deterministic; verified byte-identical across runs):

```text
== deploy N-1 (before): self-time, top 5 leaves ==
 14  ############                          encode;json.dumps
  9  ########                              db.query;net.recv
  8  #######                               handle;gc.collect
  7  ######                                auth;pbkdf2
  5  ####                                  v1_join;sort

== deploy N (after): self-time, top 5 leaves ==
 21  ##################                    encode;json.dumps
  8  #######                               db.query;net.recv
  6  #####                                 handle;gc.collect
  4  ###                                   cache;deser
  3  ###                                   auth;pbkdf2

== regressions (>= +50% and >= +2 samples) ==
  main;handle;encode;json.dumps  14 -> 21 samples (+7)
  main;handle;cache;deser  0 -> 4 samples (+4)
```

The mechanics generalize: the diff compares *shares*, the threshold demands both relative change
(+50%) and an absolute floor (+2 samples), and a vanishing stack (`v1_join;sort`) is never flagged --
it disappears. Parca and Pyroscope diff UIs add traffic normalization. Other pitfalls: **sample-count
mismatch** (compare normalized shares, not raw counts); **JIT warmup** (align on process age, not
deploy time); **minimum-sample floors** (2 -> 5 samples reads as +150% and is pure noise).

## Cardinality, Storage, and Retention Costs

Profiles inherit the label-explosion problem from metrics. Each stored profile object is roughly:

```text
 profiles = services x instances x profile_types x scrape_windows x label_sets
```

`service_name`, `pod`, `version`, `region` multiply exactly as the multiplication rule in [Metrics
Cardinality Explosions](../sre/metrics-cardinality.md) describes, with one mitigating structural
difference: the payload is a folded tree, not a counter. Ten thousand samples in a 10-second window
collapse to a few hundred unique stacks, so retention costs object-storage bytes rather than
per-series in-memory state -- month-scale retention stays affordable.

- **Parca** (Polar Signals' OSS profiler): the agent discovers targets from Kubernetes or systemd,
  profiles system-wide via eBPF, and speaks pprof in and out. The server stores samples in FrostDB,
  a columnar database built for observability -- Arrow-style columns, Parquet files on object
  storage.
- **Grafana Pyroscope**: Grafana Labs merged its Phlare backend with the acquired Pyroscope project
  (2023); the result is the multi-tenant aggregation system documented as Grafana Pyroscope. The v1
  architecture aligned with Prometheus/Mimir; as of Pyroscope 2.0 the server writes profiles
  directly to object storage, dropping in-memory ingesters and local disks. It also ingests OTLP
  profiles and renders them in Grafana Profiles Drilldown.

Profiles are *append-only, immutable, tree-aggregated* data -- a shape that favors columnar/object
layouts and makes cheap long retention, and therefore historical deploy diffs, an architectural
property rather than a bolted-on feature.

## How Production Flame Graphs Mislead

[Flame Graphs](./flamegraph.md) covers how folded stacks become boxes; this is what to distrust:

1. **Merged stacks destroy causality.** A wide `handle_request` bar can mean one pathological
   request, ten thousand normal ones, or anything between; tail latency is invisible in the
   aggregation. For per-request ordering you need flame charts or traces.
2. **Missing leaf frames misattribute time.** JIT frames lacking debug info, cgo boundaries,
   frame-pointer-omitted C++ builds, and failed kernel unwinds collapse samples onto the nearest
   *known* frame. An unexpected `[unknown]` bucket means attribution is broken.
3. **Color carries no meaning by default.** The classic `flamegraph.pl` palette assigns warm hues
   essentially at random -- red is not "hotter" than orange. Red/green semantics exist only in *diff*
   flame graphs (regression/improvement).
4. **The on-CPU flame graph says nothing about off-CPU time.** Timer samples record only intervals
   where the thread was running. The widest bar being 15% while p99 latency triples is not a
   contradiction: the wait sits in I/O, locks, or scheduler queues, visible only via off-CPU
   profiling or runtime block/mutex profiles. "Red bar" in a CPU diff means more on-CPU samples --
   never confuse it with the actual off-CPU wait that made users angry.

## Interview Angle

- *Keep overhead under control permanently?* Sample rate bounded by unwind cost, frame-pointer
  builds, allocation sampling instead of tracing -- and verify by profiling the profiler.
- *Where does a gigabyte-per-day heap leak show up?* In `inuse_objects`/`inuse_space` profiles over
  days -- the case for retention measured in months, not in any single CPU or alloc window.

## References

All probed live (HTTP 200) at write time.

- Grafana Pyroscope documentation: <https://grafana.com/docs/pyroscope/>
- Pyroscope v2 architecture (direct-to-object-storage writes): <https://grafana.com/docs/pyroscope/latest/reference-pyroscope-v2-architecture/>
- OpenTelemetry eBPF profiler (OTLP profile ingestion): <https://grafana.com/docs/pyroscope/latest/configure-client/opentelemetry/ebpf-profiler/>
- Parca docs, architecture and eBPF whole-system agent: <https://www.parca.dev/docs/overview>
- Parca storage model and FrostDB: <https://www.parca.dev/docs/storage>
- google/pprof and the `profile.proto` schema: <https://github.com/google/pprof>
- Polar Signals, "Profiling internals: hardware timers and eBPF" (2026): <https://www.polarsignals.com/blog/posts/2026/03/25/profiling-internals-hardware-timers-and-ebpf>
- Brendan Gregg, Flame Graphs: <https://www.brendangregg.com/flamegraphs.html>
