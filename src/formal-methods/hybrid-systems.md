# Hybrid Systems and Hybrid Automata

A thermostat switches a furnace on and off while the room's temperature rises
and falls continuously; a cruise controller switches between accelerating,
braking, and coasting while the car obeys Newtonian dynamics throughout.
Systems that combine **discrete mode changes** with **continuous physical
evolution** are hybrid systems, and the standard formal model for them is the
**hybrid automaton** (Alur, Courcoubetis, Henzinger, and Ho, 1993) — the
mathematical substrate of cyber-physical verification: automotive control,
avionics, medical devices, power electronics.

Hybrid automata break two assumptions this section's neighbors rely on. Unlike
the finite Kripke structures consumed by [model checking](model-checking.md),
the state space is uncountably infinite (real positions, velocities, clocks).
And the question is usually not program correctness but *can the system ever
reach an unsafe state?* — a question with a precise, partially negative answer.

Each section below keeps one running example — the bouncing ball — so the
formalism, the decidability boundaries, the SMT encoding, and the flowpipe
machinery can all be seen against the same two-line model.

## Flows, Guards, Jumps, Invariants

A hybrid automaton interleaves:

- **locations (modes)** — discrete states such as `CRUISE` or `BRAKE`, each
  carrying an invariant over continuous variables;
- **continuous variables** `x ∈ R^n` that evolve inside a mode according to the
  mode's *flow* — a differential equation or inclusion `x' = f(x)`;
- **guards** — predicates on `x` that enable a transition;
- **jumps (reset relations)** — the discrete update applied when a transition
  fires, e.g. `v := -c·v`;
- **initial conditions** — a starting mode plus a starting set of valuations.

An execution alternates *flowing* (continuous evolution inside a mode) and
*jumping* (a discrete transition). The transition may be **nondeterministic**:
any point in time that satisfies the guard may be chosen, and disturbances may
be modeled by differential inclusions (`x' ∈ f(x) + [-b, b]`).

```text
              one mode with continuous flow          jump across a guard
        ┌────────────────────────────────────┐   guard: x = 0 ∧ v < 0
        │  flow:  x' = v                     │   reset: v := -c·v
        │         v' = -g                    │ ◄──────────────────────┐
        │  invariant: x ≥ 0                  │                        │
        └────────────────────────────────────┘ ────────────────────────┘
             x(t) rises, falls (continuous)       instantaneous state update
```

The single-mode automaton above is the **bouncing ball**: `x` is height, `v`
velocity, gravity pulls `v' = -g` continuously, and the guard `x = 0 ∧ v < 0`
triggers the reset `v := -c·v` (restitution c = 0.8 below). It is the "hello
world" of the field precisely because it is tiny yet exhibits both flowing and
jumping — and one famous pathology (Zeno behavior) we return to in §7.

## Reachability: The Question Everything Reduces To

Safety verification asks: from the initial set, can any execution reach a state
where some bad predicate `x ∈ Bad` holds? Formally:

```text
Reach(init) = least set containing init, closed under
              (a) continuous flow within a mode, and (b) jumps across guards
safe  ⟺  Reach(init) ∩ Bad = ∅
```

For finite-state models this is graph search. For hybrid automata it is not:

- **General hybrid automata: undecidable.** Henzinger, Kopke, Puri, and Varaiya
  (1998) proved that even reachability for automata with quite restricted
  dynamics (piecewise-constant derivatives in two dimensions, plus a single
  two-slope variable) is undecidable. Intuition: continuous variables can
  encode the tape of a two-counter machine — one variable's fractional part
  stores a counter value, mode switches implement increment/decrement, and
  zero-tests become guards.
- **Decidable subclasses exist**, and they are exactly the classes tools
  support with completeness guarantees:

| Subclass | Dynamics | Decidability of reachability | Classic algorithm |
|---|---|---|---|
| Timed automata | clocks, `x' = 1` only | decidable (Alur–Dill 1994) | region/zone abstraction |
| Initialized rectangular | derivative range may change only via re-initialization | decidable | partition refinement |
| Constant-slope multi-mode (LHA) | `x' = a_i`, finite modes | semi-decidable (relative completeness) | conserv. abstractions |
| O-minimal systems | flows definable in o-minimal theories (e.g. polynomial+exp) | decidable, finite bisimulation | definable equivalence |
| General nonlinear `x' = f(x)` | arbitrary ODEs | undecidable | bounded/over-approx only |

The o-minimal case is worth pausing on: if all sets definable in the flow's
theory (polynomials, exponentials, but *not* sine) have finitely many Boolean
combinations, the "same abstract state" relation has finite index and the
infinite continuous system collapses to a finite bisimulation quotient.
Timed automata are the flagship special case: clock valuations partition into
finitely many *regions*, which is why UPPAAL can verify timing protocols
exhaustively.

## Bounded Reachability as SMT over the Reals

Drop completeness; ask a bounded question instead: *is there an execution of at
most k jumps and total time T reaching Bad?* Fix a time step τ and unroll:

```text
step i:   x_{i+1} = x_i + ∫[t_i, t_i+τ] f(x) dt      (flow constraint)
          inv(x_i) holds for all i                    (mode invariant)
          some j ≤ k with guard_j(x_{i_j})            (jump occurred)
claim:    Bad(x_k) is unreachable                     (negate → satisfiability)
```

Each unrolling is an SMT formula over nonlinear real arithmetic — polynomial
ODE constraints make it undecidable classically, which is where
**δ-decidability** (Gao, Avigad, Clarke) enters. dReal answers *δ-sat* queries:
if δ-satisfiable, an execution reaches the target within a perturbation of at
most δ > 0 per variable; if unsatisfiable, no perturbation below δ helps. The
solver does rigorous interval arithmetic and ICP (interval constraint
propagation) internally, so a "SAT with δ = 10⁻⁸" answer is a *proof with a
stated error bar*, not a floating-point guess — the pragmatic sweet spot for
nonlinear CPS, where bounded model checking of, e.g., a neural-network
controller in the loop becomes a δ-complete satisfiability query (general
machinery in [SAT/SMT solvers](sat-smt-solvers.md)).

The exists/forall shape matters for robustness: "no execution reaches Bad" is
an exists-query over the negation, while "no execution comes within ε of Bad"
is a forall over a neighborhood, and δ-decidability gives both a one-sided
guarantee. Designers pick δ from physical tolerances (sensor noise, actuator
quantization), turning an awkward real-arithmetic question into an engineering
parameter.

## Flowpipe Construction: Over-Approximating All Trajectories

The workhorse of *unbounded-ish* reachability for nonlinear systems is the
**flowpipe**: compute, for each mode, a sequence of sets `Ω_0, Ω_1, Ω_2, …`
such that every trajectory segment lies inside some `Ω_i`, then intersect with
guards to obtain jump successors, and repeat.

```text
          v
          │      Ω3                bad set B
          │     ╱───╮                   ▓▓▓
          │    Ω2 ─╮ ╲                ▓▓▓
          │   ╱──╮ ╲ ╲              ▓▓▓   ← Ω4 ∩ B = ∅ ⇒ this jump
          │  Ω1 ╲ ╲ ╲ ╲           ▓▓▓        cannot happen (proved)
          │ ╱──╮ ╲ ╲ ╲ ╲        ▓▓▓
          └────────────────────────────── x
            each Ω_i covers dt of continuous time,
            with guaranteed error margin (bloated boxes)
```

The art is the *shape* of `Ω_i` and the error bound:

- **Interval boxes** (bloating): integrate `x' = f(x)` numerically, then inflate
  by a rigorous Lipschitz-based margin `±L·dt`. Cheap, coarse, compounds
  exponentially with horizon.
- **Polyhedra / support functions** (SpaceEx's STC scenario): for linear
  `x' = Ax`, the reachable set over `[0, T]` is exactly `e^{At}·X₀ + convex
  hull` terms; support functions represent these compactly in high dimension.
- **Taylor models** (Flow*): truncate the Taylor expansion of the flow and keep
  a rigorous remainder bound per variable — much tighter for nonlinear flows,
  which is why Flow* wins on the nonlinear ARCH benchmarks.

Guard intersection is just set intersection: `Ω_i ∩ Guard ≠ ∅` yields a jump
successor set, reset-transformed into the target mode's initial set. If any
flowpipe box (or its convex hull) touches the bad set, either a counterexample
exists or the abstraction was too loose — refine by shrinking `dt`, raising
Taylor order, or switching set representation. This is the same
counterexample-guided loop that [model checking](model-checking.md) uses, but
the refinement knobs are numerical.

## Case Study Mechanics: Adaptive Cruise Control

The ARCH competition's ACC benchmark distills platoon safety into two cars:
a lead car `x_l` and an ego car `x_e`, state `(D, v_l, v_e, γ)` with headway
`D = x_l - x_e`, and a controller mode-switching on `D` and relative speed:

| Mode | Ego acceleration law | Entered when |
|---|---|---|
| ACC | `a = clamp(k1·(D - D_safe) - k2·(v_e - v_l))` | `D > D_safe` |
| CP (speed control) | `a = k3·(v_set - v_e)` | `D` large, near set speed |
| CA (collision avoid.) | `a = -a_max` | `D ≤ D_safe` |

The safety property is `D > 0` at all times — no matter what the lead car does
within a modeled acceleration envelope `|γ| ≤ b`. Verification proceeds
exactly as §5 describes: start from an initial box of `(D, v, γ)` values,
flow under each mode's closed-loop ODE, over-approximate with polyhedra or
Taylor models, intersect with the mode-switch guards, and check every resulting
box against `D ≤ 0`. SpaceEx, Flow*, and HYLAA have all published results on
ACC-class models; platoons add per-vehicle copies plus communication-delay
variables, turning one flowpipe into a compositional one. The engineering
payoff: such a proof certifies the *controller* over an input envelope — a
deployment artifact that complements simulation and survives controller
refactoring as long as the model does.

## A Worked Simulation: the Bouncing Ball, Warts Included

Single-trajectory simulation is *not* verification, and the bouncing ball shows
why in a few lines. The script below simulates the hybrid automaton of §2 with
a fixed Euler step, detects the guard, applies the reset, and compares against
the closed-form (Zeno) settle time `t_fall + 2·v₁/(g·(1−c))`:

```python
"""1-D bouncing-ball hybrid automaton, simulated with fixed-step Euler:
flow x' = v, v' = -g inside one mode; guard x <= 0 and v < 0; reset v := -c*v,
x := 0. Compares against the closed-form Zeno settle time."""
G, C, DT = 9.81, 0.80, 0.01
HORIZON = 700                                  # 7 s horizon, fixed-step Euler

x, v, t = 1.0, 0.0, 0.0
events, guard_lag = [], 0.0
for _ in range(HORIZON):
    x += v * DT
    v -= G * DT
    t += DT                                    # one Euler step of the flow
    if x <= 0.0 and v < 0.0:                   # guard: at the floor, falling
        guard_lag = max(guard_lag, -x)
        events.append((t, v, -C * v))          # (impact time, v_before, v_after)
        v, x = -C * v, 0.0                     # reset relation

rows = []
for i, (t_imp, vb, va) in enumerate(events):
    seg = t_imp if i == 0 else t_imp - events[i - 1][0]
    box = (min(va, vb) - G * DT / 2, max(va, vb) + G * DT / 2)
    rows.append((i + 1, t_imp, seg, vb, va, box))

print("impact  t_euler  seg_dur  v_before  v_after   flowpipe v-box")
for r in rows[:4]:
    print(f"  #{r[0]:<4d} {r[1]:7.3f}  {r[2]:6.3f}  {r[3]:8.3f}  {r[4]:7.3f}"
          f"   [{r[5][0]:6.3f},{r[5][1]:6.3f}]")
v1 = C * (2 * G * 1.0) ** 0.5
settle = (2 * 1.0 / G) ** 0.5 + 2 * v1 / (G * (1 - C))
spurious = sum(1 for e in events if e[0] > settle)
print(f"bounces in {HORIZON * DT:.0f} s horizon : {len(events)}")
print(f"analytic Zeno settle time : {settle:.2f} s"
      "  (t_fall + 2*v1/(g*(1-c)))")
print(f"spurious post-settle bounces (numerical limit cycle): {spurious}")
print(f"max guard lag (Euler overshoot below x=0): {guard_lag:.4f} m")
```

```text
impact  t_euler  seg_dur  v_before  v_after   flowpipe v-box
  #1      0.460   0.460    -4.513    3.610   [-4.562, 3.659]
  #2      1.210   0.750    -3.747    2.998   [-3.796, 3.047]
  #3      1.840   0.630    -3.182    2.546   [-3.231, 2.595]
  #4      2.370   0.530    -2.653    2.123   [-2.702, 2.172]
bounces in 7 s horizon : 26
analytic Zeno settle time : 4.06 s  (t_fall + 2*v1/(g*(1-c)))
spurious post-settle bounces (numerical limit cycle): 18
max guard lag (Euler overshoot below x=0): 0.0272 m
```

Three field lessons hide in this output:

1. **Guard lag.** The ball crosses `x = 0` between steps, but a step-wise guard
   can only fire *at* a step, so impact #2 arrives with speed 3.747 m/s rather
   than the ideal 3.61 — the extra 0.137 m/s is pure detection delay, the
   `0.0272 m` overshoot below the floor. Production tools interpolate the
   crossing or shrink steps adaptively.
2. **A spurious limit cycle.** Physically the ball is at rest after 4.06 s
   (impacts accumulate Zeno-fast), yet the simulation reports 18 more bounces
   up to 7 s. The overshoot clamp `x := 0` injects back the potential energy
   the ball "lost" below the floor, and the discretized system reaches a false
   periodic orbit instead of the Zeno fixed point. A tester trusting this
   simulation would conclude the ball never rests; a flowpipe tool bounding
   each segment with a rigorous margin would prove rest.
3. **Flowpipe boxes are conservative by construction.** The v-boxes in the
   table add a `±g·dt/2` margin per segment. They are guaranteed to contain
   *every* trajectory consistent with the model, including the exact one —
   which is the whole point: over-approximation errs on the side of safety,
   simulation errs on the side of whatever happened once.

## Tools at a Glance

| Tool | Dynamics | Set representation | Notable for |
|---|---|---|---|
| SpaceEx | linear / affine | support functions, polyhedra | STC & LGG scenarios; industrial-scale models |
| Flow* | nonlinear ODEs | Taylor models | tight nonlinear reachability; ARCH benchmarks |
| HYLAA | linear | orthogonal polytopes (LGG) | fast projection-based reachability |
| dReal | nonlinear, SMT-based | δ-complete constraint solving | bounded exists/forall queries, NN controllers |
| UPPAAL | timed automata | zones | protocol/timing verification |

The ARCH serial competition publishes yearly head-to-head reachability results
on ACC, platoon, and power-electronics models — the de facto benchmark ladder
of the field.

## References

1. R. Alur, C. Courcoubetis, T. A. Henzinger, P.-H. Ho, "Hybrid automata: An
   algorithmic approach to the specification and verification of hybrid
   systems," *Hybrid Systems*, LNCS 1066, 1993.
   [DOI: 10.1007/3-540-57318-6_30](https://doi.org/10.1007/3-540-57318-6_30)
2. T. A. Henzinger, P. W. Kopke, A. Puri, P. Varaiya, "What's decidable about
   hybrid automata?" *J. Computer and System Sciences* 57(1):94–124, 1998.
   [DOI: 10.1006/jcss.1998.1581](https://doi.org/10.1006/jcss.1998.1581)
3. R. Alur, D. L. Dill, "A theory of timed automata," *Theoretical Computer
   Science* 126(2):183–235, 1994.
   [DOI: 10.1016/0304-3975(94)90010-8](https://doi.org/10.1016/0304-3975(94)90010-8)
4. S. Gao, J. Avigad, E. M. Clarke, "Delta-decidability over the reals,"
   *LICS 2012*. [DOI: 10.1109/LICS.2012.41](https://doi.org/10.1109/LICS.2012.41)
5. G. Frehse et al., "SpaceEx: Scalable verification of hybrid systems,"
   *CAV 2011*, LNCS 6806.
   [DOI: 10.1007/978-3-642-22110-1_30](https://doi.org/10.1007/978-3-642-22110-1_30)
6. Tool pages: [Flow*](https://flowstar.org/) and
   [dReal](https://dreal.github.io/) (both probed live; the SpaceEx site was
   unreachable at write time, so the CAV'11 paper above is the canonical link).
