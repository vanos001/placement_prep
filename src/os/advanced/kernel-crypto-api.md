# Linux Kernel Crypto API: Handles, Requests, and the Async Fork

The kernel crypto API is the in-kernel plumbing behind dm-crypt volumes, fscrypt
filesystems, IPsec ESP, and the `/dev/crypto`-style userspace socket (AF_ALG,
not covered here). Its design is dominated by one constraint: crypto work is
frequently requested from **softirq context** -- packet paths and block
completion paths -- where sleeping is illegal and SIMD register use is
conditional, yet hardware accelerators and AES-NI wrappers complete work
*asynchronously*. Everything else (the `crypto_alloc_*` call zoo, the
`request` objects, the `crypto_wait` idiom, backlog semantics) follows from
that.

A survey-level mention plus the dm-crypt usage of this API lives in
[block-layer](../kernel-advanced/block-layer.md); this page covers the API
mechanics themselves.

---

## 1. Object model: algorithm, transform, request

```text
  crypto_alg  (one per implementation, on crypto_alg_list)
     |  crypto_alloc_skcipher("xts(aes)", 0, 0)
     v
  crypto_tfm / crypto_skcipher  ("tfm")   -- configuration handle: key, flags
     |  skcipher_request_alloc(tfm, GFP_KERNEL)   (or SKCIPHER_REQUEST_ON_STACK)
     v
  skcipher_request               -- one in-flight operation: src sg, dst sg,
     |                              len, IV, callback
     v
  crypto_skcipher_encrypt(req) -> 0 | -EINPROGRESS | -EBUSY | -EINVAL ...
        completion: req->base.complete(req->base.data)  [possibly softirq ctx]
```

A **tfm** is a configured object (key set, IV size fixed) -- think connection,
not operation. A **request** is one operation over that connection. Requests
carry their own completion callback because the submit call usually returns
before the work is done. shash is the one exception: it is strictly
synchronous with no request object, which is why non-softirq hash consumers
(dm-verity, dm-integrity) prefer it.

## 2. Names, drivers, priorities: how lookup works

Every registered algorithm has:

| Field | Meaning | Example |
|---|---|---|
| `cra_name` | generic/standard name many callers ask for | `xts(aes)` |
| `cra_driver_name` | implementation-specific instance name | `xts(aes-aesni)` |
| `cra_priority` | unsigned ranking; lookup returns the highest | 351 (aesni xts) vs 100 (generic) |
| `cra_flags` | type bits + `CRYPTO_ALG_ASYNC` + tested/internal flags | -- |
| `cra_blocksize` / `ctxsize` / `init/exit` | geometry and per-tfm context constructor | -- |

`crypto_alloc_*` takes `(name, type, mask)` and resolves by the rule
`((cra_flags ^ type) & mask) == 0`: bits set in `mask` must match exactly
between what the caller declared and the algorithm's flags. Passing
`CRYPTO_ALG_ASYNC` in `mask` *forbids* async; passing it in `type` *requires*
it; omitting it from both accepts either. Among matching algorithms, the
highest `cra_priority` wins (registration order breaks ties). Templates
(`xts`, `gcm`, `ctr`, `cts`, `rfc4106`, `pkcs1pad`, `adiantum`) instantiate
instances over child algorithms at lookup time:

```text
  "gcm(aes)"  ->  template "gcm"  spawns over  "aes"
                 |  best child by priority: aes-aesni
                 |  gcm needs ctr(aes) + ghash:
                 v
  instance "gcm_base(ctr(aes-aesni),ghash-clmulni)"   (registered on the fly)
```

Callers can also ask for a `cra_driver_name` directly to pin an
implementation, but pinning is an anti-pattern: it defeats the arch fallback
and breaks on other hardware.

## 3. Sync vs async: the `crypto_wait` idiom

An async submit returns `-EINPROGRESS` (accepted, completion will come via
callback) or `-EBUSY` (hardware/driver queue full; with
`CRYPTO_TFM_REQ_MAY_BACKLOG` the request is backlogged and *will* still be
submitted and completed by the driver -- without the backlog flag `-EBUSY`
means "rejected, try later"). The canonical synchronous wrapper from
[api-samples](https://docs.kernel.org/crypto/api-samples.html):

```c
DECLARE_CRYPTO_WAIT(wait);
skcipher_request_set_callback(req, CRYPTO_TFM_REQ_MAY_BACKLOG,
                              crypto_req_done, &wait);
err = crypto_skcipher_encrypt(req);
if (err == -EINPROGRESS || err == -EBUSY)
        err = crypto_wait_req(err, &wait);   /* sleep until callback */
```

`crypto_req_done` just calls `complete()`; it may run in **softirq context**,
which is precisely why the waiter must sleep rather than spin with locks held.
Three context rules follow:

1. **Process context** (fscrypt, key mgmt): may use sync or async freely;
   many drivers keep it simple with sync-only tfms.
2. **Softirq / atomic** (dm-crypt's completion path, IPsec ESP output): must
   not sleep -> either require an async-capable tfm (`mask = 0`, tolerate
   `-EINPROGRESS` and finish in the callback) or bounce to a workqueue.
3. **SIMD discipline**: AES-NI may only be used when `may_use_simd()` holds;
   in softirq on a preemptible kernel it often doesn't, so the aesni wrapper
   for AEAD/modes defers through **cryptd** -- a kernel thread that re-executes
   the request in task context where FPU state is legal. That is why "async
   AES-GCM on x86" completes on a cryptd worker even without real hardware.

## 4. A skcipher request lifecycle, dm-crypt-shaped

dm-crypt encrypts each bio's pages with XTS before issue (write path) and
after completion (read path):

1. at table-load: `crypto_alloc_skcipher("capi:xts(aes)-aesni" or "xts(aes)")`,
   `crypto_skcipher_setkey()` with the per-device key from the keyslot manager;
2. per-bio (in `kcryptd` worker or on the fly): fill a request from the
   per-CPU tfm -- `skcipher_request_set_crypt(req, src_in, dst_out,
   bio->bi_iter.bi_size, iv)`, with the IV generator (plain/essiv) producing
   the sector-number tweak per 512-byte sector -> 16-byte XTS tweak;
3. `skcipher_walk_virt()`/`walk_done` in the implementation step over the
   scatterlist in `crypto_skcipher_walksize` chunks so drivers see aligned
   pages;
4. submit; completion callback decrypts the next stage or ends the bio.

The per-sector IV granularity is the reason the API is request-per-bio, not
request-per-disk: [dm-crypt](../../linux/kernel/drivers/dm-crypt.md) maps
this to bio granularity and [block-layer](../kernel-advanced/block-layer.md)
shows where it sits relative to blk-mq.

## 5. Generic vs arch-optimized implementations

Every primitive ships a portable C implementation (`*-generic`) plus
architecture backends that register themselves with higher priorities:
`aes-aesni`/`aesni-intel` (with `ghash-clmulni` for GCM's GHASH and
`sha256-avx2`-style digests) on x86, `aes-ce` on arm64. Arch code registers
*algorithms* (cipher cores) and *mode-glue* (XTS/LRW implementations that call
the block cipher directly, avoiding template overhead and enabling per-mode
tuning). Two consequences:

- **Priority lookup is the selection mechanism** -- the same `crypto_alloc`
  call gets AES-NI on one host and generic C on another, with no caller
  changes (the demo below models this).
- **Fallback is structural**: arch modes instantiate over the best child
  cipher, so a mode built on `aes-aesni` silently degrades to `aes-generic`
  hardware-free hosts. Hardware AES is also the constant-time story -- table
  lookup software AES is a cache-timing hazard (see
  [constant-time](../../security/advanced/side-channel-resistant.md)).

## 6. Testmgr: the self-test gate

`crypto/testmgr.c` runs known-answer and randomized vectors at registration
and template instantiation; an algorithm that fails is not usable (lookup
prefers `CRYPTO_ALG_TESTED`-flagged algorithms, and instantiation triggers
`cryptomgr` tests before the instance is returned). This is also the FIPS
mode enforcement point (`fips=1` restricts to tested/approved algorithms and
panics the registration path on failure). Practical corollary: a new arch
backend that disagrees with the generic reference implementation by one byte
will be rejected at boot -- the test vectors *are* the contract.

## Interview questions

1. **"Why does dm-crypt care whether its skcipher is async?"** Bio completion
   runs in softirq. A sync-only tfm forces inline crypto in softirq context --
   fine with AES-NI in non-preemptible builds, but an accelerator tfm must
   complete via callback; dm-crypt handles both by ending bios from the
   crypto completion path, so it *prefers* async tfms and queues work when
   the driver backlogs.
2. **"You see `-EBUSY` from `crypto_skcipher_encrypt` -- did the request run?"**
   With `MAY_BACKLOG` it was queued and will complete later (keep waiting);
   without it, it was rejected -- resubmit. Confusing the two loses or
   double-completes requests.
3. **"Why does `crypto_alloc_skcipher("xts(aes)")` return a different driver
   name on two servers?"** Priority lookup over registered implementations:
   the host with AES-NI instantiates `xts(aes-aesni)` (prio 351), the other
   falls back to `xts(aes-generic)` (prio 100). Same API, same name, different
   backend -- check `/proc/crypto`.
4. **"shash vs ahash -- when do you actually need ahash?"** Only when the
   completion must be offloaded (hardware hash engines, or when the caller
   cannot afford synchronous hashing in softirq); ahash costs a request +
   callback. dm-verity and dm-integrity stay on shash because their callers
   are process-context.

```python
# Mini crypto-API model. (1) crypto_alloc() name resolution with the kernel's
# ((alg_flags ^ type) & mask) == 0 rule and highest-cra_priority winner.
# (2) async skcipher request engine with -EBUSY backlog and the crypto_wait
# sync wrapper. Deterministic; values are model parameters, not measured.
CRYPTO_ALG_ASYNC = 0x80     # CRYPTO_ALG_ASYNC (include/linux/crypto.h)

# (generic name, driver name, priority, flags)
REGISTRY = [
    ("xts(aes)", "xts(aes-aesni)",   351, 0),
    ("xts(aes)", "xts(aes-generic)", 100, 0),
    ("gcm(aes)", "gcm_base(ctr(aes-aesni),ghash-clmulni)", 300, CRYPTO_ALG_ASYNC),
    ("gcm(aes)", "gcm(aes-generic)", 100, 0),
    ("sha256",   "sha256-avx2",      250, 0),
    ("sha256",   "sha256-generic",   100, 0),
]

def crypto_alloc(name, type_, mask):
    """crypto_alg_lookup rule: ((alg.flags ^ type) & mask) == 0, best priority."""
    cands = [a for a in REGISTRY
             if a[0] == name and ((a[3] ^ type_) & mask) == 0]
    return max(cands, key=lambda a: a[2]) if cands else None

SYNC_ONLY = (0, CRYPTO_ALG_ASYNC)          # mask forbids async
ASYNC_OK  = (0, 0)                         # either completion style
ASYNC_REQ = (CRYPTO_ALG_ASYNC, CRYPTO_ALG_ASYNC)  # caller demands async

print("== crypto_alloc resolution: ((flags ^ type) & mask) == 0, max(cra_priority) ==")
for name, (ty, mk), caller in [("xts(aes)", ASYNC_OK,  "dm-crypt (softirq-safe, either)"),
                               ("gcm(aes)", SYNC_ONLY, "fscrypt-style inline caller"),
                               ("gcm(aes)", ASYNC_REQ, "ESP-style async consumer"),
                               ("sha256",   ASYNC_OK,  "hash of a bio (sync shash)")]:
    a = crypto_alloc(name, ty, mk)
    print(f"  {caller:<32} alloc({name!r},0x{ty:02x},0x{mk:02x}) -> {a[1]} (prio {a[2]})")

# ---- part 2: async skcipher engine, queue depth 2; driver returns -EBUSY ----
QDEPTH, LAT = 2, 10
trace, inflight, backlog = [], [], []
t = 0
rcs = {}
for req in range(1, 6):
    if len(inflight) < QDEPTH:
        inflight.append((req, t + LAT))
        rcs[req] = "-EINPROGRESS"
        trace.append(f"t={t:>2} submit#{req} -> -EINPROGRESS")
    else:
        backlog.append(req)
        rcs[req] = "-EBUSY      "
        trace.append(f"t={t:>2} submit#{req} -> -EBUSY (queued via MAY_BACKLOG)")
    while inflight and inflight[0][1] <= t:
        r, _ = inflight.pop(0)
        trace.append(f"t={t:>2} done#{r}    <- crypto_req_done() callback (softirq ctx)")
        if backlog:
            nxt = backlog.pop(0)
            inflight.append((nxt, t + LAT))
            rcs[nxt] = "-EBUSY+wait "
            trace.append(f"t={t:>2} debacklog#{nxt} (request submitted by engine)")
    t += 1
while inflight or backlog:
    while inflight and inflight[0][1] <= t:
        r, _ = inflight.pop(0)
        trace.append(f"t={t:>2} done#{r}    <- crypto_req_done() callback (softirq ctx)")
        if backlog:
            nxt = backlog.pop(0)
            inflight.append((nxt, t + LAT))
            trace.append(f"t={t:>2} debacklog#{nxt} (request submitted by engine)")
    t += 1
print(f"\n== skcipher request trace (queue depth {QDEPTH}, HW latency {LAT}) ==")
for line in trace:
    print(" ", line)
einpr = sum(1 for v in rcs.values() if v.startswith("-EINPROGRESS"))
ebusy = sum(1 for v in rcs.values() if v.startswith("-EBUSY"))
print(f"\ncrypto_wait_req view: {einpr}x -EINPROGRESS + {ebusy}x -EBUSY -> sync caller")
print("slept on all 5 requests; completion callbacks fired crypto_req_done(wait)")
```

Real output:

```text
== crypto_alloc resolution: ((flags ^ type) & mask) == 0, max(cra_priority) ==
  dm-crypt (softirq-safe, either)  alloc('xts(aes)',0x00,0x00) -> xts(aes-aesni) (prio 351)
  fscrypt-style inline caller      alloc('gcm(aes)',0x00,0x80) -> gcm(aes-generic) (prio 100)
  ESP-style async consumer         alloc('gcm(aes)',0x80,0x80) -> gcm_base(ctr(aes-aesni),ghash-clmulni) (prio 300)
  hash of a bio (sync shash)       alloc('sha256',0x00,0x00) -> sha256-avx2 (prio 250)

== skcipher request trace (queue depth 2, HW latency 10) ==
  t= 0 submit#1 -> -EINPROGRESS
  t= 1 submit#2 -> -EINPROGRESS
  t= 2 submit#3 -> -EBUSY (queued via MAY_BACKLOG)
  t= 3 submit#4 -> -EBUSY (queued via MAY_BACKLOG)
  t= 4 submit#5 -> -EBUSY (queued via MAY_BACKLOG)
  t=10 done#1    <- crypto_req_done() callback (softirq ctx)
  t=10 debacklog#3 (request submitted by engine)
  t=11 done#2    <- crypto_req_done() callback (softirq ctx)
  t=11 debacklog#4 (request submitted by engine)
  t=20 done#3    <- crypto_req_done() callback (softirq ctx)
  t=20 debacklog#5 (request submitted by engine)
  t=21 done#4    <- crypto_req_done() callback (softirq ctx)
  t=30 done#5    <- crypto_req_done() callback (softirq ctx)

crypto_wait_req view: 2x -EINPROGRESS + 3x -EBUSY -> sync caller
slept on all 5 requests; completion callbacks fired crypto_req_done(wait)
```

The second half of the trace shows the property that surprises newcomers:
backlogged requests complete *later* (t=20/30) but still through the same
callback -- the sync wrapper just parks on a completion until then.

## References

1. Kernel crypto API architecture (types, masks, priorities, templates, spawn):
   <https://docs.kernel.org/crypto/architecture.html> (HTTP 200).
2. Kernel crypto API interface specification (sync/async concepts):
   <https://docs.kernel.org/crypto/intro.html> (HTTP 200).
3. Programming interface (tfm/request allocators, `crypto_alloc_*`):
   <https://docs.kernel.org/crypto/api.html> (HTTP 200).
4. Symmetric key cipher API (`skcipher_request_*`, walks):
   <https://docs.kernel.org/crypto/api-skcipher.html> (HTTP 200).
5. AEAD API (`crypto_aead_*`, associated data):
   <https://docs.kernel.org/crypto/api-aead.html> (HTTP 200).
6. Code examples (`DECLARE_CRYPTO_WAIT`, `crypto_req_done`, `crypto_wait_req`):
   <https://docs.kernel.org/crypto/api-samples.html> (HTTP 200).
7. fscrypt documentation (kernel crypto API consumer, modes and key derivation):
   <https://docs.kernel.org/filesystems/fscrypt.html> (HTTP 200).
8. dm-crypt documentation (IV generators, cipher specs):
   <https://docs.kernel.org/admin-guide/device-mapper/dm-crypt.html> (HTTP 200).
