# TypeScript Interview Questions

## Beginner

### Q1: What is TypeScript and why use it?

TypeScript is a statically-typed superset of JavaScript that compiles to plain JavaScript. It adds optional static typing, interfaces, generics, and advanced type features. The primary benefits are catching errors at compile time rather than runtime, better IDE support (autocompletion, refactoring), and self-documenting code through type annotations. TypeScript does not add runtime overhead — all type information is erased during compilation.

### Q2: What is the difference between `interface` and `type`?

Both can describe object shapes, but they differ in several ways:

| Feature | `interface` | `type` |
|---------|------------|--------|
| Declaration merging | Yes | No |
| Extends | `interface B extends A` | `type B = A & { ... }` |
| Union types | No (use type alias) | Yes |
| Primitive aliases | No | Yes (`type ID = string`)
| Computed keys | Limited | Yes |

**Interview tip:** Use interfaces for object shapes that may be extended by third parties (libraries use declaration merging). Use type aliases for unions, intersections, and utility types.

### Q3: Explain `enum` vs `const enum` vs union types.

```typescript
enum Direction { Up, Down, Left, Right }       // generates runtime JS code
const enum ConstDir { Up, Down }                  // inlined at compile time
type Dir = 'Up' | 'Down' | 'Left' | 'Right';     // zero runtime cost
```

**Interview trap:** Many teams prefer union types over enums because they produce no runtime code, work better with tree-shaking, and provide exhaustiveness checking with `never`.

### Q4: What are `any`, `unknown`, and `never`?

- `any`: Opt out of type checking entirely. The compiler allows any operation. **Avoid in production.**
- `unknown`: Type-safe `any`. You must narrow the type before using it (via `typeof`, `instanceof`, type guards).
- `never`: Represents values that never occur. Used for functions that always throw or never return, and in exhaustiveness checks.

```typescript
function exhaustiveCheck(x: never): never { throw new Error('Unhandled: ' + x); }
```

### Q5: What is type narrowing?

Type narrowing is the process of TypeScript refining a broad type into a narrower type based on control flow analysis.

```typescript
function double(value: string | number) {
  if (typeof value === 'string') {
    // value is narrowed to string
    return value.repeat(2);
  }
  // value is narrowed to number
  return value * 2;
}
```

Narrowing mechanisms: `typeof`, `instanceof`, `in`, `===`, truthiness checks, and custom type guards.

---

## Intermediate

### Q6: Explain generics with constraints.

Generics let you write reusable code that works across types while preserving type safety.

```typescript
function getLength<T extends { length: number }>(item: T): number {
  return item.length;
}
getLength('hello');     // works: string has .length
getLength([1, 2, 3]);  // works: array has .length
getLength(123);        // error: number has no .length
```

The `extends` constraint restricts which types are valid. Common patterns include `T extends Record<string, unknown>` for generic objects and `K extends keyof T` for type-safe property access.

### Q7: What are conditional types?

Conditional types select one of two types based on a condition:

```typescript
type IsString<T> = T extends string ? true : false;
type A = IsString<'hello'>;  // true
type B = IsString<42>;       // false
```

**Key built-in conditional types:**
- `T extends U ? X : Y`
- `Exclude<T, U>` — remove types from a union
- `Extract<T, U>` — extract matching types
- `ReturnType<T>` — extract return type of a function
- `NonNullable<T>` — remove `null` and `undefined`

### Q8: What are mapped types?

Mapped types transform existing types by iterating over their keys:

```typescript
type Readonly<T> = { readonly [K in keyof T]: T[K] };
type Optional<T> = { [K in keyof T]?: T[K] };
type Flags<T> = { [K in keyof T]: boolean };
```

Combined with template literal types:
```typescript
type Getter<T> = `get${Capitalize<string & keyof T>}`;
type Getters<T> = { [K in keyof T as Getter<T>]: () => T[K] };
```

### Q9: Explain utility types.

| Utility Type | Purpose | Example |
|-------------|---------|--------|
| `Partial<T>` | All properties optional | Update functions |
| `Required<T>` | All properties required | Validation |
| `Readonly<T>` | All properties readonly | Immutable state |
| `Pick<T, K>` | Subset of properties | API responses |
| `Omit<T, K>` | Exclude properties | Remove sensitive fields |
| `Record<K, V>` | Object type from keys | Dictionaries |
| `ReturnType<F>` | Return type | Function utilities |
| `Parameters<F>` | Parameter tuple | Higher-order functions |

### Q10: What is `keyof` and how is it used?

`keyof` creates a union type of all keys of a type:

```typescript
interface User { name: string; age: number; email: string; }
type UserKey = keyof User;  // 'name' | 'age' | 'email'

function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
const user: User = { name: 'Alice', age: 30, email: 'a@b.com' };
getProperty(user, 'name');  // string — type-safe
getProperty(user, 'phone'); // error: 'phone' is not assignable
```

---

## Advanced

### Q11: How does `infer` work in conditional types?

`infer` declares a type variable to be inferred within a conditional type:

```typescript
// Extract return type of a function
type MyReturnType<T> = T extends (...args: any[]) => infer R ? R : never;

// Extract element type of an array
type ElementOf<T> = T extends (infer E)[] ? E : never;

// Extract resolved type of a Promise
type Awaited<T> = T extends Promise<infer U> ? Awaited<U> : T;
```

### Q12: Explain the `satisfies` operator.

```typescript
const palette = {
  red: [255, 0, 0],
  green: '#00ff00',
  blue: [0, 0, 255],
} satisfies Record<string, string | number[]>;

// palette.green is still typed as string (not string | number[])
// But the object is validated against the broader type
```

`satisfies` validates an expression matches a type WITHOUT widening it — preserving the specific literal types while ensuring structural correctness.

### Q13: What is declaration file (.d.ts) and when do you need it?

Declaration files describe the types of JavaScript code without any implementation. Use cases:

- Providing types for untyped libraries (`@types/node`, `@types/lodash`)
- Publishing type definitions for a JavaScript library
- Ambient module declarations (`declare module 'some-lib'`)
- Global type augmentations

```typescript
// types/my-lib.d.ts
declare module 'my-lib' {
  export function transform(input: string): string[];
  export interface Config { verbose: boolean; }
}
```

### Q14: Explain discriminated unions and exhaustiveness checking.

```typescript
type Shape =
  | { kind: 'circle'; radius: number }
  | { kind: 'rectangle'; width: number; height: number }
  | { kind: 'triangle'; base: number; height: number };

function area(shape: Shape): number {
  switch (shape.kind) {
    case 'circle': return Math.PI * shape.radius ** 2;
    case 'rectangle': return shape.width * shape.height;
    case 'triangle': return 0.5 * shape.base * shape.height;
    default:
      // Compile-time guarantee all cases are handled
      const _exhaustive: never = shape;
      return _exhaustive;
  }
}
```

---

## Common Traps

1. **`enum` produces runtime code** — use union types instead for zero-cost abstractions.
2. **`any` disables all type checking** — use `unknown` if you truly need dynamic types.
3. **`== null` catches both null and undefined** — use strict equality `=== null` if you need to distinguish.
4. **Type assertions (`as`) bypass the compiler** — prefer type guards and narrowing over assertions.
5. **`interface` merging can cause unexpected behavior** — be aware when consuming third-party types.

---

## References

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/)
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)
- [Type Challenges](https://github.com/type-challenges/type-challenges)
