# Chapter 2: Mathematical Foundations

Mathematics is the language of algorithms. Before diving into data structures and algorithms, we need a solid foundation in the mathematical concepts that underpin everything we'll study. This chapter is designed for readers who may not have a strong math background — we start from absolute first principles and build up.

---

## 2.1 Logarithms

### What Is a Logarithm?

A logarithm answers the question: **"How many times do I multiply this number by itself to get that number?"**

Formally, if:

\\[b^y = x\\]

then we say:

\\[\log_b(x) = y\\]

**In plain English:** "log base b of x equals y" means "b raised to the power y gives x."

**Example:**

\\[\log_2(8) = 3 \quad \text{because} \quad 2^3 = 8\\]

\\[\log_{10}(1000) = 3 \quad \text{because} \quad 10^3 = 1000\\]

### Visual Explanation

Think of a logarithm as the **inverse of exponentiation**:

```
Exponentiation:    2 × 2 × 2 × 2 = 16    →  2^4 = 16
Logarithm:         log₂(16) = 4           →  "How many 2s multiplied together give 16?"
```

Here's a table to build intuition:

| Expression | Question | Answer |
|---|---|---|
| log₂(1) | 2^? = 1 | 0 |
| log₂(2) | 2^? = 2 | 1 |
| log₂(4) | 2^? = 4 | 2 |
| log₂(8) | 2^? = 8 | 3 |
| log₂(16) | 2^? = 16 | 4 |
| log₂(32) | 2^? = 32 | 5 |
| log₂(1024) | 2^? = 1024 | 10 |

**Key insight:** log₂(1024) = 10. This is why binary search on 1024 elements takes only ~10 steps!

### Properties of Logarithms

These properties are essential and appear constantly in algorithm analysis:

| Property | Formula | Example |
|---|---|---|
| Product Rule | log(xy) = log(x) + log(y) | log(8×4) = log(8) + log(4) = 3 + 2 = 5 |
| Quotient Rule | log(x/y) = log(x) - log(y) | log(16/4) = log(16) - log(4) = 2 |
| Power Rule | log(x^n) = n·log(x) | log(2^10) = 10·log(2) = 10 |
| Change of Base | log_b(x) = log_k(x) / log_k(b) | log₂(8) = ln(8)/ln(2) |
| Log of 1 | log_b(1) = 0 | Any base |
| Log of Base | log_b(b) = 1 | Any base |

### Why Logarithms Appear in CS

Logarithms appear everywhere in computer science because of **divide and conquer**:

1. **Binary Search**: If you halve the search space each step, after k steps you have n/2^k elements. When n/2^k = 1, we get k = log₂(n).

2. **Balanced Binary Trees**: A balanced tree with n nodes has height log₂(n).

3. **Merge Sort**: Divides the problem in half at each level, giving log₂(n) levels.

4. **Bit representation**: Representing the number n in binary requires ⌊log₂(n)⌋ + 1 bits.

### Change of Base Formula

In CS we almost always use log₂, but calculators typically compute log₁₀ or ln (log_e). The change of base formula lets us convert:

\\[\log_b(x) = \frac{\log_k(x)}{\log_k(b)}\\]

**In code:**

```cpp
#include <iostream>
#include <cmath>

int main() {
    double x = 1024.0;
    double b = 2.0;

    // Change of base: log_b(x) = ln(x) / ln(b)
    double result = std::log(x) / std::log(b);
    std::cout << "log₂(1024) = " << result << std::endl;  // Output: 10

    // In C++ we can also use:
    std::cout << "log2(1024) = " << std::log2(x) << std::endl;  // Output: 10
    return 0;
}
```

### Common Misconception

In algorithm analysis, when we write O(log n), the base doesn't matter! Why? Because:

\\[\log_a(n) = \frac{\log_b(n)}{\log_b(a)}\\]

Since log_b(a) is just a constant, O(log₂ n) = O(log₁₀ n) = O(ln n). We drop constants in Big-O notation.

---

## 2.2 Exponentials

### What Is an Exponential?

An exponential expression has the form b^n, meaning "multiply b by itself n times."

\\[b^n = \underbrace{b \times b \times \cdots \times b}_{n \text{ times}}\\]

### Growth Rates — Why O(2^n) Is Terrifying

Understanding exponential growth is crucial for recognizing when an algorithm is impractical:

| n | n² | n³ | 2^n | n! |
|---|---|---|---|---|
| 1 | 1 | 1 | 2 | 1 |
| 5 | 25 | 125 | 32 | 120 |
| 10 | 100 | 1000 | 1024 | 3,628,800 |
| 15 | 225 | 3375 | 32,768 | 1.3 × 10¹² |
| 20 | 400 | 8000 | 1,048,576 | 2.4 × 10¹⁸ |
| 30 | 900 | 27000 | 1.07 × 10⁹ | 2.7 × 10³² |
| 50 | 2500 | 125000 | 1.13 × 10¹⁵ | 3.0 × 10⁶⁴ |
| 100 | 10000 | 10⁶ | 1.27 × 10³⁰ | 9.3 × 10¹⁵⁷ |

**Key insight:** For n = 50, 2^50 ≈ 10^15. If your computer does 10^9 operations per second, this takes ~10^6 seconds ≈ 11.5 days! An O(n²) algorithm for n = 50 does only 2500 operations.

### Powers of 2 in CS

Powers of 2 are everywhere in computer science:

| Power | Value | Significance |
|---|---|---|
| 2⁰ | 1 | Single element |
| 2¹ | 2 | Bit states (0 or 1) |
| 2⁸ | 256 | Byte (ASCII character) |
| 2¹⁰ | 1,024 | ~1 Kilobyte |
| 2¹⁶ | 65,536 | Unsigned short max |
| 2²⁰ | 1,048,576 | ~1 Megabyte |
| 2³¹ | 2,147,483,648 | Signed int max + 1 |
| 2³² | 4,294,967,296 | Unsigned int max + 1 |
| 2⁶³ | 9.2 × 10¹⁸ | Signed long long max + 1 |

### Fast Exponentiation (Binary Exponentiation)

Computing a^n naively takes O(n) multiplications. We can do it in O(log n):

**Idea:** a^13 = a^8 · a^4 · a^1. Write the exponent in binary: 13 = 1101₂.

```cpp
#include <iostream>

// Computes (base^exp) % mod in O(log exp) time
long long power(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        // If the current bit is set, multiply result by current base
        if (exp & 1) {
            result = (result * base) % mod;
        }
        // Square the base for the next bit
        base = (base * base) % mod;
        // Shift exponent right by 1
        exp >>= 1;
    }
    return result;
}

int main() {
    std::cout << "2^10 mod 1000 = " << power(2, 10, 1000) << std::endl;       // 24
    std::cout << "3^13 mod 1000000007 = " << power(3, 13, 1000000007) << std::endl; // 1594323
    return 0;
}
```

**Dry Run: Compute 2^10**

| Step | exp (binary) | exp & 1 | result | base |
|---|---|---|---|---|
| Init | 1010 | 0 | 1 | 2 |
| 1 | 101 | 0 | 1 | 4 |
| 2 | 10 | 0 | 1 | 16 |
| 3 | 1 | 1 | 16 | 256 |
| 4 | 0 | — | 16 | — |

Wait, that gives 16. Let me recheck: 2^10 = 1024. Let me redo:

| Step | exp | exp & 1 | result | base |
|---|---|---|---|---|
| Init | 10 | - | 1 | 2 |
| 1 | 10→5 | 0 (10 is even) | 1 | 2² = 4 |
| 2 | 5→2 | 1 (5 is odd) | 1×4 = 4 | 4² = 16 |
| 3 | 2→1 | 0 (2 is even) | 4 | 16² = 256 |
| 4 | 1→0 | 1 (1 is odd) | 4×256 = 1024 | - |

Result: 1024. ✓

---

## 2.3 Binary Numbers

### Why Do Computers Use Binary?

Computers are built from transistors — tiny switches that are either **ON** (1) or **OFF** (0). It's physically simplest to represent two states. While ternary (base-3) computers have been built, binary won because:

1. **Noise resistance**: Distinguishing between two voltage levels is far more reliable than three or more.
2. **Simple circuits**: Boolean logic (AND, OR, NOT) maps directly to binary.
3. **Error detection**: Binary makes parity checks straightforward.

### Decimal to Binary Conversion

**Method: Repeated Division by 2**

To convert decimal 42 to binary:

```
42 ÷ 2 = 21  remainder 0  (LSB - least significant bit)
21 ÷ 2 = 10  remainder 1
10 ÷ 2 = 5   remainder 0
 5 ÷ 2 = 2   remainder 1
 2 ÷ 2 = 1   remainder 0
 1 ÷ 2 = 0   remainder 1  (MSB - most significant bit)
```

Read remainders bottom to top: **42 = 101010₂**

**Verification:** 1×32 + 0×16 + 1×8 + 0×4 + 1×2 + 0×1 = 32 + 8 + 2 = 42 ✓

### Binary to Decimal Conversion

Each binary digit represents a power of 2:

```
Position:  5    4    3    2    1    0
Bit:       1    0    1    0    1    0
Value:     32   16   8    4    2    1
           ↓    ↓    ↓    ↓    ↓    ↓
         32 +  0 +  8 +  0 +  2 +  0 = 42
```

### Binary Arithmetic

**Addition (just like decimal, but carry at 2):**

```
  1011    (11)
+ 0101    ( 5)
------
 10000    (16)
```

Step by step:
- 1 + 1 = 10, write 0 carry 1
- 1 + 0 + 1(carry) = 10, write 0 carry 1
- 0 + 1 + 1(carry) = 10, write 0 carry 1
- 1 + 0 + 1(carry) = 10, write 0 carry 1

**Subtraction (borrow when needed):**

```
  1011    (11)
- 0101    ( 5)
------
  0110    ( 6)
```

### Negative Numbers: Two's Complement

Computers represent negative integers using **two's complement**:

1. Start with the positive number in binary
2. Flip all bits (one's complement)
3. Add 1

**Example: Represent -5 in 8-bit:**

```
 5 in binary:     00000101
Flip all bits:    11111010
Add 1:           11111011  → This is -5
```

**Why this works:** In 8-bit two's complement, adding a number and its negative gives 0 (mod 2⁸):

```
  00000101   (5)
+ 11111011   (-5)
----------
 100000000   → Discard overflow bit → 00000000 (0)
```

**Range:** In n-bit two's complement, the range is [-2^(n-1), 2^(n-1) - 1].

| Bits | Min | Max |
|---|---|---|
| 8 | -128 | 127 |
| 16 | -32768 | 32767 |
| 32 | -2,147,483,648 | 2,147,483,647 |

---

## 2.4 Bit Operations

Bit operations are fundamental to many algorithms and appear frequently in interviews.

### The Four Basic Operations

#### AND (&)

Returns 1 only if **both** bits are 1.

| A | B | A & B |
|---|---|---|
| 0 | 0 | 0 |
| 0 | 1 | 0 |
| 1 | 0 | 0 |
| 1 | 1 | 1 |

**Example:** `0b1100 & 0b1010 = 0b1000` (12 & 10 = 8)

```
  1100
& 1010
------
  1000
```

#### OR (|)

Returns 1 if **at least one** bit is 1.

| A | B | A \| B |
|---|---|---|
| 0 | 0 | 0 |
| 0 | 1 | 1 |
| 1 | 0 | 1 |
| 1 | 1 | 1 |

**Example:** `0b1100 | 0b1010 = 0b1110` (12 | 10 = 14)

```
  1100
| 1010
------
  1110
```

#### XOR (^)

Returns 1 if the bits are **different**.

| A | B | A ^ B |
|---|---|---|
| 0 | 0 | 0 |
| 0 | 1 | 1 |
| 1 | 0 | 1 |
| 1 | 1 | 0 |

**Example:** `0b1100 ^ 0b1010 = 0b0110` (12 ^ 10 = 6)

```
  1100
^ 1010
------
  0110
```

**XOR properties (extremely useful):**
- `a ^ a = 0` (any number XOR itself is 0)
- `a ^ 0 = a` (any number XOR 0 is itself)
- XOR is commutative and associative
- **Application:** Finding the single number in an array where all others appear twice:

```cpp
#include <iostream>
#include <vector>

int singleNumber(const std::vector<int>& nums) {
    int result = 0;
    for (int num : nums) {
        result ^= num;  // Pairs cancel out, single number remains
    }
    return result;
}

int main() {
    std::vector<int> nums = {4, 1, 2, 1, 2};
    std::cout << "Single number: " << singleNumber(nums) << std::endl;  // 4
    return 0;
}
```

#### NOT (~)

Flips all bits. In C++, `~0b00001010 = 0b11110101` (on a typical 8-bit view).

**Be careful in C++:** `~` operates on all bits of the type. For `int x = 5`, `~x = -6` (in two's complement).

### Bit Shifts

#### Left Shift (<<)

Shifts bits left by n positions. Each left shift **multiplies** by 2.

```
0b0001 << 1 = 0b0010   (1 << 1 = 2)
0b0001 << 2 = 0b0100   (1 << 2 = 4)
0b0001 << 3 = 0b1000   (1 << 3 = 8)
```

**Key formulas:**
- `1 << n` = 2^n (a power of 2)
- `x << n` = x × 2^n

#### Right Shift (>>)

Shifts bits right by n positions. Each right shift **divides** by 2 (integer division).

```
0b1000 >> 1 = 0b0100   (8 >> 1 = 4)
0b1000 >> 2 = 0b0010   (8 >> 2 = 2)
0b1000 >> 3 = 0b0001   (8 >> 3 = 1)
```

### Bit Masks

A **bitmask** is a value used to select specific bits. Common patterns:

```cpp
#include <iostream>

int main() {
    int x = 42;  // Binary: 101010

    // Check if bit k is set
    int k = 3;
    bool bitK = (x >> k) & 1;
    std::cout << "Bit " << k << " of " << x << " is: " << bitK << std::endl;  // 1

    // Set bit k (make it 1)
    x |= (1 << k);
    std::cout << "After setting bit " << k << ": " << x << std::endl;

    // Clear bit k (make it 0)
    x &= ~(1 << k);
    std::cout << "After clearing bit " << k << ": " << x << std::endl;

    // Toggle bit k
    x ^= (1 << k);
    std::cout << "After toggling bit " << k << ": " << x << std::endl;

    // Check if number is even
    int n = 7;
    bool isEven = (n & 1) == 0;
    std::cout << n << " is even: " << isEven << std::endl;  // 0 (false)

    // Multiply/divide by powers of 2
    std::cout << "7 * 8 = " << (7 << 3) << std::endl;   // 56
    std::cout << "56 / 8 = " << (56 >> 3) << std::endl;  // 7

    return 0;
}
```

### Useful Bit Tricks

```cpp
#include <iostream>

int main() {
    int n = 12;  // Binary: 1100

    // Check if n is a power of 2
    bool isPow2 = (n > 0) && ((n & (n - 1)) == 0);
    std::cout << n << " is power of 2: " << isPow2 << std::endl;  // 0 (false, 12 is not)

    // Count set bits (Brian Kernighan's algorithm)
    int count = 0;
    int temp = n;
    while (temp > 0) {
        temp &= (temp - 1);  // Clear the lowest set bit
        count++;
    }
    std::cout << "Set bits in " << n << ": " << count << std::endl;  // 2

    // Lowest set bit
    int lowest = n & (-n);
    std::cout << "Lowest set bit of " << n << ": " << lowest << std::endl;  // 4

    return 0;
}
```

---

## 2.5 Modulo Arithmetic

### What Is Modulo?

The modulo operation gives the **remainder** after division.

\\[a \mod n = \text{remainder when } a \text{ is divided by } n\\]

**Examples:**
- 17 mod 5 = 2 (because 17 = 3×5 + 2)
- 10 mod 3 = 1 (because 10 = 3×3 + 1)
- 20 mod 4 = 0 (because 20 = 5×4 + 0)

```cpp
#include <iostream>

int main() {
    std::cout << 17 % 5 << std::endl;  // 2
    std::cout << 10 % 3 << std::endl;  // 1
    std::cout << 20 % 4 << std::endl;  // 0

    // Note: In C++, negative modulo can be negative!
    std::cout << -7 % 3 << std::endl;  // -1 (not 2!)
    // To get positive modulo:
    int a = -7, n = 3;
    int positive_mod = ((a % n) + n) % n;
    std::cout << positive_mod << std::endl;  // 2
    return 0;
}
```

### Properties of Modular Arithmetic

These properties are the foundation of competitive programming and cryptographic algorithms:

| Property | Formula |
|---|---|
| Addition | (a + b) mod m = ((a mod m) + (b mod m)) mod m |
| Subtraction | (a - b) mod m = ((a mod m) - (b mod m) + m) mod m |
| Multiplication | (a × b) mod m = ((a mod m) × (b mod m)) mod m |
| Exponentiation | a^n mod m can be computed via binary exponentiation |

**Why this matters:** When computing with very large numbers, we can take mod at every step to prevent overflow!

### Modular Exponentiation

We already saw this in Section 2.2 with the `power()` function. The key insight is that we can take mod at every multiplication step:

```cpp
#include <iostream>

const long long MOD = 1e9 + 7;  // A common prime modulus in competitive programming

long long modpow(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) {
            result = (result * base) % mod;
        }
        base = (base * base) % mod;
        exp >>= 1;
    }
    return result;
}

int main() {
    // Compute 2^100 mod (10^9 + 7)
    std::cout << "2^100 mod (10^9+7) = " << modpow(2, 100, MOD) << std::endl;
    return 0;
}
```

### Modular Inverse

The **modular inverse** of a number a (mod m) is a number a⁻¹ such that:

\\[a \times a^{-1} \equiv 1 \pmod{m}\\]

**When does it exist?** The modular inverse exists if and only if gcd(a, m) = 1 (a and m are coprime).

**Computing modular inverse using Fermat's Little Theorem:** If m is prime:

\\[a^{-1} \equiv a^{m-2} \pmod{m}\\]

```cpp
#include <iostream>

const long long MOD = 1e9 + 7;

long long modpow(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = (result * base) % mod;
        base = (base * base) % mod;
        exp >>= 1;
    }
    return result;
}

// Modular inverse when mod is prime (Fermat's little theorem)
long long modInverse(long long a, long long mod) {
    return modpow(a, mod - 2, mod);
}

int main() {
    long long a = 3;
    long long inv = modInverse(a, MOD);
    std::cout << "3 * " << inv << " mod " << MOD << " = " << (a * inv) % MOD << std::endl;
    // Should print 1
    return 0;
}
```

### Overflow Prevention

One of the most common bugs in competitive programming is integer overflow. Modular arithmetic helps:

```cpp
// BAD: Overflow before taking mod
long long bad = (a * b) % MOD;  // a * b might overflow long long!

// GOOD: Take mod at each step
long long good = ((a % MOD) * (b % MOD)) % MOD;

// For addition of many numbers:
long long sum = 0;
for (int x : arr) {
    sum = (sum + x) % MOD;  // Never overflows if MOD < 2^62
}
```

---

## 2.6 Prime Numbers

### What Is a Prime?

A **prime number** is a natural number greater than 1 that has no positive divisors other than 1 and itself.

**First few primes:** 2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, ...

**Key facts:**
- 1 is NOT prime.
- 2 is the only even prime.
- Every integer > 1 is either prime or can be written as a product of primes (Fundamental Theorem of Arithmetic).

### Trial Division

The simplest way to check if n is prime: try dividing by every number from 2 to √n.

**Why √n?** If n = a × b, then at least one of a or b must be ≤ √n.

```cpp
#include <iostream>
#include <cmath>

bool isPrime(int n) {
    if (n < 2) return false;
    if (n == 2) return true;
    if (n % 2 == 0) return false;
    for (int i = 3; i * i <= n; i += 2) {
        if (n % i == 0) return false;
    }
    return true;
}

int main() {
    for (int i = 1; i <= 30; i++) {
        if (isPrime(i)) {
            std::cout << i << " ";
        }
    }
    std::cout << std::endl;
    // Output: 2 3 5 7 11 13 17 19 23 29
    return 0;
}
```

**Time complexity:** O(√n) per query.

### Sieve of Eratosthenes

To find all primes up to n efficiently, the **Sieve of Eratosthenes** is the classic algorithm.

**Algorithm:**
1. Create a boolean array `is_prime[0..n]`, initially all true.
2. Mark 0 and 1 as false.
3. For each number i from 2 to √n:
   - If `is_prime[i]` is true, mark all multiples of i (from i² to n) as false.
4. All remaining true entries are primes.

**Why start from i²?** Because smaller multiples of i (like 2i, 3i, ..., (i-1)i) have already been marked by smaller primes.

```cpp
#include <iostream>
#include <vector>

std::vector<int> sieveOfEratosthenes(int n) {
    std::vector<bool> is_prime(n + 1, true);
    is_prime[0] = is_prime[1] = false;

    for (int i = 2; i * i <= n; i++) {
        if (is_prime[i]) {
            // Mark all multiples of i starting from i*i
            for (int j = i * i; j <= n; j += i) {
                is_prime[j] = false;
            }
        }
    }

    std::vector<int> primes;
    for (int i = 2; i <= n; i++) {
        if (is_prime[i]) {
            primes.push_back(i);
        }
    }
    return primes;
}

int main() {
    auto primes = sieveOfEratosthenes(100);
    std::cout << "Primes up to 100: ";
    for (int p : primes) {
        std::cout << p << " ";
    }
    std::cout << std::endl;
    std::cout << "Count: " << primes.size() << std::endl;  // 25
    return 0;
}
```

**Dry Run for n = 30:**

```
Initial: 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30

i=2: Mark 4,6,8,10,12,14,16,18,20,22,24,26,28,30
i=3: Mark 9,15,21,27  (6,12,18,24,30 already marked)
i=4: Already marked, skip
i=5: Mark 25  (10,15,20,30 already marked)

Remaining primes: 2 3 5 7 11 13 17 19 23 29
```

**Time Complexity:** O(n log log n) — nearly linear!
**Space Complexity:** O(n)

### Linear Sieve (Bonus)

The standard sieve visits some composites multiple times. A linear sieve visits each number exactly once:

```cpp
#include <iostream>
#include <vector>

std::vector<int> linearSieve(int n) {
    std::vector<bool> is_prime(n + 1, true);
    std::vector<int> primes;
    is_prime[0] = is_prime[1] = false;

    for (int i = 2; i <= n; i++) {
        if (is_prime[i]) {
            primes.push_back(i);
        }
        for (int p : primes) {
            if (i * p > n) break;
            is_prime[i * p] = false;
            if (i % p == 0) break;  // Key optimization
        }
    }
    return primes;
}

int main() {
    auto primes = linearSieve(100);
    std::cout << "Primes up to 100: ";
    for (int p : primes) std::cout << p << " ";
    std::cout << std::endl;
    return 0;
}
```

**Time Complexity:** O(n) — truly linear!

---

## 2.7 GCD and LCM

### Greatest Common Divisor (GCD)

The GCD of two numbers is the largest number that divides both.

\\[\gcd(12, 8) = 4 \quad \text{because } 4 \mid 12 \text{ and } 4 \mid 8\\]

### Euclidean Algorithm

The key insight: **gcd(a, b) = gcd(b, a mod b)**

**Why?** If d divides both a and b, then d divides a - q·b = a mod b. And vice versa.

**Base case:** gcd(a, 0) = a.

```cpp
#include <iostream>

// Iterative Euclidean algorithm
long long gcd(long long a, long long b) {
    while (b != 0) {
        long long temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

// Recursive version
long long gcd_recursive(long long a, long long b) {
    if (b == 0) return a;
    return gcd_recursive(b, a % b);
}

// C++17 has std::gcd in <numeric>
// #include <numeric>
// std::gcd(a, b)

int main() {
    std::cout << "gcd(12, 8) = " << gcd(12, 8) << std::endl;    // 4
    std::cout << "gcd(54, 24) = " << gcd(54, 24) << std::endl;  // 6
    std::cout << "gcd(17, 13) = " << gcd(17, 13) << std::endl;  // 1
    return 0;
}
```

**Dry Run: gcd(54, 24)**

| Step | a | b | a mod b |
|---|---|---|---|
| 1 | 54 | 24 | 6 |
| 2 | 24 | 6 | 0 |
| 3 | 6 | 0 | done |

Result: gcd = 6 ✓

**Time Complexity:** O(log(min(a, b))). This is extremely fast — even for 64-bit numbers, it takes at most ~90 steps.

### Least Common Multiple (LCM)

\\[\text{lcm}(a, b) = \frac{a \times b}{\gcd(a, b)}\\]

```cpp
#include <iostream>

long long gcd(long long a, long long b) {
    while (b != 0) {
        long long temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

long long lcm(long long a, long long b) {
    // Divide first to avoid overflow
    return (a / gcd(a, b)) * b;
}

int main() {
    std::cout << "lcm(12, 8) = " << lcm(12, 8) << std::endl;  // 24
    std::cout << "lcm(4, 6) = " << lcm(4, 6) << std::endl;    // 12
    return 0;
}
```

### Extended Euclidean Algorithm

The extended Euclidean algorithm finds integers x and y such that:

\\[a \cdot x + b \cdot y = \gcd(a, b)\\]

This is called **Bézout's identity** and is essential for computing modular inverses.

```cpp
#include <iostream>
#include <tuple>

// Returns {gcd, x, y} such that a*x + b*y = gcd
std::tuple<long long, long long, long long> extgcd(long long a, long long b) {
    if (b == 0) {
        return {a, 1, 0};
    }
    auto [g, x1, y1] = extgcd(b, a % b);
    long long x = y1;
    long long y = x1 - (a / b) * y1;
    return {g, x, y};
}

int main() {
    auto [g, x, y] = extgcd(35, 15);
    std::cout << "gcd = " << g << ", x = " << x << ", y = " << y << std::endl;
    // gcd = 5, x = 1, y = -2
    // Verify: 35*1 + 15*(-2) = 35 - 30 = 5 ✓
    return 0;
}
```

**Proof sketch for the recurrence:**

We know: gcd(a, b) = gcd(b, a mod b)

If gcd(b, a mod b) = b·x₁ + (a mod b)·y₁, and a mod b = a - (a/b)·b:

g = b·x₁ + (a - (a/b)·b)·y₁
g = a·y₁ + b·(x₁ - (a/b)·y₁)

So: x = y₁, y = x₁ - (a/b)·y₁

---

## 2.8 Combinatorics

### Permutations

A **permutation** is an arrangement of objects in a specific order.

**n distinct objects, arranging r of them:**

\\[P(n, r) = \frac{n!}{(n-r)!} = n \times (n-1) \times \cdots \times (n-r+1)\\]

**Example:** How many ways to arrange 3 books from 5 on a shelf?

\\[P(5, 3) = \frac{5!}{(5-3)!} = \frac{120}{2} = 60\\]

**Intuition:** First book: 5 choices. Second: 4 choices. Third: 3 choices. Total: 5 × 4 × 3 = 60.

### Combinations

A **combination** is a selection of objects where order doesn't matter.

\\[C(n, r) = \binom{n}{r} = \frac{n!}{r!(n-r)!}\\]

**Example:** How many ways to choose 3 students from 10?

\\[C(10, 3) = \frac{10!}{3! \times 7!} = \frac{10 \times 9 \times 8}{3 \times 2 \times 1} = 120\\]

**Intuition:** Permutations count arrangements (order matters). Combinations count selections (order doesn't). Since each group of r items can be arranged in r! ways: C(n,r) = P(n,r) / r!.

### Pascal's Triangle

Pascal's triangle gives all binomial coefficients:

```
            1
          1   1
        1   2   1
      1   3   3   1
    1   4   6   4   1
  1   5  10  10   5   1
```

**Property:** C(n, r) = C(n-1, r-1) + C(n-1, r)

**Why?** Either the element is included (choose r-1 from remaining n-1) or it's not (choose r from remaining n-1).

```cpp
#include <iostream>
#include <vector>

// Compute C(n, k) using Pascal's triangle
// O(n*k) time, O(k) space with 1D DP
long long nCr(int n, int k) {
    if (k > n) return 0;
    if (k > n - k) k = n - k;  // Symmetry optimization

    std::vector<long long> dp(k + 1, 0);
    dp[0] = 1;

    for (int i = 1; i <= n; i++) {
        // Traverse backwards to avoid using updated values
        for (int j = std::min(i, k); j > 0; j--) {
            dp[j] = dp[j] + dp[j - 1];
        }
    }
    return dp[k];
}

// Compute n! modulo mod
long long factorial(int n, long long mod) {
    long long result = 1;
    for (int i = 2; i <= n; i++) {
        result = (result * i) % mod;
    }
    return result;
}

int main() {
    std::cout << "C(10, 3) = " << nCr(10, 3) << std::endl;  // 120
    std::cout << "C(5, 2) = " << nCr(5, 2) << std::endl;    // 10
    std::cout << "C(0, 0) = " << nCr(0, 0) << std::endl;    // 1

    // Print Pascal's triangle
    std::cout << "\nPascal's Triangle (10 rows):\n";
    for (int i = 0; i < 10; i++) {
        for (int j = 0; j <= i; j++) {
            std::cout << nCr(i, j) << " ";
        }
        std::cout << "\n";
    }
    return 0;
}
```

### Computing C(n, k) with Modular Arithmetic

When answers need to be modulo a prime (common in competitive programming):

```cpp
#include <iostream>

const long long MOD = 1e9 + 7;

long long modpow(long long base, long long exp, long long mod) {
    long long result = 1;
    base %= mod;
    while (exp > 0) {
        if (exp & 1) result = (result * base) % mod;
        base = (base * base) % mod;
        exp >>= 1;
    }
    return result;
}

long long modInverse(long long a, long long mod) {
    return modpow(a, mod - 2, mod);
}

// Precompute factorials and inverse factorials
const int MAXN = 1000001;
long long fact[MAXN], inv_fact[MAXN];

void precompute() {
    fact[0] = 1;
    for (int i = 1; i < MAXN; i++) {
        fact[i] = (fact[i - 1] * i) % MOD;
    }
    inv_fact[MAXN - 1] = modInverse(fact[MAXN - 1], MOD);
    for (int i = MAXN - 2; i >= 0; i--) {
        inv_fact[i] = (inv_fact[i + 1] * (i + 1)) % MOD;
    }
}

long long nCr_mod(int n, int r) {
    if (r < 0 || r > n) return 0;
    return (((fact[n] * inv_fact[r]) % MOD) * inv_fact[n - r]) % MOD;
}

int main() {
    precompute();
    std::cout << "C(100, 50) mod (10^9+7) = " << nCr_mod(100, 50) << std::endl;
    return 0;
}
```

---

## 2.9 Probability

### Basic Probability

The probability of an event A is:

\\[P(A) = \frac{\text{Number of favorable outcomes}}{\text{Total number of outcomes}}\\]

**Example:** Rolling a die, P(getting 3) = 1/6.

### Rules of Probability

**Addition Rule (for mutually exclusive events):**
\\[P(A \text{ or } B) = P(A) + P(B)\\]

**General Addition Rule:**
\\[P(A \cup B) = P(A) + P(B) - P(A \cap B)\\]

**Multiplication Rule (for independent events):**
\\[P(A \text{ and } B) = P(A) \times P(B)\\]

### Conditional Probability

The probability of A given that B has occurred:

\\[P(A|B) = \frac{P(A \cap B)}{P(B)}\\]

**Example:** A bag has 3 red and 2 blue balls. Draw 2 without replacement. P(second is red | first was red)?

After drawing one red: 2 red, 2 blue remain. P = 2/4 = 1/2.

### Bayes' Theorem

\\[P(A|B) = \frac{P(B|A) \times P(A)}{P(B)}\\]

**Medical test example:**
- A disease affects 1% of people: P(Disease) = 0.01
- Test is 99% accurate: P(Positive|Disease) = 0.99
- False positive rate: P(Positive|No Disease) = 0.01

**Question:** If you test positive, what's the probability you have the disease?

\\[P(Disease|Positive) = \frac{P(Positive|Disease) \times P(Disease)}{P(Positive)}\\]

\\[P(Positive) = P(Positive|Disease) \times P(Disease) + P(Positive|No Disease) \times P(No Disease)\\]
\\[= 0.99 \times 0.01 + 0.01 \times 0.99 = 0.0198\\]

\\[P(Disease|Positive) = \frac{0.99 \times 0.01}{0.0198} = 0.5 = 50\%\\]

**Surprising result!** Even with a 99% accurate test, a positive result only means 50% chance of disease. This is because the disease is rare (base rate fallacy).

### Expected Value

The **expected value** is the average outcome over many trials:

\\[E[X] = \sum_{i} x_i \cdot P(x_i)\\]

**Example:** Expected value of a fair die roll:
\\[E[X] = 1 \cdot \frac{1}{6} + 2 \cdot \frac{1}{6} + \cdots + 6 \cdot \frac{1}{6} = \frac{21}{6} = 3.5\\]

**Application in algorithms:** Linearity of expectation is a powerful tool. Even when events are NOT independent:

\\[E[X + Y] = E[X] + E[Y]\\]

**Example:** Expected number of heads in 100 coin flips = 100 × 0.5 = 50. No need to compute the full distribution!

```cpp
#include <iostream>
#include <vector>
#include <random>

// Simulate expected value of a die roll
double simulateExpectedValue(int trials) {
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(1, 6);

    long long sum = 0;
    for (int i = 0; i < trials; i++) {
        sum += dis(gen);
    }
    return static_cast<double>(sum) / trials;
}

int main() {
    std::cout << "Simulated E[die] with 1M trials: "
              << simulateExpectedValue(1000000) << std::endl;
    // Should be close to 3.5
    return 0;
}
```

---

## 2.10 Recurrence Relations

### What Is a Recurrence Relation?

A recurrence relation defines a sequence where each term is defined in terms of previous terms.

**Example — Fibonacci sequence:**
\\[F(0) = 0, \quad F(1) = 1, \quad F(n) = F(n-1) + F(n-2)\\]

**Example — Factorial:**
\\[F(0) = 1, \quad F(n) = n \times F(n-1)\\]

### Why Recurrences Matter in CS

Recurrences naturally describe the time complexity of recursive algorithms:

| Algorithm | Recurrence | Solution |
|---|---|---|
| Binary Search | T(n) = T(n/2) + O(1) | O(log n) |
| Merge Sort | T(n) = 2T(n/2) + O(n) | O(n log n) |
| Quick Sort (avg) | T(n) = 2T(n/2) + O(n) | O(n log n) |
| Quick Sort (worst) | T(n) = T(n-1) + O(n) | O(n²) |
| Fibonacci (naive) | T(n) = T(n-1) + T(n-2) | O(2^n) |
| Tower of Hanoi | T(n) = 2T(n-1) + O(1) | O(2^n) |

### Solving by Substitution (Iteration)

**Method:** Expand the recurrence step by step until you see a pattern.

**Example:** T(n) = T(n/2) + 1, T(1) = 1

```
T(n) = T(n/2) + 1
     = T(n/4) + 1 + 1
     = T(n/8) + 1 + 1 + 1
     ...
     = T(n/2^k) + k
```

When n/2^k = 1, we get k = log₂(n), so T(n) = 1 + log₂(n) = O(log n).

**Example:** T(n) = 2T(n/2) + n, T(1) = 1

```
Level 0: n                           → cost n
Level 1: n/2 + n/2                   → cost n
Level 2: n/4 + n/4 + n/4 + n/4      → cost n
...
Level k: n/2^k copies, each cost 1   → cost n

Height: log₂(n) levels
Total: n × log(n) = O(n log n)
```

### The Master Theorem

For recurrences of the form T(n) = aT(n/b) + O(n^d):

Where:
- a = number of subproblems
- b = factor by which input shrinks
- d = exponent of work done outside recursion

**Compare log_b(a) with d:**

| Case | Condition | Result |
|---|---|---|
| 1 | log_b(a) > d | O(n^(log_b(a))) — recursion dominates |
| 2 | log_b(a) = d | O(n^d × log n) — equal work at each level |
| 3 | log_b(a) < d | O(n^d) — top-level work dominates |

**Examples:**

| Recurrence | a | b | d | log_b(a) | Case | Result |
|---|---|---|---|---|---|---|
| T(n) = 2T(n/2) + n | 2 | 2 | 1 | 1 | Case 2 | O(n log n) |
| T(n) = T(n/2) + 1 | 1 | 2 | 0 | 0 | Case 2 | O(log n) |
| T(n) = 4T(n/2) + n | 4 | 2 | 1 | 2 | Case 1 | O(n²) |
| T(n) = 2T(n/2) + n² | 2 | 2 | 2 | 1 | Case 3 | O(n²) |
| T(n) = 2T(n/4) + √n | 2 | 4 | 0.5 | 0.5 | Case 2 | O(√n log n) |

```cpp
#include <iostream>
#include <cmath>

// Solve T(n) = aT(n/b) + n^d using Master theorem
void masterTheorem(double a, double b, double d) {
    double log_b_a = std::log(a) / std::log(b);

    std::cout << "T(n) = " << a << "T(n/" << b << ") + n^" << d << std::endl;
    std::cout << "log_" << b << "(" << a << ") = " << log_b_a << std::endl;

    if (std::abs(log_b_a - d) < 1e-9) {
        std::cout << "Case 2: T(n) = O(n^" << d << " log n)" << std::endl;
    } else if (log_b_a > d) {
        std::cout << "Case 1: T(n) = O(n^" << log_b_a << ")" << std::endl;
    } else {
        std::cout << "Case 3: T(n) = O(n^" << d << ")" << std::endl;
    }
    std::cout << std::endl;
}

int main() {
    masterTheorem(2, 2, 1);   // Merge Sort
    masterTheorem(1, 2, 0);   // Binary Search
    masterTheorem(4, 2, 1);   // Some 4-way recursion
    masterTheorem(2, 2, 2);   // Linear scan with halving
    return 0;
}
```

---

## 2.11 Proof by Induction

### What Is Mathematical Induction?

Induction is a proof technique that proves a statement for all natural numbers by showing:

1. **Base Case:** The statement is true for the smallest value (usually n = 0 or n = 1).
2. **Inductive Step:** If the statement is true for n = k, then it's true for n = k + 1.

**Analogy:** It's like a chain of dominoes:
- The first domino falls (base case).
- Each domino knocks over the next (inductive step).
- Therefore, ALL dominoes fall.

### Example 1: Sum of First n Natural Numbers

**Claim:** 1 + 2 + 3 + ... + n = n(n+1)/2

**Base Case (n = 1):** 1 = 1(2)/2 = 1 ✓

**Inductive Step:** Assume true for n = k: 1 + 2 + ... + k = k(k+1)/2

For n = k + 1:
```
1 + 2 + ... + k + (k+1)
= k(k+1)/2 + (k+1)       (by inductive hypothesis)
= (k+1)(k/2 + 1)
= (k+1)(k+2)/2
= (k+1)((k+1)+1)/2       ✓
```

### Example 2: Sum of Powers of 2

**Claim:** 1 + 2 + 4 + ... + 2^(n-1) = 2^n - 1

**Base Case (n = 1):** 1 = 2^1 - 1 = 1 ✓

**Inductive Step:** Assume true for n = k: 1 + 2 + ... + 2^(k-1) = 2^k - 1

For n = k + 1:
```
1 + 2 + ... + 2^(k-1) + 2^k
= (2^k - 1) + 2^k
= 2 × 2^k - 1
= 2^(k+1) - 1              ✓
```

### Example 3: Binary Search Correctness

**Claim:** Binary search correctly finds (or determines absence of) a target in a sorted array of size n.

**Base Case (n = 1):** We directly compare the single element with the target. Correct. ✓

**Inductive Step:** Assume binary search works correctly for arrays of size ≤ k.

For an array of size k + 1:
- We check the middle element.
- If it's the target, we're done.
- If the target is smaller, we search the left half (size ≤ k/2 ≤ k). By the inductive hypothesis, this is correct.
- If the target is larger, we search the right half (size ≤ k/2 ≤ k). Similarly correct.

Therefore, binary search works for arrays of size k + 1. ✓

### Strong Induction

In **strong induction**, the inductive step assumes the statement is true for ALL values up to k (not just k itself).

**Claim:** Every integer n ≥ 2 can be written as a product of primes.

**Base Case (n = 2):** 2 is prime. ✓

**Inductive Step:** Assume true for all integers from 2 to k.

For n = k + 1:
- If k + 1 is prime, done.
- If k + 1 is composite, then k + 1 = a × b where 2 ≤ a, b ≤ k. By the inductive hypothesis, both a and b are products of primes. Therefore k + 1 is a product of primes. ✓

### Induction in Algorithm Correctness

Induction is the primary tool for proving algorithm correctness:

```cpp
#include <iostream>
#include <vector>

// Prove by induction that this correctly computes prefix sums
// Claim: prefixSum[i] = arr[0] + arr[1] + ... + arr[i-1], with prefixSum[0] = 0
//
// Base case: prefixSum[0] = 0 (empty sum). ✓
// Inductive step: If prefixSum[i] = sum of first i elements,
//   then prefixSum[i+1] = prefixSum[i] + arr[i] = sum of first (i+1) elements. ✓

std::vector<long long> prefixSum(const std::vector<int>& arr) {
    int n = arr.size();
    std::vector<long long> prefix(n + 1, 0);
    for (int i = 0; i < n; i++) {
        prefix[i + 1] = prefix[i] + arr[i];
    }
    return prefix;
}

int main() {
    std::vector<int> arr = {3, 1, 4, 1, 5, 9, 2, 6};
    auto prefix = prefixSum(arr);

    std::cout << "Prefix sums: ";
    for (long long x : prefix) std::cout << x << " ";
    std::cout << std::endl;
    // Output: 0 3 4 8 9 14 23 25 31

    // Query: sum of arr[2..5] = prefix[6] - prefix[2] = 23 - 4 = 19
    std::cout << "Sum of arr[2..5] = " << prefix[6] - prefix[2] << std::endl;
    return 0;
}
```

---

## Interview Tips

1. **Modular arithmetic** is your best friend for preventing overflow. When in doubt, take mod early and often.

2. **GCD/LCM** — Know `std::gcd` (C++17, `<numeric>`). It's O(log(min(a,b))) and extremely fast.

3. **Bit manipulation** — Practice these patterns: check power of 2 (`n & (n-1) == 0`), count bits, isolate lowest bit (`n & -n`).

4. **Fast exponentiation** — O(log n) instead of O(n). Know it cold.

5. **Sieve of Eratosthenes** — Precompute primes up to 10^6 or 10^7 as needed. O(n log log n).

6. **Pascal's triangle** — C(n,k) = C(n-1,k-1) + C(n-1,k). This recurrence is the basis of many DP problems.

7. **Bayes' theorem** — Surprisingly relevant for probability-based interview questions. Remember the base rate fallacy.

## Common Mistakes

| Mistake | Why It's Wrong | Fix |
|---|---|---|
| `a * b % mod` when a, b are large | a * b overflows before mod | `((a % mod) * (b % mod)) % mod` |
| Using `%` for negative numbers in C++ | `-7 % 3 = -1`, not 2 | `((a % m) + m) % m` |
| Integer overflow in `i * i <= n` | If i is large, i*i overflows | Use `i <= sqrt(n)` or `i <= n/i` |
| Forgetting 1 is not prime | Edge case | Check n >= 2 |
| GCD of 0 and n | gcd(0, n) = n, not 0 | Handle edge cases |
| Off-by-one in combinatorics | C(n,n) = 1, C(n,0) = 1 | Verify boundary cases |

## Practice Problems

| # | Problem | Difficulty | Hint |
|---|---|---|---|
| 1 | Count primes less than n | Easy | Sieve of Eratosthenes |
| 2 | Power of three (no loops/recursion) | Easy | 3^19 is the largest power of 3 in int range |
| 3 | Excel column number (A→1, B→2, ..., Z→26, AA→27) | Easy | Base-26 conversion |
| 4 | Water and jug problem | Medium | Bézout's identity: ax + by = gcd(a,b) |
| 5 | Count numbers with unique digits | Medium | Permutation counting |
| 6 | Ugly number II (find nth number whose only prime factors are 2,3,5) | Medium | Three pointers / min-heap |
| 7 | Super Pow (a^(b array)) | Medium | Modular exponentiation + a^(10x+y) = (a^x)^10 · a^y |
| 8 | Integer to English words | Hard | Careful number decomposition |
| 9 | Number of digit one (count 1s in all numbers from 1 to n) | Hard | Digit-by-digit analysis |
| 10 | Count of range sum | Hard | Merge sort + prefix sums |

---

*In the next chapter, we'll use these mathematical foundations to analyze algorithm complexity — the single most important skill for technical interviews.*
