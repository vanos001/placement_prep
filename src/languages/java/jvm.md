# JVM Internals

## Overview

The Java Virtual Machine (JVM) is the runtime engine that executes Java bytecode. Understanding JVM internals is crucial for performance tuning, debugging, and senior-level interviews.

## JVM Architecture

```mermaid
flowchart TD
    SRC[".java files"] --> COMP["javac (Compiler)"]
    COMP --> BC[".class files (Bytecode)"]
    BC --> CL["Class Loader Subsystem"]
    CL --> MDA["Method Area<br/>(Class metadata)"]
    CL --> HEAP["Heap<br/>(Objects)"]
    
    subgraph "Execution Engine"
        INTERP["Interpreter"]
        JIT["JIT Compiler"]
        GC["Garbage Collector"]
    end
    
    MDA --> INTERP
    HEAP --> INTERP
    INTERP --> JIT
    JIT --> NATIVE["Native Code"]
    
    subgraph "Thread Data Areas"
        STACK["Stack<br/>(Frames)"]
        PC["PC Register"]
        NATIVE_STACK["Native Method Stack"]
    end
```

## Class Loading

### Class Loader Hierarchy

```mermaid
flowchart TD
    BOOT["Bootstrap ClassLoader<br/>(rt.jar, core Java)"]
    EXT["Extension/Platform ClassLoader<br/>(ext dirs)"]
    APP["Application ClassLoader<br/>(classpath)"]
    CUSTOM["Custom ClassLoader"]
    
    BOOT --> EXT
    EXT --> APP
    APP --> CUSTOM
```

### Class Loading Phases

1. **Loading** — Find and read `.class` file
2. **Linking**
   - **Verify** — Bytecode verification (security, type safety)
   - **Prepare** — Allocate memory for static fields, set defaults
   - **Resolve** — Convert symbolic references to direct references
3. **Initialization** — Execute static initializers and static blocks

### Delegation Model

```java
// Parent-first delegation
// 1. Check if already loaded
// 2. Delegate to parent
// 3. Try to load yourself
// This prevents loading duplicate classes
```

## Bytecode

### What is Bytecode?

```java
// Java source
public int add(int a, int b) {
    return a + b;
}
```

```
// Bytecode (javap -c)
iload_1    // Push local var 1 (a)
iload_2    // Push local var 2 (b)
iadd       // Pop two ints, push sum
ireturn    // Return int
```

### Common Bytecode Instructions

| Category | Instructions | Description |
|----------|-------------|-------------|
| **Load/Store** | iload, lload, fload, aload, istore, lstore, fstore, astore | Local variable ↔ operand stack |
| **Arithmetic** | iadd, isub, imul, idiv, irem | Integer arithmetic |
| **Comparison** | if_icmpeq, if_icmpne, if_icmplt | Integer comparison |
| **Stack** | dup, swap, pop, pop2 | Operand stack manipulation |
| **Objects** | new, getfield, putfield, invokevirtual, invokeinterface | Object operations |
| **Arrays** | newarray, aload, astore, arraylength | Array operations |
| **Control** | goto, tableswitch, lookupswitch | Branching |

## JIT Compilation

### How JIT Works

```mermaid
flowchart LR
    BC[Bytecode] --> INTERP[Interpreter<br/>First execution]
    INTERP --> PROF[Profiling<br/>Hot methods detected]
    PROF --> C1[C1 Compiler<br/>Quick optimization]
    C1 --> C2[C2 Compiler<br/>Full optimization]
    C2 --> NATIVE[Native Code<br/>10-100x faster]
```

### JIT Optimizations

| Optimization | Description |
|--------------|-------------|
| **Method inlining** | Replace call with method body |
| **Loop unrolling** | Replicate loop body to reduce overhead |
| **Escape analysis** | Allocate on stack if object doesn't escape |
| **Null check elimination** | Remove redundant null checks |
| **Bounds check elimination** | Remove redundant array bounds checks |
| **Dead code elimination** | Remove unreachable code |
| **Constant folding** | Compute constants at compile time |
| **Scalar replacement** | Break objects into primitives |

### Tiered Compilation

```
Level 0: Interpreter (no compilation)
Level 1: C1, no profiling (simple methods)
Level 2: C1, limited profiling
Level 3: C1, full profiling
Level 4: C2, full optimization (hot methods)
```

## Runtime Data Areas

### Heap Structure

```mermaid
flowchart TD
    subgraph "Heap"
        subgraph "Young Generation"
            EDEN[Eden Space<br/>New objects]
            S0[Survivor 0]
            S1[Survivor 1]
        end
        subgraph "Old Generation"
            OLD[Tenured Space<br/>Long-lived objects]
        end
    end
    
    EDEN -->|Minor GC| S0
    S0 -->|Age threshold| OLD
    OLD -->|Major GC| COLLECT[Collected]
```

### Stack Frames

Each method call creates a stack frame:

```mermaid
flowchart TD
    subgraph "Stack Frame"
        LV[Local Variables<br/>Array of slots]
        OS[Operand Stack<br/>LIFO stack]
        RT[Return Address]
        LC[Frame Data<br/>Constant pool ref]
    end
```

| Component | Description |
|-----------|-------------|
| **Local variables** | Array of slots (this, parameters, local vars) |
| **Operand stack** | LIFO stack for computation |
| **Frame data** | Return address, exception table, constant pool reference |

## String Pool

```java
// String literals are interned
String s1 = "hello";  // Stored in string pool
String s2 = "hello";  // Same reference from pool
s1 == s2;             // true (same reference)

String s3 = new String("hello"); // New object on heap
s1 == s3;                        // false (different reference)
s1.equals(s3);                   // true (same content)

// Explicit interning
String s4 = s3.intern(); // Returns pooled reference
s1 == s4;                // true
```

## Memory Management

### Object Header

```
| Mark Word (8 bytes) | Class Pointer (4 bytes) | Array Length (4 bytes, if array) |
```

Mark Word contains:
- Identity hashCode
- GC age (4 bits)
- Lock state (biased, lightweight, heavyweight)

### Escape Analysis

```java
public int calculate() {
    Point p = new Point(1, 2); // Does p escape?
    return p.x + p.y;         // No → allocate on stack
}

public Point create() {
    Point p = new Point(1, 2);
    return p; // Escapes → allocate on heap
}
```

## Garbage Collection Algorithms

### Generational GC

| Generation | Collection | Frequency |
|------------|-----------|-----------|
| **Young** | Minor GC | Frequent, fast |
| **Old** | Major/Full GC | Rare, slower |

### G1 Garbage Collector

```mermaid
flowchart TD
    subgraph "G1 Regions"
        E[Eden]
        S[Survivor]
        O[Old]
        H[Humongous<br/>> 50% region]
        FREE[Free]
    end
    
    E -->|Young GC| S
    S -->|Age| O
    O -->|Mixed GC| FREE
```

- Divides heap into equal-sized regions (1-32MB)
- Tracks live objects per region
- Collects regions with most garbage first (Garbage First)
- Target: configurable pause time (default 200ms)

### ZGC (Java 15+)

- Sub-millisecond pauses
- Concurrent marking and relocation
- Colored pointers (load barriers)
- No generational (until JDK 21)
- Good for large heaps (terabytes)

## Interview Questions

### Q: What happens when you run `java Main`?

1. JVM starts, Bootstrap ClassLoader loads core classes
2. Application ClassLoader loads `Main.class`
3. Static initializer runs
4. `main()` method invoked
5. JIT compiles hot methods
6. GC manages memory
7. JVM exits when main thread finishes

### Q: How does HashMap handle hash collisions?

```java
// Java 8+: linked list → tree (when bucket > 8 entries)
// Hash: (h = key.hashCode()) ^ (h >>> 16)
// Index: (n - 1) & hash
// Tree threshold: TREEIFY_THRESHOLD = 8
// Untreeify threshold: UNTREEIFY_THRESHOLD = 6
```

### Q: What is the difference between == and equals()?

| `==` | `.equals()` |
|------|------------|
| Reference comparison | Content comparison |
| Compares memory addresses | Compares object content |
| For primitives: value comparison | Can be overridden |

### Q: How does ConcurrentHashMap work?

- **Java 7**: Segment-based locking (16 segments)
- **Java 8**: CAS + synchronized on bins (finer granularity)
- Thread-safe without full synchronization
- `size()` is approximate (not locked)

### Q: What are the different GC roots?

1. Local variables in active stack frames
2. Static variables
3. Active Java threads
4. JNI references

## Related Topics

- [Java GC Algorithms](./gc.md) — Detailed GC comparison
- [Java Concurrency](./concurrency.md) — Threading deep dive
- [OS Memory Management](../../os/memory/) — OS-level memory concepts
- [Computer Architecture](../../arch/) — Hardware memory model
