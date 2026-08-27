# Binary Rewriting & Instrumentation

A compiler meets your program as source or IR; a binary rewriter meets it as bytes already committed to specific addresses. Every branch displacement, every PC-relative data reference, every alignment padding decision has been baked in. Rewriting means mutating those bytes - adding instrumentation, redirecting control flow, re-laying-out code - without breaking an address contract the original linker negotiated. This page covers how static and dynamic rewriters work, why stripped binaries resist, the arithmetic that makes patching in place hard, and the production uses: coverage, hardening, and kernel live patching. For post-link *performance* re-optimization (BOLT), see [profile-guided optimization](./profile-guided-optimization.md), which covers it in depth; here we treat BOLT only as one point on the spectrum.

## The rewriting spectrum

Rewriting tools differ in *when* bytes are rewritten and *who* executes the result:

```text
        static                    load-time / offline            dynamic (DBI)
  <------------------------|------------------------------|----------------------->
  E9Patch, reassembly      BOLT (post-link layout),      DynamoRIO / Pin / Frida /
  tools; emit a new ELF    kernel livepatch modules,     Valgrind; rewrite into a
  on disk                  ld --incremental patches      code cache while running
                          .............................
                           detour/trampoline libraries
```

- **Static rewriting** reads a complete executable, computes a new one, and writes it out. The result runs at full speed with no runtime harness, but every transformation must be proven correct offline, against a binary whose relocation metadata may be gone.
- **Dynamic binary instrumentation (DBI)** never edits the file. The engine intercepts execution, copies code fragments into a *code cache*, rewrites them there, and stitches the result together as the program runs. Nothing on disk changes; the process itself is the artifact being rewritten.
- **Load-time rewriting** sits between: patch modules or relocations applied when the loader maps the image, before the first instruction of the patch target executes.

The DBI engines each stake out a different trade-off. [DynamoRIO](https://dynamorio.org/) grew out of MIT's Dynamo work on transparent dynamic optimization and manipulates arbitrary transformations in its code cache. Intel's [Pin](https://www.intel.com/content/www/us/en/developer/articles/tool/pin-a-binary-instrumentation-tool-downloads.html) popularized the Pintool model - C/C++ plugins that observe and edit instruction streams - and its "probe mode" can even patch in place. [Frida](https://frida.re/docs/home/) targets live processes (and mobile apps especially, where it is both the analyst's favorite and the anti-tamper vendor's nemesis - see the mobile security page's hooking discussion), exposing rewriting to JavaScript with its Stalker tracing engine. Valgrind, covered in [the debugging toolchain](../../linux/debugging/valgrind.md), belongs to the same family from a different angle: a JIT recompiler whose "tools" are whole-program analyses rather than lightweight instrumentation. The survey bullet list in [compiler optimizations](./compiler-optimizations.md) names the DBI trio; this page explains the machinery those bullets assume.

## Static vs dynamic: two contracts with the address space

| Dimension | Static rewriting | Dynamic instrumentation |
|-----------|------------------|-------------------------|
| Artifact | New executable / library on disk | Rewritten code cache in process memory |
| Startup cost | Zero at run time | Cache warm-up, then near-native |
| Instrumentation overhead | Full speed once patched | ~1.2-4x typical (DBI code cache) |
| Coverage of code | All code, whether or not it runs | Only paths actually executed |
| Requires recompile/link | No, but must locate every patch site | No; catches code as it executes |
| Stripped-binary risk | High: missing relocs/symbols break analysis | Lower: only discovered code is rewritten |
| Persistence | Patch survives restart, can ship | Ends with the process |
| Typical uses | Hardening, live patching, BOLT-style layout | Profiling, fuzzing harnesses, taint tracking |

The overhead figure is the honest hedge: DynamoRIO's design goal was transparent optimization *faster* than the original in some workloads; Pin sits near 2x for many tools; Frida's Stalker trades raw speed for scripting ergonomics. None of these numbers are guarantees - they scale with how aggressively a tool instruments.

## Why stripped binaries fight back

The rewriter's first job is deceptively simple: find the instructions. Without symbols and relocations it must rediscover what the compiler knew:

1. **Direct branches are solvable - iteratively.** Start at the entry point and each symbol you have; decode; follow direct jumps/calls; repeat to a fixed point. The catch: function pointers inside data tables, jump tables the compiler emitted as raw address arrays, and inter-function padding all need data-flow heuristics. Miss one edge and your rewritten binary branches into a byte you misidentified as an instruction operand.
2. **Indirect branches are undecidable in general.** `jmp rax` may target anything. A rewriter either conservatively wraps every indirect branch with a check (which is what CFI tools do anyway), or accepts unknown edges and leaves them uninstrumented - dangerous when the unknown edge is the attacker's favorite gadget.
3. **PC-relative addressing reaches into data.** On x86-64 a `mov eax, [rip+0x1234]` reads a pool that may sit *between* functions, and a rewriting pass that slides code by N bytes must fix every such reference or the program reads garbage. With relocations stripped, nothing distinguishes an embedded address from an ordinary constant.
4. **Relocations are gone.** A linked, stripped binary has already resolved `.rela.text`; the "fix this address later" information the rewriter craves no longer exists. Reassembly approaches try to regenerate it; E9Patch (Duck, Gao, Roychoudhury - PLDI 2020) showed you can skip CFG recovery entirely and still insert instrumentation, using out-of-line trampolines keyed to verified instruction boundaries rather than a rebuilt CFG.

The lesson the field converged on: *perfect recovery is impossible, so design the rewrite to degrade locally* - a missed edge should cost you instrumentation coverage on one path, not a corrupted binary.

## Displacement: the arithmetic of patching in place

The detour is the atom of rewriting: overwrite some bytes at the patch site with a jump to your new code. On x86-64 the budget is brutally small:

| Encoding | Bytes | Reach | Patch-slot notes |
|----------|-------|-------|------------------|
| `jmp`/`jcc` rel8 | 2 | +/-127 B | Never enough for a detour |
| `call` rel32 | 5 | +/-2 GiB | The classic detour size on x86-64 |
| `jmp` rel32 | 5 | +/-2 GiB | In-place detour for `__fentry__`/ftrace sites |
| `jcc` rel32 | 6 | +/-2 GiB | 6-byte detour, needs one more byte of slack |
| `movabs` + `jmp reg` | 12-14 | 2^64 | Absolute jumps for far or unknown targets |
| ARM64 `B`/`BL` | 4 | +/-128 MiB | Fixed width: no variable-length slack at all |

A 5-byte detour must land where 5 contiguous bytes can be stolen. Mid-instruction is fatal; so is overrunning a site's basic block into a branch target. Compilers that expect patching leave room: GCC/Clang's `-fpatchable-function-entry=N` emits N NOPs at each function entry precisely so a rewriter or the kernel's ftrace can stuff a 5-byte (or 16-byte) detour into guaranteed padding.

```text
trampoline anatomy: instrumenting the call to audit_log at 0x401a00

  BEFORE                              AFTER
  .text                               .text
  0x401a00 push rbp                   0x401a00 jmp  relay        ; 5 stolen
  0x401a01 mov  rbp, rsp   (4B)       0x401a05 mov  rbp, rsp     ; untouched
  0x401a05 mov  rdi, [rbp+8]          ...

  relay (cave / new section)
    [0] push rbp                      ; relocated first instr
    [4] mov  rbp, rsp                 ; relocated second instr
    [8] call hook_log                 ; instrumentation payload
    [c] jmp  0x401a05                 ; jump back into the stream
```

Three costs hide in that diagram. *Space*: the code cave must be within rel32 reach of every site, or the relay needs absolute jumps. *Semantics*: the stolen bytes are relocated, so they must be position-independent or require fixing - RIP-relative instructions stolen across a distance break. *Cascade*: inserting any byte shifts every later address; this is where rewriting arithmetic bites hardest, and the next section quantifies it.

## A displacement overflow model (runnable)

When an insertion of S bytes shifts downstream code, every short (rel8) branch with displacement close to the +/-127 limit overflows and must be re-encoded as rel32 - which adds 4 more bytes and can cascade. The model below scatters branches through a function body, injects a detour of S bytes, and Monte-Carlo-measures (a) how often a random site even has room for an in-place patch, and (b) how often the insertion trips at least one rel8 overflow:

```python
"""Monte Carlo model of the displacement problem in binary rewriting.

A function body is a linear run of L bytes. Branch instructions (calls,
conditional jumps) are scattered through it with random spacing. A rewriter
must inject an instrumentation detour of S bytes at some site. Two failure
modes are measured:

  1. FIT   - the detour overwrites the bytes of a neighbouring instruction
             (no contiguous free run of S bytes at the site).
  2. CASCADE - the insertion shifts every downstream address by S, so any
             short (rel8, +-127) branch whose displacement already sits near
             the limit now overflows and must be re-encoded as rel32
             (+4 bytes each), which can itself cause further shifts.
"""
import random

random.seed(2026)
REL8 = 127  # 8-bit signed displacement limit


def lay_out(length, mean_gap):
    """Place branch sites through [0, length); return sorted offsets."""
    sites, pos = [], 0
    while True:
        pos += max(2, int(random.expovariate(1.0 / mean_gap)))
        if pos >= length:
            return sites
        sites.append(pos)


def run(length, mean_gap, slot):
    sites = lay_out(length, mean_gap)
    # gap between each site and the next instruction boundary
    gaps = [b - a for a, b in zip(sites, sites[1:] + [length])]
    # 1) fit test: patch a random site in place with `slot` bytes
    i = random.randrange(len(sites))
    fit = gaps[i] >= slot
    # 2) cascade: insertion of `slot` bytes shifts downstream code; count
    #    short branches whose original displacement (site -> random target
    #    up to the function end) exceeds REL8 after the shift
    over, extra = 0, 0
    for pos in sites:
        if pos >= sites[i]:
            target = random.randint(pos + 2, max(pos + 2, length))  # fwd branch
            disp = target - pos
            if disp <= REL8 and disp + slot > REL8:
                over += 1
                extra += 4  # rel8 -> rel32 re-encode
    return fit, over, extra


def monte_carlo(length, mean_gap, slot, trials=10000):
    fits = overs = extras = 0
    for _ in range(trials):
        fit, over, extra = run(length, mean_gap, slot)
        fits += fit
        overs += over > 0
        extras += extra
    n = trials
    return 100.0 * fits / n, 100.0 * overs / n, extras / float(n)


print("In-place detour feasibility and rel8 cascade (10k Monte Carlo runs/row)")
print("function  mean    slot | sites where  sites where  avg re-encode")
print("  size    gap          patch fits   cascade hit  bytes added")
print("---------+------+------+------------+------------+--------------")
for length, gap in ((512, 16), (2048, 24), (8192, 32)):
    for slot in (4, 5, 16):
        f, o, e = monte_carlo(length, gap, slot)
        print(f"{length:7d}B {gap:5d}B {slot:4d}B | {f:9.1f}%  {o:9.1f}%  {e:8.1f}")
```

Output (real run, CPython 3.12):

```text
In-place detour feasibility and rel8 cascade (10k Monte Carlo runs/row)
function  mean    slot | sites where  sites where  avg re-encode
  size    gap          patch fits   cascade hit  bytes added
---------+------+------+------------+------------+--------------
    512B    16B    4B |      78.1%       15.4%       0.7
    512B    16B    5B |      73.6%       18.6%       0.9
    512B    16B   16B |      37.2%       44.9%       2.9
   2048B    24B    4B |      85.0%       26.0%       1.2
   2048B    24B    5B |      81.4%       32.4%       1.6
   2048B    24B   16B |      51.0%       67.6%       5.2
   8192B    32B    4B |      88.2%       32.9%       1.6
   8192B    32B    5B |      86.1%       40.1%       2.1
   8192B    32B   16B |      60.6%       78.0%       6.6
```

Reading it: a 4-byte slot (ARM64-scale) almost always fits and rarely trips a rel8 overflow; a 5-byte x86 detour is usually patchable in place but cascades on a third or more of large-function sites; a 16-byte slot (the kernel-friendly `-fpatchable-function-entry=16` budget) cannot even fit at roughly half of random sites. This is why production rewriters either reserve padding up front, allocate out-of-line trampolines, or rewrite into a code cache instead of in place - and why function padding and section layout interact with patchability more than most engineers expect.

## What rewriting is for

**Coverage instrumentation.** Fuzzing harnesses get edge coverage from DBI: DynamoRIO-based AFL forks (and WinAFL on Windows) rewrite each basic block to toggle a coverage map; AFL++'s Frida mode uses Stalker for the same job. The mechanism is exactly the detour above, applied per basic block.

**Hardening and re-randomization.** Binary-level CFI rewriters rewrite a COTS binary so every indirect branch lands on a validated target: CCFIR (Zhang & Sekar, USENIX Security 2013) sorted call/jmp targets into a "springboard" of classified stubs, checking classification at each indirect transfer. The Bin-CFI family of tools applies the same idea to fully stripped binaries. The same rewriting machinery re-randomizes: layout randomization of a shipped binary, per-launch GOT/PLT shuffling, and re-linking with fresh ASLR entropy all mutate a binary that was never built with randomization in mind.

**Re-optimization.** BOLT disassembles the final binary, replays a profile, and re-lays-out functions and blocks for instruction-cache and branch-predictor wins on datacenter fleets. That story (and its measured gains) belongs to the [PGO page](./profile-guided-optimization.md); the point here is architectural: BOLT is a *static* rewriter whose correctness argument rests on linker-visible metadata that is normally still present - which is exactly what stripped-binary rewriting lacks.

**Kernel live patching.** The Linux kernel's livepatch subsystem is binary rewriting executed in production, on the most hostile binary there is. A patch module ships replacement functions; at enable time, each patched function's prologue is redirected through the ftrace mechanism - a 5-byte call site at function entry becomes a jump to the replacement. Concurrency (tasks mid-execution inside the old function), stack reliability, and consistency models are the hard parts. The [kernel live patching page](../../linux/kernel/live-patching.md) covers the module format, stacking, and the transition state machine; the kernel's own documentation lives at [docs.kernel.org/livepatch](https://docs.kernel.org/livepatch/livepatch.html).

## Symbolization is not rewriting

Perf, `addr2line`, and every profiler's flamegraph answer a read-only question: *which named entity owns address 0x401a00?* Symbolization walks symbol tables and DWARF; it never writes a byte. Rewriting answers a mutation question, and the two disciplines' artifacts conflict constantly:

| Symptom in production | Real cause |
|-----------------------|------------|
| Breakpoint lands mid-instruction after a patch | Symbolizer mapped stale offsets; rewriter shifted addresses |
| Unwinding breaks inside patched functions | Rewriter did not update `.eh_frame` / CFI for new code |
| perf report shows samples in unknown region | Detour code lives in a fresh section with no symbols |
| Build-id mismatch rejects a core dump | Rewritten binary's build-id was never regenerated |

The division of labor: the rewriter must emit new symbol and unwind metadata for what it adds; the symbolizer must be told about the rewrite. Tools that do both (BOLT regenerates symbolization-friendly layouts; livepatch keeps `kallsyms` coherent) exist precisely because half-done rewriting produces binaries that run correctly and debug incorrectly - the worst possible failure mode for production.

## References

- DynamoRIO - dynamic binary instrumentation framework: <https://dynamorio.org/>
- Frida documentation (core, gadget, Stalker): <https://frida.re/docs/home/>
- Linux kernel livepatch documentation: <https://docs.kernel.org/livepatch/livepatch.html>
- Duck, Gao, Roychoudhury, "Binary Rewriting without Control Flow Recovery," PLDI 2020: <https://doi.org/10.1145/3385412.3385972> (tool: <https://e9patch.github.io/>)
- Zhang & Sekar, "Control Flow Integrity for COTS Binaries," USENIX Security 2013: <https://www.usenix.org/conference/usenixsecurity13/technical-sessions/presentation/zhang>
