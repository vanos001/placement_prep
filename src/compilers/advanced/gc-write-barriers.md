# GC Write Barriers and the Tricolor Abstraction

A tracing collector that marks while the program runs faces a race: the mutator can move a reference from a region the collector has processed into one it will never look at again, silently abandoning live objects. **Write barriers** are the small pieces of code the compiler plants around every reference store to close that hole. This page builds the tricolor abstraction barriers are defined against, walks the three canonical designs (Dijkstra, Steele, Yuasa SATB) with a runnable floating-garbage accounting demo, then descends into what real runtimes ship: G1's SATB queues and card tables, JIT barrier elision, ZGC's load barriers, Go's hybrid barrier, and Boehm's barrier-free compromise. The collector algorithms themselves are covered in [garbage-collection.md](garbage-collection.md); this page is about the per-store cost they impose on compiled code.

## The Mutator-Collector Race

Concurrent marking interleaves collector work with mutator stores. Two interleavings are dangerous, and they fail differently:

```text
A is black, B white and unreached  ->  collector will never visit B again
Race 1 (live object lost, FATAL):  mutator A.f = B; sweep reclaims B while still referenced
Race 2 (dead object kept, BENIGN): mutator A.f = null; already-marked X survives one cycle
```

Race 1 destroys memory safety; race 2 merely wastes a cycle. Every correct barrier design prevents Race 1 and chooses how much of Race 2 to tolerate. That choice is the whole design space.

## The Tricolor Abstraction

Classify every object during marking: **white** (not yet visited — candidate garbage), **gray** (visited, fields not yet scanned), **black** (fully scanned — the collector is done with it). Marking ends when no gray objects remain; then white = garbage. The single dangerous pattern is a **black object pointing at a white object**: the black one will never be rescanned, so that white subtree is invisible. Two invariants make the pattern impossible, and each defines a barrier family:

| Invariant | Statement | Enforced by | Barrier watches |
|-----------|-----------|-------------|-----------------|
| Strong tri-color | No black→white edge ever exists | Steele (re-gray the source) | pointer *insertion* |
| Weak tri-color | Every black→white edge is protected: the white target is reachable from some gray via a white path | Dijkstra (shade the target) | pointer *insertion* |
| Snapshot consistency | The set of white objects only ever shrinks; anything live at cycle start stays live to cycle end | Yuasa SATB (gray the overwritten value) | pointer *deletion* |

Insertion barriers fire when a source *gains* a reference; deletion barriers fire when a reference is *overwritten away*. They are duals: incremental-update collectors lose mid-cycle deaths immediately but must police every added edge; SATB collectors preserve the beginning-of-cycle snapshot but retain everything that dies mid-cycle as floating garbage.

## Dijkstra: Shade the New Target

Dijkstra, Lamport, Martin, Scholten, and Steffens' 1978 on-the-fly collector was the first to solve the race. On every pointer store `s.f = v`, before committing:

```text
if s is black and v is white: shade v gray
```

This is an **incremental update** barrier: the collector remembers the new edge and gets a second chance to walk from `v`. It maintains only the weak invariant — black→white edges may exist, but every one leads back to a gray object, so termination scanning grays catches them. The costs:

- The barrier must fire on stores *from any object*, since even white sources turn black later; in practice it is unconditional (cheap branch: one color test). Termination is also delicate: the mutator can keep re-creating black→white edges, so grays resurface until quiescence — under heavy pointer churn this can starve the collector, the classic motivation for Steele's fix.

## Steele: Restore the Invariant at the Source

Guy Steele's 1975-76 independent design (published alongside) restores the **strong** invariant: on store `s.f = v` from a black `s` to a white `v`, re-gray *the source* `s` instead of shading `v`. A gray object is by definition "will be rescanned", so the black→white edge disappears immediately and no bookkeeping of outstanding edges is needed. The trade: every violating store forces a full rescan of the source object's fields later — write-heavy objects (arrays, hash tables) can be re-grayed many times per cycle. Steele's barrier is robust (the collector always terminates regardless of mutator behavior) at the price of rescan work; Dijkstra's is rescan-free but relies on the weak invariant holding at termination. Modern production collectors mostly picked a third path:

## Yuasa SATB: Snapshot-at-the-Beginning

Taiichi Yuasa's 1990 real-time collector inverts the problem. Instead of protecting edges that appear, it promises: **anything reachable when the cycle begins survives the cycle**. The barrier, on every reference store, *before* the overwrite:

```text
old = s.f
if old is not None and old is white: shade old gray
s.f = v
```

New objects are allocated **black**, so they are exempt from collection (a mutator may hold them) without being part of the snapshot. Now the mutator can never delete the last path to a snapshot-live object — the deletion barrier resurrects it. The consequences, visible in the demo below:

- **Floating garbage is the snapshot delta.** Objects reachable at cycle start but dead by cycle end are still marked; the collector reclaims them next cycle. SATB *revives* garbage that an incremental-update collector would have freed mid-cycle — bounded by the death rate during one concurrent phase.
- **No rescans, ever.** A black object stays black; the collector does a fixed amount of work per snapshot object. This determinism is why G1 (and CMS before it) chose SATB over incremental update.
- The gray-set bookkeeping is a queue: HotSpot's G1 pushes overwritten values into per-thread **SATB buffers** flushed by the same machinery as the remembered set below.

## The Demo: Floating-Garbage Accounting

Both flavors run on an identical interleaved mutator trace. The heap: roots `{A, S}`; `A.left=B`, `A.right=D`, `B.val=C`, `S.slot=X`. The mutator allocates `W`, overwrites `A.right=W` (dropping D), `B.val=null` (dropping C), `S.slot=null` (dropping X), with marker steps interleaved:

```python
#!/usr/bin/env python3
"""Tricolor marking on an identical mutator trace under two write-barrier
flavors: Dijkstra-style incremental update (pre-shade the NEW target) vs
Yuasa-style SATB (pre-gray the OVERWRITTEN old target; allocate black).

Part 1 accounts marked / floating-garbage / reclaimed-this-cycle sets and
checks liveness safety for both flavors. Part 2 models G1-style card-table
barrier accounting: barrier invocations vs unique cards dirtied vs
remembered-set entries after refinement. Pure stdlib, deterministic.
"""

WHITE, GRAY, BLACK = "white", "gray", "black"

class Obj:
    def __init__(self, oid, **fields):
        self.id = oid
        self.color = WHITE
        self.fields = dict(fields)      # field name -> Obj or None

def dijkstra_store(src, field, new, flavor, log):
    """Incremental update: protect the edge being ADDED."""
    if src.color == BLACK and new is not None and new.color == WHITE:
        new.color = GRAY
        flavor["gray"].append(new)
        log.append(f"  barrier: store {src.id}.{field} -> {new.id}: "
                   f"shade {new.id} gray (incremental update)")
    src.fields[field] = new

def yuasa_store(src, field, new, flavor, log):
    """SATB deletion barrier: protect the snapshot behind the edge REMOVED."""
    if flavor["marking"]:
        old = src.fields.get(field)
        if old is not None and old.color == WHITE:
            old.color = GRAY
            flavor["gray"].append(old)
            log.append(f"  barrier: store {src.id}.{field} overwrites {old.id}: "
                       f"shade {old.id} gray (SATB)")
    src.fields[field] = new

def marker_step(gray_stack, log):
    if not gray_stack:
        return
    o = gray_stack.pop()
    o.color = BLACK
    touched = []
    for v in o.fields.values():
        if v is not None and v.color == WHITE:
            v.color = GRAY
            gray_stack.append(v)
            touched.append(v.id)
    log.append(f"  marker : scan {o.id} -> black"
               + (f", shades {touched}" if touched else ", no new grays"))

def run(flavor_name, barrier, trace_notes):
    """Build the same snapshot heap, interleave fixed mutator ops with
    marker steps, then finish marking and account the outcome."""
    A = Obj("A", left=None, right=None); B = Obj("B", val=None)
    C = Obj("C"); D = Obj("D"); S = Obj("S", slot=None); X = Obj("X")
    A.fields["left"], A.fields["right"], B.fields["val"], S.fields["slot"] = B, D, C, X
    heap = {"A": A, "B": B, "C": C, "D": D, "S": S, "X": X}
    snapshot = set(heap)                       # all six live at cycle start
    roots = [A, S]
    gray = list(roots)
    for r in gray:
        r.color = GRAY
    log = [f"--- {flavor_name} ---", "  init   : roots {A, S} gray"]
    flavor = {"marking": True, "gray": gray}

    def mut_alloc(oid):
        o = Obj(oid)
        if flavor_name.startswith("Yuasa"):
            o.color = BLACK          # SATB allocates objects black
        heap[oid] = o
        return o

    muts = [
        ("u1 alloc W",             lambda: (mut_alloc("W"),
                                            log.append("  mutator: allocate W"
                                            + (" (born black)" if flavor_name.startswith("Yuasa") else " (white)")))),
        ("u2 A.right = W (drops D)", lambda: (dijkstra_store if flavor_name.startswith("Dijkstra") else yuasa_store)(A, "right", heap["W"], flavor, log)),
        ("u3 B.val = null (drops C)", lambda: (dijkstra_store if flavor_name.startswith("Dijkstra") else yuasa_store)(B, "val", None, flavor, log)),
        ("u4 S.slot = null (drops X)", lambda: (dijkstra_store if flavor_name.startswith("Dijkstra") else yuasa_store)(S, "slot", None, flavor, log)),
    ]
    for note, fn in muts:
        fn()
        marker_step(gray, log)
        marker_step(gray, log)
    while gray:
        marker_step(gray, log)
    flavor["marking"] = False

    # ground truth: reachable from roots at cycle end
    seen, work = set(), [r for r in roots]
    while work:
        o = work.pop()
        if o.id in seen:
            continue
        seen.add(o.id)
        work += [v for v in o.fields.values() if v is not None]
    marked = {o.id for o in heap.values() if o.color == BLACK}
    floating = marked - seen            # marked but dead at cycle end
    reclaimed = snapshot - marked       # in snapshot, not marked -> free now
    safe = seen <= marked               # nothing reachable was reclaimed
    for line in log:
        print(line)
    print(f"  result : reachable now = {sorted(seen)}")
    print(f"           marked       = {sorted(marked)}")
    print(f"           floating garbage (marked, dead at end) = {sorted(floating) or '{}'}")
    print(f"           reclaimed THIS cycle = {sorted(reclaimed) or '{}'}")
    print(f"           liveness safety: {'OK' if safe else 'VIOLATED'}")
    print()
    return len(floating), len(reclaimed), safe

def part2():
    print("--- G1-style card table accounting ---")
    CARD, objs = 4, [f"o{i}" for i in range(12)]
    card_of = lambda oid: int(oid[1:]) // CARD
    stores = [("o0","o5"), ("o1","o6"), ("o0","o9"), ("o2","o5"),
              ("o7","o11"), ("o8","o5"), ("o3","o10"), ("o4","o9")]
    dirty, rs_entries = set(), set()
    for src, dst in stores:
        dirty.add(card_of(src))            # pre-barrier dirties source's card
        rs_entries.add((card_of(src), dst))
    print(f"  {len(stores)} reference stores; card size {CARD} objects")
    print(f"  barrier invocations   = {len(stores)} (every store pays)")
    print(f"  unique cards dirtied  = {len(dirty)} -> {sorted(dirty)}")
    print(f"  remembered-set entries after refinement = {len(rs_entries)}")
    print(f"  buffer ratio: {len(dirty)/len(stores):.2f} cards per store")
    print()

print("PART 1: SATB vs incremental-update on one mutator trace")
print("snapshot heap: A.left=B A.right=D, B.val=C, S.slot=X; roots {A,S}")
print("trace: alloc W; A.right=W; B.val=null; S.slot=null (marker interleaved)")
print()
f = run("Dijkstra (incremental update)", dijkstra_store, None)
y = run("Yuasa (snapshot-at-the-beginning)", yuasa_store, None)
print(f"SUMMARY: floating garbage Dijkstra={f[0]}, Yuasa={y[0]}; "
      f"reclaimed-now Dijkstra={f[1]}, Yuasa={y[1]}; safe={f[2] and y[2]}")
part2()
```

Real output of the script above:

```text
PART 1: SATB vs incremental-update on one mutator trace
snapshot heap: A.left=B A.right=D, B.val=C, S.slot=X; roots {A,S}
trace: alloc W; A.right=W; B.val=null; S.slot=null (marker interleaved)

--- Dijkstra (incremental update) ---
  init   : roots {A, S} gray
  mutator: allocate W (white)
  marker : scan S -> black, shades ['X']
  marker : scan X -> black, no new grays
  marker : scan A -> black, shades ['B', 'W']
  marker : scan W -> black, no new grays
  marker : scan B -> black, no new grays
  result : reachable now = ['A', 'B', 'S', 'W']
           marked       = ['A', 'B', 'S', 'W', 'X']
           floating garbage (marked, dead at end) = ['X']
           reclaimed THIS cycle = ['C', 'D']
           liveness safety: OK

--- Yuasa (snapshot-at-the-beginning) ---
  init   : roots {A, S} gray
  mutator: allocate W (born black)
  marker : scan S -> black, shades ['X']
  marker : scan X -> black, no new grays
  barrier: store A.right overwrites D: shade D gray (SATB)
  marker : scan D -> black, no new grays
  marker : scan A -> black, shades ['B']
  barrier: store B.val overwrites C: shade C gray (SATB)
  marker : scan C -> black, no new grays
  marker : scan B -> black, no new grays
  result : reachable now = ['A', 'B', 'S', 'W']
           marked       = ['A', 'B', 'C', 'D', 'S', 'W', 'X']
           floating garbage (marked, dead at end) = ['C', 'D', 'X']
           reclaimed THIS cycle = {}
           liveness safety: OK

SUMMARY: floating garbage Dijkstra=1, Yuasa=3; reclaimed-now Dijkstra=2, Yuasa=0; safe=True
--- G1-style card table accounting ---
  8 reference stores; card size 4 objects
  barrier invocations   = 8 (every store pays)
  unique cards dirtied  = 3 -> [0, 1, 2]
  remembered-set entries after refinement = 7
  buffer ratio: 0.38 cards per store
```

Read the summary line as the thesis of the whole page: both collectors are safe, but SATB reclaimed *nothing* this cycle — D, C, and X all floated (D and C were resurrected by the deletion barrier; X was simply marked before it died, which happens in any concurrent design). Incremental update freed the two white deaths immediately. SATB traded two objects of extra residency for a collector that never rescans; that is the deal G1 signed.

## Generational Barriers: Card Tables and Remembered Sets

The tricolor barriers above serve *concurrent marking*. Generational collectors need a different barrier for a different invariant: **old-to-young pointers**, because minor collections only scan the young generation — an old object pointing at a young one would be invisible to a young-only trace. Scanning the whole old gen per minor GC defeats the purpose, so runtimes track old→young edges coarsely with a **card table**: a byte per 512-byte heap card, marked dirty by a post-store barrier whenever the store might cross generations.

```text
heap:   | card 0 (512B) | card 1 (512B) | card 2 (512B) | ...
cardtbl:|  0x00         |  0x01 (dirty) |  0x00         |   <- byte per card
                              ^ post-barrier writes 1 on any ref store here
refinement threads read dirty cards, find old->young refs,
record precise per-region remembered-set entries, clear the card
```

G1 stacks both barriers on every reference store:

1. **Pre-barrier (SATB):** if marking is active, push the *overwritten* value into a thread-local SATB buffer (the Yuasa mechanism from the demo, at production scale).
2. **Post-barrier (cross-region check):** compare the region of the object stored with the region of the target; if they differ, dirty the source's card and enqueue the card for **refinement** — background threads convert coarse dirty cards into per-region remembered sets (`RSet`) so a young/mixed collection of region R scans only the external roots into R.

The demo's Part 2 accounts this precisely: 8 stores pay the barrier 8 times but dirty only 3 distinct cards (two stores to the same card dirty it once — the card table is the barrier's *memoization*), and refinement condenses 8 stores into 7 remembered-set entries. This coarse-to-precise pipeline is the same idea as [mvcc-garbage-collection.md](../../dbms/advanced/mvcc-garbage-collection.md) applies at the database layer: pay a cheap bounded per-write cost so the expensive reclaim pass can skip most of the heap. G1's barrier has kept evolving — the card-table byte and pre-barrier split described here is the classic design, and Schatzl's write-up of the newer post-write-only barrier work documents the current push to strip per-store work further.

## When Barriers Vanish: JIT Elision and Colored Pointers

A write barrier executes on *every* reference store, which makes it one of the largest steady-state managed-runtime costs — so JITs spend enormous effort proving particular stores don't need it:

- **Escape analysis elision:** an object proven non-escaping (see [escape-analysis.md](escape-analysis.md)) can be stack-allocated or scalar-replaced, and stores into it skip the barrier entirely — no other thread or collector can hold a reference to it.
- **Trivial-store fast paths:** storing null, storing the value already there, and storing into an already-dirty card short-circuit before the slow path; the JIT also inlines the cross-region generation check and elides the card write when both ends are provably in the same region. HotSpot lowers G1's post-barrier to a card-table byte load + compare + rare branch to the slow-path stub.
- **Load barriers instead:** ZGC eliminates *write* barriers almost entirely and puts a small barrier on every reference **load** — the loaded pointer's color bits say whether it must be self-healed before use. That is what makes concurrent *compaction* possible (objects move while threads run), the trade documented in [zgc.md](zgc.md) and [garbage-collection.md](garbage-collection.md).

| Runtime | Barrier flavor | Fires on | Slow path |
|---------|----------------|----------|-----------|
| JVM G1  | SATB deletion (pre) + card (post) | every ref store | SATB buffer flush / card refinement |
| JVM ZGC | load barrier, colored pointers | every ref load | pointer self-heal |
| .NET GC | card marking | cross-gen ref store | card scan |
| Go      | hybrid Yuasa-Dijkstra | ref store when GC active | shading + buffer flush |
| Boehm-Demers-Weiser | none on stores | — | conservative stack/regs scan + page-protection dirty bits |

Two entries deserve a note. **Go 1.8+** ships a *hybrid* barrier that is simultaneously a deletion barrier (Yuasa: gray the overwritten value) and an insertion barrier (Dijkstra-style: shade the new value if the GC is active) — the combination removed the stack-rescan pauses Yuasa alone required, which is why Go's STW pauses dropped to sub-millisecond. **Boehm-Demers-Weiser** goes the other way: a collector for C/C++ that cannot require compiler cooperation, so it installs *no* store barriers and instead scans the stack and registers conservatively and tracks modified pages via hardware dirty bits — the "barrier" moves from per-store code to per-page page-fault handling. It is slower per GC but the only option for uncooperative code (Boehm's original paper is in the references).

## References

1. E. W. Dijkstra, L. Lamport, A. J. Martin, C. S. Scholten, E. F. M. Steffens, "On-the-fly garbage collection: an exercise in cooperation," *Communications of the ACM* 21(11), 1978. doi:10.1145/359642.359655 (verified via Crossref).
2. T. Yuasa, "Real-time garbage collection on general-purpose machines," *Journal of Systems and Software* 11(3), 1990. doi:10.1016/0164-1212(90)90084-y (verified via Crossref).
3. R. Jones, A. Hosking, E. Moss, *The Garbage Collection Handbook: The Art of Automatic Memory Management*, 2nd ed., Chapman & Hall/CRC, 2016 (text reference; chapters on tricolor invariants, barrier taxonomy, and remembered sets).
4. T. Schatzl, "New Write Barriers for G1" — the G1 architect's account of replacing the classic pre/post barrier pair. https://tschatzl.github.io/2025/02/21/new-write-barriers.html (probed: HTTP 200).
5. H.-J. Boehm, "Garbage collection in an uncooperative environment," *Software: Practice and Experience* 18(9), 1988. doi:10.1002/spe.4380180902 (verified via Crossref).
