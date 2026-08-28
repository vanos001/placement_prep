# BPF Trampolines: Generated Direct-Call Attach Points

Every dynamic instrumentation technology has to answer one question: when a
marked function runs, how does control reach your code? kprobes answer with a
breakpoint trap. ftrace answers with a patched call into a fixed trampoline
plus a dispatch loop. BPF trampolines answer with something stronger: *native
code generated per attach point*, which saves the live argument registers,
calls each attached BPF program directly, and then continues into (or past)
the original function. There is no trap, no synthesized `pt_regs`, and no
per-hit stack reservation. This page dissects that generated code, the
refcounted image architecture behind it, and how the verifier models programs
that attach through it.

The program-type view (how you *write* an fentry program) lives in
[kprobes-advanced.md](./kprobes-advanced.md); the verifier's general proof
procedure is covered in [ebpf-verifier.md](./ebpf-verifier.md). Here the focus
is the mechanism between the call site and the program.

## Three Attach Mechanisms, Side by Side

x86_64 patches the first instruction (or a compiler-planted `call __fentry__`
slot — see [ftrace-internals.md](./ftrace-internals.md)) to redirect execution.
The three regimes differ in what happens after the redirect:

| Mechanism | Patch site | Path per invocation | Stack/regs cost |
| --- | --- | --- | --- |
| kprobe | int3 (0xCC) over first insn | trap → handler → pre_handler → single-step OOL → trap → post_handler | full `pt_regs` synthesis, 2 traps |
| ftrace | 5-byte `call __fentry__` nop | patched call → ftrace trampoline → ops dispatch loop | `ftrace_regs` frame, one call |
| BPF trampoline | same 5-byte slot | patched call → generated image → direct `call` per BPF prog | ~2 register spills, zero pt_regs |

The decisive structural difference: kprobes and ftrace funnel every hit
through generic dispatch code that must be prepared for *anything*. A BPF
trampoline is compiled for exactly one attach point — it knows the target
function's signature from BTF at attach time — so the generic work happens
once, at attach time, and the per-hit work is only what the program actually
needs.

## Anatomy of the Generated Code

When the first program attaches to a function, `bpf_trampoline_update()`
JIT-compiles an image. Conceptually the image for an fentry+fexit pair looks
like this:

```text
   tcp_v4_connect()                     trampoline image (generated code)
  -----------------                    --------------------------------------
    push rbp/rbx...                     prologue: save caller-saved regs
    ...                                 (frames used by the original function
    call __fentry__   == patched ==>      are relocated per the BTF model)
      (5-byte slot)                     build ctx: pack live arg regs into
    ... body ...                          a struct the prog types reference
    ret                                 call fentry prog #1 (direct, native)
                                        call fentry prog #2 ...
                                        restore original arg regs
                                        call original function body
                                        stash return value in run_ctx
                                        call fexit prog #1 (sees retval)
                                        restore regs; ret to real caller
```

Properties that fall out of this design:

- **Zero trap overhead.** The patched slot is a plain `call`; the trampoline
  runs on the caller's own kernel stack with a small frame, so there is no
  `int3` vectoring, no single-stepping, and no `MAX_STACK`-sized reservation
  the way kprobes budget for worst-case stack use.
- **Direct calls, not prog arrays.** Each attached program is a native `call`
  to its JIT image, the same shape as the XDP fast path's "one program, one
  call" contract. Dispatch cost is O(programs attached), with no hash lookups
  or list walks on the hot path.
- **fexit sees the return value and, for `void`-returning targets, the
  original argument registers too** — because the image keeps them live
  across the call to the original function. A kretprobe cannot do this
  without caching the entry context itself.
- **fmod_ret can rewrite the return.** Modifier programs run *instead of*
  calling the original (or after it, short-circuiting with a chosen retval);
  the image writes the chosen value into the return register.

Only functions that were compiled with an fentry nop have a patch site, and
the attach target must carry BTF; `bpf_check_attach_target()` rejects
functions without BTF, `__init`-section functions, and other
not-instrumentable targets at attach time.

## fentry, fexit, fmod_ret: The Program-Type Contract

All three load as `BPF_PROG_TYPE_TRACING` with an `attach_btf_id` naming the
target. The differences are where in the image the program's call lands and
what it may do:

| Program flavor | Runs | Sees | May modify retval | Requires |
| --- | --- | --- | --- | --- |
| fentry | before original body | arg regs (BTF-typed) | no | BTF + patch site |
| fexit | after original body | args + return value | no | BTF + patch site |
| fmod_ret | before body, may skip it | args | yes | `ALLOW_ERROR_INJECTION` on target |

The `ALLOW_ERROR_INJECTION` requirement is deliberate: only functions the
kernel maintainers have explicitly marked may have their results overridden.
The largest fmod_ret consumer is BPF LSM, which attaches security hooks and
votes on allow/deny decisions. Sleepable programs (`BPF_F_SLEEPABLE`) may
attach to fentry/fexit/fmod_ret targets only from an explicit
`may_sleep`-validated allowlist, because the trampoline call context must
tolerate the program blocking.

## How the Verifier Models Trampoline Programs

For a kprobe program the verifier sees one opaque `struct pt_regs *ctx` and
must force every read through `bpf_probe_read*()` because it cannot know what
the registers pointed at. For a trampoline-attached program the verifier has
the target's BTF signature, so:

- arguments become **`PTR_TO_BTF_ID`** pointers to the *actual* kernel types
  (`struct sock *`, `struct tcp_sock *`), so the program dereferences fields
  directly and the verifier enforces offset/type bounds per field;
- the BTF type graph also fixes **argument lifetime and reference rules**:
  if a target takes or returns a refcounted pointer (kfuncs do), the verifier
  can require the program to release it;
- the program is verified *against that one attach point* — a program loaded
  for `fentry/tcp_v4_connect` cannot silently reattach elsewhere, and
  incompatibility is caught at attach time rather than by a crash.

The cost is coupling: when a target function's signature changes across
kernel versions, BTF changes with it, and stale fentry programs fail to
attach — the verifier turns what used to be silent memory corruption into a
load-time error.

## Images, Refcounts, and the Link Type

The runtime object is `struct bpf_trampoline`, keyed by attach BTF ID:

- it holds up to `TRAMPOLINE_MAX_...`-bounded lists — `entry_progs` (fentry),
  `exit_progs` (fexit), and `mod_ret_progs` — plus a regenerated image;
- the image is **refcounted and shared**: ten fexit programs on
  `tcp_retransmit_skb` share one trampoline and one patched call site, and
  `image->refcnt` tracks them; the image is only torn down when the last
  link detaches;
- when a new program joins, the kernel **recompiles the whole image** (all
  programs' call sequences in one blob) and swaps it in — attachment is
  atomic, mid-flight callers see either the old or the new image;
- each attachment is a `struct bpf_link` of type `BPF_LINK_TYPE_TRACING`,
  giving fd-based ownership, `bpf_link_detach()`, and pinning semantics —
  the same lifecycle every modern BPF attachment uses.

This is also the substrate for **freplace**: a freplace program replaces a
global function by pointing the caller-side call at a trampoline-like image
that never calls the original — the same generated-code machinery with the
"call original" step deleted.

## Where Trampolines Carry Production Load

- **BPF TCP congestion control (struct_ops).** Since kernel 5.6,
  `struct tcp_congestion_ops` can be implemented in BPF; each ops callback a
  program implements is dispatched through a generated trampoline, so the
  kernel calls BPF-written `ssthresh()`/`cong_avoid()` as native calls (see
  the LWN struct_ops article in the references).
- **BPFtrace's `kfunc:`/`kretfunc:` probes.** Modern bpftrace defaults these
  to fentry/fexit attachment; scripts that used kprobes migrate to the
  typed, cheaper mechanism without changing their source semantics.
- **BPF LSM.** Every hooked security hook that a BPF program guards is an
  fmod_ret trampoline attachment.
- **A common conflation worth flagging:** XDP programs attach through the
  netdev BPF hook (a prog-array dispatch on the driver path), *not* through
  trampolines. "XDP metadata" kfuncs (e.g. device-supplied RX timestamps)
  are ordinary kernel functions — which fentry *programs can trace*, which
  is where the two features genuinely meet.

## Overhead: A Deterministic Model

The trap-free design shows up as a structural cost difference, not just a
tuning difference. The model below fixes order-of-magnitude x86_64 costs for
each stage of both paths and computes per-invocation totals; constants are
stated in the source so the arithmetic is auditable.

```python
# Deterministic per-invocation overhead model: kprobe (int3) vs BPF trampoline.
# Cycle counts are order-of-magnitude x86_64 constants (documented below); the
# point is the structural cost difference, not a microbenchmark.

# Cost components (cycles) for one invocation of an instrumented function.
KPROBE = {
    "int3 trap + do_int3 + notifier chain": 180,
    "kprobe dispatch (hash + aggregate list)": 55,
    "pre_handler call": 25,
    "single-step trap on OOL buffer": 170,
    "post_handler call": 25,
    "pt_regs restore + resume": 60,
}
FENTRY = {
    "patched call into trampoline image": 5,
    "prologue: save caller-saved regs": 12,
    "build BPF ctx from live regs (no pt_regs)": 16,
    "direct call into JIT'd prog body": 30,
    "epilogue: restore regs, ret to caller": 9,
}
FEXIT = dict(FENTRY)
FEXIT["read exit regs from run_ctx"] = 12
FMOD_RET = dict(FEXIT)
FMOD_RET["rewrite return value in run_ctx"] = 8

k  = sum(KPROBE.values())
fe = sum(FENTRY.values())
fx = sum(FEXIT.values())
fm = sum(FMOD_RET.values())
print("per-invocation overhead model (x86_64 cycles, fixed constants)")
print(f"{'mechanism':<22}{'structure':<44}{'cycles':>7}")
print(f"{'kprobe pre+post':<22}{'2 traps: int3 + OOL single-step':<44}{k:>7}")
print(f"{'fentry (trampoline)':<22}{'direct call, no pt_regs, no trap':<44}{fe:>7}")
print(f"{'fexit (trampoline)':<22}{'same + exit-regs readout':<44}{fx:>7}")
print(f"{'fmod_ret (trampoline)':<22}{'same + return-value rewrite':<44}{fm:>7}")
print(f"\nspeedup fentry vs kprobe : {k/fe:.1f}x")
print(f"speedup fexit vs kprobe  : {k/fx:.1f}x")

# Attach-point scaling: N programs, one target function.
print("\nsame target function, N attached programs (cycles per hit)")
print(f"{'N':>3}{'kprobe aggregate chain':>24}{'trampoline chain':>18}")
for n in (1, 4, 16, 64):
    kp = k + 25 * (n - 1)          # every pre_handler runs in one trap
    tr = 40 + 30 * n               # one direct call per prog, shared prologue
    print(f"{n:>3}{kp:>24}{tr:>18}")
print("\nrefcount note: the N trampoline programs share ONE image; "
      "bpf_trampoline.image->refcnt = N. The N kprobes keep N hash entries "
      "but collapse into one aggr list at the single int3 site.")
```

```text
per-invocation overhead model (x86_64 cycles, fixed constants)
mechanism             structure                                    cycles
kprobe pre+post       2 traps: int3 + OOL single-step                 515
fentry (trampoline)   direct call, no pt_regs, no trap                 72
fexit (trampoline)    same + exit-regs readout                         84
fmod_ret (trampoline) same + return-value rewrite                      92

speedup fentry vs kprobe : 7.2x
speedup fexit vs kprobe  : 6.1x

same target function, N attached programs (cycles per hit)
  N  kprobe aggregate chain  trampoline chain
  1                     515                70
  4                     590               160
 16                     890               520
 64                    2090              1960

refcount note: the N trampoline programs share ONE image; bpf_trampoline.image->refcnt = N. The N kprobes keep N hash entries but collapse into one aggr list at the single int3 site.
```

Two readings of the scaling table matter in practice. First, at small N the
trampoline wins by roughly the cost of two traps (~450 cycles here) — that is
the "zero stack overhead, direct calls" claim made concrete. Second, the
curves *cross* at high N: a kprobe aggregate chain calls plain C function
pointers, while the trampoline must direct-call N separate JIT bodies, so a
function shared by dozens of heavyweight programs is the one workload where
the kprobe path stays competitive. Real deployments rarely hit that point;
profile-driven teams instead split programs across fentry/fexit or batch
their work into one program.

## Limits and Gotchas

- **Arch support is not uniform.** Trampolines shipped first on x86_64;
  arm64 and other ports followed. A program attachable on one arch may be
  rejected on another where the image generator lacks register-model support.
- **Image churn under attach storms.** Every new attachment regenerates the
  image; attaching thousands of programs to one function serializes behind
  image rebuilds rather than amortizing.
- **Verifier coupling is a feature and a tax.** Signature changes in the
  kernel invalidate old attach points (good for safety, awkward for
  pre-compiled CO-RE binaries — they must handle attach-time failure).
- **fmod_ret is allowlisted by design.** You cannot hijack an arbitrary
  function's return value; if the hook you want is not annotated, the only
  routes are kprobes (observe) or upstreaming an `ALLOW_ERROR_INJECTION`
  annotation.

## See Also

- [kprobes-advanced.md](./kprobes-advanced.md) — writing fentry/fexit
  programs, and the kprobe machinery the trampoline bypasses.
- [ebpf-verifier.md](./ebpf-verifier.md) — the proof procedure that models
  `PTR_TO_BTF_ID` arguments for trampoline programs.
- [ftrace-internals.md](./ftrace-internals.md) — the fentry patch site the
  trampoline reuses, and the ops dispatch loop it avoids.

## References

1. Starovoitov, A., *Introduce BPF trampoline* (patch series, LWN mirror,
   Nov 2019) — <https://lwn.net/Articles/804937/> (verified HTTP 200).
2. Corbet, J., *Kernel operations structures in BPF* (struct_ops/BPF TCP
   congestion control, 5.6), LWN, Feb 2020 — <https://lwn.net/Articles/811631/> (verified HTTP 200).
3. eBPF Docs, *Trampolines* (concept reference) —
   <https://docs.ebpf.io/linux/concepts/trampolines/> (verified HTTP 200).
4. eBPF Foundation, *Bouncing on trampolines to run eBPF programs* —
   <https://ebpf.foundation/bouncing-on-trampolines-to-run-ebpf-programs/> (verified HTTP 200).
5. bpftrace Reference Guide (`kfunc:`/`kretfunc:` probe types) —
   <https://github.com/bpftrace/bpftrace/blob/master/docs/reference_guide.md> (verified HTTP 200).

*Bot-blocked probes:* `docs.kernel.org/bpf/trampoline.html` returns **404**
(no such page — the mechanism is documented via the eBPF docs site and the
patch series instead, contrary to common third-party citations);
`lore.kernel.org` returns **403 to curl**, so the original trampoline patch
series is cited via its LWN mirror above.
