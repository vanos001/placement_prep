# Session Types

A session type is a **protocol written as a type**. It specifies that on a given channel you will send an `Int`, then receive a `String`, then offer a choice between two sub-protocols — all statically typed. The compiler enforces two invariants: (1) every message has the right type at the right position in the protocol; (2) the channel is used in the order specified, with no skipped steps. Combined with **linearity** (each channel used exactly once), session types give you protocol safety at compile time — a server that forgets to send a message, sends one twice, or sends the wrong type simply fails to compile.

Session types were introduced by Honda, Vasconcelos, and Kubo in 1998 for binary protocols and extended to multi-party protocols by Honda, Yoshida, and Carbone (POPL 2008). Production use is concentrated in Scribble (a protocol description language generating API stubs), in the OCaml `channels` and `mpst` libraries, and in research languages like SePi and the Rust `mpst` crates.

## The dual of a session type

Binary session types describe a **two-party protocol**. Every type has a **dual** — the type viewed from the other end of the channel. Send becomes receive, receive becomes send; the choice becomes offer, the offer becomes choice.

```
  !T . S       send a T, then continue with S       dual:  ?T . S̄
  ?T . S       receive a T, then continue with S     dual:  !T . S̄
  ⊕{ l₁:S₁,...,lₙ:Sₙ }   internal choice (we pick)   dual:  &{ l₁:S̄₁,...,lₙ:S̄ₙ }
  &{ l₁:S₁,...,lₙ:Sₙ }   external choice (peer picks) dual: ⊕{ l₁:S̄₁,...,lₙ:S̄ₙ }
  μX . S       recursive session                     dual:  μX . S̄  (X̄ = X)
  end          close the channel                     dual:  end
```

Duality is essential to type checking: when you create a channel `c` of type `S`, you get two ends `c⁺` and `c⁻` where one has type `S` and the other has type `S̄` (the dual). Each operation on `c⁺` of type `!T . S` corresponds to a receive of `T` followed by session `S̄` on the other end. The dual type-checks both sides simultaneously from a single session declaration.

```
            Buyer (c⁺ : S)                  Seller (c⁻ : S̄)
            ┌─────────────────────┐         ┌─────────────────────┐
            │ send T  over c⁺      │ ─────> │ recv T  over c⁻      │
            │ recv U  over c⁺      │ <───── │ send U  over c⁻      │
            │ select lᵢ over c⁺    │ ─────> │ offer l₁..lₙ over c⁻ │
            │ close   over c⁺      │ ─────> │ close   over c⁻      │
            └─────────────────────┘         └─────────────────────┘
                       (S and S̄ are duals — type-check one, both check)
```

## The choice and offer operators

The most expressive part of session types is the choice (`⊕`) and offer (`&`) pair:

```
  Server session:  μX . &{ Login: ?Cred . !Token . X,
                           Quit:  end }
  Client session:  μX . ⊕{ Login: !Cred . ?Token . X,
                           Quit:  end }
```

The server offers two branches; the client picks one. The `&` says "I am ready to handle either label, you choose." The `⊕` says "I will select one of these labels and then proceed."

Concretely, in OCaml with the `channels` library, the types are encoded via polymorphic variants:

```ocaml
(* Server: external choice on label *)
let rec server (c : [< `Login of ... | `Quit ] ... ) =
  match_recv c with
  | `Login c -> let cred, c = recv c in
                let c = send c (make_token cred) in
                server c
  | `Quit c -> close c

(* Client: internal choice *)
let login cred c =
  let c = select `Login c in
  let c = send c cred in
  let token, c = recv c in
  c
```

The type checker verifies that the labels the client can `select` match the labels the server `match_recv`s, and that the continuation types match on both ends.

## Recursive sessions

Real protocols loop: a chat client sends messages until logout; a TCP connection cycles through send/receive/ack. Session types express this via the **μ-binder**:

```
  μX . !Msg . ?Ack . X         -- send a Msg, get an Ack, repeat
```

The `μX` introduces a recursive variable; occurrences of `X` in the body unfold to the same session. Type-checking unfolds `μX . S` to `S[X := μX . S]` whenever the recursion is entered. The key soundness condition is **contractiveness**: the recursion must be **guarded** by a communication action (a `!`, `?`, `⊕`, or `&`). A non-contractive type like `μX . X` would unfold forever without communicating — it is rejected by the parser.

Most implementations hide the μ-binder behind an OCaml/Haskell `type` definition, so recursion looks like ordinary recursive types:

```ocaml
type 'a chat_server =
  [`Msg of string * 'a chat_server
  |`Quit ]
```

This is just sugar for `μX . &{ Msg: ?String . X, Quit: end }`.

## The linearity constraint

Session types are sound only if **each channel is used exactly once**. If you could write `send c x; send c y` (use `c` twice), the receiver's protocol would be confused — the second send would be interpreted as the second message in *its* protocol, but the line might have moved on. If you could write `send c x; ignore c`, the protocol would be stuck — the receiver blocks forever.

```
Linear typing rule for sessions:

  Γ, c : !T . S  ⊢  e : S            (c used once in e)
  ───────────────────────────────────────  (⊢ send)
  Γ  ⊢  (send c v) : ... 

  (with the continuation typed at S; the old c at !T . S is consumed)
```

This is why session-typed libraries require linear types — OCaml's `channels` uses phantom linear parameters, Rust's session libraries lean on Rust's affine ownership, Haskell's `sessions` uses Linear Haskell.

A practical concern: you often want to **branch** a session — fork two threads that each handle part of the protocol. This is modeled by **session decomposition**:

```
  If c : !T₁ . !T₂ . S, then
    c can be split into c₁ : !T₁ . end  and  c₂ : !T₂ . S
  (subject to channel implementation semantics)
```

The linear constraint is preserved: each piece is used exactly once.

## Multi-party session types (MPST)

Binary session types cover two-party protocols (client/server). Real protocols often have **more than two participants**: a payment protocol has buyer, seller, bank, and fraud-detection service. Honda, Yoshida, and Carbone (2008) generalized binary sessions to **multi-party session types (MPST)**.

The key innovation: a global type `G` describes the whole protocol from a god's-eye view; each role's local type `Lᵢ` is **projected** from `G`.

```
  Global type G:
    Buyer → Seller : Item
    Seller → Bank   : Invoice(Item)
    Bank   → Seller : OK | Fail
    Seller → Buyer  : Confirm | Reject

  Projection to Buyer (L_buyer):
    !Seller(Item). ?Seller(Confirm | Reject). end

  Projection to Seller (L_seller):
    ?Buyer(Item). !Bank(Invoice). ?Bank(OK | Fail).
       ⊕{ OK: !Buyer(Confirm). end,
          Fail: !Buyer(Reject). end }

  Projection to Bank (L_bank):
    ?Seller(Invoice). ⊕{ OK: !Seller(OK). end,
                         Fail: !Seller(Fail). end }
```

The projection is mechanical; given `G`, the compiler generates the local types. Each participant then type-checks against its local type only — but conformance to local types guarantees **the global protocol is respected**. This is the central theorem of MPST: **local type-checking implies global progress and safety**.

```
              ┌──────────────────────────────────────┐
              │         Global Type G                │
              │   Buyer -> Seller -> Bank -> Seller ->│
              │             Buyer                     │
              └──────────────────────────────────────┘
                  │            │            │
        project   │            │ project    │  project
        to Buyer   │           to Seller     │  to Bank
                  ▼            ▼            ▼
            ┌────────┐    ┌────────┐    ┌────────┐
            │L_buyer │    │L_seller│    │L_bank  │
            └────────┘    └────────┘    └────────┘
              (each party type-checks against its local type only)
```

Scribble (the protocol description language) makes this concrete. You write a `.scr` file with the global protocol, run the Scribble tool, and it generates API stubs in Java, Python, OCaml, Go, etc. Each stub is a state machine: the only methods you can call are the ones legal at the current state, and the return type encodes the next state.

## Asynchrony: "Asynchronous Session Logic"

Classic session types are **synchronous**: send and receive block until matched. Real systems are **asynchronous**: messages queue up; a sender can fire-and-forget. The line of work crystallized in "Asynchronous Session Logic" extends session types to a setting with **buffered channels**.

```
  Session types with queues:
    c : !T . S  means  "send a T; you may queue it; the queue then holds [T]
                       and the continuation is S"
    c : ?T . S  means  "you may receive only after the head of the queue is T;
                       the continuation is S"
```

The typing rules are subtler: you can send into a queue even if no one is reading, but receives must match the queue head. The dual is preserved. Asynchronous session types are the basis of real-world implementations (Go channels, Erlang processes, OCaml's `Lwt`-based channels), because no real network is synchronous.

A subtle consequence of asynchrony: **session fidelity is no longer just a typing property**; you need **liveness** arguments to guarantee that messages are actually delivered (otherwise you can have a type-correct program that deadlocks at runtime — the queue grows unboundedly, or a receive blocks forever). Most implementations punt on this: they check the typing and accept that liveness is a runtime/operational concern, enforced via timeouts and supervision.

## Production use

| System | Implementation style | Host language | Notes |
|--------|---------------------|----------------|-------|
| **Scribble** | Global protocol DSL → local API stubs | Multi-language | Used in finance and bioinformatics protocols |
| **OCaml `channels`** | Phantom-typed linear channels | OCaml | Lightweight; uses GADTs for state |
| **OCaml `mpst`** | MPST with role-indexed endpoints | OCaml | Binary and n-party; uses Multicore OCaml |
| **Rust `mpst` crates** | Affine + macros | Rust | Compiler-checked MPST; binary and n-party |
| **SePi** | Native language | SePi | Research; sessions integrated into the language |

The OCaml `channels` library is the cleanest example for study:

```ocaml
type (_, _) chan
val send  : 'a -> ([< `Send of 'a ] msg, 's) chan -> 's chan
val recv  : ([< `Recv of 'a ] msg, 's) chan -> 'a * 's chan
val close : ([ `End ] msg, _) chan -> unit
```

Each operation *consumes* the channel and produces a new one with the **next session type**. The type-level encoding uses polymorphic variants to represent labels, and the linear consumption is enforced by the type checker (you cannot reuse the old channel — its type is no longer compatible).

## Comparison to API contracts

Session types vs API contracts (OpenAPI, gRPC schema, Protobuf service definitions):

| Aspect | Session types | API contracts |
|--------|---------------|---------------|
| Scope | One conversation, multiple messages | Stateless request/response |
| Order | Statically enforced | Not enforced |
| State | Implicit in type | Implicit in server code |
| Verification | Compile-time type error | Runtime check |
| Tools | Scribble, OCaml channels | OpenAPI generators |

A typical REST API says `POST /order` accepts an `Order` and returns an `OrderResponse`. It does not say "you must first authenticate, then create a cart, then add items, then checkout." Session types say all of that in a single type. The cost: session types assume **stateful channels**, which REST explicitly rejects. The benefit: protocol errors are impossible at runtime.

For stateful protocols (TLS handshake, OAuth dance, payment flows, distributed commit), session types are a massive win. For stateless REST APIs, they are overhead. The trend in modern microservices is hybrid: REST for CRUD operations, but session-typed WebSocket/gRPC streams for the parts that need ordered stateful conversations.

## Conclusion

Session types bring protocol-level reasoning into the type system. They sit at the intersection of type theory (linear typing for channels) and concurrency theory (the π-calculus and its variants). The linearity constraint is the secret sauce: by forcing each channel to be used exactly once, the type system can guarantee that a well-typed program **cannot deadlock or communicate out of order** (a property called *session fidelity*).

For industry: session types are still mostly used in research and a few niche deployments (financial protocols via Scribble, verified concurrent libraries). The OCaml `channels` library and the Rust `mpst` crate are accessible entry points for learning. The trend is toward **multi-party** types with **asynchronous** semantics, because real protocols are multi-party and real networks are async — the more recent work on monitored session types, deadlock-freedom in MPST, and the integration with effect handlers (in Multicore OCaml and Koka) suggests the field is converging on a practical answer.

## References

- K. Honda, N. Yoshida, M. Carbone, *Multiparty Asynchronous Session Types* (POPL 2008) — https://dl.acm.org/doi/10.1145/1328438.1328472
- The Scribble project (protocol description language and tools) — http://www.scribble.org/
- OCaml `mpst` library (multi-party session types in OCaml) — https://github.com/ocaml-multicore/ocaml-mpst
- S. Gay, *Session Types publications index*, University of Glasgow — http://www.dcs.gla.ac.uk/~simon/publications/
- K. Honda, V. Vasconcelos, M. Kubo, *Language Primitives for Non-deterministic Concurrent Functions* (ICCL 1998), the original binary session types paper — https://dl.acm.org/doi/10.1109/ICCL.1998.687524
- L. Padovani, *Asynchronous Session Logic* and related work — http://www.di.unito.it/~padovani/Research.html
- D. Sangiorgi, D. Walker, *The Pi-Calculus: A Theory of Mobile Processes* (Cambridge University Press, 2001)
- N. Ng, V. Vasconcelos, *Sill: A Generative Spreadsheet API for Session Types* — http://www.di.fc.ul.pt/~vv/papers/sill/
