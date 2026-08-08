# Python Ecosystem and Tooling

## Overview

Python's ecosystem is its superpower: **NumPy** (numeric arrays), **Pandas/Polars** (dataframes), **scikit-learn** (ML), **PyTorch** (deep learning), **FastAPI/Django/Flask** (web), **Pydantic** (validation), **SQLAlchemy** (ORM), and **asyncio** (async). It's the default language for data science, ML, scripting, and increasingly for APIs. See [Python Overview](./README.md) for the language.

## Numeric Foundation: NumPy

NumPy provides the `ndarray` — a fast, C-implemented multidimensional array. Everything else (Pandas, scikit-learn, PyTorch's CPU path) builds on it.

```python
import numpy as np
a = np.arange(12).reshape(3, 4)
b = a * 2            # vectorized — no Python loop
print(a.sum(axis=1)) # [6, 22, 38]
```

Why it's fast: **vectorized operations** run in C (with SIMD), avoiding Python's per-element interpreter overhead. The interview rule: *never loop over arrays in Python — vectorize*.

## Dataframes: Pandas vs Polars

| | **Pandas** | **Polars** |
|---|---|---|
| Engine | Python + Cython | **Rust** (compiled, SIMD, multi-threaded) |
| Execution | Eager only | **Lazy** (default) with query optimizer |
| Memory | NumPy (PyArrow opt-in) | **Apache Arrow** (native, zero-copy) |
| Scale | In-memory | In-memory + **streaming engine** (out-of-core) |
| Group-by (10M rows) | ~12.5 s | ~0.45 s |
| Status (2026) | 2.x/3.0 (CoW, PyArrow strings) | 1.2x+ stable, 2.8M weekly downloads |

**Pandas 3.0** (alpha in 2026) brings copy-on-write defaults and PyArrow-backed strings, closing part of the gap. Practical guidance: **Pandas for familiarity/ecosystem and small data; Polars for large-data pipelines** — many teams use Polars for heavy transforms and convert to Pandas at the ML/plotting boundary.

```python
import polars as pl
df = pl.scan_csv("big.csv")            # lazy
result = (df.filter(pl.col("qty") > 0)
            .group_by("category")
            .agg(pl.col("amount").sum())
            .collect())                # optimized plan executes
```

## ML Stack

| Library | Role |
|---|---|
| **scikit-learn** | Classical ML (regression, trees, clustering, preprocessing) — the default for non-deep ML |
| **PyTorch** | Deep learning (see [PyTorch](../../frameworks/pytorch/README.md)); dynamic graphs, autograd |
| **TensorFlow/Keras** | Deep learning (production/deployment-focused, TF Serving) |
| **XGBoost / LightGBM** | Gradient boosting — tabular data winners |
| **Hugging Face Transformers** | Pretrained models and fine-tuning |
| **JAX** | NumPy+autograd+JIT; research/TPU |

## Web Frameworks

| Framework | Style | Best for |
|---|---|---|
| **FastAPI** | Async, type-hint-driven, automatic OpenAPI docs | Modern APIs, high concurrency |
| **Django** | Batteries-included (ORM, admin, auth) | Full-stack products (see [Django](../../frameworks/django/README.md)) |
| **Flask** | Minimal microframework | Small/medium apps, flexibility |

## Validation & Persistence

- **Pydantic** — data validation via type annotations (`BaseModel`); FastAPI's request/response layer; the modern standard for typed Python data.
- **SQLAlchemy** — the standard ORM (Core + ORM); async support via `asyncpg`.
- **psycopg3 / asyncpg** — Postgres drivers.

```python
from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    name: str = Field(min_length=1)
    email: EmailStr

u = User(id=1, name="Ada", email="ada@example.com")  # validated + typed
```

## Async: asyncio and friends

- **asyncio** — the built-in event loop (`async def`, `await`); see [AsyncIO](./asyncio.md).
- **uvloop** — drop-in faster event loop (Cython).
- **anyio / trio** — structured concurrency alternatives.
- **httpx** — modern async HTTP client.

## Packaging & Tooling

| Tool | Role |
|---|---|
| **pip** | Installer |
| **venv / uv** | Virtual environments (uv is the fast new standard) |
| **poetry / uv** | Dependency + packaging management |
| **ruff / black** | Linting + formatting (ruff is the fast Rust-based linter) |
| **mypy / pyright** | Type checking |
| **pytest** | The standard test framework |
| **Docker** | Deployment |

## Interview Questions

### Q: Why is NumPy so much faster than Python lists?

NumPy's `ndarray` is a contiguous C array with **vectorized operations** that run in compiled C (with SIMD), operating on whole arrays at once. Python lists store boxed objects and loop element-by-element in the interpreter — orders of magnitude slower. The rule: vectorize with NumPy/Pandas/Polars rather than writing Python loops.

### Q: Pandas vs Polars — when would you choose each?

Pandas for familiarity, ecosystem integration (ML/plotting libraries), and small-to-medium in-memory data. Polars for large datasets where speed and memory matter: lazy execution with a query optimizer, multi-threaded Rust engine, and a streaming engine for data bigger than RAM. Many production pipelines use Polars for transforms and convert to Pandas at the boundary where ML libraries live.

### Q: What does Pydantic do and why is it popular?

Pydantic validates data **from type annotations** at runtime: you declare a `BaseModel` with typed fields, and construction validates/coerces/parses the data (e.g., JSON → typed objects), raising clear errors on failure. It's FastAPI's foundation, gives editor type-safety, and has become the standard for typed Python data handling — replacing manual validation code.

### Q: asyncio vs threads in Python?

asyncio runs **cooperative concurrency** on one thread with an event loop — ideal for I/O-bound work (many connections, API calls) with low overhead. Threads also work for I/O but fight the GIL for CPU work and cost more per unit. For CPU-bound parallelism, use **multiprocessing** (separate processes, no GIL) — asyncio doesn't help CPU-bound code. See [AsyncIO](./asyncio.md) and [GIL](./gil.md).

### Q: How do you package and type-check a Python project in 2026?

Modern stack: `uv` for env/dependency management (fast), `ruff` for lint+format, `mypy`/`pyright` for typing, `pytest` for tests, `pyproject.toml` as the single config. Add type hints with Pydantic models at boundaries, and run `mypy`/`ruff` in CI.

## References

- NumPy — https://numpy.org/
- Pandas — https://pandas.pydata.org/
- Polars — https://pola.rs/
- scikit-learn — https://scikit-learn.org/
- FastAPI — https://fastapi.tiangolo.com/
- Pydantic — https://docs.pydantic.dev/
- SQLAlchemy — https://www.sqlalchemy.org/
- asyncio docs — https://docs.python.org/3/library/asyncio.html
- uv — https://docs.astral.sh/uv/

## Related Topics

- [Python Overview](./README.md) — the language
- [CPython Internals](./cpython-internals.md) — how the interpreter works
- [GIL](./gil.md) — concurrency constraints
- [AsyncIO](./asyncio.md) — the async model
- [PyTorch](../../frameworks/pytorch/README.md) — deep learning
- [FastAPI](../../frameworks/fastapi/README.md) — API framework
- [Django](../../frameworks/django/README.md) — full-stack framework
