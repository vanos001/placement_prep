# CMake — Cross-Platform Build System Generator

## Introduction

CMake is the de facto standard build system generator for C and C++ projects. Unlike
Make, which directly builds targets, CMake generates native build scripts (Makefiles,
Ninja files, Visual Studio projects, Xcode projects) from a platform-independent
description. CMake handles compiler detection, dependency finding, cross-compilation,
testing (CTest), and packaging (CPack) in a unified framework.

CMake was created in 2000 by Kitware for the ITK medical imaging project. Today it's
used by the Linux kernel (optionally), LLVM/Clang, KDE, OpenCV, Boost, and thousands
of other projects. Modern CMake (3.x+) emphasizes target-based design with proper
dependency propagation.

## Architecture

```
┌───────────────────────────────────────────────────────┐
│                    CMakeLists.txt                       │
│                 (source description)                    │
└──────────────────────┬────────────────────────────────┘
                       │
                ┌──────▼──────┐
                │    CMake     │
                │  (configure) │
                └──────┬──────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌──────────┐
   │Makefiles│   │  Ninja  │   │ Visual   │
   │         │   │  files  │   │ Studio   │
   └────┬────┘   └────┬────┘   └────┬─────┘
        │              │             │
        └──────────────┼─────────────┘
                       ▼
              ┌──────────────┐
              │   Build      │
              │  (make/ninja)│
              └──────────────┘
```

### CMake Workflow

```bash
# Configure step (generate build system)
mkdir build && cd build
cmake ..

# Build step (compile)
cmake --build .

# Or equivalently:
make -j$(nproc)       # If Makefiles generator
ninja                 # If Ninja generator

# Test
ctest

# Install
cmake --install . --prefix=/usr/local
```

## CMakeLists.txt Basics

### Minimal Project

```cmake
cmake_minimum_required(VERSION 3.16)
project(myproject VERSION 1.0 LANGUAGES C)

add_executable(myprogram main.c utils.c)
target_compile_options(myprogram PRIVATE -Wall -Wextra)
target_link_libraries(myprogram PRIVATE m pthread)
```

### Complete Project

```cmake
cmake_minimum_required(VERSION 3.20)

project(myproject
    VERSION 2.1.0
    DESCRIPTION "A sample project"
    LANGUAGES C CXX
    HOMEPAGE_URL "https://example.com"
)

# C/C++ standards
set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Build type
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Options
option(BUILD_TESTS "Build tests" ON)
option(BUILD_SHARED_LIBS "Build shared libraries" OFF)
option(ENABLE_ASAN "Enable AddressSanitizer" OFF)

# Compiler flags
add_compile_options(-Wall -Wextra -Wpedantic)

# Sanitizer
if(ENABLE_ASAN)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
endif()

# Library
add_library(mylib STATIC
    src/utils.c
    src/parser.c
    src/network.c
)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(mylib
    PUBLIC
        Threads::Threads
    PRIVATE
        m
)

# Executable
add_executable(myprogram src/main.c)

target_link_libraries(myprogram
    PRIVATE
        mylib
)

# Tests
if(BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Install
install(TARGETS myprogram mylib
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

install(DIRECTORY include/
    DESTINATION include
    FILES_MATCHING PATTERN "*.h"
)
```

## Targets

Modern CMake is target-centric. Each target carries its own compile options,
include directories, and link dependencies.

### Target Types

```cmake
# Executable
add_executable(myprogram main.c)

# Static library
add_library(mylib STATIC src/utils.c)

# Shared library
add_library(mylib SHARED src/utils.c)

# Object library (no archive, just object files)
add_library(myobj OBJECT src/utils.c)

# Interface library (header-only)
add_library(myheader INTERFACE)

# Module library (plugin)
add_library(myplugin MODULE src/plugin.c)

# Alias
add_library(MyProject::mylib ALIAS mylib)
```

### Target Properties

```cmake
# Compile options (per-target)
target_compile_options(mylib PRIVATE -Wall -Wextra)
target_compile_options(mylib PUBLIC -fPIC)
target_compile_options(mylib INTERFACE -std=c17)

# Compile definitions
target_compile_definitions(mylib
    PUBLIC  VERSION="1.0"
    PRIVATE DEBUG_MODE=1
)

# Include directories
target_include_directories(mylib
    PUBLIC  ${CMAKE_CURRENT_SOURCE_DIR}/include
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Link libraries
target_link_libraries(mylib
    PUBLIC  Threads::Threads
    PRIVATE m
)

# Link options
target_link_options(mylib PRIVATE -Wl,--as-needed)

# Sources (add after target creation)
target_sources(mylib PRIVATE src/extra.c)
```

### Visibility (PRIVATE/PUBLIC/INTERFACE)

```
┌──────────────────────────────────────────────┐
│          Visibility Propagation               │
│                                               │
│  PRIVATE   → Only this target                 │
│  PUBLIC    → This target + consumers          │
│  INTERFACE → Only consumers (header-only lib) │
│                                               │
│  Example:                                     │
│  mylib uses -fPIC (PRIVATE)                   │
│  mylib exposes headers in include/ (PUBLIC)   │
│  myprogram links mylib                        │
│    → myprogram sees include/ headers          │
│    → myprogram does NOT see -fPIC             │
└──────────────────────────────────────────────┘
```

## find_package

CMake's `find_package` locates external libraries and creates imported targets.

### Config Mode

```cmake
# Modern config-mode (preferred)
find_package(OpenCV 4.5 REQUIRED)
find_package(Eigen3 3.3 REQUIRED NO_MODULE)
find_package(Boost 1.70 REQUIRED COMPONENTS filesystem system)

# Use imported targets
target_link_libraries(myprogram
    PRIVATE
        opencv_core
        opencv_imgproc
        Eigen3::Eigen
        Boost::filesystem
        Boost::system
)
```

### Module Mode

```cmake
# Module-mode (legacy, uses FindXXX.cmake)
find_package(ZLIB REQUIRED)
find_package(OpenSSL REQUIRED)

# Use variables (older style)
target_include_directories(myprogram PRIVATE ${ZLIB_INCLUDE_DIRS})
target_link_libraries(myprogram PRIVATE ${ZLIB_LIBRARIES})

# Better: use imported targets (if available)
target_link_libraries(myprogram PRIVATE ZLIB::ZLIB OpenSSL::SSL OpenSSL::Crypto)
```

### Finding Packages

```bash
# Show package info
cmake --find-package -DNAME=OpenCV -DCOMPILER_ID=GNU -DLANGUAGE=CXX -DMODE=EXIST

# Show all found packages
cmake -LAH build/ 2>&1 | grep "Found"

# Check if package was found
cmake -DPRINT_HELP=ON ..
```

### pkg-config Integration

```cmake
# Use pkg-config for libraries without CMake support
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBSSH2 REQUIRED libssh2)

target_include_directories(myprogram PRIVATE ${LIBSSH2_INCLUDE_DIRS})
target_link_libraries(myprogram PRIVATE ${LIBSSH2_LIBRARIES})
target_compile_options(myprogram PRIVATE ${LIBSSH2_CFLAGS_OTHER})
```

### Writing a Find Module

```cmake
# cmake/FindMyLib.cmake
find_path(MYLIB_INCLUDE_DIR
    NAMES mylib.h
    PATHS /usr/local/include /usr/include
)

find_library(MYLIB_LIBRARY
    NAMES mylib
    PATHS /usr/local/lib /usr/lib
)

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(MyLib
    DEFAULT_MSG
    MYLIB_LIBRARY
    MYLIB_INCLUDE_DIR
)

if(MyLib_FOUND AND NOT TARGET MyLib::MyLib)
    add_library(MyLib::MyLib UNKNOWN IMPORTED)
    set_target_properties(MyLib::MyLib PROPERTIES
        IMPORTED_LOCATION "${MYLIB_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${MYLIB_INCLUDE_DIR}"
    )
endif()

mark_as_advanced(MYLIB_INCLUDE_DIR MYLIB_LIBRARY)
```

## Generators

CMake supports multiple build system generators:

```bash
# List available generators
cmake --help

# Use Ninja (recommended, faster than Make)
cmake -G Ninja -B build

# Use Unix Makefiles (default on Linux)
cmake -G "Unix Makefiles" -B build

# Use Make with specific version
cmake -G "Unix Makefiles" -B build

# Multi-config generators (Visual Studio, Ninja Multi-Config)
cmake -G "Ninja Multi-Config" -B build
cmake --build build --config Release
cmake --build build --config Debug

# Single-config generators (Make, Ninja)
cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -B build
cmake --build build
```

### Ninja vs Make

| Feature | Make | Ninja |
|---------|------|-------|
| Speed | Good | 2-10x faster |
| Parallel | -j N | Default parallel |
| Dependency tracking | Limited | Built-in |
| Output | Verbose | Minimal |
| Debugging | Easy | Harder |
| Use case | Interactive | CI/build farms |

## CMake Variables

```bash
# Set on command line
cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/usr/local \
      -DBUILD_TESTS=ON \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++ \
      ..

# Set in CMakeLists.txt
set(MY_VAR "value")
set(MY_LIST "a;b;c")

# Environment variables
set(ENV{PATH} "/usr/local/bin:$ENV{PATH}")

# Cache variables
set(MY_CACHE_VAR "value" CACHE STRING "Description")
set(MY_CACHE_VAR "value" CACHE PATH "Directory path")
set(MY_CACHE_VAR ON CACHE BOOL "Enable feature")

# CMake standard variables
# CMAKE_SOURCE_DIR      — Top-level source directory
# CMAKE_BINARY_DIR      — Top-level build directory
# CMAKE_CURRENT_SOURCE_DIR — Current source directory
# CMAKE_CURRENT_BINARY_DIR — Current build directory
# CMAKE_BUILD_TYPE      — Debug/Release/RelWithDebInfo/MinSizeRel
# CMAKE_INSTALL_PREFIX  — Installation prefix
# CMAKE_C_COMPILER      — C compiler
# CMAKE_CXX_COMPILER    — C++ compiler
# CMAKE_C_FLAGS         — C compiler flags
# CMAKE_CXX_FLAGS       — C++ compiler flags
# PROJECT_NAME          — Current project name
# PROJECT_VERSION       — Current project version
```

### Build Types

| Type | C Flags | C++ Flags | Description |
|------|---------|-----------|-------------|
| `Debug` | `-g` | `-g` | Debug symbols, no optimization |
| `Release` | `-O3 -DNDEBUG` | `-O3 -DNDEBUG` | Maximum optimization |
| `RelWithDebInfo` | `-O2 -g -DNDEBUG` | `-O2 -g -DNDEBUG` | Optimized with debug symbols |
| `MinSizeRel` | `-Os -DNDEBUG` | `-Os -DNDEBUG` | Optimize for size |

## Toolchain Files

Toolchain files describe the compiler and system for cross-compilation:

```cmake
# cmake/aarch64-toolchain.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)

set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)

set(CMAKE_FIND_ROOT_PATH /usr/aarch64-linux-gnu)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

```bash
# Cross-compile
cmake -DCMAKE_TOOLCHAIN_FILE=cmake/aarch64-toolchain.cmake -B build-arm
cmake --build build-arm
```

## CTest and CDash

CTest is CMake's testing framework. CDash is the web dashboard for test results.

### Basic Testing

```cmake
# Enable testing
enable_testing()

# Add a simple test
add_test(NAME mytest COMMAND myprogram --test)

# Test with properties
set_tests_properties(mytest PROPERTIES
    TIMEOUT 30
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    LABELS "unit;fast"
)

# Test with fixtures
add_test(NAME setup COMMAND setup_script)
add_test(NAME test1 COMMAND myprogram --test1)
set_tests_properties(test1 PROPERTIES FIXTURES_SETUP setup_fixture)
set_tests_properties(test1 PROPERTIES FIXTURES_REQUIRED setup_fixture)
```

### Using GTest

```cmake
# Fetch Google Test
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG        v1.14.0
)
FetchContent_MakeAvailable(googletest)

# Test executable
add_executable(mytests test_main.cpp test_utils.cpp)

target_link_libraries(mytests
    PRIVATE
        mylib
        GTest::gtest_main
)

# Register with CTest
include(GoogleTest)
gtest_discover_tests(mytests)
```

### Running Tests

```bash
# Run all tests
ctest

# Run with verbose output
ctest --verbose

# Run specific tests by label
ctest -L unit

# Run tests matching regex
ctest -R "test_name.*"

# Parallel testing
ctest -j$(nproc)

# Stop on first failure
ctest --stop-on-failure

# Output JUnit XML
ctest --output-junit results.xml

# Test with specific build config (multi-config)
ctest -C Release
```

### CDash Integration

```cmake
# CTestCustom.cmake or in CMakeLists.txt
include(CTest)

# CDash configuration
set(CTEST_PROJECT_NAME "MyProject")
set(CTEST_NIGHTLY_START_TIME "00:00:00 UTC")
set(CTEST_DROP_METHOD "https")
set(CTEST_DROP_SITE "cdash.example.com")
set(CTEST_DROP_LOCATION "/submit.php?project=MyProject")
```

```bash
# Submit results to CDash
ctest -D Experimental
ctest -D Nightly
ctest -D Continuous
```

## CMake Presets

Presets define common configurations in a JSON file:

```json
// CMakePresets.json
{
    "version": 3,
    "configurePresets": [
        {
            "name": "default",
            "displayName": "Default Config",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug"
            }
        },
        {
            "name": "release",
            "displayName": "Release Build",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "BUILD_TESTS": "OFF"
            }
        },
        {
            "name": "cross-arm",
            "displayName": "Cross-compile for ARM",
            "toolchainFile": "${sourceDir}/cmake/arm-toolchain.cmake",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "default",
            "configurePreset": "default"
        }
    ],
    "testPresets": [
        {
            "name": "default",
            "configurePreset": "default",
            "output": {
                "outputOnFailure": true
            }
        }
    ]
}
```

```bash
# Use presets
cmake --preset default
cmake --build --preset default
ctest --preset default

# List presets
cmake --list-presets
cmake --list-presets --build
cmake --list-presets --test
```

## CPack — Packaging

```cmake
# At the end of CMakeLists.txt
include(CPack)

set(CPACK_PACKAGE_NAME "myproject")
set(CPACK_PACKAGE_VERSION "${PROJECT_VERSION}")
set(CPACK_PACKAGE_CONTACT "maintainer@example.com")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "My awesome project")

# DEB package
set(CPACK_GENERATOR "DEB")
set(CPACK_DEBIAN_PACKAGE_DEPENDS "libc6 (>= 2.17)")
set(CPACK_DEBIAN_PACKAGE_SECTION "devel")

# RPM package
set(CPACK_GENERATOR "RPM")
set(CPACK_RPM_PACKAGE_REQUIRES "glibc >= 2.17")

# Multiple generators
set(CPACK_GENERATOR "DEB;RPM;TGZ")
```

```bash
# Create packages
cpack

# Or with specific generator
cpack -G DEB
cpack -G RPM
cpack -G TGZ
```

## Modern CMake Patterns

### Imported Targets for External Libraries

```cmake
# Create an imported target for a library without CMake support
add_library(myexternal STATIC IMPORTED)
set_target_properties(myexternal PROPERTIES
    IMPORTED_LOCATION "/usr/local/lib/libmyexternal.a"
    INTERFACE_INCLUDE_DIRECTORIES "/usr/local/include"
)

target_link_libraries(myprogram PRIVATE myexternal)
```

### Generator Expressions

```cmake
# Conditional based on build type
target_compile_options(mylib PRIVATE
    $<$<CONFIG:Debug>:-g -O0>
    $<$<CONFIG:Release>:-O3 -DNDEBUG>
)

# Conditional based on language
target_compile_options(mylib PRIVATE
    $<$<COMPILE_LANGUAGE:C>:-std=c17>
    $<$<COMPILE_LANGUAGE:CXX>:-std=c++20>
)

# Conditional based on platform
target_compile_definitions(mylib PRIVATE
    $<$<PLATFORM_ID:Linux>:LINUX>
    $<$<PLATFORM_ID:Darwin>:MACOS>
)

# Install interface generator expression
target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
)
```

### FetchContent (Dependency Management)

```cmake
include(FetchContent)

FetchContent_Declare(
    fmt
    GIT_REPOSITORY https://github.com/fmtlib/fmt.git
    GIT_TAG        10.1.1
)

FetchContent_Declare(
    spdlog
    GIT_REPOSITORY https://github.com/gabime/spdlog.git
    GIT_TAG        v1.12.0
)

FetchContent_MakeAvailable(fmt spdlog)

target_link_libraries(myprogram PRIVATE fmt::fmt spdlog::spdlog)
```

### CMake Modules

```cmake
# Include custom modules
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(MyCustomModule)

# Built-in useful modules
include(CheckCCompilerFlag)
check_c_compiler_flag(-fsanitize=address HAS_ASAN)

include(CheckIncludeFile)
check_include_file(sys/epoll.h HAS_EPOLL)

include(CheckFunctionExists)
check_function_exists(epoll_create HAS_EPOLL_CREATE)

include(GNUInstallDirs)
# Provides: CMAKE_INSTALL_BINDIR, CMAKE_INSTALL_LIBDIR, etc.

install(TARGETS myprogram
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
```

## CMake Commands Reference

```bash
# Configure
cmake -S . -B build                    # Source and build dirs
cmake -S . -B build -G Ninja           # With generator
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release

# Build
cmake --build build                    # Build using generated build system
cmake --build build -j8               # Parallel build
cmake --build build --target myprogram # Build specific target
cmake --build build --clean-first     # Clean before building

# Install
cmake --install build                  # Install
cmake --install build --prefix /tmp    # Custom prefix
cmake --install build --component dev  # Install specific component

# Test
ctest --test-dir build                 # Run tests
ctest --test-dir build -j8             # Parallel testing
ctest --test-dir build -R "test_name"  # Run matching tests

# Information
cmake --version                        # CMake version
cmake --system-information             # System info
cmake --build build --target help      # List targets
cmake -LAH build/                      # List cache variables
```

## Best Practices

1. **Use modern CMake (3.16+)** — target-based approach, not global variables
2. **Use imported targets** — `OpenSSL::SSL` not `${OPENSSL_LIBRARIES}`
3. **Use `target_*` not global commands** — `target_compile_options` not `add_compile_options`
4. **Use FetchContent** — for dependencies without system packages
5. **Use CMake presets** — for reproducible configurations
6. **Use Ninja generator** — faster than Make
7. **Out-of-source builds** — always `cmake -B build`
8. **Use `CMAKE_INSTALL_PREFIX`** — for portable installations
9. **Use `GNUInstallDirs`** — for standard installation paths
10. **Use CTest for testing** — integrated test framework

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [CMake Documentation](https://cmake.org/cmake/help/latest/)
- [CMake Tutorial](https://cmake.org/cmake/help/latest/guide/tutorial/)
- [Modern CMake](https://cliutils.gitlab.io/modern-cmake/)
- [Effective Modern CMake](https://gist.github.com/mbinna/c61dbb39bca0e4fb7d1f73b0d66a4fd1)
- [CMake Cookbook](https://www.packtpub.com/product/cmake-cookbook/9781788470711)

## Related Topics

- [Make](./make.md) — Classic build automation (CMake can generate Makefiles)
- [GCC](./gcc.md) — The compiler CMake typically drives
- [Clang/LLVM](./clang-llvm.md) — Alternative compiler and toolchain
- [Linker](./linker.md) — How object files become executables
