# Rust Procedural Macros

## Overview

Rust has two kinds of macros: **declarative** (`macro_rules!`) and **procedural**. Declarative macros are pattern-matchers over the token stream; procedural macros are ordinary Rust functions that take a `TokenStream` and return a `TokenStream`. They are compiled into a dynamic library that the compiler loads and executes at expansion time, which lets them synthesize arbitrary code — implementing traits, generating builders, embedding DSLs (`sqlx::query!`, `tokio::main`) — that declarative macros cannot.

There are three flavors:

- **Derive macros** (`#[proc_macro_derive(...)]`) — invoked by `#[derive(...)]` on a struct/enum, can add a trait impl.
- **Attribute macros** (`#[proc_macro_attribute]`) — replace or modify the annotated item.
- **Function-like macros** (`#[proc_macro]`) — invoked with `name!(...)` like declarative macros, but with full arbitrary-token-stream parsing.

This page covers the mechanics shared by all three: the `proc_macro` crate, `syn` and `quote`, hygiene, diagnostics, and a worked custom derive.

## The `proc_macro` crate

A proc-macro crate is a regular crate whose `Cargo.toml` declares:

```toml
[lib]
proc-macro = true

[dependencies]
syn = { version = "2", features = ["full", "extra-traits"] }
quote = "1"
proc-macro2 = "1"
```

The `proc_macro` crate is the *compiler-provided* API. Its two key types are `TokenStream` (an iterator over token trees) and `Span` (location/diagnostic info). The crate is special: it must only be used inside proc-macro crates, never in a normal library. That restriction is why `proc_macro2` exists — it lets you write macro-support code in normal libraries and unit-test it without the compiler.

A minimal function-like macro:

```rust
use proc_macro::TokenStream;

#[proc_macro]
pub fn answer(_input: TokenStream) -> TokenStream {
    "42".parse().unwrap()
}
```

Invoked as `let x: i32 = answer!();`. The function receives the token stream *inside* the parentheses (here, empty), and must return a token stream that becomes the macro's expansion.

## `TokenStream`, token trees, and spans

A `TokenStream` is a sequence of **token trees**. A token tree is one of:

- a `Group` (`(...)`, `[...]`, `{...}`) containing a nested `TokenStream`,
- an `Ident`,
- a `Punct` (a piece of punctuation such as `::`, `<`, `+`),
- a `Literal`.

Crucially, `TokenStream` is **not** an AST. Whitespace and comments are mostly discarded (only spans retain their positions). A macro author typically converts this stream to an AST using `syn`, manipulates it, and converts back using `quote!`.

Every token carries a `Span`. Spans drive diagnostics: when you emit an error on a span, the compiler points at the original source location the token came from. `proc_macro2::Span::call_site()` marks tokens that should resolve to the macro *call site*; `mixed_site()` provides macro-definition hygiene (see "Hygiene" below).

## `syn` — parsing Rust syntax

`syn` parses a `TokenStream` into typed structures mirroring the Rust grammar: `Item`, `ItemStruct`, `ItemFn`, `Expr`, `Stmt`, etc. The `DeriveInput` is what derive macros consume:

```rust
use proc_macro::TokenStream;
use syn::{parse_macro_input, DeriveInput, Data, Fields};

#[proc_macro_derive(Describe)]
pub fn derive_describe(input: TokenStream) -> TokenStream {
    let input = parse_macro_input!(input as DeriveInput);
    let name = &input.ident;
    let n_fields = match &input.data {
        Data::Struct(s) => match &s.fields {
            Fields::Named(named) => named.named.len(),
            Fields::Unnamed(unnamed) => unnamed.unnamed.len(),
            Fields::Unit => 0,
        },
        _ => 0,
    };
    let _ = (name, n_fields);
    TokenStream::new()
}
```

`parse_macro_input!` either parses successfully or emits a nice error and aborts. `DeriveInput` models the syntactic surface: visibility, attributes, generics, ident, and `data` (struct/enum/union).

## `quote!` — building token streams

`quote!` is a macro for building `proc_macro2::TokenStream`s using normal Rust syntax with `#var` interpolation:

```rust
use quote::quote;

let name = quote::format_ident!("describe");
let n = 3usize;
let tokens = quote! {
    impl #name for MyType {
        const FIELD_COUNT: usize = #n;
    }
};
```

`#var` works like `format!`'s `{}` — it splices `ToTokens` values. To splice an iterator, use `#(#iter)*` (with separators like `#(#iter),*`). Repetition binds across parallel iterators, all of which must have the same length.

## A custom derive macro — `Hello`

Goal: `#[derive(Hello)]` on a struct generates

```rust
impl Hello for Foo { fn hello() { println!("Hello from Foo"); } }
```

`src/lib.rs`:

```rust
use proc_macro::TokenStream;
use quote::quote;
use syn::{parse_macro_input, DeriveInput};

trait Hello {
    fn hello();
}

#[proc_macro_derive(Hello)]
pub fn derive_hello(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);
    let name = &ast.ident;

    let expanded = quote! {
        impl Hello for #name {
            fn hello() {
                println!("Hello from {}", stringify!(#name));
            }
        }
    };

    expanded.into()
}
```

`stringify!(#name)` turns the identifier into a string literal at compile time. `.into()` converts `proc_macro2::TokenStream` into `proc_macro::TokenStream`.

## Derive helper attributes

A derive can declare helper attributes that the compiler strips before the struct is seen by other derives. `serde` uses `#[serde(rename = "...")]`; `tokio` uses `#[tokio::main]` arguments. Declaration:

```rust
#[proc_macro_derive(Hello, attributes(hello_msg))]
pub fn derive_hello(input: TokenStream) -> TokenStream {
    let ast = parse_macro_input!(input as DeriveInput);

    // Look for #[hello_msg = "..."] on the struct
    let msg = ast.attrs.iter().find_map(|attr| {
        if attr.path().is_ident("hello_msg") {
            attr.parse_args::<syn::LitStr>().ok().map(|s| s.value())
        } else {
            None
        }
    }).unwrap_or_else(|| "Hello".to_string());

    let name = &ast.ident;
    let expanded = quote! {
        impl Hello for #name {
            fn hello() { println!("{}", #msg); }
        }
    };
    expanded.into()
}
```

Without `attributes(hello_msg)`, the compiler emits "unknown attribute" errors.

## Attribute macros

Attribute macros can be applied to any item (functions, structs, modules) and can completely replace the input. The signature is `fn(attr: TokenStream, item: TokenStream) -> TokenStream`. The first argument is the attribute's own argument list (everything after the name); the second is the annotated item.

A no-op attribute that wraps a function with a logging call:

```rust
use proc_macro::TokenStream;
use quote::quote;
use syn::{parse_macro_input, ItemFn};

#[proc_macro_attribute]
pub fn log_call(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let item = parse_macro_input!(item as ItemFn);
    let sig = item.sig.clone();
    let block = item.block.clone();

    let expanded = quote! {
        #sig {
            println!("entering {}", stringify!(#sig));
            #block
        }
    };
    expanded.into()
}
```

## Function-like macros

Function-like procedural macros accept any token sequence; you parse it yourself. They are the only macro form that can generate top-level items at compile time from arbitrary input — useful for DSLs like `sqlx::query!`.

```rust
use proc_macro::TokenStream;
use quote::quote;
use syn::parse::{Parse, ParseStream};
use syn::{Ident, LitStr, Token, parse_macro_input};

struct Kv { key: Ident, val: LitStr }

impl Parse for Kv {
    fn parse(input: ParseStream) -> syn::Result<Self> {
        let key: Ident = input.parse()?;
        let _: Token![=] = input.parse()?;
        let val: LitStr = input.parse()?;
        Ok(Kv { key, val })
    }
}

#[proc_macro]
pub fn make_kv(input: TokenStream) -> TokenStream {
    let kv = parse_macro_input!(input as Kv);
    let key = kv.key;
    let val = kv.val;
    (quote! { (#key, #val) }).into()
}
```

Invoked as `let pair = make_kv!(name = "Ada");`.

## How the compiler invokes proc-macros

```
+------------------+      parse       +----------+
|   source .rs     | ----------------> |   AST    |
+------------------+                   +----------+
                                            |
                                            | expand macros (iterated fixpoint)
                                            v
+------------------+      lower       +------------------+
|     MIR/HIR      | <-------------- |  expanded AST   |
+------------------+                  +------------------+
        |
        v
   codegen (LLVM IR)
```

Proc-macros run between parsing and lowering. Expansion is iterated until a fixpoint — a proc-macro's output can contain macro calls (even calls to itself), and the compiler keeps expanding until nothing changes. The compiled proc-macro crate is loaded as a `.so`/`.dll`/`dylib` and called as a function pointer from the compiler process.

## Hygiene

Hygiene controls whether an identifier in macro output refers to a name at the call site or at the definition site. Rust's hygiene is based on *syntax contexts*; each identifier carries both a span and a context, and resolution matches both.

In practical terms:

- **`Span::call_site()`** — identifier resolves in the caller's scope. Use this when the macro wants to refer to caller-provided names (`self`, fields).
- **`Span::mixed_site()`** — hybrid: identifiers introduced by the macro are definition-site, but paths starting with `::` and path prefixes resolve at the call site. This is what `macro_rules!` uses and the safest choice for most proc-macros.
- **`Span::def_site()`** — definition-only. Nightly-only and unstable.

The most famous hygiene bug: deriving `Default` for a struct whose field type happens to share a name with a binding in the caller's scope, e.g., a local `f32`. Without mixed hygiene the generated `f32::default()` could resolve to the caller's `f32` instead of the primitive type. Mixed hygiene prevents that collision.

When emitting identifier literals via `quote::format_ident!`, set the span explicitly:

```rust
use proc_macro2::Span;
use quote::{quote, format_ident};

let helper = format_ident!("__my_macro_helper", span = Span::mixed_site());
let ts = quote! { let #helper = 0; };
```

This places `__my_macro_helper` in the macro's definition-site context, so it cannot clobber a caller variable of the same name.

## Diagnostic APIs

`syn::Error` lets you return a typed error pointing at any span:

```rust
use syn::{Error, Lit};

fn validate(s: &Lit) -> syn::Result<()> {
    match s {
        Lit::Str(_) => Ok(()),
        other => Err(Error::new(other.span(), "expected a string literal")),
    }
}
```

`Error::to_compile_error()` produces a `TokenStream` that the compiler surfaces as a proper diagnostic. For multiple errors, accumulate in `Vec<Error>` and use `Error::new(span, "...").to_compile_error()` combined into one stream — or use the nightly-only `proc_macro::Diagnostic` API for richer multi-span errors.

## Common pitfalls

1. **Forgetting `proc-macro = true` in `Cargo.toml`** — the macro will fail to load with "no `proc_macro_derive` macro found".
2. **Using `proc_macro` types in a `cfg(test)` unit test** — the compiler refuses; that's what `proc_macro2` is for.
3. **Returning nothing for `#[derive]`** — silently compiles, but the user gets *no* trait impl. Always emit at least a generated impl or an `Error`.
4. **Spans from `quote!` default to call-site** — for helpers internal to the macro, switch to `mixed_site()` via `proc_macro2::Span::mixed_site()`.
5. **Recursive expansion** — a proc-macro that emits a call to itself will keep expanding until the recursion limit (default 128). Bump with `#![recursion_limit = "256"]` when deliberate.
6. **Path hygiene for external traits** — `impl serde::Serialize for Foo` may fail if `serde` isn't a direct dependency of the user's crate. Always use absolute paths: `::serde::Serialize` and require `serde` in caller dependencies.

## How `#[derive(Debug)]` works internally

The standard library's `Debug` derive is implemented in `core`'s proc-macro crate and does roughly what we did for `Hello`, except it walks every field, fetches the field's `Debug` impl via `::core::fmt::Debug::fmt`, and emits a `DebugStruct`/`DebugTuple`/`DebugSet` builder call sequence. `Clone`, `PartialEq`, etc., follow the same pattern: they are ordinary proc-macros producing `impl` blocks that delegate to field-level impls.

## Interview questions

1. **What's the difference between declarative and procedural macros?**
   Declarative (`macro_rules!`) macros are pattern-matching templates; procedural macros are Rust functions compiled into a dynamic library and executed by the compiler.

2. **What are the three kinds of proc-macros?**
   Derive (`#[proc_macro_derive]`), attribute (`#[proc_macro_attribute]`), function-like (`#[proc_macro]`).

3. **Why must a proc-macro live in its own crate?**
   The compiler builds the crate as a `.so`/`.dylib` and loads it into the compiler process. Macros can't be defined and used in the same compilation unit because of the cyclic dependency between building the macro and compiling code that uses the macro.

4. **Why use `quote!` and `syn` instead of manipulating `TokenStream` directly?**
   `TokenStream` is a flat sequence of token trees; `syn` gives typed AST nodes, and `quote!` gives string-template-like interpolation with repetition support.

5. **What is hygiene, and why does it matter?**
   Hygiene tracks which scope an identifier in macro output resolves in. Without it, a macro emitting `let x = ...` could clobber a caller's `x`, or refer to a caller-side binding in place of an intended language item.

## References

- [The Rust Reference — Macros](https://doc.rust-lang.org/reference/macros.html)
- [The Rust Reference — Procedural Macros](https://doc.rust-lang.org/reference/procedural-macros.html)
- [The Rust Reference — The `derive` attribute](https://doc.rust-lang.org/reference/attributes/derive.html)
- [syn crate documentation](https://docs.rs/syn/latest/syn/)
- [quote crate documentation](https://docs.rs/quote/latest/quote/)
- [proc_macro crate documentation](https://doc.rust-lang.org/proc_macro/index.html)
- [proc-macro2 crate documentation](https://docs.rs/proc-macro2/latest/proc_macro2/)
- [The Little Book of Rust Macros](https://veykril.github.io/tlborm/)
- [The Rust Programming Language — Macros](https://doc.rust-lang.org/book/ch19-06-macros.html)
- [dtolnay — proc-macro-workshop](https://github.com/dtolnay/proc-macro-workshop)

## See also

- [Traits](./traits.md) — How `#[derive]`d traits like `Clone`, `Debug` are defined
- [Ownership](./ownership.md) — `Clone`, `Copy` derives interact with move semantics
- [Error Handling](./error-handling.md) — `#[derive(thiserror::Error)]`
