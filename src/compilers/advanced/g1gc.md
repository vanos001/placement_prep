# G1GC (Garbage-First Garbage Collector)

G1GC (Garbage-First Garbage Collector) is the default garbage collector in Java 9+ (replacing Parallel GC). It targets predictable pause times (default 200 ms) on heaps from 4 GB to 64 GB, balancing latency and throughput. This page covers the region-based heap model, the marking phases, the evacuation pauses, and the production tuning.

## The Region-Based Heap

G1GC divides the heap into ~2048 regions of equal size (1-32 MB each):

```text
Heap layout (regions):
┌────────┬────────┬────────┬────────┬────────┐
│  E  │  E  │  S  │  O  │  H  │  O  │  H  │ ...
└────────┴────────┴────────┴────────┴────────┘

E = Eden region (new allocations)
S = Survivor region (survived 1 collection)
O = Old region (survived many collections)
H = Humongous region (single large object)
```

Regions are dynamically assigned: an empty region can become Eden, Survivor, or Old as needed. This is the "garbage-first" naming: G1 picks the regions with the most garbage (highest collection efficiency) and collects them first.

## The Generational Model

G1 is logically generational (Eden, Survivor, Old) but physically region-based. The region's role can change:
- An empty region becomes Eden when allocation needs space.
- An Eden region's surviving objects are copied to a Survivor region.
- A Survivor region's surviving objects (after several young GCs) are promoted to Old.

This is different from the older Parallel GC, which has fixed Eden/Survivor/Old regions. G1's flexibility allows fine-grained collection: only some Eden regions need to be collected, not the whole Eden.

## The GC Cycle

G1 has two cycles: the young collection (frequent, fast) and the mixed collection (less frequent, larger).

### Young Collection (Pause)

```text
1. Stop-the-world pause.
2. Find all Eden regions with live objects.
3. Copy live objects to Survivor regions (or to Old, if old enough).
4. Empty the collected Eden regions.
5. Resume application.
```

A young collection is typically 50-200 ms (depending on heap size and Eden region count). It happens when Eden fills (typically every few seconds).

### Concurrent Marking

G1 runs concurrent marking periodically (default every 5 hours or when heap > 45% full):

```text
1. Initial mark (STW, piggybacks on a young GC).
2. Root region scan (concurrent): scan remembered sets of regions pointing into old gen.
3. Concurrent mark: walk the object graph, marking live objects.
4. Remark (STW): finalize marking.
5. Cleanup (STW): identify "garbage" regions (no live objects) and add to the collection set.
```

The concurrent phases don't stop the application; only the STW pauses (initial mark, remark, cleanup) do. These pauses are typically < 100 ms.

### Mixed Collection (Pause)

After concurrent marking identifies garbage regions, G1 can do "mixed" collections that include Old regions:

```text
1. Stop-the-world.
2. Collect: Eden regions (always) + some Old regions (the "garbage-first" choice).
3. Copy surviving objects to free regions.
4. Resume application.
```

Mixed collections reduce the Old generation's size gradually. A typical mixed collection cycle does 8 mixed collections (over ~10 seconds), each collecting a few Old regions.

## Humongous Objects

Objects larger than 50% of a region are "humongous" and get their own region(s). G1 treats humongous objects specially:
- Allocated directly in Old (no Eden phase).
- Marked and collected during concurrent marking (no copy in young GC).
- Often a source of memory pressure (a 1 GB humongous array takes 32 32MB regions).

## Tuning

G1's main tunables:

```bash
java -XX:+UseG1GC -Xmx16g -XX:MaxGCPauseMillis=200 -jar myapp.jar
```

- `MaxGCPauseMillis`: target pause time (default 200 ms). G1 adjusts region count and collection set size to meet this.
- `G1HeapRegionSize`: region size (default: chosen by JVM based on heap; 1 MB for <4 GB, 32 MB for >64 GB).
- `InitiatingHeapOccupancyPercent`: trigger concurrent marking when Old > this % (default 45%).
- `G1NewSizePercent` / `G1MaxNewSizePercent`: min/max young gen size (default 5%/60%).
- `G1MixedGCLiveThresholdPercent`: don't include an Old region in mixed collection if it's > this % live (default 85%).

The most important tuning: don't over-tune. G1 is designed to work well with defaults. Tuning one parameter (e.g., `MaxGCPauseMillis=50`) may force G1 to do smaller, more frequent GCs — sometimes worse.

## Comparison to Other Collectors

| Aspect | Serial | Parallel | G1GC | ZGC | Shenandoah |
|--------|--------|---------|------|------|------------|
| Default in | Java <9 | Java 6-8 | Java 9+ | — | — |
| Pause time | High | High | 200 ms (default) | <10 ms | <10 ms |
| Heap size | Small | Small-medium | Medium-large (up to 64GB) | Up to 16 TB | Up to 64 GB |
| Throughput | Low | High | Medium | Medium | Medium |
| Best for | Small heaps | Batch jobs | Default Java apps | Latency-critical | Latency-critical |

G1GC is the "reasonable default" — most Java applications work well with it without tuning.

## Production Monitoring

G1 logs (Java 9+ unified logging):

```bash
java -Xlog:gc*,gc+heap=debug:file=gc.log:time,level,tags -jar myapp.jar
```

The log includes:
- Per-GC pause time, Eden/Survivor/Old size.
- Concurrent phase durations.
- Humongous allocations.
- Mixed collection choices.

Tools like GCViewer, GCEasy, and Java Flight Recorder (JFR) parse these logs to visualize GC behavior.

## Common Pitfalls

1. **Setting `MaxGCPauseMillis` too low.** A target of 50 ms forces G1 to do tiny, frequent GCs — overall throughput drops. The default 200 ms is usually best.

2. **Forgetting that humongous objects cause pauses.** A 1 GB array allocation in a hot loop creates humongous regions, slowing concurrent marking. Either avoid large arrays or use byte buffers (ByteBuffer.allocateDirect).

3. **Forgetting that G1GC's pauses scale with live set.** A young GC's pause is proportional to the live data being copied (Eden + Survivor surviving objects). Large young gen → long pauses.

4. **Trusting `InitiatingHeapOccupancyPercent` to be optimal.** The default 45% may be too low (frequent marking) or too high (rare marking, larger pauses). Monitor and adjust per workload.

5. **Forgetting that G1's mixed collections need to complete.** If mixed collections are interrupted (e.g., by a young GC that fills Eden), the cycle restarts. Reduce mixed collection set size (`G1MixedGCCountTarget`) if mixed cycles don't complete.

6. **Confusing G1GC's "old gen" with Parallel GC's.** G1's Old is region-based (no fixed size); Parallel's is contiguous. Tuning parameters differ.

## References

- [JEP 247: G1GC as default in Java 9](https://openjdk.org/jeps/247)
- [HotSpot G1GC source code](https://github.com/openjdk/jdk/tree/master/src/hotspot/share/gc/g1)
- Monika Beck et al., "[The Garbage-First Garbage Collector](https://www.researchgate.net/publication/220832694_The_Garbage-first_Garbage_Collector)" (SIGOPS 2008)
- [Java 9+ G1GC tuning guide](https://docs.oracle.com/en/java/javase/21/gctuning/garbage-first-garbage-collector-tuning.html)
- [G1GC vs ZGC vs Shenandoah comparison](https://malloc.se/blog/zgc-jdk21)
- [JEP 377: ZGC production (Java 15)](https://openjdk.org/jeps/377)
- [LWN: G1GC in modern Java (2020)](https://lwn.net/Articles/816426/)
