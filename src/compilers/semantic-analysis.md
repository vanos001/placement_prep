# Semantic Analysis

Parsing ensures the program is syntactically correct. **Semantic analysis** checks that the program is *meaningful* — that variables are declared before use, types are compatible, functions are called with the right number of arguments, and so on.

## Symbol Tables

A **symbol table** maps names to their declarations and attributes. It is the central data structure for semantic analysis.

```c
typedef struct {
    char *name;
    Type *type;          // int, float, function(int) -> bool, etc.
    Kind kind;           // VAR, FUNC, PARAM, CONST
    int scope_level;
    int offset;          // stack frame offset (for codegen)
} Symbol;

// Scoping: typically a stack of hash maps
typedef struct Scope {
    HashMap *symbols;    // name -> Symbol*
    struct Scope *parent;
    int level;
} Scope;
```

**Operations**:
- `insert(scope, name, symbol)` — add a new binding (error on duplicate in same scope).
- `lookup(scope, name)` — search current scope, then parent scopes, up to global.
- `enter_scope()` / `exit_scope()` — push/pop scope stack on `{` and `}`.

Most compilers implement the symbol table as a **chain of hash maps** (one per scope), giving O(1) average lookup within a scope and O(d) for d nesting levels.

## Type Checking

Type checking verifies that operations are applied to compatible types. There are two main strategies:

| Strategy | Description | Language Examples |
---|---|---|
**Explicit typing** | Types declared by the programmer; compiler checks consistency | C, Java, Rust |
**Type inference** | Compiler deduces types from usage | Haskell, ML, Rust (with `let`), TypeScript |

### Type Compatibility Rules

```c
// Coercion: int is promoted to double in C
double x = 3;       // OK: int → double (implicit coercion)
int    y = 3.14;    // Warning: truncation, double → int

// Assignment compatibility
int a = 5;
float b = a;        // OK: widening
int c = b;          // Error/warning: narrowing

// Function call checking
int add(int, int);
add(1, 2);          // OK
add(1.0, 2);        // OK with coercion
add("hi", 2);      // Error: incompatible type
```

### Structural vs. Nominal Typing

- **Nominal** (C, Java, Rust): types are compatible only if they have the same name. `struct A { int x; }` and `struct B { int x; }` are different types.
- **Structural** (TypeScript, Go interfaces, ML): types are compatible if they have the same structure (same members). Go's interfaces are a classic example — any type with the required methods satisfies the interface implicitly.

## Type Inference

**Hindley-Milner type inference** (Algorithm W) is the standard approach for statically-typed functional languages. It works through **unification**:

```python
# Example: Haskell-like inference
# let f x = x + 1
# Step 1: x has type α (unknown)
# Step 2: (+) :: Num a => a -> a -> a, so x must be Num
# Step 3: 1 has type Num, so a is unified with the literal's type
# Result: f :: Num a => a -> a
```

In practice:
- **Rust** infers types for local variables (`let x = 42;` → `i32`) but requires annotations for function signatures and struct fields.
- **TypeScript** infers from initializers and usage context.
- **C++** has `auto` with template argument deduction (`auto x = std::vector{1, 2, 3};` → `std::vector<int>`).

## Scope Resolution

Scoping rules determine which declaration a name refers to:

| Scope Type | Rule | Example |
---|---|---|
**Lexical (static)** | Resolved at compile time based on source text nesting | C, Python, JavaScript (pre-`let`), Rust |
**Dynamic** | Resolved at runtime based on call chain | Emacs Lisp, Bash, some configurations of Python |

```c
int x = 10;              // global scope
void foo() {
    int x = 20;          // shadows global x
    { 
        int x = 30;      // shadows outer x
        // x == 30 here
    }
    // x == 20 here
}
```

**Closures** and **first-class functions** complicate lexical scoping — the captured environment must outlive the enclosing function's stack frame, requiring heap allocation of captured variables.

## Name Resolution

Name resolution is the process of binding each identifier use to its declaration. Key concerns:

- **Forward references**: In C, functions can be called before definition if declared. In Java, methods can reference classes not yet defined.
- **Overload resolution**: C++ and Java select among functions with the same name by matching argument types.
- **Two-pass analysis**: Some languages require the compiler to collect all declarations before resolving references (e.g., Java class bodies).

## References

- Dragon Book, Chapter 6: Semantic Analysis
- Pierce, *Types and Programming Languages* (TAPL)

## Interview Questions

1. **What is a symbol table and why is it needed?** It maps identifier names to their type, scope, and memory layout information. It's essential for type checking and code generation.
2. **What is the difference between lexical and dynamic scoping?** Lexical scoping resolves names based on where they appear in the source code. Dynamic scoping resolves them based on the call chain at runtime.
3. **What is type inference?** The compiler deduces the type of an expression without explicit annotation. Hindley-Milner (Algorithm W) is the classic approach, using unification of type variables.
4. **Explain nominal vs. structural typing.** Nominal: type identity is by name (Java, C). Structural: type compatibility is by shape/structure (TypeScript, Go interfaces).
5. **How does a compiler handle variable shadowing?** The symbol table is scope-aware. When entering a new scope, the same name can be inserted. Lookup walks from the current scope upward, so the innermost binding wins.