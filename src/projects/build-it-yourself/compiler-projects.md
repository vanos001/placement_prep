# Compiler Build-It-Yourself Projects

## 1. Build a Lexer

Implement a tokenizer (lexer/scanner) for a simple language. Support identifiers, keywords (`if`, `else`, `while`, `fn`, `let`, `return`), numeric literals (integers and floats), string literals with escape sequences, operators (`+`, `-`, `*`, `/`, `==`, `!=`, `<`, `<=`), delimiters, and comments (single-line `//` and multi-line `/* */`). Implement proper error reporting with line/column numbers. Use a character-by-character DFA approach rather than regex substitution.

**Key concepts**: Lexical analysis, finite automata, lookahead, token types, error recovery (skip to next token on error), string interning for identifiers. **Complexity**: Beginner (1-2 weeks). **References**: Crafting Interpreters (Nystrom) Ch. 4, LLVM Kaleidoscope tutorial, `lex`/`flex` source for reference.

## 2. Build a Parser

Implement a recursive descent parser for an expression grammar supporting arithmetic expressions with correct precedence (using Pratt parsing or the classic expression/term/factor grammar), if/else statements, while loops, function declarations with parameters, variable bindings, and return statements. Produce an Abstract Syntax Tree (AST). Implement error recovery (synchronizing on statement boundaries after a parse error) so the parser reports multiple errors in a single run rather than stopping at the first.

**Key concepts**: Recursive descent parsing, grammar ambiguity, precedence climbing / Pratt parsing, AST node design, error recovery strategies, left recursion elimination. **Complexity**: Intermediate (2-3 weeks). **References**: Crafting Interpreters Ch. 6-8, Pratt parsing paper (Vaughan Pratt), `tree-sitter` for reference, ANTLR book.

## 3. Build an Interpreter

Build a tree-walk interpreter over your AST. Implement an environment (scope chain) that maps variable names to values, supporting lexical scoping and closures (functions that capture their defining environment). Support basic types (integers, floats, booleans, strings, null), arithmetic and comparison operators, control flow (if/else, while, for), and function calls (user-defined and built-in). Detect and report runtime errors (type mismatches, undefined variables, stack overflow from infinite recursion).

**Key concepts**: Tree-walk interpretation, environment/scope chain, lexical scoping, closures, dynamic typing, call stack management, runtime error handling. **Complexity**: Intermediate (2-3 weeks). **References**: Crafting Interpreters Ch. 8-12, Lox interpreter, Monkey interpreter (Thorsten Ball), Writing An Interpreter In Go.

## 4. Build a Bytecode VM

Compile your AST to a custom bytecode format and build a stack-based virtual machine to execute it. Design an instruction set with operations for constant loading, variable get/set, arithmetic, comparisons, jumps (conditional and unconditional), function calls, and return. Implement a value representation using tagged unions or NaN-boxing. Add a simple mark-and-sweep garbage collector that traces from the roots (stack, global environment) to collect unreachable objects.

**Key concepts**: Bytecode compilation, stack machine architecture, instruction encoding (operand types), value representation (tagged pointers, NaN-boxing), garbage collection (mark-and-sweep, tri-color marking). **Complexity**: Intermediate-Advanced (4-5 weeks). **References**: Lua VM design, CPython bytecode, Crafting Interpreters Ch. 13-27, Bob Nystrom's bytecode VM blog posts, JSC bytecode format.

## 5. Build an Optimizer

Implement an optimization pass over your AST or bytecode. Start with constant folding (evaluate constant expressions at compile time: `2 + 3` → `5`), dead code elimination (remove unreachable code after `return`, remove unused variable assignments), and constant propagation (track known constant values through assignments). Extend with inline expansion for small functions, peephole optimization over bytecode (e.g., `LOAD 0; ADD` → `INC`), and common subexpression elimination.

**Key concepts**: Constant folding, dead code elimination, constant propagation, inline expansion, peephole optimization, dataflow analysis, control flow graphs, SSA form basics. **Complexity**: Intermediate (3-4 weeks). **References**: LLVM optimization passes, Dragon Book Ch. 9, Cranelift IR optimizations, GCC `-O2` pass list.

## 6. Build a Toy JIT

Build a just-in-time compiler for a simple expression language targeting x86-64. Allocate executable memory (`mmap` with `PROT_EXEC`), emit x86-64 machine code bytes directly (or use a small assembler library), and jump to the generated code. Implement register allocation (even a simple linear scan allocator over 3-4 registers), basic instruction selection for arithmetic expressions, and function calls to built-in operations. Measure the speedup over interpretation.

**Key concepts**: Machine code generation, x86-64 calling convention (System V ABI), register allocation (linear scan), executable memory (`mmap` + `mprotect`), instruction encoding, JIT vs AOT trade-offs. **Complexity**: Advanced (4-6 weeks). **References**: LLVM JIT tutorial, libffi, JitWriter blog posts, "A lightweight JIT compiler" by Raph Levien, ykjit, Spasm JIT.

> **Interview Angle**: Compiler projects signal deep understanding of how code executes. Even if you're not interviewing for a compiler role, understanding parsing, evaluation, and code generation helps with SQL query engines, protocol parsers, configuration languages, and any system that processes structured text.