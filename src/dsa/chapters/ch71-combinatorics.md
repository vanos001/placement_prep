# Chapter 71: Combinatorics

## Prerequisites

- Basic math (factorials, modular arithmetic)
- Number theory (modular inverse)

## Interview Frequency: ★★★

Combinatorics appears in counting problems, probability calculations, and competitive programming. **Google**, **Meta**, and **Amazon** test combinatorial reasoning in problems involving counting, probability, and arrangement.

| Topic | Frequency | Difficulty | Notes |
|---|---|---|---|
| nCr / nPr | ★★★★ | Easy | Basic counting |
| Pascal's Triangle | ★★★ | Easy | Build and use |
| Stars and Bars | ★★★ | Medium | Distribution problems |
| Catalan Numbers | ★★★★ | Medium | Parentheses, trees |
| Inclusion-Exclusion | ★★★ | Medium | Counting with constraints |
| Derangements | ★★ | Medium | Permutations with restrictions |

---

## 71.1 Permutations and Combinations

### nPr: Permutations of r items from n

```
nPr = n! / (n-r)!
```

### nCr: Combinations of r items from n

```
nCr = n! / (r! × (n-r)!)
nCr = nCr-1 × (n-r+1) / r
```

```cpp
#include <iostream>
#include <vector>

const long long MOD = 1e9 + 7;

long long powerMod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

class Combinatorics {
    std::vector<long long> fact, invFact;
    long long mod;
    
public:
    Combinatorics(int n, long long mod) : fact(n + 1), invFact(n + 1), mod(mod) {
        fact[0] = 1;
        for (int i = 1; i <= n; i++) fact[i] = fact[i-1] * i % mod;
        invFact[n] = powerMod(fact[n], mod - 2, mod);
        for (int i = n - 1; i >= 0; i--) invFact[i] = invFact[i+1] * (i+1) % mod;
    }
    
    long long nCr(int n, int r) {
        if (r < 0 || r > n) return 0;
        return fact[n] % mod * invFact[r] % mod * invFact[n-r] % mod;
    }
    
    long long nPr(int n, int r) {
        if (r < 0 || r > n) return 0;
        return fact[n] % mod * invFact[n-r] % mod;
    }
};

int main() {
    Combinatorics comb(1000000, MOD);
    
    std::cout << "C(10, 3) = " << comb.nCr(10, 3) << "\n"; // 120
    std::cout << "C(100, 50) mod 1e9+7 = " << comb.nCr(100, 50) << "\n";
    std::cout << "P(10, 3) = " << comb.nPr(10, 3) << "\n"; // 720
    
    return 0;
}
```

---

## 71.2 Pascal's Triangle

```
C(n, r) = C(n-1, r-1) + C(n-1, r)
```

```cpp
#include <iostream>
#include <vector>

std::vector<std::vector<long long>> pascalsTriangle(int n, long long mod) {
    std::vector<std::vector<long long>> C(n + 1, std::vector<long long>(n + 1, 0));
    for (int i = 0; i <= n; i++) {
        C[i][0] = 1;
        for (int j = 1; j <= i; j++) {
            C[i][j] = (C[i-1][j-1] + C[i-1][j]) % mod;
        }
    }
    return C;
}

int main() {
    auto C = pascalsTriangle(10, 1000000007);
    
    std::cout << "Pascal's Triangle (first 6 rows):\n";
    for (int i = 0; i <= 5; i++) {
        for (int j = 0; j <= i; j++) {
            std::cout << C[i][j] << " ";
        }
        std::cout << "\n";
    }
    
    return 0;
}
```

---

## 71.3 Stars and Bars

**Problem**: Distribute n identical items into k distinct bins.

**Formula**: C(n + k - 1, k - 1)

### Example

Distribute 5 identical candies among 3 children: C(5 + 3 - 1, 3 - 1) = C(7, 2) = 21

```cpp
#include <iostream>

// C(n + k - 1, k - 1)
long long starsAndBars(int n, int k) {
    // Using iterative computation to avoid overflow
    long long result = 1;
    for (int i = 0; i < k - 1; i++) {
        result = result * (n + k - 1 - i) / (i + 1);
    }
    return result;
}

int main() {
    std::cout << "Distribute 5 candies among 3 children: " 
              << starsAndBars(5, 3) << "\n"; // 21
    std::cout << "Distribute 10 candies among 4 children: " 
              << starsAndBars(10, 4) << "\n"; // 286
    
    return 0;
}
```

---

## 71.4 Catalan Numbers

The n-th Catalan number: C(n) = C(2n, n) / (n + 1)

```
C(0) = 1, C(1) = 1, C(2) = 2, C(3) = 5, C(4) = 14, C(5) = 42
```

### Applications

| Problem | Catalan Number |
|---|---|
| Valid parenthesizations of n pairs | C(n) |
| Binary trees with n nodes | C(n) |
| Paths from (0,0) to (n,n) not above diagonal | C(n) |
| Triangulations of (n+2)-gon | C(n) |
| Stack-sortable permutations of length n | C(n) |

```cpp
#include <iostream>
#include <vector>

const long long MOD = 1e9 + 7;

long long powerMod(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = result * base % mod;
        base = base * base % mod;
        exp >>= 1;
    }
    return result;
}

// Catalan numbers using the formula C(n) = C(2n,n) / (n+1)
std::vector<long long> catalanNumbers(int n, long long mod) {
    std::vector<long long> fact(2 * n + 1, 1);
    for (int i = 1; i <= 2 * n; i++) fact[i] = fact[i-1] * i % mod;
    
    std::vector<long long> invFact(2 * n + 1);
    invFact[2 * n] = powerMod(fact[2 * n], mod - 2, mod);
    for (int i = 2 * n - 1; i >= 0; i--) invFact[i] = invFact[i+1] * (i+1) % mod;
    
    std::vector<long long> catalan(n + 1);
    for (int i = 0; i <= n; i++) {
        long long c2n_n = fact[2*i] % mod * invFact[i] % mod * invFact[i] % mod;
        catalan[i] = c2n_n * powerMod(i + 1, mod - 2, mod) % mod;
    }
    
    return catalan;
}

int main() {
    auto cat = catalanNumbers(20, MOD);
    
    std::cout << "Catalan numbers:\n";
    for (int i = 0; i <= 15; i++) {
        std::cout << "C(" << i << ") = " << cat[i] << "\n";
    }
    
    return 0;
}
```

---

## 71.5 Inclusion-Exclusion Principle

```
|A₁ ∪ A₂ ∪ ... ∪ Aₙ| = Σ|Aᵢ| - Σ|Aᵢ ∩ Aⱼ| + Σ|Aᵢ ∩ Aⱼ ∩ Aₖ| - ...
```

### Example: Count integers in [1, N] divisible by any of a set of primes

```cpp
#include <iostream>
#include <vector>

// Count integers in [1, n] divisible by at least one of the given primes
long long countDivisible(long long n, const std::vector<int>& primes) {
    int m = primes.size();
    long long result = 0;
    
    // Iterate over all non-empty subsets of primes
    for (int mask = 1; mask < (1 << m); mask++) {
        long long lcm = 1;
        int bits = 0;
        for (int i = 0; i < m; i++) {
            if (mask & (1 << i)) {
                lcm *= primes[i];
                bits++;
            }
        }
        
        long long count = n / lcm;
        if (bits % 2 == 1) result += count;
        else result -= count;
    }
    
    return result;
}

int main() {
    // Count integers in [1, 100] divisible by 2, 3, or 5
    std::vector<int> primes = {2, 3, 5};
    std::cout << "Count in [1,100] divisible by 2,3,5: " 
              << countDivisible(100, primes) << "\n"; // 74
    
    return 0;
}
```

---

## 71.6 Derangements

A **derangement** is a permutation where no element appears in its original position.

```
D(n) = (n-1) × (D(n-1) + D(n-2))
D(0) = 1, D(1) = 0, D(2) = 1, D(3) = 2, D(4) = 9
```

```cpp
#include <iostream>
#include <vector>

std::vector<long long> derangements(int n, long long mod) {
    std::vector<long long> D(n + 1);
    D[0] = 1;
    if (n >= 1) D[1] = 0;
    for (int i = 2; i <= n; i++) {
        D[i] = (i - 1) * (D[i-1] + D[i-2]) % mod;
    }
    return D;
}

int main() {
    auto D = derangements(20, 1000000007);
    
    std::cout << "Derangements:\n";
    for (int i = 0; i <= 10; i++) {
        std::cout << "D(" << i << ") = " << D[i] << "\n";
    }
    
    return 0;
}
```

---

## Summary

| Technique | Formula | Application |
|---|---|---|
| nCr | n!/(r!(n-r)!) | Choosing r from n |
| Stars and Bars | C(n+k-1, k-1) | Distributing n items into k bins |
| Catalan | C(2n,n)/(n+1) | Parentheses, trees, paths |
| Inclusion-Exclusion | Alternating sum | Counting with constraints |
| Derangements | (n-1)(D(n-1)+D(n-2)) | Permutations with no fixed points |

---

## 71.7 Stirling Numbers

**Stirling numbers of the second kind** S(n,k) count the number of ways to partition n elements into k non-empty subsets.

```
S(n,k) = k * S(n-1,k) + S(n-1,k-1)
S(n,0) = 0, S(n,n) = 1, S(n,1) = 1
```

```cpp
#include <iostream>
#include <vector>

const long long MOD = 1e9 + 7;

std::vector<std::vector<long long>> stirling2(int n) {
    std::vector<std::vector<long long>> S(n + 1, std::vector<long long>(n + 1, 0));
    S[0][0] = 1;
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= i; j++)
            S[i][j] = (j * S[i-1][j] + S[i-1][j-1]) % MOD;
    return S;
}

int main() {
    auto S = stirling2(10);
    std::cout << "S(5,3) = " << S[5][3] << "\n"; // 25
    std::cout << "S(10,5) = " << S[10][5] << "\n";
    return 0;
}
```

---

## 71.8 Bell Numbers

The Bell number B(n) counts the total number of partitions of a set of n elements.

```
B(n) = Σ S(n,k) for k = 0 to n
B(0) = 1, B(1) = 1, B(2) = 2, B(3) = 5, B(4) = 15
```

```cpp
#include <iostream>
#include <vector>

const long long MOD = 1e9 + 7;

std::vector<long long> bellNumbers(int n) {
    auto S = stirling2(n); // From above
    std::vector<long long> B(n + 1, 0);
    for (int i = 0; i <= n; i++)
        for (int k = 0; k <= i; k++)
            B[i] = (B[i] + S[i][k]) % MOD;
    return B;
}

// Alternative: Bell triangle
std::vector<long long> bellTriangle(int n) {
    std::vector<std::vector<long long>> tri(n + 1, std::vector<long long>(n + 1, 0));
    tri[0][0] = 1;
    for (int i = 1; i <= n; i++) {
        tri[i][0] = tri[i-1][i-1];
        for (int j = 1; j <= i; j++)
            tri[i][j] = (tri[i][j-1] + tri[i-1][j-1]) % MOD;
    }
    std::vector<long long> B(n + 1);
    for (int i = 0; i <= n; i++) B[i] = tri[i][0];
    return B;
}

int main() {
    auto B = bellTriangle(15);
    for (int i = 0; i <= 10; i++)
        std::cout << "B(" << i << ") = " << B[i] << "\n";
    return 0;
}
```
