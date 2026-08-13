# Practical Programming Problems

## Overview

This section covers real-world programming problems that test your ability to build **production-quality software**. Unlike algorithm problems, these focus on:

- **Parsing and processing** real-world data formats
- **Building tools** that solve actual problems
- **Handling edge cases** that exist in production
- **Writing clean, maintainable code** under constraints

## Why These Problems Matter

Companies test practical skills because that's what you'll do daily:
- Parse configuration files → **Parsers**
- Build internal tools → **CLI Tools**
- Process log files and data → **File Processing**
- Handle concurrent operations → **Concurrent Problems**
- Build resilient systems → **System Utilities**

## Problem Categories

| Category | Problems | Key Skills |
|----------|----------|------------|
| Parsers | JSON, CSV, URL, Expression | Recursive descent, state machines |
| CLI Tools | Argument parsing, prompts, output | UX, formatting, error handling |
| File Processing | Logs, duplicates, search | I/O, streaming, regex |
| Concurrent | Producer-consumer, pools | Threading, synchronization |
| System Utilities | Rate limiter, circuit breaker | Resilience, configuration |

## Files in This Section

- [parsers.md](parsers.md) — Building parsers from scratch
- [cli-tools.md](cli-tools.md) — Building CLI tools
- [file-processing.md](file-processing.md) — File processing problems
- [concurrent-problems.md](concurrent-problems.md) — Concurrency problems
- [system-utilities.md](system-utilities.md) — System utility libraries

## Tips for Success

1. **Handle edge cases first** — empty input, malformed data, null values
2. **Use streaming when possible** — don't load entire files into memory
3. **Write composable functions** — small functions that chain together
4. **Test with real data** — use actual log files, JSON samples, etc.
5. **Consider performance** — but don't premature optimize
