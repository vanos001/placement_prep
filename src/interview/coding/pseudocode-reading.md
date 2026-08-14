# Reading Pseudocode in Online Assessments

Some OAs present algorithms in pseudocode and ask you to predict output, find bugs, or implement the logic in your chosen language. Pseudocode varies by source but follows predictable conventions.

## Common Pseudocode Conventions

| Convention | Meaning |
|-----------|---------|
| `A[1..n]` | Array indexed from 1 to n (1-based) |
| `A[0..n-1]` | Array indexed from 0 to n-1 (0-based) |
| `for i = 1 to n` | Inclusive range: i takes values 1, 2, ..., n |
| `for i = 0 to n-1` | Inclusive range: i takes values 0, 1, ..., n-1 |
| `while x > 0 do` | Loop body indented below |
| `x ← value` or `x := value` | Assignment (not equality check) |
| `return x` | Function returns x |
| `if ... then ... else ... end if` | Conditional block |
| `MOD` or `%` | Modulo operator |
| `DIV` or `/` | Integer division (floor) unless specified |
| `len(A)` or `length(A)` | Size of array A |
| `append(A, x)` or `A.push(x)` | Add x to end of A |
| `swap(A[i], A[j])` | Exchange values at indices i and j |
| `∞` or `INF` | Infinity / very large number |
| `NULL` or `nil` | Null/empty reference |

## Key Differences to Watch For

**1-based vs 0-based indexing** is the single most common source of errors. If the pseudocode says `A[1]`, it's 1-based. When translating to Python (0-based), subtract 1 from all indices.

**Inclusive vs exclusive ranges:** `for i = 1 to n` includes n. Python's `range(1, n)` does *not* include n — use `range(1, n + 1)`.

**Integer division:** Pseudocode `5 / 2` often means integer division (result: 2). Python 3 requires `5 // 2`. Java/C/C++ integer division is automatic for int types.

## Tracing Through Examples

Always trace with concrete values. Use a table:

```
Pseudocode:  x ← 0; for i = 1 to 4 do x ← x + i * i

Step | i | x (before) | i*i | x (after)
------|---|-------------|-----|----------
  1   | 1 |     0      |  1  |    1
  2   | 2 |     1      |  4  |    5
  3   | 3 |     5      |  9  |   14
  4   | 4 |    14      | 16  |   30

Result: x = 30
```

## Converting Pseudocode to Your Language

### Step-by-step process

1. **Identify the indexing** — is it 0-based or 1-based? Adjust all array accesses.
2. **Identify the loop bounds** — convert inclusive ranges to the target language's convention.
3. **Identify data structures** — "array" could be a list (Python), vector (C++), or ArrayList (Java). "set" could be a hash set or tree set.
4. **Handle integer division** — replace `/` with `//` in Python if the pseudocode implies integer division.
5. **Translate conditionals** — pseudocode `if A[i] > 0 and A[i] < 10` translates directly; watch for `else if` vs `elif`.
6. **Test with the given example** — verify your translation produces the same output.

### Common translation pitfalls

| Pseudocode | Python | C++ |
|-----------|--------|-----|
| `A[1..n]` access | `A[i-1]` | `A[i-1]` |
| `for i = 1 to n` | `for i in range(1, n+1)` | `for (int i=1; i<=n; i++)` |
| `x ← x + 1` | `x += 1` | `x += 1;` |
| `x MOD y` | `x % y` | `x % y` |
| `A.push_back(x)` | `A.append(x)` | `A.push_back(x)` |

## Interview Tips

- When asked to find bugs in pseudocode, check: off-by-one in loops, missing base cases in recursion, wrong comparison operator (`<` vs `<=`), and integer overflow
- If asked to implement pseudocode, **don't optimize** — implement exactly what's written, then optimize if asked
- Practice reading code in languages you don't use — many OAs show Java or C++ pseudocode to Python developers
