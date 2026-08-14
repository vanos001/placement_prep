# Property-Based Testing

## Overview

Instead of writing tests with specific input/output pairs (example-based testing), property-based testing defines **properties** that should hold for *all* valid inputs, and the framework generates thousands of random inputs to check them.

| Aspect | Example-Based | Property-Based |
|--------|--------------|----------------|
| Inputs | Hand-picked | Randomly generated |
| Coverage | Specific scenarios | Broad input space |
| Failure diagnosis | Known input | Minimal failing case (shrinking) |
| Tools | Any framework | QuickCheck, Hypothesis, fast-check |

## QuickCheck (Haskell) — The Original

```haskell
-- Property: reversing a list twice returns the original
prop_reverseTwice :: [Int] -> Bool
prop_reverseTwice xs = reverse (reverse xs) == xs

-- Run: quickCheck prop_reverseTwice
-- +++ OK, passed 100 tests
```

## Hypothesis (Python)

```python
from hypothesis import given, strategies as st

def sort_and_deduplicate(items):
    return sorted(set(items))

@given(st.lists(st.integers()))
def test_sorted_is_sorted(items):
    result = sort_and_deduplicate(items)
    assert result == sorted(result), "Output is not sorted"

@given(st.lists(st.integers()))
def test_no_duplicates(items):
    result = sort_and_deduplicate(items)
    assert len(result) == len(set(result)), "Output has duplicates"

@given(st.lists(st.integers()))
def test_subset_preserved(items):
    result = sort_and_deduplicate(items)
    assert set(result).issubset(set(items)), "Output has extra elements"
```

## Shrinking

When a property fails, the framework **shrinks** the failing input to the smallest case that still triggers the failure, making diagnosis easier.

```
Failure: input [3, -1, 42, 0, 7] fails
  Shrink:  [3, -1, 42, 0, 7]
  Shrink:  [3, -1, 0, 7]
  Shrink:  [-1, 0, 7]
  Shrink:  [-1, 0]
  Minimal: [-1, 0]  ← smallest failing input
```

## Common Properties to Test

| Property | Description |
|----------|-------------|
| Idempotency | `f(f(x)) == f(x)` |
| Involution | `f(f(x)) == x` (reverse, complement) |
| Round-trip | `decode(encode(x)) == x` |
| Commutativity | `f(a, b) == f(b, a)` |
| Invariants | Post-condition holds for all valid inputs |

## Interview Questions

**Q: When would you prefer property-based testing over example-based?**
A: When the input space is large and hard to enumerate (e.g., parsing, serialization, data transformations). Properties like "round-trip encode/decode preserves data" or "sort produces ordered output" are more efficiently verified over random inputs.

**Q: What is shrinking and why is it important?**
A: Shrinking finds the minimal input that still triggers a failure. Without shrinking, a failure from a 10,000-element list gives you a 10,000-element failing case to debug. With shrinking, you might get `[0, -1]` — much easier to reason about.

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [fast-check (TypeScript)](https://fast-check.dev/)
- [QuickCheck Papers](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/QuickCheck.pdf)
- See also: [Unit Testing](./unit-testing.md), [TDD & BDD](./tdd-bdd.md), [Mocking](./mocking.md), [Test Strategy](./test-strategy.md)
