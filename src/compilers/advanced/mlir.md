# MLIR

MLIR (Multi-Level Intermediate Representation) is a compiler infrastructure project started at Google by Chris Lattner (creator of LLVM) and others in 2018, open-sourced in 2019, and integrated into LLVM itself in 2020. MLIR is designed to make it easy to build domain-specific intermediate representations and the transformations between them, addressing a problem that LLVM alone could not: the gap between the high-level abstractions of DSLs (TensorFlow, PyTorch, ONNX, OpenAI Triton) and the low-level scalar code that LLVM IR expects. This page covers the operation/dialect model, the type system, the pass infrastructure, and how MLIR is used in production compilers for ML, hardware design, and scientific computing.

## Why MLIR Exists

LLVM IR is a scalar representation: it consists of basic blocks of instructions operating on single SSA values. This is perfect for traditional compilers (C, C++, Rust) but awkward for ML compilers:

- A single matrix multiply in TensorFlow is one operation; representing it in LLVM IR takes thousands of scalar mul/add instructions.
- Optimizations like operator fusion, layout transformation, and tiling need to see the high-level structure (e.g., "this is a reshape followed by a matmul") — they cannot operate on already-lowered scalar IR.

MLIR introduces the concept of **operations** (a single MLIR op can represent a matmul, a convolution, a loop nest, or a function call) and **dialects** (collections of related operations). A typical MLIR compiler:

1. Parses the high-level program (e.g., TF graph) into a high-level MLIR dialect (e.g., `tf` dialect).
2. Lowers through a series of dialects (`tf → linalg → affine → std → llvm`).
3. Emits LLVM IR for final code generation.

Each lowering step runs targeted passes that exploit the structure visible at that abstraction level.

## Operations and Dialects

An MLIR operation is a first-class entity. Here is a simple example from the `arith` dialect:

```mlir
// Compute c = a + b in 32-bit float
%c = arith.addf %a, %b : f32
```

The same operation in LLVM IR (after lowering) would be ~5 instructions (load, load, add, store). MLIR's higher-level op captures the intent and lets optimization passes reason about it.

A more complex example — a matmul in the `linalg` dialect:

```mlir
// C[i,j] = sum_k A[i,k] * B[k,j]
linalg.matmul ins(%a, %b : tensor<8x8xf32>, tensor<8x8xf32>)
              outs(%c : tensor<8x8xf32>)
```

The `linalg.matmul` op is a structured operation: it has named iterator types (parallel, reduction), it has explicit input/output operands, and it carries type information that survives lowering. A transformation pass can tile this:

```mlir
// After tiling to 4x4 blocks:
scf.foreach_thread (%i, %j) = (%0, %1) in (8, 8) step (4, 4) {
  %a_tile = tensor.extract_slice %a[%i, %0][4, 8][1, 1] : ...
  %b_tile = tensor.extract_slice %b[%0, %j][8, 4][1, 1] : ...
  %c_tile = tensor.extract_slice %c[%i, %j][4, 4][1, 1] : ...
  linalg.matmul ins(%a_tile, %b_tile)
                outs(%c_tile)
  }
```

The tiling pass operates on the structured `linalg.matmul` op, not on a soup of scalar instructions. After tiling, the inner `linalg.matmul` is lowered to `affine` loops, then to LLVM IR.

## The Type System

MLIR has an extensible type system. Built-in types include:

- `i32`, `i64`, `f32`, `f64` — scalars
- `tensor<8x8xf32>` — a multi-dimensional tensor with shape and element type
- `memref<8x8xf32>` — a memory reference (like a pointer to a tensor)
- `!tf.string` — a `tf`-dialect type
- `!llvm.struct<(i32, ptr<f32>)>` — an LLVM-IR-level type

Custom dialects can define their own types. The `tf` dialect defines `!tf.variant`, `!tf.string`, etc. The `gpu` dialect defines `!gpu.async_token`. The type system is intentionally permissive: dialects opt-in to type verification.

## The Pass Infrastructure

MLIR's pass infrastructure is its most powerful feature. A pass is a C++ class that walks the IR and transforms it. Passes are registered and chained:

```cpp
// In a tool like `mlir-opt` or `iree-compile`:
pm.addPass(createInlinerPass());         // inline function calls
pm.addPass(createCanonicalizerPass());   // simplify IR
pm.addPass(createLinalgFusionPass());     // fuse linalg ops
pm.addPass(createGpuKernelOutliningPass()); // extract GPU kernels
pm.addPass(createConvertLinalgToLoopsPass()); // lower linalg → affine → scf
pm.addPass(createConvertSCFToCFPass());   // lower scf → cf
pm.addPass(createConvertFuncToLLVMPass()); // lower to LLVM IR
```

Passes are scheduled by a PassManager that handles IR invalidation, dependency tracking, and parallel scheduling. The infrastructure guarantees that any pass that has run is consistent with the IR's verifier — a pass that produces invalid IR is rejected before it can corrupt the pipeline.

## Standard Dialects

The MLIR ecosystem ships with several canonical dialects:

| Dialect | Purpose | Lowered from / to |
|---------|---------|---------------------|
| `func`   | Function definitions, calls | top of stack |
| `arith`  | Arithmetic operations | lowered to `llvm` |
| `math`   | Math functions (sin, cos, sqrt) | lowered to `llvm` or libm |
| `cf`     | Control flow (branches, switches) | lowered to `llvm` |
| `scf`    | Structured Control Flow (for, while, parallel) | lowered to `cf` |
| `vector` | Vector operations (SIMD, SVE) | lowered to `llvm` |
| `tensor` | Tensor types and shape inference | lowered to `memref` |
| `memref` | Memory references | lowered to `llvm` |
| `linalg` | Linear algebra ops (matmul, conv, generic) | lowered to `affine` or `scf` |
| `affine` | Affine-loop nests (compile-time analyzable) | lowered to `cf` |
| `gpu`    | GPU kernel outlining and launch | lowered to `nvvm`/`rocdl`/`spirv` |
| `async`  | Async tasks and groups | lowered to `scf` + runtime |
| `llvm`   | LLVM IR types and ops | terminal — goes to LLVM |

Domain-specific dialects:

- `tf` (TensorFlow graphs), `tosa` (Tensor Operator Set Architecture — a portable ML ops standard), `torch` (PyTorch ops), `stablehlo` (a stable HLO variant for XLA).
- `firrtl` (hardware IR for Chisel/FIRRTL compilers), `hw` (hardware dialect).
- `affine` and `linalg` are used in scientific computing (e.g., Fortran IR for flang).

## Production Use

MLIR is the backbone of:

- **IREE** (Open Source ML compiler from Google) — takes `stablehlo` and lowers all the way to host CPU + GPU + custom accelerator code.
- **TensorFlow's XLA** — uses MLIR for graph-level optimizations before emitting HLO.
- **PyTorch's Torch-MLIR** — converts PyTorch models to MLIR for hardware targets.
- **JAX** — uses StableHLO → MLIR pipeline for TPU compilation.
- **CIRCT** (LLVM's hardware compiler infrastructure) — uses MLIR for RTL and gate-level IRs.
- **Flang** (LLVM's Fortran compiler) — uses MLIR for high-level analysis.

The Python binding `mlir-python` lets you build and transform MLIR from Python:

```python
from mlir.ir import *
from mlir.dialects import arith, func

ctx = Context()
module = Module.create()
with ctx, Location.unknown():
    with InsertionPoint(module.body):
        @func.FuncOp.from_py_func(f32, f32)
        def add(a, b):
            return arith.addf(a, b)
```

## Comparison to LLVM IR

| Aspect | MLIR | LLVM IR |
|--------|------|---------|
| Abstraction level | Multi-level (any) | Single-level (scalar) |
| Type system | Extensible (dialect-defined) | Fixed (i32, f32, struct, ...) |
| Operations | User-defined | Fixed set |
| Optimization passes | Per-dialect, targeted | Cross-cutting |
| Backend support | Lowered to LLVM IR | Direct machine code emission |
| Use cases | DSL compilers, hardware | C/C++/Rust/Swift |

LLVM IR is "the floor" — every MLIR compiler eventually lowers to LLVM IR for machine code. MLIR's value is in the layers above: it provides a structured, type-safe, extensible way to write the transformations needed to get from high-level DSLs to the floor.

## Pitfalls

1. **Treating MLIR as just "another IR".** The point of MLIR is that you define your own IRs (dialects) for your domain. A team that uses only the standard dialects (`linalg`, `affine`, etc.) without defining their own is not using MLIR's main feature.

2. **Forgetting that passes must preserve the verifier.** A pass that produces IR violating the dialect's verifier will be rejected by the PassManager. Pass authors must run `mlir-opt --verify-each` during development to catch this.

3. **Lowering too eagerly.** The temptation is to lower `linalg.matmul` to LLVM IR as fast as possible. The point of MLIR is to stay at the structured level long enough to apply transformations (tiling, fusion, layout change) that are impossible or much harder at the LLVM level.

4. **Assuming MLIR is ML-specific.** Despite the name, MLIR is a general compiler infrastructure. CIRCT (hardware), Flang (Fortran), and MLIR's use in scientific computing demonstrate this.

5. **Confusing MLIR and StableHLO.** StableHLO is a specific MLIR dialect (used by JAX/PyTorch/XLA) for portable ML graphs. MLIR is the underlying infrastructure that hosts StableHLO.

## References

- [MLIR: A Compiler Infrastructure for the End of Moore's Law](https://arxiv.org/abs/2002.11054) (arXiv 2020)
- [MLIR documentation](https://mlir.llvm.org/)
- Chris Lattner et al., "[MLIR: Scaling Compiler Infrastructure for Domain Specific Computation](https://www.computer.org/csdl/proceedings-article/2021-cgo/516500a543/1Cb4BP2PHTY%3D/10)" (CGO 2021)
- [IREE: A Compiler and Runtime for ML](https://github.com/iree-org/iree)
- [Torch-MLIR](https://github.com/llvm/torch-mlir)
- [StableHLO specification](https://github.com/openxml/stablehlo)
- [LLVM CIRCT project (hardware design)](https://www.circt.org/)
