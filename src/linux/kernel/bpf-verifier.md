# The eBPF Verifier: Proving Program Safety Before the Kernel Runs It

A BPF program is user-written C that will execute in kernel mode, and a crash that arrived through a BPF program was historically nearly unattributable: the oops pointed at kernel code that never wrote itself. The design answer was to make the kernel refuse to attach anything it cannot *prove* safe, statically, at load time. The verifier is that proof engine: a ~20k-line static analyzer (`kernel/bpf/verifier.c`) that abstractly interprets the bytecode; only programs whose proof succeeds are JIT-compiled and attached. It is a security boundary, so verifier bugs are themselves CVEs with privilege-escalation exploits - the design trades convenience for checkability at every step. For the surrounding platform (maps, helpers, JIT, BTF) see [eBPF](../debugging/ebpf.md); this page goes inside the proof itself.

## What must be proven, in one list

For every reachable instruction and every reachable program state:

1. **Termination** - no unbounded loops (bounded ones are fine, see below).
2. **Memory safety** - every load/store hits a valid object (map value, stack slot, packet buffer, context) within proven bounds.
3. **Type safety** - registers holding pointers are never used as numbers, and numbers never used as pointers; kernel addresses are not leaked to unprivileged callers.
4. **Contract compliance** - every helper call passes arguments with the exact types, sizes, and initialization the helper declared.
5. **Initialized access** - uninitialized stack or register data is never read (leaks kernel state).

Anything not provable is rejected, even if it would have been safe at runtime. The verifier is sound but intentionally incomplete.

## Two phases: shape first, then abstract interpretation

Phase 1 walks the control-flow graph: every instruction must be reachable from entry, every jump target must land on a valid instruction boundary, and (historically) the CFG had to be acyclic - the cheap form of termination, until kernel 5.3.

Phase 2 is a forward abstract interpretation over all paths. The verifier keeps a state per program point: values for all 11 registers plus stack slot contents, each tagged as scalar or one of the pointer flavors. At a jump it *splits* the state into two children (taken / not-taken), refines each, and pushes both. At a join point, a previously explored state may *absorb* an equivalent newcomer instead of re-simulating.

## Tracking values: tnum, the tristate number

A register's value is usually not known exactly, so the verifier tracks each 64-bit register as a **tnum** - "tracked number"; the source header calls it *tracked (or tristate) numbers* - a pair `(value, mask)` where each bit is one of three things:

| value bit | mask bit | meaning |
|-----------|----------|---------|
| 1 | 0 | known to be 1 |
| 0 | 0 | known to be 0 |
| 0 | 1 | unknown (value bit forced 0 by the invariant `value & mask == 0`) |

A u8 loaded from memory becomes `tnum(0, 0xff)`: eight unknown bits, 56 known zeros. Alongside the tnum, the verifier tracks four numeric bounds (`smin/smax`, `umin/umax`), and after every conditional jump it *syncs* the two views: bounds tighten the mask (a constant range fixes bits), and known bits tighten the bounds. This two-representation dance is where most precision - and historically most verifier bugs - lives. `tnum_and`, `tnum_or`, `tnum_xor` are straightforward; `tnum_add` propagates carry chains into new unknowns, and `tnum_mul` does schoolbook long multiplication where an unknown multiplier bit forces a union of the two partial products. The runnable lab at the bottom ports the exact kernel algorithms and brute-force checks them.

## Pointers: a parallel type lattice

Scalars are never allowed to touch memory. Pointer registers carry a *type* (`PTR_TO_CTX`, `PTR_TO_MAP_VALUE`, `PTR_TO_STACK`, `PTR_TO_PACKET`, `PTR_TO_SOCKET`, ...) plus a fixed offset `off`, a variable offset (`var_off`, a tnum), and reference/object ids. Pointer + scalar with a proven mask is fine; pointer + pointer is a type error. Types that may fail - `bpf_map_lookup_elem` results, ringbuf reservations - are marked `PTR_MAYBE_NULL` and *demote* every alias; only a null check on that register (or any copy sharing its id) promotes them back. The full register-type table and direct packet access mechanics are covered in [eBPF](../debugging/ebpf.md#bpf-verifier-internals); the helper-side contracts that consume these types are below.

## Branches and the pruning cache

Exploring every path is exponential, so the verifier memoizes: each instruction keeps a list of already-validated states. A newly arriving state is compared against them; if register types, tnums, bounds, and stack contents are equivalent (modulo *precision* marks - values never actually read), the newcomer is **pruned** and its subtree skipped. Pruning is the reason large programs verify at all - and its heuristics have twice needed fixes for unsound pruning (more below).

```text
        A:  r0 = *(u32 *)(r1 + 0)      ; input word, unknown
            if r0 > 100 goto C
        B1: r1 = 42                    ; path L
            goto J
        B2: r1 = 42                    ; path R (same effect!)
            goto J
        C:  r1 = 7
        J:  r2 = map_value[r1]         ; join / merge point

    state space the verifier explores:

        A {r0: scalar(0,0xffffffff)}
          |                      \
        B1 {r1: const 42}         B2 {r1: const 42}
          |                        /
        J  first visit via B1: analyze, record state S1={r1:42,...}
          ^ second arrival via B2 gives state == S1  ==>  PRUNED (C-arrival {r1:7} differs -> analyze)
```

Without pruning, a 2k-instruction program with 100 branches is 2^100 states; with it, verification cost tracks *distinct* states, bounded by the complexity budget below. The trade: a too-aggressive equivalence test that ignores a value that *is* later read turns into a soundness hole, which is why states carry liveness and precision metadata instead of comparing blindly.

## Loops: from forbidden, to bounded, to contract-based

- Before 5.3: any back-edge was rejected. Loops had to be unrolled at compile time (and `#pragma unroll` failures were a rite of passage).
- 5.3 (2019): loops allowed when the verifier can bound the induction variable via its scalar tracking - each iteration re-enters the state machine and must converge to a seen state or hit the instruction budget.
- 5.17-era: `bpf_loop()` and open-coded iterators moved loop control into helpers/kfuncs with *contractual* termination (the helper guarantees `next()` returns NULL); the verifier then only has to prove safety of the body, using the state-equivalence check across iterations. `BPF_MAX_LOOPS` caps helper-driven iterations at 8,388,608.

## The budget

| Limit | Value | Enforced on |
|-------|-------|-------------|
| `BPF_COMPLEXITY_LIMIT_INSNS` | 1,000,000 | total insns processed per verification ("yes. 1M insns" - `include/linux/bpf.h`) |
| program size, CAP_BPF holder | 1,000,000 | instructions in one program |
| `BPF_MAXINSNS` (no CAP_BPF) | 4,096 | unprivileged program size (`bpf_cap ? 1M : 4096` in `syscall.c`) |
| `BPF_COMPLEXITY_LIMIT_JMP_SEQ` | 8,192 | path/exploration stack depth |
| `BPF_COMPLEXITY_LIMIT_STATES` | 64 | cached states per instruction |
| `MAX_BPF_STACK` | 512 B | stack frame per call frame |
| `MAX_CALL_FRAMES` | 8 | bpf-to-bpf call nesting |
| `MAX_TAIL_CALL_CNT` | 33 | tail-call chain length |
| `BPF_MAX_LOOPS` | 8,388,608 | iterations via `bpf_loop`/iterators |

The 1M budget arrived with kernel 5.2 (2019) together with *precision tracking*, which let pruning drop provably-never-read state without losing soundness; unprivileged programs remain at 4096 instructions.

## When the verifier is the bug

A soundness bug in the verifier is a local-privilege-escalation primitive: the attacker gets the kernel to accept (and JIT) a program that reads or writes outside its proven bounds. The repeated failure mode is the 32/64-bit bounds coupling: bounds tracked for the full register drifting out of sync with bounds tracked for a subregister. CVE-2020-8835 and CVE-2021-31440 were incorrect bounds calculations; **CVE-2021-3490** was the ALU32 bounds tracking for bitwise AND/OR/XOR failing to update the 32-bit bounds (a local privilege escalation, reported via Pwn2Own 2021). Academic work now automates finding such bugs: Vishwanathan et al.'s CAV 2023 paper "Verifying the Verifier" built differential checker harnesses for the range analysis and uncovered new soundness bugs in add/sub handling - the verifier analyzed by a verifier. Separately, since 2019 the verifier hardens accepted programs against Spectre v1-style speculation by inserting barriers wherever a path could use an unmasked pointer under misprediction; and unsound *pruning* (state equivalence) needed its own rework in 2023 after incorrect state comparison logic was reported. The verifier thus defends two ways at once: proving safety of programs, and being provable (or at least checkable) itself.
False rejections are the everyday cost: valid programs fail because a mask crosses a subregister boundary, a branch order confuses pruning, or a helper's `ARG_CONST_SIZE` can't be proven nonzero. Reading the log (below) is a learned skill, and [libbpf](../debugging/libbpf.md) rewrites/relocates code precisely to stay inside the provable subset.

## Helper contracts: ARG_*

Each helper is described to the verifier by a `bpf_func_proto` with five argument descriptors from `include/linux/bpf.h`:

| arg_type | meaning |
|----------|---------|
| `ARG_ANYTHING` | any initialized scalar |
| `ARG_CONST_MAP_PTR` | const map pointer (used to resolve map metadata) |
| `ARG_PTR_TO_MAP_KEY` | pointer to `key_size` bytes (stack/packet/map) |
| `ARG_PTR_TO_MAP_VALUE` | pointer to `value_size` bytes; `_OR_NULL` variant must be null-checked first |
| `ARG_CONST_SIZE` / `ARG_CONST_SIZE_OR_ZERO` | scalar is a byte count bounded by the preceding buffer arg |
| `ARG_PTR_TO_CTX` | the program context (type-checked per program type) |
| `ARG_PTR_TO_MEM` / `ARG_PTR_TO_UNINIT_MEM` | valid memory / writable uninitialized memory (flags: `MEM_UNINIT`, `MEM_WRITE`, `MEM_FIXED_SIZE`) |
| `ARG_PTR_TO_SOCKET` / `ARG_PTR_TO_SOCK_COMMON` | refcounted socket pointers (acquire/release tracked) |
| `ARG_PTR_TO_BTF_ID` | pointer to a specific in-kernel struct (BTF-typed) |
| `ARG_PTR_TO_SPIN_LOCK` / `ARG_PTR_TO_TIMER` / `ARG_PTR_TO_RINGBUF_MEM` | special-object pointers with lifetime rules |

The `_OR_NULL` variants are how the API encodes fallibility: the verifier types the result `PTR_MAYBE_NULL` and refuses dereference until a branch proves it non-null. Helpers are whitelisted per program type - a tracing program's `ARG_PTR_TO_CTX` means `pt_regs`, an XDP program's means `xdp_md` - so the same program-type table drives both helper availability and context-field access rewrites.

## Reading the log

An abridged load-time failure (modern kernels print full register state per line):

```text
  ; if (key > 42)
  12: (25) if r2 > 0x2a goto pc+3
  R2_w=inv(smin=0,smax=umax=42,var_off=(0x0; 0x3f))    ; bounds+tnum after the branch
  ; return bpf_map_lookup_elem(&m, &k);
  15: (85) call bpf_map_lookup_elem#1
  R0_w=map_value_or_null(id=1)                          ; maybe-null type
  16: (b7) *(u8 *)(r0 +0) = 1
  invalid mem access 'map_value_or_null'                ; no null check first
  from 12 to 16: safe                                   ; pruned sibling marked
  processed 18 insns (limit 1000000): load rejected
```

Diagnosis discipline: find the first `Rn=` state line before the faulting insn, read the register's type and `var_off` mask, and ask what refinement the verifier was missing - almost always a missing bounds check, a mask crossing 32/64 bits, or a lost `id` linkage through a helper call. The final error names the crash site, not the proof failure point.

## A runnable tnum lab

The script ports `tnum_add`, `tnum_mul`, and friends from `kernel/bpf/tnum.c` bit-for-bit, brute-force checks soundness against concrete execution, then replays a verifier-style refinement trace on one register:

```python
# Port of the eBPF verifier's tnum algebra from kernel/bpf/tnum.c (64-bit),
# plus brute-force soundness checking and a verifier-style refinement trace.
# tnum = (value, mask); bit: mask=1 unknown, else known = value bit.
M64 = (1 << 64) - 1

class TNum:
    def __init__(self, value=0, mask=0):
        self.value, self.mask = value & M64, mask & M64
    def concretes(self):                 # every value this tnum may take
        bits = [i for i in range(64) if self.mask >> i & 1]
        return [self.value | sum(1 << bits[j] for j in range(len(bits))
                                 if c >> j & 1) for c in range(1 << len(bits))]
    def __repr__(self):
        s = "".join("x" if self.mask >> i & 1 else str(self.value >> i & 1)
                    for i in range(7, -1, -1))
        return f"tnum(value=0x{self.value:x}, mask=0x{self.mask:x}) [{s}]"

def tnum_add(a, b):                      # kernel/bpf/tnum.c
    sm, sv = (a.mask + b.mask) & M64, (a.value + b.value) & M64
    sigma = (sm + sv) & M64
    chi = sigma ^ sv
    mu = chi | a.mask | b.mask
    return TNum(sv & ~mu & M64, mu)

def tnum_mul(a, b):                      # long multiplication over bit products
    acc, a2, b2 = TNum(), TNum(a.value, a.mask), TNum(b.value, b.mask)
    while a2.value or a2.mask:
        if a2.value & 1:                 # LSB known 1:  acc += b
            acc = tnum_add(acc, b2)
        elif a2.mask & 1:                # LSB unknown:  acc = union(acc, acc + b)
            acc = tnum_union(acc, tnum_add(acc, b2))
        a2, b2 = TNum(a2.value >> 1, a2.mask >> 1), TNum(b2.value << 1, b2.mask << 1)
    return acc

def tnum_and(a, b):
    v = a.value & b.value
    return TNum(v, (a.value | a.mask) & (b.value | b.mask) & ~v & M64)

def tnum_or(a, b):
    v = a.value | b.value
    return TNum(v, (a.mask | b.mask) & ~v & M64)

def tnum_range(lo, hi):                  # conservative tnum for a [lo, hi] range
    bits = (lo ^ hi).bit_length()
    delta = M64 if bits > 63 else (1 << bits) - 1
    return TNum(lo & ~delta, delta)

def tnum_intersect(a, b):
    return TNum((a.value | b.value) & ~(a.mask & b.mask) & M64, a.mask & b.mask)

def tnum_union(a, b):
    mu = (a.value ^ b.value) | a.mask | b.mask
    return TNum((a.value & b.value) & ~mu & M64, mu)

# ---- Act A: brute-force soundness of add and mul on random small tnums ----
import itertools, random
random.seed(7)
def rand_tnum():
    m = random.randrange(0, 16)          # up to 4 unknown low bits
    return TNum(random.randrange(0, 1 << 6) & ~m, m)

def sound(fn, op, trials=150):
    bad = exact = 0
    for _ in range(trials):
        a, b = rand_tnum(), rand_tnum()
        r = fn(a, b)
        results = {op(x, y) & M64 for x, y in itertools.product(a.concretes(), b.concretes())}
        if not results <= set(r.concretes()):   # soundness: reality inside abstraction
            bad += 1
        if results == set(r.concretes()):       # precision: nothing extra allowed
            exact += 1
    return bad, exact, trials

for fn, op, sym in ((tnum_add, lambda x, y: x + y, "add"), (tnum_mul, lambda x, y: x * y, "mul")):
    bad, exact, n = sound(fn, op)
    print(f"A) tnum_{sym}: {n} random tnum pairs -> unsound={bad}, exact={exact}/{n}")

# ---- Act B: verifier-style trace of one tracked register ----
x = TNum(0, 0xFF)                        # R1 = *(u8 *)data : low 8 bits unknown
print(f"\nB) R1 = *(u8 *)data              -> {x}")
y = tnum_add(x, TNum(3))                 # R2 = R1 + 3
print(f"B) R2 = R1 + 3                   -> {y}")
print(f"   tnum span [{min(y.concretes())},{max(y.concretes())}] vs true span [3,258]:",
      "sound, but carry made bit 8 unknown")
b1 = tnum_intersect(y, tnum_range(3, 200))   # branch: if (R2 <= 200)
print(f"B) branch (R2 <= 200), intersect -> {b1}")
z = tnum_and(b1, TNum(0x0F))             # R3 = R2 & 0xF
print(f"B) R3 = R2 & 0xF                 -> {z}")
print(f"B) R4 = R3 | 0x20                -> {tnum_or(z, TNum(0x20))}")

# ---- Act C: constant propagation refines everything ----
c1 = tnum_add(TNum(5), TNum(7))
c2 = tnum_mul(TNum(2, 0x1), TNum(10))    # R = (2 or 3) * 10  [value&mask==0]
print(f"\nC) tnum(5,0) + tnum(7,0)         -> {c1}   (folded to constant {c1.value})")
print(f"C) tnum(2,mask 1) * 10           -> {c2}")
print(f"   actual products {sorted({v * 10 for v in (2, 3)})}",
      f"are inside tnum set {sorted(c2.concretes())}")
```

Output (real run):

```text
A) tnum_add: 150 random tnum pairs -> unsound=0, exact=5/150
A) tnum_mul: 150 random tnum pairs -> unsound=0, exact=2/150

B) R1 = *(u8 *)data              -> tnum(value=0x0, mask=0xff) [xxxxxxxx]
B) R2 = R1 + 3                   -> tnum(value=0x0, mask=0x1ff) [xxxxxxxx]
   tnum span [0,511] vs true span [3,258]: sound, but carry made bit 8 unknown
B) branch (R2 <= 200), intersect -> tnum(value=0x0, mask=0xff) [xxxxxxxx]
B) R3 = R2 & 0xF                 -> tnum(value=0x0, mask=0xf) [0000xxxx]
B) R4 = R3 | 0x20                -> tnum(value=0x20, mask=0xf) [0010xxxx]

C) tnum(5,0) + tnum(7,0)         -> tnum(value=0xc, mask=0x0) [00001100]   (folded to constant 12)
C) tnum(2,mask 1) * 10           -> tnum(value=0x14, mask=0xa) [0001x1x0]
   actual products [20, 30] are inside tnum set [20, 22, 28, 30]
```

Reading the output: add/mul are *sound* on all 150 random pairs but rarely *exact* - over-approximation is the price of closed-form bit arithmetic (the `{20,30}` true product set becomes `{20,22,28,30}`). The Act B trace is the verifier's everyday life: an unknown byte acquires a ninth unknown bit from a carry, a conditional jump intersects a range back down, and a mask (`& 0xF`) then fixes all high bits - exactly the refinement chain that turns "some number" into "safe offset". For where to go next: [BTF](../debugging/bpf-type-format.md) covers type metadata, [maps & helpers](../debugging/bpf-maps-helpers.md) the data-plane APIs, [eBPF security](../../security/ebpf-security.md) the threat model around the verifier, and [Abstract Interpretation](../../compilers/advanced/abstract-interpretation.md) the general framework this all instantiates.

## References

- [BPF Verifier - kernel documentation](https://docs.kernel.org/bpf/verifier.html) - official internals: register states, pruning, direct packet access
- [kernel/bpf/tnum.c](https://github.com/torvalds/linux/blob/master/kernel/bpf/tnum.c) - the tracked-number algebra ported in the lab above
- H. Vishwanathan et al. [Verifying the Verifier: eBPF Range Analysis Verification](https://link.springer.com/chapter/10.1007/978-3-031-37709-9_12) (CAV 2023) - automated soundness checking of the verifier's value tracking
- [NVD: CVE-2021-3490](https://nvd.nist.gov/vuln/detail/CVE-2021-3490) - ALU32 bounds-tracking flaw; verifier bugs as privilege escalation
- Trail of Bits, [Harnessing the eBPF Verifier](https://blog.trailofbits.com/2023/01/19/ebpf-verifier-harness) - practitioner deep dive into building verifier harnesses
