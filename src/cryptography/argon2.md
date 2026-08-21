# Argon2

Argon2 is a memory-hard password hashing function designed by Alex Biryukov, Daniel Dinu, and Dmitry Khovratovich for the Password Hashing Competition (PHC), held 2013-2015. It won the competition and is the current best-practice password hash, replacing bcrypt (1999) and scrypt (2009). Argon2 is specified in RFC 9106 (2021) and is part of the libsodium API. This page covers the algorithm, the variants (Argon2d, Argon2i, Argon2id), the tuning parameters, and the migration path from bcrypt.

## Why Memory-Hard Hashing?

Password hashing must be slow enough to make brute-force expensive, but fast enough to validate legitimate logins in ~100 ms. The historical progression:

- **crypt (1979)**: 25 iterations of DES. ~0.1 ms. Trivial to brute-force.
- **MD5crypt (1994)**: 1000 iterations of MD5. ~1 ms. Still trivially broken.
- **bcrypt (1999)**: 2^cost iterations of Blowfish, with cost=12 → ~250 ms. Hard to break on CPUs, but feasible on GPUs (1000× faster).
- **scrypt (2009)**: PBKDF2-like core + memory-hard (16 MB working set). GPU and ASIC performance degraded to ~CPU speed because GPU memory bandwidth is the bottleneck.
- **Argon2 (2015)**: Improved memory-hard + side-channel resistant. Default for new systems.

The progression is in response to attack hardware: CPUs → GPUs (highly parallel, high-bandwidth memory) → ASICs (custom silicon for bcrypt/scrypt). Each new hash function raises the cost of an attack.

## The Argon2 Algorithm

Argon2 fills a large block of memory (e.g., 64 MB) with derived data, then mixes it with the password and salt, producing a hash. The memory-hard property comes from the fact that the attacker must either:

1. **Compute the memory blocks sequentially**: limited by memory bandwidth. GPUs are no faster than CPUs.
2. **Compute the blocks in parallel**: requires storing all the blocks, which costs as much memory as the legitimate computation. ASICs would need the same 64 MB per hash as the defender.

The algorithm in pseudocode:

```text
1. Allocate matrix B[m][n] of 1 KB blocks.
   - m = parallelism (lanes)
   - n = memory_blocks / parallelism

2. Initial blocks:
   B[0][0] = H(P || S || p || T || m || t || v || y || K || X)
   where H is Blake2b, P=password, S=salt, p=parallelism,
   T=type, m=memory, t=iterations, v=version, y=output length,
   K=optional key, X=optional associated data.

3. Compute first row of each lane:
   B[i][0] for i in 1..m-1: H(B[0][0] || i || 0)

4. Compute first column of each lane:
   B[0][j] for j in 1..n-1: H(B[0][0] || 0 || j)

5. Fill the rest:
   For each block B[i][j] in dependency order:
     ref_block = pseudo-randomly chosen from earlier blocks
     B[i][j] = G(B[i][j-1] XOR B[ref_block.i][ref_block.j], B[i][j-1])
   where G is a compression function (Blake2b-based, 1 KB → 1 KB)

6. After t passes over the matrix:
   C = B[i_max][j_max] XOR B[i_max][j_max] (for all i_max)
   output = H(C)  ← the resulting hash
```

The `t` parameter is the "time cost" — the number of passes over the matrix. More passes = more security but slower.

## The Three Variants

- **Argon2d** (data-dependent): the `ref_block` selection depends on the contents of earlier blocks. Faster, but vulnerable to side-channel attacks (cache-timing attacks can leak the password if the attacker can observe memory accesses).
- **Argon2i** (data-independent): the `ref_block` selection is determined by the iteration count alone, not by data. Slower (more memory accesses for the same security) but side-channel safe. Recommended for password hashing where side-channels are a concern.
- **Argon2id** (hybrid): data-independent for the first half of memory, data-dependent for the second half. Side-channel safe for the first pass; faster overall. **Recommended default**.

RFC 9106 recommends Argon2id for general use. libsodium uses Argon2id as its `crypto_pwhash` algorithm.

## Tuning Parameters

```c
argon2id(
    out,        // output buffer
    out_len,    // typically 32 bytes (the hash)
    pwd,        // password
    pwd_len,
    salt,       // 16 random bytes
    salt_len,
    t_cost,     // iterations (passes), default 3
    m_cost,     // memory in KB, default 65536 (64 MB)
    parallelism, // threads, default 4
    type        // Argon2id
);
```

Recommended parameters (for ~100 ms hashing time on a modern CPU, 2024):

| Use case | t_cost | m_cost | parallelism | Time |
|----------|-------:|-------:|------------:|-----:|
| Low-risk (consumer app) | 1 | 16 MB | 2 | 30 ms |
| Standard (recommended) | 3 | 64 MB | 4 | 100 ms |
| High-value (banking) | 3 | 256 MB | 8 | 500 ms |
| Sensitive (admin accounts) | 5 | 1 GB | 8 | 2 sec |

These should be revisited every 2-3 years as hardware improves. A parameter set that takes 100 ms today will take 50 ms in 3 years (Moore's law).

The libsodium API exposes this:

```c
char hash[crypto_pwhash_STRBYTES];
crypto_pwhash_str(
    hash,
    password, strlen(password),
    crypto_pwhash_OPSLIMIT_INTERACTIVE,    // or SENSITIVE
    crypto_pwhash_MEMLIMIT_INTERACTIVE,     // or SENSITIVE
    crypto_pwhash_ALG_ARGON2ID13
);
// hash is in PHC string format: $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
```

## The PHC String Format

Password hashes are stored in a self-describing string format that includes the parameters used:

```text
$argon2id$v=19$m=65536,t=3,p=4$YXNkZmdoamts$WVFZQk1BV0RPV0pEU1RGRA

└─ algorithm ─┘  └ params ─┘ └─ salt (b64) ─┘ └─ hash (b64) ─┘
```

This allows parameter changes over time without invalidating existing hashes: when a user logs in, the system reads their stored hash's parameters, recomputes the hash with those parameters, and validates. If the parameters are weaker than the current standard, the system can re-hash with the new parameters on next login (transparent upgrade).

## Migration from bcrypt

Existing systems with bcrypt hashes should not invalidate passwords; instead, the migration strategy is:

1. When a user logs in successfully (validating the bcrypt hash), compute a new Argon2id hash.
2. Store the Argon2id hash alongside the bcrypt hash (or replace it).
3. Future logins use the Argon2id hash.

This is "lazy migration" — only users who log in get the upgrade. Users who never log in keep their bcrypt hash (which is still ~250 ms to break per password).

## Comparison Table

| Hash | Memory | Time (100 ms target) | GPU speedup | ASIC resistant | Notes |
|------|--------|----------------------|--------------|----------------|-------|
| bcrypt | 4 KB | 250 ms (cost=12) | 100× | No | Single-threaded, GPU-friendly |
| scrypt | 16 MB | 100 ms | 10× | Mostly | Memory-hard |
| Argon2id | 64 MB | 100 ms | 1× (memory-bound) | Yes | Recommended |
| PBKDF2 | 0 KB | 100 ms | 1000× | No | Don't use |

PBKDF2 is "memory-easy" — it iterates a hash function with no memory cost, so GPUs and ASICs can run millions of iterations in parallel. It should not be used for new password storage.

## Common Pitfalls

1. **Using too-low memory.** A 1 MB memory cost makes Argon2 no better than scrypt. Use at least 16 MB, ideally 64 MB or more.

2. **Not setting parallelism correctly.** If your server has 8 cores and you set parallelism=4, you can validate 2 simultaneous logins per core. Set parallelism based on your server's concurrency.

3. **Comparing hashes with `==`.** Use a constant-time comparison (`crypto_verify` in libsodium) to prevent timing attacks. The string comparison `==` leaks via timing.

4. **Storing the salt in a separate column.** The salt is included in the PHC string format; storing it separately is redundant. The whole PHC string is the hash + parameters + salt.

5. **Generating the salt with `Math.random()` or `time()`.** The salt must be cryptographically random — use `/dev/urandom` (or `crypto_pwhash` which generates it internally). Predictable salts enable precomputed attacks.

6. **Reusing salts across users.** Two users with the same salt and same password get the same hash, leaking info. Generate a unique salt per hash.

7. **Forgetting to upgrade parameters over time.** Moore's law makes 100 ms today become 50 ms in 3 years. Re-evaluate annually.

8. **Locking users out during upgrade.** Some implementations require the user to log in to upgrade their hash. A user who hasn't logged in for years still has the old (weak) hash. Consider migrating proactively to higher-cost bcrypt first, then to Argon2id.

## References

- [RFC 9106: Argon2](https://datatracker.ietf.org/doc/html/rfc9106)
- Argon2 PHC submission: [the paper](https://www.password-hashing.net/argon2-2015.pdf)
- Alex Biryukov's Argon2 page: [https://www.cryptolux.org/index.php/Argon2](https://www.cryptolux.org/index.php/Argon2)
- [libsodium password hashing documentation](https://doc.libsodium.org/password_hashing/)
- [OWASP password storage cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Password Hashing Competition results](https://www.password-hashing.net/)
- [Hacker News: Argon2 vs bcrypt (2020 discussion)](https://news.ycombinator.com/item?id=24019400)
- [Dropbox: Bcrypt and Argon2 migration](https://dropbox.tech/security/how-dropbox-securely-stores-your-passwords)
