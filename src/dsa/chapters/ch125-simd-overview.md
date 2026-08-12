# Chapter 125: SIMD Overview

## Prerequisites
- CPU architecture basics
- Basic understanding of how processors execute instructions

## Interview Frequency: ★

SIMD (Single Instruction Multiple Data) is a class of parallel processing where one instruction operates on multiple data elements simultaneously. Modern CPUs include SIMD registers and instructions that can dramatically accelerate numerical and data processing tasks.

---

## 125.1 What Is SIMD?

Traditional (scalar) code processes one element at a time:

```
ADD R1, R2, R3   → R1 = R2 + R3 (one addition)
```

SIMD processes multiple elements in one instruction:

```
VADD V1, V2, V3  → V1[0..3] = V2[0..3] + V3[0..3] (four additions at once)
```

**Analogy:** If scalar code is a single lane of traffic, SIMD is a 4-lane highway — same speed limit, but 4× throughput.

---

## 125.2 SIMD Instruction Sets

| Instruction Set | Width | int32 | float32 | Introduced |
|---|---|---|---|---|
| MMX | 64-bit | 2 | 2 | 1997 |
| SSE | 128-bit | 4 | 4 | 1999 |
| SSE2 | 128-bit | 4 | 4 | 2001 |
| AVX | 256-bit | 8 | 8 | 2011 |
| AVX2 | 256-bit | 8 | 8 | 2013 |
| AVX-512 | 512-bit | 16 | 16 | 2016 |
| NEON (ARM) | 128-bit | 4 | 4 | 2011 |
| SVE (ARM) | 128-2048 bit | varies | varies | 2016 |

The **width** determines how many elements fit in one register:
- 128-bit SSE: 4 × float32 or 4 × int32
- 256-bit AVX2: 8 × float32 or 8 × int32
- 512-bit AVX-512: 16 × float32 or 16 × int32

---

## 125.3 How SIMD Works

### Registers
SIMD uses wide registers (xmm: 128-bit, ymm: 256-bit, zmm: 512-bit).

```
ymm0: [a0, a1, a2, a3, a4, a5, a6, a7]  (8 floats)
ymm1: [b0, b1, b2, b3, b4, b5, b6, b7]  (8 floats)

VADDPS ymm2, ymm0, ymm1
ymm2: [a0+b0, a1+b1, ..., a7+b7]        (8 additions in 1 instruction)
```

### Common Operations
| Operation | Description |
|---|---|
| VADDPS | Add packed single-precision floats |
| VMULPS | Multiply packed floats |
| VFMADDPS | Fused multiply-add |
| VCMPPS | Compare packed floats |
| VMAXPS / VMINPS | Element-wise max/min |
| VSHUFPS | Shuffle elements |
| VBROADCASTSS | Broadcast scalar to all lanes |

---

## 125.4 Auto-Vectorization

Modern compilers (GCC, Clang, MSVC) can automatically vectorize simple loops with `-O2` or `-O3`.

**What the compiler auto-vectorizes:**
- Simple element-wise loops (add, multiply, etc.)
- No loop-carried dependencies (except reductions)
- Contiguous memory access
- Known trip count

**What requires manual SIMD:**
- Complex data layouts (AoS → SoA conversion)
- Conditional operations (need masked operations)
- Non-contiguous memory access
- Cross-lane operations (shuffles, reductions)

### Example: Auto-Vectorized Addition

```cpp
#include <iostream>
#include <vector>

// The compiler will likely auto-vectorize this loop
void addArrays(const float* a, const float* b, float* c, int n) {
    for (int i = 0; i < n; i++)
        c[i] = a[i] + b[i];
}

int main() {
    const int N = 1000;
    std::vector<float> a(N, 1.0f), b(N, 2.0f), c(N);
    addArrays(a.data(), b.data(), c.data(), N);
    std::cout << "c[0] = " << c[0] << "\n"; // 3.0
    return 0;
}
```

Compile with: `g++ -O3 -mavx2 -o add add.cpp`

To verify vectorization: `g++ -O3 -mavx2 -ftree-vectorize -fopt-info-vec add.cpp`

---

## 125.5 Intrinsics: Manual SIMD

When auto-vectorization isn't enough, you can use compiler intrinsics — C/C++ functions that map directly to SIMD instructions.

### Example: Vectorized Dot Product with AVX2

```cpp
#include <immintrin.h>
#include <iostream>
#include <vector>

float dotProductSIMD(const float* a, const float* b, int n) {
    __m256 sum = _mm256_setzero_ps();
    int i = 0;
    
    // Process 8 floats at a time
    for (; i + 8 <= n; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        sum = _mm256_fmadd_ps(va, vb, sum);  // sum += a[i] * b[i]
    }
    
    // Horizontal sum of 8 lanes
    __m128 hi = _mm256_extractf128_ps(sum, 1);
    __m128 lo = _mm256_castps256_ps128(sum);
    __m128 s  = _mm_add_ps(lo, hi);
    s = _mm_hadd_ps(s, s);
    s = _mm_hadd_ps(s, s);
    
    float result;
    _mm_store_ss(&result, s);
    
    // Handle remaining elements
    for (; i < n; i++)
        result += a[i] * b[i];
    
    return result;
}

int main() {
    std::vector<float> a = {1, 2, 3, 4, 5, 6, 7, 8};
    std::vector<float> b = {8, 7, 6, 5, 4, 3, 2, 1};
    std::cout << "Dot product: " << dotProductSIMD(a.data(), b.data(), 8) << "\n";
    // 1*8 + 2*7 + 3*6 + 4*5 + 5*4 + 6*3 + 7*2 + 8*1 = 120
    return 0;
}
```

### Python with NumPy (uses SIMD under the hood)

```python
import numpy as np

a = np.array([1, 2, 3, 4, 5, 6, 7, 8], dtype=np.float32)
b = np.array([8, 7, 6, 5, 4, 3, 2, 1], dtype=np.float32)

# NumPy uses SIMD internally
result = np.dot(a, b)
print(f"Dot product: {result}")  # 120.0
```

### Java with Panama Vector API (Java 17+)

```java
import jdk.incubator.vector.*;

class SimdDotProduct {
    static float dotProduct(float[] a, float[] b) {
        var species = FloatVector.SPECIES_256;
        int i = 0;
        var sum = FloatVector.zero(species);
        
        for (; i + species.length() <= a.length; i += species.length()) {
            var va = FloatVector.fromArray(species, a, i);
            var vb = FloatVector.fromArray(species, b, i);
            sum = va.fma(vb, sum);  // fused multiply-add
        }
        
        float result = sum.reduceLanes(VectorOperators.ADD);
        for (; i < a.length; i++)
            result += a[i] * b[i];
        
        return result;
    }
    
    public static void main(String[] args) {
        float[] a = {1, 2, 3, 4, 5, 6, 7, 8};
        float[] b = {8, 7, 6, 5, 4, 3, 2, 1};
        System.out.println("Dot product: " + dotProduct(a, b));
    }
}
```

---

## 125.6 Performance Considerations

### Speedup Expectations

| Scenario | Expected Speedup |
|---|---|
| Simple element-wise ops (add, mul) | 2-8× (depends on width) |
| Fused multiply-add (FMA) | 4-16× (two ops in one) |
| Reductions (sum, max) | 1.5-3× (horizontal bottleneck) |
| Gather/scatter (non-contiguous) | 1-2× (memory bound) |
| Branching code | 1-2× (need masked ops) |

### Memory Alignment

SIMD works best with aligned memory:

```cpp
// Aligned allocation (32-byte for AVX)
float* a = (float*)aligned_alloc(32, n * sizeof(float));

// Aligned load (faster)
__m256 va = _mm256_load_ps(a);    // Requires 32-byte alignment

// Unaligned load (slower but works anywhere)
__m256 va = _mm256_loadu_ps(a);   // No alignment requirement
```

### Data Layout: AoS vs SoA

**Array of Structures (AoS):** Bad for SIMD
```cpp
struct Particle { float x, y, z, mass; };
Particle particles[1000]; // x,y,z,mass interleaved
```

**Structure of Arrays (SoA):** Good for SIMD
```cpp
struct Particles {
    float x[1000], y[1000], z[1000], mass[1000]; // Contiguous arrays
};
```

SoA allows loading 8 consecutive x values into one SIMD register.

---

## 125.7 Practical Example: Image Brightness Adjustment

**Scalar version:**
```cpp
void brighten_scalar(uint8_t* pixels, int n, int brightness) {
    for (int i = 0; i < n; i++) {
        int val = pixels[i] + brightness;
        pixels[i] = val > 255 ? 255 : val;
    }
}
```

**SIMD version (SSE2):**
```cpp
#include <emmintrin.h>

void brighten_simd(uint8_t* pixels, int n, int brightness) {
    __m128i vbright = _mm_set1_epi8((char)brightness);
    __m128i vmax = _mm_set1_epi8((char)255);
    
    int i = 0;
    for (; i + 16 <= n; i += 16) {
        __m128i v = _mm_loadu_si128((__m128i*)(pixels + i));
        __m128i result = _mm_adds_epu8(v, vbright); // Saturating add
        _mm_storeu_si128((__m128i*)(pixels + i), result);
    }
    
    // Scalar remainder
    for (; i < n; i++) {
        int val = pixels[i] + brightness;
        pixels[i] = val > 255 ? 255 : val;
    }
}
```

The SIMD version processes 16 pixels per iteration vs 1, giving ~10-12× speedup.

---

## 125.8 When to Use SIMD

**Good candidates:**
- Image/video processing
- Audio processing
- Matrix/vector operations in ML
- Physics simulations
- Cryptography
- Signal processing
- Database column scans

**Poor candidates:**
- Code with many branches
- Linked list traversal
- Small data sets (< 100 elements)
- I/O-bound code
- Code that's already memory-bound

---

## 125.9 SIMD in DSA Context

While SIMD isn't a data structure or algorithm itself, it accelerates many DSA operations:

| Operation | SIMD Benefit |
|---|---|
| Array summation | 4-8× faster |
| Matrix multiplication | 4-16× faster |
| String comparison | 4-16× faster |
| Sorting networks | 2-4× faster for small arrays |
| Hash computation | 2-4× faster |
| Binary search | Marginal (branch-heavy) |

---

## 125.10 Exercises

1. **Write a SIMD function** that computes the element-wise maximum of two float arrays.

2. **Benchmark** a scalar vs SIMD dot product for arrays of size 10⁶. Measure the speedup.

3. **Convert an AoS** (array of Point{x,y,z}) to SoA (separate x[], y[], z[] arrays) and compare SIMD performance.

4. **Implement a SIMD version** of the `memchr` function (find byte in memory).

5. **Explain why** a linked list traversal cannot benefit from SIMD.

---

## 125.11 Interview Questions

1. **"What is SIMD and when would you use it?"** — Single Instruction Multiple Data; use for data-parallel operations on arrays.

2. **"Why is SoA better than AoS for SIMD?"** — Contiguous data allows loading into SIMD registers without gather operations.

3. **"Can SIMD help with binary search?"** — Minimally; binary search is branch-heavy and sequential. SIMD helps with comparing multiple candidates simultaneously in some variants.

4. **"What is auto-vectorization?"** — Compiler optimization that transforms scalar loops into SIMD instructions automatically.

5. **"What's the difference between AVX2 and AVX-512?"** — Width (256 vs 512 bits), plus AVX-512 adds masked operations and more registers.

---

## 125.12 Cross-References

- **CPU Architecture:** Understanding pipelining and superscalar execution helps understand why SIMD works
- **Cache and Memory:** SIMD benefits from sequential memory access patterns (see cache optimization)
- **Parallel Computing:** SIMD is data-level parallelism; threads are task-level parallelism
- **Matrix Operations:** SIMD accelerates matrix multiplication (see Strassen's, BLAS)

---

## Summary

| Aspect | Details |
|---|---|
| What | Process multiple data elements with one instruction |
| Width | 128-bit (SSE) to 512-bit (AVX-512) |
| Speedup | 4-16× for suitable workloads |
| Best for | Array operations, image/audio, matrix math |
| Auto-vectorization | Works for simple loops with -O3 |
| Manual control | Intrinsics for complex patterns |
| Memory | Prefer aligned, contiguous, SoA layout |
| Pitfalls | Branch-heavy code, small datasets, gather/scatter |
