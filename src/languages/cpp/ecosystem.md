# C++ Ecosystem and Tooling

## Overview

C++ has a mature but historically fragmented toolchain: **CMake** is the de facto build system (~83% market share), **vcpkg/Conan** are the package managers, **GoogleTest/Catch2** the test frameworks, and libraries like **Boost, Eigen, fmt, and Qt** fill the standard library's gaps. This page is the practical map of the ecosystem for interviews and real projects. See [C++ Overview](./README.md) for the language.

## Build Systems: CMake is the Standard

| Tool | Role | Notes |
|---|---|---|
| **CMake** | Meta build system (generates Ninja/Make/VS projects) | ~83% share; `CMakeLists.txt`; `cmake --build` |
| **Ninja** | Fast low-level build backend | CMake's default generator for speed |
| **Make** | Classic build tool | Legacy; manual dependency handling |
| **Meson** | Modern alternative (Python-like) | ~5% share, growing |
| **Bazel** | Google's build tool | Fast incremental + remote cache; steep learning curve |

```cmake
cmake_minimum_required(VERSION 3.20)
project(myapp CXX)

set(CMAKE_CXX_STANDARD 20)

add_executable(myapp src/main.cpp)
target_link_libraries(myapp PRIVATE fmt::fmt)
```

**Best practice**: CMake + Ninja as the default; use **CMake Presets** for reproducible configurations and `FetchContent` for small dependencies.

## Package Managers: vcpkg vs Conan

| | **vcpkg** (Microsoft) | **Conan** (JFrog) |
|---|---|---|
| Registry | Central (vcpkg registry) | Decentralized (ConanCenter + private remotes) |
| Versioning | Baseline-based (vcpkg.json + lockfile) | Version ranges + lockfiles, graph resolution |
| CMake integration | Toolchain file (transparent) | CMakeDeps generator (explicit) |
| Custom packages | Port files | Python recipes (`conanfile.py`) |
| Cross-compilation | Triplets | Profiles |
| Best for | Quick start, Windows/VS ecosystem | Complex/large dependency graphs, private packages |

**Choose vcpkg** for simplicity and Windows/Visual Studio; **Conan** for cross-platform flexibility, binary caching at scale, and fine-grained versioning. Use **manifest + lockfiles** in both for reproducible builds.

## Testing: GoogleTest vs Catch2

| | **GoogleTest** | **Catch2** |
|---|---|---|
| Style | xUnit (TEST_F, assertions, death tests) | BDD-ish (SECTION, REQUIRE), header-only option |
| Mocks | **Built-in** (gmock) | External (trompeloeil) |
| Best for | Large projects, Google-style, mocking | Simpler/header-only projects, expressive tests |

```cpp
// GoogleTest
TEST(MathTest, Add) {
    EXPECT_EQ(add(2, 3), 5);
}
```

```cpp
// Catch2
TEST_CASE("add works") {
    REQUIRE(add(2, 3) == 5);
}
```

Both integrate with CTest (`add_test` in CMake). **Doctest** is a lighter third option.

## The Key Libraries

| Library | Role | When to use |
|---|---|---|
| **Boost** | "Second standard library": smart pointers, asio, graph, filesystem, regex, random... | Broad utility; many pieces became standard (shared_ptr, filesystem, regex) |
| **fmt** | Fast, safe string formatting (`fmt::format`) | **The** modern formatting library; basis of C++20 `std::format` |
| **Eigen** | Linear algebra (matrices, vectors) | Numerical/scientific/ML code |
| **Qt** | Full GUI framework (widgets, QML, signals/slots, networking) | Desktop/embedded GUIs |
| **{fmt}/std::format** | Formatting | Replaces printf/sstream for safety + speed |
| **Range-v3** | Ranges | Basis of C++20 ranges |
| **Abseil** | Google's utility library | Big-codebase utilities |

### fmt example

```cpp
#include <fmt/core.h>
int main() {
    fmt::print("Hello, {}! You have {} messages.\n", "world", 42);
}
```

`fmt::format` is **type-safe** (compile-time format string checking), fast, and is the reference implementation of C++20's `std::format`.

### Eigen example

```cpp
#include <Eigen/Dense>
Eigen::MatrixXd m(2, 2);
m << 1, 2, 3, 4;
auto v = m * Eigen::Vector2d(1, 1);   // vectorized, expression templates
```

## Analysis and Debugging Tools

| Tool | Role |
|---|---|
| **clang-tidy / cppcheck** | Static analysis (lints, bug patterns) |
| **clang-format** | Formatting |
| **AddressSanitizer (ASan) / UBSan / TSan** | Runtime memory/UB/race detection — `-fsanitize=address,undefined` |
| **Valgrind** | Memory debugging/profiling |
| **gdb / lldb** | Debuggers |
| **perf / gprof** | Profiling |
| **Doxygen** | Documentation generation |

Sanitizers are the single most valuable addition for finding the bugs the language lets you write (use-after-free, leaks, UB).

## Interview Questions

### Q: Why is CMake the de facto standard build system?

CMake is a **meta build system** that generates platform-native build files (Ninja/Make/Visual Studio/Xcode) from one `CMakeLists.txt`, making cross-platform builds reproducible. It has the largest ecosystem (most libraries ship CMake support), integrates with package managers (vcpkg/Conan) and IDEs, and `cmake --build` is a uniform interface. ~83% of C++ projects use it.

### Q: vcpkg vs Conan — which would you choose?

vcpkg for simplicity, quick start, and tight Windows/Visual Studio integration (toolchain-file transparency). Conan for cross-platform flexibility, fine-grained versioning with lockfiles, binary caching at scale, and private package registries. Both integrate with CMake; use manifest + lockfiles for reproducibility.

### Q: What do sanitizers catch and why are they essential in C++?

ASan catches memory errors (use-after-free, heap overflow, leaks), UBSan catches undefined behavior, TSan data races. Compile with `-fsanitize=address,undefined` in tests/CI to catch the bug classes C++ allows (raw pointers, manual memory) before they reach production — where they manifest as hard-to-debug crashes and security holes.

### Q: How does `std::format`/fmt differ from `printf`?

`printf` is type-unsafe (format string vs arguments can mismatch → UB). `std::format` (from the **fmt** library) checks the format string **at compile time**, is type-safe, and supports user-defined types — with comparable or better performance. It's the modern replacement for printf-style formatting.

### Q: What would you use Boost for today?

Boost is the "second standard library": asio (async I/O), graph, random, spirit (parsers), multiprecision, etc. Many of its components were adopted into the standard library (shared_ptr, filesystem, regex, chrono), so modern C++ often needs Boost only for the parts not yet standardized — asio (networking) being the main one until C++26 networking matures. Use Boost where it fills a real gap; prefer the standard library first.

## References

- CMake documentation — https://cmake.org/documentation/
- vcpkg — https://vcpkg.io/
- Conan — https://conan.io/
- GoogleTest — https://google.github.io/googletest/
- Catch2 — https://github.com/catchorg/Catch2
- fmt — https://fmt.dev/
- Eigen — https://eigen.tuxfamily.org/
- Boost — https://www.boost.org/
- Qt — https://www.qt.io/

## Related Topics

- [C++ Overview](./README.md) — the language
- [Memory Model](./memory-model.md) — why sanitizers matter
- [Move Semantics](./move-semantics.md) — modern C++ idioms
- [Compilation](../c/compilation.md) — the C compilation pipeline (shared with C++)
- [CMake and Builds](../c/compilation.md) — build tooling
