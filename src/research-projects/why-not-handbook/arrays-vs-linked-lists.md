# Arrays vs Linked Lists

## Overview

The textbook comparison is three cells long: arrays have O(1) indexing and O(n) middle insertion; linked lists have O(1) insertion/deletion given a node and O(n) indexing. From this, generations of students concluded that linked lists are "better for insertion-heavy workloads". The conclusion survives exams and dies in production, because it ignores the two things that dominate real performance on modern hardware: memory layout and what it actually costs to *obtain* the node pointer that makes insertion O(1). Contiguous arrays enjoy cache lines, hardware prefetching, and per-element memory overhead of zero; linked lists pay a pointer (8 bytes) plus allocator headers per node and chase pointers scattered across the heap. Meanwhile, the array's O(n) insertion is a fast linear memmove, while the linked list's O(1) insertion usually sits behind an O(n) search to find the insertion point — so the honest workload comparison is often "O(n) fast constant" vs "O(n) slow constant", not O(n) vs O(1).

This page applies the [handbook framework](./index.md): mechanisms, complexity against reality, failure modes, the conditions where linked lists genuinely win, and a decision framework.

## Mechanisms

**Dynamic array (vector, ArrayList, slice).** A single contiguous allocation holds elements end to end. Element *i* lives at `base + i × sizeof(T)` — one multiply-add, no dereference chain. Appending past capacity triggers reallocation: allocate a new block (typically 1.5×–2× — C++ implementations commonly use 1.5 or 2; Java's ArrayList grows 1.5×), copy all elements, free the old block. Geometric growth is what makes append amortized O(1): doubling means each element is copied at most log₂(n) times across its lifetime, so n appends cost O(n) total copies. Deletion from the middle shifts the tail down — a `memmove` of `(size − i) × sizeof(T)` bytes, which is a highly optimized streaming operation even though it is asymptotically O(n).

**Linked list (singly or doubly).** Each node is separately heap-allocated and contains the element plus one or two pointers. Insertion or deletion *given a node pointer* relinks a constant number of pointers and touches nothing else. Iteration and indexing follow pointers: to reach element *i* you must dereference *i* links, and each dereference is a dependent load — the CPU cannot fetch node *i+1* until node *i* has been read, so the memory-level parallelism that prefetchers and out-of-order cores rely on is structurally unavailable. This is the pointer-chasing problem: latency becomes `i × memory-latency` instead of a pipelined stream.

## Cache Lines, Prefetching, and the Real Cost Model

A modern CPU moves memory in cache lines of 64 bytes (128 on some systems). A contiguous array of 8-byte elements packs 8 elements per line; scanning it streams lines from memory at full prefetcher speed, and the last read warms exactly the data the next iteration needs. A linked-list node holding one 8-byte element plus two 8-byte pointers plus 16–32 bytes of allocator metadata occupies its own cache line, of which maybe a quarter is payload. Traversing n nodes touches n distinct cache lines, most of them cold, each a full memory-latency stall with no prefetch possible (the next address is unknown until the current node is read). Drepper's "What Every Programmer Should Know About Memory" (LWN, 2007) remains the canonical treatment: on typical hardware, sequential access runs roughly an order of magnitude (often more) faster than dependent pointer chasing, and the gap widens as working sets exceed cache.

This rewrites the interview clichés:

- **"O(1) insertion" is conditional.** It requires the node pointer in hand. If you must *find* the insertion point in a singly linked list, that is an O(n) traversal of cold, pointer-chased memory — far slower than the array's O(n) shift over warm contiguous bytes. Doubly linked lists with an iterator improve the setup, but then see the iterator-invalidation asymmetry below.
- **"O(n) deletion/insertion" in arrays is cheap-O(n).** A memmove of POD types is a vectorized streaming copy at multiple GB/s. The linked list's O(1) relink is constant but its traversal constant is brutal. Benchmarks repeatedly show array-based containers beating list-based ones even at workloads chosen to favor lists, until elements are large enough that shifting cost dominates (elements of hundreds of bytes or non-movable types).
- **Iteration is the extreme case.** Array iteration vectorizes, unrolls, and prefetches; list iteration is a serial chain of dependent loads. Same asymptotic O(n), and routinely a 5–20× constant-factor difference — which is why "linked lists for iteration-heavy code" is backwards.

## Amortized Claims in Practice

The dynamic array's amortized O(1) append also deserves its failure-mode audit. Three real costs hide in the amortization:

- **Reallocation stalls**: the append that triggers growth copies the entire array and allocates a new block — for a 1 GB vector, a 1 GB copy. Latency-sensitive systems pre-`reserve()` capacity or use incremental-growth arenas to avoid the spike (the same amortization-vs-deadline issue as hash-table rehash storms — see [Binary Search vs Hashing](./binary-search-vs-hashing.md)).
- **Iterator/pointer invalidation**: reallocation moves every element, so references, pointers, and iterators into the vector are invalidated — a classic source of use-after-free bugs. Linked-list iterators stay valid across any number of inserts elsewhere in the list.
- **Fragmentation and allocation count**: a linked list of n nodes makes n separate allocations, potentially scattered across arenas; vectors make one. In long-running processes, many small allocations interleave with other threads' allocations, so even "adjacent" list nodes are often far apart in address space, destroying what little spatial locality remains.

## When Linked Lists Genuinely Win

No strawmen — the list is the right structure in specific, identifiable situations:

- **Stable iterators and references under mutation.** If other code holds long-lived references into the collection while it grows and shrinks (observable lists, subscription registries), the list's guarantee — node addresses never change — is the whole point. A vector cannot offer it without indirection (see slot maps below).
- **Intrusive lists.** When the node structure is embedded in the object itself (the Linux kernel's `list_head` is the canonical example), there is no per-node allocation at all: the "allocation cost" argument vanishes, the object's lifetime governs the node, and unlinking an object from a list is O(1) with zero memory traffic beyond the two neighbor pointers. Kernels, allocators, and lock-free structures use intrusive lists pervasively for exactly these reasons.
- **O(1) splice.** Moving a contiguous run of nodes between two lists relinks a constant number of pointers regardless of run length — `std::list::splice` is genuinely O(1) (or O(s) to get the iterator, but the move itself is constant). The same operation on arrays is a full copy. Workflows that constantly transfer segments between collections (task schedulers moving whole queues) benefit structurally.
- **LIFO stacks and freelists where the node exists anyway.** A singly linked freelist — push/pop at the head — is ideal when nodes are recycled objects (allocator free lists, coroutine frames, buffer pools). No ordering requirement, no traversal, O(1) both ends, and the node memory is already paid for.
- **Bounded, predictable operations.** List operations allocate nothing (intrusive) and copy nothing, so worst-case timing is stable — relevant in real-time contexts where a vector's growth stall is unacceptable and pre-reservation is not possible because the max size is unknown.

## Edge Cases and Counterexamples

**The LRU-cache trap.** The classic "hash map + doubly linked list" LRU answer is right, but for a subtle reason worth articulating: the O(1) move-to-front is only O(1) because the hash map hands you the node pointer directly, bypassing traversal. Interviewers who follow up with "now make it cache-friendly" expect the modern answer: a flat array of entries plus an index-based doubly linked list (storing 32-bit indices instead of pointers), which keeps O(1) semantics while restoring contiguity — this is how many production LRU implementations actually work.

**"Vector of structs" vs "vector of pointers to structs".** A common attempted fix — keep the vector but store pointers to heap-allocated elements — defeats itself: iteration now chases n scattered pointers, recreating the linked list's locality problem while keeping the array's invalidation problem. The insight generalizes: *contiguity only pays when the payload is contiguous*. Struct-of-arrays or index-based designs preserve it; pointer arrays do not.

**The deque middle ground.** `std::deque` (and similar chunked deques) allocates fixed-size chunks (typically 512 bytes to 4 KB) and a small map of chunk pointers. You get O(1) push front *and* back, O(1) random access, and a defined invalidation middle ground: the standard guarantees that inserting at either end invalidates iterators but *not* references to existing elements, while keeping chunk-level contiguity so iteration streams within a chunk. It is the pragmatic answer for workloads that need queue semantics plus indexing plus less brutal invalidation rules. Between the extremes there are also unrolled linked lists (arrays chained by pointers — list semantics, better locality) and slot maps / generational arenas (game engines, ECS frameworks: a vector of slots plus free-list and generation counters, giving O(1) access, stable handles, and full contiguity).

**Benchmarks must specify the workload — here is the reasoning template.** When you see "X is faster than Y" for these structures, decompose it: (1) what is the operation mix (iterate/insert/erase/index)? (2) where does the node pointer come from? (3) what is sizeof(T) — shifting cost scales with it? (4) is the working set cache-resident? A benchmark showing lists losing on "insert in middle" is usually measuring the O(n) search the array never had to do.

## Complexity Summary

| Operation | Dynamic array | Linked list | Honest note |
|-----------|---------------|-------------|-------------|
| Index i-th element | O(1) | O(n) dependent loads | List indexing is rare in real code for this reason |
| Append (amortized) | O(1)* | O(1) | *array: occasional O(n) copy spike; list: allocation per node |
| Insert/delete at known node/iterator | O(n) memmove | O(1) | Finding that point is O(n) for the list unless you hold the iterator |
| Insert/delete at front | O(n) | O(1) | Deque fixes this for arrays |
| Splice a run between collections | O(run length) copy | O(1) relink | Lists' structural advantage |
| Iterate | O(n), streamed, prefetchable | O(n), dependent loads | Largest practical gap; lists lose badly |
| Memory overhead | None beyond slack capacity | 8–16 B pointers + 16–32 B allocator headers per node | Vector slack vs list per-node tax |
| Reference stability under growth | Invalidated | Guaranteed | The decisive guarantee for some designs |

## Decision Framework

1. **Default to the dynamic array.** The burden of proof is on the list; contiguous memory is the closest thing to a free lunch in systems programming.
2. **Need O(1) front operations or double-ended growth with indexing?** Deque (chunked array).
3. **Hold long-lived references/iterators across mutations?** Linked list, or an index-based (slot map) design if locality matters too.
4. **Objects already exist and need cheap unlinking (kernel-style)?** Intrusive list.
5. **Pure LIFO over pre-existing/recycled nodes?** Singly linked freelist/stack.
6. **Moving runs between collections frequently?** List splice — the one operation with no array equivalent.
7. **Large elements where shifting dominates?** Array of indices into element storage, or reconsider the layout entirely.
8. **Latency-critical with unpredictable size?** Either pre-reserve arrays or use intrusive lists — both avoid reallocation stalls.

## Interview Questions

1. **Linked-list insertion is O(1) and array insertion is O(n). Why do array-based containers usually win on insert-heavy benchmarks anyway?** The list's O(1) requires the node pointer; finding it is an O(n) traversal over pointer-chased, cache-cold memory. The array's O(n) is a vectorized memmove over contiguous, prefetched bytes. Total work is O(n) for both, but the constants differ by an order of magnitude — and arrays keep iteration fast for the rest of the workload.
2. **What does geometric growth buy a dynamic array, and what two problems does it create?** Doubling (or 1.5×) makes n appends cost O(n) total copies — amortized O(1) per append. It creates (a) a reallocation spike — one append copies everything, which matters for latency SLOs, and (b) iterator/pointer invalidation, since all elements move. Pre-reservation and stable-handle designs (slot maps) are the standard mitigations.
3. **Why can't CPUs prefetch linked-list traversal the way they prefetch array scans?** Prefetching needs future addresses; in a list, the address of node i+1 is data stored inside node i. The load chain is serially dependent, so the core cannot overlap memory latency across iterations — this is the mechanism behind the 5–20× iteration gap.
4. **Design an LRU cache with O(1) get/put that is also cache-friendly.** Hash map from key to index into a flat array of entries; the entries themselves form a doubly linked list via 32-bit previous/next indices stored in the entries. O(1) access via the map, O(1) move-to-front via index relinking, and the entries stay contiguous — the classic pointer-based design's locality problem is fixed without giving up the asymptotics.
5. **Name a situation where a linked list is not just acceptable but clearly correct.** Intrusive lists in kernel code: nodes are embedded in objects, so there is no allocation or memory overhead, unlinking an arbitrary object is O(1), and object lifetime governs node lifetime. Also `std::list::splice` workloads — transferring whole runs between lists in O(1) has no array equivalent.

## Key Takeaways

- The real axis is not "array vs list" but "contiguous memory vs pointer chasing"; cache lines and prefetchability decide almost every practical benchmark.
- Amortized O(1) appends hide reallocation spikes and iterator invalidation; O(1) list insertion hides an O(n) search unless you already hold the node.
- Linked lists win where their guarantees are structural, not asymptotic: stable references, O(1) splice, intrusive membership, allocation-free relinking for real-time paths.
- Middle grounds exist and are production-proven: `std::deque` chunking, unrolled lists, and slot maps/generational arenas restore locality while keeping stable handles.
- In interviews, decompose any benchmark claim into operation mix, pointer provenance, element size, and cache residency — the mechanism, not the big-O, explains the numbers.

## Cross-References

- [Arrays & Strings chapter](../../dsa/chapters/ch04-arrays-strings.md) — array mechanics and two-pointer patterns.
- [Linked Lists chapter](../../dsa/chapters/ch12-linked-lists.md) — singly/doubly list mechanics and classic manipulations.
- [Memory Hardware](../../dsa/chapters/ch52-memory-hardware.md) — cache lines, prefetching, and the memory hierarchy behind the locality claims.
- [Binary Search vs Hashing](./binary-search-vs-hashing.md) — sibling comparison covering locality constants and amortization spikes.
- [Concurrent Queues](../../concurrency/concurrent-queues.md) — where ring buffers (array-based) beat list-based queues under contention.
- [DSA](../../dsa/README.md) — the main algorithms track.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
