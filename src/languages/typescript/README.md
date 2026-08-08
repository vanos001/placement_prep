# TypeScript

## Overview

TypeScript is a **typed superset of JavaScript** developed by Microsoft (lead architect Anders Hejlsberg, first released 2012). It adds a **static type system** on top of JavaScript: you write `.ts` files with type annotations, and the TypeScript compiler (`tsc`) type-checks and **erases** the types, emitting plain JavaScript that runs anywhere JS runs.

> "TypeScript is JavaScript with syntax for types." — TypeScript Handbook

TypeScript does **not** change how the code runs — types are compile-time only. Its value: earlier error detection, self-documenting code, safer refactoring, and editor tooling (autocomplete, go-to-definition) powered by the type checker.

## Why TypeScript Matters

- **Dominant in the ecosystem**: React, Next.js, Angular, NestJS, and most major libraries ship types or are written in TS.
- **Enterprise adoption**: large codebases stay maintainable; teams rename/refactor with confidence.
- **The "superset" guarantee**: any valid JS is valid TS (with `allowJs`/`checkJs`, plain JS files are checked too).
- **Compiler performance story**: the **Go-native rewrite** (TypeScript 7, GA July 2026) makes full builds ~8–12× faster (10.6 s vs 125.7 s for VS Code's codebase), removing the "too slow for big repos" objection.

## The Type System

### Primitives and basics

```typescript
let count: number = 5;
const name: string = "Ada";
let isDone: boolean = false;
let anything: any = "whatever";        // opt-out of checking — avoid
let maybe: unknown = JSON.parse(x);    // safe unknown — must narrow before use
let nothing: void = undefined;
let n: null = null;
let u: undefined = undefined;
```

### Structural typing (the key idea)

TypeScript is **structurally typed**: two types are compatible if their *shapes* match, not because of a shared name/class hierarchy. This mirrors how JavaScript actually works (duck typing) while adding safety.

```typescript
interface Point { x: number; y: number; }
function draw(p: Point) { /* ... */ }

// Any object with x and y is a Point — no class relationship needed
draw({ x: 0, y: 0 });
const other = { x: 1, y: 2, z: 3 };  // extra properties OK (variable, not literal)
draw(other);
```

This differs fundamentally from **nominal** typing (Java/C#) — the interview-relevant distinction.

### Interfaces vs type aliases

| | `interface` | `type` |
|---|---|---|
| Declaration merging | ✅ (can extend) | ❌ |
| Primitives/unions/tuples | ❌ | ✅ |
| Mapped/conditional types | ❌ | ✅ |
| When to use | Object shapes, library API contracts | Unions, tuples, complex transformations |

Modern guidance: prefer `interface` for object shapes you expect to extend; `type` for everything else.

### Literal types and unions

```typescript
type Direction = "north" | "south" | "east" | "west";   // string literal union
type Status = "idle" | "loading" | "success" | "error";
type Result = { ok: true; data: string } | { ok: false; error: Error };  // discriminated union
```

**Discriminated unions** (a common `kind`/`type` discriminant field) are the backbone of modeling state machines, API responses, and Redux actions.

## Generics

```typescript
function identity<T>(arg: T): T { return arg; }

interface Box<T> { value: T; }
const b: Box<number> = { value: 42 };

// Constraints
function longest<T extends { length: number }>(a: T, b: T): T {
  return a.length >= b.length ? a : b;
}
```

Generics capture **relationships between types** (input type → output type) rather than fixing a concrete type. Interview topics: generic constraints, default type params, `keyof`, and conditional types.

## Advanced Types (interview gold)

```typescript
type Keys = keyof { a: 1, b: 2 };            // "a" | "b"
type Readonly<T> = { readonly [P in keyof T]: T[P] };  // mapped type
type Partial<T> = { [P in keyof T]?: T[P] };
type Pick<T, K extends keyof T> = { [P in K]: T[P] };
type Exclude<T, U> = T extends U ? never : T;  // conditional type
type Return<T> = T extends (...args: any[]) => infer R ? R : never;  // infer
```

**Utility types** built into the stdlib: `Partial`, `Required`, `Readonly`, `Pick`, `Omit`, `Record`, `Exclude`, `Extract`, `NonNullable`, `Parameters`, `ReturnType`, `Awaited`.

**Narrowing** — TypeScript narrows unions through checks:

```typescript
function format(value: string | number) {
  if (typeof value === "string") return value.toUpperCase();   // narrowed to string
  return value.toFixed(2);                                     // narrowed to number
}
```

`typeof`, `instanceof`, `in`, discriminated-union checks, and type predicates (`value is T`) all narrow.

## tsconfig.json Essentials

| Option | Meaning |
|---|---|
| `strict: true` | Master switch: `strictNullChecks`, `noImplicitAny`, `strictFunctionTypes`, etc. |
| `target` | JS version emitted (ES2022, ES2023, ...) |
| `module` | Module system (commonjs, esnext, nodenext) |
| `moduleResolution` | How imports resolve (bundler, node16, nodenext) |
| `outDir` / `rootDir` | Emit layout |
| `noEmit` | Type-check only (common in CI and with bundlers) |
| `declaration` | Emit `.d.ts` type declarations for library consumers |
| `isolatedModules` | Safe for single-file transpilers (esbuild, Babel, SWC) |

**`strict` mode is the default recommendation** — it's where TypeScript's value lives (`strictNullChecks` alone catches a huge class of bugs).

## Runtime: How Types Are Removed

Modern pipelines rarely run `tsc` for transpilation alone:

| Tool | Role |
|---|---|
| **`tsc`** | Type-check + emit (the reference implementation) |
| **esbuild / SWC** | Blazing-fast **type-stripping** transpilers (no type-check) — used by Vite, Next.js, tsup |
| **ts-node / tsx** | Run TS directly in Node (tsx uses esbuild) |
| **Babel** | Transpile via `@babel/preset-typescript` |

TypeScript 5.8+/Node 22+ also supports **type stripping natively** (`--experimental-strip-types`), and Node 24 has stable type-stripping support — meaning many `.ts` files run in Node with zero build step. (Type checking still requires `tsc`.)

## TypeScript vs JavaScript (interview framing)

| Aspect | JavaScript | TypeScript |
|---|---|---|
| Types | Dynamic, checked at runtime | Static, checked at compile time |
| Runtime | Runs directly | Types erased → runs as JS |
| Errors | Surface at runtime | Many caught before runtime |
| Tooling | Limited by dynamic types | Rich (refactor, autocomplete) |
| Learning curve | Lower | Higher (type system) |

## Interview Questions

### Q: What is structural typing and how does it differ from nominal typing?

Structural typing (TypeScript, Go, OCaml's structural aspects) checks compatibility by **shape**: an object is a `Point` if it has the same members, regardless of class hierarchy. Nominal typing (Java, C#, Rust) requires an explicit name/type relationship (inheritance or interface implementation). TypeScript chose structural typing because JavaScript is duck-typed — the type system models the actual runtime behavior.

### Q: What is the difference between `interface` and `type`?

`interface` supports declaration merging and is intended for object shapes and extensible API contracts. `type` aliases can express unions, tuples, primitives, and mapped/conditional types that interfaces cannot. Both are structural. Prefer `interface` for shapes, `type` for transformations/unions.

### Q: How do discriminated unions help model state?

A discriminated union is a union of object types distinguished by a shared literal field (e.g., `kind`). With a `switch` (or `if`) on that field, TypeScript narrows each case to the specific variant — so the compiler guarantees you handle every case and the properties you access exist. This models async states (`idle | loading | success | error`), API results, and UI events safely.

### Q: What did the TypeScript 7 rewrite change?

TypeScript 7 (GA July 2026) replaced the JavaScript-based compiler with a **native Go port** — a port, not a rewrite, preserving behavior — giving ~8–12× faster full builds via native code and shared-memory parallelism. It is the same `tsc`, same output, same strict-mode defaults (with some 6.0 deprecations becoming hard errors); the stable programmatic API for tooling lands in 7.1.

### Q: How do you type an API response that could be an error?

Use a discriminated union:

```typescript
type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; message: string };

async function fetchUser(id: number): Promise<ApiResult<User>> { /* ... */ }

const res = await fetchUser(1);
if (res.ok) console.log(res.data.name);   // narrowed — safe
else console.error(res.status, res.message);
```

## References

- TypeScript Handbook — https://www.typescriptlang.org/docs/
- TypeScript GitHub — https://github.com/microsoft/TypeScript
- TypeScript blog: *A 10x Faster TypeScript* (native port announcement, March 2025) — https://devblogs.microsoft.com/typescript/a-10x-faster-typescript/
- TypeScript blog: *TypeScript 7* (GA, July 2026) — https://devblogs.microsoft.com/typescript/
- tsconfig reference — https://www.typescriptlang.org/tsconfig/

## Related Topics

- [JavaScript Overview](../javascript/README.md) — the language TypeScript supersets
- [V8 Engine](../javascript/v8.md) — how the emitted JS runs
- [Node.js](../javascript/nodejs.md) — running TypeScript server-side
- [React](../../frameworks/react/README.md) — TS is the default for React apps
- [FastAPI](../../frameworks/fastapi/README.md) — Pydantic (Python) shares the "annotations → validation" idea
- [OCaml](../ocaml/README.md) — strong static type systems beyond the JS world
