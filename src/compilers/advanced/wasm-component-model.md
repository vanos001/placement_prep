# WebAssembly Component Model

The WebAssembly Component Model is the post-MVP vision for Wasm: a typed, language-agnostic composition system where modules written in Rust, Go, Python, JavaScript, and C# call each other with no shared address space and no host-defined FFI. Where the 2017 Wasm MVP gave us a sandboxed, stack-based execution core, the Component Model (finalised in 2023, hitting 1.0 in wasmtime 18 / Wasmtime 24) gives us **interface types**, a **canonical ABI**, the concept of a **world**, and the **WASI Preview 2** system interface. This chapter covers the component spec, WIT (Wasm Interface Types), the canonical ABI, cross-language composition, and how this replaces the FFI/JSON-Library boundary of the 2010s.

## The Problem with the MVP

Wasm 1.0 (2017) gave us:

- A linear memory (`ArrayBuffer` of bytes).
- Imported and exported *functions* whose only types are `i32`, `i64`, `f32`, `f64`.
- Tables of function references.

That's it. No strings, no records, no variants, no lists, no resources. If you wanted to call a Rust function `fn greet(name: &str) -> String` from JavaScript, you had to:

1. Allocate `name` as UTF-8 bytes in the Wasm module's linear memory.
2. Pass `(ptr, len)` to the function.
3. The function would call `malloc` inside its own memory, write the result string, and return `(ptr, len)`.
4. JS reads the bytes back, decodes UTF-8, and frees the buffer.

This is the "shared linear memory" coupling. Every language has its own conventions for string layout, memory ownership, error handling. The glue code (`wasm-bindgen`, Emscripten's `cwrap`, AssemblyScript's `js_runtime`) is hundreds of lines per binding. There is no type-safe ABI; you pass `i32` pointers around and hope the host and guest agree.

The Component Model eliminates this glue.

## The Component Model

A **component** is a *higher-order* Wasm module. Instead of (or in addition to) the classic core module's linear-memory-based exports, a component exports typed *functions* with rich types: `string`, `record`, `variant`, `list`, `option`, `result`, `tuple`, `flags`, `enum`, `resource`. The component spec defines:

- **Component instances**: instantiations of components, with their own state.
- **Lifted/lowered values**: a typed value crossing the host/guest boundary through the canonical ABI.
- **Linking**: components can be *linked* — one component's exports become another's imports — with the runtime performing type-checked adapters.

```text
                ┌─────────────────────────────────────────┐
                │            Component instance           │
                │  ┌─────────────┐  ┌─────────────┐       │
                │  │ Core module │  │ Core module │       │
   (imported    │  │   (Rust)    │  │    (Go)     │       │  (exported
    funcs) ───► │  │  linear mem │  │  linear mem │       │  funcs)
                │  └─────────────┘  └─────────────┘       │   ──►
                │   ▲              ▲                       │
                │   │ canonical ABI │                       │
                │   │   lifts/lower │                       │
                └───┴──────────────┴───────────────────────┘
```

The component instance may wrap one or more core Wasm modules; the runtime handles the typed-ABI translation between the host's view and the core module's `i32`-pointer view.

## WIT (Wasm Interface Types)

WIT is the Interface Definition Language for components. A `.wit` file declares interfaces and types:

```wit
// greet.wit — a world describing a greeting service
package myorg:greet@1.0.0;

interface api {
    // A record type
    record person {
        name: string,
        age: u32,
    }

    // A variant — Rust-style enum with associated data
    variant greeting-result {
        ok(string),
        err(string),
    }

    // A function returning a result
    greet: func(p: person) -> greeting-result;
}

// A "world" is the top-level component type
world greeter {
    import logging: interface {
        log: func(level: u8, msg: string);
    }
    export api;
}
```

From this WIT, code generators (`wit-bindgen`) emit Rust traits, Go interfaces, C# classes, Python type stubs — and the runtime-generated *canonical ABI adapters* that turn high-level calls into the low-level `i32`/`i64` machine-level function calls.

## The Canonical ABI

The Canonical ABI is a fully-specified encoding for typed values into the memory model of core Wasm (and host-provided memory). For example:

| WIT type | Canonical ABI |
|---|---|
| `bool` | `i32` (0 or 1) |
| `u8`, `u16`, `u32` | `i32` |
| `u64` | `i64` |
| `string` | `(i32 ptr, i32 len)` into a memory, with the host's memory view |
| `list<T>` | `(i32 ptr, i32 len)` |
| `record { a: T1, b: T2 }` | flattened tuple of T1, T2 components, with `0` padding for alignment |
| `variant` | `(i32 discriminant, payload-with-max-alignment)` |
| `option<T>` | variant with discriminant `0` (none) or `1` (some) |
| `result<T, E>` | variant with discriminant `0` (ok) or `1` (err) |
| `resource` | opaque `i32` handle to a host-managed resource |

The ABI is *exactly specified* — every WIT type maps to one canonical encoding, and adapters generated by `wit-bindgen` are interoperable across languages. A Rust component and a Go component calling each other need not even know each other's source language; they only agree on the WIT.

The canonical ABI defines two directions:

- **Lifting**: take low-level (`i32`, `i64`) parameters received from a function call, construct a typed `value` (e.g., a `string`).
- **Lowering**: take a typed `value`, write its byte representation to memory, and produce the low-level parameters to pass.

Crucially, the component ABI handles memory ownership. The caller may pass a `string` either by borrowing it (caller retains ownership, callee reads) or by transferring it (caller gives up ownership, callee must free). The default is *borrow*: no copying is required for read-only data.

## The "World" Concept

A **world** is a WIT declaration of a complete component — what it imports and what it exports. The `world` is the *type* of the component, in the same sense that a function type is the type of a function. Worlds compose: if world A imports the interface B exports, you can *link* A and B into a single component.

```text
   World: app
   ─────────────────────────────────
   import: cli (env vars, args, stdin/stdout)
   import: http-types (fetch)
   import: mydb (a key-value store component)

   export: serve (fn handle_request(req: http-request) -> http-response)
```

A "world" is typically used as:

- The **target** for `wit-bindgen` — generates bindings for a specific language.
- The **linker** argument — the runtime walks the world's imports, resolves each against available components or host implementations, and instantiates.

In Fermyon Spin (a serverless Wasm platform), each application declares a world that imports `wasi:http` and `wasi:keyvalue`; Spin provides both, and the application exports a `handle-http-request` function. Deploying a Spin app is "build the component, link it, run it".

## WASI Preview 2

WASI Preview 1 (the "snapshot" interface shipped in 2019) exposed POSIX-like functionality (`fd_read`, `fd_write`, `path_open`) through host calls. It was a *file-descriptor*-centric API: every resource is an `i32` fd.

WASI Preview 2 ("WASI 0.2", released December 2023) is the *component-model* version of WASI. It replaces fd's with **typed resources**:

- `wasi:cli/environment` — environment variables, args, exit
- `wasi:io/streams` — `input-stream`, `output-stream` resources with `read`, `write`, `flush`, `cancel`
- `wasi:filesystem/types` — `descriptor` resource with `read-via-stream`, `write-via-stream`, `stat-at`
- `wasi:http/types` — `request`, `response`, `body` resources
- `wasi:clocks/monotonic-clock`, `wasi:clocks/wall-clock` — time
- `wasi:random/random` — cryptographic randomness

Resources are *handles* (opaque `i32`s in the canonical ABI) that the runtime garbage-collects; the host side may keep file descriptors, sockets, or whatever.

The architectural difference is significant: Preview 1 forces everything through the fd abstraction (treating HTTP as a stream of bytes via a TCP socket is awkward), while Preview 2 lets each interface expose its natural types. A Wasm component making an HTTP request in Preview 2:

```rust
// Spin (or any Preview 2 host) provides wasi:http/outgoing-handler
use wasi::http::outgoing_handler::handle;
use wasi::http::types::*;

let req = OutgoingRequest::new(Headers::new());
req.set_method(&Method::Get).unwrap();
req.set_scheme(Some(&Scheme::Https)).unwrap();
req.set_authority(Some("example.com")).unwrap();
let fut = handle(req, None).unwrap();
let resp = fut.get();
println!("status: {:?}", resp.status_code());
```

No TCP sockets, no manual HTTP parsing. The host implements the protocol; the guest sees a typed `request`/`response` resource.

## Cross-Language Composition

Because the Canonical ABI is universal, components in different languages can be composed without any of them being aware of the others' language. A canonical example: a Rust component exporting a `kv-store` interface, a Go component importing that interface and using it from a server, a Python component that does the same. The composition is:

```text
   .wasm (Rust)         .wasm (Go)          .wasm (Python)
   ──────────           ──────────          ─────────────
   exports kv:read      imports kv:read      imports kv:read
          kv:write              kv:write            kv:write
   uses its own          exposes HTTP         exposes Python
   linear memory         endpoint             bindings
```

The host (Wasmtime, jco, Spin) instantiates each component, links the Go and Python components' imports to the Rust component's exports, and produces a single component instance that handles HTTP requests using the Rust storage. The host performs no copy between the Go and Rust linear memories — the Canonical ABI adapters perform the byte-level conversion in the host, in a single buffer.

## Comparison to FFI

Traditional FFI (Foreign Function Interface) is what the Component Model replaces on the Wasm platform. Compare:

| Aspect | FFI (e.g., CPython calling C) | Component Model |
|---|---|---|
| Type system | C types: `int`, `char*`, `void*` | Rich: string, record, variant, resource, result |
| Memory | Shared address space; caller/callee share pointers | Per-component linear memory; adapters marshal |
| ABI | Platform-specific (SysV, Win64, ARM AAPCS) | One canonical ABI per type, all platforms |
| Errors | `errno`, return-code conventions | `result<T, E>` first-class type |
| Resource lifetime | Caller/callee manually manage; UAF common | Resource handles, runtime GC |
| Cross-language | Need per-pair bindings (CPython↔Rust, CPython↔Go, …) | One WIT → bindings per language; pairwise free |
| Sandboxing | None — FFI escape | Wasm sandbox applies to every component |
| Linker | Build-time / dlopen | Runtime composition via WIT imports/exports |

The killer feature is the *linear-memory isolation*. A traditional Python+C extension has the C code in the same address space as the Python interpreter — a buffer overflow in the C code corrupts the interpreter. The Component Model keeps each component in its own linear memory; the canonical ABI is the only thing that can cross the boundary, and the runtime validates every access.

## Wasmtime + WASI Preview 2

Wasmtime (Bytecode Alliance) is the canonical runtime for the Component Model. As of Wasmtime 18+ (mid-2024), Preview 2 is the default WASI. To run a component:

```bash
# Generate Rust bindings from a WIT file
$ wit-bindgen rust greet.wit --out-dir bindings

# Write the Rust implementation, then build to .wasm
$ cargo build --target wasm32-wasip2

# Run with wasmtime
$ wasmtime greet.wasm "Alice"
Hello, Alice!
```

The `wasm32-wasip2` target (Rust 1.78+) produces a `.wasm` component (not just a core module). To enable host-side WASI imports (filesystem, http), pass `--config` flags:

```bash
$ wasmtime --dir=. --env=API_KEY=... greet.wasm "Alice"
```

For HTTP-receiving components (those exporting `wasi:http/incoming-handler`), Wasmtime provides a `wasi-http` provider; you can run a Spin component directly:

```bash
$ wasmtime serve -S 0.0.0.0:8080 app.wasm
```

## Fermyon Spin

Spin is a serverless platform built on Wasmtime + the Component Model. A `spin.toml` describes a serverless app:

```toml
spin_manifest_version = "2"
name = "kv-demo"

[[component]]
id = "rust_kv"
source = "kv.wasm"
[component.key_value_stores]
store = "default"     # Spin provides this; the component imports wasi:keyvalue/store

[[trigger.http]]
route = "/api/..."
component = "rust_kv"
```

When Spin starts, it instantiates each component with its declared WASI imports (key-value, http, sqlite, llm) backed by Spin's runtime. On an HTTP request to `/api/...`, Spin calls the component's exported `handle-http-request` with a typed `Request` resource. The component reads from the key-value store; Spin routes the call to its Redis/SQLite backend. The component sees no TCP, no Redis protocol — only typed resources.

## Beyond Serverless: Plugin Architectures

The Component Model is increasingly used for *plugin* architectures in native applications. Examples:

- **Extism** — "make every app scriptable in Wasm." Provides an embeddable runtime for Go, Rust, Python, Ruby, JS host applications with Wasm plugins. A user can extend a Go program with a plugin written in any Wasm-targetable language, with the host exposing a WIT interface and the plugin implementing it.

- **Shopify Functions** — discount and checkout logic is shipped as Wasm components; Shopify's checkout calls them through the component ABI.

- **Deno / Node.js** — both now support loading Wasm components as ES modules through the standard module system.

## Common Pitfalls

1. **Confusing core Wasm modules with components.** A core module (the `.wasm` you get from `cargo build --target wasm32-unknown-unknown`) is *not* a component — it has no typed exports. To make it a component, you need `wasm-tools component new` (or build with `wasm32-wasip2`). The two are interoperable (a component can wrap a core module), but you cannot call a component's `string`-typed export from raw core-Wasm host code without an adapter.

2. **Assuming string passing is free.** The Canonical ABI's `borrow` mode is zero-copy for the data, but the *adapter* may still need to copy if the host's and guest's string representations differ (e.g., UTF-8 host vs UTF-16 guest). Use `borrow` (`&str`) instead of `string` (ownership transfer) wherever possible.

3. **Forgetting resource cleanup.** Resources (`resource` in WIT) are reference-counted and garbage-collected by the runtime, but you must call `.drop()` (or let it go out of scope in Rust) to free them. Leaks are possible — the runtime will eventually GC, but holdouts add up.

4. **Expecting Preview 1 modules to run under Preview 2 hosts.** There is an adapter module (`wasi_snapshot_preview1` component adapter) that lets Preview 1 modules run under Preview 2 hosts, but it's not perfect — some syscalls behave differently, especially around `poll` and async I/O. Plan migration: build for `wasm32-wasip2` directly.

5. **Mixing async and sync handlers.** A component can declare either a sync or async export (`async fn`). Wasmtime's async support is built on tokio; sync and async functions can't be mixed in the same component interface. Pick one.

6. **Not realising the Component Model is a *linker*, not just an ABI.** Linking is *explicit*: each world import must be satisfied by either another component's export or the host. The error messages when a component is missing a dependency are sometimes cryptic ("interface `wasi:cli/stdout` not found in linker"). Use `wasm-tools component link` or `wasmtime new --dir` to debug the linker state.

## References

- [WebAssembly Component Model specification](https://github.com/WebAssembly/component-model) — the canonical spec, including WIT and the Canonical ABI
- [WIT documentation](https://component-model.bytecodealliance.org/design/wit.html) — interface definition language
- [WASI Preview 2 specification](https://github.com/WebAssembly/WASI/blob/main/wasip2/README.md) — released December 2023
- [Wasmtime documentation](https://docs.wasmtime.dev/) — reference Component Model runtime
- [Bytecode Alliance](https://bytecodealliance.org/) — steward of the Wasm component ecosystem
- [Fermyon Spin](https://developer.fermyon.com/spin/) — serverless Wasm platform
- Luke Wagner, "[Typing WebAssembly: From Stacks to Types](https://github.com/WebAssembly/component-model/blob/main/design/mvp/Explainer.md)" — Component Model design explainer
- [wit-bindgen: bindings generator for WIT](https://github.com/bytecodealliance/wit-bindgen)
- [wasm-tools: component model CLI](https://github.com/bytecodealliance/wasm-tools)
- [Extism: The Plug-in Framework for WebAssembly](https://extism.org/)
- [Wasm 2023 Component Model milestone](https://github.com/WebAssembly/component-model/issues/200) — stabilisation tracking
- [Shopify Functions: WebAssembly extensions for commerce](https://shopify.engineering/ship-fast-with-webassembly-shopify-functions)
- [jco: JavaScript Component toolchain](https://github.com/bytecodealliance/jco) — runs and builds components in Node.js and browsers
