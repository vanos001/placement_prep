# RCU Torture Testing: Validating Lockless Code at Kernel Scale

Read-copy-update (RCU) is unusual among synchronization primitives in that the kernel ships its own adversarial test infrastructure for it — and has run it continuously for two decades. `rcutorture` (kernel source `kernel/rcu/rcutorture.c`) exists because the RCU contract is subtle in exactly the way humans get wrong: a grace period must not complete while *any* reader that started before it still holds a reference, but readers leave almost no trace — no count, no lock, nothing the implementation can poll. The only way to gain confidence in such a contract is to stress it: hammer the primitive with readers and writers at scale, under every flavor of preemption, CPU hotplug, and forward-progress pressure the kernel can synthesize, and instrument the results so that a contract violation *looks like something* when it happens. For [RCU itself](./rcu.md) and [SRCU](./srcu.md), see those pages; this page is about the testing machinery and the transferable lessons it teaches about validating lockless code of your own.

The infrastructure has three layers, and it is worth keeping them separate in your head: the **torture module** (`CONFIG_RCU_TORTURE_TEST`, buildable as a loadable module) that runs the actual read/write stress in-kernel; the **scenario configurations** (Kconfig fragments under `tools/testing/selftests/rcutorture/configs/`) that pin down one environment per run; and the **harness** (`kvm.sh`, same selftests directory) that builds kernels, boots each scenario in QEMU, waits, and greps the console output for failure signatures. The path itself is a recent fact worth knowing: the whole thing moved from `tools/testing/rcutorture/` to `tools/testing/selftests/rcutorture/` in 2024, which breaks every older tutorial that gives paths without the `selftests/` component.

## What rcutorture Actually Tests

The core instrument is the "pipe". The writer task continuously replaces a global pointer to an `rcu_torture` object (fields verified from the source: `rtort_pipe_count`, plus payload pages); every replaced object joins an aging list and advances **one pipe stage per completed grace period** (`rcu_torture_pipe_update_one()`), being recycled when its stage reaches `RCU_TORTURE_PIPE_LEN = 10`. Each object therefore encodes how many grace periods have elapsed since it was unlinked. A reader that ends its read-side critical section and finds `pipe_count > 0` on the object it holds has just *observed a grace period that completed while it was reading* — a contract violation, tabulated into the per-CPU `rcu_torture_count[]` histogram that the periodic stats printout renders as the famous `Reader Pipe:` line. Bucket 0 is health; nonzero buckets mean the implementation let a grace period pass under a live reader.

This design has two properties that make it a template for testing your own lockless code. First, the *evidence lives in the data the readers touch*: there is no external oracle, because an RCU violation is invisible to a kernel that isn't looking — the aged object is the oracle. Second, the check is *cheap enough to run always*: two loads and a compare at read exit, which is why the torture runs for hours without distorting what it measures. The source is blunt about the known-broken control case: a `pipe_count` beyond the pipe length "Should not happen in a correct RCU implementation, happens quite often for torture_type=busted" — `busted` is the deliberately fake implementation used to prove the harness can actually catch failures.

## The Cast: Tasks and Module Parameters

Loading `rcutorture` spawns the task family (all names verified from `kernel/rcu/rcutorture.c`):

| Task | Role |
|------|------|
| `rcu_torture_writer` | Replaces the current object on a timer, drives it through the pipe; owns the state machine (`RTWS_DELAY`, `RTWS_REPLACE`, `RTWS_DEF_FREE`, `RTWS_EXP_SYNC`, `RTWS_COND_GET`, ...) that cycles through grace-period-wait styles |
| `rcu_torture_reader` | Take read-side critical sections of varying flavor (plain `rcu_read_lock()`, BH, SRCU, preemption-enabled variants), snapshot the pointer, and run the pipe check at section end (one kthread per reader; the accompanying `rcu_torture_reader_do_mbchk()` cross-checks concurrent readers) |
| `rcu_torture_fakewriter` | Exists only to wait for grace periods without publishing — diluting writer activity so reader pressure dominates, and exercising GP machinery with no payload traffic |
| `rcu_torture_stats` | Periodically prints the `Reader Pipe:` / `Reader Batch:` histograms and writer-state |
| `rcu_torture_fwd_prog` | Forward-progress prober: verifies that grace periods *complete* under adversarial scheduling (`fwd_progress`, `fwd_progress_div`, `fwd_progress_holdoff` module params) |
| `rcu_torture_stall` | Deliberately holds a CPU inside an RCU read-side critical section (or across `cond_resched()` boundaries) to trigger and validate RCU stall warnings |
| `rcu_torture_boost` / `rcu_torture_barrier` / `rcu_torture_updown` | Specialized stress: RCU-boost priority inversion, `call_rcu()` barrier semantics, and up/down (hrtimer) readers |

Key module parameters (registration via the `torture_param()` macro, descriptions verbatim from the source): `torture_type` ("Type of RCU to torture (rcu, srcu, ...)"), `nreaders` ("Number of RCU reader threads"), `fqs_duration`/`fqs_holdoff`/`fqs_stutter` (forced-quiescent-state bursts — how hard the implementation is squeezed to find quiescent states), `gp_cond`/`gp_cond_exp`/`gp_cond_full` (select conditional and expedited GP-wait primitives), and `extendables` (which reader-side extensions the readers may apply).

## Torture Types and Scenarios

`torture_type` selects the primitive under test — all ten values verified in the source: `rcu`, `busted` (the self-confessed broken control), `srcu`, `srcud`, `busted_srcud` (the broken SRCU control), `trivial` (CONFIG_PREEMPT=n-only testing), `trivial-preempt`, `tasks`, `tasks-rude`, `tasks-tracing`. Each type defines the same operation interface (`readlock`, `readunlock`, `deferred_free`, `get_gp_state`, ...), which is why one harness exercises ten primitives with identical instrumentation.

A *scenario* is one Kconfig fragment plus boot arguments — one hypothesis about an environment that could break RCU. The canonical list lives in `tools/testing/selftests/rcutorture/configs/rcu/CFLIST`: `TREE01` through `TREE09` (plus more), `SRCU-N`, `SRCU-P`, `TINY01`, and friends. `TREE04`, for example, is exactly this fragment (fetched from the tree): `CONFIG_SMP=y`, `CONFIG_NR_CPUS=8`, `CONFIG_PREEMPT_LAZY=y`, with `CONFIG_PREEMPT_NONE/VOLUNTARY/PREEMPT/PREEMPT_DYNAMIC` all `=n`, and the self-check marker `#CHECK#CONFIG_TREE_RCU=y` that the harness verifies after the build. The scenarios span the preemption matrix, CPU counts from tiny to large, and debug-option combinations; running the full set is the closest thing RCU has to a proof.

## kvm.sh: The Harness

`kvm.sh` (same directory, `bin/kvm.sh`) automates one scenario end-to-end: configure, build, boot under QEMU, run for a duration, shut down, and scan the console log for torture alerts. Flags verified from the script itself:

| Flag | Purpose |
|------|---------|
| `--configs "TREE04 TREE09"` | Scenario list to run |
| `--duration 30` | Minutes per run (accepts `h`/`d` suffixes) |
| `--kconfig "CONFIG_DEBUG_OBJECTS_RCU_HEAD=y"` | Extra Kconfig per run |
| `--bootargs "rcutorture.fqs_duration=1000"` | Kernel boot arguments passed through |
| `--allcpus` | Give the guest all host CPUs |
| `--cpus`, `--memory` | Guest CPU/memory sizing |
| `--dryrun sched` | Print the plan without building |
| `--buildonly` | Build without booting |
| `--jitter`, `--shutdown-grace`, `--trust-make`, `--kasan`, `--kcsan`, `--results`, `--datestamp` | Timing jitter injection, shutdown pacing, incremental rebuild reuse, sanitizer builds, output locations |

A typical invocation — `kvm.sh --configs "TREE04 TREE09" --duration 30 --kconfig "CONFIG_PROVE_LOCKING=y"` — runs two scenarios for half an hour each and leaves per-scenario result directories. Failures surface as console greps: torture alerts, `Reader Pipe:` buckets above zero at end-of-test, RCU CPU stall warnings, or QEMU timeouts, each retained verbatim in the results tree.

## Stall Warnings and Forward Progress

Two companion mechanisms turn "hung" into "diagnosed". The **RCU CPU stall detector** (documented in `Documentation/RCU/stallwarn.rst`, options verified there: `rcu_cpu_stall_timeout`, `rcu_cpu_stall_suppress`, `rcu_cpu_stall_cputime`) prints a volumetric warning when a grace period appears stuck — naming the CPU blocking progress and the task holding the read-side critical section. `rcutorture`'s `rcu_torture_stall` task manufactures exactly this condition on demand, so the warning path itself is exercised every run rather than only in production incidents. Forward progress is the other half: a grace period that *eventually* completes but only under luck is still a bug, and the `rcu_torture_fwd_prog` task's params (`fwd_progress`, `fwd_progress_div`, `fwd_progress_holdoff`) exist to catch livelocks under heavy load, nohz_full configurations, and hrtimer pressure — the class of failure that simple timeout-based testing misses because the system was never actually dead, just starving.

## Worked Demo

```python
"""Userspace mini-rcutorture: deterministic single-thread event loop modeled on
kernel/rcu/rcutorture.c. The writer publishes a page object (version, a, b);
every replaced page joins an aging list and advances one pipe stage per
completed grace period (rcu_torture_pipe_update_one), being freed when its
stage reaches RCU_TORTURE_PIPE_LEN=10. A reader that ends its critical section
holding a page already in the pipe (pipe_count > 0) has observed a grace
period that did not wait for it -- the exact contract rcutorture's
rcu_torture_count[] histogram checks. Mode 'busted' emulates
torture_type=busted: grace periods complete instantly."""
PIPE, TICKS, PUBLISH_EVERY = 10, 140, 6

def run(mode):
    cur = {"ver": 0, "a": 0, "b": 0, "pipe": 0}
    publishes = gps = freed = 0
    reads = violations = 0
    hist = [0] * (PIPE + 1)          # bucket = pipe stage at read end
    active = {}                      # reader -> (page, end_tick, start_tick)
    pending = []                     # grace periods in flight: (start_tick, ...)
    aging = []                       # replaced pages, one stage per GP
    for t in range(TICKS):
        # 1) writer publishes every PUBLISH_EVERY ticks
        if t % PUBLISH_EVERY == 3 and t < TICKS - PUBLISH_EVERY:
            old, cur = cur, {"ver": cur["ver"] + 1, "a": 0, "b": 0, "pipe": 0}
            publishes += 1
            if mode == "busted":     # instant "grace period"
                gps += 1
                aging.append(old)
                still = []
                for pg in aging:     # every removed page advances one stage
                    pg["pipe"] += 1
                    if pg["pipe"] >= PIPE:
                        freed += 1
                    else:
                        still.append(pg)
                aging = still
            else:
                aging.append(old)
                pending.append(t)
        # 2) one grace period completes when no pre-existing reader is active
        if mode == "clean" and pending:
            start_tick = pending[0]
            if all(end < t or st_tick >= start_tick
                   for st_tick, end in ((v[2], v[1]) for v in active.values())):
                pending.pop(0)
                gps += 1
                still = []
                for pg in aging:     # rcu_torture_pipe_update(): all pages age
                    pg["pipe"] += 1
                    if pg["pipe"] >= PIPE:
                        freed += 1
                    else:
                        still.append(pg)
                aging = still
        # 3) readers: three fixed schedules, 2-tick sections
        for r in range(3):
            if (t + r) % 5 < 2:
                if r not in active:              # section start: snapshot pointer
                    active[r] = (cur, t + 1, t)
                elif active[r][1] == t:          # section end: the contract check
                    page = active.pop(r)[0]
                    reads += 1
                    hist[min(page["pipe"], PIPE)] += 1
                    if page["pipe"] > 0:         # GP passed while reader held page
                        violations += 1
    return publishes, gps, reads, hist, violations, freed, publishes + 1

for mode in ("clean", "busted"):
    pubs, gps, reads, hist, viol, freed, pool = run(mode)
    print(f"mode={mode}  pages published={pubs}  grace periods={gps}  reads={reads}  pages freed={freed}")
    print("  Reader Pipe: " + " ".join(f"{h:>2}" for h in hist))
    print(f"  reads ending on an aged (in-pipe) page: {viol}")
    print(f"  End of test: {'SUCCESS' if viol == 0 else 'FAILURE'}")
```

```text
mode=clean  pages published=22  grace periods=22  reads=56  pages freed=13
  Reader Pipe: 56  0  0  0  0  0  0  0  0  0  0
  reads ending on an aged (in-pipe) page: 0
  End of test: SUCCESS
mode=busted  pages published=22  grace periods=22  reads=56  pages freed=13
  Reader Pipe: 47  9  0  0  0  0  0  0  0  0  0
  reads ending on an aged (in-pipe) page: 9
  End of test: FAILURE
```

The two modes are structurally identical — same publish schedule, same reader schedules, same pipe mechanics — and differ only in whether grace periods wait for pre-existing readers. In `clean` mode all 56 reads end with their page still in bucket 0: every grace period waited for every reader that held the old page, and 13 fully-aged pages were recycled, showing the pipe draining as designed. In `busted` mode, 9 of 56 reads ended on a page already advanced into pipe stage 1 — the implementation freed-or-aged memory the reader was still holding, which is the exact event the kernel's histogram records as nonzero buckets. Note the kernel allocates its object pool at `10 * RCU_TORTURE_PIPE_LEN` entries: the pool must outlast the longest possible aging chain, which is why "freed" lags "published" even in the healthy run.

## Lessons for Your Own Lockless Code

The transferable checklist, straight from what the infrastructure does: **(1)** build the aged-object oracle — make contract violations visible in data the hot path already touches, not in external assertions; **(2)** include a deliberately broken control implementation (the kernel's `busted`) to prove your detector fires; **(3)** vary the environment systematically (preemption, CPU count, hotplug, forward-progress pressure) the way scenarios do, because lockless bugs are environment-shaped; **(4)** keep the in-path check cheap enough to run always; and **(5)** never trust a single long run — the kernel runs disjoint *scenarios* because each isolates one hypothesis. For static-rule checking the complement is [lockdep](./lockdep.md), for broader in-kernel test frameworks see [KUnit](../debugging/kunit.md); rcutorture's niche is the runtime contract that neither static tool can see.

## Interview Questions

1. **Why is the pipe mechanism an adequate oracle for RCU — what does it actually catch?** It catches grace periods that complete while a reader still holds an object replaced before that grace period began — the core "too short GP" failure, including flavors caused by missing memory barriers on the reader exit path. It does not catch stale-read hazards outside RCU's contract (data the reader misinterprets) — that's what `rcu_torture_reader`'s value-pair checks and the `rtort_mbtest` word add.
2. **What is the point of `rcu_torture_fakewriter`? Why would a test want writers that don't write?** Grace-period machinery must be exercised without conflating it with payload churn. Fakewriters issue GP waits with no replacement, changing the reader/writer ratio and GP cadence; failures that only appear when writer traffic is sparse (or dense) get isolated this way.
3. **`torture_type=busted` intentionally fails. Why ship a known-broken implementation?** A detector that has never seen a failure cannot be trusted; `busted` is the control case proving the pipe histogram, alerts, and end-of-test verdicts actually fire. Every serious test harness needs its "always fails" calibration — without it, a silent detector and a correct implementation are indistinguishable.
4. **You must validate a custom seqlock-like primitive for an embedded kernel. What do you borrow from rcutorture?** The aged-object oracle (embed a generation counter in returned objects; check at use end), the fake-writer concept (GP-like waits without payload), a scenario matrix (preemption, SMP count, hotplug), the deliberate-broken control, and console-grep-able verdicts (`End of test: SUCCESS/FAILURE`) so CI can gate on words, not heuristics.

## References

1. Linux kernel source, `kernel/rcu/rcutorture.c` (task names, `torture_param()` descriptions, pipe mechanism, `RCU_TORTURE_PIPE_LEN=10`). https://raw.githubusercontent.com/torvalds/linux/master/kernel/rcu/rcutorture.c
2. Linux kernel source, `tools/testing/selftests/rcutorture/bin/kvm.sh` (flag set verified above). https://raw.githubusercontent.com/torvalds/linux/master/tools/testing/selftests/rcutorture/bin/kvm.sh
3. Linux kernel source, `tools/testing/selftests/rcutorture/configs/rcu/CFLIST` and `TREE04` (scenario fragments). https://raw.githubusercontent.com/torvalds/linux/master/tools/testing/selftests/rcutorture/configs/rcu/CFLIST
4. Linux kernel documentation, `Documentation/RCU/rcu.rst`. https://raw.githubusercontent.com/torvalds/linux/master/Documentation/RCU/rcu.rst
5. Linux kernel documentation, `Documentation/RCU/stallwarn.rst` (`rcu_cpu_stall_timeout` et al.). https://raw.githubusercontent.com/torvalds/linux/master/Documentation/RCU/stallwarn.rst
6. Kernel.org rendered RCU documentation. https://www.kernel.org/doc/html/latest/RCU/rcu.html
