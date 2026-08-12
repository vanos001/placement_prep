# Chapter 178: Burnside's Lemma & Pólya Enumeration

## 1. Definition

**Burnside's Lemma** (also called the **Cauchy-Frobenius Lemma**) counts the number of distinct objects under group actions — that is, the number of **orbits** (equivalence classes) when symmetries are taken into account.

**Theorem**: Let G be a finite group acting on a finite set X. The number of orbits is:

```
|X/G| = (1/|G|) · Σ_{g ∈ G} |Fix(g)|
```

where |Fix(g)| is the number of elements of X that are **fixed** (unchanged) by the group element g.

**Pólya Enumeration Theorem** generalizes this to count objects by **weight**, enabling us to count the number of distinct colorings, arrangements, or structures with specific properties.

## 2. Motivation

### The Counting Problem

How many distinct necklaces can you make with 4 beads, each colored red or blue?

- Total arrangements: 2⁴ = 16
- But rotations (and possibly reflections) make some equivalent
- "RRBB" and "BBRR" are the same necklace (rotation by 2)

Naively enumerating and removing duplicates is error-prone. Burnside's lemma gives a **formula** that counts correctly.

### Why Should Programmers Care?

1. **Competitive programming**: Problems asking "how many distinct X up to symmetry" appear regularly.
2. **Combinatorics on words**: Count distinct strings under cyclic shifts.
3. **Graph theory**: Count non-isomorphic graphs, colorings.
4. **Chemistry**: Count distinct molecules with given bonding patterns.
5. **Puzzle solving**: Count distinct configurations of Rubik's cube, sliding puzzles, etc.

## 3. Intuition: The Averaging Argument

### Group Actions and Orbits

A **group action** of G on X means each element g ∈ G transforms each x ∈ X into some g·x ∈ X, satisfying:
- Identity: e·x = x for all x
- Compatibility: (gh)·x = g·(h·x)

The **orbit** of x is {g·x : g ∈ G} — all positions reachable from x via symmetries.

An element x is **fixed** by g if g·x = x.

### Why Averaging Works

Imagine a table where rows are group elements g and columns are elements x ∈ X. Put a 1 in cell (g, x) if g fixes x.

- **Sum by rows**: Σ_g |Fix(g)| = total number of 1s in the table
- **Sum by columns**: Σ_x |Stab(x)| = total number of 1s in the table (where Stab(x) is the stabilizer subgroup)

By the orbit-stabilizer theorem: |Stab(x)| · |Orbit(x)| = |G|, so |Stab(x)| = |G| / |Orbit(x)|.

Therefore:
```
Σ_g |Fix(g)| = Σ_x |G| / |Orbit(x)| = |G| · Σ_x 1/|Orbit(x)|
```

Elements in the same orbit contribute |Orbit| · (1/|Orbit|) = 1 each. So the sum equals |G| · (number of orbits).

Dividing by |G| gives the number of orbits. ∎

## 4. Formal Treatment

### 4.1 Group Actions

**Definition**: A group action of G on X is a function G × X → X satisfying:
1. e · x = x for all x ∈ X (identity)
2. (g₁g₂) · x = g₁ · (g₂ · x) for all g₁, g₂ ∈ G, x ∈ X (compatibility)

### 4.2 Key Subgroups and Sets

| Concept | Definition | Formula |
|---------|-----------|---------|
| **Orbit** of x | All elements reachable from x | Orb(x) = {g·x : g ∈ G} |
| **Stabilizer** of x | All elements that fix x | Stab(x) = {g ∈ G : g·x = x} |
| **Fixed set** of g | All elements fixed by g | Fix(g) = {x ∈ X : g·x = x} |
| **Orbit space** | Set of all orbits | X/G = {Orb(x) : x ∈ X} |

### 4.3 Orbit-Stabilizer Theorem

|Orb(x)| · |Stab(x)| = |G|

### 4.4 Burnside's Lemma

|X/G| = (1/|G|) Σ_{g ∈ G} |Fix(g)|

### 4.5 Pólya Enumeration Theorem

Let G act on a set of n positions, and let c be the number of available colors. Define the **cycle index**:

```
Z(G; t₁, t₂, ..., tₙ) = (1/|G|) Σ_{g ∈ G} t₁^{c₁(g)} · t₂^{c₂(g)} · ... · tₙ^{cₙ(g)}
```

where cᵢ(g) is the number of cycles of length i in the permutation g.

The number of distinct colorings using c colors is:

```
Z(G; c, c, ..., c) = (1/|G|) Σ_{g ∈ G} c^{cycles(g)}
```

where cycles(g) is the total number of cycles in g.

## 5. Step-by-Step Walkthrough

### Example 1: Binary Necklaces of Length 4

**Problem**: How many distinct binary strings of length 4 exist, up to rotation?

**Setup**:
- X = all 2⁴ = 16 binary strings of length 4
- G = cyclic group C₄ = {r⁰, r¹, r², r³} where r is rotation by 1 position
- |G| = 4

**Step 1**: Identify Fix(g) for each rotation.

**r⁰ (identity)**: Fixes everything. |Fix(r⁰)| = 16.

**r¹ (rotate by 1)**: A string is fixed iff all characters are the same.
- Fixed strings: 0000, 1111
- |Fix(r¹)| = 2

**r² (rotate by 2)**: A string abcd is fixed iff a=c and b=d.
- Fixed strings: 0000, 0101, 1010, 1111
- |Fix(r²)| = 4

**r³ (rotate by 3)**: Same as rotate by 1 (reverse direction).
- |Fix(r³)| = 2

**Step 2**: Apply Burnside's lemma.
```
|X/G| = (1/4)(16 + 2 + 4 + 2) = 24/4 = 6
```

**Step 3**: Verify by enumeration.
The 6 distinct necklaces are:
1. 0000
2. 0001 (≡ 0010 ≡ 0100 ≡ 1000)
3. 0011 (≡ 0110 ≡ 1100 ≡ 1001)
4. 0101 (≡ 1010)
5. 0111 (≡ 1110 ≡ 1101 ≡ 1011)
6. 1111

✓

### Example 2: Binary Bracelets of Length 4

**Problem**: Same as above, but also allow reflection (flip).

**Setup**:
- G = dihedral group D₄ = {r⁰, r¹, r², r³, f₀, f₁, f₂, f₃}
- where fᵢ are the 4 reflections (for n=4: 2 axis-through-vertices + 2 axis-through-edges)
- |G| = 8

**Rotations** (same as before):
- |Fix(r⁰)| = 16, |Fix(r¹)| = 2, |Fix(r²)| = 4, |Fix(r³)| = 2

**Reflections**:

For n=4, there are 4 reflections. Let's use the 2 types:

**f₀, f₁ (reflect through opposite vertices)**: Fixes strings where the axis characters are free and the other pairs match.
- Pattern: a b a b (no, that's wrong for vertex reflection)
- For vertex reflection through positions 0 and 2: a, b, a, d → need a=a (trivially) and b=d
- So: 2² · 2 = 8 strings fixed? Let me be more careful.

Actually, let's label positions 0,1,2,3.

**Reflection through axis between positions 0 and 1 (and 2 and 3)**:
- Maps: 0↔3, 1↔2
- String abcd fixed iff a=d and b=c
- 2² = 4 strings: 0000, 0110, 1001, 1111

**Reflection through axis between positions 1 and 2 (and 3 and 0)**:
- Maps: 0↔1, 2↔3
- String abcd fixed iff a=b and c=d
- 2² = 4 strings: 0000, 0011, 1100, 1111

**Reflection through axis through positions 0 and 2**:
- Maps: 1↔3, fixes 0 and 2
- String abcd fixed iff b=d
- 2³ = 8 strings (a, b, c, b for any a,b,c)

**Reflection through axis through positions 1 and 3**:
- Maps: 0↔2, fixes 1 and 3
- String abcd fixed iff a=c
- 2³ = 8 strings

So for the 4 reflections: |Fix| = 4, 4, 8, 8.

**Burnside**:
```
|X/G| = (1/8)(16 + 2 + 4 + 2 + 4 + 4 + 8 + 8) = 48/8 = 6
```

Hmm, same as rotation-only for n=4, c=2. Let me verify... Actually for n=4, c=2, the answer is indeed 6 for both necklaces and bracelets. This is because the bracelet symmetries don't merge any additional orbits in this specific case.

For a different example: n=4, c=3 (3 colors):
- Rotations: (81 + 3 + 9 + 3)/4 = 96/4 = 24 necklaces
- With reflections: (81 + 3 + 9 + 3 + 9 + 9 + 27 + 27)/8 = 168/8 = 21 bracelets

### Example 3: Cube Face Coloring

**Problem**: Color the faces of a cube with 3 colors. How many distinct colorings?

**Setup**: The rotation group of a cube has 24 elements:
- 1 identity
- 6 face rotations (90° and 270° around 3 axes): 4 cycles of length 1 + 1 cycle of length 4... no, let me think again.

Actually, the rotation group of a cube (acting on 6 faces):
1. **Identity** (1): 6 cycles of length 1 → c = 6
2. **90° face rotation** (6): 2 fixed faces + 1 cycle of 4 → c = 3
3. **180° face rotation** (3): 2 fixed faces + 2 cycles of 2 → c = 4
4. **120° vertex rotation** (8): 2 cycles of 3 → c = 2
5. **180° edge rotation** (6): 3 cycles of 2 → c = 3

Total: 1 + 6 + 3 + 8 + 6 = 24 ✓

**Apply Pólya**:
```
Z = (1/24)(3⁶ + 6·3³ + 3·3⁴ + 8·3² + 6·3³)
  = (1/24)(729 + 6·27 + 3·81 + 8·9 + 6·27)
  = (1/24)(729 + 162 + 243 + 72 + 162)
  = (1/24)(1368)
  = 57
```

There are **57** distinct ways to color a cube with 3 colors.

## 6. Code Implementations

### 6.1 C++ — Burnside's Lemma for Necklaces

```cpp
#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1e9 + 7;

long long power(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

long long mod_inv(long long a, long long mod) {
    return power(a, mod - 2, mod);
}

/**
 * Count distinct necklaces with n beads and c colors.
 * Necklaces: equivalence under rotation only.
 * 
 * Burnside: answer = (1/n) * Σ_{d|n} φ(n/d) * c^d
 * where φ is Euler's totient function.
 * 
 * Time: O(√n * log n)
 */
long long count_necklaces(int n, int c) {
    // Compute Euler's totient
    auto euler_totient = [](int m) -> long long {
        long long result = m;
        for (int p = 2; p * p <= m; p++) {
            if (m % p == 0) {
                while (m % p == 0) m /= p;
                result = result / p * (p - 1);
            }
        }
        if (m > 1) result = result / m * (m - 1);
        return result;
    };

    long long ans = 0;
    // Sum over all divisors d of n
    // Rotation by k positions has gcd(n,k) cycles, each of length n/gcd(n,k)
    // Equivalently: for each d | n, there are φ(n/d) rotations with exactly d cycles
    for (int d = 1; d * d <= n; d++) {
        if (n % d == 0) {
            // d is a divisor
            ans = (ans + euler_totient(n / d) % MOD * power(c, d, MOD) % MOD) % MOD;
            // n/d is also a divisor (if different)
            if (d * d != n) {
                ans = (ans + euler_totient(d) % MOD * power(c, n / d, MOD) % MOD) % MOD;
            }
        }
    }
    ans = ans % MOD * mod_inv(n, MOD) % MOD;
    return ans;
}

/**
 * Count distinct bracelets with n beads and c colors.
 * Bracelets: equivalence under rotation AND reflection.
 * 
 * If n is odd:  answer = (necklaces + c^((n+1)/2)) / 2
 * If n is even: answer = (necklaces + (c^(n/2) + c^(n/2+1)) / 2) / 2
 * 
 * Actually, more precisely:
 * answer = (necklaces_count * n + reflection_fixed) / (2n)
 * 
 * For reflections:
 * - n odd: each reflection fixes c^((n+1)/2) colorings, n reflections
 * - n even: n/2 reflections through vertices fix c^(n/2), 
 *           n/2 reflections through edges fix c^(n/2+1)
 */
long long count_bracelets(int n, int c) {
    long long necklaces = count_necklaces(n, c);

    long long reflection_fixed;
    if (n % 2 == 1) {
        // n reflections, each fixes c^((n+1)/2)
        reflection_fixed = (long long)n * power(c, (n + 1) / 2, MOD) % MOD;
    } else {
        // n/2 through-vertex reflections: fix c^(n/2)
        // n/2 through-edge reflections: fix c^(n/2 + 1)
        reflection_fixed = ((long long)(n / 2) * power(c, n / 2, MOD) % MOD +
                           (long long)(n / 2) * power(c, n / 2 + 1, MOD) % MOD) % MOD;
    }

    // Burnside with 2n group elements (n rotations + n reflections)
    long long total = (necklaces % MOD * n % MOD + reflection_fixed) % MOD;
    return total % MOD * mod_inv(2 * n % MOD, MOD) % MOD;
}

/**
 * Direct Burnside for necklaces (alternative implementation)
 * For each rotation k (0 to n-1), count fixed colorings.
 * Rotation k has gcd(n,k) cycles, each of length n/gcd(n,k).
 * A coloring is fixed iff all beads in each cycle have the same color.
 * So |Fix(r^k)| = c^gcd(n,k).
 */
long long count_necklaces_direct(int n, int c) {
    long long ans = 0;
    for (int k = 0; k < n; k++) {
        int g = __gcd(n, k);
        ans = (ans + power(c, g, MOD)) % MOD;
    }
    return ans * mod_inv(n, MOD) % MOD;
}

int main() {
    int n = 4, c = 2;
    cout << "Necklaces (n=" << n << ", c=" << c << "): " << count_necklaces(n, c) << endl;
    cout << "Bracelets (n=" << n << ", c=" << c << "): " << count_bracelets(n, c) << endl;
    cout << "Direct necklace count: " << count_necklaces_direct(n, c) << endl;

    n = 6; c = 3;
    cout << "\nNecklaces (n=" << n << ", c=" << c << "): " << count_necklaces(n, c) << endl;
    cout << "Bracelets (n=" << n << ", c=" << c << "): " << count_bracelets(n, c) << endl;

    return 0;
}
```

### 6.2 C++ — Pólya Enumeration for General Group Actions

```cpp
#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1e9 + 7;

long long power(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

long long mod_inv(long long a, long long mod) {
    return power(a, mod - 2, mod);
}

/**
 * Pólya enumeration for a general permutation group.
 * 
 * permutations: vector of permutations (each is a vector<int> of length n)
 * n: number of positions
 * c: number of colors
 * 
 * For each permutation, count the number of cycles.
 * Answer = (1/|G|) * Σ c^{cycles(g)}
 * 
 * Time: O(|G| * n)
 */
long long polya_count(const vector<vector<int>>& permutations, int n, int c) {
    long long ans = 0;
    for (const auto& perm : permutations) {
        // Count cycles in this permutation
        vector<bool> visited(n, false);
        int cycles = 0;
        for (int i = 0; i < n; i++) {
            if (!visited[i]) {
                cycles++;
                int j = i;
                while (!visited[j]) {
                    visited[j] = true;
                    j = perm[j];
                }
            }
        }
        ans = (ans + power(c, cycles, MOD)) % MOD;
    }
    return ans * mod_inv(permutations.size(), MOD) % MOD;
}

/**
 * Generate all rotations of a cyclic group C_n
 */
vector<vector<int>> generate_rotations(int n) {
    vector<vector<int>> perms;
    for (int k = 0; k < n; k++) {
        vector<int> perm(n);
        for (int i = 0; i < n; i++)
            perm[i] = (i + k) % n;
        perms.push_back(perm);
    }
    return perms;
}

/**
 * Generate dihedral group D_n (rotations + reflections)
 */
vector<vector<int>> generate_dihedral(int n) {
    vector<vector<int>> perms = generate_rotations(n);
    // Add reflections
    for (int k = 0; k < n; k++) {
        vector<int> perm(n);
        for (int i = 0; i < n; i++)
            perm[i] = (k - i + n) % n; // reflect then rotate
        perms.push_back(perm);
    }
    return perms;
}

int main() {
    int n = 4, c = 2;

    // Necklace (cyclic group)
    auto rotations = generate_rotations(n);
    cout << "Necklaces: " << polya_count(rotations, n, c) << endl;

    // Bracelet (dihedral group)
    auto dihedral = generate_dihedral(n);
    cout << "Bracelets: " << polya_count(dihedral, n, c) << endl;

    // Cube face coloring
    // The cube rotation group on 6 faces has 24 elements
    // We can enumerate them or use the formula directly
    cout << "\nCube face coloring with 3 colors:" << endl;
    long long cube_ans = (power(3, 6, MOD) +
                         6 * power(3, 3, MOD) % MOD +
                         3 * power(3, 4, MOD) % MOD +
                         8 * power(3, 2, MOD) % MOD +
                         6 * power(3, 3, MOD) % MOD) % MOD;
    cube_ans = cube_ans * mod_inv(24, MOD) % MOD;
    cout << "Answer: " << cube_ans << endl; // 57

    return 0;
}
```

### 6.3 Python — Burnside's Lemma and Pólya Enumeration

```python
from math import gcd
from functools import lru_cache

MOD = 10**9 + 7

def power(base, exp, mod=MOD):
    """Fast modular exponentiation"""
    result = 1
    base %= mod
    while exp > 0:
        if exp & 1:
            result = result * base % mod
        base = base * base % mod
        exp >>= 1
    return result

def mod_inv(a, mod=MOD):
    return power(a, mod - 2, mod)

def euler_totient(n):
    """Compute Euler's totient function φ(n)"""
    result = n
    p = 2
    while p * p <= n:
        if n % p == 0:
            while n % p == 0:
                n //= p
            result = result // p * (p - 1)
        p += 1
    if n > 1:
        result = result // n * (n - 1)
    return result


def count_necklaces(n, c):
    """
    Count distinct necklaces with n beads and c colors.
    
    Uses Burnside's lemma with the cyclic group C_n.
    Rotation by k positions has gcd(n,k) cycles.
    
    Formula: (1/n) * Σ_{d|n} φ(n/d) * c^d
    
    Time: O(√n * log n)
    """
    ans = 0
    for d in range(1, n + 1):
        if n % d == 0:
            ans = (ans + euler_totient(n // d) * power(c, d)) % MOD
    return ans * mod_inv(n) % MOD


def count_bracelets(n, c):
    """
    Count distinct bracelets with n beads and c colors.
    
    Bracelets = necklaces + reflection symmetry.
    
    Time: O(√n * log n)
    """
    necklaces = count_necklaces(n, c)

    if n % 2 == 1:
        reflection_fixed = n * power(c, (n + 1) // 2) % MOD
    else:
        half = n // 2
        reflection_fixed = (half * power(c, half) + half * power(c, half + 1)) % MOD

    total = (necklaces * n + reflection_fixed) % MOD
    return total * mod_inv(2 * n) % MOD


def polya_count(permutations, n, c):
    """
    Pólya enumeration for a general permutation group.
    
    permutations: list of permutations (each is a list of length n)
    n: number of positions
    c: number of colors
    
    Time: O(|G| * n)
    """
    ans = 0
    for perm in permutations:
        # Count cycles
        visited = [False] * n
        cycles = 0
        for i in range(n):
            if not visited[i]:
                cycles += 1
                j = i
                while not visited[j]:
                    visited[j] = True
                    j = perm[j]
        ans = (ans + power(c, cycles)) % MOD

    return ans * mod_inv(len(permutations)) % MOD


def generate_rotations(n):
    """Generate cyclic group C_n as permutations"""
    return [[(i + k) % n for i in range(n)] for k in range(n)]


def generate_dihedral(n):
    """Generate dihedral group D_n (rotations + reflections)"""
    perms = generate_rotations(n)
    for k in range(n):
        perms.append([(k - i + n) % n for i in range(n)])
    return perms


def count_distinct_strings(s):
    """
    Count distinct strings obtainable by rotating s.
    This is the size of the orbit of s under cyclic rotation.
    
    Uses Burnside: orbit_size = |G| / |Stab(s)|
    where Stab(s) = number of rotations that fix s.
    """
    n = len(s)
    # Count rotations that fix s (period of s)
    stab_size = 0
    for k in range(n):
        if all(s[(i + k) % n] == s[i] for i in range(n)):
            stab_size += 1
    return n // stab_size


def necklace_enumeration(n, c):
    """
    Enumerate all distinct necklaces (for small n and c).
    Returns list of representative strings.
    """
    def canonical(s):
        """Lexicographically smallest rotation"""
        n = len(s)
        return min(s[i:] + s[:i] for i in range(n))

    seen = set()
    # Generate all c^n strings
    def generate(pos, current):
        if pos == n:
            canon = canonical(current)
            seen.add(canon)
            return
        for color in range(c):
            generate(pos + 1, current + str(color))

    generate(0, "")
    return sorted(seen)


# === Applications ===

def count_necklaces_with_constraints(n, c, constraint_fn=None):
    """
    Count necklaces with constraints using Burnside.
    constraint_fn: function(coloring) -> bool
    
    For small n only (exponential in n).
    """
    rotations = generate_rotations(n)
    ans = 0

    for rot in rotations:
        # Count colorings fixed by this rotation that satisfy constraint
        fixed_count = 0
        # A coloring fixed by rot must be constant on each cycle
        # Find cycles
        visited = [False] * n
        cycles = []
        for i in range(n):
            if not visited[i]:
                cycle = []
                j = i
                while not visited[j]:
                    visited[j] = True
                    cycle.append(j)
                    j = rot[j]
                cycles.append(cycle)

        # Enumerate colorings constant on cycles
        def enumerate_cycles(cycle_idx, coloring):
            nonlocal fixed_count
            if cycle_idx == len(cycles):
                if constraint_fn is None or constraint_fn(coloring):
                    fixed_count += 1
                return
            for color in range(c):
                for pos in cycles[cycle_idx]:
                    coloring[pos] = color
                enumerate_cycles(cycle_idx + 1, coloring)

        enumerate_cycles(0, [0] * n)
        ans += fixed_count

    return ans * mod_inv(len(rotations)) % MOD


def count_graph_colorings(n, edges, c):
    """
    Count distinct vertex colorings of a graph with c colors.
    Two colorings are equivalent if a graph automorphism maps one to the other.
    
    This is a more complex application of Pólya enumeration.
    For small graphs only.
    """
    from itertools import permutations

    # Find all graph automorphisms
    def is_automorphism(perm):
        """Check if perm is a graph automorphism"""
        for u, v in edges:
            if (perm[u], perm[v]) not in edges and (perm[v], perm[u]) not in edges:
                return False
        return True

    automorphisms = []
    for perm in permutations(range(n)):
        perm = list(perm)
        if is_automorphism(perm):
            automorphisms.append(perm)

    if not automorphisms:
        automorphisms = [list(range(n))]  # Identity only

    return polya_count(automorphisms, n, c)


# === Demo ===
if __name__ == "__main__":
    # Necklace counting
    print("=== Necklaces and Bracelets ===")
    for n in range(1, 11):
        nc = count_necklaces(n, 2)
        bc = count_bracelets(n, 2)
        print(f"n={n:2d}: necklaces={nc:4d}, bracelets={bc:4d}")

    print(f"\nNecklaces(4, 2) = {count_necklaces(4, 2)}")  # 6
    print(f"Necklaces(6, 3) = {count_necklaces(6, 3)}")  # 130

    # Pólya for general groups
    print("\n=== Pólya Enumeration ===")
    perms = generate_rotations(4)
    print(f"C4 on 4 positions, 2 colors: {polya_count(perms, 4, 2)}")

    perms = generate_dihedral(4)
    print(f"D4 on 4 positions, 2 colors: {polya_count(perms, 4, 2)}")

    # Enumeration verification
    print("\n=== Enumeration Verification ===")
    necklaces = necklace_enumeration(4, 2)
    print(f"Distinct necklaces of length 4 with 2 colors: {len(necklaces)}")
    for n in necklaces:
        print(f"  {n}")

    # Cube coloring
    print("\n=== Cube Face Coloring ===")
    c = 3
    ans = (power(c, 6) + 6*power(c, 3) + 3*power(c, 4) +
           8*power(c, 2) + 6*power(c, 3)) % MOD
    ans = ans * mod_inv(24) % MOD
    print(f"Cube with {c} colors: {ans}")  # 57
```

### 6.4 Python — Weighted Pólya Enumeration

```python
def polya_weighted(permutations, n, weights):
    """
    Weighted Pólya enumeration.
    Instead of c colors, each position has a set of weighted choices.
    
    permutations: group elements as permutations
    n: number of positions
    weights: dict mapping (cycle_structure) -> generating_function
    
    Returns the generating function for distinct colorings.
    """
    from collections import Counter

    cycle_index_terms = []

    for perm in permutations:
        # Find cycle structure
        visited = [False] * n
        cycle_lengths = []
        for i in range(n):
            if not visited[i]:
                length = 0
                j = i
                while not visited[j]:
                    visited[j] = True
                    j = perm[j]
                    length += 1
                cycle_lengths.append(length)

        cycle_structure = Counter(cycle_lengths)
        cycle_index_terms.append(cycle_structure)

    # For counting with c colors: replace each t_i with c
    # This gives the standard Pólya count
    return cycle_index_terms


def count_orbit_representatives(n, c, group_perms):
    """
    Count orbit representatives (distinct objects) under a group action.
    Also returns one representative per orbit (for small n).
    """
    visited = set()
    orbits = []

    # Generate all colorings
    def generate_all(pos, current):
        if pos == n:
            yield tuple(current)
            return
        for color in range(c):
            yield from generate_all(pos + 1, current + [color])

    for coloring in generate_all(0, []):
        if coloring in visited:
            continue
        # Found a new orbit representative
        orbits.append(coloring)
        # Mark all elements in this orbit
        for perm in group_perms:
            transformed = tuple(coloring[perm[i]] for i in range(n))
            visited.add(transformed)

    return orbits
```

### 6.5 Java — Burnside's Lemma

```java
import java.util.*;

public class BurnsideLemma {

    static final long MOD = 1_000_000_007L;

    static long power(long base, long exp, long mod) {
        long result = 1;
        base %= mod;
        while (exp > 0) {
            if ((exp & 1) == 1) result = result * base % mod;
            base = base * base % mod;
            exp >>= 1;
        }
        return result;
    }

    static long modInv(long a, long mod) {
        return power(a, mod - 2, mod);
    }

    static long eulerTotient(int n) {
        long result = n;
        for (int p = 2; p * p <= n; p++) {
            if (n % p == 0) {
                while (n % p == 0) n /= p;
                result = result / p * (p - 1);
            }
        }
        if (n > 1) result = result / n * (n - 1);
        return result;
    }

    /**
     * Count distinct necklaces with n beads and c colors.
     * Formula: (1/n) * Σ_{d|n} φ(n/d) * c^d
     */
    static long countNecklaces(int n, int c) {
        long ans = 0;
        for (int d = 1; d * d <= n; d++) {
            if (n % d == 0) {
                ans = (ans + eulerTotient(n / d) % MOD * power(c, d, MOD) % MOD) % MOD;
                if (d * d != n) {
                    ans = (ans + eulerTotient(d) % MOD * power(c, n / d, MOD) % MOD) % MOD;
                }
            }
        }
        return ans * modInv(n, MOD) % MOD;
    }

    /**
     * Count distinct bracelets with n beads and c colors.
     */
    static long countBracelets(int n, int c) {
        long necklaces = countNecklaces(n, c);
        long reflectionFixed;
        if (n % 2 == 1) {
            reflectionFixed = (long) n * power(c, (n + 1) / 2, MOD) % MOD;
        } else {
            int half = n / 2;
            reflectionFixed = ((long) half * power(c, half, MOD) % MOD +
                              (long) half * power(c, half + 1, MOD) % MOD) % MOD;
        }
        long total = (necklaces * n % MOD + reflectionFixed) % MOD;
        return total * modInv(2L * n, MOD) % MOD;
    }

    /**
     * Pólya enumeration for a general permutation group.
     */
    static long polyaCount(List<int[]> permutations, int n, int c) {
        long ans = 0;
        for (int[] perm : permutations) {
            boolean[] visited = new boolean[n];
            int cycles = 0;
            for (int i = 0; i < n; i++) {
                if (!visited[i]) {
                    cycles++;
                    int j = i;
                    while (!visited[j]) {
                        visited[j] = true;
                        j = perm[j];
                    }
                }
            }
            ans = (ans + power(c, cycles, MOD)) % MOD;
        }
        return ans * modInv(permutations.size(), MOD) % MOD;
    }

    static List<int[]> generateRotations(int n) {
        List<int[]> perms = new ArrayList<>();
        for (int k = 0; k < n; k++) {
            int[] perm = new int[n];
            for (int i = 0; i < n; i++) perm[i] = (i + k) % n;
            perms.add(perm);
        }
        return perms;
    }

    static List<int[]> generateDihedral(int n) {
        List<int[]> perms = generateRotations(n);
        for (int k = 0; k < n; k++) {
            int[] perm = new int[n];
            for (int i = 0; i < n; i++) perm[i] = (k - i + n) % n;
            perms.add(perm);
        }
        return perms;
    }

    public static void main(String[] args) {
        System.out.println("=== Necklaces and Bracelets ===");
        for (int n = 1; n <= 10; n++) {
            System.out.printf("n=%2d: necklaces=%4d, bracelets=%4d%n",
                n, countNecklaces(n, 2), countBracelets(n, 2));
        }

        System.out.println("\n=== Pólya Enumeration ===");
        int n = 4, c = 2;
        System.out.println("C4, 2 colors: " + polyaCount(generateRotations(n), n, c));
        System.out.println("D4, 2 colors: " + polyaCount(generateDihedral(n), n, c));
    }
}
```

## 7. Complexity Analysis

| Algorithm | Time | Space | Notes |
|-----------|------|-------|-------|
| Necklace count (formula) | O(√n · log n) | O(1) | Using divisor enumeration + totient |
| Bracelet count (formula) | O(√n · log n) | O(1) | Necklace + reflection term |
| Direct Burnside (enumerate G) | O(\|G\| · n) | O(n) | For general groups |
| Pólya enumeration | O(\|G\| · n) | O(n) | Count cycles per permutation |
| Orbit enumeration | O(cⁿ · \|G\| · n) | O(cⁿ) | Only for small n, c |

The formula-based approaches for necklaces/bracelets are extremely efficient. The general Pólya enumeration depends on the group size.

## 8. Applications

### 8.1 Necklace Problems in Competitive Programming

**Problem**: Given n positions and c colors, count distinct necklaces modulo 10⁹+7.

**Solution**: Direct application of the necklace formula.

### 8.2 String Equivalence

**Problem**: Two strings are equivalent if one is a rotation of the other. Count equivalence classes.

**Solution**: Burnside with the cyclic group. The number of distinct rotations of a string s with period p is n/p.

### 8.3 Graph Coloring Under Symmetry

**Problem**: Color the vertices of a graph with c colors, where two colorings are equivalent if an automorphism maps one to the other.

**Solution**: Find all graph automorphisms (hard in general, but feasible for small/symmetric graphs), then apply Pólya.

### 8.4 Tiling Problems

**Problem**: Count distinct ways to tile a 2×n board with dominoes, where rotations of the board are considered equivalent.

**Solution**: The board has a rotation symmetry group; apply Burnside.

### 8.5 Chemical Isomers

In chemistry, counting distinct molecular structures with given bonding patterns reduces to Pólya enumeration over the symmetry group of the molecular graph.

## 9. Common Pitfalls

1. **Confusing necklaces and bracelets**: Necklaces allow rotation only; bracelets allow rotation AND reflection. Different formulas!
2. **Forgetting to divide by |G|**: The sum Σ |Fix(g)| counts each orbit |G| times. Always divide.
3. **Non-prime modular inverse**: When computing (1/|G|) mod M, ensure |G| is invertible mod M. For prime M, this is automatic if |G| < M.
4. **Wrong cycle count**: When computing |Fix(g)| for permutation g, the number of fixed colorings is c^{cycles(g)}, NOT c^{n-cycles(g)}.
5. **Overcounting reflections**: For dihedral groups, be careful about the number and type of reflections (depends on n being odd/even).

## 10. Exercises

### Warm-Up
1. How many distinct necklaces of length 5 with 2 colors exist? Compute using Burnside's lemma and verify by enumeration.
2. How many distinct bracelets of length 5 with 2 colors exist?
3. Verify that the number of distinct necklaces of length 6 with 2 colors is 14.

### Standard
4. Count the number of distinct ways to color the vertices of a regular pentagon with 3 colors (up to rotation).
5. Count the number of distinct ways to color the vertices of a regular pentagon with 3 colors (up to rotation AND reflection).
6. How many distinct dice are there? (A die has 6 faces, each labeled with 1-6 pips, with opposite faces summing to 7.) Hint: The rotation group of a cube has 24 elements.
7. Implement Pólya enumeration for a general permutation group. Test on the cube rotation group.

### Challenge
8. **[CEOI 2004]** Given a circular arrangement of n colored beads, count the number of distinct necklaces using exactly k different colors.
9. Count the number of distinct 3×3 binary matrices up to rotation (0°, 90°, 180°, 270°).
10. Design an algorithm to count distinct colorings of a graph with c colors under its automorphism group. What is the complexity?
11. Prove that the number of distinct binary necklaces of length n is (1/n) · Σ_{d|n} φ(d) · 2^{n/d}.

## 11. Interview Questions

1. **Q**: What is Burnside's lemma and how does it work?
   **A**: Burnside's lemma counts equivalence classes under group actions. The number of orbits equals the average number of fixed points: |X/G| = (1/|G|) Σ |Fix(g)|. Each group element g contributes the number of configurations unchanged by g.

2. **Q**: What's the difference between necklaces and bracelets?
   **A**: Necklaces allow rotation symmetry only (cyclic group Cₙ). Bracelets additionally allow reflection (dihedral group Dₙ). Bracelets always have ≤ necklaces.

3. **Q**: How would you count distinct strings up to cyclic rotation?
   **A**: Use Burnside with the cyclic group Cₙ. Rotation by k has gcd(n,k) cycles. The count is (1/n) · Σ_{k=0}^{n-1} c^{gcd(n,k)}, which simplifies to (1/n) · Σ_{d|n} φ(n/d) · c^d.

4. **Q**: When would you use Pólya enumeration vs. simple Burnside?
   **A**: Burnside counts the number of orbits. Pólya enumeration additionally tracks the "weight" or "type" of each coloring via generating functions — useful when you need to count colorings with specific numbers of each color.

5. **Q**: How does Burnside's lemma relate to group theory?
   **A**: It connects group actions (abstract algebra) to counting (combinatorics). The orbit-stabilizer theorem is the key bridge: |Orbit| · |Stab| = |G|. Burnside is essentially counting orbits by averaging fixed points.

## 12. Cross-References

- **Chapter 71: Combinatorics** — Counting principles, binomial coefficients
- **Chapter 33: Bit Manipulation** — Popcount connection to binary necklace counts
- **Chapter 70: Computational Models** — Group theory basics
- **Chapter 96: NP-Completeness** — Graph isomorphism (related to automorphism groups)
- **Chapter 162: Algorithmic Game Theory** — Symmetry in game states
- **Appendix G: Mathematics Handbook** — Euler's totient, modular arithmetic
