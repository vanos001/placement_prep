# Number Theory for Programming

## Fast Exponentiation

Compute a^b mod m in O(log b):

```python
def power(a, b, m):
    result = 1
    a %= m
    while b > 0:
        if b & 1:           # b is odd
            result = result * a % m
        a = a * a % m
        b >>= 1             # b = b / 2
    return result

# Example: 2^10 mod 1000
# 2^10 = 1024, 1024 mod 1000 = 24
# Computed in 4 iterations (log2(10) ≈ 4)
```

## Modular Inverse

```python
# Extended Euclidean Algorithm
def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x, y = extended_gcd(b % a, a)
    return gcd, y - (b // a) * x, x

def mod_inverse(a, m):
    gcd, x, _ = extended_gcd(a, m)
    if gcd != 1:
        return None  # No inverse
    return x % m
```

## Sieve of Eratosthenes

Find all primes up to n in O(n log log n):

```python
def sieve(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = is_prime[1] = False
    for i in range(2, int(n**0.5) + 1):
        if is_prime[i]:
            for j in range(i*i, n+1, i):
                is_prime[j] = False
    return [i for i in range(n+1) if is_prime[i]]
```

## GCD and LCM

```python
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def lcm(a, b):
    return a * b // gcd(a, b)
```

## Euler's Totient Function

φ(n) = count of integers from 1 to n that are coprime with n.

```
φ(p) = p - 1 (for prime p)
φ(p^k) = p^k - p^(k-1)
φ(mn) = φ(m) × φ(n) (if coprime)

Example: φ(12) = φ(4) × φ(3) = 2 × 2 = 4
Coprime with 12: {1, 5, 7, 11}
```

**Fermat's Little Theorem**: a^(p-1) ≡ 1 (mod p) if p is prime and gcd(a,p) = 1

## Chinese Remainder Theorem

Solve system of congruences:
```
x ≡ a₁ (mod m₁)
x ≡ a₂ (mod m₂)
...
x ≡ aₖ (mod mₖ)

If m₁, m₂, ..., mₖ are pairwise coprime, solution exists and is unique mod M = m₁×m₂×...×mₖ
```

```python
def crt(remainders, moduli):
    M = 1
    for m in moduli:
        M *= m
    x = 0
    for a, m in zip(remainders, moduli):
        Mi = M // m
        yi = mod_inverse(Mi, m)
        x = (x + a * Mi * yi) % M
    return x
```

## Miller-Rabin Primality Test

Probabilistic test — false positive probability ≤ 4^(-k) for k rounds:

```python
def miller_rabin(n, k=20):
    if n < 2: return False
    if n == 2 or n == 3: return True
    if n % 2 == 0: return False
    
    # Write n-1 as 2^r × d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True
```

## Pollard's Rho Algorithm

Factor large numbers in O(n^(1/4)):

```python
def pollard_rho(n):
    if n % 2 == 0: return 2
    x = random.randint(2, n - 1)
    y = x
    c = random.randint(1, n - 1)
    d = 1
    while d == 1:
        x = (x * x + c) % n
        y = (y * y + c) % n
        y = (y * y + c) % n
        d = gcd(abs(x - y), n)
    return d if d != n else None
```

## Interview Questions

**Q: How do you compute a^b mod m efficiently?**
A: Binary exponentiation (fast power). Process bits of b from LSB to MSB. If bit is set, multiply result by current base. Square the base each step. O(log b) time.

**Q: What is the Sieve of Eratosthenes?**
A: Algorithm to find all primes up to n. Start with all numbers marked prime. For each prime p, mark all multiples of p as composite. Start marking from p² (smaller multiples already marked). O(n log log n) time.

**Q: What is the Chinese Remainder Theorem used for in programming?**
A: Solving systems of modular equations. Used in: competitive programming (large number arithmetic), cryptography (RSA decryption optimization), distributed systems (consistent hashing). Enables working with large numbers by decomposing into smaller moduli.

## References

- [CP-Algorithms — Number Theory](https://cp-algorithms.com/)
- [Introduction to Algorithms — CLRS, Chapter 31](https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/)
