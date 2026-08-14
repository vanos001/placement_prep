# Online Assessment Strategies

Online assessments (OAs) are the gatekeeper to most technical interviews. Unlike live interviews, you have no one to ask clarifying questions — your ability to self-manage determines the outcome.

## Time Allocation Across Problems

### 2-Problem OA (60 min)

| Phase | Duration | Action |
|-------|----------|--------|
| Read both problems | 5 min | Identify difficulty, note constraints |
| Easier problem | 20 min | Solve completely, test thoroughly |
| Harder problem | 25 min | Aim for optimal or strong brute force |
| Buffer / review | 10 min | Re-test, handle edge cases |

### 3-Problem OA (75–90 min)

| Phase | Duration | Action |
|-------|----------|--------|
| Read all problems | 5 min | Rank by difficulty |
| Easy problem | 12 min | Clean solve, no mistakes |
| Medium problem | 25 min | Full optimal solution |
| Hard problem | 25 min | Brute force first, optimize if time permits |
| Review | 8 min | Edge cases on all three |

**Rule of thumb:** If you haven't made progress in 8 minutes, move on. You can return later. A partial solution scores more than a blank submission.

## Problem Selection Strategy

### Easy-First Approach (recommended for most)

Start with the easiest problem to secure guaranteed points, build confidence, and warm up. Most OAs award full points for correctness regardless of which problem you solve first.

### Hardest-First Approach (only for strong candidates)

If you're confident in your speed and the hardest problem carries disproportionate weight, tackling it first ensures you have peak mental energy for it. Risk: if you get stuck, you lose time on easy free points.

### When to Skip a Problem

- No clear approach after 8 minutes of thinking
- The problem requires knowledge you don't have (e.g., segment trees, advanced DP)
- You have 3+ problems and only 20 minutes remain — focus on testing what you have
- The problem is worth fewer points than time invested elsewhere

**Always submit something.** A brute force O(n²) solution that passes some test cases earns partial credit. An empty submission earns zero.

## Reading Comprehension Tips

OA problem statements are often verbose. Use this systematic approach:

1. **Read the title and first paragraph** — identifies the problem type
2. **Skip to constraints and input/output format** — tells you the feasible complexity class
3. **Read the examples** — often clarify ambiguity better than the prose
4. **Re-read the full statement** — now you have context to parse details

Common pitfalls:
- **1-indexed vs 0-indexed** arrays — check examples carefully
- **Inclusive vs exclusive** ranges — "between 1 and n" usually means inclusive
- **Return format** — some OAs require a specific output format (e.g., space-separated vs array)
- **Hidden constraints** — negative numbers, empty inputs, duplicate elements

## Edge Case Checklist

Before hitting submit, mentally verify these cases:

```
□ Empty input (empty string, empty array, null)
□ Single element
□ All identical elements
□ Already sorted / reverse sorted
□ Negative numbers (if applicable)
□ Maximum constraint values (overflow check)
□ Minimum constraint values
□ Duplicates in input
□ Input at boundary (e.g., n=1, n=10⁵)
```

## OA Platform Comparison

| Feature | HackerRank | CodeSignal | Codility | HireVue |
|---------|-----------|-----------|----------|--------|
| Tab switching | Sometimes flagged | Proctored | Proctored | Proctored + video |
| Language support | 30+ | 20+ | 25+ | Limited |
| Copy-paste | Often disabled | Disabled | Allowed | Varies |
| Custom test cases | Yes | Limited | Yes | No |
| Partial scoring | Common | Rare | Yes | Varies |
| Hidden tests | Yes | Yes | Yes | Yes |
| Difficulty curve | Gentle | Steep | Moderate | Gentle |
| Time limits | Per problem | Total session | Per problem | Per problem |

## Test Case Patterns OAs Commonly Use

OAs typically run 5–20 test cases. Knowing the pattern helps you debug faster:

1. **Example test cases** (1–3): Given in the problem. If these fail, you misunderstood the problem.
2. **Small random** (2–4): n ≤ 10. Tests correctness on tiny inputs.
3. **Edge cases** (1–2): Empty input, single element, all same values.
4. **Large input, simple pattern** (1–2): n = 10⁵ but with a simple structure (sorted, all same). Tests complexity.
5. **Large input, complex pattern** (1–3): n = 10⁵ with adversarial data. Tests correctness at scale.
6. **Boundary values** (1): Values at int min/max, n at constraint limit.

**If you pass examples but fail hidden tests**, the issue is almost always an edge case or integer overflow. Add `sys.setrecursionlimit` in Python for deep recursion, and use `long` or explicit big-integer handling in Java/C++.

## Handling Partial Scoring

Many platforms (HackerRank, Codility) award points proportional to test cases passed. Strategy:

1. **Submit a brute force first** — guarantees some points even if you can't optimize
2. **Then optimize incrementally** — each improvement may unlock more test cases
3. **Don't delete your brute force** — comment it out, keep it as fallback

## Interview Tips

- Practice on the actual platform beforehand — each has its own IDE quirks
- Have a template ready (imports, fast I/O for Python/Java) to avoid wasting time on boilerplate
- Use `print()` debugging liberally during practice, but remove all debug prints before submitting
- If the platform allows custom test cases, write 3–4 of your own before submitting
- Keep a scratch pad — write out the approach in plain English before coding
