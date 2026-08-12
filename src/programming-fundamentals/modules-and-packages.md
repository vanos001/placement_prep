# Modules and Packages

> No one writes everything from scratch. Modules and packages are how we organize, share, and reuse code.

## 1. Namespaces

A **namespace** is a container that prevents name collisions by grouping identifiers.

```cpp
// C++
namespace graphics {
    class Renderer { /* ... */ };
    class Texture { /* ... */ };
}

namespace audio {
    class Renderer { /* ... */ };  // OK — different namespace
}

// Usage
graphics::Renderer r;
using namespace graphics;  // import all names (use sparingly)
Renderer r2;               // OK after using directive
```

```csharp
// C#
namespace Company.Project.Module {
    public class MyClass { /* ... */ }
}

// File-scoped namespace (C# 10)
namespace Company.Project.Module;
public class MyClass { /* ... */ }
```

```python
# Python: modules ARE namespaces
import math
math.sqrt(4)  # 2

# From import
from math import sqrt
sqrt(4)

# Namespace packages (PEP 420)
# mypackage/
# ├── __init__.py
# └── subpackage/
#     └── __init__.py
```

## 2. Modules

A **module** is a unit of code organization — typically a single file or a cohesive collection of functions, classes, and variables.

### Module Systems by Language

#### Python Modules

```python
# math_utils.py
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

__all__ = ["add", "multiply"]  # controls `from module import *`
```

```python
# main.py
import math_utils
result = math_utils.add(1, 2)

from math_utils import add
result = add(1, 2)
```

#### JavaScript Modules (ES Modules)

```javascript
// math_utils.js
export function add(a, b) {
    return a + b;
}

export function multiply(a, b) {
    return a * b;
}

export default class Calculator { /* ... */ }
```

```javascript
// main.js
import Calculator, { add, multiply } from './math_utils.js';
import * as math from './math_utils.js';

// Dynamic import
const module = await import('./math_utils.js');
```

#### Java Modules (Java 9+)

```java
// module-info.java
module com.myapp.core {
    requires java.sql;           // dependency
    requires transitive java.logging;  // transitive dependency
    exports com.myapp.core.api;  // public API
}
```

#### Go Packages

```go
// package mathutil
package mathutil

func Add(a, b int) int {
    return a + b
}

// Capitalized = exported (public)
// lowercase = unexported (private)
```

```go
// import
import "myproject/mathutil"

result := mathutil.Add(1, 2)
```

#### Rust Modules

```rust
// Inline module
mod math {
    pub fn add(a: i32, b: i32) -> i32 {
        a + b
    }
    
    // Nested module
    pub mod advanced {
        pub fn power(base: i32, exp: u32) -> i32 {
            (0..exp).fold(1, |acc, _| acc * base)
        }
    }
}

// File-based modules
// src/lib.rs
mod math_utils;  // loads math_utils.rs or math_utils/mod.rs
pub use math_utils::add;  // re-export
```

### Module Access Control

| Language | Public | Private | Protected | Package |
|----------|--------|---------|-----------|---------|
| Java | `public` | `private` | `protected` | (default) |
| Python | no keyword | `_prefix` | N/A | N/A |
| JavaScript | `export` | not exported | N/A | N/A |
| Go | `UpperCase` | `lowerCase` | N/A | N/A |
| Rust | `pub` | (default) | N/A | N/A |
| C++ | `public` | `private` | `protected` | N/A |

## 3. Packages

A **package** is a collection of modules distributed as a unit.

### Package Structure

```
my-package/
├── src/
│   ├── __init__.py       # makes it a Python package
│   ├── core.py
│   └── utils.py
├── tests/
│   ├── __init__.py
│   └── test_core.py
├── pyproject.toml        # build configuration
├── README.md
├── LICENSE
└── CHANGELOG.md
```

```
# Java/Maven structure
my-project/
├── src/
│   ├── main/
│   │   └── java/
│   │       └── com/example/
│   │           └── App.java
│   └── test/
│       └── java/
│           └── com/example/
│               └── AppTest.java
├── pom.xml
└── README.md
```

## 4. Imports and Exports

### Import Styles

```python
# Python
import os                           # import module
from os import path                 # import specific name
from os.path import join            # import from submodule
import numpy as np                  # import with alias
from os import *                    # import all (avoid!)
```

```javascript
// JavaScript ESM
import defaultExport from './module.js';        // default import
import { named } from './module.js';            // named import
import { named as alias } from './module.js';   // aliased import
import * as module from './module.js';           // namespace import
import './module.js';                            // side-effect only
```

```go
// Go
import (
    "fmt"                    // standard library
    "github.com/user/pkg"   // external package
    local "github.com/other/pkg"  // aliased
    _ "github.com/lib/only-init"  // init only
)
```

### Circular Dependencies

Most module systems **prohibit circular imports** (A imports B, B imports A):

```python
# Python: circular import causes ImportError
# a.py
from b import func_b
def func_a(): return "a"

# b.py
from a import func_a  # ImportError!
def func_b(): return "b"

# Solution: restructure, use late import, or merge modules
```

## 5. Dependency Management

### Package Managers

| Language | Manager | Lock File | Config File |
|----------|---------|-----------|-------------|
| Python | pip, Poetry, uv | `poetry.lock`, `uv.lock` | `pyproject.toml` |
| JavaScript | npm, yarn, pnpm | `package-lock.json`, `yarn.lock` | `package.json` |
| Java | Maven, Gradle | N/A | `pom.xml`, `build.gradle` |
| Go | go mod | `go.sum` | `go.mod` |
| Rust | cargo | `Cargo.lock` | `Cargo.toml` |
| Ruby | bundler | `Gemfile.lock` | `Gemfile` |
| C# | NuGet | `packages.lock.json` | `.csproj` |
| C++ | vcpkg, Conan | varies | varies |

### Virtual Environments

```python
# Python: venv
python -m venv .venv
source .venv/bin/activate
pip install requests

# Poetry
poetry install
poetry add requests

# uv (fast)
uv venv
uv pip install requests
```

```javascript
// Node.js: node_modules is the "virtual environment"
npm init
npm install express

// pnpm: uses a global store + symlinks (space efficient)
pnpm install express
```

### Dependency Resolution

```
my-app requires:
├── requests>=2.25
│   ├── urllib3>=1.21,<1.27
│   └── certifi>=2017.4.17
└── flask>=2.0
    ├── Werkzeug>=2.0
    │   └── MarkupSafe>=2.0
    └── Jinja2>=3.0
        └── MarkupSafe>=2.0  ← shared dependency
```

### Lock Files

Lock files pin **exact versions** of all dependencies (including transitive):

```json
// package-lock.json (simplified)
{
    "packages": {
        "node_modules/express": {
            "version": "4.18.2",
            "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz"
        }
    }
}
```

**Why lock files matter:**
- Reproducible builds
- Same versions across team members and CI
- Protect against supply chain attacks (unexpected version changes)

## 6. Semantic Versioning (SemVer)

```
MAJOR.MINOR.PATCH

MAJOR: incompatible API changes
MINOR: new functionality (backward compatible)
PATCH: bug fixes (backward compatible)

Examples:
1.0.0 → 1.0.1  (bug fix)
1.0.1 → 1.1.0  (new feature)
1.1.0 → 2.0.0  (breaking change)
```

### Version Ranges

```
^1.2.3  → >=1.2.3, <2.0.0    (compatible with 1.x)
~1.2.3  → >=1.2.3, <1.3.0    (compatible with 1.2.x)
1.2.x   → >=1.2.0, <1.3.0
>=1.0.0 → any version >= 1.0.0
*       → any version
```

```json
// package.json
{
    "dependencies": {
        "express": "^4.18.0",     // any 4.x >= 4.18.0
        "lodash": "~4.17.21",    // any 4.17.x >= 4.17.21
        "exact": "1.2.3"         // exactly 1.2.3
    }
}
```

```toml
# Cargo.toml
[dependencies]
serde = "1.0"        # equivalent to ^1.0
tokio = "~1.28"      # equivalent to ~1.28
exact = "=1.2.3"
```

### Pre-release Versions

```
1.0.0-alpha.1  → alpha release
1.0.0-beta.1   → beta release
1.0.0-rc.1     → release candidate
1.0.0          → stable release

Order: alpha < beta < rc < stable
```

## 7. Dependency Injection

**Dependency Injection (DI)** provides dependencies from outside rather than creating them inside.

```java
// Without DI — tightly coupled
class OrderService {
    private DatabaseRepo repo = new MySqlRepo();  // hard-coded!
}

// With DI — loosely coupled
class OrderService {
    private final Repository repo;
    
    public OrderService(Repository repo) {  // injected
        this.repo = repo;
    }
}

// Now you can inject any implementation
OrderService service = new OrderService(new PostgresRepo());
// Or use a DI framework (Spring, Guice)
```

```python
# Python: DI via constructor
class OrderService:
    def __init__(self, repo: Repository):
        self.repo = repo

# Inject
service = OrderService(PostgresRepo())
```

### DI Benefits

| Benefit | Explanation |
|---------|-------------|
| Testability | Inject mocks for testing |
| Flexibility | Swap implementations easily |
| Loose coupling | Depend on abstractions, not concretions |
| Single Responsibility | Classes don't create their own dependencies |

## 8. Monorepo vs Polyrepo

| Aspect | Monorepo | Polyrepo |
|--------|----------|----------|
| Structure | One repo, many packages | One repo per package |
| Dependency sharing | Easy (symlinks, workspaces) | Version pinning |
| Atomic commits | ✅ Cross-package changes | ❌ Separate PRs |
| Tooling | Bazel, Nx, Turborepo, Lerna | Standard Git |
| Scaling | Needs specialized tooling | Simple Git |
| Examples | Google, Meta, Microsoft | Most open-source projects |

## Interview Questions

1. **What is a namespace? Why is it important?**
   A container that prevents name collisions by grouping identifiers. Essential in large codebases where multiple libraries might define the same name.

2. **Explain the difference between a module and a package.**
   A module is a single file or unit of code. A package is a collection of modules distributed as a unit. A package typically includes metadata (version, dependencies, description).

3. **What are lock files and why are they important?**
   Lock files pin exact versions of all dependencies (including transitive). They ensure reproducible builds across environments and protect against unexpected dependency updates.

4. **Explain semantic versioning.**
   MAJOR.MINOR.PATCH. Major: breaking changes. Minor: new features (backward compatible). Patch: bug fixes. Helps communicate the nature of changes to consumers.

5. **What is dependency injection?**
   Providing dependencies from outside a class rather than creating them inside. Improves testability (inject mocks), flexibility (swap implementations), and follows the Dependency Inversion Principle.

6. **What are circular dependencies? How do you resolve them?**
   When module A imports B and B imports A. Causes import errors or infinite loops. Solutions: restructure code, merge modules, use late/lazy imports, extract shared code into a third module.

7. **What's the difference between `^` and `~` in version ranges?**
   `^1.2.3`: compatible with 1.x (>=1.2.3, <2.0.0). `~1.2.3`: compatible with 1.2.x (>=1.2.3, <1.3.0). Caret is more permissive; tilde is more conservative.

8. **When would you use a monorepo vs polyrepo?**
   Monorepo: tightly coupled projects, shared tooling, atomic cross-package changes. Polyrepo: independent teams, different release cycles, open-source projects.
