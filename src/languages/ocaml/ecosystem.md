# OCaml Ecosystem and Tooling

## Overview

OCaml's industrial adoption (led by Jane Street, Ahrefs, Docker's desktop tooling, and others) rests on a mature toolchain: **opam** for packages, **dune** for builds, **Merlin/ocaml-lsp** for editor support, and a rich library ecosystem centered on **Base/Core** (standard library alternatives), **Lwt/Async** (concurrency), and modern web frameworks. See [OCaml Overview](./README.md) for the language itself.

## The Toolchain

| Tool | Role |
|---|---|
| **opam** | OCaml package manager: switches (compiler versions), local pins, publishing |
| **dune** | Build system (Jane Street's, open-sourced): fast, parallel, composable, monorepo-friendly |
| **Merlin** | Editor backend: type information, completion, jump-to-definition |
| **ocaml-lsp** | Language Server Protocol implementation for OCaml |
| **ocamlformat** | Automatic code formatter (opinionated, widely adopted) |
| **utop** | Enhanced interactive REPL |
| **odoc** | Documentation generator |

### opam

```bash
opam switch create 5.2.0        # create a compiler switch
opam install dune merlin        # install packages
opam pin add mylib .            # use a local dev copy
eval $(opam env)                # activate the switch environment
```

Switches isolate compiler versions and package sets per project — the standard way to manage multiple projects with different OCaml versions.

### dune

Builds are declared with **`dune` files** (s-expression syntax):

```lisp
; dune
(library
 (name mylib)
 (libraries base lwt))

(executable
 (name main)
 (libraries mylib))
```

Dune understands OCaml's toolchain precisely: it handles module dependencies, native vs bytecode targets, ppx rewriters, cross-compilation, and multi-context builds, and it's fast due to parallelism and incremental caching.

## Standard Libraries: Base and Core

Jane Street's libraries replace the compiler's standard library for production use:

| Library | Description |
|---|---|
| **Base** | Lightweight, dependency-minimal alternative to the stdlib; `Result`, `Option`, `List`/`Map`/`Set` with a uniform, total API |
| **Core** | The full industrial-strength library (Unix, I/O, threads, time); `Core_kernel` is the portable kernel |
| **Containers** | Community lightweight extension of the stdlib |

Design differences vs the stdlib: **total functions** (no partial exceptions where avoidable), consistent `Map`/`Set` module functors, and `Result.t`/`Option.t` as first-class types. Most Jane Street-style code uses `Base` for portability and `Core` when Unix/I-O are needed.

## Concurrency: Lwt vs Async

Both are **cooperative (coroutine) concurrency** libraries for I/O-bound work — the OCaml 5 runtime adds *parallelism* (domains), which is orthogonal.

| | **Lwt** | **Async** (Jane Street) |
|---|---|---|
| Core type | `'a Lwt.t` | `'a Deferred.t` |
| Style | Monadic; `let%lwt x = ...` / `let*` | Monadic; `let%bind` / `>>=` |
| Scheduling | Cooperative | Cooperative |
| Community | **The de facto standard** — most libraries (Cohttp, Dream, Opium) are built on it | Jane Street internal + ecosystem |
| Compatibility | Widely supported, ports to many backends | Tied to Jane Street stack |
| Choose when | Building libraries/web apps with broad compat | Working inside Jane Street-style infrastructure |

They are **mutually incompatible** (an `Lwt.t` can't be used where a `Deferred.t` is expected), so ecosystem packages often ship adapters (`foo-lwt` and `foo-async`). The community overwhelmingly standardizes on **Lwt**.

```ocaml
(* Lwt *)
let fetch url =
  let%lwt body = Cohttp_lwt_unix.Client.get (Uri.of_string url) in
  Lwt.return (Cohttp.Response.status body)

(* Async *)
let fetch url =
  let%bind resp = Cohttp_async.Client.get (Uri.of_string url) in
  return (Cohttp.Response.status resp)
```

## OCaml 5: Domains and Parallelism

OCaml 5 (2023) introduced a **multicore runtime** with **domains** (parallel execution on multiple cores) and the **effect handlers** foundation. Concurrency vs parallelism in OCaml:

- **Lwt/Async** — interleave I/O on one domain (concurrency, no parallelism).
- **Domains** — true parallel execution (`Domain.spawn`), plus **`Domainslib`** for parallel task pools.
- **Effect handlers** (OCaml 5) — the low-level mechanism that lets libraries implement schedulers; fiber-based parallelism via libraries like Eio.

**Eio** is the emerging modern I/O library built directly on OCaml 5 effect handlers — a design in the spirit of async/await in other languages, with structured concurrency.

## Web and Application Libraries

| Library | Role |
|---|---|
| **Dream** | Modern, simple web framework (Lwt-based), middleware, WebSockets |
| **Cohttp** | HTTP client/server library (Lwt and Async versions) |
| **Opium** | Lightweight web framework (Sinatra-like) |
| **Lwt_unix** | Async Unix I/O (sockets, files) |
| **Eio** | Effect-handler-based I/O for OCaml 5 |
| **ocaml-protoc / atdgen** | Serialization/IDL tools (JSON, protobuf) |
| **dune-release / opam-publish** | Releasing packages |

## Interview Questions

### Q: What is opam and how does it differ from pip/npm?

opam is OCaml's package manager with a distinctive feature: **switches** — isolated compiler + package environments. You create a switch per compiler version (or per project), and `opam install` builds packages from source against that compiler. This handles the "different projects, different compiler versions" problem that language package managers typically ignore. Local development uses `opam pin` to override published packages.

### Q: What is dune and why is it preferred for OCaml builds?

Dune is a build system that encodes OCaml's compilation rules precisely (module dependencies, ppx rewriters, native/bytecode targets, cross-compilation) rather than treating OCaml as a black box. It's fast (parallel, incremental), composable (multiple projects in one build), and requires no system dependencies beyond OCaml itself. Its `dune` files use a simple s-expression DSL.

### Q: Lwt vs Async — which would you choose and why?

For broad ecosystem compatibility, **Lwt**: the community standard, and most web/HTTP libraries (Dream, Cohttp, Opium) are built on it. **Async** is Jane Street's library — powerful and well-designed but less widely used outside Jane Street's stack. The two are incompatible (Lwt.t vs Deferred.t), so the choice determines which libraries you can use. Inside Jane Street-style infrastructure, Async; otherwise Lwt.

### Q: What is the difference between concurrency and parallelism in OCaml 5?

Concurrency (Lwt/Async) interleaves I/O-bound work on a single domain — you're never using multiple cores. Parallelism (OCaml 5 **domains**) runs computations on multiple cores simultaneously, with `Domain.spawn` and libraries like Domainslib. Effect handlers in OCaml 5 give libraries (like Eio) the primitives to build structured, fiber-based schedulers that combine both.

### Q: What are Base and Core?

Jane Street's standard-library alternatives. **Base** is the lightweight, portable kernel (types, containers, total functions, `Result`/`Option` idioms). **Core** is the full library adding Unix, I/O, time, and threads (`Core_kernel` is its portable subset). They're used because the compiler stdlib is missing useful pieces, has non-tail-recursive functions in places, and defaults to exceptions where a total function is safer.

## References

- OCaml official site — https://ocaml.org/
- opam documentation — https://opam.ocaml.org/doc/
- Dune build system — https://dune.build/
- Jane Street open source (Base, Core, Async) — https://opensource.jane.com/
- Lwt — https://github.com/ocsigen/lwt
- Dream web framework — https://aantron.github.io/dream/
- OCaml 5 multicore blog (ocaml.org) — https://ocaml.org/docs/multicore

## Related Topics

- [OCaml Overview](./README.md) — the language, types, modules
- [OCaml Interview Questions](./interview-questions.md) — language-level Q&A
- [Rust Async](../../languages/rust/async.md) — comparing async models
- [Go Channels](../../languages/go/channels.md) — another concurrency model
- [Concurrency](../../concurrency/overview.md) — general async/await concepts
