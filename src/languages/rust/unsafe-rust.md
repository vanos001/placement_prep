# Unsafe Rust: a Deep Dive

Unsafe Rust is not a different language; it is the same language with five
additional operations the compiler refuses to verify on its own. The point
of unsafe is not to "turn off the borrow checker" — the borrow checker still
runs on every line of unsafe code. The point is to mark the points where
*you* are taking responsibility for an invariant the compiler cannot check.
This page covers the five superpowers, the safety contract you sign, how
`Send`/`Sync` interact with `unsafe impl`, the interior-mutability pattern
rooted in `UnsafeCell`, what undefined behavior means in this language, how
Miri detects it, and where unsafe shows up inside `std` itself.

## 1. The five unsafe superpowers

The Rust Reference enumerates exactly five things that are only legal inside
an `unsafe` block or `unsafe fn`:

1. **Dereference a raw pointer** (`*const T`, `*mut T`).
2. **Read or write a `static mut`** variable.
3. **Access a field of a `union`**.
4. **Call an `unsafe fn`** (including FFI).
5. **Implement an `unsafe trait`** with `unsafe impl`.

Everything else — borrows, ownership, lifetime tracking, type checking,
`Drop` ordering, the borrow checker — still applies. `unsafe` does not
unlock arbitrary mutation or let you skip the borrow rules. It does not even
let you transmute types directly; `mem::transmute` is an `unsafe fn` you
call, not an `unsafe` block primitive.

A canonical small example:

```rust
fn split_at_mut(xs: &mut [i32], mid: usize) -> (&mut [i32], &mut [i32]) {
    let len = xs.len();
    assert!(mid <= len);

    let ptr = xs.as_mut_ptr();

    // SAFETY: we assert mid <= len, and the two slices do not overlap.
    unsafe {
        (
            std::slice::from_raw_parts_mut(ptr, mid),
            std::slice::from_raw_parts_mut(ptr.add(mid), len - mid),
        )
    }
}
```

The `unsafe` block says "I have manually verified the safety precondition of
`from_raw_parts_mut` here." The borrow checker still insists that
`ptr` is a valid `*mut i32`, still checks the lifetimes of the returned
slices against `xs`, and still rejects overlapping mutable borrows at the
language level.

## 2. The safety contract

Every `unsafe` operation carries a written precondition. The Reference
calls this the "safety contract." A good `unsafe` block has a `// SAFETY:`
comment above it explaining exactly which precondition the code satisfies:

```rust
// SAFETY: `ptr` is non-null, 4-byte aligned, points to a valid `i32`,
// and the surrounding memory is not mutated for the duration of this read.
unsafe {
    let v: i32 = std::ptr::read(ptr);
}
```

Clippy has a lint (`clippy::undocumented_unsafe_blocks`) that fails on
uncommented `unsafe` blocks. The Reference's "Unsafe Code Guidelines"
project is the canonical list of these contracts.

A few important contracts:

- `std::ptr::read(ptr)` requires `ptr` be properly aligned for `T`,
  non-null, point to a validly-initialized `T`, and not be aliased in a way
  that violates the stacked-borrows / tree-borrows model.
- `std::mem::transmute<S, T>(s)` requires `sizeof::<S>() == sizeof::<T>()`
  (a compile-time check) and that the bit pattern of `s` is a valid `T`.
- `unsafe impl Send for MyType` requires that *no* `!Send` field is reachable
  from `MyType` and that no other thread can observe a violation of `Send`'s
  contract.
- `unsafe impl Sync for MyType` requires that `MyType` can be shared
  between threads by reference; equivalently, `&MyType: Send`.

## 3. Raw pointers

`*const T` and `*mut T` are the language's escape hatch for when you must
work with addresses, including FFI:

```rust
let mut x: i32 = 42;
let r1: *const i32 = &x;
let r2: *mut i32 = &mut x;

unsafe {
    println!("{}", *r1);
    *r2 = 7;
    println!("{}", *r2);
}
```

Raw pointers differ from references in:

- No lifetime tracking.
- No null prevention; `std::ptr::null()` exists.
- No aliasing guarantee. Two `*mut T` may alias the same memory; the
  compiler is free to assume they don't (strict aliasing rules in LLVM),
  which is why misusing raw pointers is the most common UB source.
- No automatic dereference; you must write `*ptr` in `unsafe`.
- They are `!Send` and `!Sync` by default — implementing `Send`/`Sync` for
  a type that wraps a raw pointer requires `unsafe impl`.

The conversion `&T as *const T` and `&mut T as *mut T` is **safe** because
it doesn't actually do anything dangerous; it just hands out the address.
The dangerous part is *using* the pointer later.

## 4. `static mut` and interior vs. exterior mutability

A `static` is a value with a fixed address and `'static` lifetime. A
`static mut` is a mutable global — and accessing it is unsafe because
the compiler cannot prove that no other thread is reading or writing it
simultaneously:

```rust
static mut COUNTER: u64 = 0;

fn bump() -> u64 {
    unsafe {
        COUNTER += 1;
        COUNTER
    }
}
```

Reading or writing `static mut` is *always* `unsafe`. The check is on the
access, not just the declaration. Note: as of Rust 1.77, `static mut` is
considered actively dangerous and the standard library pushes toward
`AtomicU64` or `std::sync::Mutex` instead — `static COUNTER: AtomicU64 =
AtomicU64::new(0)` is safe to access.

`static mut` is also subject to the strictest reading of the memory model:
two writes from two threads without synchronization is a data race, which
in Rust is *defined* as undefined behavior (see section 7).

## 5. Unions

A `union` is a C-style tagged-less sum type where every variant occupies
the same memory:

```rust
union Value {
    i: u32,
    f: f32,
}

let mut v = Value { i: 1 };
unsafe {
    println!("{}", v.i);
    // Reading v.f here is UB if the bit pattern is not a valid f32.
}
```

Reading a union field is `unsafe` because you must independently
guarantee that the bits at that location are valid for the type you're
reading as. Unions exist primarily for C FFI; safe Rust code should
almost always prefer an `enum` (which carries a discriminant) or a
`#[repr(C)]` enum.

`std::mem::ManuallyDrop<T>` is implemented with a union internally to
expose the `T` value without running its `Drop`.

## 6. `unsafe fn` and `extern`

```rust
unsafe fn raw_index(buf: *const u8, i: usize) -> u8 {
    // SAFETY: caller must ensure buf is valid for i+1 bytes
    unsafe { *buf.add(i) }
}

extern "C" {
    fn abs(x: i32) -> i32;
}

fn main() {
    let n = unsafe { abs(-5) };   // FFI is unsafe by default
}
```

`unsafe fn` declares a function whose body contains unsafe operations
*or* whose caller must satisfy a precondition. Declaring a function
`unsafe fn` does not let you write unsafe operations without an `unsafe`
block — that's the so-called `unsafe_op_in_unsafe_fn` lint, off by
default but recommended on in new code (RFC 2585, "Unsafe external
impls" / lint 71268).

`extern "C"` declares a foreign function; calling it is `unsafe`. The
`extern "C"` ABI is the most common, but Rust also supports `"system"`,
`"stdcall"`, `"aapcs"`, `"C-unwind"`, `"fastcall"`, and many more.

## 7. `unsafe trait` and `unsafe impl`

A trait can be marked `unsafe` to indicate that implementing it correctly
requires the implementer to uphold an invariant that the compiler cannot
verify:

```rust
/// # Safety
/// Implementors must ensure that no value of the implementing type
/// can be made visible to another thread in a way that violates Send.
unsafe auto trait SendStable {}

unsafe impl SendStable for MyHandle {}
```

The `unsafe` keyword on a trait means "implementing this trait is an unsafe
operation." The most prominent example in `std` is `Send` and `Sync`,
which until Rust 1.50 were proper `unsafe` traits:

```rust
pub unsafe auto trait Send {}
pub unsafe auto trait Sync {}
```

`auto` means the trait is auto-implemented: for any type `T` composed
entireally of `Send` fields, the compiler emits `impl Send for T`
automatically. To opt out, you `unsafe impl !Send for MyType` (negative
impls are still unstable; the workaround is to insert a `PhantomData<*const
()>` or `PhantomData<Rc<()>>` field, which is `!Send` and `!Sync`, making
the containing type `!Send`).

The `unsafe impl` says "I, the implementer, have manually verified that
the safety contract is satisfied." For `Send` on a struct that wraps a
raw pointer:

```rust
struct ThreadSafeHandle(*mut RawData);
// *mut is !Send, so ThreadSafeHandle is !Send by default.
// If we know the raw pointer is actually a handle to thread-safe data
// (e.g. an OS handle), we can opt in:
unsafe impl Send for ThreadSafeHandle {}
```

This is a real responsibility: if `RawData` later turns out not to be
thread-safe, a data race surfaces in `ThreadSafeHandle`'s users.

## 8. Interior mutability and `UnsafeCell`

In safe Rust, you cannot mutate through a `&T`. This is the cornerstone of
aliasing-based optimization: the compiler may assume that no `&T` aliases
a `&mut T` of the same location. But many real APIs need interior
mutability — a value that can be mutated through a shared reference. The
language's answer is `UnsafeCell<T>`:

```rust
#[repr(transparent)]
pub struct UnsafeCell<T: ?Sized> {
    value: T,
}
```

`UnsafeCell` is the *only* legal way to mutate through `&T` in Rust. The
compiler knows about it specifically — it disables the aliasing-based
optimization for `UnsafeCell`-wrapped memory. `Cell<T>`, `RefCell<T>`,
`Mutex<T>`, `RwLock<T>`, `AtomicUsize`, and friends are all built on top
of `UnsafeCell`:

- `Cell<T>` — for `T: Copy`, swaps the value atomically with no borrow
  tracking; runtime-free.
- `RefCell<T>` — runtime borrow tracking via a counter; panics or returns
  `Err` on double-borrow.
- `Mutex<T>` and `RwLock<T>` — OS-level synchronization for shared
  mutation across threads.
- `AtomicU32` and friends — single-word lock-free atomics.

The pattern is: *the safe wrapper enforces the safety invariant using
runtime checks*, and the underlying mutation goes through `UnsafeCell` so
the compiler doesn't assume immutability.

```rust
struct Cell<T: Copy> {
    value: UnsafeCell<T>,
}

impl<T: Copy> Cell<T> {
    pub fn get(&self) -> T {
        // SAFETY: T is Copy; no &mut T is ever exposed.
        unsafe { *self.value.get() }
    }
    pub fn set(&self, v: T) {
        // SAFETY: &self is shared, but UnsafeCell permits the write.
        // T: Copy so we don't run a destructor on the old value.
        unsafe { *self.value.get() = v; }
    }
}
```

`UnsafeCell` is `!Sync` by default (because raw shared mutability is not
thread-safe); the safe wrappers either keep `!Sync` (`Cell`, `RefCell`)
or restore `Sync` with their own synchronization (`Mutex`, `RwLock`,
`AtomicU32` — the latter two restore `Sync` via `unsafe impl Sync`).

## 9. Undefined behavior in Rust

Undefined behavior (UB) is the contract Rust draws around what programs are
allowed to do. The Reference lists the actions that cause UB:

- **Data races.** Concurrent reads + writes or writes + writes to the
  same location without synchronization.
- **Dangling references / pointer dereferences** of unallocated or
  deallocated memory.
- **Unaligned access** (`*ptr` of `T` when `ptr` is not aligned to
  `align_of::<T>()`).
- **Out-of-bounds** array/slice indexing.
- **Reading an uninitialized `u8`** (or any uninitialized memory).
- **Invalid values for a type**: `bool` that is not 0 or 1, `char` that is
  not a valid scalar value, a `NonNull<T>` that is null, an enum that has
  an out-of-range discriminant.
- **Aliasing `&mut T` and any other reference** (Stacked Borrows / Tree
  Borrows model, the precise aliasing model is still being pinned down).
- **Returning from a non-`extern "C"` function called via a thunk of the
  wrong ABI.**
- **Violating `unsafe trait`'s safety contract.**

Critically: **a UB program may do anything** — the compiler is free to
delete branches that contain UB, hoist code across it, and silently
miscompile. This is the same standard as C/C++ UB, and it is why "unsafe
code that runs fine" is not the same as "correct unsafe code." It may run
fine today, on this compiler version, with this optimization level, and
break tomorrow.

## 10. Miri

Miri is the standard tool for catching UB in unsafe code. It is an
interpreter for the MIR (Mid-level IR) of Rust programs, built into
rustc as an experimental component. Miri does not optimize, so it can
insert invariant checks at every unsafe operation:

```bash
$ rustup component add miri
$ cargo +nightly miri test
$ MIRIFLAGS="-Zmiri-track-raw-pointers" cargo +nightly miri run
```

Miri checks:

- Aliasing violations (Stacked Borrows by default, Tree Borrows under
  `-Zmiri-tree-borrows`).
- Out-of-bounds reads and writes.
- Unaligned access.
- Use of uninitialized memory (returning a `MemChecked` flag on every
  byte).
- Data races (it can run multi-threaded code under `-Zmiri-many-seeds`
  for partial race detection).
- Leaks and stack-overflow conditions.

Miri is sound: if it reports a UB, there is UB. It is incomplete: it does
not catch every UB, particularly in code paths not exercised by the test
suite, and it cannot reason about kernel-level synchronization. Treat
Miri as a strong partial oracle, not a proof.

The recommended workflow:

```
cargo +nightly miri test            # every test passes Miri
MIRIFLAGS="-Zmiri-track-raw-pointers" cargo +nightly miri test
```

The `-Zmiri-track-raw-pointers` flag enables stricter aliasing checks for
raw pointers (the default is more permissive for backwards compat).

## 11. Production use of `unsafe`

`std` itself is full of `unsafe`. A few highlights:

- `std::collections::VecDeque` and `Vec<T>` use raw pointers and
  `MaybeUninit<T>` for the backing buffer; their `push`/`pop`/index impls
  are heavily commented `unsafe` blocks with precise SAFETY
  preconditions.
- `Mutex<T>` is `unsafe` internally and uses OS-level futexes (Linux) or
  `pthread_mutex_t`. The safe wrapper exposes a `MutexGuard` whose `Drop`
  releases the lock.
- `Box<T>`, `Rc<T>`, `Arc<T>` all use `unsafe` to manage their refcount
  and drop ordering.
- `std::sync::atomic::*` are wrappers around `AtomicU8`/`AtomicU32`/...
  which are wrappers around `core::intrinsics::atomic_*` LLVM intrinsics
  accessed via `unsafe`.
- `MaybeUninit<T>` is the standard escape hatch for uninitialized memory
  in safe code; it uses `unsafe` under the hood.
- `std::thread::spawn` is `unsafe` internally because it must transfer
  `Send`/`Sync` guarantees into the OS thread spawn primitive.

A reasonable figure: roughly 5-10% of the `std` source is `unsafe` code,
concentrated in collections, sync primitives, and FFI.

## 12. Comparison to C

C has no concept of "safe subset" vs. "unsafe subset" — *all* of C is what
Rust calls unsafe. Every pointer dereference is `*ptr`, every static is
`static mut`, every FFI call is just a function call. Rust's contribution
is:

- A *default-safe* language in which `unsafe` is a marked minority of the
  code.
- A *named contract* for each unsafe operation, auditable by lint and review.
- A *runtime UB detector* (Miri) for the unsafe subset that the compiler
  can't statically prove.
- A *library ecosystem* (`Vec`, `Mutex`, `Arc`, `Rc`, `RefCell`,
  `AtomicU*`) that contains unsafe internally but exposes safe APIs.

The mental model: Rust is C with `unsafe` blocks being the C subset, and
the rest being statically checked by an aggressive type and lifetime
system. The goal is *fewer* unsafe lines, not *no* unsafe lines — and each
unsafe line should have a SAFETY comment justifying it.

## 13. When to reach for `unsafe`

Practical guidelines for when to write `unsafe` in production Rust:

- **FFI** — necessary, no alternative.
- **Performance-critical code that beats the safe variant** — only after
  profiling, and with a benchmark to prove the win.
- **Implementing safe abstractions** — `Vec`, `Mutex`, `Arc`, custom
  lock-free data structures.
- **Embedded / `no_std`** — sometimes the only way to talk to hardware.
- **Reusing existing C libraries** via `bindgen`.

When *not* to reach for `unsafe`:

- Avoiding a borrow-checker error. The error usually indicates a design
  flaw; refactor with `Arc`, channels, or a different ownership split.
- Micro-optimizations the compiler can do for you. The optimizer is good
  at inlining, vectorizing, and removing bounds checks when it can prove
  them.
- Anything you can do with `Cell`/`RefCell`/`Mutex`/`Atomic*`. These are
  pre-checked safe wrappers.

## References

- The Rust Reference, "Unsafe Code" — https://doc.rust-lang.org/reference/unsafe.html
- The Rustonomicon — https://doc.rust-lang.org/nomicon/
- Rust RFC 2585 — `unsafe_op_in_unsafe_fn` — https://rust-lang.github.io/rfcs/2585-unsafe-block-in-unsafe-fn.html
- Miri documentation — https://github.com/rust-lang/miri/
- Miri book — https://rust-lang.github.io/miri/
- Ralf Jung's blog — https://www.ralfj.de/blog/
- Stacked Borrows paper (Jung et al.) — https://plv.mpi-sws.org/rustbelt/stacked-borrows/
- Tree Borrows specification — https://perso.crans.org/monasse/tree-borrows/
- `UnsafeCell` API reference — https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html
- Unsafe Code Guidelines reference — https://rust-lang.github.io/unsafe-code-guidelines/
- Jon Gjengset, "Rust Atomics and Locks" — book on safe wrappers around unsafe primitives — https://marabos.nl/atomics/
