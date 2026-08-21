# The eBPF Verifier

## Why a Verifier Exists

Unlike a kernel module, an eBPF program is loaded into the kernel from
untrusted userspace. The kernel therefore has to prove, *before* it allows the
JIT to emit any native code, that the program cannot crash the system, take
unbounded time, leak kernel pointers to userspace, or read/write memory it is
not entitled to touch. That proof procedure is the eBPF verifier, implemented
in `kernel/bpf/verifier.c` (~40k lines as of 6.x). It is the single most
important reason eBPF can be safely exposed to non-root users on production
systems.

The verifier is a *static* analysis: it never executes the program. It walks
every reachable instruction with an abstract interpretation over the register
file, producing a proof of safety. If the proof fails, `bpf(BPF_PROG_LOAD)`
returns `-EACCES` (or `-EINVAL`) and the kernel keeps a textual log that the
loader can read with `BPF_LOG_LEVEL`.

## The Two Verification Passes

Loading a program goes through two distinct passes, each with its own
responsibilities:

```
   .bpf/.o (BPF bytecode)              userspace loader
        |
        |  bpf(BPF_PROG_LOAD, attr)
        v
+-------------------------+
| Pass 0: control-flow    |   add_subprog(), find_subprog_endpoints()
| graph check.            |   - detect subprograms (BPF-to-BPF calls)
|                         |   - check_cfg()  builds a DFS over insns[]
|                         |   - rejects unreachable code
|                         |   - rejects infinite loops (pre-5.3)
+-------------------------+
        |
        v
+-------------------------+
| Pass 1: abstract        |   do_check()  (recursive / state-stacked)
| interpretation.         |   - per-register bpf_reg_state
|                         |   - per-instruction stack type/bounds
|                         |   - path pruning via register equivalence
|                         |   - helper call whitelisting & arg checks
+-------------------------+
        |
        v
   bpf_int_jit_compile()      (per-arch, e.g. x86 JIT)
        |
        v
   program live in kernel
```

### Pass 0 — Control-flow graph check

`check_cfg()` (kernel/bpf/verifier.c, `check_cfg`) performs a depth-first
search over the instruction array treating every `BPF_JMP`, `BPF_JMP_REG`,
`BPF_CALL` (with subprog targets), and `BPF_EXIT` as edges. It enforces:

- The first instruction must not be a jump target with a backwards edge
  (loops are forbidden pre-5.3 unless a back-edge is provably bounded).
- The instruction stream is well-formed — no jumps land in the middle of a
  16-bit BPF instruction.
- No unreachable instructions: every instruction must be on a path from the
  entry block.
- Every `BPF_EXIT` in a main program returns from the main entry, and every
  `BPF_EXIT` in a subprog returns from that subprog.

A CFG error is reported as a line in the verifier log with the offending
instruction index, e.g.:

```
0: (bf) r6 = r1
1: (05) goto pc+3         ; jump to 5
2: ...                    ; unreachable!
BPF_VERIFIER_ERR: unreachable insn 2
```

### Pass 1 — Path exploration with abstract interpretation

`do_check()` walks the CFG again, but this time carrying **register state**
across edges. For each instruction it simulates the effect on a virtual
machine with 11 registers (R0–R10) and a 512-byte stack, recording for every
live register a `struct bpf_reg_state`:

```c
/* include/linux/bpf_verifier.h, abridged */
enum bpf_reg_type {
    NOT_INIT     = 0,   /* never written this run */
    SCALAR_VALUE,       /* an integer, with tnum bounds */
    PTR_TO_CTX,         /* points to bpf program context */
    CONST_PTR_TO_MAP,   /* pointer to a map struct */
    PTR_TO_MAP_VALUE,   /* pointer into map value */
    PTR_TO_MAP_KEY,      /* pointer to map key for lookup */
    PTR_TO_STACK,       /* frame pointer or stack slot */
    PTR_TO_PACKET,      /* points into sk_buff data */
    PTR_TO_PACKET_META,
    PTR_TO_PACKET_END,  /* exactly data_end */
    PTR_TO_BTF_ID,      /* kernel struct via BTF */
    PTR_TO_MEM,         /* memory region of known size */
    PTR_TO_FUNC,        /* points to a BPF subprog */
    PTR_TO_MAP,         /* generic map ptr */
    ...
};

struct tnum {
    u64 value;   /* known bits */
    u64 mask;    /* 1 = unknown bit (symbolic) */
};

struct bpf_reg_state {
    enum bpf_reg_type type;
    struct tnum var_off;          /* for SCALAR_VALUE */
    s64 smin_value, smax_value;   /* signed bounds */
    u64 umin_value, umax_value;   /* unsigned bounds */
    s32 s32_min_value, s32_max_value;
    u32 u32_min_value, u32_max_value;
    struct bpf_reg_state *parent;  /* for path pruning */
    u32 id;                        /* for PTR_TO_MAP_VALUE_OR_NULL tracking */
    /* ... alu_limit, ref_obj_id, off, ... */
};
```

A `tnum` (tracked number) is the canonical two-component representation: a
"known bits" word and a "unknown bits" mask. If `value=0xffff` and `mask=0`,
the register is exactly 0xffff. If `value=0` and `mask=0xff`, the register is
"some byte, 0..255".

### Bounds propagation example

Consider the canonical packet access idiom that the verifier exists to make
safe:

```c
SEC("xdp")
int prog(struct xdp_md *ctx)
{
    void *data     = (void *)(long)ctx->data;
    void *data_end = (void *)(long)ctx->data_end;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)     /* bounds check */
        return XDP_ABORT;

    /* eth is now PTR_TO_PACKET with size >= sizeof(*eth) */
    if (eth->h_proto == htons(ETH_P_IP))
        return XDP_PASS;

    return XDP_DROP;
}
```

The verifier walks this code as follows:

```
after "data = ctx->data":     R6 = PTR_TO_PACKET,        off=0,  size=0
after "data_end = ctx->data_end": R7 = PTR_TO_PACKET_END

R1=data, R2=data_end after bpf_probe_read?  no — direct ptr.
"eth = data" (register alias):  R8 = R6  (PTR_TO_PACKET)

"if (eth+1 > data_end) goto abort":
   - compute eth+1 →  PTR_TO_PACKET with off=sizeof(struct ethhdr)
   - verifier compares against R7 (PTR_TO_PACKET_END)
   - on the fall-through branch: marks R6 with id=N, range ≥ 14
   - on the jump branch: no narrowing (will return)

"eth->h_proto == htons(ETH_P_IP)":
   - verifier sees R6 of type PTR_TO_PACKET, range ≥ 14
   - offsetof(struct ethhdr, h_proto) = 12, 12+2 = 14 ≤ 14   → SAFE
   - emit JIT-friendly load
```

The verifier emits a `-EACCES` if a developer forgets the bounds check:

```
0: (61) r1 = *(u32 *)(r1 +0)       ; r1 = ctx->data
1: (61) r2 = *(u32 *)(r1 +0)       ; r2 = *(u32*)ctx  -- but r1 is PTR_TO_CTX,
                                  ; only fields at fixed offsets are allowed
...
invalid bpf_context access off=0 size=4
```

## Register State Tracking

Every ALU/jump instruction that operates on a `SCALAR_VALUE` register must
*update the tnum bounds*. The verifier implements a small abstract algebra
for this in `adjust_reg_min_max_vals()`:

- `r += K` (immediate add): bounds shift by `K`. Signed min/max saturate at
  `S64_MIN`/`S64_MAX` to avoid overflow in the analysis itself.
- `r += r2`: the result has `smin = r.smin + r2.smin` (clamped), etc.
- `r &= 0xff`: forces `var_off` to `tnum_and(...)`, sets `umax = 0xff`,
  `umin = 0`.
- `r >>= K`: shifts bounds; if `K` is symbolic (variable shift), the verifier
  must produce conservative bounds (sometimes the verifier refuses the
  operation entirely).
- `r = (u8)r`: zero-extension collapses `var_off.mask` to the lower byte.

When the verifier cannot prove a tighter bound than "0 .. U64_MAX", it treats
the register as fully unknown, which makes any pointer arithmetic with that
register unsafe.

`tnum` arithmetic has a property critical for soundness: it is *monotonic* in
the lattice of refinement. The pruning step (below) relies on this: when two
paths merge, the verifier joins the two register states to a more general
(common) one, which is itself still sound.

## Path Pruning and the Instruction Budget

A naive walk over all paths explodes exponentially on real programs — even a
chain of `if/else` with depth 30 gives 2³⁰ paths. The verifier avoids this by
**pruning** at every join point. At a back-edge or after a conditional jump,
it compares the current `bpf_reg_state` of every live register against the
state cached from a previous visit to that instruction. If the new state is
*equivalent or more permissive* (every register's `tnum` is a superset, every
pointer's `id` and `off` match), the verifier stops walking that path — it
has already proven the downstream code safe.

This pruning is also why the verifier logs sometimes look bizarre: the log
only shows the *first* exploration of each instruction, even though dozens of
paths may have been tried internally.

To bound worst-case time, the kernel caps the number of explored states:

```
BPF_COMPLEXITY_LIMIT_INSNS   = 1 000 000   ; verified instructions
BPF_COMPLEXITY_LIMIT_STACK   = 8192         ; stack frame depth (bytes)
BPF_COMPLEXITY_LIMIT_STATES  = 100 000      ; total visited states
BPF_MAXINSN (legacy)         = 4096         ; pre-5.2 unpriv cap
```

Hitting any of those produces `-E2BIG` or `-EACCES`. The 1M-insn limit is the
key number for production BPF: it is the reason the verifier is
~deterministic in time on a modern CPU (a few ms to a few hundred ms
depending on program structure).

## Bounded Loops (5.3+)

Until 5.3 the verifier rejected every back-edge as a CFG violation, so BPF
programs had to be loop-free or unrolled by the compiler. Linux 5.3 added
**bounded loops**: a back-edge is permitted provided the verifier can prove,
statically, that the loop terminates in a known number of iterations.

The mechanism is a *symbolic* execution of the loop body using `tnum`. The
verifier walks the loop body once with a generic iteration count, then
*re-walks* the body, each time trying to refine the induction-variable bound.
After `BPF_MAX_LOOP_VERIFY_ITERATIONS` (4096 currently) refinements without
proof of termination it gives up.

A typical accepted pattern:

```c
SEC("xdp")
int sum_packet(struct xdp_md *ctx)
{
    void *d = (void *)(long)ctx->data;
    void *e = (void *)(long)ctx->data_end;
    int sum = 0;

    #pragma unroll                  /* unroll for guaranteed termination */
    for (int i = 0; i < 4; i++) {
        if (d + 4 > e) break;
        sum += *(int *)d;
        d += 4;
    }
    return sum;
}
```

Without `#pragma unroll` the verifier still accepts it in 5.3+, but logs the
extra passes:

```
processed 47 insns (limit 1000000) max_states_per_insn 0 total_states 3
...
mark_precise: precise_value_needed for r3 (off=0, size=4)
...
processed 132 insns ... max_states_per_insn 4 total_states 17
```

The verifier still rejects unbounded forms such as `while (data[0])` (where
the exit condition depends on memory) because it cannot statically prove a
decreasing induction variable.

## The Verifier Log

Every load attempt can capture a human-readable log. libbpf requests this
with `BPF_LOG_LEVEL` 1 (instructions + errors), 2 (instructions + states), or
3 (everything, including register-level). The log is a circular buffer; on
overflow the kernel truncates and appends `...` at the end.

```c
struct bpf_load_log {
    __u32  level;        /* requested log level  */
    char  *buf;          /* user-provided buffer */
    __u32  buf_size;     /* capacity             */
    __u32  actual_size;  /* bytes consumed (set by kernel) */
};
```

A minimal loader snippet:

```c
char log_buf[16 * 1024 * 1024];
LIBBPF_OPTS(bpf_prog_load_opts, opts,
    .log_buf = log_buf,
    .log_size = sizeof(log_buf),
    .log_level = 2,
);
int fd = bpf_prog_load(BPF_PROG_TYPE_KPROBE, "demo",
                       obj, "demo", license, &opts);
if (fd < 0)
    fprintf(stderr, "verifier:\n%s\n", log_buf);
```

Sample log lines you will see:

```
0: (bf) r6 = r1
1: (61) r2 = *(u32 *)(r6 +0)
2: (61) r3 = *(u32 *)(r6 +4)
3: (bf) r4 = r2
4: (0f) r4 += r3
5: (2d) if r4 > r2 goto pc+1   <true> r4 = scalar(smin=0,smax=U64_MAX)
                               <false> r4 = scalar(smin=0,smax=U64_MAX)  ; merged
6: ...
last_idx 6 first_idx 0
regs=4 stack=0 before 5: (0f) r4 += r3
7: (95) exit
processed 8 insns (limit 1000000) max_states_per_insn 0 total_states 1
```

Each line includes the disassembly of the BPF instruction followed by the
resulting register state on the *current* path. `last_idx`, `first_idx`,
`regs`, `stack`, `before` are emitted when a path is about to be pruned —
they let a reader reconstruct *why* the verifier decided the next state was
equivalent to a cached one.

## Common Rejection Reasons

| Reason | Typical log line | Fix |
|--------|------------------|-----|
| Uninitialised read | `BPF_[ALU] uses uninitialized r5` | Zero the slot or set it before the use. |
| Pointer arithmetic on ctx | `arithmetic on ctx pointer` | Use a copy: `r6 = r1; r6 += 4`. |
| Pointer leak to map | `invalid map access` / `cannot pass ptr to helper` | Don't store pointers in non-PTR_TO_MAP maps. |
| Out-of-bounds stack access | `invalid stack off=-5 size=8` | Stack slots are 8-byte aligned; align your struct. |
| Loop not provable | `infinite loop detected` | Add a monotonic induction variable; cap iterations. |
| Helper arg type mismatch | `helper call not allowed in this program type` | Check the program type, e.g. XDP can't call `bpf_get_current_pid_tgid`. |
| Return value wrong | `at exit: invalid type of r0 (SCALAR_VALUE), expected PTR_TO_CTX_OR_NULL` | Make sure `r0` holds the type the program type expects on `exit`. |
| Direct packet read without check | `invalid bpf_context access off=N size=M` | Insert the `data + sizeof(...) > data_end` guard. |
| Unaligned access | `misaligned stack access off=-8 size=4` | Use `__attribute__((packed))` carefully or align fields. |
| `CONFIG_BPF_JIT_ALWAYS_ON` mismatch | `-EINVAL` on load | Some helpers require JIT enabled (e.g. on certain arches). |
| Insufficient capabilities | `-EPERM` | `CAP_BPF`, `CAP_SYS_ADMIN`, `CAP_PERFMON`, `CAP_NET_ADMIN` as required. |

## Verifier Complexity Limits in Practice

The 1M-insn cap and 100k-state cap sound large, but a pathologically
branchy program can still hit them. A loop that produces a fresh state on
every iteration — typically because the verifier cannot prune — is the
common killer. Symptoms:

```
BPF_COMPLEXITY_LIMIT_STATES (100000) hit
verification time 4218 usec
```

Mitigations:

1. Use `bpf_for()` / `bpf_for_each()` macros from libbpf — they emit a
   standard shape the verifier recognises.
2. Replace per-element `bpf_map_update_elem()` inside the loop with a
   `bpf_loop()` helper and unroll inner work.
3. Pull the hot loop out into a separate subprogram and use a tail call to
   reset the verifier's budget between stages (each tail call gets a fresh
   budget).
4. Use `BPF_F-test_state` (when available) and `bpf_assert()` macros to
   communicate invariants explicitly.

## Userspace Validation vs the Kernel Verifier

A natural question: if the verifier is so good, why does the kernel not
trust a *userspace*-signed certificate and skip the slow walk? Two
approaches co-exist in the ecosystem:

1. **In-kernel static analysis** (the verifier you just read). Trusted by the
   kernel; runs at every load; result depends only on the bytecode and the
   running kernel's `BTF`/helpers.
2. **libbpf/bpf-loader pre-validation**. Before issuing the syscall, libbpf
   calls `bpf_object__probe_*()`, resolves BTF, rewrites CO-RE relocations,
   and runs a tiny in-process sanity check on instruction shape. This catches
   packaging bugs but cannot replace the verifier — there is no way for
   userspace to fake the proof.

There are two things that *do* bypass the verifier:

- **BPF_PROG_TYPE_STRUCT_OPS** programs: tiny trampolines generated by the
  kernel itself, not by userspace — there is nothing to verify, they are
  kernel code.
- **`BPF_F_BUILD_ID_CHECK`** (rare, research/ChromeOS) — programs whose ELF
  Build-ID matches a whitelisted binary; the JIT-compiled code is reused on
  subsequent loads (saving verifier time) but the program was still verified
  on first load.

`PRELOAD` mode (recent kernels) lets the verifier save its state to the
filesystem so subsequent loads of the same program are essentially free. See
`kernel/bpf/sysfs_btf.c` and `BPF_TOKEN_*` for the upstream work on delegated
loading in unprivileged containers.

## Worked Example: Diagnosing a Rejection

Here is a deliberately broken XDP program and how to read the verifier log.

```c
SEC("xdp")
int bad(struct xdp_md *ctx)
{
    void *d = (void *)(long)ctx->data;
    struct ethhdr *eth = d;
    return eth->h_proto;   /* no bounds check! */
}
```

Log (level 2):

```
0: (61) r1 = *(u32 *)(r1 +0)        ; R1=inv(id=0)  r1.w = ctx->data
1: (bf) r2 = r1                    ; R2=inv(id=0,smin=0,smax=umax=0xffffffff)
2: (61) r1 = *(u16 *)(r2 +12)      ; R1=pkt(off=12,r=0)
invalid bpf_context access off=12 size=2
```

The verifier sees `r2` is the `data` pointer but with `range = 0` (no proven
bound). The `r2 + 12` access exceeds the proven range and is rejected. Fix:
add the standard guard before the load.

## References

- Linux kernel docs, "BPF verifier" — https://docs.kernel.org/bpf/verifier.html
- Linux kernel docs, "BPF and XDP Reference Guide" — https://docs.kernel.org/networking/filter.html
- `kernel/bpf/verifier.c` source (Linux 6.x) — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/bpf/verifier.c
- `include/linux/bpf_verifier.h` — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/include/linux/bpf_verifier.h
- LWN: "Bounded loops in BPF programs" (Jonathan Corbet, 2019) — https://lwn.net/Articles/794190/
- LWN: "BPF, the streaming execution engine" — https://lwn.net/Articles/754605/
- LWN: "BPF: the future of performance analysis" (Jonathan Corbet) — https://lwn.net/Articles/741301/
- ebpf.io project overview — https://ebpf.io/
- libbpf: "BPF verifier log levels" — https://libbpf.readthedocs.io/en/latest/
- "On the Soundness of the eBPF Verifier" — Klingebiel et al., OOPSLA'24 — https://dl.acm.org/doi/10.1145/3649820
- "BPF: A verifier-internals walk-through" (Lize Punyadayita, 2022) — https://lwn.net/Articles/882514/
- Cilium project docs on verifier limits — https://docs.cilium.io/en/stable/bpf/
