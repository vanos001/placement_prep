# Convex Hull Trick and Li Chao Tree

Recurrences of the form dp[i] = min over j of (m_j * x_i + b_j) can drop
the min from O(n) terms to O(1) or O(log C): each candidate j is a line,
each query x_i a point, and the answer is the lower envelope. The survey
table in [DP Optimization](./dp-optimization.md) lists it among the DP
accelerators and [Chapter 86](../chapters/ch86-dp-optimization.md) has a
C++ monotone implementation; this page derives the invariants, compares
the structures people actually ship, and ends with an executable Li Chao
cross-checked against a brute-force oracle.

## Reading a DP Transition as Lines

Take the split-into-pieces recurrence with prefix sums S:

    dp[i] = min over j < i of ( dp[j] + (S_i - S_j)^2 )
          = x^2 + min over j of ( -2 S_j * x + dp[j] + S_j^2 ),  x = S_i

Every previous state j offers one line with slope m_j = -2 S_j and
intercept b_j = dp[j] + S_j^2; x^2 is a per-i constant. Mini example,
a = [2, 3, 1], S = [0, 2, 5, 6]:

    L0: m = 0,   b = 0     (dp[0] = 0)
    L1: m = -4,  b = 8     (dp[1] = 4)
    L2: m = -10, b = 38    (dp[2] = 13)
    query x = 5:  L0 -> 0, L1 -> -12, L2 -> -12  => dp[2] = -12 + 25 = 13
    query x = 6:  L0 -> 0, L1 -> -16, L2 -> -22  => dp[3] = -22 + 36 = 14

dp[3] = 14 matches the brute-force best split [2] [3] [1] with cost
4 + 9 + 1. The whole art is answering "min over lines at x" fast.

## Pointer-Walk CHT and the Bad Test

If lines arrive with non-increasing slopes and queries have
non-decreasing x, a stack of envelope lines plus a query pointer runs in
amortized O(1). Invariants: the hull is sorted by slope, and the active
line pointer only moves right (queries sorted). A middle line l2 dies
when it never wins strictly between l1 and l3:

```text
lines (min envelope), slopes ordered m1 = 0 > m2 = -1 > m3 = -2

  x      :  0     2     6     10    12
  L1: y=0         0     0     0     0     0
  L2: y=-x+10    10     8     4     0    -2
  L3: y=-2x+12   12     8     0    -8   -12
  min            0      0     0     0     0

L2 touches the envelope only at x = 2 and x = 10, never strictly below
both neighbours -> dead. Crossing arithmetic agrees: L1 and L3 meet at
x = (b1 - b3)/(m3 - m1) = 6, where L2 evaluates to 4 > 0.
```

Keep the test exact with integer cross products:

    l2 unnecessary  <=>  (b3 - b1) * (m2 - m1) >= (b2 - b1) * (m3 - m1)

Slopes up to 4 * 10^9 and intercepts up to 10^18 push each side to
~10^27, far beyond 64 bits: use __int128 in C++ (long double invites
silent wrong pops). Equal slopes make the intersection formula divide by
zero -- keep only the better intercept.

## Li Chao Tree: The Midpoint Invariant

When insertions or queries are not monotone, the pointer-walk breaks
(classic WA). The Li Chao tree fixes an x-domain [0, C) and keeps a
segment tree whose every node stores the line best at its interval
midpoint. Insertion descends from the root: compare at the midpoint, the
winner stays in the node, and the loser recurses into the ONE side where
it can still win (two lines cross at most once), stopping when it cannot
beat the stored line at either endpoint. Consequence: if line L is the
true minimum at x, L is stored on the root-to-leaf path for x, so
query(x) = min over the O(log C) lines on that path is exact, in any
insertion and query order.

```text
insertion effect on the envelope, domain [0,16):
lines y = x and y = -x + 10 already inserted; now insert y = 3

  x       : 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
  y=x     : 0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
  y=-x+10 :10  9  8  7  6  5  4  3  2  1  0 -1 -2 -3 -4 -5
  y=3     : 3  3  3  3  3  3  3  3  3  3  3  3  3  3  3  3
  envelope: 0  1  2  3  3  3  3  3  2  1  0 -1 -2 -3 -4 -5
                          ^^^^^^^  y = 3 wins on x in [3, 7]
```

Iterative layout over a power-of-two domain: heap indexing, node v with
children 2v and 2v+1, no child allocation; memory is 2 * 2^k for a
domain of 2^k integers, so compress arbitrary coordinates or round the
domain up. Real-valued x needs discretization.

## Choosing a Structure

| Structure | Insert | Query | Constraints | Typical use |
|---|---|---|---|---|
| Pointer-walk CHT | O(1) amortized | O(1) amortized | slopes and queries both monotone | parabolic-cost partition DPs |
| Li Chao tree | O(log C) | O(log C) | fixed integer x-domain, lines only | arbitrary insert/query order |
| Line container | O(log n) | O(log n) | balanced set over upper hull, deletable | dynamic CHT, heavy churn |
| Kinetic segment tree | event-driven | O(log^2 n) amortized | slopes change linearly over time | moving objects, niche |

The line container (KACTL's LineContainer) replaces the fixed domain
with an ordered set and survives arbitrary churn; kinetic trees track
certified "collision" events and are rare in contest DPs.

## Coordinates and Overflow

- Cross products: (b3 - b1) * (m2 - m1) reaches ~10^27 with 64-bit-ish
  inputs -- promote to __int128 in C++; doubles (53 bits) are not safe.
- A Li Chao query outside the built domain walks off the implicit tree;
  clamp or pad. The tree array must be sized to the domain, not to n.
- Parallel lines: no intersection exists; discard the dominated
  intercept before any crossing arithmetic.
- min vs max flips every comparison (midpoint swap, endpoint tests, bad
  test); rewriting is safer than negating intercepts.

## Reference Implementation

Iterative Li Chao over a power-of-two domain, cross-checked against the
naive minimum over all inserted lines, including a late insertion and a
parallel-slope probe. Real output (Python 3.12) follows the code.

```python
# Li Chao tree (iterative, power-of-two x-domain) cross-checked against
# the naive minimum over all inserted lines.

class LiChao:
    """Lines y = m*x + b over integer domain [0, size), size a power of 2.
    tree[node] holds the line best at the node's midpoint; node 1 = root."""
    def __init__(self, log2_size):
        self.size = 1 << log2_size
        self.tree = [None] * (2 * self.size)   # lines as (m, b) tuples
    def _f(self, line, x):
        return line[0] * x + line[1]
    def insert(self, line):
        node, lo, hi = 1, 0, self.size
        while True:
            mid = (lo + hi) // 2
            cur = self.tree[node]
            if cur is None or self._f(line, mid) < self._f(cur, mid):
                self.tree[node], line = line, cur   # keep better-at-mid here
                if line is None:
                    return
                cur = self.tree[node]
            if hi - lo == 1:
                return
            # the surviving "line" may still win on one side of mid
            left_win = self._f(line, lo) < self._f(cur, lo)
            right_win = self._f(line, hi - 1) < self._f(cur, hi - 1)
            if left_win and not right_win:
                node, hi = 2 * node, mid
            elif right_win and not left_win:
                node, lo = 2 * node + 1, mid
            else:
                return
    def query(self, x):
        best = None
        node, lo, hi = 1, 0, self.size
        while True:
            line = self.tree[node]
            if line is not None:
                v = self._f(line, x)
                best = v if best is None else min(best, v)
            if hi - lo == 1:
                return best
            mid = (lo + hi) // 2
            if x < mid:
                node, hi = 2 * node, mid
            else:
                node, lo = 2 * node + 1, mid

def naive(lines, x):
    return min(m * x + b for m, b in lines)

if __name__ == "__main__":
    print("Demo 1: envelope after each insertion (domain [0, 16))")
    lc = LiChao(4)                       # size 16
    demo = [(1, 0), (-1, 10), (0, 3)]    # y=x, y=-x+10, y=3
    for m, b in demo:
        lc.insert((m, b))
        vals = [lc.query(x) for x in range(16)]
        print(f"  after y = {m}x + {b}: min value {min(vals):>3} at x = "
              f"{min(range(16), key=vals.__getitem__)}")
    print("Envelope check: lichao vs naive at every x in [0,16):")
    print("  all 16 points agree:",
          all(lc.query(x) == naive(demo, x) for x in range(16)))
    xs = [0, 3, 5, 8, 12, 15]
    print("  x       :", xs)
    print("  lichao  :", [lc.query(x) for x in xs])
    print("  naive   :", [naive(demo, x) for x in xs])
    print()
    print("Demo 2: randomized cross-check, domain [0, 1024)")
    import random
    random.seed(7)
    lc2 = LiChao(10)
    lines = [(random.randint(-20, 20), random.randint(-5000, 5000))
             for _ in range(500)]
    for m, b in lines:
        lc2.insert((m, b))
    queries = [random.randint(0, 1023) for _ in range(500)]
    bad = sum(1 for x in queries if lc2.query(x) != naive(lines, x))
    print(f"  lines inserted: 500   random queries: 500   mismatches: {bad}"
          f"   {'ALL OK' if bad == 0 else 'FAILED'}")
    extra = (13, -100)                 # late insertion must also work
    lc2.insert(extra)
    lines.append(extra)
    queries2 = [random.randint(0, 1023) for _ in range(500)]
    bad2 = sum(1 for x in queries2 if lc2.query(x) != naive(lines, x))
    print(f"  after late insert (13,-100): 500 queries, mismatches: {bad2}"
          f"   {'ALL OK' if bad2 == 0 else 'FAILED'}")
    lc3 = LiChao(5)                    # parallel slopes: better intercept wins
    for b in (100, 7, 99):
        lc3.insert((2, b))
    print("  parallel slopes (m=2, b=100/7/99): query(3) =",
          lc3.query(3), " expected", 2 * 3 + 7)
```

```text
Demo 1: envelope after each insertion (domain [0, 16))
  after y = 1x + 0: min value   0 at x = 0
  after y = -1x + 10: min value  -5 at x = 15
  after y = 0x + 3: min value  -5 at x = 15
Envelope check: lichao vs naive at every x in [0,16):
  all 16 points agree: True
  x       : [0, 3, 5, 8, 12, 15]
  lichao  : [0, 3, 3, 2, -2, -5]
  naive   : [0, 3, 3, 2, -2, -5]

Demo 2: randomized cross-check, domain [0, 1024)
  lines inserted: 500   random queries: 500   mismatches: 0   ALL OK
  after late insert (13,-100): 500 queries, mismatches: 0   ALL OK
  parallel slopes (m=2, b=100/7/99): query(3) = 13  expected 13
```

The run reproduces the ASCII envelope above: y = 3 clips the bowl of
y = x and y = -x + 10 exactly on [3, 7].

## Failure Modes

- Pointer-walk CHT fed unsorted queries: the pointer invariant dies and
  answers silently degrade -- works on the sample, WA on stress. Switch
  to Li Chao.
- Cross-product overflow in the bad test pops wrong lines and corrupts
  the envelope while the code keeps running. Promote to __int128 first.
- Li Chao array sized to n instead of the x-domain, or queries outside
  [0, size): out-of-domain access on the implicit tree.
- Equal slopes with different intercepts must drop the dominated line,
  or crossing arithmetic divides by zero.
- min vs max: flip every comparison deliberately; negating intercepts
  alone produces a subtly wrong envelope.

## References

- [cp-algorithms: Convex hull trick and Li Chao tree](https://cp-algorithms.com/geometry/convex_hull_trick.html)
- [KACTL LineContainer (dynamic CHT via ordered set)](https://github.com/kth-competitive-programming/kactl/blob/main/content/data-structures/LineContainer.h)
- [PEGWiki: Convex hull trick](https://wcipeg.com/wiki/Convex_hull_trick)
- [Codeforces 319C "Kalila and Dimna in the Logging Industry"](https://codeforces.com/contest/319/problem/C)
- [Codeforces 631E "Product Sum" (move one element, CHT)](https://codeforces.com/contest/631/problem/E)
