# Programming Languages, Compilers & Runtimes Reference Library

This page is a verified index of primary sources for compilers: official documentation, developer and API portals, source repositories, SDKs, downloadable or offline documentation, a two-track learning path, and free-access research literature.

It is a **navigation layer**, not a tutorial. Where the rest of this book explains a concept, this page tells you which document to open to get the authoritative answer, and in what order to read things. Every link was HTTP-verified on the date shown below; sources that block automated checkers but work in a browser are flagged rather than silently dropped.

Compiler infrastructure, language specifications, managed runtimes and JITs, WebAssembly, parsing tooling, and a two-track path from Crafting Interpreters to reading V8, rustc and MLIR.

**82 entries** across 8 categories, plus **59 education & reference-implementation resources** (24 basic / 35 advanced).

Every link HTTP-verified on **2026-10-07**.

> www.gnu.org (the Bison manual) did not respond to our checker — the host blocks our verification network. The project is live: ftp.gnu.org/gnu/bison and savannah.gnu.org both returned 200, and the manual loads normally in a browser.

## Contents

- [1. Compiler infrastructure](#1-compiler-infrastructure) — 7
- [2. Systems languages & their implementations](#2-systems-languages--their-implementations) — 7
- [3. Managed runtimes & virtual machines](#3-managed-runtimes--virtual-machines) — 13
- [4. Functional languages & type systems](#4-functional-languages--type-systems) — 5
- [5. WebAssembly & language specifications](#5-webassembly--language-specifications) — 7
- [6. Parsing, tooling & language engineering](#6-parsing-tooling--language-engineering) — 4
- [7. Proof assistants, verification & teaching material](#7-proof-assistants-verification--teaching-material) — 12
- [8. Research papers & open-access literature](#8-research-papers--open-access-literature) — 27
- [Education & reference implementations](#education--reference-implementations) — 59 (24 basic / 35 advanced)


## 1. Compiler infrastructure

### LLVM

- **Docs:** [llvm.org/docs](https://llvm.org/docs/)
- **Developer / API:** [llvm.org/docs/LangRef.html](https://llvm.org/docs/LangRef.html)
- **Source:** [github.com/llvm/llvm-project](https://github.com/llvm/llvm-project)
- **SDKs & repos:** Clang, LLD, libc++, MLIR, Polly — one monorepo
- **Downloadable / offline:** Docs build from source; released as HTML per version
- *Note:* The dominant compiler infrastructure. `LangRef.html` is the IR specification and the single most useful document here.

### Clang

- **Docs:** [clang.llvm.org/docs](https://clang.llvm.org/docs/)
- **Developer / API:** [clang.llvm.org/docs/InternalsManual.html](https://clang.llvm.org/docs/InternalsManual.html)
- **Source:** [github.com/llvm/llvm-project](https://github.com/llvm/llvm-project)
- **SDKs & repos:** libclang, clang-tidy, clangd, AST matchers
- **Downloadable / offline:** Docs per release
- *Note:* The Internals Manual explains how a real industrial frontend is structured.

### MLIR

- **Docs:** [mlir.llvm.org](https://mlir.llvm.org/)
- **Developer / API:** [mlir.llvm.org/docs](https://mlir.llvm.org/docs/)
- **Source:** [github.com/llvm/llvm-project](https://github.com/llvm/llvm-project)
- **SDKs & repos:** Dialect infrastructure; used by XLA, TVM, Triton, CIRCT, Flang
- **Downloadable / offline:** Docs site + tutorials
- *Note:* The most important compiler-infrastructure development of the last decade. The Toy tutorial is the way in.

### GCC

- **Docs:** [gcc.gnu.org/onlinedocs](https://gcc.gnu.org/onlinedocs/)
- **Developer / API:** [gcc.gnu.org/onlinedocs/gccint](https://gcc.gnu.org/onlinedocs/gccint/)
- **Source:** [gcc.gnu.org/git](https://gcc.gnu.org/git/)
- **SDKs & repos:** GIMPLE and RTL internals; plugins
- **Downloadable / offline:** Full manuals as HTML, PDF and info
- *Note:* The internals manual (`gccint`) is dense but authoritative. Still the reference for many targets LLVM handles less well.

### Cranelift

- **Docs:** [github.com/bytecodealliance/…](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift)
- **Developer / API:** [docs.rs/cranelift](https://docs.rs/cranelift)
- **Source:** [github.com/bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime)
- **SDKs & repos:** Fast code generator used by Wasmtime and Rust's debug backend
- **Downloadable / offline:** In-repo docs
- *Note:* Designed for compile speed and verifiability rather than peak output. A useful contrast with LLVM.

### QBE

- **Docs:** [c9x.me/compile](https://c9x.me/compile/)
- **Developer / API:** [c9x.me/compile/doc/il.html](https://c9x.me/compile/doc/il.html)
- **SDKs & repos:** A compact backend aiming for 70% of LLVM's performance at 10% of the complexity
- **Downloadable / offline:** Docs on site
- *Note:* Small enough to read entirely. Excellent if LLVM is too large to approach.

### chibicc

- **Docs:** [github.com/rui314/chibicc](https://github.com/rui314/chibicc)
- **Source:** [github.com/rui314/chibicc](https://github.com/rui314/chibicc)
- **SDKs & repos:** A small C compiler developed in readable, incremental commits
- **Downloadable / offline:** Read the git history commit by commit
- *Note:* Rui Ueyama's teaching compiler. The commit sequence *is* the tutorial.


## 2. Systems languages & their implementations

### Rust

- **Docs:** [doc.rust-lang.org/book](https://doc.rust-lang.org/book/)
- **Developer / API:** [doc.rust-lang.org/reference](https://doc.rust-lang.org/reference/)
- **Source:** [github.com/rust-lang/rust](https://github.com/rust-lang/rust)
- **SDKs & repos:** Cargo, rustup, clippy, rust-analyzer; MIR and borrow checker in-tree
- **Downloadable / offline:** All books ship offline with rustup (`rustup doc`)
- *Note:* The rustc dev guide is one of the best explanations of a modern compiler's internals ever published openly.

### rustc dev guide

- **Docs:** [rustc-dev-guide.rust-lang.org](https://rustc-dev-guide.rust-lang.org/)
- **Source:** [github.com/rust-lang/rustc-dev-guide](https://github.com/rust-lang/rustc-dev-guide)
- **SDKs & repos:** Query-based compilation, HIR, MIR, borrow checking, codegen
- **Downloadable / offline:** mdBook, downloadable
- *Note:* Read this even if you never touch Rust. It explains incremental and query-based compiler architecture better than any textbook.

### Go

- **Docs:** [go.dev/doc](https://go.dev/doc/)
- **Developer / API:** [go.dev/ref/spec](https://go.dev/ref/spec)
- **Source:** [github.com/golang/go](https://github.com/golang/go)
- **SDKs & repos:** Full toolchain in-tree; the compiler is written in Go
- **Downloadable / offline:** `go doc` offline; spec is one readable page
- *Note:* The Go spec is short enough to read in a sitting — a rare virtue. The runtime source (scheduler, GC) is also unusually approachable.

### Zig

- **Docs:** [ziglang.org/documentation/master](https://ziglang.org/documentation/master/)
- **Developer / API:** [ziglang.org/documentation/master/std](https://ziglang.org/documentation/master/std/)
- **Source:** [github.com/ziglang/zig](https://github.com/ziglang/zig)
- **SDKs & repos:** Self-hosted compiler; comptime; also works as a C/C++ cross-compiler
- **Downloadable / offline:** Single-page language reference
- *Note:* `comptime` is the most interesting language-design idea in recent systems languages.

### C++ standardization (WG21)

- **Docs:** [open-std.org/jtc1/sc22/wg21/docs/papers](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/)
- **Source:** [github.com/cplusplus](https://github.com/cplusplus)
- **SDKs & repos:** Every proposal paper, public
- **Downloadable / offline:** Papers as PDF/HTML
- *Note:* Reading WG21 papers is the only way to understand why C++ is shaped as it is. cppreference.com is the practical reference.

### C standardization (WG14)

- **Docs:** [open-std.org/jtc1/sc22/wg14](https://www.open-std.org/jtc1/sc22/wg14/)
- **SDKs & repos:** Working drafts are free; the final standard is not
- **Downloadable / offline:** Drafts as PDF
- *Note:* The latest working draft is functionally the standard for most purposes.

### Swift

- **Docs:** [swift.org/documentation](https://www.swift.org/documentation/)
- **Source:** [github.com/swiftlang/swift](https://github.com/swiftlang/swift)
- **SDKs & repos:** SwiftPM, swift-syntax; SIL is a documented intermediate language
- **Downloadable / offline:** Docs site; The Swift Programming Language book free
- *Note:* SIL (Swift Intermediate Language) is well documented and worth studying as a high-level IR design.


## 3. Managed runtimes & virtual machines

### CPython

- **Docs:** [docs.python.org/3/reference](https://docs.python.org/3/reference/)
- **Developer / API:** [devguide.python.org](https://devguide.python.org/)
- **Source:** [github.com/python/cpython](https://github.com/python/cpython)
- **SDKs & repos:** C API, bytecode, the `dis` module
- **Downloadable / offline:** Full docs downloadable as HTML/PDF/EPUB archives
- *Note:* The developer guide now includes solid internals documentation. `dis` plus `ceval.c` is a practical VM course.

### PyPy

- **Docs:** [doc.pypy.org/en/latest](https://doc.pypy.org/en/latest/)
- **Source:** [foss.heptapod.net/pypy/pypy](https://foss.heptapod.net/pypy/pypy)
- **SDKs & repos:** RPython toolchain; meta-tracing JIT
- **Downloadable / offline:** Sphinx docs
- *Note:* Generating a JIT from an interpreter specification is a genuinely different idea. Read the architecture docs.

### OpenJDK

- **Docs:** [github.com/openjdk/jdk](https://github.com/openjdk/jdk)
- **Developer / API:** [docs.oracle.com/javase/specs](https://docs.oracle.com/javase/specs/)
- **Source:** [github.com/openjdk/jdk](https://github.com/openjdk/jdk)
- **SDKs & repos:** HotSpot, C1/C2, G1 and ZGC collectors, JVMTI
- **Downloadable / offline:** JLS and JVMS free as PDF/HTML
- *Note:* The JVM Specification is the best-written VM spec in existence. Read it before any JVM internals material.

### GraalVM

- **Docs:** [graalvm.org/latest/docs](https://www.graalvm.org/latest/docs/)
- **Source:** [github.com/oracle/graal](https://github.com/oracle/graal)
- **SDKs & repos:** Truffle language framework, native image, Graal JIT
- **Downloadable / offline:** Docs site
- *Note:* Truffle — building languages as AST interpreters that partial-evaluate into fast code — is the most interesting runtime research shipping in production.

### .NET runtime

- **Docs:** [learn.microsoft.com/en-us/dotnet](https://learn.microsoft.com/en-us/dotnet/)
- **Developer / API:** [learn.microsoft.com/en-us/dotnet/api](https://learn.microsoft.com/en-us/dotnet/api/)
- **Source:** [github.com/dotnet/runtime](https://github.com/dotnet/runtime)
- **SDKs & repos:** RyuJIT, CoreCLR, the BCL; extensive in-repo design docs
- **Downloadable / offline:** Microsoft Learn offline export
- *Note:* `docs/design/` in dotnet/runtime is a treasure of real runtime engineering writing.

### Roslyn

- **Docs:** [github.com/dotnet/roslyn](https://github.com/dotnet/roslyn)
- **Developer / API:** [learn.microsoft.com/en-us/…](https://learn.microsoft.com/en-us/dotnet/csharp/roslyn-sdk/)
- **Source:** [github.com/dotnet/roslyn](https://github.com/dotnet/roslyn)
- **SDKs & repos:** Compiler-as-a-service: syntax trees, semantic model, analyzers
- **Downloadable / offline:** In-repo docs
- *Note:* The clearest production example of an IDE-oriented incremental compiler.

### V8

- **Docs:** [v8.dev/docs](https://v8.dev/docs)
- **Source:** [github.com/v8/v8](https://github.com/v8/v8)
- **SDKs & repos:** Ignition interpreter, TurboFan and Maglev JITs, Orinoco GC
- **Downloadable / offline:** Docs site + the V8 blog
- *Note:* The V8 blog posts on hidden classes and inline caches are the standard explanation of dynamic-language optimization.

### SpiderMonkey

- **Docs:** [spidermonkey.dev](https://spidermonkey.dev/)
- **Developer / API:** [spidermonkey.dev/docs](https://spidermonkey.dev/docs/)
- **Source:** [github.com/mozilla/gecko-dev](https://github.com/mozilla/gecko-dev)
- **SDKs & repos:** Firefox's JS engine; WarpMonkey JIT
- **Downloadable / offline:** Docs site

### Node.js

- **Docs:** [nodejs.org/docs/latest/api](https://nodejs.org/docs/latest/api/)
- **Source:** [github.com/nodejs/node](https://github.com/nodejs/node)
- **SDKs & repos:** libuv event loop over V8
- **Downloadable / offline:** Docs downloadable as JSON/HTML per version

### Deno

- **Docs:** [docs.deno.com](https://docs.deno.com/)
- **Developer / API:** [docs.deno.com/api](https://docs.deno.com/api/)
- **Source:** [github.com/denoland/deno](https://github.com/denoland/deno)
- **SDKs & repos:** V8 + Rust + Tokio; permissions model
- **Downloadable / offline:** Docs site

### Bun

- **Docs:** [bun.com/docs](https://bun.com/docs)
- **Developer / API:** [bun.com/docs/api/http](https://bun.com/docs/api/http)
- **Source:** [github.com/oven-sh/bun](https://github.com/oven-sh/bun)
- **SDKs & repos:** Built on JavaScriptCore and Zig
- **Downloadable / offline:** Docs site

### LuaJIT

- **Docs:** [luajit.org/luajit.html](https://luajit.org/luajit.html)
- **Developer / API:** [luajit.org/ext_ffi.html](https://luajit.org/ext_ffi.html)
- **Source:** [github.com/LuaJIT/LuaJIT](https://github.com/LuaJIT/LuaJIT)
- **SDKs & repos:** Trace-compiling JIT, FFI
- **Downloadable / offline:** Docs on site
- *Note:* Mike Pall's tracing JIT remains among the most impressive single-author compiler engineering efforts anywhere.

### Lua

- **Docs:** [lua.org/manual/5.4](https://www.lua.org/manual/5.4/)
- **Source:** [github.com/lua/lua](https://github.com/lua/lua)
- **SDKs & repos:** The whole language in a ~25,000-line C codebase
- **Downloadable / offline:** Single-page manual
- *Note:* One of the most readable language implementations in existence. A good first real interpreter to study.


## 4. Functional languages & type systems

### GHC (Haskell)

- **Docs:** [downloads.haskell.org/ghc/…](https://downloads.haskell.org/ghc/latest/docs/users_guide/)
- **Source:** [github.com/ghc/ghc](https://github.com/ghc/ghc)
- **SDKs & repos:** Core, STG and Cmm intermediate languages, all documented
- **Downloadable / offline:** User guide as HTML/PDF
- *Note:* The Core-to-STG-to-Cmm pipeline is the reference for compiling lazy functional languages.

### OCaml

- **Docs:** [ocaml.org/docs](https://ocaml.org/docs)
- **Developer / API:** [ocaml.org/manual](https://ocaml.org/manual/)
- **Source:** [github.com/ocaml/ocaml](https://github.com/ocaml/ocaml)
- **SDKs & repos:** Dune, opam; the compiler is small and readable
- **Downloadable / offline:** Manual as HTML/PDF
- *Note:* Frequently the implementation language of choice for compiler research, for good reasons.

### Erlang/OTP

- **Docs:** [erlang.org/docs](https://www.erlang.org/docs)
- **Developer / API:** [erlang.org/doc](https://www.erlang.org/doc/)
- **Source:** [github.com/erlang/otp](https://github.com/erlang/otp)
- **SDKs & repos:** BEAM VM, OTP behaviours
- **Downloadable / offline:** Docs per release
- *Note:* BEAM's scheduler and process isolation design is unlike anything else in this list.

### Elixir

- **Docs:** [hexdocs.pm/elixir/introduction.html](https://hexdocs.pm/elixir/introduction.html)
- **Developer / API:** [hexdocs.pm/elixir](https://hexdocs.pm/elixir/)
- **Source:** [github.com/elixir-lang/elixir](https://github.com/elixir-lang/elixir)
- **SDKs & repos:** Runs on BEAM; macro system
- **Downloadable / offline:** HexDocs, downloadable

### Kotlin

- **Docs:** [kotlinlang.org/docs/home.html](https://kotlinlang.org/docs/home.html)
- **Developer / API:** [kotlinlang.org/api/latest/jvm/stdlib](https://kotlinlang.org/api/latest/jvm/stdlib/)
- **Source:** [github.com/JetBrains/kotlin](https://github.com/JetBrains/kotlin)
- **SDKs & repos:** JVM, Native (LLVM) and JS backends
- **Downloadable / offline:** Docs site


## 5. WebAssembly & language specifications

### WebAssembly spec

- **Docs:** [webassembly.github.io/spec/core](https://webassembly.github.io/spec/core/)
- **Source:** [github.com/WebAssembly/spec](https://github.com/WebAssembly/spec)
- **SDKs & repos:** Formal semantics, with a reference interpreter in OCaml
- **Downloadable / offline:** Spec as HTML and PDF
- *Note:* A fully formally specified mainstream VM — rare, and worth reading as an example of how to specify one.

### Wasmtime

- **Docs:** [docs.wasmtime.dev](https://docs.wasmtime.dev/)
- **Developer / API:** [docs.rs/wasmtime](https://docs.rs/wasmtime)
- **Source:** [github.com/bytecodealliance/wasmtime](https://github.com/bytecodealliance/wasmtime)
- **SDKs & repos:** Cranelift backend; WASI implementation
- **Downloadable / offline:** Docs site
- *Note:* The reference standalone runtime.

### Wasmer

- **Docs:** [docs.wasmer.io](https://docs.wasmer.io/)
- **Source:** [github.com/wasmerio/wasmer](https://github.com/wasmerio/wasmer)
- **SDKs & repos:** Multiple backends; WASIX
- **Downloadable / offline:** Docs site

### WAMR

- **Docs:** [github.com/bytecodealliance/wasm-micro-runtime](https://github.com/bytecodealliance/wasm-micro-runtime)
- **Source:** [github.com/bytecodealliance/wasm-micro-runtime](https://github.com/bytecodealliance/wasm-micro-runtime)
- **SDKs & repos:** Tiny runtime for embedded targets
- **Downloadable / offline:** In-repo docs

### ECMAScript specification

- **Docs:** [tc39.es/ecma262](https://tc39.es/ecma262/)
- **Source:** [github.com/tc39/ecma262](https://github.com/tc39/ecma262)
- **SDKs & repos:** The normative JavaScript language definition
- **Downloadable / offline:** Single HTML document
- *Note:* Surprisingly readable once you learn the abstract-operation notation.

### TC39 proposals

- **Docs:** [github.com/tc39/proposals](https://github.com/tc39/proposals)
- **Source:** [github.com/tc39/proposals](https://github.com/tc39/proposals)
- **SDKs & repos:** Every JS language proposal by stage
- **Downloadable / offline:** Repo
- *Note:* Watch the language evolve in public.

### Java Language & VM Specifications

- **Docs:** [docs.oracle.com/javase/specs](https://docs.oracle.com/javase/specs/)
- **Source:** [github.com/openjdk/jdk](https://github.com/openjdk/jdk)
- **SDKs & repos:** JLS and JVMS per release
- **Downloadable / offline:** Free PDF and HTML
- *Note:* The JVMS is a model of how to specify a virtual machine.


## 6. Parsing, tooling & language engineering

### tree-sitter

- **Docs:** [tree-sitter.github.io/tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- **Source:** [github.com/tree-sitter/tree-sitter](https://github.com/tree-sitter/tree-sitter)
- **SDKs & repos:** Incremental GLR parsing; grammars for 100+ languages; bindings everywhere
- **Downloadable / offline:** Docs site
- *Note:* Now the standard parsing layer for editors. The incremental re-parsing design is the interesting part.

### ANTLR

- **Docs:** [antlr.org](https://www.antlr.org/)
- **Developer / API:** [github.com/antlr/…](https://github.com/antlr/antlr4/blob/master/doc/index.md)
- **Source:** [github.com/antlr/antlr4](https://github.com/antlr/antlr4)
- **SDKs & repos:** ALL(*) parsing; targets Java, C#, Python, Go, C++, JS
- **Downloadable / offline:** Documentation in-repo; reference book available
- *Note:* The practical choice when you need a parser for a real grammar quickly.

### GNU Bison

- **Docs:** [gnu.org/software/bison/manual/bison.html](https://www.gnu.org/software/bison/manual/bison.html)
- **Source:** [cgit.git.savannah.gnu.org/cgit/bison.git](https://cgit.git.savannah.gnu.org/cgit/bison.git)
- **SDKs & repos:** LALR(1) and GLR parser generator
- **Downloadable / offline:** Manual as HTML, PDF and info; releases at [ftp.gnu.org/gnu/bison](https://ftp.gnu.org/gnu/bison/)
- *Note:* Still worth learning for the grammar theory, even if you ship tree-sitter. www.gnu.org blocks our verification network at the host level — the project is live (ftp.gnu.org and savannah both responded 200) and the manual loads normally in a browser.

### LLVM Kaleidoscope tutorial

- **Docs:** [llvm.org/docs/tutorial](https://llvm.org/docs/tutorial/)
- **Source:** [github.com/llvm/llvm-project](https://github.com/llvm/llvm-project)
- **SDKs & repos:** Build a working language with an LLVM backend, chapter by chapter
- **Downloadable / offline:** In the LLVM docs
- *Note:* The canonical 'my first LLVM frontend' path.


## 7. Proof assistants, verification & teaching material

### Compiler Explorer (godbolt)

- **Docs:** [godbolt.org](https://godbolt.org/)
- **Source:** [github.com/compiler-explorer/compiler-explorer](https://github.com/compiler-explorer/compiler-explorer)
- **SDKs & repos:** Live compilation to assembly across dozens of compilers and languages; self-hostable
- **Downloadable / offline:** Whole site runs locally from the repo
- *Note:* The single most useful interactive tool in this field. Also shows LLVM IR, MIR and GIMPLE, not just assembly.

### cppreference

- **Docs:** [en.cppreference.com/w](https://en.cppreference.com/w/)
- **SDKs & repos:** The practical C and C++ reference, tracking the standard closely
- **Downloadable / offline:** Full offline archive available for download
- *Note:* 403s to bots, fine in a browser. More usable than the standard itself for day-to-day work.

### Rustonomicon

- **Docs:** [doc.rust-lang.org/nomicon](https://doc.rust-lang.org/nomicon/)
- **Source:** [github.com/rust-lang/nomicon](https://github.com/rust-lang/nomicon)
- **SDKs & repos:** Unsafe Rust, aliasing rules, variance, drop order
- **Downloadable / offline:** Ships offline with rustup
- *Note:* The place where Rust’s memory model is actually explained.

### Racket

- **Docs:** [docs.racket-lang.org](https://docs.racket-lang.org/)
- **Developer / API:** [docs.racket-lang.org/reference](https://docs.racket-lang.org/reference/)
- **Source:** [github.com/racket/racket](https://github.com/racket/racket)
- **SDKs & repos:** Language-oriented programming; `#lang` lets you define whole new languages
- **Downloadable / offline:** Full docs ship with the installation
- *Note:* Built specifically for making languages. If you want to prototype a language design quickly, start here.

### R7RS Scheme

- **Docs:** [small.r7rs.org](https://small.r7rs.org/)
- **SDKs & repos:** The small Scheme standard
- **Downloadable / offline:** Free PDF, about 80 pages
- *Note:* A complete language specification you can read in an evening. Excellent calibration for what a spec can be.

### SICP

- **Docs:** [web.mit.edu/6.001/6.037/sicp.pdf](https://web.mit.edu/6.001/6.037/sicp.pdf)
- **Developer / API:** [sarabander.github.io/sicp](https://sarabander.github.io/sicp/)
- **SDKs & repos:** Structure and Interpretation of Computer Programs, including the metacircular evaluator
- **Downloadable / offline:** Free PDF; a cleaner HTML edition at [sarabander.github.io/sicp](https://sarabander.github.io/sicp/)
- *Note:* Chapters 4 and 5 — building an evaluator and a register machine — are the relevant part for this topic.

### Essentials of Compilation

- **Docs:** [github.com/IUCompilerCourse/…](https://github.com/IUCompilerCourse/Essentials-of-Compilation)
- **Source:** [github.com/IUCompilerCourse/…](https://github.com/IUCompilerCourse/Essentials-of-Compilation)
- **SDKs & repos:** Jeremy Siek’s incremental compiler course book, in Racket and Python editions
- **Downloadable / offline:** Drafts free from the repo
- *Note:* Builds a compiler in small verified increments. A strong complement to Crafting Interpreters.

### Lean 4

- **Docs:** [lean-lang.org/documentation](https://lean-lang.org/documentation/)
- **Developer / API:** [leanprover-community.github.io](https://leanprover-community.github.io/)
- **Source:** [github.com/leanprover/lean4](https://github.com/leanprover/lean4)
- **SDKs & repos:** Dependently typed language and proof assistant; also a serious general-purpose language
- **Downloadable / offline:** Functional Programming in Lean and Theorem Proving in Lean, both free
- *Note:* Lean is written largely in Lean, so the compiler source doubles as an advanced example.

### Rocq (formerly Coq)

- **Docs:** [rocq-prover.org](https://rocq-prover.org/)
- **Developer / API:** [rocq-prover.org/doc](https://rocq-prover.org/doc/)
- **Source:** [github.com/rocq-prover/rocq](https://github.com/rocq-prover/rocq)
- **SDKs & repos:** The proof assistant behind CompCert and Software Foundations
- **Downloadable / offline:** Full manual online
- *Note:* Renamed from Coq in 2025. Older material still says Coq; it is the same system.

### Agda

- **Docs:** [agda.readthedocs.io](https://agda.readthedocs.io/)
- **Source:** [github.com/agda/agda](https://github.com/agda/agda)
- **SDKs & repos:** Dependently typed functional language and proof assistant
- **Downloadable / offline:** Sphinx docs

### Dafny

- **Docs:** [dafny.org](https://dafny.org/)
- **Developer / API:** [dafny.org/latest/DafnyRef/DafnyRef](https://dafny.org/latest/DafnyRef/DafnyRef)
- **Source:** [github.com/dafny-lang/dafny](https://github.com/dafny-lang/dafny)
- **SDKs & repos:** Verification-aware language with an SMT backend
- **Downloadable / offline:** Reference manual online
- *Note:* The most approachable entry into program verification — write preconditions and let Z3 do the work.

### matklad’s blog

- **Docs:** [matklad.github.io](https://matklad.github.io/)
- **SDKs & repos:** Aleksey Kladov on parsers, IDEs, build systems and rust-analyzer internals
- **Downloadable / offline:** Free archive
- *Note:* The Pratt parsing article and the IDE-architecture posts are essential reading for anyone building language tooling.


## 8. Research papers & open-access literature

### arXiv

- **Docs:** [arxiv.org](https://arxiv.org/)
- **Developer / API:** [info.arxiv.org/help/api/index.html](https://info.arxiv.org/help/api/index.html)
- **SDKs & repos:** Preprints across all of CS; most systems, ML and PL work appears here before publication
- **Downloadable / offline:** Every paper is a free PDF. Bulk access documented at [info.arxiv.org/help/bulk_data/index.html](https://info.arxiv.org/help/bulk_data/index.html); a full-text API at export.arxiv.org
- *Note:* Not peer-reviewed. Treat an arXiv-only paper as a claim, not a result — but it is where you will read almost everything first.

### ar5iv

- **Docs:** [ar5iv.labs.arxiv.org](https://ar5iv.labs.arxiv.org/)
- **SDKs & repos:** Renders any arXiv paper as responsive HTML instead of PDF
- **Downloadable / offline:** Free; swap `arxiv.org/abs/ID` for `ar5iv.labs.arxiv.org/html/ID`
- *Note:* Makes papers readable on a phone and searchable in-page. Underused.

### alphaXiv

- **Docs:** [alphaxiv.org](https://www.alphaxiv.org/)
- **SDKs & repos:** arXiv papers with a public comment and discussion layer
- **Downloadable / offline:** Free
- *Note:* Useful when a paper is contested — the discussion often contains the critique you were looking for.

### Semantic Scholar

- **Docs:** [semanticscholar.org](https://www.semanticscholar.org/)
- **Developer / API:** [api.semanticscholar.org/graph/v1](https://api.semanticscholar.org/graph/v1)
- **SDKs & repos:** 200M+ papers with citation graph, influential-citation scoring and TLDR summaries
- **Downloadable / offline:** Free Graph API ([semanticscholar.org/product/api](https://www.semanticscholar.org/product/api)), bulk datasets available on request
- *Note:* The best free citation graph. 'Highly influential citations' is a genuinely useful filter for finding what actually mattered.

### OpenAlex

- **Docs:** [openalex.org](https://openalex.org/)
- **Developer / API:** [api.openalex.org/works](https://api.openalex.org/works)
- **SDKs & repos:** Fully open catalogue of works, authors, venues and institutions; successor to Microsoft Academic Graph
- **Downloadable / offline:** Entirely free API with no key required; complete database snapshots downloadable
- *Note:* The only large-scale bibliographic database that is open all the way down, including bulk snapshots.

### DBLP

- **Docs:** [dblp.org](https://dblp.org/)
- **Developer / API:** [dblp.org/faq/13501473.html](https://dblp.org/faq/13501473.html)
- **SDKs & repos:** Authoritative CS bibliography — complete author and venue listings
- **Downloadable / offline:** Free; full XML dump downloadable
- *Note:* The fastest way to find everything a given researcher has published, and to see a conference's full programme by year.

### OpenReview

- **Docs:** [openreview.net](https://openreview.net/)
- **Developer / API:** [docs.openreview.net](https://docs.openreview.net/)
- **Source:** [github.com/openreview](https://github.com/openreview)
- **SDKs & repos:** ICLR, NeurIPS, COLM and dozens of other venues — papers plus the full review threads
- **Downloadable / offline:** Free; REST API
- *Note:* Reading the reviews and author rebuttals teaches you how the field evaluates work. Nothing else exposes this.

### CORE

- **Docs:** [core.ac.uk](https://core.ac.uk/)
- **Developer / API:** [core.ac.uk/services/api](https://core.ac.uk/services/api)
- **SDKs & repos:** Aggregates 300M+ open-access papers from repositories worldwide
- **Downloadable / offline:** Free API and bulk datasets
- *Note:* Good for finding the green open-access copy when a publisher's version is paywalled.

### Unpaywall

- **Docs:** [unpaywall.org](https://unpaywall.org/)
- **Developer / API:** [api.unpaywall.org](https://api.unpaywall.org/)
- **SDKs & repos:** Finds legal free copies of paywalled papers via DOI
- **Downloadable / offline:** Free API; browser extension
- *Note:* Legal, author-deposited copies only. Install the extension and most paywalls simply stop appearing.

### Papers We Love

- **Docs:** [paperswelove.org](https://paperswelove.org/)
- **Source:** [github.com/papers-we-love/papers-we-love](https://github.com/papers-we-love/papers-we-love)
- **SDKs & repos:** A curated, categorised repository of classic CS papers with local meetup talks
- **Downloadable / offline:** Repo cloneable; many PDFs mirrored in-repo
- *Note:* The best starting point if you do not yet know which papers matter in a subfield.

### The Morning Paper (archive)

- **Docs:** [blog.acolyer.org](https://blog.acolyer.org/)
- **SDKs & repos:** Adrian Colyer's daily paper summaries, 2014-2021
- **Downloadable / offline:** Free archive, still online
- *Note:* No longer updated, but the back catalogue of ~1000 summarised papers is one of the great free CS resources.

### USENIX Proceedings

- **Docs:** [usenix.org/publications/proceedings](https://www.usenix.org/publications/proceedings)
- **SDKs & repos:** OSDI, SOSP (co-published), NSDI, ATC, FAST, Security — the core systems venues
- **Downloadable / offline:** Every paper free, immediately, with no membership. Often with recorded talks
- *Note:* USENIX made everything open access years before the rest of the field. If a systems paper exists, check here first.

### ACM Digital Library

- **Docs:** [dl.acm.org](https://dl.acm.org/)
- **SDKs & repos:** SIGMOD, ASPLOS, PLDI, POPL, SoCC and the ACM journals
- **Downloadable / offline:** Partly open: ACM Open and author-paid OA papers are free; others are paywalled
- *Note:* 403s to automated clients; loads in a browser. For paywalled items, check arXiv, the author's homepage or Unpaywall first — the free copy usually exists.

### IEEE Xplore

- **Docs:** [ieeexplore.ieee.org](https://ieeexplore.ieee.org/)
- **SDKs & repos:** ISCA, MICRO, HPCA and the IEEE journals
- **Downloadable / offline:** Mostly paywalled; abstracts free
- *Note:* Almost always worth searching the author's page or arXiv instead. Architecture authors in particular post preprints widely.

### DROPS / LIPIcs (Dagstuhl)

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, ITP, CONCUR, SAT and many theory venues
- **Downloadable / offline:** 100% open access, free PDFs, Creative Commons licensed
- *Note:* A fully open publisher. Every paper, always free, no exceptions.

### arXiv cs.PL (Programming Languages)

- **Docs:** [arxiv.org/list/cs.PL/recent](https://arxiv.org/list/cs.PL/recent)
- **SDKs & repos:** PL and compiler preprints
- **Downloadable / offline:** Free
- *Note:* See also [arxiv.org/list/cs.SE/recent](https://arxiv.org/list/cs.SE/recent) for software engineering.

### SIGPLAN OpenTOC

- **Docs:** [sigplan.org/OpenTOC](https://www.sigplan.org/OpenTOC/)
- **SDKs & repos:** Free, sanctioned access to the tables of contents and papers of PLDI, POPL, ICFP, OOPSLA and SPLASH
- **Downloadable / offline:** Free via the OpenTOC links
- *Note:* The official free route into SIGPLAN proceedings. Most people do not know this exists and pay or give up instead.

### ACM SIGPLAN

- **Docs:** [sigplan.org](https://www.sigplan.org/)
- **SDKs & repos:** The PL special interest group; PACMPL is its open-access journal
- **Downloadable / offline:** PACMPL papers are open access
- *Note:* Proceedings of the ACM on Programming Languages is gold open access — POPL, PLDI, ICFP and OOPSLA papers are free.

### PLDI

- **Docs:** [pldi25.sigplan.org](https://pldi25.sigplan.org/)
- **SDKs & repos:** Programming Language Design and Implementation — the compiler-heavy venue
- **Downloadable / offline:** Papers free via PACMPL/OpenTOC
- *Note:* If you care about compilers rather than type theory, start here.

### POPL

- **Docs:** [popl25.sigplan.org](https://popl25.sigplan.org/)
- **SDKs & repos:** Principles of Programming Languages — the theory venue
- **Downloadable / offline:** Free via PACMPL

### ICFP

- **Docs:** [icfp25.sigplan.org](https://icfp25.sigplan.org/)
- **SDKs & repos:** International Conference on Functional Programming
- **Downloadable / offline:** Free via PACMPL

### SPLASH / OOPSLA

- **Docs:** [2025.splashcon.org](https://2025.splashcon.org/)
- **SDKs & repos:** Object-oriented, applied and practice-oriented PL research
- **Downloadable / offline:** Free via PACMPL

### ECOOP

- **Docs:** [2025.ecoop.org](https://2025.ecoop.org/)
- **SDKs & repos:** European Conference on Object-Oriented Programming
- **Downloadable / offline:** 100% open access via LIPIcs/DROPS
- *Note:* Published through Dagstuhl, so every paper is free and Creative Commons licensed.

### The Art, Science, and Engineering of Programming

- **Docs:** [programming-journal.org](https://programming-journal.org/)
- **SDKs & repos:** Open-access PL journal with an unusually broad remit
- **Downloadable / offline:** Free, Creative Commons
- *Note:* Publishes work that does not fit the conference mould, including essays and artifacts.

### conf.researchr.org

- **Docs:** [conf.researchr.org](https://conf.researchr.org/)
- **SDKs & repos:** The hosting platform for most PL and SE conferences — programmes, artifacts, recorded talks
- **Downloadable / offline:** Free
- *Note:* Browse any recent conference programme here; artifact links are often more useful than the papers.

### DROPS / LIPIcs

- **Docs:** [drops.dagstuhl.de](https://drops.dagstuhl.de/)
- **SDKs & repos:** ECOOP, ITP, CONCUR, FSCD and other formal-methods venues
- **Downloadable / offline:** Fully open access

### LLVM Weekly

- **Docs:** [llvmweekly.org](https://llvmweekly.org/)
- **SDKs & repos:** Weekly digest of LLVM development
- **Downloadable / offline:** Free archive
- *Note:* The best way to track what is actually changing in the dominant compiler infrastructure.


## Education & reference implementations

Two tracks: **Basic** builds the foundations, **Advanced** is about reading and extending real implementations. Everything listed is free and publicly accessible.


### Basic

*24 resources across 6 topics.*


#### The book to start with

- **[Crafting Interpreters](https://craftinginterpreters.com/)** — Build two complete interpreters — a tree-walker in Java and a bytecode VM in C — with every line of code in the text. Free online, beautifully written. The best introduction to this field by a wide margin.
- **[Crafting Interpreters source](https://github.com/munificent/craftinginterpreters)** — Reference implementations of both interpreters.
- **[Writing a C Compiler](https://nostarch.com/writing-c-compiler)** — Nora Sandler's incremental C compiler book; the free blog series it grew from is also still online.
- **[Write a Compiler (blog series)](https://norasandler.com/2017/11/29/Write-a-Compiler.html)** — The free predecessor to the book. A complete staged project.


#### Small implementations to read end to end

- **[chibicc](https://github.com/rui314/chibicc)** — A C compiler built in readable incremental commits. Walk the git history as a tutorial.
- **[Lua source](https://github.com/lua/lua)** — A complete, fast, widely deployed language in ~25k lines of exceptionally clean C.
- **[QBE](https://c9x.me/compile/)** — A compiler backend small enough to actually read, aiming at most of LLVM's performance with a fraction of the complexity.
- **[Let's Build a Compiler (Crenshaw)](https://compilers.iecc.com/crenshaw/)** — Dated in its target, timeless in its method. Still one of the gentlest introductions.


#### Courses with public materials

- **[Stanford CS143 Compilers](https://web.stanford.edu/class/cs143/)** — Lexing through code generation, with public assignments building a full COOL compiler.
- **[LLVM Kaleidoscope tutorial](https://llvm.org/docs/tutorial/)** — Get a real language running on a real backend in a weekend.
- **[MLIR Toy tutorial](https://mlir.llvm.org/docs/)** — The seven-chapter Toy tutorial is the standard entry point to MLIR.


#### Specifications worth reading early

- **[The Go specification](https://go.dev/ref/spec)** — Short enough to read in one sitting. A model of specification economy.
- **[ECMAScript specification](https://tc39.es/ecma262/)** — Learn to read the abstract-operation notation; it makes JavaScript's oddities explicable.
- **[Java Virtual Machine Specification](https://docs.oracle.com/javase/specs/)** — The clearest specification of a virtual machine anywhere. Free.
- **[WebAssembly core spec](https://webassembly.github.io/spec/core/)** — A formally specified VM with a reference interpreter you can read.


#### Tools to pick up alongside

- **[tree-sitter](https://tree-sitter.github.io/tree-sitter/)** — Write a grammar and get incremental parsing plus editor integration for free.
- **[ANTLR](https://www.antlr.org/)** — When you need a working parser fast.
- **[GNU Bison](https://www.gnu.org/software/bison/manual/bison.html)** — Learn LALR parsing properly once.
- **[LLVM LangRef](https://llvm.org/docs/LangRef.html)** — Learn to read LLVM IR. It is a lingua franca across the whole field.


#### Finding and reading papers

- **[Papers We Love](https://paperswelove.org/)** — Start here when you do not yet know which papers matter. Curated by subfield, with recorded talks.
- **[The Morning Paper archive](https://blog.acolyer.org/)** — Around a thousand papers summarised in plain language. No longer updated; still one of the best free CS resources.
- **[Semantic Scholar](https://www.semanticscholar.org/)** — Free citation graph. The 'highly influential citations' filter is the fastest way to find what a paper actually changed.
- **[Unpaywall](https://unpaywall.org/)** — Install the extension. Most paywalls stop appearing, legally, because the author deposited a copy.
- **[ar5iv](https://ar5iv.labs.arxiv.org/)** — Read any arXiv paper as HTML instead of a two-column PDF. Swap arxiv.org/abs for ar5iv.labs.arxiv.org/html.


### Advanced

*35 resources across 6 topics.*


#### Production compiler internals

- **[rustc dev guide](https://rustc-dev-guide.rust-lang.org/)** — Query-based incremental compilation, MIR, borrow checking — explained unusually well. Read it regardless of your language.
- **[Clang Internals Manual](https://clang.llvm.org/docs/InternalsManual.html)** — How an industrial C/C++ frontend is actually organised.
- **[LLVM documentation](https://llvm.org/docs/)** — Pass infrastructure, the pass manager, and writing your own passes.
- **[GCC internals (gccint)](https://gcc.gnu.org/onlinedocs/)** — GIMPLE and RTL. Dense, but the only authoritative source.
- **[Roslyn](https://github.com/dotnet/roslyn)** — Incremental, IDE-first compiler design — a different set of constraints from batch compilation.
- **[Cranelift](https://github.com/bytecodealliance/wasmtime/tree/main/cranelift)** — A backend optimized for compile speed and verifiability instead of peak output.


#### MLIR & modern compiler infrastructure

- **[MLIR docs](https://mlir.llvm.org/docs/)** — Dialects, regions, the pattern rewriting infrastructure.
- **[MLIR](https://mlir.llvm.org/)** — Start with the Toy tutorial, then read a real dialect.
- **[LLVM monorepo](https://github.com/llvm/llvm-project)** — MLIR lives here alongside LLVM proper; read them together.
- **[Apache TVM](https://tvm.apache.org/docs/)** — Domain-specific compilation with autotuning.
- **[OpenXLA](https://openxla.org/xla)** — A production ML compiler with genuinely good internal documentation.


#### Runtimes, JITs & garbage collection

- **[V8 docs and blog](https://v8.dev/docs)** — Hidden classes, inline caches, and the tiering between Ignition, Maglev and TurboFan.
- **[V8 source](https://github.com/v8/v8)** — Large but navigable if you enter through a blog post's named files.
- **[OpenJDK](https://github.com/openjdk/jdk)** — HotSpot's C2, plus G1 and ZGC — the most mature GC implementations available to read.
- **[JVM Specification](https://docs.oracle.com/javase/specs/)** — Read the spec before the implementation.
- **[GraalVM](https://www.graalvm.org/latest/docs/)** — Truffle and partial evaluation: build an AST interpreter, get a JIT. A genuinely different approach.
- **[.NET runtime design docs](https://github.com/dotnet/runtime)** — `docs/design/` contains real engineering writing on RyuJIT and the GC.
- **[PyPy](https://doc.pypy.org/en/latest/)** — Meta-tracing — generating a JIT from an interpreter definition.
- **[LuaJIT](https://luajit.org/luajit.html)** — Trace compilation at its most refined.
- **[CPython developer guide](https://devguide.python.org/)** — The bytecode VM, the specializing adaptive interpreter, and the C API.


#### Type systems & programming language theory

- **[Types and Programming Languages (TAPL)](https://www.cis.upenn.edu/~bcpierce/tapl/)** — The standard text. Companion OCaml implementations are free from this page.
- **[Software Foundations](https://softwarefoundations.cis.upenn.edu/)** — Machine-checked PL theory in Coq. Free, enormous, and rigorous.
- **[PLAI — Programming Languages: Application and Interpretation](https://cs.brown.edu/courses/cs173/2012/book/)** — Free book building language features by implementing them.
- **[GHC user guide](https://downloads.haskell.org/ghc/latest/docs/users_guide/)** — Where advanced type-system features actually ship. The extensions documentation is a tour of modern type theory.
- **[OCaml](https://ocaml.org/docs)** — The practical implementation language of PL research.


#### WebAssembly in depth

- **[WebAssembly core specification](https://webassembly.github.io/spec/core/)** — Formal semantics with a reference interpreter.
- **[Wasmtime](https://github.com/bytecodealliance/wasmtime)** — The reference runtime; read it with Cranelift.
- **[Wasmer](https://docs.wasmer.io/)** — Alternative backends and a different design philosophy.
- **[WAMR](https://github.com/bytecodealliance/wasm-micro-runtime)** — Wasm on microcontrollers.


#### Research & community

- **[Cornell CS6120 — Advanced Compilers](https://www.cs.cornell.edu/courses/cs6120/2023fa/)** — Adrian Sampson's self-guided PhD course. All materials, readings and a working IR are public. Outstanding.
- **[SIGPLAN](https://www.sigplan.org/)** — The umbrella for PL conferences, with open-access policies.
- **[PLDI](https://pldi25.sigplan.org/)** — Implementation-focused.
- **[POPL](https://popl25.sigplan.org/)** — Theory-focused.
- **[WG21 papers](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/)** — Language design argued in public, at length.
- **[TC39 proposals](https://github.com/tc39/proposals)** — The same, for JavaScript, and easier to follow.


---

## If you only do three things

1. **Work through Crafting Interpreters.** Both halves. Free, and nothing else in this field comes close as an introduction.
2. **Read the rustc dev guide.** It is the best public explanation of how a modern incremental compiler is architected — useful even if you never write Rust.
3. **Do the LLVM Kaleidoscope tutorial, then the MLIR Toy tutorial.** Two weekends, and the modern compiler stack opens up.

## Honest notes

- **Read a small implementation before a large one.** Lua (~25k lines) or chibicc, then LLVM. Starting at LLVM is how people bounce off this field.
- **The Go spec and the JVM spec are short and excellent.** Most engineers have never read a language specification; these two are the easiest places to start.
- **MLIR is where the field is moving.** Nearly every new ML and hardware compiler is built on it.
- **Cornell CS6120 is designed for self-study** — public materials, a working IR, and real assignments. Rare for a graduate course.
- **LLVM IR is a lingua franca.** Learning to read `LangRef` pays off across compilers, security work and performance engineering.

---

## Related sections of this book

- [Compilers](../compilers/README.md) — the explanatory chapters this index points out from
- [Reference Libraries index](./README.md) — the other six topic indexes
