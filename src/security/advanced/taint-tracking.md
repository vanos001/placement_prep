# Taint Tracking and Information Flow Control

Access control asks "who may call this operation?"; information flow asks
"where did this data go?". The second question is the one that matters
when the danger is not an unauthorized call but an authorized one - the
password field logged by a legitimate logging call, the secret key
flattened into a world-readable cache, the untrusted string concatenated
into a query. Taint tracking and information-flow control (IFC) make
"where data flows" a first-class, checkable property. This page builds
both the dynamic machinery (shadow-memory taint, as used by Dytan,
libdft, TaintDroid) and the static lattice model (Denning), and shows the
classic limits: implicit flows and covert channels.

Related pages: [web security](../web-security.md) (where untrusted-input
validation is the frontend of this problem), [sandboxing](./sandboxing.md)
(the complementary confinement mechanism), and
[cryptography](../../security/cryptography.md) for the key-handling
policies IFC systems try to enforce.

## The dynamic model: taint as shadow state

Dynamic taint tracking threads a "tainted" bit (or a richer label) through
every value the program touches:

- **Sources** introduce taint: network reads, argv, file contents, HTML
  inputs, hardware counters.
- **Propagators** move it: `t = a + b` taints t if a or b is tainted;
  memcpy propagates byte-for-byte; comparisons can leak (below).
- **Sinks** check it: `exec()` taints on any argument; a log call taints
  on password-labeled data; a return-to-user sink taints on kernel
  pointers (the classic kernel-exploit detector).

Implementation is a shadow map: for x86 emulation tools (libdft) one
shadow byte per register and shadow page per memory page - roughly 1/8
memory overhead and a 2-10x slowdown depending on instrumentation density
(hence its research-tools niche rather than production fleets). TaintDroid
(Android, OSDI 2010) took the pragmatic route: taint at the interpreter's
variable level plus inter-component messaging, which gave system-wide
tracking at ~14% overhead on a phone and produced the famous finding that
two-thirds of the studied apps misused location/identifier data.

```text
  source:  tainted = net_read()
  prop:    q = tainted + 1        q: tainted (arithmetic propagates)
           if q > 0 ...           branch CONDITION influenced - see implicit flows
  sink:    exec(q)                <- policy violation flagged here
           log(q)                 <- ok for data, not for secrets
```

## The static model: Denning's lattice

Denning (1976) framed IFC statically: every variable carries a security
class in a lattice (say `L < H` for public/secret, or a richer product
lattice over principals); assignment `x := y` requires
`class(x) >= class(y)` (data may only flow *up*, toward more restricted).
The compiled check proves that no execution - not one input - violates
the policy, which dynamic tracking can never promise. The price: policy
expressiveness is bounded by the lattice, and real programs need
declassification ("this hash of the password is public") that must be
explicit, audited, and small.

Decentralized IFC (Myers' Jif, HiStar, Flume) generalizes the lattice to
per-principal label graphs with integrity components - Flume applied it
to OS processes with labels on file descriptors, the design lineage
behind Chrome's site-isolation thinking.

## Implicit flows: the hole everyone falls into once

Explicit propagation is the easy 90%. The remaining 10% is why IFC is a
discipline and not a library call:

```text
  if (secret != 0):            # secret is HIGH
      public = 1               # public is LOW - assignment in a
                               # secret-dependent branch LEAKS one bit
```

No explicit data moved from secret to public; the *control flow* carried
the bit. Sound systems handle this by requiring branch conditions to be
at least as restrictive as every assignment inside them (program-counter
label, as in Jif) - and dynamic taint trackers either ignore this (false
negative) or taint the branch and explode in false positives. Timing
makes it worse: even a constant-time program leaks through cache sets -
which is why covert channels are formally *out of scope* for IFC (they
cannot be eliminated without eliminating concurrency itself) and why
[constant-time crypto](./side-channel-resistant.md) is its
own discipline.

## The demo: lattice IFC + dynamic taint on one toy IR

The implementation below runs both engines on the same tiny instruction
stream: a static lattice checker (with PC-label for implicit flows) and a
dynamic taint interpreter. The stream is crafted so the dynamic tracker
misses the implicit leak the static checker catches - the exact
complementarity the theory predicts.

```python
#!/usr/bin/env python3
"""Two IFC engines over one toy IR:

  static  : Denning-style lattice (L < H) + program-counter label.
            Proves the whole stream safe/unsafe BEFORE execution.
            Catches implicit flows (assignments under H-conditions).
  dynamic : per-variable taint bits + branch-condition tainting,
            the TaintDroid-style compromise (no PC-label carry-out).

The IR stream contains an explicit violation, an implicit leak, and a
clean segment - each engine's verdict per instruction is printed."""

L, H = 0, 1                     # lattice: L < H
NAME = {L: "L", H: "H"}


def join_static(pc_label, value_class):
    """static check for x := v: require class(x) >= pc_join(v, pc)"""
    return max(value_class, pc_label)


# IR: (op, dst, operands, comment)
#   label classes: secret=H, public=L
IR = [
    ("const", "pw",   H, "pw := read_password()   [source, H]"),
    ("const", "user", L, "user := read_username() [source, L]"),
    ("binop", "hash", "pw", "hash := H(pw)  [derived from H]"),
    ("declassify", "hash", L, "declassify(hash -> L) [audited declass]"),
    ("sink", "LOG", "hash", "log(hash)        [ok: hash now L]"),
    ("sink", "LOG", "pw",   "log(pw)          [VIOLATION: H into LOG sink]"),
    ("branch", "IF", "pw",  "if pw != 0:      [pc becomes H]"),
    ("const", "flag", L,    "  flag := 1     [implicit leak: L store under H-pc]"),
    ("label", "ENDIF", None, "endif          [pc back to L]"),
    ("sink", "NET", "flag", "send(flag)      [flag leaked the secret bit]"),
]


def static_check(ir):
    print("STATIC (Denning lattice + PC label):")
    pc = L
    classes = {}
    ok = True
    for op, dst, a, comment in ir:
        if op == "const":
            cls = a
            cls_eff = join_static(pc, cls)
            classes[dst] = cls_eff
            print(f"  {comment:<48} class({dst})={NAME[cls_eff]}")
        elif op == "binop":
            cls_eff = join_static(pc, classes.get(a, L))
            classes[dst] = cls_eff
            print(f"  {comment:<48} class({dst})={NAME[cls_eff]}")
        elif op == "declassify":
            classes[dst] = a
            print(f"  {comment:<44} class({dst})={NAME[a]} (audited)")
        elif op == "branch":
            pc = max(pc, classes.get(a, L))
            print(f"  {comment:<48} pc={NAME[pc]}")
        elif op == "label":
            pc = L if dst == "ENDIF" else pc
            print(f"  {comment:<48} pc={NAME[pc]}")
        elif op == "sink":
            sink, var = dst, a
            need = L if sink in ("LOG", "NET") else H
            cls_eff = join_static(pc, classes.get(var, L))
            verdict = "ok" if cls_eff <= need else "REJECTED"
            if verdict == "REJECTED":
                ok = False
            sinkname = "LOW" if need == L else "HIGH"
            print(f"  {comment:<48} {verdict} (flow {NAME[cls_eff]} -> {sinkname} sink)")
    print(f"  static verdict: {'SAFE' if ok else 'UNSAFE'} (proved for all inputs)")
    return ok


def dynamic_run(ir):
    print()
    print("DYNAMIC (per-variable taint, branch-condition taint, no PC carry):")
    taint = {}
    branch_taint = 0
    ok = True
    for op, dst, a, comment in ir:
        if op == "const":
            taint[dst] = a
            print(f"  {comment:<48} taint({dst})={NAME[a]}")
        elif op == "binop":
            taint[dst] = max(taint.get(a, L), branch_taint)
            print(f"  {comment:<48} taint({dst})={NAME[taint[dst]]}")
        elif op == "declassify":
            taint[dst] = a
            print(f"  {comment:<44} taint({dst})={NAME[a]}")
        elif op == "branch":
            branch_taint = max(branch_taint, taint.get(a, L))
            print(f"  {comment:<48} cond taint={NAME[branch_taint]} (not carried)")
        elif op == "label":
            branch_taint = 0 if a == "ENDIF" else branch_taint
            print(f"  {comment:<48} (labels ignored)")
        elif op == "sink":
            sink, var = dst, a
            need = L if sink in ("LOG", "NET") else H
            t = taint.get(var, L)
            verdict = "ok" if t <= need else "REJECTED"
            if verdict == "REJECTED":
                ok = False
            print(f"  {comment:<48} {verdict} (taint {NAME[t]})")
    print(f"  dynamic verdict: {'CLEAN' if ok else 'VIOLATION seen'}"
          f" - but the implicit leak executed undetected")
    return ok


s = static_check(IR)
d = dynamic_run(IR)
print()
print(f"static verdict={s} (UNSAFE), dynamic trip on log(pw)={not d}:")
print("the static checker proves the program unsafe BEFORE it runs and")
print("catches the branch-carried leak; the dynamic tracker only trips")
print("on the explicit log(pw) and waves the implicit leak through.")
```

```text
STATIC (Denning lattice + PC label):
  pw := read_password()   [source, H]              class(pw)=H
  user := read_username() [source, L]              class(user)=L
  hash := H(pw)  [derived from H]                  class(hash)=H
  declassify(hash -> L) [audited declass]      class(hash)=L (audited)
  log(hash)        [ok: hash now L]                ok (flow L -> LOW sink)
  log(pw)          [VIOLATION: H into LOG sink]    REJECTED (flow H -> LOW sink)
  if pw != 0:      [pc becomes H]                  pc=H
    flag := 1     [implicit leak: L store under H-pc] class(flag)=H
  endif          [pc back to L]                    pc=L
  send(flag)      [flag leaked the secret bit]     REJECTED (flow H -> LOW sink)
  static verdict: UNSAFE (proved for all inputs)

DYNAMIC (per-variable taint, branch-condition taint, no PC carry):
  pw := read_password()   [source, H]              taint(pw)=H
  user := read_username() [source, L]              taint(user)=L
  hash := H(pw)  [derived from H]                  taint(hash)=H
  declassify(hash -> L) [audited declass]      taint(hash)=L
  log(hash)        [ok: hash now L]                ok (taint L)
  log(pw)          [VIOLATION: H into LOG sink]    REJECTED (taint H)
  if pw != 0:      [pc becomes H]                  cond taint=H (not carried)
    flag := 1     [implicit leak: L store under H-pc] taint(flag)=L
  endif          [pc back to L]                    (labels ignored)
  send(flag)      [flag leaked the secret bit]     ok (taint L)
  dynamic verdict: VIOLATION seen - but the implicit leak executed undetected

static verdict=False (UNSAFE), dynamic trip on log(pw)=True:
the static checker proves the program unsafe BEFORE it runs and
catches the branch-carried leak; the dynamic tracker only trips
on the explicit log(pw) and waves the implicit leak through.
```

## Where the ideas ship

- **Databases and query engines**: column-level lineage plus label
  propagation (see [data lineage](../../dbms/advanced/data-lineage-provenance.md))
  is Denning's model in analytics clothing.
- **Browsers**: post-Spectre, origin isolation plus site isolation are
  confinement answers to side-channel versions of the implicit-flow
  problem; work on Spectre-safe IFC in JS engines continues.
- **Kernels**: seccomp + namespace confinement
  ([seccomp](../../os/advanced/seccomp-bpf.md)) handle the "who can
  call" axis; IFC systems (Flume lineage) cover "where data went", and
  production designs usually layer both.
- **Android**: TaintDroid's findings drove platform-level permission
  scoping; the current battleground is SDK-level data resale, which is a
  declassification-policy problem, not a mechanism problem.

## Interview probes

- Why can a sound IFC system not also eliminate covert channels? State
  the argument and its consequences for side-channel-adjacent code.
- Design the PC-label rule for `if`/`while` and show the one-bit leak it
  prevents; then show a timing leak it still permits.
- Your tracker reports 30% of an app's instructions tainted (shadow-byte
  model). Name three engineering responses, each with its cost.
- Where must declassification sit in the Jif/Flume model, and why is
  "declassify on demand" an anti-pattern?

## References

1. Denning, "A lattice model of secure information flow", CACM 19(5),
   1976, [doi:10.1145/360051.360056](https://doi.org/10.1145/360051.360056)
   - the lattice formulation and the program-certification rules.
2. Enck, Gilbert, Han, TaintDroid team, "TaintDroid: an information-flow
   tracking system for realtime privacy monitoring on smartphones",
   OSDI 2010, [the paper](https://www.usenix.org/legacy/events/osdi10/tech/full_papers/Enck.pdf)
   - the system-wide dynamic tracking results and app-misuse findings.
3. Kemerlis, Portokalidis, Jee, Keromytis, "libdft: practical dynamic
   data flow tracking for commodity systems", VEE 2012,
   [doi:10.1145/2365864.2151042](https://dl.acm.org/doi/10.1145/2365864.2151042)
   (author-hosted follow-up: [libdft for the masses, ACSAC 2022](
   https://cs.brown.edu/people/vpk/papers/libdft.acsac22.pdf)) - the
   shadow-memory architecture and its measured overheads.
4. [Sandboxing (this repo)](./sandboxing.md) and
   [web security (this repo)](../web-security.md) - the confinement
   mechanisms that pair with IFC in deployed stacks.
