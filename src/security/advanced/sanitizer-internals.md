# Sanitizer Internals: Shadow Memory, Vector Clocks, and Tagged Silicon

Sanitizers are not linters and not debuggers: they are compiler passes plus runtime
libraries that make illegal program states *crash on schedule*. [Exploit
Mitigations](./exploit-mitigations.md) covers the defensive controls an attacker must
defeat; [Developer Tools](../../debugging/developer-tools.md) covers when to reach for
each tool. This page is the machinery under the flag: how every load and store gets
vetted by shadow bytes, how unproven values and unsynchronized accesses are tracked,
and how Arm moved the whole check into the CPU with MTE.

## The common skeleton: instrument, shadow, check, report

```text
  compiler pass  ->  rewrite loads/stores/allocs with checks
  runtime lib    ->  owns shadow memory + allocator/reporter hooks
  check          ->  a few inlined instructions on the fast path
  violation      ->  cold-path call into runtime, which prints a report
```

What differs is *what state the shadow encodes* and *how much precision it has*.
That one design choice sets the memory overhead, the CPU overhead, and the class of
bugs the tool can possibly see:

| Tool | Bug class | Shadow state | Shadow cost | Typical CPU cost |
| --- | --- | --- | --- | --- |
| AddressSanitizer | memory errors | 1 byte per 8-byte granule | ~1/8 of memory | ~2x |
| MemorySanitizer | uninitialized reads | 1 bit per data bit (+origin) | 1x (+1/4 origin) | ~3x |
| ThreadSanitizer | data races | 4 shadow cells per 8-byte word | 2x | 5-15x |
| UBSan | undefined behavior | none (pure checks) | ~0 | small |
| KASAN generic / KFENCE | kernel memory errors | 1/8 shadow / guard pages | ~1/8 / fixed pool | high / ~0 unsampled |

The CPU figures are the tool authors' published ballparks (clang and kernel docs),
not benchmarks.

## AddressSanitizer: the 1/8 shadow trick

ASan divides application memory into 8-byte granules and keeps **one shadow byte
per granule**. On Linux/x86-64 with the default offset the map is a plain linear
fold -- `shadow_addr = (app_addr >> 3) + 0x7fff8000` -- and the shadow is mapped
`MAP_NORESERVE`, so the "16+ TB of virtual address space" the docs warn about costs
nothing until a page is touched:

```text
          application memory                    shadow (1/8 the size)
  +-----------------------------+ 0x7fffffffffff     +---------------------+
  |        HighMem              |          |         |     HighShadow      |
  +-----------------------------+ 0x10007fff8000  -> +---------------------+
  |                             |                    |     ShadowGap       |
  +-----------------------------+ 0x00008fff7000  -> +---------------------+
  |        LowMem               |                    |     LowShadow       |
  +-----------------------------+ 0x000000000000     +---------------------+
                                        ^ 0x00007fff8000
```

The instrumented check is two instructions on the fast path:

```text
  tmp = *(u8*)shadow_addr          ; one shadow-byte load
  if (tmp && last_byte_of_access >= tmp) __asan_report_load1(addr)
```

The shadow byte vocabulary (current LLVM, `compiler-rt/lib/asan/asan_internal.h`):
`0x00` all 8 granule bytes addressable; `0x01`..`0x07` first N bytes addressable;
`0xfa` heap redzone (left and right in current LLVM); `0xfd` freed heap chunk;
`0xf1`/`0xf2`/`0xf3` stack left/mid/right redzones; `0xf5` stack frame after
return; `0xf8` stack object out of scope; `0xf9` global redzone; `0xf7`
user-poisoned (`__asan_poison_memory_region`); `0xfc` intra-object container
overflow. Negative-valued magics mean "fully poisoned", `k` in 1..7 means
"byte-precise partial".

### Redzones and the partial-granule encoding

The ASan allocator never returns raw memory -- each chunk ships wrapped:

```text
      left redzone    user data (size 13)       right redzone
  +---------------+-------------------------+----------------+
  | 0xfa 0xfa     | 0x00   | 0x05           | 0xfa 0xfa ...  |
  +---------------+-------------------------+----------------+
   16 bytes         8 + 8 granules            16 bytes
                    (second granule has
                     only 5 live bytes)
```

Redzones are why a *one-byte* overflow is caught even though both pages are mapped
and readable. The partial-granule byte (`0x05`) is what makes byte-precise checking
possible at 8-byte granularity: the last granule of a 13-byte allocation knows
exactly 5 of its bytes are live. The simulation below reproduces the whole story --
address math, chunk poisoning, the check, and free:

```python
# asan_shadow_sim.py -- model AddressSanitizer's shadow encoding on Linux/x86-64.
# Shadow map (default SHADOW_OFFSET): shadow = (app >> 3) + 0x7fff8000  (1/8 ratio).
# Shadow byte meanings (LLVM compiler-rt asan_internal.h):
#   0x00 = all 8 granule bytes addressable | k in 1..7 = first k bytes addressable
#   0xfa = heap redzone   0xfd = freed heap chunk   (negative magics = fully poisoned)

SHADOW_OFFSET = 0x7fff8000
LEFT_RZ = 0xfa          # heap left AND right redzone byte in current LLVM
FREED   = 0xfd          # quarantined (freed) heap chunk
MAGICS  = {LEFT_RZ: "redzone", FREED: "freed", 0xf1: "stack-left-rz",
           0xf5: "stack-after-return", 0xf8: "stack-use-after-scope"}

def shadow_of(app_addr):                    # the 1/8 fold, one shift + one add
    return (app_addr >> 3) + SHADOW_OFFSET

class Shadow:
    def __init__(self): self.mem = {}

    def poison(self, lo, hi, byte):
        for g in range(lo & ~7, hi, 8):     # one byte per 8-byte granule
            self.mem[shadow_of(g)] = byte

    def malloc(self, base, size, rz=16):
        # layout: [left rz][user size][right rz] -- redzones pad to granule edges
        self.poison(base - rz, base, LEFT_RZ)               # left redzone
        for g in range(base, base + size, 8):               # user region
            k = min(size - (g - base), 8)                   # addressable bytes
            self.mem[shadow_of(g)] = 0 if k == 8 else k     # full -> 0x00, else k
        uz_end = base + ((size + 7) & ~7)                   # user region, granule-aligned
        self.poison(uz_end, uz_end + rz, LEFT_RZ)           # right redzone

    def free(self, base, size):
        self.poison(base, base + size, FREED)               # enter quarantine

    def check(self, app_addr):
        b = self.mem.get(shadow_of(app_addr), 0)
        if b == 0:            return "ok"
        if 1 <= b <= 7:
            if (app_addr & 7) < b: return "ok"
            return "heap-buffer-overflow (partial granule, first %d bytes live)" % b
        return "heap-buffer-overflow (%s)" % MAGICS.get(b, hex(b))

sh = Shadow()
BASE, SIZE = 0x602000000010, 13
print("malloc(%d) at 0x%x" % (SIZE, BASE))
sh.malloc(BASE, SIZE)
print("  app   0x%x -> shadow 0x%x" % (BASE + 8, shadow_of(BASE + 8)))
for g in range(BASE - 16, BASE + SIZE + 16, 8):
    print("  granule 0x%x  shadow@0x%x = 0x%02x" % (g, shadow_of(g), sh.mem[shadow_of(g)]))
for off in (0, 12, 13, 16):
    print("  check p[%2d]: %s" % (off, sh.check(BASE + off)))
sh.free(BASE, SIZE)
for off in (0, 12):
    print("  after free, p[%2d]: %s" % (off, sh.check(BASE + off)))
```

Output (real run):

```text
malloc(13) at 0x602000000010
  app   0x602000000018 -> shadow 0xc047fff8003
  granule 0x602000000000  shadow@0xc047fff8000 = 0xfa
  granule 0x602000000008  shadow@0xc047fff8001 = 0xfa
  granule 0x602000000010  shadow@0xc047fff8002 = 0x00
  granule 0x602000000018  shadow@0xc047fff8003 = 0x05
  granule 0x602000000020  shadow@0xc047fff8004 = 0xfa
  granule 0x602000000028  shadow@0xc047fff8005 = 0xfa
  check p[ 0]: ok
  check p[12]: ok
  check p[13]: heap-buffer-overflow (partial granule, first 5 bytes live)
  check p[16]: heap-buffer-overflow (redzone)
  after free, p[ 0]: heap-buffer-overflow (freed)
  after free, p[12]: heap-buffer-overflow (freed)
```

Three details worth noticing: the shadow address is pure arithmetic (`0x...018 >>
3` plus offset), byte 12 of the allocation passes while byte 13 is caught *by the
partial granule byte*, and after `free()` the same pointer hits `0xfd` -- the chunk
was not returned to the OS, it was relabeled.

### Quarantine: buying time against use-after-free

Poisoning on free is not enough: the memory could be handed to the next `malloc()`,
which would un-poison it and the dangling pointer would look valid again. ASan
delays reuse: freed chunks enter a **quarantine** (a per-thread cache draining into
a global FIFO ring, `quarantine_size_mb` default 256 MiB on 64-bit) and stay
poisoned with `0xfd` until evicted. A use-after-free is caught with near-certainty
while the chunk sits in quarantine, at the cost of ~256 MiB of frozen heap and an
allocator that recycles less aggressively. Generic KASAN borrowed this wholesale --
it is the only KASAN mode with a quarantine.

### Use-after-return: the fake stack

No redzone scheme can keep a dead stack frame poisoned without breaking the next
call, so ASan moves the problem: each thread owns a **fake stack** of frames in 11
size classes (64 B up to 64 KB). The compiler allocates locals in a fake frame on
function entry and poisons it with `0xf5` on return; the real stack holds only a
frame descriptor. Accessing a local after return then hits `0xf5` and reports
`stack-use-after-return`. Modern clang builds this runtime-decided by default
(`-fsanitize-address-use-after-return=runtime`), with detection enabled on Linux
via `ASAN_OPTIONS=detect_stack_use_after_return=1` -- protection without paying the
fake-stack cost unless the option is set.

## MemorySanitizer: one bit per data bit

Uninitialized memory cannot be summarized per granule: `x + y` propagates taint bit
by bit, and a struct copy must carry per-bit state. MSan keeps a **1:1 shadow** --
one bit per application bit -- plus, with `-fsanitize-memory-track-origins`, a
second **origin shadow at 1/4 scale** holding a 4-byte origin ID per 4-byte value.
The origin identifies the allocation or frame where undefinedness was born; origin
level 2 also records the last few stores, so a report can print the chain "created
by heap allocation here, stored here, loaded here". Instrumentation propagates
shadow through every expression and checks *uses*: a conditional branch, syscall
argument, pointer dereference, or return derived from an uninit bit triggers
`use-of-uninitialized-value`.

Two consequences: uninstrumented code silently forgives taint (it writes real
memory without updating shadow), so everything including libc must be rebuilt or
intercepted -- which is why MSan is Clang-only with pre-instrumented system
libraries (Android, Chromium). And shadow-on-copy means a copy of uninit bytes
stays uninit but harmless until *used*, matching how the UB actually bites. Cost:
~3x CPU typical, roughly doubled memory with origins. The kernel cousin KMSAN uses
the same design and has flushed out a long tail of info-leak bugs.

## ThreadSanitizer: shadow cells and vector clocks

TSan must prove two accesses to a word are *unordered*, not merely invalid. Its
shadow, per 8-byte application word, holds **4 shadow cells of 4 bytes** (2x the
application memory), each recording one recent access:

```text
  per 8-byte app word                      one 4-byte shadow cell
  +--------------------------------+       +-------------------------------+
  | cell3 | cell2 | cell1 | cell0  |  =    | sid:8 | epoch:14 | size,mode  |
  +--------------------------------+       +-------------------------------+
                                             thread "slot id"  logical clock
```

Each thread owns a **vector clock** (one logical timestamp per thread slot). An
access bumps the accessor's clock; synchronization (mutex lock/unlock, atomic RMW)
merges clocks. The check for an access by thread T:

```text
  for each shadow cell c in the word:
      if c.conflicts(T access) and c.epoch > T.clock[c.sid]
      ->  report data race      # T has not synchronized with that
                                # thread since its recorded access
```

The cell epoch is truncated to 14 bits (~16K ticks); wrapping forces the runtime to
rescan cells, part of why TSan costs **5-15x CPU and 5-10x memory** (clang docs).
Atomic accesses do not call the checker -- they *merge clocks*, so a correctly
synchronized program never reports, while one lock-protected access plus one plain
access to the same word reports immediately. Go's `-race` flag is the same TSan v2
algorithm lineage wired into the gc toolchain.

## UBSan: checks with no shadow at all

UBSan takes the opposite trade: zero shadow, pure fast-path checks of *defined*
program semantics, each a compare-and-branch to a cold handler:

| Check (`-fsanitize=` value) | Emitted predicate |
| --- | --- |
| `signed-integer-overflow` | result overflows `INT_MAX`/`INT_MIN` |
| `shift` | exponent negative or >= width |
| `alignment` / `null` | misaligned / null load or store |
| `object-size` | access beyond `__builtin_object_size` |
| `vptr` | C++ member call on wrong dynamic type |
| `float-cast-overflow` / `function` | bad float->int cast / wrong fn type |

With `-fsanitize-recover` (default for most checks) it prints and continues -- what
makes UBSan deployable in CI and production fleets; `-fno-sanitize-recover` or
`-fsanitize-trap` aborts (SIGTRAP, no handler, size-constrained builds). UBSan
composes freely with ASan (`-fsanitize=address,undefined`) because their shadow
ranges are disjoint: ASan checks *where memory is touched*, UBSan checks *what the
program means*. Together they cover most memory-and-integer bug classes short of
races (see [undefined behavior in C](../../languages/c/undefined-behavior.md) for
the bug catalogue itself).

## Inside the kernel: KASAN and KFENCE

The kernel cannot copy userspace ASan naively -- no 47-bit user VA gap to hide a
16 TB shadow -- so each arch supplies its own fold (x86-64 via
`CONFIG_KASAN_SHADOW_OFFSET` with an xor trick, arm64 a fixed carve-out). The
kernel docs define three KASAN modes: **Generic** (`CONFIG_KASAN_GENERIC`,
ASan-style 1/8 shadow with slab redzones and -- uniquely among the modes -- a
quarantine; debugging builds), **software tag-based** (`CONFIG_KASAN_SW_TAGS`,
arm64 top-byte tags HWASan-style; moderate overhead, dogfooding on memory-limited
devices), and **hardware tag-based** (`CONFIG_KASAN_HW_TAGS`, Arm MTE tags checked
by the CPU; low overhead, production-capable).

**KFENCE** attacks cost from the other side: a *sampling* detector with **no
instrumentation at all**. It allocates from a dedicated pool -- default 255
objects, each two pages (object + guard) -- roughly one allocation per
`kfence.sample_interval` ms (default 100). An access into the guard page or a
poisoned freed object page faults, and the fault handler prints an ASan-style
report. When nothing is sampled KFENCE costs nothing -- the kernel's answer to
"memory-safety coverage on every production node, not just test labs": you trade
per-run catch probability for always-on everywhere.

## Arm MTE: the check moves into silicon

MTE (Armv8.5-A / Armv9-A) replaces the software shadow with hardware: every 16-byte
granule of physical memory carries a 4-bit **allocation tag**, and a pointer carries
a matching tag in its top byte (TBI, bits 56-59). Load and store compare the two
and fault on mismatch. Three check modes: **synchronous** (precise, faults at the
offending instruction), **asynchronous** (reports imprecisely later -- cheaper,
sampled), and asymmetric (sync stores, async loads). The compiler story exists as
Hardware Tag-Based KASAN in the kernel and memtag stack/heap instrumentation in
userspace; Android pushed furthest -- Pixel 8 shipped MTE-enabled, and Android 16's
Advanced Protection mode turns MTE on.

| Property | ASan (software shadow) | MTE (hardware tags) |
| --- | --- | --- |
| Granule | 8 bytes, byte-precise partial encoding | 16 bytes, tag-or-nothing |
| Sub-granule overflow | caught via partial granule byte | invisible inside one granule |
| CPU overhead | ~2x | low (no shadow loads) |
| Memory overhead | ~1/8 shadow + redzones + quarantine | 4 bits per 16 bytes + tag storage |
| Stack / globals | covered | only with stack/global tagging enabled |
| Deployment role | test / CI builds | production-capable |

The honest summary: MTE catches the same bug families (OOB, UAF) at a fraction of
the overhead but misses sub-granule overflows that ASan's partial byte catches --
complement across the dev-to-prod pipeline, not substitute.

## Interview probes

1. Why 1/8 shadow, not 1/16? What breaks in the byte encoding if granules were 16
   bytes? (The partial-granule trick needs 3 bits of "first k live bytes".)
2. Walk the byte sequence for `malloc(13)`: why is the last user granule `0x05`,
   and what exactly does the check compare against?
3. Why does ASan need a quarantine for use-after-free but a fake stack for
   use-after-return? What breaks with only one?
4. Give one expression where a granule-level uninit encoding would produce a false
   negative -- why must MSan shadow be 1:1?
5. KFENCE has no shadow and no instrumentation: where does the error signal
   physically come from, and what does that imply about which allocations it can
   police?

## References

1. Clang AddressSanitizer docs -- detection classes, UAR modes, 2x overhead:
   <https://clang.llvm.org/docs/AddressSanitizer.html>
2. AddressSanitizerAlgorithm, google/sanitizers wiki -- shadow map and encoding:
   <https://github.com/google/sanitizers/wiki/AddressSanitizerAlgorithm>
3. Serebryany et al., "AddressSanitizer: A Fast Address Sanity Checker", USENIX
   ATC 2012: <https://www.usenix.org/system/files/conference/atc12/atc12-final39.pdf>
4. Clang MemorySanitizer docs (origin tracking) and ThreadSanitizer docs (5-15x
   overhead, design): <https://clang.llvm.org/docs/MemorySanitizer.html>,
   <https://clang.llvm.org/docs/ThreadSanitizer.html>
5. Kernel Address Sanitizer and Kernel Electric-Fence docs -- KASAN modes, KFENCE
   sampling pool: <https://docs.kernel.org/dev-tools/kasan.html>,
   <https://docs.kernel.org/dev-tools/kfence.html>
6. Arm MTE security update and Android AOSP MTE docs:
   <https://developer.arm.com/documentation/110362/latest>,
   <https://source.android.com/docs/security/test/memory-safety/arm-mte>
