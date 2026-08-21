# Erlang/OTP — The BEAM VM, Actor Model, and Behaviors

## Overview

Erlang was built at Ericsson in the late 1980s for telecom switches — systems that must run continuously for decades, tolerate hardware failures, and be upgraded without downtime. The language and its runtime, the **BEAM VM**, encode three properties directly:

- **Concurrency** via isolated processes that share no memory.
- **Fault tolerance** via supervision trees and "let it crash" semantics.
- **Hot code loading** as a first-class runtime feature.

OTP (Open Telecom Platform) is the middleware layer: a set of design patterns called **behaviors** (`gen_server`, `gen_statem`, `supervisor`, `application`) and libraries that codify decades of operational experience.

## The BEAM VM

BEAM is a register-based virtual machine that executes BEAM bytecode compiled from Erlang (or Elixir, Gleam, etc.). Its design centers on cheap processes:

- Each process has its own heap and stack; no shared memory means no data races, no locks, and no cache-line contention between processes.
- Process spawning is on the order of a microsecond; millions of processes can coexist on one VM (the default `max_processes` is 268,435,455, but practical limits are RAM-driven).
- The scheduler is a **preemptive, reduction-counting** one: each process runs until it consumes a budget of ~2000 reductions, then yields. A reduction is roughly a function application. This guarantees fair scheduling and bounds tail-call latency.
- Schedulers run one per CPU core (by default), and each has a run queue. Work stealing balances queues across schedulers.

```
+--------------------+   process spawn   +----------------------+
|     erlang code    | ----------------> |  BEAM process (PID)  |
+--------------------+                   |   - own heap         |
        |  compile                       |   - own mailbox      |
        v                                |   - own stack        |
+--------------------+                   +----------------------+
|   BEAM bytecode    |                              |
+--------------------+                              |  send message
        |                                           v
        v                                +----------------------+
+--------------------+  reduction        |  mailbox            |
|    BEAM scheduler  |  yield /          +----------------------+
|  (1 per CPU core)  |  receive
+--------------------+
```

## Processes, mailboxes, and message passing

An Erlang process is created by `spawn/1`:

```erlang
Pid = spawn(fun() -> loop(0) end),
Pid ! {inc, self()},
receive
    {ok, V} -> io:format("got ~p~n", [V])
after 1000 -> io:format("timeout~n")
end.

loop(N) ->
    receive
        {inc, From} -> From ! {ok, N + 1}, loop(N + 1);
        stop -> ok
    end.
```

Key rules:

- `!` is asynchronous send. The message is appended to the recipient's mailbox (a FIFO, but `receive` pattern-matches out of order).
- `receive` walks the mailbox in order, taking the first message matching any of its clauses. Non-matching messages stay in the mailbox.
- Messages are *deep copied* when sent between processes (and serialized via the external term format when sent across nodes). This is what enables the "no shared memory" guarantee — but it's also why Erlang doesn't beat shared-memory threading for tight, hot loops.
- The process identifier (PID) is the only handle to a process. There is no shared pointer.

## The actor model

Erlang implements Hewitt's actor model: each actor has a private state, processes one message at a time, and can (a) send messages to other actors it knows about, (b) spawn new actors, (c) decide how to handle the next message. There is no shared state to coordinate; concurrent state changes are *serialized inside* each process. This is why Erlang is so good at fault-tolerant systems — if a process crashes, no other process has corrupted state.

The trade-off: every "shared" data structure must be modeled as a process. Cache-line contention is replaced by mailbox contention, which is *much* worse per-operation but scales *much* better across cores and nodes because there is no global lock.

## Let it crash

Erlang's most famous principle: don't write defensive code. If a function can't proceed sensibly — a key is missing, a TCP socket is closed, an invariant is violated — *let the process die*. The supervisor will restart it in a known-good state.

The reasoning:

- Defensive `try/catch` everywhere hides bugs and creates *inconsistent* state — half-applied mutations, dangling references, etc.
- A restarted process returns to a clean initial state. Recovery is O(1) — restart, not rollback.
- Crash reports are logged with the failure context, making post-mortem debugging tractable.

The supervisor restart strategy decides how aggressively to restart. `one_for_one` restarts only the crashed child; `one_for_all` restarts all siblings; `rest_for_one` restarts the crashed child and everything started after it.

## Supervision trees

A supervisor is itself a process that owns child processes (workers or other supervisors). The tree of supervisors is the application's fault-tolerance backbone:

```
                  [application master]
                          |
                  [supervisor (one_for_one)]
              /            |             \
        [gen_server]  [gen_server]  [supervisor (one_for_all)]
                                         /        \
                                  [gen_server]  [gen_server]
```

If a leaf worker crashes, its parent supervisor sees the `{'EXIT', Pid, Reason}` signal and decides what to do based on its `ChildSpec`. If the supervisor itself crashes (e.g., max restart intensity exceeded), it exits and *its* parent gets the signal — failures propagate up the tree, isolating blast radius.

The `ChildSpec` records the restart policy (`permanent`, `temporary`, `transient`), the shutdown timeout, and the start function (`{M, F, A}`). The supervisor also tracks restart frequency: if a child restarts more than `MaxR` times in `MaxT` seconds, the supervisor itself terminates with reason `reached_max_restart_intensity`.

## OTP behaviors

A **behavior** is an OTP abstraction that codifies a concurrency pattern. The behavior module (`gen_server`) supplies the boilerplate (message loop, code loading, tracing, debug logging); the callback module supplies the *domain logic* via well-defined callback functions.

### `gen_server`

The classic request/response server. The callback module exports `init/1`, `handle_call/3`, `handle_cast/2`, `handle_info/2`, `terminate/2`, and `code_change/3`:

```erlang
-module(counter).
-behaviour(gen_server).

-export([start_link/0, inc/1, get_count/1]).
-export([init/1, handle_call/3, handle_cast/2,
         handle_info/2, terminate/2, code_change/3]).

start_link() -> gen_server:start_link({local, ?MODULE}, ?MODULE, [], []).
inc(N)        -> gen_server:cast(?MODULE, {inc, N}).
get_count(_)  -> gen_server:call(?MODULE, get).

init([])                    -> {ok, 0}.
handle_call(get, _From, N)  -> {reply, N, N}.
handle_cast({inc, K}, N)    -> {noreply, N + K}.
handle_info(_Msg, N)        -> {noreply, N}.
terminate(_Reason, _N)      -> ok.
code_change(_Old, N, _Extra)-> {ok, N}.
```

`gen_server:call` is synchronous (with a timeout); `gen_server:cast` is fire-and-forget. The `Reply`/`noreply`/`stop` tuples the callback returns drive the behavior's loop — the callback never sees the receive.

### `gen_statem` (formerly `gen_fsm`)

`gen_fsm` is the legacy finite-state machine behavior; `gen_statem` is the modern replacement. A `gen_statem` callback handles events in the context of a current state. State can be data or a callback module itself; events are either `call`, `cast`, or `info`, plus timeouts (`state_timeout`).

```erlang
-module(door).
-behaviour(gen_statem).

-export([start_link/0, push/0]).
-export([init/1, callback_mode/0]).

start_link() -> gen_statem:start_link({local, ?MODULE}, ?MODULE, [], []).
push()        -> gen_statem:cast(?MODULE, push).

init([]) -> {ok, closed, []}.
callback_mode() -> state_functions.   % or handle_event_function

%% state functions (when callback_mode() = state_functions)
closed({call, From}, push, Data) -> {next_state, open, Data, [{reply, From, ok}]};
closed(EventType, Event, Data)   -> handle_event(EventType, Event, Data).
open(cast, push, Data)           -> {next_state, closed, Data};
open(EventType, Event, Data)     -> handle_event(EventType, Event, Data).

handle_event(_Type, _Event, _Data) -> keep_state_and_data.
```

`gen_statem`'s distinguishing features over `gen_fsm`: it supports *deferred events* (a state can postpone an event until a later state), *state enter calls* (`{next_state, S, D, [{next_event, internal, Action}]}`), and *time actions* (`{timeout, Ms, Msg}` / `state_timeout`).

### `supervisor`

A supervisor's callback returns `{ok, {SupFlags, [ChildSpec]}}`:

```erlang
-module(my_sup).
-behaviour(supervisor).

-export([start_link/0, init/1]).

start_link() -> supervisor:start_link({local, ?MODULE}, ?MODULE, []).

init([]) ->
    SupFlags = #{strategy => one_for_one,
                 intensity => 5,
                 period => 60},
    ChildSpecs = [#{id => counter,
                    start => {counter, start_link, []},
                    restart => permanent,
                    shutdown => 5000,
                    type => worker}],
    {ok, {SupFlags, ChildSpecs}}.
```

`intensity` and `period` set the max-restart window. `type` can be `worker` or `supervisor` — the latter is how nested supervisors are declared.

### `application`

An application bundles a set of modules and supervisors with a start function. `application:start(my_app)` starts the root supervisor and brings the whole tree up. The `.app` file (or `my_app.app.src`) declares the modules, registered names, environment, and start module.

## Hot code loading

BEAM can load new module versions at runtime. When you `c(counter)` or `l(counter)` in the shell, BEAM keeps the old version around (for in-flight processes) until the next time the process makes a fully-qualified call into the module, at which point the old version's code is purged. Processes stuck in old code are killed.

OTP codifies this with `code_change/3` (gen_server) and `code_change/4` (gen_statem), letting a behavior migrate internal state from one version's representation to another during an upgrade. This is how Erlang systems are upgraded without stopping — a real, used-in-production feature, not a curiosity. An *appup* file (`my_app.appup`) describes the ordered sequence of `code_change` calls and any load/unload ordering required across multiple modules.

## Distribution

Erlang nodes connect via TCP using a custom protocol; the Erlang Port Mapper Daemon (EPMD) handles node discovery on a host. Once connected, `Pid ! Msg` works across nodes transparently; the message is encoded via the *external term format*. Distribution is built into the language, not a library.

The trade-off: cross-node `!` is slow (network round-trip), and `monitor`/`link` across nodes must account for node-down events. The `global` module registers names across a cluster; `pg2` / `pg` provide process groups.

## Common pitfalls

1. **Mailbox blow-up** — a `receive` that only matches some clauses leaves unmatched messages accumulating. Use selective receive sparingly and flush.
2. **`process_flag(trap_exit, true)` everywhere** — silently changes process semantics. Use it where you intend to trap exits, not preemptively.
3. **Forgetting `terminate/2`** — resources held by the process (sockets, file descriptors) should be released there.
4. **Crashing the supervisor** — `max_restarts` defaults are low; a child that crash-loops will kill the supervisor, which can cascade up.
5. **Confusing `cast` and `call`** — `cast` is fire-and-forget; using it for things that need confirmation loses guarantees silently.
6. **Treating processes as objects** — one process per "object" is often overkill; batch related state into one gen_server.

## Interview questions

1. **What is BEAM?**
   The register-based virtual machine that executes Erlang bytecode. It schedules processes preemptively via reduction counting.

2. **Why "let it crash"?**
   Defensive code creates inconsistent state. A restarted process returns to a known-good state with O(1) recovery, and the crash is logged for diagnosis.

3. **What is a supervision tree?**
   A tree of supervisors owning workers (or sub-supervisors). Each supervisor applies a restart strategy when a child exits, isolating failures to subtrees.

4. **What's the difference between `gen_server` and `gen_statem`?**
   `gen_server` is request/response-oriented with implicit state; `gen_statem` makes state transitions explicit, supports deferred events, and supersedes `gen_fsm`.

5. **How does hot code loading work?**
   BEAM loads the new version alongside the old. Processes switch on the next fully-qualified call. `code_change` callbacks let behaviors migrate state across versions.

## References

- [Erlang/OTP — Getting Started](https://www.erlang.org/docs/getting_started/intro)
- [Erlang Reference Manual — Processes](https://www.erlang.org/doc/reference_manual/processes.html)
- [Erlang Reference Manual — Code Loading](https://www.erlang.org/doc/reference_manual/code_loading.html)
- [OTP Design Principles — Behaviors](https://www.erlang.org/doc/design_principles/des_princ.html)
- [OTP Design Principles — Supervisors](https://www.erlang.org/doc/design_principles/sup_princ.html)
- [gen_server module documentation](https://www.erlang.org/doc/man/gen_server.html)
- [gen_statem module documentation](https://www.erlang.org/doc/man/gen_statem.html)
- [Learn You Some Erlang for Great Good!](https://learnyousomeerlang.com/)
- [Joe Armstrong — *Making Reliable Distributed Systems in the Erlang Style* (PhD thesis)](https://erlang.org/download/armstrong_thesis_2003.pdf)
- [Erlang Efficiency Guide — Processes](https://www.erlang.org/doc/efficiency_guide/processes.html)

## See also

- [Concurrency Overview](../../concurrency/overview.md)
- [Coroutines](../../concurrency/coroutines.md)
- [Work Stealing](../../concurrency/work-stealing.md)
