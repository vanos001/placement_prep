# JVM Bytecode

## The Stack Machine

The JVM is a *stack-based* abstract machine. There are no general-purpose registers visible to bytecode; instead each thread has a **frame** whose most important components are a `local_vars[]` array and an `operand_stack`. Instructions pop arguments off the operand stack, do work, and push results back. A typical instruction sequence for `int c = a + b;` is:

```
   ; assume a is in slot 1, b in slot 2, c will land in slot 3

   iload_1            ; push local 1 (a)            stack: [a]
   iload_2            ; push local 2 (b)            stack: [a, b]
   iadd               ; pop two, add, push result   stack: [a+b]
   istore_3           ; pop into local 3 (c)        stack: []
```

The operand stack has a fixed max size determined at compile time and recorded in the `Code` attribute of the method. The verifier rejects any program that would push more than `max_stack` slots at any point.

## Frames

Every method invocation creates a new frame, pushed onto the current thread's JVM stack. A frame has:

```
   ┌──────────────────────────────────────┐
   │ Local variable table                 │  indexed by slot, includes
   │   slot 0: this (for instance methods) │  `this` at slot 0, args at 1..n
   │   slot 1..n: arguments                │
   │   slot n+1..m: compiler temporaries  │
   ├──────────────────────────────────────┤
   │ Operand stack                        │  bounded by max_stack
   │   max_stack slots, top-of-stack ptr   │  in the `Code` attribute
   ├──────────────────────────────────────┤
   │ Reference to the constant pool        │  of the *current* class
   │ Frame's reference to method metadata  │  (LVT etc.)
   │ Return PC                             │  where to resume caller
   └──────────────────────────────────────┘
```

A `long` and a `double` take *two* slots in both the locals array and on the operand stack (the only types that do). Everything else is one slot — `int`, `float`, `reference`, `returnAddress`, `byte`/`short`/`char`/`boolean` are sign-extended to `int` when pushed.

## Local Variables in Detail

`javac` is responsible for assigning local variable slots. The slot for a variable may be reused once it falls out of lexical scope — that's why `javap -v` shows two distinct `LocalVariableTable` entries both pointing at slot 2 for two different local variables in adjacent scopes.

```
$ cat Hello.java
public class Hello {
    public int add(int a, int b) {
        int c = a + b;
        return c;
    }
}
$ javac Hello.java
$ javap -c -p -v Hello | sed -n '1,40p'
public int add(int, int);
  descriptor: (II)I
  flags: (0x0001) ACC_PUBLIC
  Code:
    stack=2, locals=4, args_size=3
       0: iload_1
       1: iload_2
       2: iadd
       3: istore_3
       4: iload_3
       5: ireturn
  LocalVariableTable:
    Start  Length  Slot  Name   Signature
        0      6     0  this   LHello;
        0      6     1  a      I
        0      6     2  b      I
        4      2     3  c      I
```

`args_size=3` because instance methods implicitly pass `this` as slot 0; `stack=2` is the maximum the stack holds (just before the `iadd`), and `locals=4` is the maximum slot index plus one.

## The Instruction Set

The JVM spec defines about 200 opcodes; they're mnemonic-coded in JVMS §6.5. The major categories:

```
   Prefix    Meaning                      Example
   ─────────────────────────────────────────────────────────
   (none)    type-agnostic (rare)         aconst_null, nop
   i…        int                          iload, istore, iadd, ireturn
   l…        long                         lload, lstore, ladd, lreturn
   f…        float                        fload, fstore, fadd, freturn
   d…        double                       dload, dstore, dadd, dreturn
   a…        reference                    aload, astore, areturn, athrow
   iconst_X  push small int constant      iconst_0..5, iconst_m1
   bipush    push signed byte             bipush 42
   sipush    push signed short            sipush 1000
   ldc       push from constant pool       ldc #5 (string/int/float/class)
   ldc2_w    push long/double             ldc2_w #7
   getfield  fetch object field           getfield #6 (I)
   putfield  store object field           putfield #6 (I)
   getstatic fetch static field           getstatic #3 (I)
   new       instantiate class            new #4 (Foo)
   anewarray instantiate ref array        anewarray #2 (Foo)
```

There are no `byte`/`short`/`char`/`boolean`-flavored arithmetic instructions — they're all widened to `int` and computed using `i…` instructions. The `byte`-typed array operations (`baload`, `bastore`) exist only because arrays carry their element type at runtime.

## Method Invocation

Five invoke instructions, distinguished by what kind of method they target:

```
   Instruction         Dispatch             Used for
   ───────────────────────────────────────────────────────────────
   invokestatic        static binding       private static methods
   invokespecial       static binding       <init>, private methods,
                                            super.foo() calls
   invokevirtual       dynamic, vtable      instance methods
   invokeinterface     dynamic, itable      interface methods
   invokedynamic       dynamic, call site   lambda/MethodHandle/etc.
```

- **invokevirtual**: looks up the actual class of the receiver, finds the method's slot in the vtable (`klass_vtable`), and calls it. If the class has a single-inheritance hierarchy, this is the standard virtual call.

- **invokeinterface**: the receiver is an interface type; the lookup is via an itable (interface table), which is a `(interface_id, method_id) → slot` search. The itable lookup is slower than a vtable lookup by a constant factor (one extra indirection) — HotSpot has had various optimizations to cache itable entries, including inline caches in C2.

- **invokespecial** is for constructors (`<init>`), private methods, and `super.foo()` calls — all situations where the exact target is statically known at compile time. There is no virtual dispatch.

- **invokestatic** is self-explanatory: static dispatch, no `this`.

- **invokedynamic** is the interesting one and the focus of the rest of this section.

## The Constant Pool

The constant pool is a `.class`-file-wide table of constants. Every `ldc`, `getfield`, `invokevirtual`, etc., references an index into this pool. Entries include:

- `CONSTANT_Class_info` — a class name reference (`Foo`)
- `CONSTANT_Fieldref_info` — `class + name + descriptor` (e.g. `Foo.x:I`)
- `CONSTANT_Methodref_info` — same shape, for a method
- `CONSTANT_InterfaceMethodref_info` — for an interface method
- `CONSTANT_String_info` — interned string constant
- `CONSTANT_Integer_info`, `CONSTANT_Float_info`, `CONSTANT_Long_info`, `CONSTANT_Double_info`
- `CONSTANT_NameAndType_info` — `name + descriptor` pair
- `CONSTANT_Utf8_info` — arbitrary UTF-8 string (real backing for everything)
- `CONSTANT_MethodHandle_info`, `CONSTANT_MethodType_info`, `CONSTANT_Dynamic_info`
- `CONSTANT_InvokeDynamic_info` — used by `invokedynamic`

A 16-bit index space limits the constant pool to 65534 entries; `javac` will fail with "too many constants" if a method gets too fat (often seen on big generated-code projects).

## invokedynamic and LambdaMetafactory

`invokedynamic` is the JVM's late-binding primitive. Unlike the other invoke instructions, the *target* of the call is not specified by the constant pool directly. Instead, the constant pool entry references a **bootstrap method** — a piece of Java code that gets to decide, the *first* time this call site executes, what to call.

The bootstrap method's signature is something like:

```java
public static CallSite bootstrap(
    MethodHandles.Lookup lookup,
    String invokedName,           // e.g. "apply"
    MethodType invokedType,       // e.g. (Foo)int
    ... additional static args
);
```

It returns a `CallSite` whose target is a `MethodHandle`. After the first call, the call site is linked to that handle, and subsequent calls dispatch directly (the JIT can inline across).

`LambdaMetafactory.metafactory` is the bootstrap used for every Java 8+ lambda:

```java
import java.util.*;
import java.util.function.*;

public class Lambdas {
    public static void main(String[] args) {
        List<String> xs = List.of("a", "bb", "ccc");
        xs.forEach(s -> System.out.println(s.length()));
    }
}
```

Compiling this with `javac` and looking at `Lambdas.class`:

```
$ javap -v -p Lambdas | rg 'InvokeDynamic|lambda'
  #1 = InvokeDynamic
  #0 = InvokeDynamic        0 #1         // 0 — bootstrap index 0
  bootstrap method #LAMBDA_FACTORY$metafactory(...)
  // ...

  public static void main(java.lang.String[]);
    Code:
       ...
       7: invokedynamic #3,  0       // InvokeDynamic apply
      12: invokeinterface Consume, 1   // forEach
```

What's actually happening:

1. `javac` does **not** generate an anonymous inner class for `s -> System.out.println(s.length())` (that was the pre-Java-8 strategy with inner classes — expensive in footprint).
2. Instead, `javac` emits an `invokedynamic` whose bootstrap is `LambdaMetafactory.metafactory`.
3. The factory, at runtime, builds a `MethodHandle` that calls the synthetic `lambda$main$0(String)` method that `javac` *did* generate inside the class file.
4. On first execution of the lambda call site, the bootstrap is invoked. The bootstrap typically chooses a strategy: either **light** (use the synthetic method directly) or **anonymous class loading** (define a class at runtime via `MethodHandles.Lookup.defineHiddenClass`, JEP 371).
5. The call site is then permanently linked — subsequent calls are direct, and the JIT inlines across.

The key insight: `invokedynamic` was originally added in JSR 292 to support dynamic-language runtimes on the JVM (JRuby, Groovy, etc.) — they can put their own `CallSite` implementation in to do inline caches, polymorphic inline caches, or whatever. Java 8 reused the same machinery to make lambdas cheap.

```
   ┌──────────────────────────────────────────────────────────┐
   │  Class file (compile-time)                               │
   │                                                          │
   │   constant pool:                                         │
   │     #3 = InvokeDynamic 0 #4                             │
   │                                                          │
   │   bootstrap_methods[]:                                   │
   │     #0: LambdaMetafactory.metafactory(look,             │
   │            name="apply", type="(String)V",               │
   │            implMethod = #5 (lambda$main$0),              │
   │            implMethodType = "(String)V",                 │
   │            instantiatedMethodType = "(String)V")        │
   │                                                          │
   └──────────────────────────────────────────────────────────┘
                              │
                              │ first execution
                              ▼
   ┌──────────────────────────────────────────────────────────┐
   │  Bootstrap call site                                     │
   │                                                          │
   │   1. LambdaMetafactory.metafactory(...) is called        │
   │   2. It produces a CallSite                              │
   │   3. The CallSite.target handle calls lambda$main$0      │
   │   4. (optionally via a hidden class)                     │
   │                                                          │
   └──────────────────────────────────────────────────────────┘
                              │
                              │ subsequent executions
                              ▼
        direct call via MethodHandle → lambda$main$0(String)
```

## Class File Format

The `class` file (JVMS §4) is a binary stream with this high-level layout:

```
   offset   contents
      0     magic           (0xCAFEBABE, 4 bytes)
      4     minor_version   (2 bytes)
      6     major_version   (2 bytes — see JVMS §4.1 table)
      8     constant_pool_count (2 bytes)
     10     constant_pool[]      (variable)
            access_flags (2 bytes, ACC_PUBLIC/ACC_FINAL/...)
            this_class    (2-byte index into constant pool)
            super_class   (2-byte index)
            interfaces_count (2)
            interfaces[]      (2 bytes each)
            fields_count      (2)
            fields[]          (field_info structs)
            methods_count     (2)
            methods[]         (method_info structs)
            attributes_count  (2)
            attributes[]      (Code, StackMapTable, etc.)
```

The `major_version` byte is what makes `javac --release 17` write `major_version=61` — and a JVM refuses to load a class whose `major_version` exceeds its own `major.version` of the VM (throws `UnsupportedClassVersionError`).

Each `method_info` contains a `Code` attribute, which contains:

- `max_stack`, `max_locals` — bounds used by the verifier and the frame allocation
- `code[]` — the bytecode array
- `exception_table[]` — try/catch regions as start/end PC ranges, plus the catch type
- `attributes` — including the all-important `StackMapTable` for verification

## Reading Real javap Output

For a slightly bigger example — the kind of thing interviewers pull out:

```java
public class Swap {
    public static void swap(int[] xs, int i, int j) {
        int t = xs[i];
        xs[i] = xs[j];
        xs[j] = t;
    }
}
```

```
$ javap -c -p -v Swap | sed -n '1,40p'
public static void swap(int[], int, int);
  descriptor: ([III)V
  flags: ACC_PUBLIC, ACC_STATIC
  Code:
    stack=3, locals=4, args_size=3
       0: aload_0                  ; xs
       1: iload_1                   ; i
       2: iaload                    ; xs[i]
       3: istore_3                 ; t
       4: aload_0                  ; xs
       5: iload_1                  ; i
       6: aload_0                  ; xs
       7: iload_2                  ; j
       8: iaload                   ; xs[j]
       9: iastore                  ; xs[i] = xs[j]
      10: aload_0                  ; xs
      11: iload_2                  ; j
      12: iload_3                  ; t
      13: iastore                  ; xs[j] = t
      14: return
```

Note:
- `aload_0` for an `int[]` argument — `a` stands for reference, not for the element type.
- `iaload` / `iastore` are the *array element* opcodes for int arrays; the equivalent for reference arrays is `aaload` / `aastore`.
- The operand stack reaches `max=3` at the moment of the first `iastore` (`xs`, `i`, `xs[j]` all stacked).

## Pitfalls and Common Confusions

- **`final` locals don't appear in bytecode**: the `final` keyword on local variables (the *effectively final* of lambda capture) is a source-language concept. The constant pool has no notion of "final local"; it's just slots.
- **`Integer` boxing uses `IntegerCache`**: `Integer.valueOf(127)` and `Integer.valueOf(127)` return the same object for `[-128, 127]` — a runtime implementation detail, not a bytecode one.
- **`String` concatenation post-JDK 9** uses `invokedynamic` with `StringConcatFactory` as bootstrap, replacing the `StringBuilder.append` chains that `javac` used to emit. Same idea as lambdas — push a factory at runtime, let the JIT inline.
- **`null` is `aconst_null`**: a one-byte instruction that pushes a null reference onto the stack.

## References

- JVMS Chapter 6 — The Java Virtual Machine Instruction Set: <https://docs.oracle.com/javase/specs/jvms/se22/html/jvms-6.html>
- JVMS Chapter 4 — The `class` File Format: <https://docs.oracle.com/javase/specs/jvms/se22/html/jvms-4.html>
- JVMS Chapter 5 — Loading, Linking, and Initializing: <https://docs.oracle.com/javase/specs/jvms/se22/html/jvms-5.html>
- JVMS §5.4.3.4 — Interface Method Resolution: <https://docs.oracle.com/javase/specs/jvms/se22/html/jvms-5.html#jvms-5.4.3.4>
- JEP 280 — Link-time indy for string concatenation: <https://openjdk.org/jeps/280>
- JEP 371 — Hidden Classes: <https://openjdk.org/jeps/371>
- JSR 292 — Supporting Dynamically Typed Languages on the JVM (the original `invokedynamic` spec): <https://www.jcp.org/en/jsr/detail?id=292>
- Brian Goetz — "Translation of Lambda Expressions" (how `javac` lowers lambdas to `invokedynamic`): <https://cr.openjdk.org/~briangoetz/lambda/lambda-translation.html>
- John Rose — "Bytecode workshop / HotSpot internals" notes (includes CallSite & MethodHandle details): <https://wiki.openjdk.org/display/HotSpot/MethodHandles>
- Aleksey Shipilev — "Lambdas in Java 8" with bytecode walkthrough: <https://shipilev.net/jvm/anatomy-quarks/2-bytecode-basics/>
- `javap` man page and `-v` (verbose) flag reference: <https://docs.oracle.com/en/java/javase/22/docs/specs/man/javap.html>
- The ASM tree API (handy for building/reading class files programmatically): <https://asm.ow2.io/javadoc/org/objectweb/asm/tree/ClassNode.html>
