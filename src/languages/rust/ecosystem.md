# Rust Ecosystem and Tooling

## Overview

Rust's ecosystem is anchored by **Cargo** (build, dependencies, testing, publishing in one tool) and organized around a few dominant libraries: **Tokio** for async runtime, **Serde** for serialization, **Rayon** for data parallelism, and framework choices like **Axum**/**Actix Web**. The ecosystem prizes type safety and zero-cost abstractions — libraries are often "the one canonical way" (serde, tokio) rather than a fragmented market.

See [Rust Overview](./README.md) and [Async Rust](./async.md) for the language.

## Cargo: The One-Stop Toolchain

Cargo is Rust's package manager **and** build system **and** test runner:

```bash
cargo new myapp          # new project (src/main.rs + Cargo.toml)
cargo add serde          # add a dependency (edition-aware)
cargo build / cargo run
cargo test               # unit + integration tests
cargo clippy             # lints
cargo fmt                # formatting
cargo doc                # docs.rs-style local docs
```

Key concepts: **Cargo.toml** (manifest), **Cargo.lock** (reproducible), **crates.io** (registry), **workspaces** (multi-crate monorepos), **features** (compile-time toggles), and **build scripts** (`build.rs`).

## Core Libraries (the "canonical" stack)

| Library | Role | Notes |
|---|---|---|
| **Serde** | Serialization framework | `#[derive(Serialize, Deserialize)]`; backends: JSON (serde_json), YAML, TOML, CBOR, Postcard |
| **Tokio** | Async runtime | Work-stealing multi-thread runtime; see [Tokio](../../frameworks/tokio/README.md) |
| **Rayon** | Data parallelism | `par_iter()` for transparent parallel iteration — the easiest way to speed up CPU-bound code |
| **Reqwest** | HTTP client | Async + blocking, TLS, JSON helpers |
| **SQLx** | Async SQL | **Compile-time checked queries** (`query!`), supports Postgres/MySQL/SQLite |
| **Diesel** | Sync ORM/query builder | Type-safe query DSL, migrations |
| **Axum** | Web framework | **Tokio ecosystem's** web framework (by the Tokio team), tower middleware, extractors |
| **Actix Web** | Web framework | Actor-based, very fast, older but mature |
| **Anyhow / thiserror** | Error handling | anyhow for apps, thiserror for libraries (see [Error Handling](./error-handling.md)) |

### Serde example

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
struct User {
    id: u64,
    name: String,
    #[serde(default)]
    email: Option<String>,
}

fn main() {
    let u = User { id: 1, name: "Ada".into(), email: None };
    let json = serde_json::to_string(&u).unwrap();
    // {"id":1,"name":"Ada","email":null}
}
```

Serde's derive macros generate the serialization impls at compile time — **zero runtime reflection**, which is the Rust way (vs Python/Go's runtime serialization).

### Rayon example

```rust
use rayon::prelude::*;

fn sum_of_squares(nums: &[u64]) -> u64 {
    nums.par_iter().map(|n| n * n).sum()   // automatic parallelism
}
```

`par_iter()` partitions the data across threads automatically, with **work-stealing** for load balancing. It's the idiomatic answer to "how do I parallelize a pure computation in Rust?"

### SQLx (compile-time checked SQL)

```rust
let user = sqlx::query_as::<_, User>(
    "SELECT id, name FROM users WHERE id = $1"
)
.bind(id)
.fetch_one(&pool)
.await?;
```

SQLx checks the SQL **against the actual database schema at compile time** (via a live DB or offline mode with cached metadata) — a genuinely unique safety property: SQL errors surface before you ship.

## Web Frameworks: Axum vs Actix Web

| | **Axum** | **Actix Web** |
|---|---|---|
| Maintainer | Tokio team (official async ecosystem) | Actix project (community) |
| Philosophy | Modular, tower middleware, type-safe extractors | Actor-based, mature, very high performance |
| Middleware | tower ecosystem | actix-web middleware |
| When | New projects, staying in the Tokio ecosystem | Legacy/mature deployments, actor patterns |

Both are excellent; **Axum is the modern default** for new Tokio-based services (it composes with tower, hyper, and the rest of the tokio stack).

```rust
use axum::{routing::get, Router};

#[tokio::main]
async fn main() {
    let app = Router::new().route("/", get(|| async { "Hello, world!" }));
    axum::Server::bind(&"0.0.0.0:3000".parse().unwrap())
        .serve(app.into_make_service())
        .await
        .unwrap();
}
```

## Other Ecosystem Staples

| Tool | Role |
|---|---|
| **clap** | CLI argument parsing (derive-based) |
| **tracing / tracing-subscriber** | Structured logging and spans (async-aware) |
| **tokio-uring** | io_uring-based async I/O for extreme performance |
| **rustfmt / clippy** | Formatting / linting |
| **criterion** | Benchmarking |
| **proptest** | Property-based testing |
| **miri** | Undefined-behavior checker for unsafe code |

## Interview Questions

### Q: What is Serde and why is it different from runtime serialization?

Serde is Rust's serialization framework using **derive macros**: `#[derive(Serialize, Deserialize)]` generates the codec at compile time — no reflection at runtime, so it's fast and the compiler catches missing fields. The same derive works across formats (JSON, YAML, TOML, CBOR) via backend crates. It's the canonical serialization library in Rust.

### Q: How does Rayon parallelize iterators?

`par_iter()` splits the collection into chunks, distributes them across a thread pool with **work-stealing** (idle threads steal from busy ones), and joins results. Because the closure must be `Send + Sync`, the compiler guarantees the parallel code is memory-safe. For pure CPU-bound work it's often a one-line change from sequential to parallel.

### Q: What makes SQLx different from a typical ORM?

SQLx is SQL-first with **compile-time checked queries**: `query!`/`query_as!` verify the SQL against the schema at build time, generating typed structs — SQL errors and type mismatches fail the build, not production. Unlike Diesel (a full ORM/query builder), SQLx doesn't hide SQL; it makes raw SQL safe. It's also async-native across Postgres/MySQL/SQLite.

### Q: Axum vs Actix Web?

Axum is the Tokio-team's modern framework — modular, tower-based middleware, type-safe extractors, and first-class composition with the tokio/hyper ecosystem; it's the default for new services. Actix Web is the older actor-based framework, extremely fast and mature. Choose Axum for new Tokio-ecosystem projects; Actix for existing deployments or actor-style designs.

### Q: How does Cargo support testing and publishing?

Cargo integrates everything: `cargo test` runs unit tests (inline `#[test]`), integration tests in `tests/`, and doc tests; `cargo publish` builds, verifies, and uploads to crates.io; workspaces organize multi-crate projects; `Cargo.lock` pins exact versions for reproducible builds. There's no separate test-runner or build tool — Cargo is the single entry point.

## References

- The Cargo Book — https://doc.rust-lang.org/cargo/
- Serde — https://serde.rs/
- Rayon — https://github.com/rayon-rs/rayon
- SQLx — https://github.com/launchbadge/sqlx
- Axum — https://github.com/tokio-rs/axum
- Actix Web — https://actix.rs/
- Tokio — https://tokio.rs/

## Related Topics

- [Rust Overview](./README.md) — the language
- [Async Rust](./async.md) — futures, tokio runtime
- [Error Handling](./error-handling.md) — anyhow/thiserror patterns
- [Tokio](../../frameworks/tokio/README.md) — the async runtime deep dive
- [Backend Engineering](../../backend/README.md) — services built on axum/actix
