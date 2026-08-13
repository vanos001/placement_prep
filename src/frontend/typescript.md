# TypeScript for Interviews

## Type System

TypeScript adds static typing to JavaScript. Types are checked at compile time and erased at runtime.

```typescript
// Basic types
let name: string = "Alice";
let age: number = 30;
let active: boolean = true;
let items: string[] = ["a", "b"];
let tuple: [string, number] = ["Alice", 30];

// Union types
let id: string | number = "abc";
id = 123; // also valid

// Literal types
type Direction = "north" | "south" | "east" | "west";
let dir: Direction = "north";
```

## Interfaces vs Type Aliases

```typescript
// Interface — extendable, mergeable
interface User {
  name: string;
  email: string;
  age?: number;           // optional
  readonly id: number;    // read-only
}

interface Admin extends User {
  permissions: string[];
}

// Type alias — more flexible
type ID = string | number;
type Pair<T> = [T, T];
type UserOrAdmin = User | Admin;

// Key difference: interfaces can be merged/extended
interface User { nickname: string; } // merges with earlier User
```

## Generics

```typescript
// Generic function
function identity<T>(arg: T): T {
  return arg;
}

identity<string>("hello");  // explicit
identity(42);               // inferred as number

// Generic constraints
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// Generic class
class Stack<T> {
  private items: T[] = [];
  push(item: T): void { this.items.push(item); }
  pop(): T | undefined { return this.items.pop(); }
}
```

## Utility Types

```typescript
interface User {
  id: number;
  name: string;
  email: string;
  age: number;
}

Partial<User>    // { id?: number; name?: string; ... }
Required<User>   // opposite of Partial
Readonly<User>   // all properties readonly
Pick<User, "id" | "name">  // { id: number; name: string }
Omit<User, "email">        // { id: number; name: string; age: number }
Record<string, number>     // { [key: string]: number }
Exclude<"a"|"b"|"c", "a"> // "b" | "c"
Extract<"a"|"b"|"c", "a"|"d"> // "a"
NonNullable<string|null|undefined> // string
ReturnType<() => string>   // string
```

## Type Narrowing

```typescript
function process(value: string | number) {
  if (typeof value === "string") {
    // TypeScript knows value is string here
    return value.toUpperCase();
  }
  // TypeScript knows value is number here
  return value.toFixed(2);
}

// Discriminated unions
type Shape = 
  | { kind: "circle"; radius: number }
  | { kind: "rectangle"; width: number; height: number };

function area(shape: Shape): number {
  switch (shape.kind) {
    case "circle":
      return Math.PI * shape.radius ** 2;
    case "rectangle":
      return shape.width * shape.height;
  }
}
```

## Conditional Types

```typescript
type IsString<T> = T extends string ? true : false;
type A = IsString<string>;  // true
type B = IsString<number>;  // false

// Infer keyword
type ReturnType<T> = T extends (...args: any[]) => infer R ? R : never;
type Unpack<T> = T extends (infer U)[] ? U : never;
```

## Interview Questions

**Q: What is the difference between `interface` and `type`?**
A: Interfaces are extendable (declaration merging, `extends`), best for object shapes. Type aliases are more flexible (unions, intersections, primitives, tuples), best for complex types. Use interface for objects you might extend; type for everything else.

**Q: What are utility types in TypeScript?**
A: Built-in generic types that transform other types: `Partial` (all optional), `Required` (all required), `Pick` (subset of properties), `Omit` (exclude properties), `Record` (map keys to values), `Readonly` (immutable). They avoid duplicating type definitions.

**Q: How does TypeScript type narrowing work?**
A: TypeScript narrows types based on control flow: `typeof` checks, `instanceof`, `in` operator, equality checks, discriminated unions. After a narrowing check, TypeScript treats the variable as the more specific type within that code branch.

## References

- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/)
- [Type Challenges](https://github.com/type-challenges/type-challenges)
