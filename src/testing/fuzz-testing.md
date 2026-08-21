# Fuzz Testing

## Overview

Fuzz testing (fuzzing) is a coverage-guided technique for finding inputs that crash, hang, or corrupt a program. Instead of guessing where bugs hide, the fuzzer treats the program as a black box that exposes its own internal coverage, then biases input generation toward mutations that touch *new* code. The discipline was introduced by Barton Miller's 1989 class project at the University of Wisconsin (*An Empirical Study of the Reliability of UNIX Utilities*), which fed random bytes to standard command-line tools and watched more than a quarter of them fail. Modern fuzzers — libFuzzer, AFL++, Honggfuzz, Jazzer, go-fuzz — have replaced blind random generation with feedback-directed mutation that converges on the deep code paths hand-written test suites miss.

The economic argument is straightforward. A typical test suite achieves 80–90% line coverage by exercising the code the engineer anticipated. The remaining 10–20% — error paths, parser branches, edge cases the author never imagined — is where the worst bugs live. Fuzzing, run for hours on cheap compute, routinely reaches the unanticipated branches and has uncovered thousands of memory-safety and logic bugs in widely deployed software (OpenSSL, libpng, SQLite, the Linux kernel, Chromium, every major JSON parser). OSS-Fuzz alone reported more than 40,000 bugs across 1,000+ open-source projects between 2016 and 2024.

## Coverage-Guided Fuzzing: The Feedback Loop

A coverage-guided fuzzer maintains a corpus of inputs and a set of *coverage bits* observed during execution. Each iteration picks a parent input from the corpus, mutates it, runs the program, and checks whether the new execution touched coverage bits the parent did not. If it did, the input is *interesting* and is added to the corpus; otherwise it is discarded. Over millions of iterations the corpus drifts toward inputs that explore distinct code paths.

```
                +------------------+
                |  seed corpus    |
                |  {in0, in1,...} |
                +--------+---------+
                         |
                         v
                +--------+---------+
                |  pick parent p   |
                +--------+---------+
                         |
                         v
                +--------+---------+
                |  mutate p -> p'  |   bit flip, byte swap,
                +--------+---------+   arithmetic, dictionary
                         |
                         v
              +----------+-----------+
              |  run target(p')      |
              |  with SanCov edges   |
              +----------+-----------+
                         |
              new edges? +---+ no
                  +-----+   +-----+
                  |               |
                 yes              |
                  v               v
        +---------+-------+   +----+----+
        | add p' to corpus|   | discard |
        +-----------------+   +---------+
                  |
                  v
              (repeat)
```

The two dominant families are **in-process** fuzzers (libFuzzer, go-fuzz, Jazzer) and **out-of-process** fuzzers (AFL++, Honggfuzz). In-process fuzzers link the target into the same binary, call `LLVMFuzzerTestOneInput(data, size)` in a tight loop, and rely on address sanitizer (ASan) plus signal handlers to catch crashes. They can run millions of inputs per second on a single core. Out-of-process fuzzers fork/exec the target per input, paying a ~1ms-per-input fork penalty but accepting any executable as the target, with no source modification required.

```c
// libFuzzer harness — link with: clang -fsanitize=fuzzer,address
#include <stdint.h>
#include <stddef.h>

int parse_header(const uint8_t *data, size_t size);

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // fuzzer calls this millions of times; keep it idempotent
    parse_header(data, size);
    return 0;  // 0 = keep going
}
```

Build and run:

```bash
clang -g -O1 -fsanitize=fuzzer,address -o fuzz_parse parse.c
./fuzz_parse corpus/                  # runs forever, max_total_time=N stops it
./fuzz_parse -max_total_time=300 corpus/   # 5-minute campaign
```

When a crash is found, libFuzzer writes the offending input to `crash-<sha1>` and the harness can be re-run on that single input for triage.

## The Mutation Engine

Coverage guidance only helps if mutations are *diverse enough* to reach new edges. AFL's mutation engine, which became the de-facto vocabulary for the field, combines a handful of deterministic and stochastic stages applied in order:

| Stage | Mutations | Purpose |
|-------|-----------|---------|
| **Bitflip** | Flip 1, 2, 4 bits; byte-aligned flips | Find magic-number checks (`if (x == 0xCAFEBABE)`) |
| **Arithmetic** | `+/-` small integers to bytes/words | Find off-by-one in length fields |
| **Interest** | Insert magic values (0, -1, INT_MAX, INT_MIN) | Trigger boundary branches |
| **Dictionary** | Insert tokens from a dictionary file | Past parser tokens (e.g., `Content-Type:`, `GET`) |
| **Havoc** | Random splice of multiple mutations | Combine effects |
| **Splice** | Crossover two corpus inputs | Build structured inputs from pieces |
| **Manual** | User-supplied extra mutations | Domain-specific tweaks |

A simple havoc mutator in 30 lines of Python captures the essence:

```python
import random

def havoc(data, dictionary, max_len=4096):
    out = bytearray(data)
    for _ in range(random.randint(1, 16)):
        op = random.choice(["flip", "byte", "arith", "dict", "del", "ins"])
        if not out:
            out = bytearray(random.randbytes(4))
        i = random.randrange(len(out))
        if op == "flip":
            out[i] ^= 1 << random.randint(0, 7)
        elif op == "byte":
            out[i] = random.randint(0, 255)
        elif op == "arith":
            out[i] = (out[i] + random.choice([-1, 1, -2, 2])) & 0xFF
        elif op == "dict" and dictionary:
            tok = random.choice(dictionary)
            out[i:i] = tok            # insert token at i
        elif op == "del":
            del out[i:i+1]
        elif op == "ins":
            out.insert(i, random.randint(0, 255))
        if len(out) > max_len:
            out = out[:max_len]
    return bytes(out)
```

The dictionary is a force multiplier. AFL ships with dictionaries for common formats (JPEG, XML, SQL); libFuzzer accepts `-dict=foo.dict` files with one token per line (`kw1="SELECT"`, `kw2="WHERE"`). Structure-aware fuzzers (below) replace dictionaries with real grammars.

## Coverage Feedback: SanCov Edges

The signal that drives the whole loop is *coverage*. LLVM's SanitizerCoverage (`-fsanitize-coverage=trace-cmp,pc-table,indirect-calls`, or `-fsanitize-coverage=inline-8bit-counters` for libFuzzer) instruments every basic block — more precisely every *edge* between blocks — with a call into the fuzzer runtime. The runtime hashes the calling PC together with the previous PC, producing a *bucketed edge ID*. AFL uses a 64K-entry shared-memory map indexed by `(prev_pc ^ cur_pc) >> 1`, libFuzzer uses a similar bucketed scheme. Bucketing coalesces adjacent edges to defeat the path explosion problem (without it, a corpus 100 inputs deep would have billions of distinct paths).

```
target binary, instrumented by SanCov
    |
    v  on each edge (src_pc -> dst_pc)
+----------------------+
| __sanitizer_cov_trace|
| _pc_guard(src_pc)    |   fuzzer runtime computes
+----------+-----------|   bucket = hash(prev_pc, cur_pc)
           |
           v
+---------------------+
| shared coverage map |
| [b0, b1, b2, ...]   |
+----------+----------+
           |
           v
new bucket toggled?  -> input is "interesting", keep it
```

The map must be shared between the fuzzer process and the target. libFuzzer links them in the same process; AFL uses `shm_open` plus `__AFL_SHM_ID` env var. ASan, MSan, UBSan, and the `trace-cmp` interceptor combine to surface not only crashes but also undefined-behavior bugs and comparison bytes that the mutator can use to defeat magic-number checks (the `redqueen` / *input-to-state* trick: extract constants from comparison operands, then inject them back into the input).

## Structure-Aware Fuzzing

Pure byte-level fuzzing struggles on inputs with checksums, length-prefixed fields, or grammar-defined structure: a single bit-flip invalidates a CRC, the parser rejects the input before reaching deep code, and coverage stalls. **Structure-aware** fuzzers generate inputs from a grammar or schema so every input is at least syntactically plausible.

Three approaches dominate:

1. **Protobuf mutators** — libFuzzer ships a `libprotobuf-mutator` that takes a `.proto` definition, mutates the protobuf *message tree* (rather than bytes), and serializes it to bytes for the harness. The fuzzer explores message *structures*, not byte patterns. Used by Chromium and LLVM to fuzz parsers of structured formats.
2. **Grammar fuzzers** — `nautilus`, `f1j`, `funfuzz`, and `grammarinator` take a context-free grammar (BNF, Pest, or custom) and generate derivations that are always syntactically valid. Excellent for SQL, JavaScript, and protocol fuzzing.
3. **Custom mutators** — libFuzzer exposes `LLVMFuzzerCustomMutator` and `LLVMFuzzerCustomCrossOver` so the engineer can plug domain-specific mutation logic (e.g., mutate AST nodes for an SQL parser). The custom mutator runs *before* the byte-level havoc stage.

```protobuf
// request.proto — used by libprotobuf-mutator
syntax = "proto2";
message Header {
  optional string magic = 1;
  optional uint32 version = 2;
  repeated KeyValue fields = 3;
}
message KeyValue {
  optional string key = 1;
  optional string value = 2;
}
message Request {
  optional Header header = 1;
  optional bytes body = 2;
}
```

```cpp
// Harness: protobuf in, bytes out to the target
#include "request.pb.h"
#include "libprotobuf-mutator/fuzzed_proto.h"

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    Request req;
    if (!req.ParseFromArray(data, size)) return 0;
    // Now run the real parser on the serialized bytes:
    std::string wire;
    req.SerializeToString(&wire);
    parse_request(wire.data(), wire.size());
    return 0;
}
```

The mutator now operates on the `Request` message tree — adding fields, removing fields, mutating `magic` to a constant extracted from a comparison — so the underlying byte parser receives inputs that exercise real branches rather than early-exit rejection.

## Fuzzing vs Property-Based Testing

Fuzz testing and property-based testing (PBT, see [Property-Based Testing](./property-based-testing.md)) both feed many generated inputs to a program, but they differ in what they look for and how they generate inputs.

| Dimension | Fuzz Testing | Property-Based Testing |
|------------|--------------|-------------------------|
| **Goal** | Find crashes, hangs, undefined behavior | Find property violations |
| **Oracle** | Implicit (crash = bug) | Explicit (assertion written by engineer) |
| **Generation** | Coverage-guided mutation of bytes | Strategy-driven generation per type |
| **Feedback** | Yes — SanCov edges steer generation | None — inputs are sampled blindly |
| **Typical scale** | Millions–billions of inputs / day | Hundreds–thousands per test |
| **Shrinking** | Minimal crash input from corpus (optional) | Built-in shrinking to minimal failing case |
| **Languages** | C/C++/Rust/Go/Java (compiled, with SanCov) | Any (Haskell, Python, JS, Rust, Swift) |
| **Discovery target** | Memory safety, deep parser branches | Invariants, round-trip properties, edge cases |

The boundary blurs in practice. libFuzzer's `-max_len`, dictionary, and structure-aware mutators share ideas with Hypothesis's `strategies` and `target` notes (Hypothesis can collect coverage via `coverage.py` and bias generation toward it with `@target`). The distinguishing question is whether you have an oracle. If you do (a property to assert per input), PBT suffices. If you don't (you can only detect crashes), fuzzing is the only game in town — and combining the two (use Hypothesis to *generate* seeds that libFuzzer then mutates) yields the best of both.

## Production Use

**OSS-Fuzz** (Google, 2016–present) runs continuous fuzzing on 1,000+ critical open-source projects. Maintainers submit a build script (`project.yaml` + `Dockerfile`) and a libFuzzer harness; Google builds with clang and SanCov, runs on its own cluster, files bugs to a private issue tracker, and after 90 days (or when fixed) makes them public. It has reported over 40,000 bugs as of 2024 — including the 2017 OpenSSL `BN_mod_exp` NULL-pointer crash and dozens of SQLite parser bugs. https://google.github.io/oss-fuzz/

**Google** uses fuzzing internally across the entire codebase. ClusterFuzz (the same infrastructure OSS-Fuzz is built on) runs 24/7 on every Chromium commit and on Google's internal monorepo. The 2018 Meltdown/Spectre-era CPU bugs surfaced via fuzzer-driven discovery of speculative-execution hazards; Chrome's V8 team runs Fuzzilli (a structure-aware JavaScript fuzzer) continuously. https://google.github.io/clusterfuzz/

**Microsoft** runs fuzzing at scale through the Microsoft Security Risk Detection service (formerly Project Springfield), used internally on Windows, Office, and Hyper-V, and offered commercially. More recently Microsoft has open-sourced OneFuzz (https://github.com/microsoft/onefuzz), a self-hosted fuzzing-as-a-service platform that orchestrates libFuzzer/AFL jobs on Azure, with crash triage via auto-reduction. Microsoft's 2019 paper *FarmingH32: leveraging OneFuzz* documents the impact: thousands of bugs in Windows-critical components shipped before they reached customers.

**AWS** runs fuzzing internally for Firecracker (the Rust microVM that powers Lambda and Fargate) using `cargo-fuzz` against the device-model crate; CVE-2022-29217 was caught this way before release. https://github.com/firecracker-microvm/firecracker

**Cloudflare** fuzzes its Rust TLS stack `boring` and its QUIC implementations continuously. **Mozilla** ships `funfuzz` for SpiderMonkey. **Rust** itself runs libFuzzer on the standard library's parsers as part of CI.

## Pitfalls and Best Practices

A fuzzer that finds *nothing* for weeks is almost always misconfigured. The usual suspects, in order of frequency:

1. **Harness short-circuits the target.** A `return 0` before the parsing call, a `try/except` that swallows errors, or a setup step that re-initializes per input — fix the harness so it actually exercises deep code.
2. **No seed corpus.** Starting from empty input forces the fuzzer to rediscover structure byte-by-byte. Seed the corpus with a few hundred real inputs (sample production traffic, parse test fixtures).
3. **No dictionary.** For structured formats, a hand-written or auto-extracted dictionary (the `redqueen` / input-to-state pass in AFL++ can auto-extract constants from comparison operands) can be the difference between coverage stalling at 30% and reaching 90%.
4. **Slow harness.** A 10ms harness caps throughput at 100/sec/core — 100× slower than typical. Profile with `-print_final_stats=1` and `strace -c`.
5. **Memory leaks masquerading as OOM.** Use the `-detect_leaks=1` flag (ASan) but also `-rss_limit_mb` to bound heap growth; persistent leaks cause the fuzzer to throttle the corpus.
6. **No minimization.** A 50KB crashing input is hard to triage. Run `./fuzz_target -minimize_crash=1 crash-<sha1>` to reduce it to the smallest input that still crashes.
7. **Ignoring non-crash bugs.** Many bugs surface as timeouts (`-timeout=5`) or OOM (`-rss_limit_mb=2048`) rather than crashes. Run with `-detect_leaks`, `-fork=8` for parallel corpus minimization.

## Interview Questions

**Q1: What does "coverage-guided" mean in a fuzzer, and why is coverage necessary?**
A: The fuzzer instruments the target with SanCov edge counters and tracks which edges each input touches. When a mutation reaches an edge that no prior input reached, the mutated input is added to the corpus and serves as a parent for future mutations. Without coverage feedback, the fuzzer would explore blindly — the vast majority of mutations would touch already-explored code and waste compute.

**Q2: Compare libFuzzer and AFL++.**
A: libFuzzer is in-process: the target is a `LLVMFuzzerTestOneInput` function linked into the fuzzer binary, called millions of times per second, with ASan catching crashes. AFL++ is out-of-process: it forks/execs the target per input (~1ms penalty) but accepts any executable and supports more aggressive mutators (redqueen, custom mutators, MOpt). Use libFuzzer when you have source and need speed; AFL++ when you have only a binary or want AFL's richer mutation strategies.

**Q3: Why does byte-level fuzzing struggle on protobuf/JSON inputs, and how do structure-aware fuzzers fix this?**
A: Length-prefixed fields and checksums mean a single bit flip usually invalidates the input, the parser rejects early, and coverage stalls. Structure-aware fuzzers (libprotobuf-mutator, grammarinator) mutate the parsed tree rather than the bytes, so every input is syntactically valid and the parser's deep branches are reachable. The trade-off is that you must define or import a grammar.

**Q4: How does fuzzing differ from property-based testing?**
A: Fuzzing looks for crashes (implicit oracle: did the program crash, hang, or violate a sanitizer?) and uses coverage feedback to steer generation. PBT looks for property violations (explicit oracle: an assertion the engineer wrote) and usually samples inputs blindly per type. Fuzzing finds memory-safety and parser bugs in C/C++/Rust; PBT finds invariant violations in higher-level code. They compose: PBT strategies can seed fuzz corpora.

**Q5: What is OSS-Fuzz and what problem does it solve?**
A: OSS-Fuzz is Google's free continuous fuzzing service for open-source projects. Maintainers contribute a build script and a libFuzzer harness; Google supplies the cluster, builds the project with sanitizers, runs the fuzzers 24/7, and files bugs (privately for 90 days, then publicly). It solves the "we know fuzzing works but we can't afford the infra" problem for projects like OpenSSL, SQLite, libpng, FFmpeg, and the Linux kernel — over 40,000 bugs found as of 2024.

**Q6: What is a dictionary in fuzzing, and when would you write a custom one?**
A: A dictionary is a list of tokens (`"GET"`, `"Content-Type:"`, `"<?xml"`) the mutator can inject into inputs. It dramatically speeds up reaching magic-number checks (`if memcmp(buf, "GET ", 4) == 0`). You write a custom dictionary when the target has well-known tokens (HTTP, SQL, file-format magic bytes) — or use the auto-extraction (redqueen) in AFL++ which pulls constants directly from comparison operands.

## References

- [libFuzzer documentation](https://llvm.org/docs/LibFuzzer.html) — official LLVM docs covering harness API, options, custom mutators
- [AFL++ documentation](https://aflplus.plus/) — community-maintained fuzzer that descends from Michal Zalewski's American Fuzzy Lop; source at https://github.com/AFLplusplus/AFLplusplus
- [OSS-Fuzz](https://google.github.io/oss-fuzz/) — Google's continuous fuzzing service for open-source software
- [Google Fuzzer documentation / ClusterFuzz](https://google.github.io/clusterfuzz/) — the infrastructure that runs OSS-Fuzz and Chrome fuzzing
- [libprotobuf-mutator](https://github.com/google/libprotobuf-mutator) — structure-aware mutator for libFuzzer
- [SanitizerCoverage](https://clang.llvm.org/docs/SanitizerCoverage.html) — the LLVM instrumentation that powers coverage feedback
- [Microsoft OneFuzz](https://github.com/microsoft/onefuzz) — self-hosted fuzzing-as-a-service
- [Miller, B. P. et al. (1990). *An Empirical Study of the Reliability of UNIX Utilities*](https://www.cs.wisc.edu/~bart/fuzz/CS-TR-1990-895.pdf) — the original fuzzing paper
- See also: [Property-Based Testing](./property-based-testing.md), [Differential & Metamorphic Testing](./differential-metamorphic.md), [Mutation Testing](./mutation-testing.md)
