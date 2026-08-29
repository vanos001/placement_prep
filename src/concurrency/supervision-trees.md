# Supervision Trees: Fault Isolation as a Structure

The other concurrency pages here cover *communication*:
[actor-model-deep.md](./actor-model-deep.md) on mailbox semantics,
[csp-model.md](./csp-model.md) on channels. This page is the other half of the
actor-model pitch: what happens *after* something fails. A supervision tree
encodes recovery in the topology itself -- which processes get rebuilt when one
dies is decided by tree position and start order, not runtime analysis.
[erlang-otp.md](../languages/erlang/erlang-otp.md) surveys OTP's behaviors;
here we dissect the supervisor: strategies, restart intensity, child policies,
and what makes "let it crash" safe.

## The failure contract: one signal, one decision

When a process dies, an exit signal reaches every process linked to it. A
supervisor traps exits (`process_flag(trap_exit, true)`), so instead of dying
with its children it receives each death as `{'EXIT', Pid, Reason}` and answers
one question: *who do I rebuild, in what order?* If nobody handles the failure,
the tree unwinds to the application root -- deliberate, ordered termination
instead of a corrupted half-running system. Learn You Some Erlang derives this
from first principles: a hand-rolled `trap_exit` restart loop works for one
child but does not compose, hence OTP's `supervisor` behavior
([learnyousomeerlang.com/supervisors](https://learnyousomeerlang.com/supervisors)).

```text
                      [root supervisor: one_for_one]   intensity=2, period=10
                      |
        +-------------+----------------+
        |                              |
 [pool_sup: rest_for_one]       [api_sup: one_for_all]
        |                              |
   +----+------+                +------+------+
   |           |                |             |
[listener]  [pool]           [router]     [handler]
 transient  permanent        temporary   transient

  crash -> parent consults ITS OWN strategy -> rebuilds a set; if it
  exceeds its intensity it kills its children, exits with reason shutdown,
  and ITS parent runs the same procedure one level up
```

## Four strategies, one table of sibling sets

A supervisor holds children in *start order*. Each strategy maps {crashed
child} to {set of children to restart}:

| Strategy       | Restart set                              | Models                        |
|----------------|------------------------------------------|-------------------------------|
| `one_for_one`  | only the crashed child                   | independent siblings          |
| `rest_for_one` | crashed child + everything started after | pipeline stages that consume earlier state |
| `one_for_all`  | all children, in start order             | tightly coupled set; any death invalidates all |
| `simple_one_for_one` / DynamicSupervisor | one dynamically added child | tasks, per-connection workers |

The `rest_for_one` intuition: children started after `session` may hold
references to it, so they are rebuilt too; earlier children are untouched.

Naming caveat interviews love: `simple_one_for_one` still exists in Erlang/OTP
(all children are dynamically added instances of one start function), but
Elixir removed it in v1.6 -- the [changelog](https://github.com/elixir-lang/elixir/blob/v1.6/CHANGELOG.md)
says `DynamicSupervisor` "encapsulates the old `:simple_one_for_one` strategy
and APIs in a proper module" ([hexdocs DynamicSupervisor](https://hexdocs.pm/elixir/DynamicSupervisor.html)); vocabulary: `supervisor:start_child/2` vs `DynamicSupervisor.start_child/2`.

Restarting forever against a deterministic bug (bad config, malformed payload,
dead upstream) burns CPU and hides the incident. So every supervisor carries a
give-up rule: if **more than `intensity` restarts occur within `period`
seconds**, it terminates all children, then itself, with reason `shutdown` --
the decision moves one level up
([supervisor(3)](https://www.erlang.org/doc/man/supervisor.html)).

| Knob            | Erlang/OTP             | Elixir                     |
|-----------------|------------------------|----------------------------|
| max restarts    | `intensity`, default 1 | `max_restarts`, default 3  |
| window          | `period`, default 5 s  | `max_seconds`, default 5 s |
| child restart   | defaults `permanent`   | defaults `:permanent`      |
| worker shutdown | 5000 ms                | 5000 ms (`:infinity` if child is a supervisor, both) |

One restart per five seconds is strict -- production Erlang usually raises it
(the 5/60 example in [erlang-otp.md](../languages/erlang/erlang-otp.md)); after
escalation, the parent's strategy applies -- often restarting just the subtree root.

## Child policies: restart type, shutdown, significance

| Restart type | On normal exit | On abnormal exit | Typical use                 |
|--------------|----------------|------------------|-----------------------------|
| `permanent`  | restart        | restart          | always-needed core services |
| `transient`  | stay down      | restart          | workers that may legitimately finish |
| `temporary`  | stay down      | stay down        | throwaway tasks, cache warmers |

`shutdown` governs teardown: `brutal_kill`, or a timeout after which an
uncooperative child is killed. OTP 25+ and Elixir add *significant children*:
with `auto_shutdown => any_significant | all_significant`, a significant child
exiting *normally* shuts the supervisor itself down
([OTP Design Principles](https://www.erlang.org/doc/design_principles/sup_princ.html)).

## Why "let it crash" needs clean boundaries

Restart-to-`init` is O(1) recovery *only if* these hold:

1. **No shared mutable state.** Each process owns its heap; crashes cannot
   corrupt siblings (isolation argued in [actor-model-deep.md](./actor-model-deep.md)).
2. **Reconstructible state.** `init` must rebuild from an authoritative source
   (ETS, database, upstream sync); unjournaled in-flight work is lost.
3. **Message-loss semantics.** An Erlang restart is a *new* process with a
   *fresh mailbox*: in-flight messages are gone, sends to the dead pid succeed
   silently -- callers need timeouts/monitors and idempotent retries.
4. **Idempotent or externalized side effects**, so re-running the worker is safe.

Akka's docs sharpen point 3: a restarted Akka actor *keeps its mailbox* ("if
the actor is restarted, the same mailbox will be there"), but the message being
processed at failure time is not put back -- lost unless your code retries
([Akka: Supervision and Monitoring](https://doc.akka.io/libraries/akka-core/current/general/supervision.html)). CSP
channels have no built-in story at all -- Erlang/Akka reliability rests on
supervision, not messaging ([csp-model.md](./csp-model.md) makes the same point).

## The same structure elsewhere

**Akka.** The supervisor owns the strategy; four moves: Resume (keep state),
Restart (clear state, new instance), Stop, Escalate ("Escalate the failure,
thereby failing itself" -- intensity escalation made explicit). Restarting an
actor restarts all subordinates, mirroring OTP's subtree semantics
([Akka: Supervision and Monitoring](https://doc.akka.io/libraries/akka-core/current/general/supervision.html)).

**Kubernetes.** A liveness probe is the same idea with a coarse restart set:
the kubelet restarts the *container*, killing everything inside it, with no
sibling coordination and no child policies. Intensity survives as exponential
backoff -- delays of 10s, 20s, 40s, ... capped at 300 seconds, reset after 10
minutes without problems -- surfaced as `CrashLoopBackOff`
([pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/);
probe mechanics in [kubernetes.md](../backend/containers/kubernetes.md)). OTP restarts
a *process* in microseconds; k8s restarts a *container* in seconds -- liveness
supervises the supervision tree, an outer ring for unrecoverable failures.

## Simulator: restart algebra and escalation

A pure-stdlib model of a 3-child supervisor: inject crashes, derive the restart set per strategy, escalate when intensity (2 restarts / 10 ticks) is exceeded.

```python
"""Restart-strategy simulator: crashes, restart sets, intensity escalation."""

KIDS = ["auth", "session", "logger"]      # fixed start order (left to right)
INTENSITY, PERIOD = 2, 10                 # max restarts / window ticks

def restart_set(strategy, crashed):
    if strategy == "one_for_one":
        return [crashed]                          # just the victim
    if strategy == "one_for_all":
        return list(KIDS)                         # everyone, start order
    if strategy == "rest_for_one":
        return KIDS[KIDS.index(crashed):]         # victim + later siblings
    raise ValueError("unknown strategy: " + strategy)

def simulate(strategy, crashes):
    """Return trace lines for a crash schedule [(tick, child)]."""
    trace, window, escalated = [], [], False
    trace.append("scenario: strategy=%s crashes=%s" %
                 (strategy, ["%s@t%d" % (c, t) for t, c in crashes]))
    for tick, child in crashes:
        group = restart_set(strategy, child)
        trace.append("  t=%d  %s crashed; restart %s" %
                     (tick, child, ", ".join(group)))
        window.append(tick)    # one restart *operation* per crash event
        if len(window) > INTENSITY:
            escalated = True
            trace.append("  t=%d  intensity %d/%ds exceeded: supervisor "
                         "terminates %s and exits(shutdown); parent decides" %
                         (tick, INTENSITY, PERIOD, ", ".join(KIDS)))
            break
    if escalated:
        trace.append("  -> escalated at t=%d after %d restart operation(s)"
                     % (tick, len(window)))
    else:
        trace.append("  -> survived: %d restart operation(s), within intensity"
                     % len(window))
    return trace

def main():
    plans = [("rest_for_one", [(1, "session")]),       # pipeline repair
             ("one_for_one", [(1, "session"), (2, "auth"), (3, "auth")]),
             ("one_for_all", [(1, "logger")])]         # tightly coupled set
    print("\n\n".join("\n".join(simulate(s, c)) for s, c in plans))

if __name__ == "__main__":
    main()
```

Real output (`python3 restart_sim.py`):

```text
scenario: strategy=rest_for_one crashes=['session@t1']
  t=1  session crashed; restart session, logger
  -> survived: 1 restart operation(s), within intensity

scenario: strategy=one_for_one crashes=['session@t1', 'auth@t2', 'auth@t3']
  t=1  session crashed; restart session
  t=2  auth crashed; restart auth
  t=3  auth crashed; restart auth
  t=3  intensity 2/10s exceeded: supervisor terminates auth, session, logger and exits(shutdown); parent decides
  -> escalated at t=3 after 3 restart operation(s)

scenario: strategy=one_for_all crashes=['logger@t1']
  t=1  logger crashed; restart auth, session, logger
  -> survived: 1 restart operation(s), within intensity
```

Scenario 2 is the story: two restarts inside the window are absorbed; the third
trips intensity and the decision moves up a level -- isolation as structure.

## Supervision and release handling

The tree is also the unit of upgrade: an OTP release handler installs an
upgrade via per-application `appup` scripts, and supervisors run the
child-level steps (suspend, load new code, resume or restart per the script and
each child's restart type)
([Release Handling](https://www.erlang.org/doc/design_principles/release_handling.html)) -- a
restart after an upgrade starts the *new* module.

## Interview traps

- Defaults differ: Erlang gives up after 1 restart in 5 s, Elixir after 3 in
  5 s. Quote the wrong pair and follow-ups write themselves.
- `simple_one_for_one` (Erlang, still documented) vs `DynamicSupervisor`
  (Elixir 1.6+): know both names and the migration direction.
- `transient` restarts on abnormal exits only; under `one_for_all` one
  crash-restart drags healthy siblings down; escalation exits `shutdown`,
  which looks gracefully terminated to anything that ignores intensity.
- Restarted Erlang process: empty mailbox. Restarted Akka actor: same mailbox
  minus the in-flight message -- at-least-once needs caller retries in both.

## References

1. [Erlang/OTP Design Principles: Supervisors](https://www.erlang.org/doc/design_principles/sup_princ.html) -- strategies, intensity/period, significant children (OTP 29 docs, probed Aug 2026)
2. [supervisor(3) manual page](https://www.erlang.org/doc/man/supervisor.html) -- strategy semantics; `intensity` defaults to 1, `period` to 5; escalation reason
3. [Learn You Some Erlang: Supervisors? From Bad to Good](https://learnyousomeerlang.com/supervisors) -- trap_exit restarts and why OTP formalizes them
4. [Elixir Supervisor](https://hexdocs.pm/elixir/Supervisor.html) -- `max_restarts`/`max_seconds` defaults (3/5), child spec fields
5. [Elixir DynamicSupervisor](https://hexdocs.pm/elixir/DynamicSupervisor.html) -- dynamic children, `max_children`
6. [Elixir v1.6 changelog](https://github.com/elixir-lang/elixir/blob/v1.6/CHANGELOG.md) -- DynamicSupervisor replaces `:simple_one_for_one`
7. [Akka: Supervision and Monitoring](https://doc.akka.io/libraries/akka-core/current/general/supervision.html) -- Resume/Restart/Stop/Escalate, mailbox behavior on restart
8. [Kubernetes: Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) -- restart backoff 10s..300s cap, CrashLoopBackOff, 10-minute reset
9. [Erlang/OTP: Release Handling](https://www.erlang.org/doc/design_principles/release_handling.html) -- appup-driven upgrades through the supervision tree
